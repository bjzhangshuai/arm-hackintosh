from pathlib import Path
import os
import struct
import sys
import tempfile
import unittest
import uuid
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import validate_install_target as target


class InstallTargetTests(unittest.TestCase):
    SIZE = 1024 * 1024

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / 'target.raw'
        self.uuid = str(uuid.uuid4())
        self.make_image()

    def make_image(self, *, kind=target.APFS, extra=None, bounds=(40, 1000),
                   attrs=0, backup_guid=None, backup_entries_lba=None,
                   block_count=100, container_uuid=None):
        last = self.SIZE // 512 - 1
        entries = bytearray(16384)
        entries[:16] = kind.bytes_le
        entries[16:32] = uuid.uuid4().bytes_le
        struct.pack_into('<QQQ', entries, 32, *bounds, attrs)
        if extra is not None:
            entries[128:144] = extra[0].bytes_le
            entries[144:160] = uuid.uuid4().bytes_le
            struct.pack_into('<QQQ', entries, 160, extra[1], extra[2], 0)
        disk_id = uuid.uuid4()

        def header(current, alternate, entries_lba, guid):
            h = bytearray(512)
            struct.pack_into('<8sIIIIQQQQ16sQIII', h, 0, b'EFI PART',
                             0x10000, 92, 0, 0, current, alternate, 34,
                             last - 33, guid.bytes_le, entries_lba, 128, 128,
                             zlib.crc32(entries) & 0xffffffff)
            struct.pack_into('<I', h, 16, zlib.crc32(h[:92]) & 0xffffffff)
            return h

        nx = bytearray(4096)
        nx[32:36] = b'NXSB'
        struct.pack_into('<IQ', nx, 36, 4096, block_count)
        nx[72:88] = uuid.UUID(container_uuid or self.uuid).bytes
        struct.pack_into('<Q', nx, 0, target.fletcher64(nx[8:]))
        with self.image.open('wb') as f:
            f.truncate(self.SIZE)
            f.seek(512); f.write(header(1, last, 2, disk_id))
            f.seek(1024); f.write(entries)
            f.seek(40 * 512); f.write(nx)
            f.seek((last - 32) * 512); f.write(entries)
            f.seek(last * 512)
            f.write(header(last, 1, backup_entries_lba or last - 32, backup_guid or disk_id))

    def inspect(self, **kwargs):
        return target.inspect_image(kwargs.get('image', self.image),
                                    kwargs.get('size', self.SIZE),
                                    kwargs.get('identity', self.uuid))

    def corrupt(self, offset):
        with self.image.open('r+b') as f:
            f.seek(offset); value = f.read(1)
            f.seek(offset); f.write(bytes([value[0] ^ 1]))

    def test_valid_identity_read_only(self):
        before = self.image.read_bytes()
        result = self.inspect()
        self.assertEqual(result['container_uuid'], self.uuid)
        self.assertTrue(result['read_only_inspection'])
        self.assertFalse(result['filesystem_health_checked'])
        self.assertEqual(before, self.image.read_bytes())

    def test_rejects_wrong_size(self):
        for size in (0, 123, self.SIZE + 512):
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.inspect(size=size)

    def test_rejects_wrong_uuid(self):
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.inspect(identity=str(uuid.uuid4()))

    def test_rejects_symlink(self):
        link = self.image.parent / 'link'
        link.symlink_to(self.image)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.inspect(image=link)

    def test_rejects_hardlink(self):
        os.link(self.image, self.image.parent / 'hardlink')
        with self.assertRaisesRegex(ValueError, 'hardlinked'):
            self.inspect()

    def test_rejects_corrupt_gpt_headers(self):
        for offset in (512 + 16, self.SIZE - 512 + 16):
            with self.subTest(offset=offset):
                self.make_image(); self.corrupt(offset)
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    self.inspect()

    def test_rejects_corrupt_partition_arrays(self):
        for offset in (1024, self.SIZE - 512 * 33):
            with self.subTest(offset=offset):
                self.make_image(); self.corrupt(offset)
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    self.inspect()

    def test_rejects_mismatched_headers(self):
        self.make_image(backup_guid=uuid.uuid4())
        with self.assertRaisesRegex(ValueError, 'headers disagree'):
            self.inspect()

    def test_rejects_unsafe_array_location(self):
        self.make_image(backup_entries_lba=100000000)
        with self.assertRaisesRegex(ValueError, 'array positions'):
            self.inspect()

    def test_rejects_isc_recovery_and_unknown_partition_types(self):
        for kind in ('69646961-6700-11aa-aa11-00306543ecac',
                     '52637672-7900-11aa-aa11-00306543ecac', str(uuid.uuid4())):
            with self.subTest(kind=kind):
                self.make_image(kind=uuid.UUID(kind))
                with self.assertRaisesRegex(ValueError, 'partition type'):
                    self.inspect()

    def test_rejects_unexpected_attributes(self):
        self.make_image(attrs=1 << 60)
        with self.assertRaisesRegex(ValueError, 'attributes'):
            self.inspect()

    def test_rejects_partition_range_errors(self):
        for bounds in ((20, 1000), (40, 3000), (1000, 40)):
            with self.subTest(bounds=bounds):
                self.make_image(bounds=bounds)
                with self.assertRaisesRegex(ValueError, 'usable range'):
                    self.inspect()

    def test_rejects_overlap(self):
        self.make_image(extra=(target.EFI, 50, 150))
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            self.inspect()

    def test_rejects_multiple_apfs_stores(self):
        self.make_image(extra=(target.APFS, 1100, 1200))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.inspect()

    def test_rejects_missing_apfs_store(self):
        self.make_image(kind=target.EFI)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.inspect()

    def test_rejects_missing_or_corrupt_superblock(self):
        for offset in (40 * 512 + 32, 40 * 512 + 128):
            with self.subTest(offset=offset):
                self.make_image(); self.corrupt(offset)
                with self.assertRaises(ValueError):
                    self.inspect()

    def test_rejects_container_exceeding_store(self):
        for count in (0, 10000):
            with self.subTest(count=count):
                self.make_image(block_count=count)
                with self.assertRaisesRegex(ValueError, 'exceeds physical store'):
                    self.inspect()

    def test_accepts_normal_efi_plus_apfs(self):
        self.make_image(extra=(target.EFI, 1100, 1200))
        self.assertEqual(self.inspect()['container_uuid'], self.uuid)

    def test_runner_separate_writable_opt_in_preserves_readonly_root(self):
        script = (ROOT / 'scripts/run-ibec-usb-restore-smoke.sh').read_text()
        self.assertIn('INSTALL_TARGET_IMAGE="${MACVM_INSTALL_TARGET_IMAGE:-}"', script)
        self.assertIn('EXISTING_BOOT119_INTERNAL', script)
        self.assertIn('installation target and staged BaseSystem root are mutually exclusive', script)
        self.assertIn('file=$ROOT_DRIVE,readonly=on', script)
        self.assertIn('vmapple-virtio-blk-pci,variant=root,drive=macvm-install-internal', script)
        self.assertLess(script.index('"$REPO_ROOT/tools/validate_install_target.py"'),
                        script.index('mkdir -p "$RUN_DIR"'))
        self.assertLess(script.index('drive=macvm-install-internal'),
                        script.index('drive=macvm-recovery-virtio'))

    def test_install_continuation_scopes_runtime_dumps(self):
        script = (ROOT / 'scripts/run-ibec-usb-restore-smoke.sh').read_text()
        self.assertIn('"$GDB_PORT" "$INSTALL_TARGET_IMAGE"', script)
        self.assertIn('scoped = target.parent / name', script)
        self.assertIn("'iBSS.runtime-7006c000-70120000.bin', 'iBEC.runtime-last.bin'", script)
        self.assertIn('text = text.replace(original, scoped)', script)
        launcher = (ROOT / 'scripts/validation-boot120.sh').read_text()
        self.assertIn('OFFLINE_DISKS_COMPLETE', launcher)
        self.assertIn('RESTORE_INPUTS_COMPLETE', launcher)
        self.assertIn('MACVM_PAUSE_ON_REBOOT=YES', launcher)
        self.assertNotIn('eraseDisk', launcher)


if __name__ == '__main__':
    unittest.main()
