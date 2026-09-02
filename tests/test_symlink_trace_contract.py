from __future__ import annotations

import unittest

from tools.symlink_trace_contract import (
    CALL_RETURNS, COMMON_RESULT, bl_target, is_completed_symlink,
    same_transaction, verify_instructions,
    may_detach_after_result,
)


class SymlinkInstructionContractTests(unittest.TestCase):
    def setUp(self):
        self.slide = 0x19344000
        # Instruction words independently captured from the 25G72 BootKC.
        self.words = {
            0xFFFFFE0009E911D0: 0x9419DF0E,
            0xFFFFFE0009E911D4: 0x35000E40,
            0xFFFFFE0009E911F4: 0x97FFBCE8,
            0xFFFFFE0009E911F8: 0x34000100,
            0xFFFFFE0009E9122C: 0x97FFB3EC,
            0xFFFFFE0009E91230: 0xAA0003F8,
            0xFFFFFE0009E91268: 0x94009013,
            0xFFFFFE0009E9126C: 0xF94017E3,
            0xFFFFFE0009E913DC: 0xAA1503E0,
            0xFFFFFE0009E913E0: 0xB40001F4,
            0xFFFFFE000A1DF89C: 0x91173001,
        }

    def read(self, address):
        return self.words[address - self.slide]

    def test_reviewed_bootkc_call_chain(self):
        verify_instructions(self.read, self.slide)

    def test_signed_backward_and_forward_bl(self):
        self.assertEqual(bl_target(0x1000, 0x97FFFFFF), 0xFFC)
        self.assertEqual(bl_target(0x1000, 0x94000001), 0x1004)

    def test_non_calls_rejected(self):
        for instruction in (0, 0x14000001, 0xD65F03C0, 0xD503201F):
            with self.subTest(instruction=instruction), self.assertRaises(ValueError):
                bl_target(0x1000, instruction)

    def test_every_call_and_return_is_checked(self):
        for _, ret, _, _ in CALL_RETURNS:
            for address in (ret - 4, ret):
                with self.subTest(address=address):
                    original = self.words[address]
                    self.words[address] ^= 1
                    with self.assertRaises(ValueError):
                        verify_instructions(self.read, self.slide)
                    self.words[address] = original

    def test_final_errno_and_proc_layout_checked(self):
        for address in (COMMON_RESULT - 4, COMMON_RESULT, 0xFFFFFE000A1DF89C):
            with self.subTest(address=address):
                original = self.words[address]
                self.words[address] = 0
                with self.assertRaises(ValueError):
                    verify_instructions(self.read, self.slide)
                self.words[address] = original

    def test_unreadable_memory_is_not_accepted(self):
        def unreadable(_):
            raise OSError("unmapped")
        with self.assertRaises(OSError):
            verify_instructions(unreadable, self.slide)

    def test_transactions_require_both_kernel_objects(self):
        self.assertTrue(same_transaction(0x123, 0x456, 0x123, 0x456))
        for args in ((0, 0, 0, 0), (1, 2, 0, 2), (1, 2, 1, 0), (1, 3, 1, 2), (3, 2, 1, 2)):
            with self.subTest(args=args):
                self.assertFalse(same_transaction(*args))

    def test_intermediate_success_never_completes_transaction(self):
        for marker in ("MACVM_SYMLINK_SYMLINKAT_VNOP_SYMLINK_RETURN",
                       "MACVM_SYMLINK_SYMLINKAT_VNODE_AUTHORIZE_RETURN",
                       "MACVM_SYMLINK_SYMLINKAT_AUTHATTR_RETURN"):
            self.assertFalse(is_completed_symlink(marker, 0, True))

    def test_final_result_must_be_success_and_same_transaction(self):
        marker = "MACVM_SYMLINK_SYMLINKAT_COMMON_RESULT"
        self.assertTrue(is_completed_symlink(marker, 0, True))
        self.assertFalse(is_completed_symlink(marker, 30, True))
        self.assertFalse(is_completed_symlink(marker, 1, True))
        self.assertFalse(is_completed_symlink(marker, 0, False))

    def test_failed_result_can_release_debugger_but_is_not_success(self):
        marker = "MACVM_SYMLINK_SYMLINKAT_COMMON_RESULT"
        self.assertFalse(may_detach_after_result(marker, 30, True))
        self.assertTrue(may_detach_after_result(marker, 30, True, include_failure=True))
        self.assertFalse(is_completed_symlink(marker, 30, True))
        self.assertFalse(may_detach_after_result(marker, 30, False, include_failure=True))
        self.assertFalse(may_detach_after_result("MACVM_SYMLINK_SYMLINKAT_AUTHATTR_RETURN", 0, True, include_failure=True))
