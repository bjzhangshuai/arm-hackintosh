import io
import struct
import unittest
import zipfile

from tools.verify_local_update_archive import verify_archive, verify_zip64_footer


def fixture(files=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in (files or [('Info.plist', b'info'), ('AssetData/payload', b'payload')]):
            archive.writestr(name, data)
    data = output.getvalue()
    end = struct.unpack('<4s4H2IH', data[-22:])
    offset = len(data) - 22
    zip64 = struct.pack('<4sQ2H2I4Q', b'PK\x06\x06', 44, 45, 45, 0, 0,
                        end[3], end[4], end[5], end[6])
    locator = struct.pack('<4sIQI', b'PK\x06\x07', 0, offset, 1)
    return data[:-22] + zip64 + locator + data[-22:]


class LocalUpdateArchiveTests(unittest.TestCase):
    def test_valid_crc_inventory_and_info(self):
        result = verify_archive(io.BytesIO(fixture()), b'info', 2, 11)
        self.assertEqual(result['regular_files'], 2)
        self.assertEqual(result['crc'], 'all entries passed')
        self.assertEqual(result['apple_signatures'], 'not evaluated')

    def test_standard_zip_without_zip64_rejected(self):
        data = fixture()
        with self.assertRaises(ValueError):
            verify_zip64_footer(io.BytesIO(data[:-98] + data[-22:]))

    def test_wrapped_central_directory_rejected(self):
        data = bytearray(fixture())
        pos = data.index(b'PK\x06\x06')
        struct.pack_into('<Q', data, pos + 48, 2**32)
        with self.assertRaisesRegex(ValueError, 'wrapped'):
            verify_zip64_footer(io.BytesIO(data))

    def test_out_of_bounds_locator_rejected(self):
        data = bytearray(fixture())
        struct.pack_into('<Q', data, len(data) - 34, 2**63)
        with self.assertRaises(ValueError):
            verify_zip64_footer(io.BytesIO(data))

    def test_trailing_bytes_rejected(self):
        with self.assertRaises(ValueError):
            verify_zip64_footer(io.BytesIO(fixture() + b'junk'))

    def test_source_info_must_match(self):
        for info in (b'wrong', b'xxxx'):
            with self.subTest(info=info), self.assertRaises(ValueError):
                verify_archive(io.BytesIO(fixture()), info, 2, 11)

    def test_source_inventory_must_match(self):
        for count, size in ((1, 11), (2, 10)):
            with self.subTest(count=count, size=size), self.assertRaises(ValueError):
                verify_archive(io.BytesIO(fixture()), b'info', count, size)

    def test_unsafe_names_rejected(self):
        for name in ('../bad', '/bad', 'a/../../bad', 'a\\bad'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify_archive(io.BytesIO(fixture([('Info.plist', b'info'), (name, b'payload')])), b'info', 2, 11)

    def test_duplicate_normalized_path_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            verify_archive(io.BytesIO(fixture([('Info.plist', b'info'), ('./Info.plist', b'info')])), b'info', 2, 8)

    def test_corrupt_payload_crc_rejected(self):
        data = fixture().replace(b'payloadPK', b'payloaePK')
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            verify_archive(io.BytesIO(data), b'info', 2, 11)
