from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from xnu_imgsrc_state import (  # noqa: E402
    MNTK_BACKS_ROOT,
    MNT_ROOTFS,
    MOUNT_FLAGS_OFFSET,
    MOUNT_KERN_FLAGS_OFFSET,
    MOUNT_LIST_NEXT_OFFSET,
    MOUNT_LIST_PREV_OFFSET,
    VNODE_USECOUNT_MAX,
    VNODE_USECOUNT_OFFSET,
    XnuImgsrcStateError,
    commit_imgsrc_transfer,
    retain_outgoing_root,
    rollback_retained_root,
)


KBASE = 0xFFFFFE0000000000
OLD_VNODE = KBASE + 0x10000
NEW_VNODE = KBASE + 0x20000
OLD_MOUNT = KBASE + 0x30000
NEXT_MOUNT = KBASE + 0x40000
PREV_NEXT_SLOT = KBASE + 0x50000
MOUNTLIST_TAIL = KBASE + 0x60000
IMGSRC = KBASE + 0x70000
NUMMOUNTS = KBASE + 0x80000


class FakeMemory:
    def __init__(self) -> None:
        self.values: dict[tuple[int, int], int] = {}

    def read_u32(self, address: int) -> int:
        return self.values.get((address, 4), 0)

    def read_u64(self, address: int) -> int:
        return self.values.get((address, 8), 0)

    def write_u32(self, address: int, value: int) -> None:
        self.values[(address, 4)] = value & 0xFFFFFFFF

    def write_u64(self, address: int, value: int) -> None:
        self.values[(address, 8)] = value & 0xFFFFFFFFFFFFFFFF

    def snapshot(self) -> dict[tuple[int, int], int]:
        return deepcopy(self.values)


def linked_memory(*, tail: bool = False) -> FakeMemory:
    memory = FakeMemory()
    memory.write_u32(OLD_VNODE + VNODE_USECOUNT_OFFSET, 3)
    memory.write_u64(IMGSRC, 0)
    memory.write_u64(OLD_MOUNT + MOUNT_LIST_NEXT_OFFSET, 0 if tail else NEXT_MOUNT)
    memory.write_u64(OLD_MOUNT + MOUNT_LIST_PREV_OFFSET, PREV_NEXT_SLOT)
    memory.write_u64(PREV_NEXT_SLOT, OLD_MOUNT)
    memory.write_u64(MOUNTLIST_TAIL, OLD_MOUNT if tail else NEXT_MOUNT)
    if not tail:
        memory.write_u64(NEXT_MOUNT + MOUNT_LIST_PREV_OFFSET, OLD_MOUNT)
    memory.write_u32(OLD_MOUNT + MOUNT_FLAGS_OFFSET, 0x81)
    memory.write_u32(OLD_MOUNT + MOUNT_KERN_FLAGS_OFFSET, 0x200)
    memory.write_u32(NUMMOUNTS, 7)
    return memory


