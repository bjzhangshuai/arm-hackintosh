#!/usr/bin/env python3
"""Build and validate XNU's boot-time multi-module TrustCache region."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import struct


# The VMApple macOS kernel uses a 16 KiB translation granule.  arm_vm_init()
# protects the whole DeviceTree + TrustCache EXTRADATA span at that granularity.
PAGE_SIZE = 16 * 1024
GIB = 1024 * 1024 * 1024
VMAPPLE_RAM_BASE = 0x70000000
MAX_CONTAINER_BYTES = 16 * 1024 * 1024
MAX_REGION_BYTES = 16 * 1024 * 1024
TRUST_CACHE_MODULE_HEADER_BYTES = 24
TRUST_CACHE_ENTRY_BYTES = {1: 22, 2: 24}
UINT64_LIMIT = 1 << 64
_U32 = struct.Struct("<I")


class TrustCacheRegionError(ValueError):
    """The supplied Image4 object, TrustCache module, or region is unsafe."""


@dataclass(frozen=True)
class TrustCacheModule:
    version: int
    uuid: bytes
    num_entries: int
    entry_bytes: int
    payload: bytes


@dataclass(frozen=True)
class TrustCacheRegion:
    offsets: tuple[int, ...]
    modules: tuple[TrustCacheModule, ...]
    logical_length: int
    padded_length: int


def _align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def _read_der_element(data: bytes, offset: int, tag: int) -> tuple[bytes, int]:
    if offset >= len(data) or data[offset] != tag:
        raise TrustCacheRegionError(f"expected DER tag 0x{tag:02x} at offset {offset}")
    if offset + 1 >= len(data):
        raise TrustCacheRegionError("truncated DER length")

    first_length = data[offset + 1]
    cursor = offset + 2
    if first_length < 0x80:
        length = first_length
    else:
        width = first_length & 0x7F
        if width == 0 or width > 4 or cursor + width > len(data):
            raise TrustCacheRegionError("unsupported or truncated DER long length")
        length_bytes = data[cursor : cursor + width]
        if length_bytes[0] == 0:
            raise TrustCacheRegionError("non-canonical DER long length")
        length = int.from_bytes(length_bytes, "big")
        cursor += width
        if length < 0x80:
            raise TrustCacheRegionError("non-canonical DER long length")

    end = cursor + length
    if end > len(data):
        raise TrustCacheRegionError("truncated DER value")
    return data[cursor:end], end


def extract_im4p_payload(container: bytes, *, component: bytes) -> bytes:
    """Extract one exact payload from a DER ``IM4P/<component>`` object."""

    if not container or len(container) > MAX_CONTAINER_BYTES:
        raise TrustCacheRegionError("Image4 container has an unsafe size")
    sequence, end = _read_der_element(container, 0, 0x30)
    if end != len(container):
        raise TrustCacheRegionError("trailing data follows the IM4P sequence")

    cursor = 0
    magic, cursor = _read_der_element(sequence, cursor, 0x16)
    observed_component, cursor = _read_der_element(sequence, cursor, 0x16)
    description, cursor = _read_der_element(sequence, cursor, 0x16)
    payload, cursor = _read_der_element(sequence, cursor, 0x04)
    if cursor != len(sequence):
        raise TrustCacheRegionError("unexpected field follows the IM4P payload")
    if magic != b"IM4P" or observed_component != component:
        expected = component.decode("ascii", errors="replace")
        raise TrustCacheRegionError(f"object is not the expected IM4P/{expected} payload")
    if description != b"1":
        raise TrustCacheRegionError("unexpected TrustCache IM4P description")
    return payload


def parse_trustcache_module(
    payload: bytes, *, expected_version: int | None = None
) -> TrustCacheModule:
    if len(payload) < TRUST_CACHE_MODULE_HEADER_BYTES:
        raise TrustCacheRegionError("TrustCache module header is truncated")
    version = _U32.unpack_from(payload, 0)[0]
    if version not in TRUST_CACHE_ENTRY_BYTES:
        raise TrustCacheRegionError(f"unsupported TrustCache module version {version}")
    if expected_version is not None and version != expected_version:
        raise TrustCacheRegionError(
            f"TrustCache module version {version} != expected {expected_version}"
        )
    uuid = payload[4:20]
    if not any(uuid):
        raise TrustCacheRegionError("TrustCache module UUID is all zeroes")
    num_entries = _U32.unpack_from(payload, 20)[0]
    if num_entries == 0:
        raise TrustCacheRegionError("TrustCache module contains no entries")
    entry_bytes = TRUST_CACHE_ENTRY_BYTES[version]
    expected_length = TRUST_CACHE_MODULE_HEADER_BYTES + num_entries * entry_bytes
    if expected_length > MAX_REGION_BYTES:
        raise TrustCacheRegionError("TrustCache module exceeds the size limit")
    if len(payload) != expected_length:
        raise TrustCacheRegionError(
            f"TrustCache v{version} with {num_entries} entries requires "
            f"{expected_length} bytes, got {len(payload)}"
        )
    return TrustCacheModule(
        version=version,
        uuid=uuid,
        num_entries=num_entries,
        entry_bytes=entry_bytes,
        payload=payload,
    )


def build_trustcache_region(
    restore_container: bytes, basesystem_container: bytes
) -> bytes:
    """Build XNU's two-static-cache offset table and page-padded payload."""

    restore_payload = extract_im4p_payload(restore_container, component=b"rtsc")
    basesystem_payload = extract_im4p_payload(basesystem_container, component=b"bstc")
    restore = parse_trustcache_module(restore_payload, expected_version=1)
    basesystem = parse_trustcache_module(basesystem_payload, expected_version=2)
    if restore.uuid == basesystem.uuid:
        raise TrustCacheRegionError("Restore and BaseSystem TrustCaches reuse one UUID")

    header_length = 4 + 2 * 4
    offsets = (header_length, header_length + len(restore.payload))
    logical = struct.pack("<III", 2, *offsets) + restore.payload + basesystem.payload
    padded_length = _align_up(len(logical), PAGE_SIZE)
    if padded_length > MAX_REGION_BYTES:
        raise TrustCacheRegionError("combined TrustCache region exceeds the size limit")
    region = logical.ljust(padded_length, b"\0")
    parse_trustcache_region(region)
    return region


