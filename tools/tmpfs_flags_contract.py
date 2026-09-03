"""Narrow metadata compatibility contract for the 25G72 Recovery tmpfs.

This does NOT relax AMFI, SIP, launch constraints, or signature validation.
It only restores the protection bit that creation failed to inherit beneath
Apple's already protected RoleAccountStaging directory. No Apple code included.
"""
from __future__ import annotations

SF_RESTRICTED = 0x80000
VA_FLAGS_ACTIVE = 0x400
VA_EXTFLAGS_ACTIVE = 1 << 45
ANCHOR = ("com.apple.xpc.roleaccountd.staging", "db", "var", "private")
EXISTING_BUNDLE = "872415233.4126.xpc"
CREATE_SUCCESS = 0xFFFFFE0009BCCFBC
GETATTR_LOCKED = 0xFFFFFE0009BC6494
WORDS = {
    CREATE_SUCCESS: 0x5280001B,
    CREATE_SUCCESS + 4: 0x17FFFFBC,
    GETATTR_LOCKED - 4: 0x9402EEF9,
    GETATTR_LOCKED: 0xAA1403E0,
    0xFFFFFE0009BC6630: 0xB9403E69,  # node.flags at +0x3c
    0xFFFFFE0009BC6634: 0xB90052C9,  # vnode_attr.va_flags at +0x50
    0xFFFFFE0009BC6964: 0x94001DA3,  # tmpfs_chflags call
    0xFFFFFE0009EB00A8: 0xF9407000,  # vnode.v_data at +0xe0
    0xFFFFFE0009EB0FB4: 0xF84C0C10,  # vnode.v_parent at +0xc0
    0xFFFFFE0009E55E70: 0xF9405E73,  # vnode.v_name at +0xb8
}


def verified_boot120_identity(record: dict) -> tuple[int, int, int]:
    """Accept only the separately observed new boot, never an old vnode guess."""
    if not isinstance(record, dict):
        raise ValueError('invalid boot observation')
    if (type(record.get('boot')) is not int or record['boot'] != 120
            or type(record.get('qemu_pid')) is not int or record['qemu_pid'] != 974460
            or record.get('read_only_observation') is not True
            or record.get('leaf_to_root') != list(ANCHOR)):
        raise ValueError('wrong boot, process, or observed path')
    slide = record.get('slide')
    if type(slide) is not int or slide != 0x19344000:
        raise ValueError('wrong exact-image slide')
    pointers = [record.get('anchor_vnode'), record.get('anchor_node')]
    for pointer in pointers:
        if (type(pointer) is not int or not 0xFFFFFE0000000000 <= pointer < 0xFFFFFF0000000000
                or pointer % 8):
            raise ValueError('invalid observed kernel pointer')
    flags = u32(record.get('anchor_flags'))
    if not flags & SF_RESTRICTED:
        raise ValueError('observation did not establish protected anchor')
    return slide, pointers[0], pointers[1]


def u32(value: int) -> int:
    if type(value) is not int or not 0 <= value < 2**32:
        raise ValueError("not a uint32")
    return value


def verify_instructions(read_u32, slide: int) -> None:
    if type(slide) is not int or not 0 <= slide <= 0x40000000 or slide % 0x4000:
        raise ValueError("unexpected kernel slide")
    for address, word in WORDS.items():
        if read_u32(address + slide) != word:
            raise ValueError(f"instruction/layout mismatch at {address:#x}")


def relative_components(leaf_to_root: tuple[str, ...]) -> tuple[str, ...] | None:
    """Return a path relative to the exact anchor, never a basename match."""
    if not 4 <= len(leaf_to_root) <= 32:
        return None
    if any(not isinstance(p, str) or not p or len(p) > 255 or
           p in (".", "..") or "/" in p or "\0" in p for p in leaf_to_root):
        return None
    for index in range(len(leaf_to_root) - 3):
        if leaf_to_root[index:index + 4] == ANCHOR:
            return tuple(reversed(leaf_to_root[:index]))
    return None


def allow_existing_repair(relative: tuple[str, ...]) -> bool:
    # Existing probe files or unknown cached executables must not be relabelled.
    return relative in (("exec",), ("tmp",)) or (
        len(relative) >= 2 and relative[:2] == ("exec", EXISTING_BUNDLE)
    )


def creation_flags(current: int, requested: int, active: int, parent: int) -> int:
    current, requested, parent = map(u32, (current, requested, parent))
    if type(active) is not int or not 0 <= active < 2**64:
        raise ValueError("invalid vnode_attr active mask")
    if (active & VA_FLAGS_ACTIVE and requested & SF_RESTRICTED and
            parent & SF_RESTRICTED):
        return current | SF_RESTRICTED
    return current


def new_child_path(parent_relative: tuple[str, ...], name: str) -> tuple[str, ...] | None:
    """Use the already named parent: a newly allocated vnode is not cached yet."""
    if not isinstance(parent_relative, tuple) or not parent_relative or parent_relative[0] not in ("tmp", "exec"):
        return None
    result = parent_relative + (name,)
    # Reuse the exact component validation, including traversal and depth limits.
    if relative_components(tuple(reversed(result)) + ANCHOR) != result:
        return None
    return result


def extended_flags_response(supported: int, requested: int, value: int) -> tuple[int, int]:
    """Ordinary tmpfs has no APFS clone/firmlink/seal extended state.

    Only synthesize its absent, explicitly requested zero-valued attribute.
    Existing supported attributes and every other bit must remain unchanged.
    Caller must additionally prove this is the known protected tmpfs subtree.
    """
    for item in (supported, requested, value):
        if type(item) is not int or not 0 <= item < 2**64:
            raise ValueError("invalid extended attribute uint64")
    if requested & VA_EXTFLAGS_ACTIVE and not supported & VA_EXTFLAGS_ACTIVE:
        return supported | VA_EXTFLAGS_ACTIVE, 0
    return supported, value


def existing_flags(current: int, anchor: int, relative: tuple[str, ...]) -> int:
    current, anchor = map(u32, (current, anchor))
    if anchor & SF_RESTRICTED and allow_existing_repair(relative):
        return current | SF_RESTRICTED
    return current
