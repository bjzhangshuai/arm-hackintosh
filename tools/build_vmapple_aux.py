#!/usr/bin/env python3
"""Build a trimmed VMApple AuxiliaryStorage image from personalized IMG4 assets."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import plistlib
import struct
import sys


TOOLS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_ROOT))

from probe_host import require_debug_environment  # noqa: E402


DEFAULT_AUX_SIZE = 4 * 1024 * 1024
HUFA_PAGE_SIZE = 0x1000
LLB_SLOT_OFFSETS = (0x20000, 0x220000)


class AuxiliaryStorageError(ValueError):
    """Raised when input assets cannot form a valid VMApple AUX image."""


def _der_length(length: int) -> bytes:
    if length < 0:
        raise AuxiliaryStorageError("DER length cannot be negative")
    if length < 0x80:
        return bytes((length,))
    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    if len(encoded) > 4:
        raise AuxiliaryStorageError("DER element is too large")
    return bytes((0x80 | len(encoded),)) + encoded


def _der_element_size(data: bytes, label: str) -> int:
    if len(data) < 2:
        raise AuxiliaryStorageError(f"{label} is truncated")
    if data[0] != 0x30:
        raise AuxiliaryStorageError(f"{label} is not a DER SEQUENCE")
    first = data[1]
    if first == 0x80:
        raise AuxiliaryStorageError(f"{label} uses indefinite DER length")
    if first < 0x80:
        header_size = 2
        content_size = first
    else:
        count = first & 0x7F
        if count == 0 or count > 4 or len(data) < 2 + count:
            raise AuxiliaryStorageError(f"{label} has invalid DER length")
        length_bytes = data[2 : 2 + count]
        if length_bytes[0] == 0 or (count == 1 and length_bytes[0] < 0x80):
            raise AuxiliaryStorageError(f"{label} has non-canonical DER length")
        header_size = 2 + count
        content_size = int.from_bytes(length_bytes, "big")
    total = header_size + content_size
    if total != len(data):
        raise AuxiliaryStorageError(
            f"{label} DER size mismatch: header declares {total}, file has {len(data)}"
        )
    return total


def _load_signing_plist(path: Path) -> tuple[bytes, dict[str, object] | None]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise AuxiliaryStorageError(f"cannot read AP ticket: {error}") from error
    try:
        value = plistlib.loads(raw)
    except (plistlib.InvalidFileException, ValueError):
        ticket = raw
        value = None
    else:
        if not isinstance(value, dict):
            raise AuxiliaryStorageError("SHSH plist is not a dictionary")
        ticket = value.get("ApImg4Ticket")
        if not isinstance(ticket, bytes):
            raise AuxiliaryStorageError("SHSH plist has no binary ApImg4Ticket")
    _der_element_size(ticket, "AP ticket")
    if b"IM4M" not in ticket[:64]:
        raise AuxiliaryStorageError("AP ticket is not an IM4M manifest")
    return ticket, value


def load_ap_ticket(path: Path) -> bytes:
    return _load_signing_plist(path)[0]


def load_generator(path: Path) -> int | None:
    _, value = _load_signing_plist(path)
    if value is None:
        return None
    generator = value.get("generator")
    if generator is None:
        return None
    if not isinstance(generator, str):
        raise AuxiliaryStorageError("SHSH generator is not a string")
    try:
        parsed = int(generator, 0)
    except ValueError as error:
        raise AuxiliaryStorageError("SHSH generator is not a valid integer") from error
    if not 1 <= parsed <= 0xFFFFFFFFFFFFFFFF:
        raise AuxiliaryStorageError("SHSH generator must be a nonzero 64-bit value")
    return parsed


def _der_private_tag(number: int) -> bytes:
    if number <= 0:
        raise AuxiliaryStorageError("private DER tag number must be positive")
    groups = bytearray()
    while number:
        groups.append(number & 0x7F)
        number >>= 7
    groups.reverse()
    for index in range(len(groups) - 1):
        groups[index] |= 0x80
    return b"\xff" + bytes(groups)


def _der_tlv(tag: bytes, content: bytes) -> bytes:
    return tag + _der_length(len(content)) + content


def build_im4r(generator: int) -> bytes:
    if not 1 <= generator <= 0xFFFFFFFFFFFFFFFF:
        raise AuxiliaryStorageError("IMG4 generator must be a nonzero 64-bit value")
    bncn_content = b"\x16\x04BNCN" + _der_tlv(
        b"\x04", generator.to_bytes(8, "little")
    )
    bncn_sequence = _der_tlv(b"\x30", bncn_content)
    bncn_private = _der_tlv(_der_private_tag(int.from_bytes(b"BNCN", "big")), bncn_sequence)
    im4r_content = b"\x16\x04IM4R" + _der_tlv(b"\x31", bncn_private)
    return _der_tlv(b"\x30", im4r_content)


def wrap_img4(payload: bytes, ticket: bytes, generator: int) -> bytes:
    _der_element_size(payload, "IM4P payload")
    _der_element_size(ticket, "IM4M ticket")
    if b"IM4P" not in payload[:64]:
        raise AuxiliaryStorageError("payload is not an IM4P object")
    if b"IM4M" not in ticket[:64]:
        raise AuxiliaryStorageError("ticket is not an IM4M object")
    manifest = b"\xa0" + _der_length(len(ticket)) + ticket
    restore_properties = _der_tlv(b"\xa1", build_im4r(generator))
    content = b"\x16\x04IMG4" + payload + manifest + restore_properties
    return b"\x30" + _der_length(len(content)) + content


def _hufa_hash(
    mode: str, header_prefix: bytes, llb_img4: bytes, logo_img4: bytes
) -> bytes:
    if len(header_prefix) != 32:
        raise AuxiliaryStorageError("HUFA header prefix must be exactly 32 bytes")
    if mode == "header":
        return hashlib.sha384(header_prefix).digest()[:32]
    if mode == "zero":
        return bytes(32)
    if mode == "llb":
        return hashlib.sha256(llb_img4).digest()
    if mode == "slot":
        return hashlib.sha256(llb_img4 + logo_img4).digest()
    raise AuxiliaryStorageError(f"unsupported HUFA hash mode: {mode}")


def build_trimmed_aux(
    llb_img4: bytes,
    logo_img4: bytes,
    *,
    size: int = DEFAULT_AUX_SIZE,
    slot: int = 0,
    upgrade_count: int = 1,
    hufa_hash_mode: str = "header",
) -> bytes:
    _der_element_size(llb_img4, "LLB IMG4")
    _der_element_size(logo_img4, "logo IMG4")
    if slot not in (0, 1):
        raise AuxiliaryStorageError("slot must be 0 or 1")
    if not 1 <= upgrade_count <= 0xFFFFFFFF:
        raise AuxiliaryStorageError("upgrade count must be between 1 and 2^32-1")
    llb_offset = LLB_SLOT_OFFSETS[slot]
    end = llb_offset + len(llb_img4) + len(logo_img4)
    if size < end:
        raise AuxiliaryStorageError(
            f"AUX size {size} is smaller than required image end {end}"
        )
    image = bytearray(size)
    hufa_offset = slot * HUFA_PAGE_SIZE
    hufa = bytearray(b"\xff" * HUFA_PAGE_SIZE)
    header_prefix = struct.pack(
        "<4sIII4I",
        b"HUFA",
        1,
        upgrade_count,
        llb_offset,
        0,
        0,
        0,
        0,
    )
    hufa[:32] = header_prefix
    hufa[32:64] = _hufa_hash(
        hufa_hash_mode, header_prefix, llb_img4, logo_img4
    )
    image[hufa_offset : hufa_offset + HUFA_PAGE_SIZE] = hufa
    image[llb_offset : llb_offset + len(llb_img4)] = llb_img4
    logo_offset = llb_offset + len(llb_img4)
    image[logo_offset : logo_offset + len(logo_img4)] = logo_img4
    return bytes(image)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llb-im4p", required=True, type=Path)
    parser.add_argument("--logo-im4p", required=True, type=Path)
    parser.add_argument("--ap-ticket", required=True, type=Path)
    parser.add_argument(
        "--generator",
        type=lambda value: int(value, 0),
        help="64-bit IMG4 generator; defaults to the generator stored in SHSH2",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--size", type=int, default=DEFAULT_AUX_SIZE)
    parser.add_argument("--slot", type=int, choices=(0, 1), default=0)
    parser.add_argument("--upgrade-count", type=int, default=1)
    parser.add_argument(
        "--hufa-hash-mode",
        choices=("header", "zero", "llb", "slot"),
        default="header",
        help=(
            "HUFA validation field; 'header' is the AVPBooter-compatible default, "
            "while the other values exist only for bounded diagnostic tests"
        ),
    )
    args = parser.parse_args()

    require_debug_environment()
    try:
        ticket = load_ap_ticket(args.ap_ticket)
        generator = args.generator
        if generator is None:
            generator = load_generator(args.ap_ticket)
        if generator is None:
            raise AuxiliaryStorageError(
                "an IMG4 generator is required when the AP ticket is raw IM4M"
            )
        llb_img4 = wrap_img4(args.llb_im4p.read_bytes(), ticket, generator)
        logo_img4 = wrap_img4(args.logo_im4p.read_bytes(), ticket, generator)
        image = build_trimmed_aux(
            llb_img4,
            logo_img4,
            size=args.size,
            slot=args.slot,
            upgrade_count=args.upgrade_count,
            hufa_hash_mode=args.hufa_hash_mode,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(image)
    except (OSError, AuxiliaryStorageError) as error:
        print(f"macvm: AUX build failed: {error}", file=sys.stderr)
        return 1
    print(
        f"wrote {args.output} ({len(image)} bytes, slot={args.slot}, "
        f"llb_img4={len(llb_img4)}, logo_img4={len(logo_img4)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
