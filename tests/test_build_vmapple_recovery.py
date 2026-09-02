from __future__ import annotations

from pathlib import Path
import os
import struct
import sys
import tempfile
import unittest
from unittest import mock
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_vmapple_recovery as RECOVERY  # noqa: E402


SOURCE_BLOCKS = 8


def write_fake_apfs(
    path: Path,
    *,
    container_uuids: tuple[uuid.UUID, ...] = (uuid.UUID(int=1), uuid.UUID(int=1)),
    volume_uuids: tuple[uuid.UUID, ...] = (uuid.UUID(int=2), uuid.UUID(int=2)),
    roles: tuple[int, ...] = (RECOVERY.APFS_VOL_ROLE_NONE, RECOVERY.APFS_VOL_ROLE_NONE),
    volume_name: str = "ramdisk",
) -> None:
    if len(volume_uuids) != len(roles):
        raise AssertionError("test fixture volume UUID/role mismatch")
    with path.open("wb") as stream:
        stream.truncate(SOURCE_BLOCKS * RECOVERY.APFS_BLOCK_SIZE)
    with path.open("r+b") as stream:
        for index, current_uuid in enumerate(container_uuids):
            block = bytearray(RECOVERY.APFS_BLOCK_SIZE)
            block[RECOVERY.APFS_MAGIC_OFFSET : RECOVERY.APFS_MAGIC_OFFSET + 4] = b"NXSB"
            struct.pack_into(
                "<I",
                block,
                RECOVERY.APFS_OBJECT_TYPE_OFFSET,
                RECOVERY.APFS_OBJECT_TYPE_NX_SUPERBLOCK,
            )
            struct.pack_into("<Q", block, RECOVERY.APFS_OBJECT_XID_OFFSET, index + 1)
            block[
                RECOVERY.APFS_CONTAINER_UUID_OFFSET : RECOVERY.APFS_CONTAINER_UUID_OFFSET + 16
            ] = current_uuid.bytes
            struct.pack_into("<Q", block, 0, RECOVERY.fletcher64(block[8:]))
            stream.seek(index * 4 * RECOVERY.APFS_BLOCK_SIZE)
            stream.write(block)
        for index, (current_uuid, role) in enumerate(zip(volume_uuids, roles)):
            block = bytearray(RECOVERY.APFS_BLOCK_SIZE)
            block[RECOVERY.APFS_MAGIC_OFFSET : RECOVERY.APFS_MAGIC_OFFSET + 4] = b"APSB"
            struct.pack_into(
                "<I", block, RECOVERY.APFS_OBJECT_TYPE_OFFSET, RECOVERY.APFS_OBJECT_TYPE_FS
            )
            struct.pack_into("<Q", block, RECOVERY.APFS_OBJECT_XID_OFFSET, index + 1)
            block[
                RECOVERY.APFS_VOLUME_UUID_OFFSET : RECOVERY.APFS_VOLUME_UUID_OFFSET + 16
            ] = current_uuid.bytes
            encoded_name = volume_name.encode("utf-8")
            block[
                RECOVERY.APFS_VOLUME_NAME_OFFSET : RECOVERY.APFS_VOLUME_NAME_OFFSET
                + len(encoded_name)
            ] = encoded_name
            struct.pack_into("<H", block, RECOVERY.APFS_VOLUME_ROLE_OFFSET, role)
            struct.pack_into("<Q", block, 0, RECOVERY.fletcher64(block[8:]))
            stream.seek((index * 4 + 1) * RECOVERY.APFS_BLOCK_SIZE)
            stream.write(block)


def rewrite_gpt_header_crc(stream, header_offset: int) -> None:
    stream.seek(header_offset)
    header = bytearray(stream.read(RECOVERY.SECTOR_SIZE))
    struct.pack_into("<I", header, 16, 0)
    struct.pack_into(
        "<I",
        header,
        16,
        RECOVERY.zlib.crc32(header[: RECOVERY.GPT_HEADER_SIZE]) & 0xFFFFFFFF,
    )
    stream.seek(header_offset)
    stream.write(header)


