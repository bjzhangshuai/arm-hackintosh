import struct
import unittest
import zlib

from tools.vmapple_ean import (EAN_OFFSET, EAN_SIZE, HEADER_SIZE,
                               empty_header, validate_empty_header, require_blank_region)


class EANHeaderTests(unittest.TestCase):
    def test_fields_and_crc_match_reviewed_driver(self):
        data = empty_header()
        self.assertEqual(len(data), 4096)
        self.assertEqual(data[:20].hex(), '01000000eaeaeaea000000000000600000100000')
        self.assertEqual(struct.unpack_from('<I', data, 4092)[0], zlib.crc32(data[:4092]))
        validate_empty_header(data)

    def test_region_does_not_overlap_isc(self):
        self.assertEqual(EAN_OFFSET + EAN_SIZE, 32 * 1024 * 1024)
        self.assertGreaterEqual(EAN_OFFSET, 0x01506000)
        self.assertGreater(struct.unpack_from('<I', empty_header(), 16)[0], 0)

    def test_every_header_byte_is_checked(self):
        original = empty_header()
        for offset in range(HEADER_SIZE):
            changed = bytearray(original)
            changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                validate_empty_header(changed)

    def test_short_or_long_headers_rejected(self):
        for data in (b'', empty_header()[:-1], empty_header() + b'\0'):
            with self.assertRaises(ValueError):
                validate_empty_header(data)

    def test_nonblank_storage_cannot_be_overwritten(self):
        require_blank_region(bytes(EAN_SIZE))
        require_blank_region(b'\xff' * EAN_SIZE)
        for data in (bytes(EAN_SIZE - 1), empty_header() + bytes(EAN_SIZE - HEADER_SIZE),
                     bytes(EAN_SIZE - 1) + b'\x01', b'\x01' + bytes(EAN_SIZE - 1)):
            with self.assertRaises(ValueError):
                require_blank_region(data)
