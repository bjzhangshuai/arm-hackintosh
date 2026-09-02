#!/usr/bin/env python3
"""Build and inspect a read-only VMApple APFS Recovery disk.

The source is an existing, unencrypted APFS container whose files must be
preserved (for example the validated RestoreRamDisk used by the recovery
chain).  The builder copies that container, gives it an independent container
and volume identity, marks every volume-superblock checkpoint as Recovery,
and wraps it in a GPT partition whose Content UUID is Apple's System Recovery
type.  It never mutates or overwrites the source or an existing output.
"""

from __future__ import annotations

import argparse
import json
import mmap
import os
from pathlib import Path
import platform
import shutil
import struct
import tempfile
import uuid
import zlib


SECTOR_SIZE = 512
APFS_BLOCK_SIZE = 4096
GPT_HEADER_SIZE = 92
GPT_ENTRY_SIZE = 128
GPT_ENTRY_COUNT = 128
GPT_ENTRY_ARRAY_BYTES = GPT_ENTRY_SIZE * GPT_ENTRY_COUNT
GPT_ENTRY_ARRAY_SECTORS = GPT_ENTRY_ARRAY_BYTES // SECTOR_SIZE
PRIMARY_HEADER_LBA = 1
PRIMARY_ENTRIES_LBA = 2
FIRST_USABLE_LBA = 34
PARTITION_START_LBA = 2048

# This is the value that macOS 26 prebootensurer compares with the IOMedia
# "Content" property while deciding whether a Recovery volume belongs to the
# System Recovery container.
RECOVERY_PARTITION_TYPE = uuid.UUID("52637672-7900-11aa-aa11-00306543ecac")
APFS_VOL_ROLE_NONE = 0x0000
APFS_VOL_ROLE_RECOVERY = 0x0004
APFS_OBJECT_TYPE_NX_SUPERBLOCK = 0x0001
APFS_OBJECT_TYPE_FS = 0x000D

APFS_OBJECT_CHECKSUM_OFFSET = 0x00
APFS_OBJECT_XID_OFFSET = 0x10
APFS_OBJECT_TYPE_OFFSET = 0x18
APFS_MAGIC_OFFSET = 0x20
APFS_CONTAINER_UUID_OFFSET = 0x48
APFS_VOLUME_UUID_OFFSET = 0xF0
APFS_VOLUME_NAME_OFFSET = 0x2C0
APFS_VOLUME_NAME_LENGTH = 0x100
APFS_VOLUME_ROLE_OFFSET = 0x3C4

_IDENTITY_NAMESPACE = uuid.UUID("55c3f1a8-e1af-4966-bc6b-0d3c5bc01dc8")
DEFAULT_DISK_UUID = uuid.uuid5(_IDENTITY_NAMESPACE, "macvm-recovery-disk")
DEFAULT_PARTITION_UUID = uuid.uuid5(_IDENTITY_NAMESPACE, "macvm-recovery-partition")
DEFAULT_CONTAINER_UUID = uuid.uuid5(_IDENTITY_NAMESPACE, "macvm-recovery-container")
DEFAULT_VOLUME_UUID = uuid.uuid5(_IDENTITY_NAMESPACE, "macvm-recovery-volume")
DEFAULT_VOLUME_NAME = "Recovery"


class RecoveryImageError(ValueError):
    """The requested Recovery image is unsafe or structurally invalid."""


def require_validation_environment() -> None:
    if os.environ.get("MACVM_DEBUG_ENV_CONFIRMED") != "YES":
        raise RecoveryImageError(
            "set MACVM_DEBUG_ENV_CONFIRMED=YES only inside the isolated validation VM"
        )
    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        raise RecoveryImageError(
            "VMApple Recovery images may only be built in the Linux x86_64 validation VM"
        )


def _checked_uuid(value: uuid.UUID | str, label: str) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
    except (AttributeError, ValueError) as error:
        raise RecoveryImageError(f"invalid {label}: {value}") from error


