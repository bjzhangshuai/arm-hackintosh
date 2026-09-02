#!/usr/bin/env python3
"""Build and inspect a VMApple iSC disk containing an APFS xART volume."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
from typing import Callable
import uuid
import zlib


SECTOR_SIZE = 512
APFS_BLOCK_SIZE = 4096
DEFAULT_SIZE_MIB = 64
GPT_HEADER_SIZE = 92
GPT_ENTRY_SIZE = 128
GPT_ENTRY_COUNT = 128
GPT_ENTRY_ARRAY_BYTES = GPT_ENTRY_SIZE * GPT_ENTRY_COUNT
GPT_ENTRY_ARRAY_SECTORS = GPT_ENTRY_ARRAY_BYTES // SECTOR_SIZE
PRIMARY_HEADER_LBA = 1
PRIMARY_ENTRIES_LBA = 2
FIRST_USABLE_LBA = 34

# Apple firmware treats AUX as more than a conventional partitioned disk.  It
# writes NVRAM, UMPv, PEEP, and panic-log records at fixed offsets before XNU
# mounts the iSC APFS volume.  Boot39 observed the highest such write ending at
# 0x01506000.  Keep a deliberately rounded 32 MiB prefix outside the APFS
# partition so those writes cannot corrupt an otherwise checksum-valid xART
# container when pflash and Apple's AUX virtio function share one backing file.
AUX_FIXED_METADATA_END = 0x01506000
AUX_RESERVED_BYTES = 32 * 1024 * 1024
PARTITION_START_LBA = AUX_RESERVED_BYTES // SECTOR_SIZE

# apfs_boot_util's iSC lookup uses this GPT content-hint UUID before looking
# for an AppleAPFSVolume whose on-disk role is xART (0x100).
ISC_PARTITION_TYPE = uuid.UUID("69646961-6700-11aa-aa11-00306543ecac")
APFS_VOL_ROLE_NONE = 0x0000
APFS_VOL_ROLE_XART = 0x0100
APFS_VOL_ROLE_PREBOOT = 0x0010
APFS_VOL_ROLE_HARDWARE = 0x0140
APFS_OBJECT_TYPE_FS = 0x000D

DEFAULT_DISK_UUID = uuid.UUID("af8164aa-893b-5fb9-b41a-9ef75f8863da")
DEFAULT_PARTITION_UUID = uuid.UUID("4d3ea4f4-d4a8-5890-bb4e-c61a14268c91")
DEFAULT_CONTAINER_UUID = uuid.UUID("4045fa42-d0e8-57fd-8623-bd2064ed6f34")
DEFAULT_VOLUME_UUID = uuid.UUID("ea5e8110-838d-5aba-9c32-6656f94a3113")

APFS_OBJECT_CHECKSUM_OFFSET = 0x00
APFS_OBJECT_TYPE_OFFSET = 0x18
APFS_MAGIC_OFFSET = 0x20
APFS_VOLUME_UUID_OFFSET = 0xF0
APFS_VOLUME_NAME_OFFSET = 0x2C0
APFS_VOLUME_NAME_LENGTH = 0x100
APFS_VOLUME_ROLE_OFFSET = 0x3C4


class ISCImageError(ValueError):
    """The requested iSC image is unsafe or structurally invalid."""


def require_validation_environment() -> None:
    if os.environ.get("MACVM_DEBUG_ENV_CONFIRMED") != "YES":
        raise ISCImageError(
            "set MACVM_DEBUG_ENV_CONFIRMED=YES only inside the isolated validation VM"
        )
    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        raise ISCImageError("VMApple iSC images may only be built in the Linux x86_64 validation VM")


def fletcher64(data: bytes) -> int:
    """Return the APFS Fletcher-64 checksum for bytes following o_cksum."""

    if len(data) % 4:
        raise ISCImageError("APFS checksum input length must be divisible by four")
    modulus = 0xFFFFFFFF
    sum1 = 0
    sum2 = 0
    for (word,) in struct.iter_unpack("<I", data):
        sum1 += word
        sum2 += sum1
    check1 = modulus - ((sum1 + sum2) % modulus)
    check2 = modulus - ((sum1 + check1) % modulus)
    return (check2 << 32) | check1


def _checked_uuid(value: uuid.UUID | str, label: str) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
    except (AttributeError, ValueError) as error:
        raise ISCImageError(f"invalid {label}: {value}") from error


def _volume_name(block: bytes) -> str:
    raw = block[
        APFS_VOLUME_NAME_OFFSET : APFS_VOLUME_NAME_OFFSET + APFS_VOLUME_NAME_LENGTH
    ].split(b"\0", 1)[0]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ISCImageError("APFS volume name is not valid UTF-8") from error


def _scan_apfs_volume_superblocks(
    image: Path, *, base_offset: int = 0, length: int | None = None
) -> list[dict[str, object]]:
    size = image.stat().st_size
    if base_offset < 0 or base_offset % APFS_BLOCK_SIZE:
        raise ISCImageError("APFS base offset must be non-negative and block aligned")
    if length is None:
        length = size - base_offset
    if length <= 0 or length % APFS_BLOCK_SIZE or base_offset + length > size:
        raise ISCImageError("APFS region must be non-empty, block aligned, and inside the image")

    found: list[dict[str, object]] = []
    with image.open("rb") as stream:
        stream.seek(base_offset)
        for relative_offset in range(0, length, APFS_BLOCK_SIZE):
            block = stream.read(APFS_BLOCK_SIZE)
            if len(block) != APFS_BLOCK_SIZE:
                raise ISCImageError("APFS image ended in the middle of a block")
            if block[APFS_MAGIC_OFFSET : APFS_MAGIC_OFFSET + 4] != b"APSB":
                continue
            object_type = struct.unpack_from("<I", block, APFS_OBJECT_TYPE_OFFSET)[0]
            if object_type & 0xFFFF != APFS_OBJECT_TYPE_FS:
                continue
            stored_checksum = struct.unpack_from(
                "<Q", block, APFS_OBJECT_CHECKSUM_OFFSET
            )[0]
            calculated_checksum = fletcher64(block[8:])
            if stored_checksum != calculated_checksum:
                raise ISCImageError(
                    f"APFS volume superblock at 0x{base_offset + relative_offset:x} "
                    "has an invalid checksum"
                )
            found.append(
                {
                    "offset": base_offset + relative_offset,
                    "uuid": str(
                        uuid.UUID(bytes=block[APFS_VOLUME_UUID_OFFSET : APFS_VOLUME_UUID_OFFSET + 16])
                    ),
                    "name": _volume_name(block),
                    "role": struct.unpack_from("<H", block, APFS_VOLUME_ROLE_OFFSET)[0],
                }
            )
    if not found:
        raise ISCImageError("no checksum-valid APFS volume superblock was found")
    return found


def patch_apfs_xart_role(image: Path) -> list[int]:
    """Set every checkpoint copy of one APFS volume to the xART role."""

    image = Path(image)
    superblocks = _scan_apfs_volume_superblocks(image)
    volume_uuids = {item["uuid"] for item in superblocks}
    if len(volume_uuids) != 1:
        raise ISCImageError("APFS image contains superblocks for more than one volume")
    unexpected = {
        int(item["role"])
        for item in superblocks
        if int(item["role"]) not in {APFS_VOL_ROLE_NONE, APFS_VOL_ROLE_XART}
    }
    if unexpected:
        roles = ", ".join(f"0x{role:x}" for role in sorted(unexpected))
        raise ISCImageError(f"refusing to replace existing APFS volume role(s): {roles}")

    offsets = [int(item["offset"]) for item in superblocks]
    with image.open("r+b") as stream:
        for offset in offsets:
            stream.seek(offset)
            block = bytearray(stream.read(APFS_BLOCK_SIZE))
            if len(block) != APFS_BLOCK_SIZE:
                raise ISCImageError("APFS image changed while applying the xART role")
            struct.pack_into("<H", block, APFS_VOLUME_ROLE_OFFSET, APFS_VOL_ROLE_XART)
            struct.pack_into("<Q", block, APFS_OBJECT_CHECKSUM_OFFSET, fletcher64(block[8:]))
            stream.seek(offset)
            stream.write(block)
        stream.flush()
        os.fsync(stream.fileno())

    verified = _scan_apfs_volume_superblocks(image)
    if any(int(item["role"]) != APFS_VOL_ROLE_XART for item in verified):
        raise ISCImageError("xART role did not persist in every APFS checkpoint")
    return offsets


def _layout(size_bytes: int) -> dict[str, int]:
    if AUX_RESERVED_BYTES % APFS_BLOCK_SIZE:
        raise ISCImageError("AUX reserved prefix must be APFS-block aligned")
    if AUX_RESERVED_BYTES <= AUX_FIXED_METADATA_END:
        raise ISCImageError("AUX reserved prefix overlaps Apple fixed metadata")
    if size_bytes % SECTOR_SIZE:
        raise ISCImageError("iSC image size must be divisible by 512 bytes")
    total_lbas = size_bytes // SECTOR_SIZE
    last_lba = total_lbas - 1
    backup_entries_lba = last_lba - GPT_ENTRY_ARRAY_SECTORS
    last_usable_lba = backup_entries_lba - 1
    if PARTITION_START_LBA > last_usable_lba:
        raise ISCImageError("iSC image is too small for an aligned APFS partition")
    # GPT's usable range ends immediately before the backup partition array,
    # which is normally seven 512-byte sectors past a 4 KiB boundary.  APFS
    # requires a whole number of 4 KiB blocks, so leave those trailing usable
    # sectors unallocated instead of giving mkapfs a misaligned container.
    apfs_sectors_per_block = APFS_BLOCK_SIZE // SECTOR_SIZE
    partition_blocks = last_usable_lba - PARTITION_START_LBA + 1
    partition_blocks -= partition_blocks % apfs_sectors_per_block
    partition_last_lba = PARTITION_START_LBA + partition_blocks - 1
    partition_bytes = partition_blocks * SECTOR_SIZE
    if (
        partition_blocks <= 0
        or partition_bytes < 512 * 1024
        or partition_bytes % APFS_BLOCK_SIZE
    ):
        raise ISCImageError("iSC APFS partition is too small or not APFS-block aligned")
    return {
        "size_bytes": size_bytes,
        "total_lbas": total_lbas,
        "last_lba": last_lba,
        "backup_entries_lba": backup_entries_lba,
        "last_usable_lba": last_usable_lba,
        "partition_start_lba": PARTITION_START_LBA,
        "partition_last_lba": partition_last_lba,
        "partition_bytes": partition_bytes,
    }


def _gpt_header(
    *,
    current_lba: int,
    backup_lba: int,
    last_usable_lba: int,
    disk_uuid: uuid.UUID,
    entries_lba: int,
    entries_crc: int,
) -> bytes:
    header = bytearray(SECTOR_SIZE)
    struct.pack_into(
        "<8sIIIIQQQQ16sQIII",
        header,
        0,
        b"EFI PART",
        0x00010000,
        GPT_HEADER_SIZE,
        0,
        0,
        current_lba,
        backup_lba,
        FIRST_USABLE_LBA,
        last_usable_lba,
        disk_uuid.bytes_le,
        entries_lba,
        GPT_ENTRY_COUNT,
        GPT_ENTRY_SIZE,
        entries_crc,
    )
    crc = zlib.crc32(header[:GPT_HEADER_SIZE]) & 0xFFFFFFFF
    struct.pack_into("<I", header, 16, crc)
    return bytes(header)


def _protective_mbr(total_lbas: int) -> bytes:
    mbr = bytearray(SECTOR_SIZE)
    struct.pack_into(
        "<B3sB3sII",
        mbr,
        446,
        0,
        b"\x00\x02\x00",
        0xEE,
        b"\xff\xff\xff",
        1,
        min(total_lbas - 1, 0xFFFFFFFF),
    )
    mbr[510:512] = b"\x55\xaa"
    return bytes(mbr)


def _partition_entries(
    layout: dict[str, int], partition_uuid: uuid.UUID
) -> bytes:
    entries = bytearray(GPT_ENTRY_ARRAY_BYTES)
    name = "VMApple iSC".encode("utf-16le")
    struct.pack_into(
        "<16s16sQQQ72s",
        entries,
        0,
        ISC_PARTITION_TYPE.bytes_le,
        partition_uuid.bytes_le,
        layout["partition_start_lba"],
        layout["partition_last_lba"],
        0,
        name.ljust(72, b"\0"),
    )
    return bytes(entries)


def _write_gpt_image(
    output: Path,
    apfs_container: Path,
    *,
    size_bytes: int,
    disk_uuid: uuid.UUID,
    partition_uuid: uuid.UUID,
) -> None:
    layout = _layout(size_bytes)
    if apfs_container.stat().st_size != layout["partition_bytes"]:
        raise ISCImageError("APFS container size does not match the GPT partition")
    entries = _partition_entries(layout, partition_uuid)
    entries_crc = zlib.crc32(entries) & 0xFFFFFFFF
    primary_header = _gpt_header(
        current_lba=PRIMARY_HEADER_LBA,
        backup_lba=layout["last_lba"],
        last_usable_lba=layout["last_usable_lba"],
        disk_uuid=disk_uuid,
        entries_lba=PRIMARY_ENTRIES_LBA,
        entries_crc=entries_crc,
    )
    backup_header = _gpt_header(
        current_lba=layout["last_lba"],
        backup_lba=PRIMARY_HEADER_LBA,
        last_usable_lba=layout["last_usable_lba"],
        disk_uuid=disk_uuid,
        entries_lba=layout["backup_entries_lba"],
        entries_crc=entries_crc,
    )

    with output.open("xb") as stream:
        stream.truncate(size_bytes)
        stream.seek(0)
        stream.write(_protective_mbr(layout["total_lbas"]))
        stream.seek(PRIMARY_HEADER_LBA * SECTOR_SIZE)
        stream.write(primary_header)
        stream.seek(PRIMARY_ENTRIES_LBA * SECTOR_SIZE)
        stream.write(entries)
        stream.seek(layout["partition_start_lba"] * SECTOR_SIZE)
        with apfs_container.open("rb") as source:
            shutil.copyfileobj(source, stream, length=1024 * 1024)
        stream.seek(layout["backup_entries_lba"] * SECTOR_SIZE)
        stream.write(entries)
        stream.seek(layout["last_lba"] * SECTOR_SIZE)
        stream.write(backup_header)
        stream.flush()
        os.fsync(stream.fileno())


def _parse_gpt_header(block: bytes, expected_lba: int) -> dict[str, object]:
    if len(block) != SECTOR_SIZE:
        raise ISCImageError("truncated GPT header")
    fields = struct.unpack_from("<8sIIIIQQQQ16sQIII", block, 0)
    (
        signature,
        revision,
        header_size,
        stored_crc,
        reserved,
        current_lba,
        backup_lba,
        first_usable_lba,
        last_usable_lba,
        disk_uuid_bytes,
        entries_lba,
        entry_count,
        entry_size,
        entries_crc,
    ) = fields
    if signature != b"EFI PART" or revision != 0x00010000:
        raise ISCImageError("invalid GPT signature or revision")
    if header_size != GPT_HEADER_SIZE or reserved != 0 or current_lba != expected_lba:
        raise ISCImageError("invalid GPT header geometry")
    checked = bytearray(block[:header_size])
    struct.pack_into("<I", checked, 16, 0)
    if zlib.crc32(checked) & 0xFFFFFFFF != stored_crc:
        raise ISCImageError("GPT header checksum mismatch")
    if entry_count != GPT_ENTRY_COUNT or entry_size != GPT_ENTRY_SIZE:
        raise ISCImageError("unsupported GPT partition-entry geometry")
    return {
        "current_lba": current_lba,
        "backup_lba": backup_lba,
        "first_usable_lba": first_usable_lba,
        "last_usable_lba": last_usable_lba,
        "disk_uuid": str(uuid.UUID(bytes_le=disk_uuid_bytes)),
        "entries_lba": entries_lba,
        "entries_crc": entries_crc,
    }


def validate_isc_volumes(superblocks: list[dict[str, object]]) -> list[dict[str, object]]:
    """Accept the legacy xART-only template or the complete reviewed iSC set."""
    expected = {APFS_VOL_ROLE_XART: "xART", APFS_VOL_ROLE_PREBOOT: "iSCPreboot",
                APFS_VOL_ROLE_HARDWARE: "Hardware"}
    roles = {int(item["role"]) for item in superblocks}
    if roles not in ({APFS_VOL_ROLE_XART}, set(expected)):
        raise ISCImageError("iSC APFS volume is not consistently marked as xART or complete iSC")
    volumes = []
    seen = set()
    for role in sorted(roles):
        copies = [item for item in superblocks if int(item["role"]) == role]
        ids = {str(item["uuid"]) for item in copies}
        if len(ids) != 1 or {item["name"] for item in copies} != {expected[role]}:
            raise ISCImageError("iSC APFS checkpoint metadata is inconsistent")
        volume_id = next(iter(ids))
        if volume_id in seen:
            raise ISCImageError("iSC volume UUID reused across roles")
        seen.add(volume_id)
        volumes.append({"uuid": volume_id, "name": expected[role], "role": role})
    return volumes


def inspect_isc_image(image: Path) -> dict[str, object]:
    image = Path(image)
    size = image.stat().st_size
    layout = _layout(size)
    with image.open("rb") as stream:
        mbr = stream.read(SECTOR_SIZE)
        if mbr[510:512] != b"\x55\xaa" or mbr[450] != 0xEE:
            raise ISCImageError("protective MBR is missing")
        stream.seek(PRIMARY_HEADER_LBA * SECTOR_SIZE)
        primary = _parse_gpt_header(stream.read(SECTOR_SIZE), PRIMARY_HEADER_LBA)
        stream.seek(int(primary["entries_lba"]) * SECTOR_SIZE)
        primary_entries = stream.read(GPT_ENTRY_ARRAY_BYTES)
        if zlib.crc32(primary_entries) & 0xFFFFFFFF != int(primary["entries_crc"]):
            raise ISCImageError("primary GPT partition-array checksum mismatch")
        stream.seek(layout["last_lba"] * SECTOR_SIZE)
        backup = _parse_gpt_header(stream.read(SECTOR_SIZE), layout["last_lba"])
        stream.seek(int(backup["entries_lba"]) * SECTOR_SIZE)
        backup_entries = stream.read(GPT_ENTRY_ARRAY_BYTES)
        if zlib.crc32(backup_entries) & 0xFFFFFFFF != int(backup["entries_crc"]):
            raise ISCImageError("backup GPT partition-array checksum mismatch")
    if primary_entries != backup_entries:
        raise ISCImageError("primary and backup GPT partition arrays differ")
    if primary["backup_lba"] != layout["last_lba"] or backup["backup_lba"] != 1:
        raise ISCImageError("primary and backup GPT headers do not reference each other")
    if (
        int(primary["entries_lba"]) != PRIMARY_ENTRIES_LBA
        or int(backup["entries_lba"]) != layout["backup_entries_lba"]
    ):
        raise ISCImageError("GPT partition-array locations do not match the disk geometry")
    if primary["disk_uuid"] != backup["disk_uuid"]:
        raise ISCImageError("primary and backup GPT disk UUIDs differ")
    if (
        int(primary["first_usable_lba"]) != FIRST_USABLE_LBA
        or int(primary["last_usable_lba"]) != layout["last_usable_lba"]
        or int(backup["first_usable_lba"]) != FIRST_USABLE_LBA
        or int(backup["last_usable_lba"]) != layout["last_usable_lba"]
    ):
        raise ISCImageError("GPT usable range does not match the disk geometry")

    populated: list[bytes] = []
    for offset in range(0, GPT_ENTRY_ARRAY_BYTES, GPT_ENTRY_SIZE):
        entry = primary_entries[offset : offset + GPT_ENTRY_SIZE]
        if entry[:16] != bytes(16):
            populated.append(entry)
    if len(populated) != 1:
        raise ISCImageError("iSC image must contain exactly one GPT partition")
    type_bytes, unique_bytes, first_lba, last_lba, attributes, name_bytes = struct.unpack(
        "<16s16sQQQ72s", populated[0]
    )
    if uuid.UUID(bytes_le=type_bytes) != ISC_PARTITION_TYPE:
        raise ISCImageError("iSC partition uses the wrong GPT type UUID")
    if first_lba != PARTITION_START_LBA or last_lba != layout["partition_last_lba"]:
        raise ISCImageError("iSC partition is not at the expected aligned range")
    if attributes != 0:
        raise ISCImageError("iSC partition has unexpected GPT attributes")
    try:
        partition_name = name_bytes.decode("utf-16le").rstrip("\0")
    except UnicodeDecodeError as error:
        raise ISCImageError("iSC GPT partition name is invalid") from error

    partition_offset = first_lba * SECTOR_SIZE
    with image.open("rb") as stream:
        stream.seek(partition_offset + APFS_MAGIC_OFFSET)
        if stream.read(4) != b"NXSB":
            raise ISCImageError("iSC partition does not begin with an APFS container")
    superblocks = _scan_apfs_volume_superblocks(
        image, base_offset=partition_offset, length=layout["partition_bytes"]
    )
    volumes = validate_isc_volumes(superblocks)
    xart = next(item for item in volumes if item["role"] == APFS_VOL_ROLE_XART)

    return {
        "size_bytes": size,
        "disk_uuid": primary["disk_uuid"],
        "partition_type": str(ISC_PARTITION_TYPE),
        "partition_uuid": str(uuid.UUID(bytes_le=unique_bytes)),
        "partition_name": partition_name,
        "partition_start_lba": first_lba,
        "partition_last_lba": last_lba,
        "apfs_volume_uuid": xart["uuid"],
        "apfs_volume_name": "xART",
        "apfs_role": APFS_VOL_ROLE_XART,
        "apfs_superblock_count": len(superblocks),
        "apfs_volumes": volumes,
    }


def _run_mkapfs(
    image: Path,
    *,
    executable: str,
    container_uuid: uuid.UUID,
    volume_uuid: uuid.UUID,
) -> None:
    resolved = shutil.which(executable) if "/" not in executable else executable
    if not resolved or not os.access(resolved, os.X_OK):
        raise ISCImageError(f"mkapfs executable is missing: {executable}")
    result = subprocess.run(
        [
            resolved,
            "-L",
            "xART",
            "-U",
            str(container_uuid),
            "-u",
            str(volume_uuid),
            str(image),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise ISCImageError(f"mkapfs failed with exit code {result.returncode}: {detail}")


MkfsRunner = Callable[[Path, uuid.UUID, uuid.UUID], None]


def build_isc_image(
    output: Path,
    *,
    size_mib: int = DEFAULT_SIZE_MIB,
    mkapfs: str = "/usr/sbin/mkapfs",
    disk_uuid: uuid.UUID | str = DEFAULT_DISK_UUID,
    partition_uuid: uuid.UUID | str = DEFAULT_PARTITION_UUID,
    container_uuid: uuid.UUID | str = DEFAULT_CONTAINER_UUID,
    volume_uuid: uuid.UUID | str = DEFAULT_VOLUME_UUID,
    mkfs_runner: MkfsRunner | None = None,
) -> dict[str, object]:
    output = Path(output)
    if output.exists():
        raise ISCImageError(f"refusing to overwrite existing output: {output}")
    if not output.parent.is_dir():
        raise ISCImageError(f"output directory does not exist: {output.parent}")
    if not isinstance(size_mib, int) or size_mib <= 0:
        raise ISCImageError("size_mib must be a positive integer")

    size_bytes = size_mib * 1024 * 1024
    layout = _layout(size_bytes)
    disk_id = _checked_uuid(disk_uuid, "disk UUID")
    partition_id = _checked_uuid(partition_uuid, "partition UUID")
    container_id = _checked_uuid(container_uuid, "container UUID")
    volume_id = _checked_uuid(volume_uuid, "volume UUID")

    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as temp_name:
        temp = Path(temp_name)
        container = temp / "xart.apfs"
        with container.open("xb") as stream:
            stream.truncate(layout["partition_bytes"])
        if mkfs_runner is None:
            _run_mkapfs(
                container,
                executable=mkapfs,
                container_uuid=container_id,
                volume_uuid=volume_id,
            )
        else:
            mkfs_runner(container, container_id, volume_id)
        if container.stat().st_size != layout["partition_bytes"]:
            raise ISCImageError("mkapfs changed the requested APFS container size")
        patch_apfs_xart_role(container)

        staging = temp / "isc.img"
        _write_gpt_image(
            staging,
            container,
            size_bytes=size_bytes,
            disk_uuid=disk_id,
            partition_uuid=partition_id,
        )
        details = inspect_isc_image(staging)
        try:
            os.link(staging, output)
        except FileExistsError as error:
            raise ISCImageError(f"refusing to overwrite existing output: {output}") from error
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    return details


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="build a new iSC image without overwriting")
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--size-mib", type=int, default=DEFAULT_SIZE_MIB)
    build.add_argument("--mkapfs", default="/usr/sbin/mkapfs")
    build.add_argument("--disk-uuid", default=str(DEFAULT_DISK_UUID))
    build.add_argument("--partition-uuid", default=str(DEFAULT_PARTITION_UUID))
    build.add_argument("--container-uuid", default=str(DEFAULT_CONTAINER_UUID))
    build.add_argument("--volume-uuid", default=str(DEFAULT_VOLUME_UUID))
    inspect = subparsers.add_parser("inspect", help="validate an existing iSC image")
    inspect.add_argument("image", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        require_validation_environment()
        if args.command == "build":
            details = build_isc_image(
                args.output,
                size_mib=args.size_mib,
                mkapfs=args.mkapfs,
                disk_uuid=args.disk_uuid,
                partition_uuid=args.partition_uuid,
                container_uuid=args.container_uuid,
                volume_uuid=args.volume_uuid,
            )
        else:
            details = inspect_isc_image(args.image)
    except (ISCImageError, OSError) as error:
        print(f"macvm: iSC image error: {error}", file=os.sys.stderr)
        return 1
    print(json.dumps(details, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
