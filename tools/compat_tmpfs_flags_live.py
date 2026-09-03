"""Temporary, narrowly scoped Recovery metadata bridge, run by guest GDB.

Linux launcher must call macvm_require_debug_env first. Hardware breakpoints
observe tmpfs with its node lock held; no guest instructions, signatures,
AMFI decisions or register values are patched. Detaching removes the bridge.
"""
import os
import json
from pathlib import Path
import struct
import sys
import time

import gdb

sys.path.insert(0, "/home/macvm/src/macvm/tools")
from tmpfs_flags_contract import (
    ANCHOR, CREATE_SUCCESS, GETATTR_LOCKED, SF_RESTRICTED,
    creation_flags, existing_flags, relative_components, verify_instructions,
    extended_flags_response, new_child_path, VA_EXTFLAGS_ACTIVE,
    verified_boot120_identity,
)

opt_in = os.environ.get("MACVM_TMPFS_COMPAT_CONFIRMED")
EXPECTED_ANCHOR_NODE = None
if opt_in == "BOOT119_ONLY":
    BOOT = 119
    SLIDE = 0x19344000
    EXPECTED_ANCHOR_VNODE = 0xFFFFFE1E3F8DB8C8
elif opt_in == "BOOT120_VERIFIED":
    BOOT = 120
    identity = Path('/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot120-internal-install/tmpfs-staging-anchor.json')
    if identity.is_symlink() or not 0 < identity.stat().st_size < 4096:
        raise RuntimeError('invalid observed boot identity file')
    record = json.loads(identity.read_text())
    SLIDE, EXPECTED_ANCHOR_VNODE, EXPECTED_ANCHOR_NODE = verified_boot120_identity(record)
    expected = Path('/home/macvm/src/macvm/build/qemu-boot119-graphics-storage/qemu-system-aarch64')
    if Path('/proc/974460/exe').resolve(strict=True) != expected:
        raise RuntimeError('observed Boot120 process no longer matches')
else:
    raise RuntimeError("explicit, verified boot metadata compatibility opt-in required")
breakpoints = []
started = time.monotonic()
counts = {"create": 0, "existing": 0, "extflags": 0, "observed": 0}
# Every write is bound to the protected anchor for this particular live boot.
repair_existing = os.environ.get("MACVM_TMPFS_REPAIR_EXISTING") == "YES"
storage_active = {}
storage_queries = 0


def read(address, size):
    if not 0xFFFFFE0000000000 <= address < 0xFFFFFF0000000000 or not 0 < size <= 4096:
        raise ValueError("unsafe kernel read")
    return gdb.selected_inferior().read_memory(address, size).tobytes()


def u32(address):
    return struct.unpack("<I", read(address, 4))[0]


def u64(address):
    return struct.unpack("<Q", read(address, 8))[0]


def pointer(raw):
    if not raw:
        return 0
    bits = 64 - ((int(gdb.parse_and_eval("$TCR_EL1")) >> 16) & 63)
    if not 39 <= bits <= 48:
        raise ValueError("unexpected kernel pointer width")
    mask = (1 << bits) - 1
    result = raw & mask | (0xFFFFFFFFFFFFFFFF ^ mask)
    if not 0xFFFFFE0000000000 <= result < 0xFFFFFF0000000000:
        raise ValueError("invalid canonical kernel pointer")
    return result


def reg(name):
    return int(gdb.parse_and_eval("$" + name)) & 0xFFFFFFFFFFFFFFFF


def lineage(vnode):
    names, objects, seen = [], [], set()
    for _ in range(32):
        if not vnode or vnode in seen:
            break
        seen.add(vnode)
        raw = read(vnode, 0xE8)
        nameptr, parent = struct.unpack_from("<QQ", raw, 0xB8)
        if not nameptr:
            break
        # VFS names are NUL-terminated. Read only through the containing page.
        length = min(256, 0x4000 - (nameptr & 0x3FFF))
        name = read(nameptr, length).split(b"\0", 1)[0].decode("utf-8", "strict")
        if not name or name == "/":
            break
        names.append(name)
        objects.append((vnode, struct.unpack_from("<Q", raw, 0xE0)[0]))
        if len(names) >= 4 and tuple(names[-4:]) == ANCHOR:
            relative = relative_components(tuple(names))
            anchor_vnode, anchor_node = objects[-4]
            # The protection already exists; the bridge never invents it.
            if (relative is None or anchor_vnode != EXPECTED_ANCHOR_VNODE
                    or (EXPECTED_ANCHOR_NODE is not None and anchor_node != EXPECTED_ANCHOR_NODE)
                    or not u32(anchor_node + 0x3C) & SF_RESTRICTED):
                return None
            return relative, objects, anchor_vnode, anchor_node
        vnode = pointer(parent)
    return None


