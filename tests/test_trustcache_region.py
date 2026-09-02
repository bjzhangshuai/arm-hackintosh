from __future__ import annotations

from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from trustcache_region import (  # noqa: E402
    PAGE_SIZE,
    TrustCacheRegionError,
    build_trustcache_region,
    extract_im4p_payload,
    load_region_image,
    parse_u64_literal,
    parse_trustcache_module,
    parse_trustcache_region,
    regions_overlap,
    validate_physical_region,
)


def der_element(tag: int, value: bytes) -> bytes:
    if len(value) < 0x80:
        length = bytes((len(value),))
    else:
        width = (len(value).bit_length() + 7) // 8
        length = bytes((0x80 | width,)) + len(value).to_bytes(width, "big")
    return bytes((tag,)) + length + value


def module(version: int, count: int, *, uuid_byte: int) -> bytes:
    entry_size = {1: 22, 2: 24}[version]
    return (
        struct.pack("<I", version)
        + bytes((uuid_byte,)) * 16
        + struct.pack("<I", count)
        + bytes((version,)) * (count * entry_size)
    )


def im4p(component: bytes, payload: bytes, *, description: bytes = b"1") -> bytes:
    sequence = b"".join(
        (
            der_element(0x16, b"IM4P"),
            der_element(0x16, component),
            der_element(0x16, description),
            der_element(0x04, payload),
        )
    )
    return der_element(0x30, sequence)


class TrustCacheRegionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.restore_module = module(1, 3, uuid_byte=0x11)
        self.basesystem_module = module(2, 5, uuid_byte=0x22)
        self.restore = im4p(b"rtsc", self.restore_module)
        self.basesystem = im4p(b"bstc", self.basesystem_module)

    def test_builds_two_module_xnu_region_with_exact_offsets_and_zero_padding(self) -> None:
        data = build_trustcache_region(self.restore, self.basesystem)
        parsed = parse_trustcache_region(data)

        self.assertEqual(len(data), PAGE_SIZE)
        self.assertEqual(parsed.offsets, (12, 12 + len(self.restore_module)))
        self.assertEqual(parsed.logical_length, 12 + len(self.restore_module) + len(self.basesystem_module))
        self.assertEqual([item.version for item in parsed.modules], [1, 2])
        self.assertEqual([item.num_entries for item in parsed.modules], [3, 5])
        self.assertFalse(any(data[parsed.logical_length :]))

    def test_parser_accepts_realistic_multpage_region(self) -> None:
        restore = im4p(b"rtsc", module(1, 524, uuid_byte=0x31))
        basesystem = im4p(b"bstc", module(2, 1073, uuid_byte=0x42))
        parsed = parse_trustcache_region(build_trustcache_region(restore, basesystem))

        self.assertEqual(parsed.padded_length, 0xC000)
        self.assertEqual(parsed.logical_length, 37340)
        self.assertEqual(parsed.offsets, (12, 11564))

    def test_extracts_only_expected_im4p_component_and_description(self) -> None:
        self.assertEqual(
            extract_im4p_payload(self.restore, component=b"rtsc"),
            self.restore_module,
        )
        with self.assertRaisesRegex(TrustCacheRegionError, "IM4P/bstc"):
            extract_im4p_payload(self.restore, component=b"bstc")
        with self.assertRaisesRegex(TrustCacheRegionError, "description"):
            extract_im4p_payload(
                im4p(b"rtsc", self.restore_module, description=b"2"), component=b"rtsc"
            )

    def test_rejects_der_truncation_trailing_data_and_noncanonical_length(self) -> None:
        with self.assertRaisesRegex(TrustCacheRegionError, "truncated DER value"):
            extract_im4p_payload(self.restore[:-1], component=b"rtsc")
        with self.assertRaisesRegex(TrustCacheRegionError, "trailing data"):
            extract_im4p_payload(self.restore + b"x", component=b"rtsc")
        with self.assertRaisesRegex(TrustCacheRegionError, "non-canonical"):
            extract_im4p_payload(b"\x30\x81\x01x", component=b"rtsc")

    def test_rejects_module_version_uuid_count_and_length_errors(self) -> None:
        cases = (
            (b"x" * 23, "truncated"),
            (struct.pack("<I", 3) + b"x" * 20, "unsupported"),
            (struct.pack("<I", 1) + b"\0" * 16 + struct.pack("<I", 1) + b"x" * 22, "UUID"),
            (struct.pack("<I", 1) + b"x" * 16 + struct.pack("<I", 0), "no entries"),
            (module(1, 1, uuid_byte=1) + b"x", "requires"),
        )
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(TrustCacheRegionError, message):
                    parse_trustcache_module(payload)
        with self.assertRaisesRegex(TrustCacheRegionError, "expected 2"):
            parse_trustcache_module(self.restore_module, expected_version=2)

    def test_rejects_wrong_component_version_and_duplicate_uuid_at_build(self) -> None:
        with self.assertRaises(TrustCacheRegionError):
            build_trustcache_region(im4p(b"rtsc", module(2, 1, uuid_byte=1)), self.basesystem)
        with self.assertRaises(TrustCacheRegionError):
            build_trustcache_region(self.restore, im4p(b"rtsc", self.basesystem_module))
        duplicate = im4p(b"bstc", module(2, 1, uuid_byte=0x11))
        with self.assertRaisesRegex(TrustCacheRegionError, "reuse one UUID"):
            build_trustcache_region(self.restore, duplicate)

    def test_rejects_corrupt_region_count_offsets_order_and_padding(self) -> None:
        original = bytearray(build_trustcache_region(self.restore, self.basesystem))
        mutations = []
        changed = bytearray(original)
        struct.pack_into("<I", changed, 0, 1)
        mutations.append((changed, "exactly 2"))
        changed = bytearray(original)
        struct.pack_into("<I", changed, 4, 16)
        mutations.append((changed, "offsets"))
        changed = bytearray(original)
        struct.pack_into("<I", changed, 8, 13)
        mutations.append((changed, "does not follow"))
        changed = bytearray(original)
        changed[-1] = 1
        mutations.append((changed, "padding"))
        for data, message in mutations:
            with self.subTest(message=message):
                with self.assertRaisesRegex(TrustCacheRegionError, message):
                    parse_trustcache_region(bytes(data))

    def test_rejects_unaligned_or_unbounded_region_image(self) -> None:
        with self.assertRaisesRegex(TrustCacheRegionError, "unsafe size"):
            parse_trustcache_region(b"x" * 128)
        with self.assertRaisesRegex(TrustCacheRegionError, "page aligned"):
            parse_trustcache_region(b"x" * (PAGE_SIZE + 1))

    def test_validates_actual_bootargs_range_and_detects_overlap(self) -> None:
        self.assertEqual(
            validate_physical_region(
                address=0x7433C000,
                size=0xC000,
                memory_base=0x70A04000,
                memory_size=0x3FEB38000,
            ),
            (0x7433C000, 0xC000),
        )
        with self.assertRaisesRegex(TrustCacheRegionError, "outside guest RAM"):
            validate_physical_region(
                address=0x46F538000,
                size=0xC000,
                memory_base=0x70A04000,
                memory_size=0x3FEB38000,
            )
        self.assertFalse(regions_overlap(0x7433C000, 0xC000, 0x3C0000000, 0xA0000000))
        self.assertTrue(regions_overlap(0x45FFFF000, 0x2000, 0x3C0000000, 0xA0000000))
        self.assertFalse(regions_overlap(0, 0, 0, 1))
        self.assertEqual(parse_u64_literal("0x7433c000"), 0x7433C000)
        for value in ("bad", "-1", str(1 << 64)):
            with self.subTest(value=value):
                with self.assertRaises(TrustCacheRegionError):
                    parse_u64_literal(value)

    def test_real_boot_layout_keeps_locked_extradata_contiguous_and_aligned(self) -> None:
        device_tree_length = 0x8C000
        old_device_tree = 0x742B8000
        old_trustcache = 0x74344000
        old_trustcache_size = 0x4000
        bootkc = old_trustcache + old_trustcache_size
        new_trustcache_size = 0xC000
        new_trustcache = bootkc - new_trustcache_size
        new_device_tree = new_trustcache - device_tree_length

        self.assertEqual(bootkc, 0x74348000)
        self.assertEqual(new_trustcache, 0x7433C000)
        self.assertEqual(new_device_tree, 0x742B0000)
        self.assertEqual(old_device_tree - new_device_tree, 0x8000)
        self.assertEqual(new_device_tree + device_tree_length, new_trustcache)
        self.assertEqual(new_trustcache + new_trustcache_size, bootkc)
        for address in (new_device_tree, new_trustcache, bootkc):
            with self.subTest(address=address):
                self.assertEqual(address % PAGE_SIZE, 0)

    def test_load_region_path_stays_beneath_allowed_root(self) -> None:
        data = build_trustcache_region(self.restore, self.basesystem)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runs"
            root.mkdir()
            image = root / "trustcache-region.raw"
            image.write_bytes(data)
            resolved, loaded, parsed = load_region_image(str(image), allowed_root=str(root))
            self.assertEqual(resolved, image.resolve())
            self.assertEqual(loaded, data)
            self.assertEqual(parsed.padded_length, PAGE_SIZE)

            outside = Path(directory) / "outside.raw"
            outside.write_bytes(data)
            link = root / "escape.raw"
            link.symlink_to(outside)
            with self.assertRaisesRegex(TrustCacheRegionError, "inside"):
                load_region_image(str(link), allowed_root=str(root))


if __name__ == "__main__":
    unittest.main()