class VMAppleRecoveryImageTests(unittest.TestCase):
    def test_constants_match_prebootensurer_contract(self) -> None:
        self.assertEqual(
            str(RECOVERY.RECOVERY_PARTITION_TYPE),
            "52637672-7900-11aa-aa11-00306543ecac",
        )
        self.assertEqual(RECOVERY.APFS_VOL_ROLE_RECOVERY, 0x4)
        self.assertEqual(
            RECOVERY.PARTITION_START_LBA * RECOVERY.SECTOR_SIZE, 1024 * 1024
        )

    def test_environment_guard_requires_isolated_linux_x86_64(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RECOVERY.RecoveryImageError, "MACVM_DEBUG_ENV_CONFIRMED"
            ):
                RECOVERY.require_validation_environment()
        with (
            mock.patch.dict(
                os.environ, {"MACVM_DEBUG_ENV_CONFIRMED": "YES"}, clear=True
            ),
            mock.patch.object(RECOVERY.platform, "system", return_value="Darwin"),
            mock.patch.object(RECOVERY.platform, "machine", return_value="arm64"),
        ):
            with self.assertRaisesRegex(
                RECOVERY.RecoveryImageError, "Linux x86_64"
            ):
                RECOVERY.require_validation_environment()

    def test_environment_guard_accepts_confirmed_linux_x86_64(self) -> None:
        with (
            mock.patch.dict(
                os.environ, {"MACVM_DEBUG_ENV_CONFIRMED": "YES"}, clear=True
            ),
            mock.patch.object(RECOVERY.platform, "system", return_value="Linux"),
            mock.patch.object(RECOVERY.platform, "machine", return_value="x86_64"),
        ):
            RECOVERY.require_validation_environment()

    def test_fletcher64_matches_zero_block_and_rejects_partial_words(self) -> None:
        self.assertEqual(
            RECOVERY.fletcher64(bytes(RECOVERY.APFS_BLOCK_SIZE - 8)),
            0xFFFFFFFFFFFFFFFF,
        )
        with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "divisible by four"):
            RECOVERY.fletcher64(b"bad")

    def test_patch_updates_all_checkpoints_and_only_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "source.apfs"
            write_fake_apfs(image)
            before = image.read_bytes()
            details = RECOVERY.patch_apfs_recovery_identity(image)
            after = image.read_bytes()
            parsed = RECOVERY._scan_apfs_superblocks(image)
            self.assertEqual(
                {item["uuid"] for item in parsed["containers"]},
                {str(RECOVERY.DEFAULT_CONTAINER_UUID)},
            )
            self.assertEqual(
                {item["uuid"] for item in parsed["volumes"]},
                {str(RECOVERY.DEFAULT_VOLUME_UUID)},
            )
            self.assertEqual({item["name"] for item in parsed["volumes"]}, {"Recovery"})
            self.assertEqual({item["role"] for item in parsed["volumes"]}, {0x4})
            self.assertEqual(details["container_superblock_count"], 2)
            self.assertEqual(details["volume_superblock_count"], 2)

            allowed: set[int] = set()
            for item in parsed["containers"]:
                offset = int(item["offset"])
                allowed.update(range(offset, offset + 8))
                allowed.update(
                    range(
                        offset + RECOVERY.APFS_CONTAINER_UUID_OFFSET,
                        offset + RECOVERY.APFS_CONTAINER_UUID_OFFSET + 16,
                    )
                )
            for item in parsed["volumes"]:
                offset = int(item["offset"])
                allowed.update(range(offset, offset + 8))
                allowed.update(
                    range(
                        offset + RECOVERY.APFS_VOLUME_UUID_OFFSET,
                        offset + RECOVERY.APFS_VOLUME_UUID_OFFSET + 16,
                    )
                )
                allowed.update(
                    range(
                        offset + RECOVERY.APFS_VOLUME_NAME_OFFSET,
                        offset
                        + RECOVERY.APFS_VOLUME_NAME_OFFSET
                        + RECOVERY.APFS_VOLUME_NAME_LENGTH,
                    )
                )
                allowed.update(
                    range(
                        offset + RECOVERY.APFS_VOLUME_ROLE_OFFSET,
                        offset + RECOVERY.APFS_VOLUME_ROLE_OFFSET + 2,
                    )
                )
            changed = {
                index for index, pair in enumerate(zip(before, after)) if pair[0] != pair[1]
            }
            self.assertTrue(changed)
            self.assertLessEqual(changed, allowed)

    def test_patch_is_idempotent_for_the_same_recovery_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "source.apfs"
            write_fake_apfs(image)
            RECOVERY.patch_apfs_recovery_identity(image)
            snapshot = image.read_bytes()
            RECOVERY.patch_apfs_recovery_identity(image)
            self.assertEqual(image.read_bytes(), snapshot)

    def test_patch_refuses_non_recovery_role_before_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "source.apfs"
            write_fake_apfs(image, roles=(0x1, 0x1))
            before = image.read_bytes()
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "refusing to replace"):
                RECOVERY.patch_apfs_recovery_identity(image)
            self.assertEqual(image.read_bytes(), before)

    def test_patch_refuses_bad_checksum_and_mixed_identities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "source.apfs"
            write_fake_apfs(image)
            with image.open("r+b") as stream:
                stream.seek(RECOVERY.APFS_BLOCK_SIZE + 0x200)
                byte = stream.read(1)
                stream.seek(RECOVERY.APFS_BLOCK_SIZE + 0x200)
                stream.write(bytes((byte[0] ^ 1,)))
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "invalid checksum"):
                RECOVERY.patch_apfs_recovery_identity(image)

            mixed = Path(temp_name) / "mixed.apfs"
            write_fake_apfs(
                mixed,
                volume_uuids=(uuid.UUID(int=2), uuid.UUID(int=3)),
            )
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "multiple volumes"):
                RECOVERY.patch_apfs_recovery_identity(mixed)

    def test_build_preserves_source_and_produces_valid_recovery_gpt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "source.apfs"
            output = Path(temp_name) / "recovery.img"
            write_fake_apfs(source)
            source_before = source.read_bytes()
            details = RECOVERY.build_recovery_image(source, output)
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(details, RECOVERY.inspect_recovery_image(output))
            self.assertEqual(
                details["partition_type"], str(RECOVERY.RECOVERY_PARTITION_TYPE)
            )
            self.assertEqual(details["partition_start_lba"], 2048)
            self.assertEqual(details["volume_uuid"], str(RECOVERY.DEFAULT_VOLUME_UUID))
            self.assertEqual(details["volume_role"], 0x4)
            self.assertEqual(details["volume_name"], "Recovery")
            RECOVERY.inspect_recovery_image(
                output, expected_volume_uuid=RECOVERY.DEFAULT_VOLUME_UUID
            )

    def test_build_refuses_existing_output_and_bad_source_without_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "source.apfs"
            output = Path(temp_name) / "recovery.img"
            write_fake_apfs(source)
            output.write_bytes(b"keep")
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "refusing to overwrite"):
                RECOVERY.build_recovery_image(source, output)
            self.assertEqual(output.read_bytes(), b"keep")

            output.unlink()
            with source.open("r+b") as stream:
                stream.seek(RECOVERY.APFS_BLOCK_SIZE + 0x200)
                stream.write(b"X")
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "invalid checksum"):
                RECOVERY.build_recovery_image(source, output)
            self.assertFalse(output.exists())

    def test_build_rejects_bad_size_role_and_uuid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "source.apfs"
            output = Path(temp_name) / "recovery.img"
            source.write_bytes(bytes(RECOVERY.APFS_BLOCK_SIZE + 1))
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "multiple of 4096"):
                RECOVERY.build_recovery_image(source, output)

            write_fake_apfs(source, roles=(0x1, 0x1))
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "non-recovery"):
                RECOVERY.build_recovery_image(source, output)

            write_fake_apfs(source)
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "invalid disk UUID"):
                RECOVERY.build_recovery_image(source, output, disk_uuid="not-a-uuid")

    def test_inspect_rejects_expected_uuid_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "source.apfs"
            output = Path(temp_name) / "recovery.img"
            write_fake_apfs(source)
            RECOVERY.build_recovery_image(source, output)
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "does not match expected"):
                RECOVERY.inspect_recovery_image(output, expected_volume_uuid=uuid.uuid4())

    def test_inspect_rejects_corrupt_primary_header_and_backup_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "source.apfs"
            first = Path(temp_name) / "first.img"
            second = Path(temp_name) / "second.img"
            write_fake_apfs(source)
            RECOVERY.build_recovery_image(source, first)
            shutil_copy = first.read_bytes()
            second.write_bytes(shutil_copy)
            with first.open("r+b") as stream:
                stream.seek(RECOVERY.SECTOR_SIZE + 56)
                byte = stream.read(1)
                stream.seek(RECOVERY.SECTOR_SIZE + 56)
                stream.write(bytes((byte[0] ^ 1,)))
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "header checksum"):
                RECOVERY.inspect_recovery_image(first)

            last_lba = second.stat().st_size // RECOVERY.SECTOR_SIZE - 1
            backup_entries_lba = last_lba - RECOVERY.GPT_ENTRY_ARRAY_SECTORS
            with second.open("r+b") as stream:
                stream.seek(backup_entries_lba * RECOVERY.SECTOR_SIZE + 1)
                byte = stream.read(1)
                stream.seek(backup_entries_lba * RECOVERY.SECTOR_SIZE + 1)
                stream.write(bytes((byte[0] ^ 1,)))
            with self.assertRaisesRegex(
                RECOVERY.RecoveryImageError, "backup GPT partition-array checksum"
            ):
                RECOVERY.inspect_recovery_image(second)

    def test_inspect_rejects_wrong_partition_content_with_valid_gpt_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "source.apfs"
            output = Path(temp_name) / "recovery.img"
            write_fake_apfs(source)
            RECOVERY.build_recovery_image(source, output)
            last_lba = output.stat().st_size // RECOVERY.SECTOR_SIZE - 1
            backup_entries_lba = last_lba - RECOVERY.GPT_ENTRY_ARRAY_SECTORS
            wrong_type = uuid.UUID("7c3457ef-0000-11aa-aa11-00306543ecac").bytes_le
            with output.open("r+b") as stream:
                for entries_lba, header_lba in (
                    (RECOVERY.PRIMARY_ENTRIES_LBA, RECOVERY.PRIMARY_HEADER_LBA),
                    (backup_entries_lba, last_lba),
                ):
                    stream.seek(entries_lba * RECOVERY.SECTOR_SIZE)
                    entries = bytearray(stream.read(RECOVERY.GPT_ENTRY_ARRAY_BYTES))
                    entries[:16] = wrong_type
                    entries_crc = RECOVERY.zlib.crc32(entries) & 0xFFFFFFFF
                    stream.seek(entries_lba * RECOVERY.SECTOR_SIZE)
                    stream.write(entries)
                    stream.seek(header_lba * RECOVERY.SECTOR_SIZE + 88)
                    stream.write(struct.pack("<I", entries_crc))
                    rewrite_gpt_header_crc(stream, header_lba * RECOVERY.SECTOR_SIZE)
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "Content UUID"):
                RECOVERY.inspect_recovery_image(output)

    def test_inspect_rejects_role_regression_with_valid_apfs_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "source.apfs"
            output = Path(temp_name) / "recovery.img"
            write_fake_apfs(source)
            RECOVERY.build_recovery_image(source, output)
            parsed = RECOVERY._scan_apfs_superblocks(
                output,
                base_offset=RECOVERY.PARTITION_START_LBA * RECOVERY.SECTOR_SIZE,
                length=source.stat().st_size,
            )
            offset = int(parsed["volumes"][0]["offset"])
            with output.open("r+b") as stream:
                stream.seek(offset)
                block = bytearray(stream.read(RECOVERY.APFS_BLOCK_SIZE))
                struct.pack_into("<H", block, RECOVERY.APFS_VOLUME_ROLE_OFFSET, 0)
                struct.pack_into("<Q", block, 0, RECOVERY.fletcher64(block[8:]))
                stream.seek(offset)
                stream.write(block)
            with self.assertRaisesRegex(RECOVERY.RecoveryImageError, "marked as Recovery"):
                RECOVERY.inspect_recovery_image(output)


if __name__ == "__main__":
    unittest.main()
