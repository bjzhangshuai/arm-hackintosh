from __future__ import annotations

import importlib.util
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

SPEC = importlib.util.spec_from_file_location(
    "macvm_wrap_img4_payload", TOOLS_ROOT / "wrap_img4_payload.py"
)
assert SPEC and SPEC.loader
WRAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WRAP)

from build_vmapple_aux import AuxiliaryStorageError, _der_element_size, _der_length  # noqa: E402


def der_sequence(marker: bytes, payload_size: int = 0, extra: bytes = b"") -> bytes:
    content = b"\x16\x04" + marker + extra + b"x" * payload_size
    return b"\x30" + _der_length(len(content)) + content


def im4p_payload(tag: bytes = b"dtre", payload_size: int = 0) -> bytes:
    return der_sequence(b"IM4P", payload_size, b"\x16\x04" + tag)


class WrapImg4PayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = 0x726174736D686974
        self.im4p = im4p_payload(payload_size=64)
        self.im4m = der_sequence(b"IM4M", 96)

    def test_stitches_im4p_with_shsh_ticket_without_restore_properties_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            im4p_path = root / "payload.im4p"
            shsh_path = root / "ticket.shsh2"
            output_path = root / "payload.img4"
            im4p_path.write_bytes(self.im4p)
            shsh_path.write_bytes(
                plistlib.dumps(
                    {
                        "ApImg4Ticket": self.im4m,
                        "generator": "0x726174736d686974",
                    }
                )
            )

            size = WRAP.wrap_img4_payload_file(
                im4p=im4p_path,
                ap_ticket=shsh_path,
                output=output_path,
            )

            wrapped = output_path.read_bytes()
            self.assertEqual(size, len(wrapped))
            self.assertEqual(_der_element_size(wrapped, "IMG4"), len(wrapped))
            self.assertIn(b"\x16\x04IMG4", wrapped[:16])
            self.assertIn(self.im4p, wrapped)
            self.assertIn(self.im4m, wrapped)
            self.assertNotIn(b"\x16\x04IM4R", wrapped)

    def test_component_name_rewrites_restore_im4p_tag_before_stitching(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            im4p_path = root / "payload.im4p"
            shsh_path = root / "ticket.shsh2"
            output_path = root / "payload.img4"
            im4p_path.write_bytes(self.im4p)
            shsh_path.write_bytes(
                plistlib.dumps(
                    {
                        "ApImg4Ticket": self.im4m,
                        "generator": hex(self.generator),
                    }
                )
            )

            WRAP.wrap_img4_payload_file(
                im4p=im4p_path,
                ap_ticket=shsh_path,
                output=output_path,
                component="RestoreDeviceTree",
            )
            wrapped = output_path.read_bytes()
            self.assertIn(b"\x16\x04IM4P\x16\x04rdtr", wrapped)
            self.assertNotIn(b"\x16\x04IM4P\x16\x04dtre", wrapped)

    def test_raw_im4m_can_stitch_without_generator_but_restore_properties_require_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            im4p_path = root / "payload.im4p"
            ticket_path = root / "ticket.im4m"
            plain_output_path = root / "payload.img4"
            restore_props_output_path = root / "payload-with-props.img4"
            im4p_path.write_bytes(self.im4p)
            ticket_path.write_bytes(self.im4m)

            size = WRAP.wrap_img4_payload_file(
                im4p=im4p_path,
                ap_ticket=ticket_path,
                output=plain_output_path,
            )
            self.assertEqual(size, plain_output_path.stat().st_size)

            with self.assertRaisesRegex(AuxiliaryStorageError, "generator is required"):
                WRAP.wrap_img4_payload_file(
                    im4p=im4p_path,
                    ap_ticket=ticket_path,
                    output=restore_props_output_path,
                    include_restore_properties=True,
                )

            size = WRAP.wrap_img4_payload_file(
                im4p=im4p_path,
                ap_ticket=ticket_path,
                output=restore_props_output_path,
                generator=self.generator,
                include_restore_properties=True,
            )
            self.assertEqual(size, restore_props_output_path.stat().st_size)
            self.assertIn(b"\x16\x04IM4R", restore_props_output_path.read_bytes())

    def test_refuses_to_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            root = Path(directory_name)
            im4p_path = root / "payload.im4p"
            shsh_path = root / "ticket.shsh2"
            output_path = root / "payload.img4"
            im4p_path.write_bytes(self.im4p)
            shsh_path.write_bytes(
                plistlib.dumps(
                    {
                        "ApImg4Ticket": self.im4m,
                        "generator": hex(self.generator),
                    }
                )
            )
            output_path.write_bytes(b"old")

            with self.assertRaisesRegex(AuxiliaryStorageError, "already exists"):
                WRAP.wrap_img4_payload_file(
                    im4p=im4p_path,
                    ap_ticket=shsh_path,
                    output=output_path,
                )

            WRAP.wrap_img4_payload_file(
                im4p=im4p_path,
                ap_ticket=shsh_path,
                output=output_path,
                force=True,
            )
            self.assertNotEqual(output_path.read_bytes(), b"old")


if __name__ == "__main__":
    unittest.main()
