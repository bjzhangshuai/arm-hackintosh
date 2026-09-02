#!/usr/bin/env python3
"""Validated one-shot state transfer for XNU's signed BaseSystem pivot.

Apple's arm64 recovery path authenticates the BaseSystem APFS volume through
``imageboot_pivot_image()``, but that function deliberately omits the image
source bookkeeping performed by ``imageboot_mount_image()``.  Recovery's
``mountrecursive`` later requires that bookkeeping through ``kern.imgsrcinfo``.

This module models the exact missing transition against a small typed memory
interface so the safety checks can be unit tested outside GDB.  The live GDB
script uses it only while QEMU's all-stop debugger has every virtual CPU
paused.  No pointer-only shortcut is permitted: the outgoing mount must be
unlinked, its root marker changed, and its retained vnode published as one
validated transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


MOUNT_LIST_NEXT_OFFSET = 0x00
MOUNT_LIST_PREV_OFFSET = 0x08
MOUNT_FLAGS_OFFSET = 0x70
MOUNT_KERN_FLAGS_OFFSET = 0x74
VNODE_USECOUNT_OFFSET = 0xB4

MNT_ROOTFS = 0x00004000
MNTK_BACKS_ROOT = 0x00004000
VNODE_USECOUNT_MAX = 0x7FFFFFFF


class XnuImgsrcStateError(ValueError):
    """The reviewed XNU layout or a live invariant did not match."""


class Memory32x64(Protocol):
    def read_u32(self, address: int) -> int: ...

    def read_u64(self, address: int) -> int: ...

    def write_u32(self, address: int, value: int) -> None: ...

    def write_u64(self, address: int, value: int) -> None: ...


@dataclass(frozen=True)
class RetainedRoot:
    vnode: int
    mount: int
    original_usecount: int


@dataclass(frozen=True)
class ImgsrcCommit:
    vnode: int
    mount: int
    next_mount: int
    previous_next_slot: int
    old_mount_count: int


def _require_kernel_pointer(value: int, name: str) -> None:
    # The macOS 26.6 kernel pointers observed in the reviewed BootKC are in the
    # canonical 0xfffffe00... region.  Requiring this before any write prevents
    # a stale register or an unslid static address from becoming a write target.
    if value < 0xFFFFFE0000000000 or value > 0xFFFFFFFFFFFFFFF8:
        raise XnuImgsrcStateError(f"{name} is not a canonical XNU kernel pointer")
    if value & 0x7:
        raise XnuImgsrcStateError(f"{name} is not 8-byte aligned")


def _validate_linkage(memory: Memory32x64, mount: int, mountlist_tail: int) -> tuple[int, int]:
    next_mount = memory.read_u64(mount + MOUNT_LIST_NEXT_OFFSET)
    previous_next_slot = memory.read_u64(mount + MOUNT_LIST_PREV_OFFSET)
    _require_kernel_pointer(previous_next_slot, "mount previous-next slot")
    if memory.read_u64(previous_next_slot) != mount:
        raise XnuImgsrcStateError("mount previous link does not point back to the mount")

    if next_mount:
        _require_kernel_pointer(next_mount, "mount next")
        if memory.read_u64(next_mount + MOUNT_LIST_PREV_OFFSET) != mount:
            raise XnuImgsrcStateError("mount next link does not point back to the mount")
    elif memory.read_u64(mountlist_tail) != mount:
        # mnt_list is the first field of struct mount, so &mnt_list.tqe_next is
        # numerically the mount pointer itself for the tail element.
        raise XnuImgsrcStateError("mount is a tail element but mountlist tail disagrees")

    return next_mount, previous_next_slot


def retain_outgoing_root(
    memory: Memory32x64,
    *,
    old_root_vnode: int,
    outgoing_mount: int,
    imgsrc_rootvnode: int,
    mountlist_tail: int,
) -> RetainedRoot:
    """Retain the rootvnode reference that ``set_rootvnode`` will release.

    All validation happens before the single write.  The caller must invoke
    :func:`rollback_retained_root` if the later pivot fails or commit validation
    refuses the live state.
    """

    _require_kernel_pointer(old_root_vnode, "outgoing root vnode")
    _require_kernel_pointer(outgoing_mount, "outgoing mount")
    _require_kernel_pointer(imgsrc_rootvnode, "imgsrc_rootvnodes[0]")
    _require_kernel_pointer(mountlist_tail, "mountlist tail")
    if memory.read_u64(imgsrc_rootvnode) != 0:
        raise XnuImgsrcStateError("imgsrc_rootvnodes[0] is already populated")
    _validate_linkage(memory, outgoing_mount, mountlist_tail)

    usecount_address = old_root_vnode + VNODE_USECOUNT_OFFSET
    usecount = memory.read_u32(usecount_address)
    if usecount == 0:
        raise XnuImgsrcStateError("outgoing root vnode has no usecount to retain")
    if usecount >= VNODE_USECOUNT_MAX:
        raise XnuImgsrcStateError("outgoing root vnode usecount cannot be incremented")

    memory.write_u32(usecount_address, usecount + 1)
    if memory.read_u32(usecount_address) != usecount + 1:
        raise XnuImgsrcStateError("outgoing root vnode retain did not persist")
    return RetainedRoot(old_root_vnode, outgoing_mount, usecount)


def rollback_retained_root(memory: Memory32x64, retained: RetainedRoot) -> None:
    """Undo only the pre-pivot retain; never repairs a partly committed list."""

    current = memory.read_u32(retained.vnode + VNODE_USECOUNT_OFFSET)
    if current != retained.original_usecount + 1:
        raise XnuImgsrcStateError("retained vnode usecount changed before rollback")
    memory.write_u32(retained.vnode + VNODE_USECOUNT_OFFSET, retained.original_usecount)


def commit_imgsrc_transfer(
    memory: Memory32x64,
    *,
    retained: RetainedRoot,
    current_root_vnode: int,
    imgsrc_rootvnode: int,
    mountlist_tail: int,
    mount_count: int,
) -> ImgsrcCommit:
    """Atomically model ``imageboot_mount_image``'s missing post-pivot state.

    The live caller runs under QEMU's all-stop debugger, so the validated write
    group cannot race another vCPU.  Every precondition is checked before the
    first list write.  Once the list is changed, failures are treated as fatal;
    the function verifies every resulting invariant before returning.
    """

    _require_kernel_pointer(current_root_vnode, "current root vnode")
    _require_kernel_pointer(imgsrc_rootvnode, "imgsrc_rootvnodes[0]")
    _require_kernel_pointer(mount_count, "nummounts")
    if current_root_vnode == retained.vnode:
        raise XnuImgsrcStateError("rootvnode did not change across the pivot")
    if memory.read_u64(imgsrc_rootvnode) != 0:
        raise XnuImgsrcStateError("imgsrc_rootvnodes[0] changed before commit")
    if memory.read_u32(retained.vnode + VNODE_USECOUNT_OFFSET) != retained.original_usecount + 1:
        raise XnuImgsrcStateError("outgoing root vnode retain was not preserved")

    next_mount, previous_next_slot = _validate_linkage(
        memory, retained.mount, mountlist_tail
    )
    old_mount_count = memory.read_u32(mount_count)
    if old_mount_count == 0 or old_mount_count > 1_000_000:
        raise XnuImgsrcStateError("nummounts is outside the reviewed range")
    mount_flags = memory.read_u32(retained.mount + MOUNT_FLAGS_OFFSET)
    if mount_flags & MNT_ROOTFS:
        raise XnuImgsrcStateError("outgoing mount still carries MNT_ROOTFS after pivot")

    # Match XNU mount_list_remove(): repair the successor/tail first, then the
    # predecessor, decrement the count, and poison neither link with a partial
    # pointer.  Only after the mount is detached do we publish imgsrc_rootvnodes.
    if next_mount:
        memory.write_u64(next_mount + MOUNT_LIST_PREV_OFFSET, previous_next_slot)
    else:
        memory.write_u64(mountlist_tail, previous_next_slot)
    memory.write_u64(previous_next_slot, next_mount)
    memory.write_u32(mount_count, old_mount_count - 1)
    memory.write_u64(retained.mount + MOUNT_LIST_NEXT_OFFSET, 0)
    memory.write_u64(retained.mount + MOUNT_LIST_PREV_OFFSET, 0)
    memory.write_u32(
        retained.mount + MOUNT_KERN_FLAGS_OFFSET,
        memory.read_u32(retained.mount + MOUNT_KERN_FLAGS_OFFSET) | MNTK_BACKS_ROOT,
    )
    memory.write_u32(
        retained.mount + MOUNT_FLAGS_OFFSET,
        mount_flags & ~MNT_ROOTFS,
    )
    memory.write_u64(imgsrc_rootvnode, retained.vnode)

    if memory.read_u64(retained.mount + MOUNT_LIST_NEXT_OFFSET) != 0:
        raise XnuImgsrcStateError("outgoing mount next link was not cleared")
    if memory.read_u64(retained.mount + MOUNT_LIST_PREV_OFFSET) != 0:
        raise XnuImgsrcStateError("outgoing mount previous link was not cleared")
    if memory.read_u32(mount_count) != old_mount_count - 1:
        raise XnuImgsrcStateError("nummounts decrement did not persist")
    if not memory.read_u32(retained.mount + MOUNT_KERN_FLAGS_OFFSET) & MNTK_BACKS_ROOT:
        raise XnuImgsrcStateError("MNTK_BACKS_ROOT did not persist")
    if memory.read_u32(retained.mount + MOUNT_FLAGS_OFFSET) & MNT_ROOTFS:
        raise XnuImgsrcStateError("MNT_ROOTFS was not cleared")
    if memory.read_u64(imgsrc_rootvnode) != retained.vnode:
        raise XnuImgsrcStateError("imgsrc_rootvnodes[0] publication did not persist")

    return ImgsrcCommit(
        vnode=retained.vnode,
        mount=retained.mount,
        next_mount=next_mount,
        previous_next_slot=previous_next_slot,
        old_mount_count=old_mount_count,
    )
