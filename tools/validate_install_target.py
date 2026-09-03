#!/usr/bin/env python3
"""Read-only identity gate for the existing Boot119 installation image.

This is not fsck or a claim that an OS is installed. Check only GPT geometry and
the immutable APFS container identity before connecting the disk read-write.
No formatting, mounting, role modification, or image creation is performed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import stat
import struct
import subprocess
import uuid
import zlib

from build_vmapple_isc import _parse_gpt_header, fletcher64

DATA_ROOT = Path('/home/macvm/installation-data')
TARGET = DATA_ROOT / 'macos-26-system.raw'
TARGET_BYTES = 137438953472
CONTAINER_UUID = '6c0d6e74-ebbb-4a40-a7f1-afde0a1b34fd'
DATA_UUID = '432e46d4-88c5-4885-bf16-1ecdb0f90ba5'
APFS = uuid.UUID('7c3457ef-0000-11aa-aa11-00306543ecac')
EFI = uuid.UUID('c12a7328-f81f-11d2-ba4b-00a0c93ec93b')
SECTOR = 512
ARRAY_BYTES = 16384


def inspect_image(image: Path, expected_bytes: int, expected_uuid: str) -> dict:
    """Bounded reads; fixtures can use a small synthetic disk in isolated tests."""
    if expected_bytes < 1024 * 1024 or expected_bytes % SECTOR:
        raise ValueError('invalid expected image size')
    if image.is_symlink():
        raise ValueError('symlink image is not allowed')
    with image.open('rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('image must be a regular, non-hardlinked file')
        if info.st_size != expected_bytes:
            raise ValueError('image capacity mismatch')
        last = expected_bytes // SECTOR - 1
        stream.seek(SECTOR)
        primary = _parse_gpt_header(stream.read(SECTOR), 1)
        stream.seek(last * SECTOR)
        backup = _parse_gpt_header(stream.read(SECTOR), last)
        if primary['backup_lba'] != last or backup['backup_lba'] != 1:
            raise ValueError('GPT headers do not reference each other')
        if primary['entries_lba'] != 2 or backup['entries_lba'] != last - 32:
            raise ValueError('unexpected GPT array positions')
        for key in ('disk_uuid', 'first_usable_lba', 'last_usable_lba'):
            if primary[key] != backup[key]:
                raise ValueError('GPT headers disagree')
        first_use, last_use = primary['first_usable_lba'], primary['last_usable_lba']
        if not 34 <= first_use <= last_use < last - 32:
            raise ValueError('unsafe GPT usable range')
        arrays = []
        for header in (primary, backup):
            stream.seek(header['entries_lba'] * SECTOR)
            entries = stream.read(ARRAY_BYTES)
            if len(entries) != ARRAY_BYTES or zlib.crc32(entries) & 0xffffffff != header['entries_crc']:
                raise ValueError('GPT array checksum mismatch')
            arrays.append(entries)
        if arrays[0] != arrays[1]:
            raise ValueError('GPT arrays differ')
        parts = []
        for offset in range(0, ARRAY_BYTES, 128):
            entry = arrays[0][offset:offset + 128]
            if not any(entry[:16]):
                continue
            kind = uuid.UUID(bytes_le=entry[:16])
            start, end, attrs = struct.unpack_from('<QQQ', entry, 32)
            if kind not in (EFI, APFS) or attrs != 0:
                raise ValueError('unexpected partition type or attributes')
            if not first_use <= start <= end <= last_use:
                raise ValueError('partition exceeds usable range')
            parts.append((start, end, kind))
        ordered = sorted(parts)
        if any(a[1] >= b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('overlapping partitions')
        stores = [p for p in parts if p[2] == APFS]
        if len(stores) != 1 or sum(p[2] == EFI for p in parts) > 1:
            raise ValueError('expected exactly one normal APFS physical store')
        start, end, _ = stores[0]
        if (end - start + 1) * SECTOR < 4096:
            raise ValueError('APFS store too small')
        stream.seek(start * SECTOR)
        nx = stream.read(4096)
        if nx[32:36] != b'NXSB' or struct.unpack_from('<I', nx, 36)[0] != 4096:
            raise ValueError('missing 4 KiB APFS container superblock')
        if struct.unpack_from('<Q', nx)[0] != fletcher64(nx[8:]):
            raise ValueError('APFS container checksum mismatch')
        container_uuid = str(uuid.UUID(bytes=nx[72:88]))
        if container_uuid != str(uuid.UUID(expected_uuid)):
            raise ValueError('APFS container identity mismatch')
        block_count = struct.unpack_from('<Q', nx, 40)[0]
        if not 1 <= block_count <= ((end - start + 1) * SECTOR) // 4096:
            raise ValueError('APFS container exceeds physical store')
        return {'image': str(image), 'bytes': info.st_size,
                'disk_uuid': primary['disk_uuid'], 'container_uuid': container_uuid,
                'apfs_start_lba': start, 'apfs_end_lba': end,
                'read_only_inspection': True, 'filesystem_health_checked': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    args = parser.parse_args()
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or platform.node() != 'macvm-validation'
            or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'):
        raise ValueError('requires isolated Linux validation guest')
    guard = Path(__file__).resolve().parents[1] / 'scripts/lib/require-debug-env.sh'
    subprocess.run(['bash', '-c', 'source "$1"; macvm_require_debug_env', 'guard', str(guard)], check=True)
    mount_uuid = subprocess.check_output(
        ['findmnt', '-n', '-o', 'UUID', '--mountpoint', str(DATA_ROOT)], text=True).strip()
    if mount_uuid != DATA_UUID:
        raise ValueError('approved data filesystem identity mismatch')
    if args.image != TARGET or args.image.resolve(strict=True) != TARGET:
        raise ValueError('only the existing approved installation image is allowed')
    print(json.dumps(inspect_image(args.image, TARGET_BYTES, CONTAINER_UUID), indent=2))


if __name__ == '__main__':
    main()
