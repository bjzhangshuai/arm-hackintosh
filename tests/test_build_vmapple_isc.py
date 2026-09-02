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

import build_vmapple_isc as ISC  # noqa: E402


TEST_SIZE_MIB = 40


def write_fake_apfs(
    path: Path,
    _container_uuid: uuid.UUID,
    volume_uuid: uuid.UUID,
    *,
    roles: tuple[int, ...] = (ISC.APFS_VOL_ROLE_NONE,),
    volume_uuids: tuple[uuid.UUID, ...] | None = None,
) -> None:
    if volume_uuids is None:
        volume_uuids = tuple(volume_uuid for _ in roles)
    if len(volume_uuids) != len(roles):
        raise AssertionError("test fixture role/UUID count mismatch")

    with path.open("r+b") as stream:
        nx = bytearray(ISC.APFS_BLOCK_SIZE)
        nx[ISC.APFS_MAGIC_OFFSET : ISC.APFS_MAGIC_OFFSET + 4] = b"NXSB"
        struct.pack_into("<I", nx, 0x24, ISC.APFS_BLOCK_SIZE)
        stream.seek(0)
        stream.write(nx)
        for index, (role, current_uuid) in enumerate(zip(roles, volume_uuids), start=1):
            block = bytearray(ISC.APFS_BLOCK_SIZE)
            block[ISC.APFS_MAGIC_OFFSET : ISC.APFS_MAGIC_OFFSET + 4] = b"APSB"
            struct.pack_into("<I", block, ISC.APFS_OBJECT_TYPE_OFFSET, ISC.APFS_OBJECT_TYPE_FS)
            block[
                ISC.APFS_VOLUME_UUID_OFFSET : ISC.APFS_VOLUME_UUID_OFFSET + 16
            ] = current_uuid.bytes
            block[
                ISC.APFS_VOLUME_NAME_OFFSET : ISC.APFS_VOLUME_NAME_OFFSET + 5
            ] = b"xART\0"
            struct.pack_into("<H", block, ISC.APFS_VOLUME_ROLE_OFFSET, role)
            struct.pack_into("<Q", block, 0, ISC.fletcher64(block[8:]))
            stream.seek(index * 2 * ISC.APFS_BLOCK_SIZE)
            stream.write(block)


