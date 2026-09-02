"""Parse the BaseSystem authentication payload embedded in ``IM4P/csys``."""

from __future__ import annotations

import struct


CSYS_FORMAT_VERSION = 2
CSYS_ROOT_HASH_TYPE = 1
CSYS_ROOT_HASH_LENGTH = 32
CSYS_AUTH_PAYLOAD_LENGTH = 208
_CSYS_HEADER = struct.Struct("<QII")


class BaseSystemAuthError(ValueError):
    """The supplied BaseSystem authentication container is malformed."""


def _read_der_element(data: bytes, offset: int, tag: int) -> tuple[bytes, int]:
    if offset >= len(data) or data[offset] != tag:
        raise BaseSystemAuthError(f"expected DER tag 0x{tag:02x} at offset {offset}")
    if offset + 1 >= len(data):
        raise BaseSystemAuthError("truncated DER length")

    first_length = data[offset + 1]
    cursor = offset + 2
    if first_length < 0x80:
        length = first_length
    else:
        length_bytes = first_length & 0x7F
        if length_bytes == 0 or length_bytes > 4 or cursor + length_bytes > len(data):
            raise BaseSystemAuthError("unsupported or truncated DER long length")
        length = int.from_bytes(data[cursor : cursor + length_bytes], "big")
        cursor += length_bytes
        if length < 0x80:
            raise BaseSystemAuthError("non-canonical DER long length")

    end = cursor + length
    if end > len(data):
        raise BaseSystemAuthError("truncated DER value")
    return data[cursor:end], end


def extract_csys_auth_payload(container: bytes) -> bytes:
    """Return APFS's fixed-size BaseSystem auth payload from ``IM4P/csys``.

    The restore asset is a DER-wrapped IM4P/csys object.  APFS receives the
    inner OCTET STRING payload: a 208-byte envelope containing the version,
    hash type, hash length, digest, and authenticated metadata.  It does not
    accept either the 229-byte DER container or the digest by itself.
    """

    sequence, end = _read_der_element(container, 0, 0x30)
    if end != len(container):
        raise BaseSystemAuthError("trailing data follows the IM4P sequence")

    cursor = 0
    im4p, cursor = _read_der_element(sequence, cursor, 0x16)
    component, cursor = _read_der_element(sequence, cursor, 0x16)
    _, cursor = _read_der_element(sequence, cursor, 0x16)
    payload, cursor = _read_der_element(sequence, cursor, 0x04)
    if cursor != len(sequence):
        raise BaseSystemAuthError("unexpected field follows the csys payload")
    if im4p != b"IM4P" or component != b"csys":
        raise BaseSystemAuthError("BaseSystem auth object is not an IM4P/csys payload")

    if len(payload) != CSYS_AUTH_PAYLOAD_LENGTH:
        raise BaseSystemAuthError(
            f"csys auth payload must be {CSYS_AUTH_PAYLOAD_LENGTH} bytes, got {len(payload)}"
        )
    version, hash_type, root_hash_length = _CSYS_HEADER.unpack_from(payload)
    if version != CSYS_FORMAT_VERSION or hash_type != CSYS_ROOT_HASH_TYPE:
        raise BaseSystemAuthError("unsupported csys root-hash payload header")
    if root_hash_length != CSYS_ROOT_HASH_LENGTH:
        raise BaseSystemAuthError(
            f"csys root-hash length must be {CSYS_ROOT_HASH_LENGTH}, got {root_hash_length}"
        )

    end = _CSYS_HEADER.size + root_hash_length
    if end > len(payload):
        raise BaseSystemAuthError("csys payload truncates the root hash")
    root_hash = payload[_CSYS_HEADER.size:end]
    if not any(root_hash):
        raise BaseSystemAuthError("csys root hash is all zeroes")
    return payload


def extract_csys_root_hash(container: bytes) -> bytes:
    """Return the digest portion of a validated ``IM4P/csys`` container."""

    payload = extract_csys_auth_payload(container)
    end = _CSYS_HEADER.size + CSYS_ROOT_HASH_LENGTH
    return payload[_CSYS_HEADER.size:end]
