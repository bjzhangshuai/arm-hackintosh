import struct
import unittest

from tools.pvg_memory import PVGMemory


class PVGMemoryTests(unittest.TestCase):
    def fixture(self, shift=14, depth=2):
        data = bytearray(8 << shift)
        struct.pack_into("<II", data, 1 << shift, 2, depth)
        struct.pack_into("<I", data, 2 << shift, 3 | 0x80000000)
        struct.pack_into("<II", data, 3 << shift, 4, 6)
        return data, lambda address, count: bytes(data[address:address + count])

    def test_geometries_and_cross_page(self):
        for shift in (12, 14):
            with self.subTest(shift=shift):
                data, read = self.fixture(shift)
                data[(5 << shift) - 2:5 << shift] = b"ab"
                data[6 << shift:(6 << shift) + 2] = b"cd"
                memory = PVGMemory(read, 1, shift)
                self.assertEqual(memory.translate(23), (4 << shift) + 23)
                self.assertEqual(memory.read((1 << shift) - 2, 4), b"abcd")

    def test_invalid_directory_geometry_depth_and_root(self):
        data, read = self.fixture()
        for directory, shift in ((0, 14), (-1, 14), (0x80000000, 14), (1, 13)):
            with self.assertRaises(ValueError):
                PVGMemory(read, directory, shift)
        for root, depth in ((0, 2), (0x80000000, 2), (2, 0), (2, 5)):
            struct.pack_into("<II", data, 1 << 14, root, depth)
            with self.assertRaises(ValueError):
                PVGMemory(read, 1, 14)

    def test_absent_and_flag_only_pte_are_distinct(self):
        data, read = self.fixture()
        memory = PVGMemory(read, 1, 14)
        for pte, message in ((0, "absent"), (0x80000000, "malformed")):
            struct.pack_into("<I", data, 3 << 14, pte)
            with self.assertRaisesRegex(ValueError, message):
                memory.read(0, 1)

    def test_short_read_and_capture_bounds(self):
        with self.assertRaisesRegex(ValueError, "short"):
            PVGMemory(lambda address, count: b"", 1, 14)
        data, read = self.fixture()
        memory = PVGMemory(read, 1, 14)
        for address, count in ((-1, 1), (1 << 38, 1), (0, -1), (0, 65537), ((1 << 38) - 1, 2)):
            with self.subTest(address=address, count=count), self.assertRaises(ValueError):
                memory.read(address, count)
        self.assertEqual(memory.read(0, 0), b"")
