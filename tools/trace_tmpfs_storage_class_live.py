"""Read-only Boot119 tmpfs storage-class contract observation, no policy edits.

Launch only through macvm_require_debug_env in isolated Linux. Observe one
mktemp directory-creation probe below the known role-account tmp directory.
"""
import os
import struct
import time

import gdb

if os.environ.get('MACVM_TMPFS_TRACE_CONFIRMED') != 'BOOT119_READ_ONLY':
    raise RuntimeError('explicit read-only Boot119 opt-in required')
SLIDE = 0x19344000
SITES = {
    0xFFFFFE0009717F58: ('enter', 0xD503237F),
    0xFFFFFE0009718058: ('getattr-return', 0x35001340),
    0xFFFFFE0009718128: ('getxattr-return', 0xAA0003F7),
    0xFFFFFE000971816C: ('getparent-return', 0xB40005A0),
    0xFFFFFE0009717FDC: ('return', 0xAA1703E0),
}
active = {}
breakpoints = []
started = time.monotonic()


def reg(name):
    return int(gdb.parse_and_eval('$' + name)) & 0xFFFFFFFFFFFFFFFF


def read(address, count):
    address &= 0xFFFFFFFFFFFFFFFF
    if not 0xFFFFFE0000000000 <= address < 0xFFFFFF0000000000 or not 0 < count <= 4096:
        raise ValueError('read outside kernel data range')
    return gdb.selected_inferior().read_memory(address, count).tobytes()


def u64(address):
    return struct.unpack('<Q', read(address, 8))[0]


def pointer(raw):
    bits = 64 - ((reg('TCR_EL1') >> 16) & 63)
    if not 39 <= bits <= 48 or raw == 0:
        raise ValueError('invalid kernel pointer')
    mask = (1 << bits) - 1
    return raw & mask | (0xFFFFFFFFFFFFFFFF ^ mask)


def names(vnode):
    result = []
    for _ in range(6):
        raw = read(vnode, 0xC8)
        name = struct.unpack_from('<Q', raw, 0xB8)[0]
        if not name:
            break
        result.append(read(name, min(256, 0x4000 - (name & 0x3FFF))).split(b'\0', 1)[0].decode())
        parent = struct.unpack_from('<Q', raw, 0xC0)[0]
        if not parent:
            break
        vnode = pointer(parent)
    return result


class Observe(gdb.Breakpoint):
    def __init__(self, address, label):
        super().__init__(f'*{address + SLIDE:#x}', gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        self.label = label

    def stop(self):
        try:
            thread = reg('TPIDR_EL1')
            if self.label == 'enter':
                proc = pointer(u64(pointer(u64(thread + 0x3E8)) + 0x18))
                if read(proc + 0x5CC, 17).split(b'\0', 1)[0] != b'mktemp':
                    return False
                path = names(reg('x0'))
                if path[:5] != ['tmp', 'com.apple.xpc.roleaccountd.staging', 'db', 'var', 'private']:
                    return False
                active[thread] = (reg('x2'), reg('x3'))
                gdb.write(f'MACVM_STORAGE_ENTER flags={reg("x1"):#x} path={path!r}\n')
            elif thread not in active:
                return False
            elif self.label == 'getattr-return':
                attrs = read(reg('sp') + 0x20, 0x1B0)
                supported, requested = struct.unpack_from('<QQ', attrs)
                flags = struct.unpack_from('<I', attrs, 0x50)[0]
                extflags = struct.unpack_from('<Q', attrs, 0x1A8)[0]
                gdb.write(f'MACVM_STORAGE_ATTR result={reg("x0")} supported={supported:#x} requested={requested:#x} flags={flags:#x} extflags={extflags:#x}\n')
            elif self.label == 'getxattr-return':
                gdb.write(f'MACVM_STORAGE_XATTR result={reg("x0")} vnode={reg("x20"):#x}\n')
            elif self.label == 'getparent-return':
                gdb.write(f'MACVM_STORAGE_PARENT result={reg("x0"):#x}\n')
            elif self.label == 'return':
                classptr, anchorptr = active.pop(thread)
                gdb.write(f'MACVM_STORAGE_RETURN errno={reg("x23")} class={read(classptr, 1).hex()} anchor={u64(anchorptr):#x}\n')
                return True
            if time.monotonic() - started > 600:
                return True
            return False
        except Exception as error:
            gdb.write(f'MACVM_STORAGE_TRACE_ERROR {error!r}\n')
            return True


try:
    gdb.execute('set pagination off')
    gdb.execute('set confirm off')
    gdb.execute('set architecture aarch64')
    gdb.execute('set print thread-events off')
    gdb.execute('target remote 127.0.0.1:12355')
    for address, (label, word) in SITES.items():
        if struct.unpack('<I', read(address + SLIDE, 4))[0] != word:
            raise ValueError(f'exact instruction mismatch at {address:#x}')
        breakpoints.append(Observe(address, label))
    gdb.write('MACVM_STORAGE_TRACE_ARMED read_only=1\n')
    gdb.execute('continue')
finally:
    for bp in breakpoints:
        if bp.is_valid():
            bp.delete()
    if gdb.selected_inferior().pid:
        gdb.execute('detach')
    gdb.write('MACVM_STORAGE_TRACE_DETACHED\n')
