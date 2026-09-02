#!/usr/bin/env python3
"""Validate a QEMU-loaded RAMDisk override before a VMApple test boot."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


VMAPPLE_RAM_BASE = 0x70000000
GIB = 1024 * 1024 * 1024
MIN_IMAGE_BYTES = 4096
MAX_IMAGE_BYTES = 4 * GIB
ALIGNMENT = 4096
UINT64_LIMIT = 1 << 64


class RamdiskOverrideError(ValueError):
    """Raised when a RAMDisk override could corrupt or escape guest RAM."""


def parse_u64_literal(value: str, *, name: str = "address") -> int:
    try:
        parsed = int(value, 0)
    except ValueError as error:
        raise RamdiskOverrideError(f"{name} must be a uint64 literal: {value}") from error
    if not 0 <= parsed < UINT64_LIMIT:
        raise RamdiskOverrideError(f"{name} must fit in uint64: {value}")
    return parsed


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
            raise RamdiskOverrideError(f"{name} must be a non-negative integer")
    if size < MIN_IMAGE_BYTES or size > MAX_IMAGE_BYTES:
        raise RamdiskOverrideError(
            f"RAMDisk size must be from {MIN_IMAGE_BYTES} through {MAX_IMAGE_BYTES} bytes"
        )
    if address % ALIGNMENT or size % ALIGNMENT:
        raise RamdiskOverrideError(
            f"RAMDisk address and size must be {ALIGNMENT}-byte aligned"
        )
    memory_end = memory_base + memory_size
    region_end = address + size
    if memory_end > UINT64_LIMIT or region_end > UINT64_LIMIT:
        raise RamdiskOverrideError("RAMDisk or guest memory range overflows uint64")
    if address < memory_base or region_end > memory_end:
        raise RamdiskOverrideError(
            f"RAMDisk [0x{address:x},0x{region_end:x}) is outside guest RAM "
            f"[0x{memory_base:x},0x{memory_end:x})"
        )
    return address, size


def validate_image_path(path: str, *, allowed_root: str) -> tuple[Path, int]:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise RamdiskOverrideError("RAMDisk image path must be absolute")
    if "," in path:
        raise RamdiskOverrideError("RAMDisk image path cannot contain a comma")
    try:
        root = Path(allowed_root).resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise RamdiskOverrideError(f"RAMDisk image path cannot be resolved: {error}") from error
    if resolved != root and root not in resolved.parents:
        raise RamdiskOverrideError(
            f"RAMDisk image must remain inside staged restore root {root}"
        )
    if not resolved.is_file():
        raise RamdiskOverrideError("RAMDisk image is not a regular file")
    if not os.access(resolved, os.R_OK):
        raise RamdiskOverrideError("RAMDisk image is not readable")
    size = resolved.stat().st_size
    return resolved, size


def validate_override(
    *, image: str, address_literal: str, memory_gib: int, allowed_root: str
) -> tuple[Path, int, int]:
    if not 1 <= memory_gib <= 36:
        raise RamdiskOverrideError("guest memory must be from 1 through 36 GiB")
    resolved, size = validate_image_path(image, allowed_root=allowed_root)
    address = parse_u64_literal(address_literal)
    validate_physical_region(
        address=address,
        size=size,
        memory_base=VMAPPLE_RAM_BASE,
        memory_size=memory_gib * GIB,
    )
    return resolved, address, size


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--address", required=True)
    parser.add_argument("--memory-gib", required=True, type=int)
    parser.add_argument("--allowed-root", required=True)
    args = parser.parse_args()
    try:
        resolved, address, size = validate_override(
            image=args.image,
            address_literal=args.address,
            memory_gib=args.memory_gib,
            allowed_root=args.allowed_root,
        )
    except RamdiskOverrideError as error:
        parser.error(str(error))
    print(f"{resolved}\t0x{address:x}\t{size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