def fletcher64(data: bytes) -> int:
    """Return the APFS Fletcher-64 checksum for bytes following o_cksum."""

    if len(data) % 4:
        raise RecoveryImageError("APFS checksum input length must be divisible by four")
    modulus = 0xFFFFFFFF
    sum1 = 0
    sum2 = 0
    for (word,) in struct.iter_unpack("<I", data):
        sum1 += word
        sum2 += sum1
    check1 = modulus - ((sum1 + sum2) % modulus)
    check2 = modulus - ((sum1 + check1) % modulus)
    return (check2 << 32) | check1


def _decode_volume_name(block: bytes) -> str:
    raw = block[
        APFS_VOLUME_NAME_OFFSET : APFS_VOLUME_NAME_OFFSET + APFS_VOLUME_NAME_LENGTH
    ].split(b"\0", 1)[0]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RecoveryImageError("APFS volume name is not valid UTF-8") from error


def _scan_apfs_superblocks(
    image: Path, *, base_offset: int = 0, length: int | None = None
) -> dict[str, list[dict[str, object]]]:
    image = Path(image)
    size = image.stat().st_size
    if base_offset < 0 or base_offset % APFS_BLOCK_SIZE:
        raise RecoveryImageError("APFS base offset must be non-negative and block aligned")
    if length is None:
        length = size - base_offset
    if (
        length < 2 * APFS_BLOCK_SIZE
        or length % APFS_BLOCK_SIZE
        or base_offset + length > size
    ):
        raise RecoveryImageError(
            "APFS region must be block aligned, non-trivial, and inside the image"
        )

    containers: list[dict[str, object]] = []
    volumes: list[dict[str, object]] = []
    with image.open("rb") as stream:
        mapped = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for relative_offset in range(0, length, APFS_BLOCK_SIZE):
                offset = base_offset + relative_offset
                magic = mapped[offset + APFS_MAGIC_OFFSET : offset + APFS_MAGIC_OFFSET + 4]
                if magic not in {b"NXSB", b"APSB"}:
                    continue
                block = mapped[offset : offset + APFS_BLOCK_SIZE]
                object_type = struct.unpack_from("<I", block, APFS_OBJECT_TYPE_OFFSET)[0]
                expected_type = (
                    APFS_OBJECT_TYPE_NX_SUPERBLOCK if magic == b"NXSB" else APFS_OBJECT_TYPE_FS
                )
                if object_type & 0xFFFF != expected_type:
                    continue
                stored_checksum = struct.unpack_from(
                    "<Q", block, APFS_OBJECT_CHECKSUM_OFFSET
                )[0]
                calculated_checksum = fletcher64(block[8:])
                if stored_checksum != calculated_checksum:
                    raise RecoveryImageError(
                        f"APFS superblock at 0x{offset:x} has an invalid checksum"
                    )
                common = {
                    "offset": offset,
                    "xid": struct.unpack_from("<Q", block, APFS_OBJECT_XID_OFFSET)[0],
                }
                if magic == b"NXSB":
                    common["uuid"] = str(
                        uuid.UUID(
                            bytes=block[
                                APFS_CONTAINER_UUID_OFFSET : APFS_CONTAINER_UUID_OFFSET + 16
                            ]
                        )
                    )
                    containers.append(common)
                else:
                    common.update(
                        {
                            "uuid": str(
                                uuid.UUID(
                                    bytes=block[
                                        APFS_VOLUME_UUID_OFFSET : APFS_VOLUME_UUID_OFFSET + 16
                                    ]
                                )
                            ),
                            "name": _decode_volume_name(block),
                            "role": struct.unpack_from(
                                "<H", block, APFS_VOLUME_ROLE_OFFSET
                            )[0],
                        }
                    )
                    volumes.append(common)
        finally:
            mapped.close()

    if not containers:
        raise RecoveryImageError("no checksum-valid APFS container superblock was found")
    if not volumes:
        raise RecoveryImageError("no checksum-valid APFS volume superblock was found")
    return {"containers": containers, "volumes": volumes}