def write_flags(node, old, new, reason, path):
    if new == old:
        return
    if new != old | SF_RESTRICTED or u32(node + 0x3C) != old:
        raise ValueError("metadata changed or attempted protection removal")
    # Mirrors tmpfs_chflags: update tn_flags and mark ctime pending; the
    # following tmpfs_update/normal unlock handles the ordinary vnode flow.
    changed = u32(node + 0x20)
    inferior = gdb.selected_inferior()
    inferior.write_memory(node + 0x3C, struct.pack("<I", new))
    inferior.write_memory(node + 0x20, struct.pack("<I", changed | 8))
    if u32(node + 0x3C) != new:
        raise ValueError("metadata write verification failed")
    counts[reason] += 1
    gdb.write(f"MACVM_TMPFS_FLAGS_{reason.upper()} path={path!r} old={old:#x} new={new:#x}\n")


class Bridge(gdb.Breakpoint):
    def __init__(self, address, kind):
        super().__init__(f"*{address + SLIDE:#x}", gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        self.kind = kind

    def stop(self):
        counts["observed"] += 1
        if counts["observed"] > 100000 or time.monotonic() - started > 7200:
            gdb.write(f"MACVM_TMPFS_FLAGS_LIMIT {counts!r}\n")
            return True
        try:
            if self.kind == "create":
                vnode, node = u64(reg("x23")), reg("x26")
                attrs, parentnode = reg("x21"), reg("x20")
                if u64(vnode + 0xE0) != node or u32(node + 0x14) not in (1, 2):
                    return False
                old = u32(node + 0x3C)
                new = creation_flags(old, u32(attrs + 0x50), u64(attrs + 8), u32(parentnode + 0x3C))
                if old == new:
                    return False
                # The new vnode is not yet name-cached here. Its parent is,
                # and the exact componentname is still live in x24.
                parentvnode = reg("x22")
                if u64(parentvnode + 0xE0) != parentnode:
                    raise ValueError("parent vnode/node mismatch")
                context = lineage(parentvnode)
                if context is None:
                    return False
                parent_relative, _, _, _ = context
                component = reg("x24")
                nameptr, namelen = u64(component + 0x28), u32(component + 0x30)
                if not 1 <= namelen <= 255:
                    return False
                relative = new_child_path(parent_relative, read(nameptr, namelen).decode("utf-8", "strict"))
                if relative is None:
                    return False
                write_flags(node, old, new, "create", relative)
            else:
                attrs = reg("x22")
                supported, requested = u64(attrs), u64(attrs + 8)
                need_extflags = bool(requested & VA_EXTFLAGS_ACTIVE and not supported & VA_EXTFLAGS_ACTIVE)
                if not need_extflags and not repair_existing:
                    return False
                vnode, node = reg("x20"), reg("x19")
                if not node or u64(vnode + 0xE0) != node or u32(node + 0x14) not in (1, 2):
                    return False
                old = u32(node + 0x3C)
                context = lineage(vnode)
                if context is None:
                    return False
                relative, _, _, anchor = context
                if need_extflags:
                    oldvalue = u64(attrs + 0x1A8)
                    newsupported, newvalue = extended_flags_response(supported, requested, oldvalue)
                    inferior = gdb.selected_inferior()
                    # Caller-owned vnode_attr result, not a policy decision or
                    # on-disk inode. tmpfs has no APFS extended state to report.
                    inferior.write_memory(attrs + 0x1A8, struct.pack("<Q", newvalue))
                    inferior.write_memory(attrs, struct.pack("<Q", newsupported))
                    if u64(attrs) != newsupported or u64(attrs + 0x1A8) != newvalue:
                        raise ValueError("extended attribute response verification failed")
                    counts["extflags"] += 1
                    if counts["extflags"] <= 16 or counts["extflags"] % 100 == 0:
                        gdb.write(f"MACVM_TMPFS_EXTFLAGS path={relative!r} supported={supported:#x}->{newsupported:#x} value=0 count={counts['extflags']}\n")
                if repair_existing:
                    new = existing_flags(old, u32(anchor + 0x3C), relative)
                    write_flags(node, old, new, "existing", relative)
        except (gdb.MemoryError, UnicodeDecodeError):
            # Uncached/unreadable names are not evidence for mutation.
            return False
        except Exception as error:
            gdb.write(f"MACVM_TMPFS_FLAGS_ERROR {error!r} {counts!r}\n")
            return True
        return False


class StorageObserve(gdb.Breakpoint):
    """Read-only confirmation of the actual role daemon's class resolution."""
    def __init__(self, address, kind):
        super().__init__(f"*{address + SLIDE:#x}", gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        self.kind = kind

    def stop(self):
        global storage_queries
        try:
            thread = reg("TPIDR_EL1")
            if self.kind == "enter":
                if storage_queries >= 8:
                    return False
                proc = pointer(u64(pointer(u64(thread + 0x3E8)) + 0x18))
                if read(proc + 0x5CC, 17).split(b"\0", 1)[0] != b"xpcroleaccountd":
                    return False
                context = lineage(reg("x0"))
                if context is None:
                    return False
                storage_queries += 1
                storage_active[thread] = (reg("x2"), reg("x3"))
                gdb.write(f"MACVM_ROLE_STORAGE_ENTER path={context[0]!r} flags={reg('x1'):#x}\n")
            elif thread in storage_active:
                if self.kind == "lookup":
                    address = reg("x0")
                    name = read(address, min(128, 0x4000 - (address & 0x3FFF))).split(b"\0", 1)[0]
                    gdb.write(f"MACVM_ROLE_STORAGE_LOOKUP name={name!r} type={reg('x1')}\n")
                else:
                    classptr, anchorptr = storage_active.pop(thread)
                    gdb.write(f"MACVM_ROLE_STORAGE_RETURN errno={reg('x23')} class={read(classptr, 1).hex()} anchor={u64(anchorptr):#x}\n")
        except (gdb.MemoryError, UnicodeDecodeError, ValueError) as error:
            storage_active.pop(reg("TPIDR_EL1"), None)
            gdb.write(f"MACVM_ROLE_STORAGE_OBSERVER_ERROR {error!r}\n")
        return False


try:
    gdb.execute("set pagination off")
    gdb.execute("set confirm off")
    gdb.execute("set architecture aarch64")
    gdb.execute("set print thread-events off")
    gdb.execute("set remotetimeout 30")
    gdb.execute("target remote 127.0.0.1:12355")
    verify_instructions(u32, SLIDE)
    breakpoints.append(Bridge(CREATE_SUCCESS, "create"))
    breakpoints.append(Bridge(GETATTR_LOCKED, "existing"))
    if os.environ.get("MACVM_TMPFS_TRACE_STORAGE") == "YES":
        for address, kind, word in (
            (0xFFFFFE0009717F58, "enter", 0xD503237F),
            (0xFFFFFE0009724050, "lookup", 0xD503237F),
            (0xFFFFFE0009717FDC, "return", 0xAA1703E0),
        ):
            if u32(address + SLIDE) != word:
                raise ValueError(f"storage observer instruction mismatch at {address:#x}")
            breakpoints.append(StorageObserve(address, kind))
    gdb.write(f"MACVM_TMPFS_FLAGS_ARMED boot={BOOT} signatures=unchanged amfi=unchanged\n")
    gdb.execute("continue")
finally:
    for bp in breakpoints:
        if bp.is_valid():
            bp.delete()
    if gdb.selected_inferior().pid:
        gdb.execute("detach")
    gdb.write(f"MACVM_TMPFS_FLAGS_DETACHED {counts!r}\n")