class XnuImgsrcStateTests(unittest.TestCase):
    def retain(self, memory: FakeMemory):
        return retain_outgoing_root(
            memory,
            old_root_vnode=OLD_VNODE,
            outgoing_mount=OLD_MOUNT,
            imgsrc_rootvnode=IMGSRC,
            mountlist_tail=MOUNTLIST_TAIL,
        )

    def commit(self, memory: FakeMemory, retained):
        return commit_imgsrc_transfer(
            memory,
            retained=retained,
            current_root_vnode=NEW_VNODE,
            imgsrc_rootvnode=IMGSRC,
            mountlist_tail=MOUNTLIST_TAIL,
            mount_count=NUMMOUNTS,
        )

    def test_middle_mount_transition_matches_xnu_contract(self) -> None:
        memory = linked_memory()
        retained = self.retain(memory)
        result = self.commit(memory, retained)

        self.assertEqual(memory.read_u32(OLD_VNODE + VNODE_USECOUNT_OFFSET), 4)
        self.assertEqual(memory.read_u64(PREV_NEXT_SLOT), NEXT_MOUNT)
        self.assertEqual(memory.read_u64(NEXT_MOUNT + MOUNT_LIST_PREV_OFFSET), PREV_NEXT_SLOT)
        self.assertEqual(memory.read_u64(OLD_MOUNT), 0)
        self.assertEqual(memory.read_u64(OLD_MOUNT + 8), 0)
        self.assertEqual(memory.read_u32(NUMMOUNTS), 6)
        self.assertEqual(memory.read_u64(IMGSRC), OLD_VNODE)
        self.assertTrue(memory.read_u32(OLD_MOUNT + MOUNT_KERN_FLAGS_OFFSET) & MNTK_BACKS_ROOT)
        self.assertFalse(memory.read_u32(OLD_MOUNT + MOUNT_FLAGS_OFFSET) & MNT_ROOTFS)
        self.assertEqual(result.old_mount_count, 7)

    def test_tail_mount_updates_tail_pointer(self) -> None:
        memory = linked_memory(tail=True)
        retained = self.retain(memory)
        self.commit(memory, retained)
        self.assertEqual(memory.read_u64(MOUNTLIST_TAIL), PREV_NEXT_SLOT)
        self.assertEqual(memory.read_u64(PREV_NEXT_SLOT), 0)

    def test_retain_can_be_rolled_back_before_commit(self) -> None:
        memory = linked_memory()
        retained = self.retain(memory)
        rollback_retained_root(memory, retained)
        self.assertEqual(memory.read_u32(OLD_VNODE + VNODE_USECOUNT_OFFSET), 3)

    def test_retain_refuses_an_existing_imgsrc_owner_without_writes(self) -> None:
        memory = linked_memory()
        memory.write_u64(IMGSRC, NEW_VNODE)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "already populated"):
            self.retain(memory)
        self.assertEqual(memory.snapshot(), before)

    def test_retain_refuses_zero_and_saturated_usecounts(self) -> None:
        for value in (0, VNODE_USECOUNT_MAX):
            with self.subTest(value=value):
                memory = linked_memory()
                memory.write_u32(OLD_VNODE + VNODE_USECOUNT_OFFSET, value)
                before = memory.snapshot()
                with self.assertRaises(XnuImgsrcStateError):
                    self.retain(memory)
                self.assertEqual(memory.snapshot(), before)

    def test_retain_refuses_noncanonical_or_unaligned_pointers(self) -> None:
        memory = linked_memory()
        for bad in (0, 0x1234, OLD_VNODE + 1):
            with self.subTest(bad=bad):
                before = memory.snapshot()
                with self.assertRaises(XnuImgsrcStateError):
                    retain_outgoing_root(
                        memory,
                        old_root_vnode=bad,
                        outgoing_mount=OLD_MOUNT,
                        imgsrc_rootvnode=IMGSRC,
                        mountlist_tail=MOUNTLIST_TAIL,
                    )
                self.assertEqual(memory.snapshot(), before)

    def test_retain_refuses_broken_predecessor_link_without_writes(self) -> None:
        memory = linked_memory()
        memory.write_u64(PREV_NEXT_SLOT, NEXT_MOUNT)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "previous link"):
            self.retain(memory)
        self.assertEqual(memory.snapshot(), before)

    def test_retain_refuses_broken_successor_link_without_writes(self) -> None:
        memory = linked_memory()
        memory.write_u64(NEXT_MOUNT + MOUNT_LIST_PREV_OFFSET, PREV_NEXT_SLOT)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "next link"):
            self.retain(memory)
        self.assertEqual(memory.snapshot(), before)

    def test_tail_requires_mountlist_tail_to_name_the_mount(self) -> None:
        memory = linked_memory(tail=True)
        memory.write_u64(MOUNTLIST_TAIL, PREV_NEXT_SLOT)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "tail disagrees"):
            self.retain(memory)
        self.assertEqual(memory.snapshot(), before)

    def test_commit_refuses_if_root_did_not_switch_and_preserves_list(self) -> None:
        memory = linked_memory()
        retained = self.retain(memory)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "did not change"):
            commit_imgsrc_transfer(
                memory,
                retained=retained,
                current_root_vnode=OLD_VNODE,
                imgsrc_rootvnode=IMGSRC,
                mountlist_tail=MOUNTLIST_TAIL,
                mount_count=NUMMOUNTS,
            )
        self.assertEqual(memory.snapshot(), before)

    def test_commit_refuses_if_imgsrc_changed_and_preserves_list(self) -> None:
        memory = linked_memory()
        retained = self.retain(memory)
        memory.write_u64(IMGSRC, NEW_VNODE)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "changed before commit"):
            self.commit(memory, retained)
        self.assertEqual(memory.snapshot(), before)

    def test_commit_refuses_if_retain_was_lost_and_preserves_list(self) -> None:
        memory = linked_memory()
        retained = self.retain(memory)
        memory.write_u32(OLD_VNODE + VNODE_USECOUNT_OFFSET, 3)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "retain was not preserved"):
            self.commit(memory, retained)
        self.assertEqual(memory.snapshot(), before)

    def test_commit_refuses_rootfs_flag_and_preserves_list(self) -> None:
        memory = linked_memory()
        retained = self.retain(memory)
        memory.write_u32(OLD_MOUNT + MOUNT_FLAGS_OFFSET, MNT_ROOTFS | 0x81)
        before = memory.snapshot()
        with self.assertRaisesRegex(XnuImgsrcStateError, "still carries MNT_ROOTFS"):
            self.commit(memory, retained)
        self.assertEqual(memory.snapshot(), before)

    def test_commit_refuses_invalid_mount_count_and_preserves_list(self) -> None:
        for count in (0, 1_000_001):
            with self.subTest(count=count):
                memory = linked_memory()
                retained = self.retain(memory)
                memory.write_u32(NUMMOUNTS, count)
                before = memory.snapshot()
                with self.assertRaisesRegex(XnuImgsrcStateError, "nummounts"):
                    self.commit(memory, retained)
                self.assertEqual(memory.snapshot(), before)

    def test_rollback_refuses_a_changed_usecount(self) -> None:
        memory = linked_memory()
        retained = self.retain(memory)
        memory.write_u32(OLD_VNODE + VNODE_USECOUNT_OFFSET, 5)
        with self.assertRaisesRegex(XnuImgsrcStateError, "changed before rollback"):
            rollback_retained_root(memory, retained)


if __name__ == "__main__":
    unittest.main()
