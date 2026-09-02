import struct
import unittest
from tools.symbolize_user_stacks import A2S


def fixture():
    return b'A2S\x02' + struct.pack('<II', 2, 8) + struct.pack('<QIQI', 0x1000, 0, 0x2000, 4) + b'one\0two\0'


class A2STests(unittest.TestCase):
    def test_exact_and_floor_lookup(self):
        table = A2S(fixture())
        self.assertEqual(table.nearest(0x1000), (0x1000, 'one', 0))
        self.assertEqual(table.nearest(0x1ffc), (0x1000, 'one', 0xffc))
        self.assertEqual(table.nearest(0x2004), (0x2000, 'two', 4))

    def test_missing_or_distant_address(self):
        table = A2S(fixture())
        self.assertIsNone(table.nearest(0xfff))
        self.assertIsNone(table.nearest(0x2005, 4))
        self.assertIsNone(A2S(b'A2S\x02' + bytes(8)).nearest(123))

    def test_invalid_extents_and_magic(self):
        for data in (b'', fixture()[:11], b'xxx\x02' + fixture()[4:], fixture()[:-1], fixture() + b'X'):
            with self.assertRaises(ValueError):
                A2S(data)

    def test_invalid_string_offset_and_terminator(self):
        data = bytearray(fixture())
        struct.pack_into('<I', data, 20, 8)
        with self.assertRaises(ValueError):
            A2S(data).nearest(0x1000)
        data = fixture()[:-1] + b'X'
        with self.assertRaises(ValueError):
            A2S(data).nearest(0x2000)

    def test_invalid_lookup_bounds(self):
        table = A2S(fixture())
        for address, distance in ((-1, 1), (1, -1)):
            with self.assertRaises(ValueError):
                table.nearest(address, distance)