def parse_trustcache_region(data: bytes) -> TrustCacheRegion:
    """Strictly validate the exact two-module region consumed by XNU."""

    if len(data) < PAGE_SIZE or len(data) > MAX_REGION_BYTES:
        raise TrustCacheRegionError("TrustCache region has an unsafe size")
    if len(data) % PAGE_SIZE:
        raise TrustCacheRegionError("TrustCache region size is not page aligned")

    num_caches = _U32.unpack_from(data, 0)[0]
    if num_caches != 2:
        raise TrustCacheRegionError(
            f"TrustCache region must contain exactly 2 modules, got {num_caches}"
        )
    header_length = 4 + num_caches * 4
    offsets = struct.unpack_from("<II", data, 4)
    if offsets[0] != header_length or offsets[1] <= offsets[0]:
        raise TrustCacheRegionError("TrustCache module offsets are malformed")
    if offsets[1] + TRUST_CACHE_MODULE_HEADER_BYTES > len(data):
        raise TrustCacheRegionError("second TrustCache module begins outside the region")

    first_header = data[offsets[0] : offsets[0] + TRUST_CACHE_MODULE_HEADER_BYTES]
    first_version = _U32.unpack_from(first_header, 0)[0]
    first_count = _U32.unpack_from(first_header, 20)[0]
    if first_version not in TRUST_CACHE_ENTRY_BYTES:
        raise TrustCacheRegionError(
            f"unsupported first TrustCache module version {first_version}"
        )
    first_length = TRUST_CACHE_MODULE_HEADER_BYTES + (
        first_count * TRUST_CACHE_ENTRY_BYTES[first_version]
    )
    if offsets[0] + first_length != offsets[1]:
        raise TrustCacheRegionError("second TrustCache offset does not follow module 0")
    first = parse_trustcache_module(
        data[offsets[0] : offsets[1]], expected_version=1
    )

    second_header = data[offsets[1] : offsets[1] + TRUST_CACHE_MODULE_HEADER_BYTES]
    second_version = _U32.unpack_from(second_header, 0)[0]
    second_count = _U32.unpack_from(second_header, 20)[0]
    if second_version not in TRUST_CACHE_ENTRY_BYTES:
        raise TrustCacheRegionError(
            f"unsupported second TrustCache module version {second_version}"
        )
    second_length = TRUST_CACHE_MODULE_HEADER_BYTES + (
        second_count * TRUST_CACHE_ENTRY_BYTES[second_version]
    )
    logical_length = offsets[1] + second_length
    if logical_length > len(data):
        raise TrustCacheRegionError("second TrustCache module exceeds the region")
    second = parse_trustcache_module(
        data[offsets[1] : logical_length], expected_version=2
    )
    if first.uuid == second.uuid:
        raise TrustCacheRegionError("TrustCache region contains duplicate UUIDs")
    if any(data[logical_length:]):
        raise TrustCacheRegionError("TrustCache page padding is not zero-filled")

    return TrustCacheRegion(
        offsets=offsets,
        modules=(first, second),
        logical_length=logical_length,
        padded_length=len(data),
    )


