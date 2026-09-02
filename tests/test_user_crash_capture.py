import unittest

from tools.user_crash_capture import capture, read_c_string


class Memory:
    va_bits = 47

    def __init__(self, chunks):
        self.chunks = chunks

    def read(self, address, count):
        if address not in self.chunks:
            raise ValueError("unmapped")
        return self.chunks[address][:count]


class CrashCaptureTests(unittest.TestCase):
    def test_bad_stack_does_not_hide_message(self):
        m = Memory({0x100004000: b"directory failure\0".ljust(64, b"x")})
        out = capture(m, {"x0": 0x100004000, "x29": 0x200004000})
        self.assertEqual(out["strings"]["x0"], b"directory failure")
        self.assertIn("frames", out["errors"])

    def test_bad_argument_does_not_hide_other_arguments(self):
        m = Memory({0x100004000: b"message\0".ljust(64, b"x")})
        out = capture(m, {"x0": 0x200004000, "x1": 0x100004000})
        self.assertEqual(out["strings"]["x1"], b"message")
        self.assertIn("x0", out["errors"])

    def test_string_stops_before_unmapped_next_page(self):
        m = Memory({0x100003ffc: b"end\0"})
        self.assertEqual(read_c_string(m, 0x100003ffc), b"end")

    def test_string_crosses_page_and_is_bounded(self):
        m = Memory({0x100003ffc: b"abcd", 0x100004000: b"efgh"})
        self.assertEqual(read_c_string(m, 0x100003ffc, 8), b"abcdefgh")
        for limit in (0, -1, 4097):
            with self.assertRaises(ValueError):
                read_c_string(m, 0x100003ffc, limit)

    def test_short_read_and_small_pointer(self):
        with self.assertRaises(ValueError):
            read_c_string(Memory({0x100004000: b"x"}), 0x100004000)
        self.assertEqual(capture(Memory({}), {"x0": 1})["strings"], {})
