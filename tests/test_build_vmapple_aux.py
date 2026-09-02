from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "macvm_build_vmapple_aux", ROOT / "tools" / "build_vmapple_aux.py"
)
assert SPEC and SPEC.loader
AUX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUX)


def der_sequence(marker: bytes, payload_size: int = 0) -> bytes:
    content = b"\x16\x04" + marker + b"x" * payload_size
    return b"\x30" + AUX._der_length(len(content)) + content


class VmappleAuxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.im4p = der_sequence(b"IM4P", 130)
        self.im4m = der_sequence(b"IM4M", 260)
        self.logo = der_sequence(b"IM4P", 20)
        self.generator = 0x726174736D686974

    def test_der_length_boundaries(self) -> None:
        self.assertEqual(AUX._der_length(0), b"\x00")
        self.assertEqual(AUX._der_length(0x7F), b"\x7f")
        self.assertEqual(AUX._der_length(0x80), b"\x81\x80")
        self.assertEqual(AUX._der_length(0x1234), b"\x82\x12\x34")

    def test_rejects_invalid_der_forms(self) -> None:
        cases = (
            (b"", "truncated"),
            (b"\x31\x00", "not a DER SEQUENCE"),
            (b"\x30\x80", "indefinite"),
            (b"\x30\x81\x01x", "non-canonical"),
            (b"\x30\x82\x01", "invalid DER length"),
            (b"\x30\x01", "size mismatch"),
            (b"\x30\x00x", "size mismatch"),
        )
        for data, message in cases:
            with self.subTest(data=data), self.assertRaisesRegex(
                AUX.AuxiliaryStorageError, message
            ):
                AUX._der_element_size(data, "fixture")

    def test_wraps_payload_and_manifest_as_img4(self) -> None:
        wrapped = AUX.wrap_img4(self.im4p, self.im4m, self.generator)
        self.assertEqual(AUX._der_element_size(wrapped, "IMG4"), len(wrapped))
        self.assertIn(b"\x16\x04IMG4", wrapped[:16])
        self.assertIn(self.im4p, wrapped)
        manifest = b"\xa0" + AUX._der_length(len(self.im4m)) + self.im4m
        expected_im4r = bytes.fromhex(
            "a12330211604494d34523119ff8492b9864e123010"
            "1604424e434e04087469686d73746172"
        )
        self.assertIn(manifest, wrapped)
        self.assertTrue(wrapped.endswith(expected_im4r))
        self.assertEqual(AUX.build_im4r(self.generator), expected_im4r[2:])

    def test_rejects_wrong_payload_and_ticket_markers(self) -> None:
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "not an IM4P"):
            AUX.wrap_img4(der_sequence(b"NOPE"), self.im4m, self.generator)
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "not an IM4M"):
            AUX.wrap_img4(self.im4p, der_sequence(b"NOPE"), self.generator)
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "nonzero 64-bit"):
            AUX.wrap_img4(self.im4p, self.im4m, 0)

    def test_loads_raw_and_shsh_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "ticket.im4m"
            raw.write_bytes(self.im4m)
            shsh = root / "ticket.shsh2"
            shsh.write_bytes(
                plistlib.dumps(
                    {
                        "ApImg4Ticket": self.im4m,
                        "generator": "0x726174736d686974",
                    }
                )
            )
            self.assertEqual(AUX.load_ap_ticket(raw), self.im4m)
            self.assertEqual(AUX.load_ap_ticket(shsh), self.im4m)
            self.assertIsNone(AUX.load_generator(raw))
            self.assertEqual(AUX.load_generator(shsh), self.generator)

    def test_rejects_invalid_shsh_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ticket.shsh2"
            path.write_bytes(plistlib.dumps({"generator": "0x1"}))
            with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "no binary"):
                AUX.load_ap_ticket(path)

    def test_builds_slot_zero_layout(self) -> None:
        llb = AUX.wrap_img4(self.im4p, self.im4m, self.generator)
        logo = AUX.wrap_img4(self.logo, self.im4m, self.generator)
        image = AUX.build_trimmed_aux(llb, logo, size=0x80000)
        fields = struct.unpack("<4sIII4I32s", image[:64])
        self.assertEqual(fields[:4], (b"HUFA", 1, 1, 0x20000))
        self.assertEqual(fields[4:8], (0, 0, 0, 0))
        self.assertEqual(
            fields[8],
            bytes.fromhex(
                "2505541d10405471bf5f3cd353f4a2d3"
                "7b40deae5e6f5c8a95c9141c3b2466e0"
            ),
        )
        self.assertEqual(fields[8], hashlib.sha384(image[:32]).digest()[:32])
        self.assertEqual(image[64:0x1000], b"\xff" * (0x1000 - 64))
        self.assertEqual(image[0x20000 : 0x20000 + len(llb)], llb)
        self.assertEqual(image[0x20000 + len(llb) : 0x20000 + len(llb) + len(logo)], logo)

    def test_builds_second_slot_and_hash_modes(self) -> None:
        llb = AUX.wrap_img4(self.im4p, self.im4m, self.generator)
        logo = AUX.wrap_img4(self.logo, self.im4m, self.generator)
        header_prefix = struct.pack(
            "<4sIII4I", b"HUFA", 1, 7, 0x220000, 0, 0, 0, 0
        )
        for mode, expected in (
            ("header", hashlib.sha384(header_prefix).digest()[:32]),
            ("zero", bytes(32)),
            ("llb", hashlib.sha256(llb).digest()),
            ("slot", hashlib.sha256(llb + logo).digest()),
        ):
            with self.subTest(mode=mode):
                image = AUX.build_trimmed_aux(
                    llb,
                    logo,
                    size=0x280000,
                    slot=1,
                    upgrade_count=7,
                    hufa_hash_mode=mode,
                )
                fields = struct.unpack("<4sIII4I32s", image[0x1000:0x1040])
                self.assertEqual(fields[:4], (b"HUFA", 1, 7, 0x220000))
                self.assertEqual(fields[8], expected)

    def test_rejects_invalid_layout_arguments(self) -> None:
        llb = AUX.wrap_img4(self.im4p, self.im4m, self.generator)
        logo = AUX.wrap_img4(self.logo, self.im4m, self.generator)
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "slot must"):
            AUX.build_trimmed_aux(llb, logo, slot=2)
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "upgrade count"):
            AUX.build_trimmed_aux(llb, logo, upgrade_count=0)
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "smaller"):
            AUX.build_trimmed_aux(llb, logo, size=0x20000)
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "unsupported"):
            AUX.build_trimmed_aux(llb, logo, hufa_hash_mode="mystery")
        with self.assertRaisesRegex(AUX.AuxiliaryStorageError, "exactly 32 bytes"):
            AUX._hufa_hash("header", b"short", llb, logo)


if __name__ == "__main__":
    unittest.main()
