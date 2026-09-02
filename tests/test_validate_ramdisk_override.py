from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_ramdisk_override import (  # noqa: E402
    GIB,
    RamdiskOverrideError,
    VMAPPLE_RAM_BASE,
    parse_u64_literal,
    validate_image_path,
    validate_override,
    validate_physical_region,
)


class RamdiskOverrideTests(unittest.TestCase):
    def test_accepts_aligned_region_fully_inside_guest_ram(self) -> None:
        self.assertEqual(
            validate_physical_region(
                address=0x3C0000000,
                size=0xA0000000,
                memory_base=0x70A04000,
                memory_size=0x3FEB38000,
            ),
            (0x3C0000000, 0xA0000000),
        )

    def test_refuses_region_past_actual_bootargs_memory_end(self) -> None:
        with self.assertRaisesRegex(RamdiskOverrideError, "outside guest RAM"):
            validate_physical_region(
                address=0x400000000,
                size=0x80000000,
                memory_base=0x70A04000,
                memory_size=0x3FEB38000,
            )

    def test_refuses_unaligned_address_and_size(self) -> None:
        for address, size in ((0x70000001, 4096), (0x70000000, 4097)):
            with self.subTest(address=address, size=size):
                with self.assertRaisesRegex(RamdiskOverrideError, "aligned"):
                    validate_physical_region(
                        address=address,
                        size=size,
                        memory_base=VMAPPLE_RAM_BASE,
                        memory_size=4 * GIB,
                    )

    def test_refuses_zero_oversized_and_uint64_overflow_regions(self) -> None:
        cases = (
            (VMAPPLE_RAM_BASE, 0, VMAPPLE_RAM_BASE, 4 * GIB, "size"),
            (VMAPPLE_RAM_BASE, 5 * GIB, VMAPPLE_RAM_BASE, 8 * GIB, "size"),
            ((1 << 64) - 4096, 8192, 0, 1 << 64, "overflows"),
        )
        for address, size, base, memory_size, message in cases:
            with self.subTest(address=address, size=size):
                with self.assertRaisesRegex(RamdiskOverrideError, message):
                    validate_physical_region(
                        address=address,
                        size=size,
                        memory_base=base,
                        memory_size=memory_size,
                    )

    def test_parses_only_uint64_literals(self) -> None:
        self.assertEqual(parse_u64_literal("0x3c0000000"), 0x3C0000000)
        for value in ("bad", "-1", str(1 << 64)):
            with self.subTest(value=value):
                with self.assertRaises(RamdiskOverrideError):
                    parse_u64_literal(value)

    def test_image_must_be_regular_aligned_readable_file_beneath_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "ramdisk.raw"
            image.write_bytes(b"x" * 4096)
            resolved, size = validate_image_path(str(image), allowed_root=str(root))
            self.assertEqual(resolved, image.resolve())
            self.assertEqual(size, 4096)

            with self.assertRaisesRegex(RamdiskOverrideError, "absolute"):
                validate_image_path("ramdisk.raw", allowed_root=str(root))
            with self.assertRaisesRegex(RamdiskOverrideError, "regular file"):
                validate_image_path(str(root), allowed_root=str(root))

    def test_image_symlink_cannot_escape_staged_restore_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "restore"
            root.mkdir()
            outside = parent / "outside.raw"
            outside.write_bytes(b"x" * 4096)
            link = root / "escape.raw"
            link.symlink_to(outside)
            with self.assertRaisesRegex(RamdiskOverrideError, "inside staged"):
                validate_image_path(str(link), allowed_root=str(root))

    def test_full_override_accepts_current_16_gib_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "ramdisk.raw"
            with image.open("wb") as handle:
                handle.truncate(0xA0000000)
            resolved, address, size = validate_override(
                image=str(image),
                address_literal="0x3c0000000",
                memory_gib=16,
                allowed_root=str(root),
            )
            self.assertEqual(resolved, image.resolve())
            self.assertEqual(address, 0x3C0000000)
            self.assertEqual(size, 0xA0000000)


if __name__ == "__main__":
    unittest.main()