class VMAppleISCImageTests(unittest.TestCase):
    def test_constants_match_apfs_boot_util_storage_contract(self) -> None:
        self.assertEqual(
            str(ISC.ISC_PARTITION_TYPE), "69646961-6700-11aa-aa11-00306543ecac"
        )
        self.assertEqual(ISC.APFS_VOL_ROLE_XART, 0x100)
        self.assertEqual(ISC.PARTITION_START_LBA, 65536)

    def test_reserved_prefix_covers_all_observed_apple_aux_metadata(self) -> None:
        self.assertGreater(ISC.AUX_RESERVED_BYTES, ISC.AUX_FIXED_METADATA_END)
        self.assertEqual(
            ISC.PARTITION_START_LBA * ISC.SECTOR_SIZE,
            ISC.AUX_RESERVED_BYTES,
        )
        self.assertEqual(ISC.AUX_RESERVED_BYTES % ISC.APFS_BLOCK_SIZE, 0)

    def test_fletcher64_has_apfs_zero_block_value(self) -> None:
        self.assertEqual(ISC.fletcher64(bytes(ISC.APFS_BLOCK_SIZE - 8)), 0xFFFFFFFFFFFFFFFF)

    def test_fletcher64_rejects_partial_words(self) -> None:
        with self.assertRaisesRegex(ISC.ISCImageError, "divisible by four"):
            ISC.fletcher64(b"abc")

    def test_layout_keeps_gpt_usable_range_and_aligns_apfs_partition(self) -> None:
        layout = ISC._layout(TEST_SIZE_MIB * 1024 * 1024)
        self.assertEqual(layout["partition_bytes"] % ISC.APFS_BLOCK_SIZE, 0)
        self.assertLess(layout["partition_last_lba"], layout["last_usable_lba"])
        self.assertEqual(
            layout["last_usable_lba"] - layout["partition_last_lba"],
            ISC.APFS_BLOCK_SIZE // ISC.SECTOR_SIZE - 1,
        )

    def test_environment_guard_requires_explicit_linux_x86_confirmation(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ISC.ISCImageError, "MACVM_DEBUG_ENV_CONFIRMED"):
                ISC.require_validation_environment()
        with (
            mock.patch.dict(os.environ, {"MACVM_DEBUG_ENV_CONFIRMED": "YES"}, clear=True),
            mock.patch.object(ISC.platform, "system", return_value="Darwin"),
            mock.patch.object(ISC.platform, "machine", return_value="arm64"),
        ):
            with self.assertRaisesRegex(ISC.ISCImageError, "Linux x86_64"):
                ISC.require_validation_environment()

    def test_environment_guard_accepts_confirmed_linux_x86_64(self) -> None:
        with (
            mock.patch.dict(os.environ, {"MACVM_DEBUG_ENV_CONFIRMED": "YES"}, clear=True),
            mock.patch.object(ISC.platform, "system", return_value="Linux"),
            mock.patch.object(ISC.platform, "machine", return_value="x86_64"),
        ):
            ISC.require_validation_environment()

    def test_patch_sets_role_and_changes_only_checksum_and_role_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "container.apfs"
            image.write_bytes(bytes(4 * ISC.APFS_BLOCK_SIZE))
            write_fake_apfs(image, ISC.DEFAULT_CONTAINER_UUID, ISC.DEFAULT_VOLUME_UUID)
            before = image.read_bytes()
            offsets = ISC.patch_apfs_xart_role(image)
            after = image.read_bytes()
            self.assertEqual(offsets, [2 * ISC.APFS_BLOCK_SIZE])
            changed = {index for index, pair in enumerate(zip(before, after)) if pair[0] != pair[1]}
            expected = set(range(offsets[0], offsets[0] + 8)) | {
                offsets[0] + ISC.APFS_VOLUME_ROLE_OFFSET,
                offsets[0] + ISC.APFS_VOLUME_ROLE_OFFSET + 1,
            }
            self.assertTrue(changed)
            self.assertLessEqual(changed, expected)
            parsed = ISC._scan_apfs_volume_superblocks(image)
            self.assertEqual([item["role"] for item in parsed], [0x100])

    def test_patch_updates_all_checkpoint_copies_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "container.apfs"
            image.write_bytes(bytes(8 * ISC.APFS_BLOCK_SIZE))
            write_fake_apfs(
                image,
                ISC.DEFAULT_CONTAINER_UUID,
                ISC.DEFAULT_VOLUME_UUID,
                roles=(0, 0),
            )
            first = ISC.patch_apfs_xart_role(image)
            snapshot = image.read_bytes()
            second = ISC.patch_apfs_xart_role(image)
            self.assertEqual(first, second)
            self.assertEqual(image.read_bytes(), snapshot)
            self.assertEqual(len(first), 2)

    def test_patch_refuses_an_existing_non_xart_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "container.apfs"
            image.write_bytes(bytes(4 * ISC.APFS_BLOCK_SIZE))
            write_fake_apfs(
                image,
                ISC.DEFAULT_CONTAINER_UUID,
                ISC.DEFAULT_VOLUME_UUID,
                roles=(0x10,),
            )
            with self.assertRaisesRegex(ISC.ISCImageError, "refusing to replace"):
                ISC.patch_apfs_xart_role(image)

    def test_patch_refuses_bad_checksum_before_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "container.apfs"
            image.write_bytes(bytes(4 * ISC.APFS_BLOCK_SIZE))
            write_fake_apfs(image, ISC.DEFAULT_CONTAINER_UUID, ISC.DEFAULT_VOLUME_UUID)
            data = bytearray(image.read_bytes())
            data[2 * ISC.APFS_BLOCK_SIZE + 0x200] ^= 1
            image.write_bytes(data)
            before = image.read_bytes()
            with self.assertRaisesRegex(ISC.ISCImageError, "invalid checksum"):
                ISC.patch_apfs_xart_role(image)
            self.assertEqual(image.read_bytes(), before)

    def test_patch_refuses_checkpoint_copies_from_multiple_volumes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            image = Path(temp_name) / "container.apfs"
            image.write_bytes(bytes(8 * ISC.APFS_BLOCK_SIZE))
            write_fake_apfs(
                image,
                ISC.DEFAULT_CONTAINER_UUID,
                ISC.DEFAULT_VOLUME_UUID,
                roles=(0, 0),
                volume_uuids=(ISC.DEFAULT_VOLUME_UUID, uuid.uuid4()),
            )
            with self.assertRaisesRegex(ISC.ISCImageError, "more than one volume"):
                ISC.patch_apfs_xart_role(image)

    def test_build_and_inspect_produce_one_special_gpt_xart_partition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"
            details = ISC.build_isc_image(
                output,
                size_mib=TEST_SIZE_MIB,
                mkfs_runner=write_fake_apfs,
            )
            self.assertEqual(output.stat().st_size, TEST_SIZE_MIB * 1024 * 1024)
            self.assertEqual(details, ISC.inspect_isc_image(output))
            self.assertEqual(details["partition_type"], str(ISC.ISC_PARTITION_TYPE))
            self.assertEqual(details["partition_start_lba"], 65536)
            self.assertEqual(details["apfs_volume_name"], "xART")
            self.assertEqual(details["apfs_role"], 0x100)
            with output.open("rb") as stream:
                stream.seek(446)
                self.assertEqual(stream.read(5)[4], 0xEE)
                stream.seek(510)
                self.assertEqual(stream.read(2), b"\x55\xaa")

    def test_build_refuses_existing_output_without_changing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"
            output.write_bytes(b"keep")
            with self.assertRaisesRegex(ISC.ISCImageError, "refusing to overwrite"):
                ISC.build_isc_image(
                    output, size_mib=TEST_SIZE_MIB, mkfs_runner=write_fake_apfs
                )
            self.assertEqual(output.read_bytes(), b"keep")

    def test_build_publish_race_preserves_competing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"

            def racing_runner(path: Path, container: uuid.UUID, volume: uuid.UUID) -> None:
                write_fake_apfs(path, container, volume)
                output.write_bytes(b"winner")

            with self.assertRaisesRegex(ISC.ISCImageError, "refusing to overwrite"):
                ISC.build_isc_image(
                    output, size_mib=TEST_SIZE_MIB, mkfs_runner=racing_runner
                )
            self.assertEqual(output.read_bytes(), b"winner")

    def test_build_failure_leaves_no_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"

            def failing_runner(_path: Path, _container: uuid.UUID, _volume: uuid.UUID) -> None:
                raise ISC.ISCImageError("synthetic mkfs failure")

            with self.assertRaisesRegex(ISC.ISCImageError, "synthetic mkfs failure"):
                ISC.build_isc_image(
                    output, size_mib=TEST_SIZE_MIB, mkfs_runner=failing_runner
                )
            self.assertFalse(output.exists())

    def test_build_refuses_mkfs_that_changes_partition_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"

            def shrinking_runner(path: Path, container: uuid.UUID, volume: uuid.UUID) -> None:
                write_fake_apfs(path, container, volume)
                with path.open("r+b") as stream:
                    stream.truncate(4 * ISC.APFS_BLOCK_SIZE)

            with self.assertRaisesRegex(ISC.ISCImageError, "changed.*container size"):
                ISC.build_isc_image(
                    output, size_mib=TEST_SIZE_MIB, mkfs_runner=shrinking_runner
                )
            self.assertFalse(output.exists())

    def test_build_rejects_bad_size_and_uuid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"
            with self.assertRaisesRegex(ISC.ISCImageError, "too small"):
                ISC.build_isc_image(output, size_mib=1, mkfs_runner=write_fake_apfs)
            with self.assertRaisesRegex(ISC.ISCImageError, "invalid disk UUID"):
                ISC.build_isc_image(
                    output,
                    size_mib=TEST_SIZE_MIB,
                    disk_uuid="not-a-uuid",
                    mkfs_runner=write_fake_apfs,
                )

    def test_inspect_rejects_corrupt_primary_header_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"
            ISC.build_isc_image(
                output, size_mib=TEST_SIZE_MIB, mkfs_runner=write_fake_apfs
            )
            with output.open("r+b") as stream:
                # Change only a payload byte: mutating current_lba would
                # correctly fail the earlier geometry check instead of CRC.
                stream.seek(ISC.SECTOR_SIZE + 56)
                byte = stream.read(1)
                stream.seek(ISC.SECTOR_SIZE + 56)
                stream.write(bytes((byte[0] ^ 1,)))
            with self.assertRaisesRegex(ISC.ISCImageError, "header checksum"):
                ISC.inspect_isc_image(output)

    def test_inspect_rejects_corrupt_backup_partition_array(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"
            ISC.build_isc_image(
                output, size_mib=TEST_SIZE_MIB, mkfs_runner=write_fake_apfs
            )
            layout = ISC._layout(output.stat().st_size)
            with output.open("r+b") as stream:
                stream.seek(layout["backup_entries_lba"] * ISC.SECTOR_SIZE + 1)
                byte = stream.read(1)
                stream.seek(layout["backup_entries_lba"] * ISC.SECTOR_SIZE + 1)
                stream.write(bytes((byte[0] ^ 1,)))
            with self.assertRaisesRegex(ISC.ISCImageError, "backup GPT partition-array checksum"):
                ISC.inspect_isc_image(output)

    def test_inspect_rejects_backup_partition_array_location_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"
            ISC.build_isc_image(
                output, size_mib=TEST_SIZE_MIB, mkfs_runner=write_fake_apfs
            )
            layout = ISC._layout(output.stat().st_size)
            header_offset = layout["last_lba"] * ISC.SECTOR_SIZE
            with output.open("r+b") as stream:
                stream.seek(header_offset)
                header = bytearray(stream.read(ISC.SECTOR_SIZE))
                struct.pack_into("<Q", header, 72, ISC.PRIMARY_ENTRIES_LBA)
                struct.pack_into("<I", header, 16, 0)
                struct.pack_into(
                    "<I",
                    header,
                    16,
                    ISC.zlib.crc32(header[: ISC.GPT_HEADER_SIZE]) & 0xFFFFFFFF,
                )
                stream.seek(header_offset)
                stream.write(header)
            with self.assertRaisesRegex(ISC.ISCImageError, "partition-array locations"):
                ISC.inspect_isc_image(output)

    def test_inspect_rejects_xart_role_regression_even_with_valid_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "isc.img"
            ISC.build_isc_image(
                output, size_mib=TEST_SIZE_MIB, mkfs_runner=write_fake_apfs
            )
            partition_offset = ISC.PARTITION_START_LBA * ISC.SECTOR_SIZE
            block_offset = partition_offset + 2 * ISC.APFS_BLOCK_SIZE
            with output.open("r+b") as stream:
                stream.seek(block_offset)
                block = bytearray(stream.read(ISC.APFS_BLOCK_SIZE))
                struct.pack_into("<H", block, ISC.APFS_VOLUME_ROLE_OFFSET, 0)
                struct.pack_into("<Q", block, 0, ISC.fletcher64(block[8:]))
                stream.seek(block_offset)
                stream.write(block)
            with self.assertRaisesRegex(ISC.ISCImageError, "not consistently marked as xART"):
                ISC.inspect_isc_image(output)


if __name__ == "__main__":
    unittest.main()
