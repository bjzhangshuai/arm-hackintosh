from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from tools.scan_aarch64_mmio_constants import (
    AddressRange,
    coalesce_hits,
    scan_move_wide_constants,
    scan_raw_literals,
)


def u32(value: int) -> bytes:
    return value.to_bytes(4, "little")


class ScanAarch64MmioConstantsTests(unittest.TestCase):
    def test_detects_movz_movk_built_32_bit_mmio_address(self) -> None:
        # movz w8, #0x40; movk w8, #0x3024, lsl #16 => 0x30240040.
        data = u32(0x52800808) + u32(0x72A60488)

        hits = scan_move_wide_constants(
            data,
            base=0x70085834,
            ranges=[AddressRange(0x30240000, 0x30250000)],
        )

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].va, 0x70085838)
        self.assertEqual(hits[0].value, 0x30240040)
        self.assertIn("movk w8", hits[0].detail)

    def test_detects_movz_shifted_32_bit_mmio_base(self) -> None:
        # movz w8, #0x3026, lsl #16 => objdump prints mov w8, #0x30260000.
        data = u32(0x52A604C8)

        hits = scan_move_wide_constants(
            data,
            base=0x7008451C,
            ranges=[AddressRange(0x30260000, 0x30270000)],
        )

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].va, 0x7008451C)
        self.assertEqual(hits[0].value, 0x30260000)
        self.assertIn("movz w8", hits[0].detail)

    def test_ignores_unknown_movk_without_prior_value(self) -> None:
        data = u32(0x72A60488)

        hits = scan_move_wide_constants(
            data,
            base=0,
            ranges=[AddressRange(0x30240000, 0x30250000)],
        )

        self.assertEqual(hits, [])

    def test_does_not_join_move_wide_constants_across_other_instructions(self) -> None:
        # movz w8, #0x40; nop; movk w8, #0x3024, lsl #16 must not be
        # reconstructed as 0x30240040.  The scanner is a root-cause triage
        # tool, so false positives here would waste QEMU patch/debug cycles.
        data = u32(0x52800808) + u32(0xD503201F) + u32(0x72A60488)

        hits = scan_move_wide_constants(
            data,
            base=0x70085834,
            ranges=[AddressRange(0x30240000, 0x30250000)],
        )

        self.assertEqual(hits, [])

    def test_reports_only_final_value_from_a_move_wide_sequence(self) -> None:
        # mov x10, #0xfc27; movk x10, #0x3000, lsl #16; movk x10, #0x20,
        # lsl #32.  The intermediate 0x3000fc27 looks like BDOOR MMIO, but
        # the completed 64-bit value is a bitmask and must not be reported.
        data = u32(0xD29F84EA) + u32(0xF2A6000A) + u32(0xF2C0040A)

        hits = scan_move_wide_constants(
            data,
            base=0x70081BA4,
            ranges=[AddressRange(0x30000000, 0x30200000)],
        )

        self.assertEqual(hits, [])

    def test_scans_aligned_raw_literals_when_requested_by_caller(self) -> None:
        data = b"\x00\x00\x00\x00" + (0x30260000).to_bytes(8, "little")

        hits = scan_raw_literals(
            data,
            base=0x70000000,
            ranges=[AddressRange(0x30260000, 0x30270000)],
        )

        self.assertTrue(any(hit.kind == "literal-64" for hit in hits))
        self.assertTrue(any(hit.value == 0x30260000 for hit in hits))

    def test_coalesces_exact_duplicate_hits(self) -> None:
        data = u32(0x52A604C8)
        hits = scan_move_wide_constants(
            data,
            base=0x7008451C,
            ranges=[AddressRange(0x30260000, 0x30270000)],
        )

        self.assertEqual(coalesce_hits(hits + hits), hits)

    def test_cli_can_scan_a_temporary_blob(self) -> None:
        from tools import scan_aarch64_mmio_constants

        with tempfile.TemporaryDirectory() as tmp_dir:
            blob = Path(tmp_dir) / "blob.bin"
            blob.write_bytes(u32(0x52800808) + u32(0x72A60488))

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = scan_aarch64_mmio_constants.main(
                    [
                        str(blob),
                        "--base",
                        "0x70085834",
                        "--range",
                        "0x30240000:0x30250000",
                    ]
                )

        self.assertEqual(rc, 0)
        self.assertIn("value=0x0000000030240040", output.getvalue())


if __name__ == "__main__":
    unittest.main()
