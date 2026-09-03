"""Offline GPT composition for one VMApple primary disk (B016).

No guest launch, filesystem formatting, signature changes or live-image access.
Input APFS containers are opaque: preserve every partition byte and UUID. The
caller must supply closed, verified raw backups, not a live QEMU backing chain.
The AUX utility/NVRAM file remains separate; this tool does not rebind it.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import struct
import subprocess
import uuid
import zlib

from build_vmapple_isc import _parse_gpt_header, _gpt_header, _protective_mbr, fletcher64

SECTOR = 512
ARRAY_BYTES = 16384
ALIGN = 1024 * 1024
ISC = uuid.UUID('69646961-6700-11aa-aa11-00306543ecac')
SYSTEM = uuid.UUID('7c3457ef-0000-11aa-aa11-00306543ecac')
RECOVERY = uuid.UUID('52637672-7900-11aa-aa11-00306543ecac')
EFI = uuid.UUID('c12a7328-f81f-11d2-ba4b-00a0c93ec93b')


@dataclass(frozen=True)
class Partition:
    source: Path
    source_size: int
    source_offset: int
    length: int
    kind: uuid.UUID
    identity: uuid.UUID
    name: str
    container_uuid: uuid.UUID | None


@dataclass(frozen=True)
class Placement:
    partition: Partition
    offset: int


def _regular(stream):
    value = os.fstat(stream.fileno())
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise ValueError('input must be a regular, non-hardlinked raw backup')
    return value


def read_partitions(path: Path) -> tuple[uuid.UUID, tuple[Partition, ...]]:
    """Bounded GPT/NXSB validation. This does not assert APFS health or quiescence."""
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or path.resolve(strict=True) != path:
        raise ValueError('input must be an absolute path without symlink components')
    with path.open('rb') as stream:
        size = _regular(stream).st_size
        if size < ALIGN or size % SECTOR:
            raise ValueError('invalid raw backup size')
        last = size // SECTOR - 1
        mbr = stream.read(SECTOR)
        if mbr[510:512] != b'\x55\xaa' or mbr[450] != 0xee:
            raise ValueError('protective MBR missing')
        stream.seek(SECTOR)
        primary = _parse_gpt_header(stream.read(SECTOR), 1)
        stream.seek(last * SECTOR)
        backup = _parse_gpt_header(stream.read(SECTOR), last)
        if (primary['backup_lba'] != last or backup['backup_lba'] != 1
                or primary['entries_lba'] != 2 or backup['entries_lba'] != last - 32):
            raise ValueError('invalid GPT header/array geometry')
        for key in ('disk_uuid', 'first_usable_lba', 'last_usable_lba'):
            if primary[key] != backup[key]:
                raise ValueError('GPT headers disagree')
        first, final = primary['first_usable_lba'], primary['last_usable_lba']
        if not 34 <= first <= final < last - 32:
            raise ValueError('unsafe usable range')
        arrays = []
        for header in (primary, backup):
            stream.seek(header['entries_lba'] * SECTOR)
            data = stream.read(ARRAY_BYTES)
            if len(data) != ARRAY_BYTES or zlib.crc32(data) & 0xffffffff != header['entries_crc']:
                raise ValueError('partition array checksum mismatch')
            arrays.append(data)
        if arrays[0] != arrays[1]:
            raise ValueError('partition arrays differ')
        result = []
        for at in range(0, ARRAY_BYTES, 128):
            entry = arrays[0][at:at + 128]
            if not any(entry):
                continue
            kind = uuid.UUID(bytes_le=entry[:16])
            identity = uuid.UUID(bytes_le=entry[16:32])
            start, end, attrs = struct.unpack_from('<QQQ', entry, 32)
            if kind not in (ISC, SYSTEM, RECOVERY, EFI) or not identity.int or attrs:
                raise ValueError('unexpected partition type, identity or attributes')
            if not first <= start <= end <= final or start * SECTOR % 4096:
                raise ValueError('invalid partition range or alignment')
            length = (end - start + 1) * SECTOR
            name = entry[56:128].decode('utf-16le').rstrip('\0')
            if '\0' in name:
                raise ValueError('embedded NUL in partition name')
            container = None
            if kind != EFI:
                stream.seek(start * SECTOR)
                nx = stream.read(4096)
                if (length < 4096 or len(nx) != 4096 or nx[32:36] != b'NXSB'
                        or struct.unpack_from('<I', nx, 36)[0] != 4096
                        or struct.unpack_from('<Q', nx)[0] != fletcher64(nx[8:])):
                    raise ValueError('invalid APFS container superblock')
                if not 1 <= struct.unpack_from('<Q', nx, 40)[0] <= length // 4096:
                    raise ValueError('APFS container exceeds partition')
                container = uuid.UUID(bytes=nx[72:88])
                if not container.int:
                    raise ValueError('zero container UUID')
            result.append(Partition(path, size, start * SECTOR, length,
                                    kind, identity, name, container))
        if not result:
            raise ValueError('empty partition table')
        ordered = sorted(result, key=lambda p: p.source_offset)
        if any(a.source_offset + a.length > b.source_offset for a, b in zip(ordered, ordered[1:])):
            raise ValueError('overlapping source partitions')
        if len({p.identity for p in result}) != len(result):
            raise ValueError('duplicate partition UUID')
        return uuid.UUID(primary['disk_uuid']), tuple(result)


def plan_primary_disk(partitions: tuple[Partition, ...]) -> tuple[int, tuple[Placement, ...]]:
    """One iSC, one ordinary APFS store, one Recovery, optional preserved EFI."""
    kinds = [p.kind for p in partitions]
    if (any(kinds.count(kind) != 1 for kind in (ISC, SYSTEM, RECOVERY))
            or kinds.count(EFI) > 1 or len(kinds) != 3 + kinds.count(EFI)):
        raise ValueError('single primary requires exactly iSC/system/Recovery and optional EFI')
    if len({p.identity for p in partitions}) != len(partitions):
        raise ValueError('duplicate partition UUID')
    containers = [p.container_uuid for p in partitions if p.kind != EFI]
    if None in containers or len(set(containers)) != 3:
        raise ValueError('missing or duplicate APFS container UUID')
    # Reserve 32 MiB, matching the existing iSC start; do not copy AUX utility
    # records into the primary GPT or reinterpret them as filesystem content.
    position = 32 * ALIGN
    placements = []
    for kind in (ISC, EFI, SYSTEM, RECOVERY):
        for part in (p for p in partitions if p.kind == kind):
            if (part.length <= 0 or part.length % SECTOR
                    or part.source_offset < 34 * SECTOR or part.source_offset % 4096
                    or part.source_offset + part.length > part.source_size - 33 * SECTOR):
                raise ValueError('invalid opaque source range')
            placements.append(Placement(part, position))
            position = ((position + part.length + ALIGN - 1) // ALIGN) * ALIGN
    size = ((position + 33 * SECTOR + ALIGN - 1) // ALIGN) * ALIGN
    return size, tuple(placements)


def gpt_records(size: int, placements: tuple[Placement, ...], disk_uuid: uuid.UUID):
    """Return only new GPT metadata; no executable or APFS bytes are patched."""
    if size < 34 * ALIGN or size % ALIGN or not disk_uuid.int:
        raise ValueError('invalid output disk geometry/identity')
    # Reject caller-invented/overlapping/out-of-order placements as well.
    expected_size, expected = plan_primary_disk(tuple(p.partition for p in placements))
    if (size, placements) != (expected_size, expected):
        raise ValueError('placements differ from canonical primary-disk plan')
    last = size // SECTOR - 1
    entries = bytearray(ARRAY_BYTES)
    for index, item in enumerate(placements):
        p = item.partition
        name = p.name.encode('utf-16le')
        if len(name) > 72 or '\0' in p.name:
            raise ValueError('invalid GPT name')
        struct.pack_into('<16s16sQQQ72s', entries, index * 128,
                         p.kind.bytes_le, p.identity.bytes_le,
                         item.offset // SECTOR, (item.offset + p.length) // SECTOR - 1,
                         0, name.ljust(72, b'\0'))
    common = dict(last_usable_lba=last - 33, disk_uuid=disk_uuid,
                  entries_crc=zlib.crc32(entries) & 0xffffffff)
    return ((0, _protective_mbr(size // SECTOR)),
            (SECTOR, _gpt_header(current_lba=1, backup_lba=last, entries_lba=2, **common)),
            (2 * SECTOR, bytes(entries)),
            ((last - 32) * SECTOR, bytes(entries)),
            (last * SECTOR, _gpt_header(current_lba=last, backup_lba=1,
                                      entries_lba=last - 32, **common)))


def validate_primary_topology(disks: tuple[tuple[str, bool, tuple[uuid.UUID, ...]], ...]):
    """Reject B016's three root devices even if all required volumes are mounted."""
    if not disks or len({name for name, _, _ in disks}) != len(disks):
        raise ValueError('missing or duplicate disk identity')
    if any(type(primary) is not bool for _, primary, _ in disks):
        raise ValueError('primary classification must be an actual boolean')
    primary = [item for item in disks if item[1]]
    if len(primary) != 1:
        raise ValueError('exactly one EmbeddedDeviceTypeRoot disk required')
    name, _, kinds = primary[0]
    if (any(kinds.count(k) != 1 for k in (ISC, SYSTEM, RECOVERY))
            or kinds.count(EFI) > 1 or len(kinds) != 3 + kinds.count(EFI)):
        raise ValueError('iSC/system/Recovery must be children of the same primary disk')
    if any(k in (ISC, RECOVERY) for _, is_primary, ks in disks if not is_primary for k in ks):
        raise ValueError('ambiguous secondary iSC/Recovery stores')
    return name


