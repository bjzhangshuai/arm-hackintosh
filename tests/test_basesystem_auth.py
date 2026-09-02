from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from basesystem_auth import (  # noqa: E402
    BaseSystemAuthError,
    CSYS_AUTH_PAYLOAD_LENGTH,
    CSYS_ROOT_HASH_LENGTH,
    extract_csys_auth_payload,
    extract_csys_root_hash,
)


def der_element(tag: int, value: bytes) -> bytes:
    if len(value) < 0x80:
        encoded_length = bytes((len(value),))
    else:
        width = (len(value).bit_length() + 7) // 8
        encoded_length = bytes((0x80 | width,)) + len(value).to_bytes(width, "big")
    return bytes((tag,)) + encoded_length + value


def csys_container(
    root_hash: bytes = bytes(range(CSYS_ROOT_HASH_LENGTH)),
    *,
    component: bytes = b"csys",
    version: int = 2,
    hash_type: int = 1,
    metadata: bytes | None = None,
) -> bytes:
    if metadata is None:
        metadata = b"m" * (CSYS_AUTH_PAYLOAD_LENGTH - 16 - len(root_hash))
    payload = version.to_bytes(8, "little") + hash_type.to_bytes(4, "little")
    payload += len(root_hash).to_bytes(4, "little") + root_hash + metadata
    contents = b"".join(
        (
            der_element(0x16, b"IM4P"),
            der_element(0x16, component),
            der_element(0x16, b"0"),
            der_element(0x04, payload),
        )
    )
    return der_element(0x30, contents)


class BaseSystemAuthTests(unittest.TestCase):
    def test_extracts_fixed_apfs_payload_and_its_root_hash_from_csys_im4p(self) -> None:
        root_hash = bytes(range(CSYS_ROOT_HASH_LENGTH))
        payload = extract_csys_auth_payload(csys_container(root_hash))

        self.assertEqual(len(payload), CSYS_AUTH_PAYLOAD_LENGTH)
        self.assertEqual(payload[16:48], root_hash)
        self.assertEqual(extract_csys_root_hash(csys_container(root_hash)), root_hash)

    def test_accepts_der_long_lengths(self) -> None:
        container = csys_container(bytes(range(CSYS_ROOT_HASH_LENGTH)))

        self.assertGreater(container[1], 0x80)
        self.assertEqual(len(extract_csys_auth_payload(container)), CSYS_AUTH_PAYLOAD_LENGTH)
        self.assertEqual(len(extract_csys_root_hash(container)), CSYS_ROOT_HASH_LENGTH)

    def test_rejects_wrong_container_tags_and_trailing_data(self) -> None:
        container = csys_container()

        with self.assertRaisesRegex(BaseSystemAuthError, "IM4P/csys"):
            extract_csys_root_hash(csys_container(component=b"krnl"))
        with self.assertRaisesRegex(BaseSystemAuthError, "trailing data"):
            extract_csys_root_hash(container + b"x")
        with self.assertRaisesRegex(BaseSystemAuthError, "expected DER tag"):
            extract_csys_root_hash(b"\x31" + container[1:])

    def test_rejects_truncated_or_noncanonical_der(self) -> None:
        container = csys_container()

        with self.assertRaisesRegex(BaseSystemAuthError, "truncated DER value"):
            extract_csys_root_hash(container[:-1])
        with self.assertRaisesRegex(BaseSystemAuthError, "non-canonical"):
            extract_csys_root_hash(b"\x30\x81\x01x")

    def test_rejects_invalid_csys_payload_header_and_hash(self) -> None:
        for root_hash in (b"\0" * CSYS_ROOT_HASH_LENGTH, b"x" * 31, b"x" * 33):
            with self.subTest(length=len(root_hash)):
                with self.assertRaises(BaseSystemAuthError):
                    extract_csys_auth_payload(csys_container(root_hash))

        with self.assertRaisesRegex(BaseSystemAuthError, "unsupported csys"):
            extract_csys_auth_payload(csys_container(version=3))
        with self.assertRaisesRegex(BaseSystemAuthError, "unsupported csys"):
            extract_csys_auth_payload(csys_container(hash_type=2))
        with self.assertRaisesRegex(BaseSystemAuthError, "208 bytes"):
            extract_csys_auth_payload(csys_container(metadata=b"x"))