def validate_physical_region(
    *, address: int, size: int, memory_base: int, memory_size: int
) -> tuple[int, int]:
    for name, value in (
        ("address", address),
        ("size", size),
        ("memory base", memory_base),
        ("memory size", memory_size),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise TrustCacheRegionError(f"{name} must be a non-negative integer")
    if size < PAGE_SIZE or size > MAX_REGION_BYTES or size % PAGE_SIZE:
        raise TrustCacheRegionError("TrustCache size must be page aligned and bounded")
    if address % PAGE_SIZE:
        raise TrustCacheRegionError("TrustCache address must be page aligned")
    memory_end = memory_base + memory_size
    region_end = address + size
    if memory_end > UINT64_LIMIT or region_end > UINT64_LIMIT:
        raise TrustCacheRegionError("TrustCache or guest memory range overflows uint64")
    if address < memory_base or region_end > memory_end:
        raise TrustCacheRegionError("TrustCache region is outside guest RAM")
    return address, size


def parse_u64_literal(value: str, *, name: str = "address") -> int:
    try:
        parsed = int(value, 0)
    except ValueError as error:
        raise TrustCacheRegionError(f"{name} must be a uint64 literal: {value}") from error
    if not 0 <= parsed < UINT64_LIMIT:
        raise TrustCacheRegionError(f"{name} must fit in uint64: {value}")
    return parsed


def regions_overlap(
    first_address: int, first_size: int, second_address: int, second_size: int
) -> bool:
    if first_size <= 0 or second_size <= 0:
        return False
    return first_address < second_address + second_size and second_address < first_address + first_size


def _read_bounded_file(path: str, *, allowed_root: str) -> tuple[Path, bytes]:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise TrustCacheRegionError("TrustCache asset path must be absolute")
    if "," in path:
        raise TrustCacheRegionError("TrustCache asset path cannot contain a comma")
    try:
        root = Path(allowed_root).resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise TrustCacheRegionError(f"TrustCache asset cannot be resolved: {error}") from error
    if resolved != root and root not in resolved.parents:
        raise TrustCacheRegionError(f"TrustCache asset must remain inside {root}")
    if not resolved.is_file() or not os.access(resolved, os.R_OK):
        raise TrustCacheRegionError("TrustCache asset is not a readable regular file")
    size = resolved.stat().st_size
    if size <= 0 or size > MAX_CONTAINER_BYTES:
        raise TrustCacheRegionError("TrustCache asset has an unsafe size")
    return resolved, resolved.read_bytes()


def load_region_image(
    path: str, *, allowed_root: str
) -> tuple[Path, bytes, TrustCacheRegion]:
    resolved, data = _read_bounded_file(path, allowed_root=allowed_root)
    return resolved, data, parse_trustcache_region(data)


def _write_new_file(path: str, data: bytes) -> Path:
    output = Path(path)
    if not output.is_absolute():
        raise TrustCacheRegionError("TrustCache output path must be absolute")
    if "," in path:
        raise TrustCacheRegionError("TrustCache output path cannot contain a comma")
    parent = output.parent.resolve(strict=True)
    resolved = parent / output.name
    try:
        with resolved.open("xb") as handle:
            handle.write(data)
    except FileExistsError as error:
        raise TrustCacheRegionError("TrustCache output already exists") from error
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--restore", required=True)
    build.add_argument("--basesystem", required=True)
    build.add_argument("--allowed-root", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--address", required=True)
    build.add_argument("--memory-gib", required=True, type=int)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--image", required=True)
    validate.add_argument("--allowed-root", required=True)
    args = parser.parse_args()

    try:
        if args.command == "build":
            restore_path, restore = _read_bounded_file(
                args.restore, allowed_root=args.allowed_root
            )
            basesystem_path, basesystem = _read_bounded_file(
                args.basesystem, allowed_root=args.allowed_root
            )
            region_bytes = build_trustcache_region(restore, basesystem)
            if not 1 <= args.memory_gib <= 36:
                raise TrustCacheRegionError("guest memory must be from 1 through 36 GiB")
            address = parse_u64_literal(args.address)
            validate_physical_region(
                address=address,
                size=len(region_bytes),
                memory_base=VMAPPLE_RAM_BASE,
                memory_size=args.memory_gib * GIB,
            )
            output = _write_new_file(args.output, region_bytes)
            region = parse_trustcache_region(region_bytes)
            print(
                f"{output}\t0x{address:x}\t{len(region_bytes)}\t{region.logical_length}\t"
                f"{restore_path}\t{basesystem_path}"
            )
        else:
            resolved, _, region = load_region_image(
                args.image, allowed_root=args.allowed_root
            )
            print(
                f"{resolved}\t{region.padded_length}\t{region.logical_length}\t"
                f"{region.modules[0].num_entries}\t{region.modules[1].num_entries}"
            )
    except TrustCacheRegionError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