def compose_offline(output: Path, sources: tuple[Path, Path, Path], *, closed_backup: bool):
    """Migration primitive for verified CLOSED backups; never a launch command.

    Production CLI activation intentionally does not exist while the user holds
    the next boot. Tests exercise this primitive only against disposable fixtures.
    Output is exclusive, verified and retained on failure, never overwritten.
    """
    guard = Path(__file__).resolve().parents[1] / 'scripts/lib/require-debug-env.sh'
    if os.uname().nodename != 'macvm-validation':
        raise ValueError('composition requires the isolated macvm-validation guest')
    subprocess.run(['bash', '-c', 'source "$1"; macvm_require_debug_env', 'guard', str(guard)], check=True)
    if closed_backup is not True:
        raise ValueError('verified closed backups required; no live migration')
    output = Path(output)
    if (not output.is_absolute() or output.exists() or output.is_symlink()
            or output.parent.resolve(strict=True) != output.parent):
        raise ValueError('output must be a new absolute path without symlink components')
    if len(sources) != 3 or len(set(sources)) != 3 or output in sources:
        raise ValueError('three distinct raw backup inputs required')
    fingerprints = {p: p.lstat() for p in sources}
    parsed = [read_partitions(p) for p in sources]
    # Make callers identify the original sources in semantic order.
    for (_, parts), wanted in zip(parsed, (ISC, SYSTEM, RECOVERY)):
        if sum(p.kind == wanted for p in parts) != 1 or any(
                p.kind != wanted and not (wanted == SYSTEM and p.kind == EFI) for p in parts):
            raise ValueError('input role/order mismatch')
    disk_id = parsed[1][0]  # Preserve the existing installation disk's GPT UUID.
    size, places = plan_primary_disk(tuple(p for _, ps in parsed for p in ps))
    records = gpt_records(size, places, disk_id)
    checksums = []
    with output.open('xb') as dst:
        os.chmod(output, 0o600)
        dst.truncate(size)
        for item in places:
            p = item.partition
            digest = hashlib.sha256()
            if p.source.is_symlink() or p.source.resolve(strict=True) != p.source:
                raise ValueError('backup path changed before copy')
            with p.source.open('rb') as src:
                actual = _regular(src)
                original = fingerprints[p.source]
                if (actual.st_dev, actual.st_ino, actual.st_size, actual.st_mtime_ns, actual.st_ctime_ns) != (
                        original.st_dev, original.st_ino, original.st_size, original.st_mtime_ns, original.st_ctime_ns
                ) or actual.st_size != p.source_size:
                    raise ValueError('backup identity changed before copy')
                src.seek(p.source_offset)
                dst.seek(item.offset)
                remaining = p.length
                while remaining:
                    chunk = src.read(min(ALIGN, remaining))
                    if not chunk:
                        raise ValueError('truncated source partition')
                    digest.update(chunk)
                    if any(chunk):
                        dst.write(chunk)
                    else:
                        dst.seek(len(chunk), os.SEEK_CUR)
                    remaining -= len(chunk)
                after = os.fstat(src.fileno())
                if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
                        actual.st_size, actual.st_mtime_ns, actual.st_ctime_ns):
                    raise ValueError('backup changed during copy')
            checksums.append((item, digest.hexdigest()))
        for offset, data in records:
            dst.seek(offset)
            dst.write(data)
        dst.flush()
        os.fsync(dst.fileno())
    result_id, result_parts = read_partitions(output)
    if result_id != disk_id or [(p.kind, p.identity, p.container_uuid, p.length) for p in result_parts] != [
            (i.partition.kind, i.partition.identity, i.partition.container_uuid, i.partition.length) for i in places]:
        raise ValueError('composed GPT/APFS identity verification failed')
    with output.open('rb') as stream:
        for item, expected in checksums:
            stream.seek(item.offset)
            digest = hashlib.sha256()
            remaining = item.partition.length
            while remaining:
                data = stream.read(min(ALIGN, remaining))
                if not data:
                    raise ValueError('truncated output partition')
                digest.update(data)
                remaining -= len(data)
            if digest.hexdigest() != expected:
                raise ValueError('opaque partition byte verification failed')
    return {'bytes': size, 'disk_uuid': str(disk_id), 'partition_count': len(places),
            'partition_sha256': {str(i.partition.identity): sha for i, sha in checksums},
            'booted': False, 'installed': False, 'sources_modified': False}
