import struct
import unittest

from tools.updatebrain_null_cleanup import (
    PROCESS, CF_BASE, CF_UUID, UB_UUID, CF_NULL, CF_RETURN, CALLER_RETURN,
    CF_WORDS, UB_WORDS, plan_cleanup, verify_uuid,
)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.data = {}
        self.base = 0x100D80000
        self.sp = 0x16F012000
        self.lr = self.base + CALLER_RETURN | 0x91AF800000000000
        self.state = dict(process=PROCESS, pc=CF_NULL, x0=0, sp=self.sp,
                          fp=self.sp, lr=self.lr)
        self.put(self.sp, struct.pack('<QQ', self.sp + 0x50, self.lr))
        self.put(self.sp + 0x28, bytes(8))
        for base, uuid, words in ((CF_BASE, CF_UUID, CF_WORDS),
                                  (self.base, UB_UUID, UB_WORDS)):
            self.put(base, self.header(uuid))
            for off, word in words.items():
                self.put(base + off, struct.pack('<I', word))

    @staticmethod
    def header(uuid):
        return struct.pack('<8I', 0xFEEDFACF, 0x100000C, 2, 6, 1, 24, 0, 0) + struct.pack('<II', 0x1B, 24) + uuid

    def put(self, address, data):
        self.data.update({address + i: b for i, b in enumerate(data)})

    def read(self, address, size):
        return bytes(self.data[address + i] for i in range(size))

    def plan(self, **changes):
        return plan_cleanup(self.read, **(self.state | changes))

    def test_exact_null_cleanup_uses_authenticated_epilogue(self):
        before = self.data.copy()
        self.assertEqual(self.plan(), CF_RETURN)
        self.assertEqual(self.data, before)
        self.assertEqual(self.state['lr'], self.lr)

    def test_non_null_release_is_never_changed_or_inspected(self):
        for value in (1, 0x100004000, (1 << 64) - 1):
            self.assertIsNone(plan_cleanup(lambda *a: self.fail('unexpected read'),
                                          **(self.state | {'x0': value})))

    def test_other_processes_are_untouched(self):
        for process in ('', 'softwareupdated', 'UpdateBrainService', PROCESS + '2'):
            self.assertIsNone(self.plan(process=process))

    def test_other_cf_release_sites_are_untouched(self):
        for pc in (0, CF_NULL - 4, CF_NULL + 4, CF_RETURN):
            self.assertIsNone(self.plan(pc=pc))

    def test_stack_alignment_and_bounds(self):
        for sp in (0, -16, self.sp + 1, 1 << 47):
            with self.subTest(sp=sp), self.assertRaises(ValueError):
                self.plan(sp=sp)

    def test_frame_pointer_must_match_prologue(self):
        with self.assertRaises(ValueError): self.plan(fp=self.sp + 16)

    def test_saved_caller_frame_must_match(self):
        self.put(self.sp, struct.pack('<Q', self.sp + 0x40))
        with self.assertRaises(ValueError): self.plan()

    def test_signed_lr_is_compared_without_replacing_it(self):
        with self.assertRaises(ValueError): self.plan(lr=self.lr ^ (1 << 60))

    def test_other_cleanup_callers_rejected(self):
        for offset in (0x514EC, 0x514F4, 0x51500, 0x12345):
            lr = self.base + offset
            self.put(self.sp + 8, struct.pack('<Q', lr))
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.plan(lr=lr)

    def test_different_aslr_base_accepted_only_with_matching_live_image(self):
        delta = 0xC000
        for address, value in list(self.data.items()):
            if self.base <= address < self.base + 0x60000:
                self.data[address + delta] = value
        lr = self.lr + delta
        self.put(self.sp + 8, struct.pack('<Q', lr))
        self.assertEqual(self.plan(lr=lr), CF_RETURN)

    def test_non_null_ticket_local_rejected(self):
        self.put(self.sp + 0x28, struct.pack('<Q', 0x12340000))
        with self.assertRaises(ValueError): self.plan()

    def test_wrong_caller_uuid_rejected(self):
        self.put(self.base + 40, bytes(16))
        with self.assertRaises(ValueError): self.plan()

    def test_wrong_cf_uuid_rejected(self):
        self.put(CF_BASE + 40, bytes(16))
        with self.assertRaises(ValueError): self.plan()

    def test_each_checked_instruction_is_required(self):
        for base, words in ((CF_BASE, CF_WORDS), (self.base, UB_WORDS)):
            for off in words:
                address = base + off
                previous = self.data[address]
                self.data[address] ^= 1
                with self.subTest(base=base, offset=off), self.assertRaises(ValueError):
                    self.plan()
                self.data[address] = previous

    def test_wrong_machine_or_subtype_rejected(self):
        for off, value in ((0, 0), (4, 0x1000007), (8, 0)):
            original = self.read(self.base + off, 4)
            self.put(self.base + off, struct.pack('<I', value))
            with self.assertRaises(ValueError): self.plan()
            self.put(self.base + off, original)

    def test_bad_command_bounds(self):
        for count, size in ((0, 24), (257, 24), (1, 0), (1, 32776)):
            self.put(self.base + 16, struct.pack('<II', count, size))
            with self.subTest(count=count, size=size), self.assertRaises(ValueError): self.plan()

    def test_bad_uuid_command_extents(self):
        for size in (0, 7, 16, 32):
            self.put(self.base + 36, struct.pack('<I', size))
            with self.subTest(size=size), self.assertRaises(ValueError): self.plan()

    def test_duplicate_uuid_rejected(self):
        self.put(self.base + 16, struct.pack('<II', 2, 48))
        self.put(self.base + 56, struct.pack('<II', 0x1B, 24) + UB_UUID)
        with self.assertRaises(ValueError): self.plan()

    def test_unreadable_memory_refuses_instead_of_guessing(self):
        del self.data[self.base + 1]
        with self.assertRaises(KeyError): self.plan()


if __name__ == '__main__':
    unittest.main()
