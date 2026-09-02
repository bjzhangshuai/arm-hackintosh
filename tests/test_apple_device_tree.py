from __future__ import annotations

import struct
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import apple_device_tree as DT  # noqa: E402


def node(name: str, properties: tuple[bytes, ...], children: tuple[bytes, ...] = ()) -> bytes:
    name_record = DT._encode_property("name", name.encode("ascii") + b"\0", secure=False)
    records = (name_record,) + properties
    return struct.pack("<II", len(records), len(children)) + b"".join(records + children)


def fixture(*, placeholder: bytes = bytes(128), secure: bool = False, collision: bool = False) -> bytes:
    chosen_properties = [
        DT._encode_property("host-os-information", placeholder, secure=secure)
    ]
    if collision:
        chosen_properties.append(DT._encode_property("boot-uuid", b"existing", secure=False))
    chosen = node("chosen", tuple(chosen_properties))
    return node("device-tree", (), (chosen,))


class ZeroFilledDeviceTreeReplacementTests(unittest.TestCase):
    def test_replacement_preserves_extent_header_offset_and_value_length(self) -> None:
        original = fixture()
        root = DT.parse_device_tree(original)
        old = DT.find_node(root, "/device-tree/chosen").property(
            "host-os-information"
        )
        prefix = b"01234567-89AB-CDEF-0123-456789ABCDEF"
        updated = DT.replace_zero_filled_property_with_prefix(
            original,
            node_path="/device-tree/chosen",
            old_name="host-os-information",
            new_name="boot-uuid",
            prefix=prefix,
        )
        self.assertEqual(len(updated), len(original))
        replacement = DT.find_node(
            DT.parse_device_tree(updated), "/device-tree/chosen"
        ).property("boot-uuid")
        self.assertEqual(replacement.header_offset, old.header_offset)
        self.assertEqual(replacement.length, 128)
        self.assertEqual(replacement.value[:36], prefix)
        self.assertEqual(replacement.value[36:], bytes(128 - 36))
        self.assertEqual(original, fixture())

    def test_replacement_refuses_nonzero_or_secure_placeholder(self) -> None:
        with self.assertRaisesRegex(DT.AppleDeviceTreeError, "nonzero data"):
            DT.replace_zero_filled_property_with_prefix(
                fixture(placeholder=b"x" + bytes(127)),
                node_path="/device-tree/chosen",
                old_name="host-os-information",
                new_name="boot-uuid",
                prefix=b"value",
            )
        with self.assertRaisesRegex(DT.AppleDeviceTreeError, "unexpectedly secure"):
            DT.replace_zero_filled_property_with_prefix(
                fixture(secure=True),
                node_path="/device-tree/chosen",
                old_name="host-os-information",
                new_name="boot-uuid",
                prefix=b"value",
            )

    def test_replacement_refuses_empty_or_oversized_prefix(self) -> None:
        with self.assertRaisesRegex(DT.AppleDeviceTreeError, "prefix is empty"):
            DT.replace_zero_filled_property_with_prefix(
                fixture(),
                node_path="/device-tree/chosen",
                old_name="host-os-information",
                new_name="boot-uuid",
                prefix=b"",
            )
        with self.assertRaisesRegex(DT.AppleDeviceTreeError, "requires 129 bytes"):
            DT.replace_zero_filled_property_with_prefix(
                fixture(),
                node_path="/device-tree/chosen",
                old_name="host-os-information",
                new_name="boot-uuid",
                prefix=bytes(129),
            )

    def test_replacement_refuses_name_collision_and_missing_property(self) -> None:
        with self.assertRaisesRegex(DT.AppleDeviceTreeError, "collides"):
            DT.replace_zero_filled_property_with_prefix(
                fixture(collision=True),
                node_path="/device-tree/chosen",
                old_name="host-os-information",
                new_name="boot-uuid",
                prefix=b"value",
            )
        with self.assertRaisesRegex(DT.AppleDeviceTreeError, "0 properties"):
            DT.replace_zero_filled_property_with_prefix(
                fixture(),
                node_path="/device-tree/chosen",
                old_name="missing",
                new_name="boot-uuid",
                prefix=b"value",
            )


if __name__ == "__main__":
    unittest.main()
