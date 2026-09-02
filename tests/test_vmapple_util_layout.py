import struct
import unittest

from tools.vmapple_util_layout import REGIONS_25G72, validate_regions, validate_isc_report


class UtilLayoutTests(unittest.TestCase):
    # Independent little-endian fixture captured from Boot112's live DeviceTree.
    RAW = bytes.fromhex('01000000000000000000a000020000000000a00000001000'
                        '030000000000b00000005000070000000000000100100000'
                        '040000000010000100f04f00050000000000500100005000'
                        '060000000000a00100006000')

    def test_captured_layout_and_partition_boundary(self):
        self.assertEqual(validate_regions(self.RAW), REGIONS_25G72)
        self.assertEqual(max(start + size for _, start, size in REGIONS_25G72), 0x2000000)
        self.assertEqual(validate_isc_report({'partition_start_lba': 65536, 'size_bytes': 67108864}), REGIONS_25G72)

    def test_every_field_mismatch_rejected(self):
        for offset in range(0, len(self.RAW), 4):
            with self.subTest(offset=offset):
                changed = bytearray(self.RAW)
                changed[offset] ^= 1
                with self.assertRaises(ValueError):
                    validate_regions(changed)

    def test_malformed_and_reordered_layout_rejected(self):
        for raw in (b'', self.RAW[:-1], self.RAW + b'\0' * 60,
                    self.RAW[12:] + self.RAW[:12], self.RAW[:12] * 7):
            with self.assertRaises(ValueError):
                validate_regions(raw)

    def test_overlap_or_out_of_disk_rejected(self):
        for start, size in ((0, 0x4000000), (0x1FFFFFF, 0x4000000),
                            (0x2000000, 0x2000000), (0x5000000, 0x4000000)):
            with self.subTest(start=start, size=size), self.assertRaises(ValueError):
                validate_regions(self.RAW, partition_start=start, disk_size=size)