def patch_apfs_recovery_identity(
    image: Path,
    *,
    container_uuid: uuid.UUID | str = DEFAULT_CONTAINER_UUID,
    volume_uuid: uuid.UUID | str = DEFAULT_VOLUME_UUID,
    volume_name: str = DEFAULT_VOLUME_NAME,
) -> dict[str, object]:
    """Retag one copied APFS container as an independent Recovery volume."""

    image = Path(image)
    container_id = _checked_uuid(container_uuid, "container UUID")
    volume_id = _checked_uuid(volume_uuid, "volume UUID")
    try:
        encoded_name = volume_name.encode("utf-8")
    except UnicodeEncodeError as error:
        raise RecoveryImageError("Recovery volume name is not valid UTF-8") from error
    if not encoded_name or len(encoded_name) >= APFS_VOLUME_NAME_LENGTH:
        raise RecoveryImageError("Recovery volume name must contain 1 through 255 UTF-8 bytes")

    before = _scan_apfs_superblocks(image)
    container_ids = {str(item["uuid"]) for item in before["containers"]}
    volume_ids = {str(item["uuid"]) for item in before["volumes"]}
    if len(container_ids) != 1:
        raise RecoveryImageError("APFS image contains checkpoints for multiple containers")
    if len(volume_ids) != 1:
        raise RecoveryImageError("APFS image contains checkpoints for multiple volumes")
    unexpected_roles = {
        int(item["role"])
        for item in before["volumes"]
        if int(item["role"]) not in {APFS_VOL_ROLE_NONE, APFS_VOL_ROLE_RECOVERY}
    }
    if unexpected_roles:
        roles = ", ".join(f"0x{role:x}" for role in sorted(unexpected_roles))
        raise RecoveryImageError(f"refusing to replace existing APFS volume role(s): {roles}")

    container_offsets = [int(item["offset"]) for item in before["containers"]]
    volume_offsets = [int(item["offset"]) for item in before["volumes"]]
    with image.open("r+b") as stream:
        for offset in container_offsets:
            stream.seek(offset)
            block = bytearray(stream.read(APFS_BLOCK_SIZE))
            if len(block) != APFS_BLOCK_SIZE or block[APFS_MAGIC_OFFSET : APFS_MAGIC_OFFSET + 4] != b"NXSB":
                raise RecoveryImageError("APFS image changed while updating container identity")
            block[
                APFS_CONTAINER_UUID_OFFSET : APFS_CONTAINER_UUID_OFFSET + 16
            ] = container_id.bytes
            struct.pack_into("<Q", block, APFS_OBJECT_CHECKSUM_OFFSET, fletcher64(block[8:]))
            stream.seek(offset)
            stream.write(block)
        for offset in volume_offsets:
            stream.seek(offset)
            block = bytearray(stream.read(APFS_BLOCK_SIZE))
            if len(block) != APFS_BLOCK_SIZE or block[APFS_MAGIC_OFFSET : APFS_MAGIC_OFFSET + 4] != b"APSB":
                raise RecoveryImageError("APFS image changed while updating volume identity")
            block[
                APFS_VOLUME_UUID_OFFSET : APFS_VOLUME_UUID_OFFSET + 16
            ] = volume_id.bytes
            block[
                APFS_VOLUME_NAME_OFFSET : APFS_VOLUME_NAME_OFFSET + APFS_VOLUME_NAME_LENGTH
            ] = encoded_name.ljust(APFS_VOLUME_NAME_LENGTH, b"\0")
            struct.pack_into("<H", block, APFS_VOLUME_ROLE_OFFSET, APFS_VOL_ROLE_RECOVERY)
            struct.pack_into("<Q", block, APFS_OBJECT_CHECKSUM_OFFSET, fletcher64(block[8:]))
            stream.seek(offset)
            stream.write(block)
        stream.flush()
        os.fsync(stream.fileno())

    after = _scan_apfs_superblocks(image)
    if {str(item["uuid"]) for item in after["containers"]} != {str(container_id)}:
        raise RecoveryImageError("Recovery container UUID did not persist in every checkpoint")
    if {str(item["uuid"]) for item in after["volumes"]} != {str(volume_id)}:
        raise RecoveryImageError("Recovery volume UUID did not persist in every checkpoint")
    if {str(item["name"]) for item in after["volumes"]} != {volume_name}:
        raise RecoveryImageError("Recovery volume name did not persist in every checkpoint")
    if any(int(item["role"]) != APFS_VOL_ROLE_RECOVERY for item in after["volumes"]):
        raise RecoveryImageError("Recovery role did not persist in every APFS checkpoint")
    return {
        "container_uuid": str(container_id),
        "volume_uuid": str(volume_id),
        "volume_name": volume_name,
        "volume_role": APFS_VOL_ROLE_RECOVERY,
        "container_superblock_count": len(after["containers"]),
        "volume_superblock_count": len(after["volumes"]),
    }


