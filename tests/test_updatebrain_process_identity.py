import unittest

from tools.updatebrain_null_cleanup import (
    PROCESS, EXECUTABLE_UUID, PROC_COMM_OFFSET, PROC_NAME_OFFSET,
    PROC_UUID_OFFSET, is_updatebrain_proc,
)


class ProcessIdentityTests(unittest.TestCase):
    def setUp(self):
        self.proc = 0xFFFFFE28D5800000
        self.data = {
            (self.proc + PROC_COMM_OFFSET, 17): PROCESS.encode()[:16] + b'\0',
            (self.proc + PROC_NAME_OFFSET, 33): PROCESS.encode()[:32] + b'\0',
            (self.proc + PROC_UUID_OFFSET, 16): EXECUTABLE_UUID,
        }
        self.calls = []

    def read(self, address, size):
        self.calls.append((address, size))
        return self.data[address, size]

    def test_real_kernel_truncation_that_old_full_name_comparison_rejected(self):
        self.assertEqual(len(PROCESS), 49)
        self.assertNotEqual(self.data[self.proc + PROC_NAME_OFFSET, 33][:-1].decode(), PROCESS)
        before = self.data.copy()
        self.assertTrue(is_updatebrain_proc(self.read, self.proc))
        self.assertEqual(self.data, before)
        self.assertEqual(self.calls, list(self.data))

    def test_same_truncated_names_with_different_executable_rejected(self):
        self.data[self.proc + PROC_UUID_OFFSET, 16] = bytes(16)
        self.assertFalse(is_updatebrain_proc(self.read, self.proc))

    def test_every_uuid_byte_is_required(self):
        for i in range(16):
            wrong = bytearray(EXECUTABLE_UUID)
            wrong[i] ^= 1
            self.data[self.proc + PROC_UUID_OFFSET, 16] = bytes(wrong)
            with self.subTest(i=i):
                self.assertFalse(is_updatebrain_proc(self.read, self.proc))

    def test_each_name_field_requires_exact_bounded_value(self):
        for offset, size in ((PROC_COMM_OFFSET, 17), (PROC_NAME_OFFSET, 33)):
            key = self.proc + offset, size
            original = self.data[key]
            for wrong in (b'', original[:-1], original[:-1] + b'X', b'X' + original[1:]):
                self.data[key] = wrong
                with self.subTest(offset=offset, wrong=wrong):
                    self.assertFalse(is_updatebrain_proc(self.read, self.proc))
            self.data[key] = original

    def test_unrelated_command_does_not_read_other_fields(self):
        self.data[self.proc + PROC_COMM_OFFSET, 17] = b'other\0' + bytes(11)
        self.assertFalse(is_updatebrain_proc(self.read, self.proc))
        self.assertEqual(self.calls, [(self.proc + PROC_COMM_OFFSET, 17)])

    def test_invalid_pointer_refuses_before_reads(self):
        for p in (None, True, 0, -1, 0x100000000, self.proc + 1, 0xFFFFFFFFFFFFFFFF):
            with self.subTest(p=p), self.assertRaises(ValueError):
                is_updatebrain_proc(self.read, p)
        self.assertEqual(self.calls, [])

    def test_unreadable_uuid_refuses(self):
        del self.data[self.proc + PROC_UUID_OFFSET, 16]
        with self.assertRaises(KeyError):
            is_updatebrain_proc(self.read, self.proc)
