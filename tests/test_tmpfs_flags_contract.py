import unittest

from tools.tmpfs_flags_contract import (
    ANCHOR, EXISTING_BUNDLE, SF_RESTRICTED as R, VA_FLAGS_ACTIVE as A, WORDS,
    creation_flags, existing_flags, relative_components, verify_instructions,
    extended_flags_response, new_child_path, VA_EXTFLAGS_ACTIVE as E,
)


class TmpfsFlagsContractTests(unittest.TestCase):
    def test_exact_instruction_contract(self):
        slide = 0x19344000
        verify_instructions(lambda p: WORDS[p - slide], slide)

    def test_every_instruction_is_required(self):
        for bad in WORDS:
            with self.subTest(bad=hex(bad)), self.assertRaises(ValueError):
                verify_instructions(lambda p: WORDS[p] ^ (p == bad), 0)

    def test_bad_slides(self):
        for slide in (-1, 1, 0x40004000, True, "0"):
            with self.subTest(slide=slide), self.assertRaises(ValueError):
                verify_instructions(lambda p: 0, slide)

    def test_unreadable_code_fails_closed(self):
        def unreadable(_):
            raise OSError("unmapped")
        with self.assertRaises(OSError):
            verify_instructions(unreadable, 0)

    def test_anchor_and_reversed_components(self):
        self.assertEqual(relative_components(("bin", EXISTING_BUNDLE, "exec") + ANCHOR),
                         ("exec", EXISTING_BUNDLE, "bin"))
        self.assertEqual(relative_components(ANCHOR), ())

    def test_lookalike_and_unsafe_paths_are_rejected(self):
        for path in (("exec", ANCHOR[0], "db", "tmp", "private"),
                     ("exec", ANCHOR[0], "db", "var"), ("..",) + ANCHOR,
                     ("a/b",) + ANCHOR, ("x\0",) + ANCHOR,
                     ("",) + ANCHOR, ("x" * 256,) + ANCHOR,
                     ("x",) * 29 + ANCHOR):
            with self.subTest(path=path):
                self.assertIsNone(relative_components(path))

    def test_new_flag_requires_both_request_and_protected_parent(self):
        for active in (0, A):
            for requested in (0, R):
                for parent in (0, R):
                    with self.subTest(active=active, requested=requested, parent=parent):
                        expected = R if active and requested and parent else 0
                        self.assertEqual(creation_flags(0, requested, active, parent), expected)

    def test_unrelated_bits_preserved_never_cleared(self):
        for current in (0, 1, 0x100000, 0xFFFFFFFF, R):
            self.assertEqual(creation_flags(current, R, A, R), current | R)
            self.assertEqual(creation_flags(current, 0, A, R), current)
            self.assertEqual(creation_flags(current, R, 0, R), current)

    def test_existing_only_known_staging_directories_and_bundle(self):
        for path in (("exec",), ("tmp",), ("exec", EXISTING_BUNDLE),
                     ("exec", EXISTING_BUNDLE, "Contents", "MacOS", "brain")):
            self.assertEqual(existing_flags(1, R, path), 1 | R)
            self.assertEqual(existing_flags(1, 0, path), 1)

    def test_existing_unknown_payloads_and_probe_are_not_relabelled(self):
        for path in ((), ("other",), ("exec", "unknown.xpc"),
                     ("exec", "macvm-flags-probe.GpA0fm"),
                     ("tmp", EXISTING_BUNDLE), ("exec-backup", EXISTING_BUNDLE)):
            self.assertEqual(existing_flags(1, R, path), 1)

    def test_negative_overflow_and_wrong_type_flags_fail(self):
        for bad in (-1, 2**32, True, "1", None):
            for index in (0, 1, 3):
                args = [0, R, A, R]
                args[index] = bad
                with self.subTest(bad=bad, index=index), self.assertRaises(ValueError):
                    creation_flags(*args)
        for bad in (-1, 2**64, True, None):
            with self.assertRaises(ValueError):
                creation_flags(0, R, bad, R)

    def test_new_path_uses_named_parent_not_uncached_child(self):
        self.assertEqual(new_child_path(("tmp",), "new.xpc"), ("tmp", "new.xpc"))
        self.assertEqual(new_child_path(("exec", "new.xpc", "Contents"), "Info.plist"),
                         ("exec", "new.xpc", "Contents", "Info.plist"))

    def test_new_path_rejects_anchor_sibling_and_unsafe_components(self):
        for parent in ((), ("other",), ("exec-backup",), ("tmp", ".."), ["tmp"]):
            self.assertIsNone(new_child_path(parent, "leaf"))
        for name in ("", ".", "..", "a/b", "x\0", "x" * 256, None):
            self.assertIsNone(new_child_path(("tmp",), name))
        self.assertIsNone(new_child_path(("tmp",) + ("x",) * 27, "leaf"))

    def test_only_requested_absent_extflags_are_synthesized(self):
        for supported in (0, 0x1600450, E, E | A, 2**64 - 1):
            for requested in (0, A, E, E | A, 2**64 - 1):
                for value in (0, 32, 2**64 - 1):
                    with self.subTest(supported=supported, requested=requested, value=value):
                        expected = (supported | E, 0) if requested & E and not supported & E else (supported, value)
                        self.assertEqual(extended_flags_response(supported, requested, value), expected)

    def test_extflags_correction_is_idempotent(self):
        supported, value = extended_flags_response(0x1600450, E | A, 0xDEADBEEF)
        self.assertEqual(extended_flags_response(supported, E | A, value), (supported, value))
        self.assertEqual(supported ^ 0x1600450, E)

    def test_extflags_invalid_inputs_fail_closed(self):
        for bad in (-1, 2**64, True, "1", None):
            for index in range(3):
                args = [0, E, 0]
                args[index] = bad
                with self.subTest(index=index, bad=bad), self.assertRaises(ValueError):
                    extended_flags_response(*args)


if __name__ == "__main__":
    unittest.main()