def _layout(container_size: int) -> dict[str, int]:
    if container_size < 2 * APFS_BLOCK_SIZE or container_size % APFS_BLOCK_SIZE:
        raise RecoveryImageError("APFS source size must be a non-trivial multiple of 4096")
    partition_sectors = container_size // SECTOR_SIZE
    partition_last_lba = PARTITION_START_LBA + partition_sectors - 1
    backup_entries_lba = partition_last_lba + 1
    last_lba = backup_entries_lba + GPT_ENTRY_ARRAY_SECTORS
    return {
        "container_size": container_size,
        "partition_start_lba": PARTITION_START_LBA,
        "partition_last_lba": partition_last_lba,
        "backup_entries_lba": backup_entries_lba,
        "last_usable_lba": partition_last_lba,
        "last_lba": last_lba,
        "total_lbas": last_lba + 1,
        "size_bytes": (last_lba + 1) * SECTOR_SIZE,
    }


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


def _partition_entries(layout: dict[str, int], partition_uuid: uuid.UUID) -> bytes:
    entries = bytearray(GPT_ENTRY_ARRAY_BYTES)
    name = DEFAULT_VOLUME_NAME.encode("utf-16le")
    struct.pack_into(
        "<16s16sQQQ72s",
        entries,
        0,
        RECOVERY_PARTITION_TYPE.bytes_le,
        partition_uuid.bytes_le,
        layout["partition_start_lba"],
        layout["partition_last_lba"],
        0,
        name.ljust(72, b"\0"),
    )
    return bytes(entries)


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
    struct.pack_into("<I", header, 16, zlib.crc32(header[:GPT_HEADER_SIZE]) & 0xFFFFFFFF)
    return bytes(header)


def _write_disk(
    output: Path,
    container: Path,
    *,
    disk_uuid: uuid.UUID,
    partition_uuid: uuid.UUID,
) -> None:
    layout = _layout(container.stat().st_size)
    entries = _partition_entries(layout, partition_uuid)
    entries_crc = zlib.crc32(entries) & 0xFFFFFFFF
    primary = _gpt_header(
        current_lba=PRIMARY_HEADER_LBA,
        backup_lba=layout["last_lba"],
        last_usable_lba=layout["last_usable_lba"],
        disk_uuid=disk_uuid,
        entries_lba=PRIMARY_ENTRIES_LBA,
        entries_crc=entries_crc,
    )
    backup = _gpt_header(
        current_lba=layout["last_lba"],
        backup_lba=PRIMARY_HEADER_LBA,
        last_usable_lba=layout["last_usable_lba"],
        disk_uuid=disk_uuid,
        entries_lba=layout["backup_entries_lba"],
        entries_crc=entries_crc,
    )
    with output.open("xb") as stream:
        stream.truncate(layout["size_bytes"])
        stream.seek(0)
        stream.write(_protective_mbr(layout["total_lbas"]))
        stream.seek(PRIMARY_HEADER_LBA * SECTOR_SIZE)
        stream.write(primary)
        stream.seek(PRIMARY_ENTRIES_LBA * SECTOR_SIZE)
        stream.write(entries)
        stream.seek(layout["partition_start_lba"] * SECTOR_SIZE)
        with container.open("rb") as source:
            shutil.copyfileobj(source, stream, length=4 * 1024 * 1024)
        stream.seek(layout["backup_entries_lba"] * SECTOR_SIZE)
        stream.write(entries)
        stream.seek(layout["last_lba"] * SECTOR_SIZE)
        stream.write(backup)
        stream.flush()
        os.fsync(stream.fileno())


def _parse_gpt_header(block: bytes, expected_lba: int) -> dict[str, object]:
    if len(block) != SECTOR_SIZE:
        raise RecoveryImageError("truncated GPT header")
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
        raise RecoveryImageError("invalid GPT signature or revision")
    if header_size != GPT_HEADER_SIZE or reserved != 0 or current_lba != expected_lba:
        raise RecoveryImageError("invalid GPT header geometry")
    checked = bytearray(block[:header_size])
    struct.pack_into("<I", checked, 16, 0)
    if zlib.crc32(checked) & 0xFFFFFFFF != stored_crc:
        raise RecoveryImageError("GPT header checksum mismatch")
    if entry_count != GPT_ENTRY_COUNT or entry_size != GPT_ENTRY_SIZE:
        raise RecoveryImageError("unsupported GPT partition-entry geometry")
    return {
        "backup_lba": backup_lba,
        "first_usable_lba": first_usable_lba,
        "last_usable_lba": last_usable_lba,
        "disk_uuid": str(uuid.UUID(bytes_le=disk_uuid_bytes)),
        "entries_lba": entries_lba,
        "entries_crc": entries_crc,
    }


def inspect_recovery_image(
    image: Path, *, expected_volume_uuid: uuid.UUID | str | None = None
) -> dict[str, object]:
    image = Path(image)
    size = image.stat().st_size
    if size % SECTOR_SIZE or size < (PARTITION_START_LBA + 64) * SECTOR_SIZE:
        raise RecoveryImageError("Recovery disk size is invalid")
    last_lba = size // SECTOR_SIZE - 1
    backup_entries_lba = last_lba - GPT_ENTRY_ARRAY_SECTORS
    with image.open("rb") as stream:
        mbr = stream.read(SECTOR_SIZE)
        if mbr[510:512] != b"\x55\xaa" or mbr[450] != 0xEE:
            raise RecoveryImageError("protective MBR is missing")
        stream.seek(PRIMARY_HEADER_LBA * SECTOR_SIZE)
        primary = _parse_gpt_header(stream.read(SECTOR_SIZE), PRIMARY_HEADER_LBA)
        stream.seek(int(primary["entries_lba"]) * SECTOR_SIZE)
        primary_entries = stream.read(GPT_ENTRY_ARRAY_BYTES)
        if zlib.crc32(primary_entries) & 0xFFFFFFFF != int(primary["entries_crc"]):
            raise RecoveryImageError("primary GPT partition-array checksum mismatch")
        stream.seek(last_lba * SECTOR_SIZE)
        backup = _parse_gpt_header(stream.read(SECTOR_SIZE), last_lba)
        stream.seek(int(backup["entries_lba"]) * SECTOR_SIZE)
        backup_entries = stream.read(GPT_ENTRY_ARRAY_BYTES)
        if zlib.crc32(backup_entries) & 0xFFFFFFFF != int(backup["entries_crc"]):
            raise RecoveryImageError("backup GPT partition-array checksum mismatch")
    if primary_entries != backup_entries:
        raise RecoveryImageError("primary and backup GPT partition arrays differ")
    if primary["backup_lba"] != last_lba or backup["backup_lba"] != PRIMARY_HEADER_LBA:
        raise RecoveryImageError("primary and backup GPT headers do not reference each other")
    if (
        int(primary["entries_lba"]) != PRIMARY_ENTRIES_LBA
        or int(backup["entries_lba"]) != backup_entries_lba
    ):
        raise RecoveryImageError("GPT partition-array locations do not match disk geometry")
    if primary["disk_uuid"] != backup["disk_uuid"]:
        raise RecoveryImageError("primary and backup GPT disk UUIDs differ")
    if int(primary["first_usable_lba"]) != FIRST_USABLE_LBA:
        raise RecoveryImageError("GPT first usable LBA is invalid")

    populated = [
        primary_entries[offset : offset + GPT_ENTRY_SIZE]
        for offset in range(0, GPT_ENTRY_ARRAY_BYTES, GPT_ENTRY_SIZE)
        if primary_entries[offset : offset + 16] != bytes(16)
    ]
    if len(populated) != 1:
        raise RecoveryImageError("Recovery disk must contain exactly one GPT partition")
    type_bytes, unique_bytes, first_lba, partition_last_lba, attributes, name_bytes = struct.unpack(
        "<16s16sQQQ72s", populated[0]
    )
    if uuid.UUID(bytes_le=type_bytes) != RECOVERY_PARTITION_TYPE:
        raise RecoveryImageError("Recovery partition uses the wrong GPT Content UUID")
    if first_lba != PARTITION_START_LBA:
        raise RecoveryImageError("Recovery partition is not 1 MiB aligned")
    if attributes != 0:
        raise RecoveryImageError("Recovery partition has unexpected GPT attributes")
    if partition_last_lba + 1 != backup_entries_lba:
        raise RecoveryImageError("Recovery partition does not end before backup GPT metadata")
    if (
        int(primary["last_usable_lba"]) != partition_last_lba
        or int(backup["last_usable_lba"]) != partition_last_lba
    ):
        raise RecoveryImageError("GPT usable range does not match the Recovery partition")
    try:
        partition_name = name_bytes.decode("utf-16le").rstrip("\0")
    except UnicodeDecodeError as error:
        raise RecoveryImageError("Recovery GPT partition name is invalid") from error
    if partition_name != DEFAULT_VOLUME_NAME:
        raise RecoveryImageError("Recovery GPT partition has an unexpected name")

    partition_offset = first_lba * SECTOR_SIZE
    partition_size = (partition_last_lba - first_lba + 1) * SECTOR_SIZE
    superblocks = _scan_apfs_superblocks(
        image, base_offset=partition_offset, length=partition_size
    )
    container_uuids = {str(item["uuid"]) for item in superblocks["containers"]}
    volume_uuids = {str(item["uuid"]) for item in superblocks["volumes"]}
    volume_names = {str(item["name"]) for item in superblocks["volumes"]}
    roles = {int(item["role"]) for item in superblocks["volumes"]}
    if len(container_uuids) != 1 or len(volume_uuids) != 1:
        raise RecoveryImageError("Recovery APFS checkpoint identities are inconsistent")
    if volume_names != {DEFAULT_VOLUME_NAME} or roles != {APFS_VOL_ROLE_RECOVERY}:
        raise RecoveryImageError("APFS volume is not consistently marked as Recovery")
    volume_id = next(iter(volume_uuids))
    if expected_volume_uuid is not None:
        expected = str(_checked_uuid(expected_volume_uuid, "expected volume UUID"))
        if volume_id != expected:
            raise RecoveryImageError(
                f"Recovery volume UUID {volume_id} does not match expected {expected}"
            )
    return {
        "size_bytes": size,
        "disk_uuid": primary["disk_uuid"],
        "partition_type": str(RECOVERY_PARTITION_TYPE),
        "partition_uuid": str(uuid.UUID(bytes_le=unique_bytes)),
        "partition_name": partition_name,
        "partition_start_lba": first_lba,
        "partition_last_lba": partition_last_lba,
        "container_uuid": next(iter(container_uuids)),
        "volume_uuid": volume_id,
        "volume_name": DEFAULT_VOLUME_NAME,
        "volume_role": APFS_VOL_ROLE_RECOVERY,
        "container_superblock_count": len(superblocks["containers"]),
        "volume_superblock_count": len(superblocks["volumes"]),
    }


def build_recovery_image(
    source: Path,
    output: Path,
    *,
    disk_uuid: uuid.UUID | str = DEFAULT_DISK_UUID,
    partition_uuid: uuid.UUID | str = DEFAULT_PARTITION_UUID,
    container_uuid: uuid.UUID | str = DEFAULT_CONTAINER_UUID,
    volume_uuid: uuid.UUID | str = DEFAULT_VOLUME_UUID,
) -> dict[str, object]:
    source = Path(source)
    output = Path(output)
    if not source.is_file():
        raise RecoveryImageError(f"APFS source is not a regular file: {source}")
    if output.exists():
        raise RecoveryImageError(f"refusing to overwrite existing output: {output}")
    if not output.parent.is_dir():
        raise RecoveryImageError(f"output directory does not exist: {output.parent}")
    if source.resolve() == output.resolve():
        raise RecoveryImageError("Recovery source and output must be different files")
    _layout(source.stat().st_size)
    # Validate all APFS checksums and role preconditions before allocating the
    # potentially large staging disk.
    source_metadata = _scan_apfs_superblocks(source)
    if any(
        int(item["role"]) not in {APFS_VOL_ROLE_NONE, APFS_VOL_ROLE_RECOVERY}
        for item in source_metadata["volumes"]
    ):
        raise RecoveryImageError("Recovery source has a non-recovery APFS role")

    disk_id = _checked_uuid(disk_uuid, "disk UUID")
    partition_id = _checked_uuid(partition_uuid, "partition UUID")
    container_id = _checked_uuid(container_uuid, "container UUID")
    volume_id = _checked_uuid(volume_uuid, "volume UUID")
    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as temp_name:
        temp = Path(temp_name)
        container = temp / "recovery.apfs"
        shutil.copyfile(source, container)
        patch_apfs_recovery_identity(
            container,
            container_uuid=container_id,
            volume_uuid=volume_id,
        )
        staging = temp / "recovery.img"
        _write_disk(
            staging,
            container,
            disk_uuid=disk_id,
            partition_uuid=partition_id,
        )
        details = inspect_recovery_image(staging, expected_volume_uuid=volume_id)
        try:
            os.link(staging, output)
        except FileExistsError as error:
            raise RecoveryImageError(f"refusing to overwrite existing output: {output}") from error
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    return details


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="build a Recovery disk without overwriting")
    build.add_argument("--source", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--disk-uuid", default=str(DEFAULT_DISK_UUID))
    build.add_argument("--partition-uuid", default=str(DEFAULT_PARTITION_UUID))
    build.add_argument("--container-uuid", default=str(DEFAULT_CONTAINER_UUID))
    build.add_argument("--volume-uuid", default=str(DEFAULT_VOLUME_UUID))
    inspect = subparsers.add_parser("inspect", help="validate an existing Recovery disk")
    inspect.add_argument("image", type=Path)
    inspect.add_argument("--expected-volume-uuid")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        require_validation_environment()
        if args.command == "build":
            details = build_recovery_image(
                args.source,
                args.output,
                disk_uuid=args.disk_uuid,
                partition_uuid=args.partition_uuid,
                container_uuid=args.container_uuid,
                volume_uuid=args.volume_uuid,
            )
        else:
            details = inspect_recovery_image(
                args.image, expected_volume_uuid=args.expected_volume_uuid
            )
    except (OSError, RecoveryImageError) as error:
        print(f"macvm: Recovery image error: {error}", file=os.sys.stderr)
        return 1
    print(json.dumps(details, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
