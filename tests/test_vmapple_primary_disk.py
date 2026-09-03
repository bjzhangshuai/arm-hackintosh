"""B016 regressions using tiny synthetic disks, inside isolated Linux only."""
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import vmapple_primary_disk as disk


class PrimaryDiskTests(unittest.TestCase):
    SIZE = 8 * disk.ALIGN

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='macvm-primary-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.sources = tuple(self.root / name for name in ('isc.raw', 'system.raw', 'recovery.raw'))
        self.ids = tuple(uuid.uuid4() for _ in self.sources)
        self.containers = tuple(uuid.uuid4() for _ in self.sources)
        for i, kind in enumerate((disk.ISC, disk.SYSTEM, disk.RECOVERY)):
            self.fixture(self.sources[i], kind, self.ids[i], self.containers[i])
        self.output = self.root / 'composed.raw'

    def fixture(self, path, kind, identity, container, *, efi=False,
                bounds=None, attrs=0, block_count=512, backup_disk=None,
                extra_kind=None, duplicate_identity=False):
        last = self.SIZE // 512 - 1
        entries = bytearray(16384)
        start, end = bounds or (2048, 6143)
        struct.pack_into('<16s16sQQQ72s', entries, 0, kind.bytes_le,
                         identity.bytes_le, start, end, attrs, 'Opaque'.encode('utf-16le'))
        if efi or extra_kind is not None:
            struct.pack_into('<16s16sQQQ72s', entries, 128,
                             (extra_kind or disk.EFI).bytes_le,
                             (identity if duplicate_identity else uuid.uuid4()).bytes_le,
                             8192, 10239, 0, 'EFI'.encode('utf-16le'))
        disk_id = identity
        common = dict(last_usable_lba=last - 33,
                      entries_crc=zlib.crc32(entries) & 0xffffffff)
        nx = bytearray(4096)
        nx[32:36] = b'NXSB'
        struct.pack_into('<IQ', nx, 36, 4096, block_count)
        nx[72:88] = container.bytes
        struct.pack_into('<Q', nx, 0, disk.fletcher64(nx[8:]))
        with path.open('wb') as f:
            f.truncate(self.SIZE)
            for at, data in ((0, disk._protective_mbr(self.SIZE // 512)),
                             (512, disk._gpt_header(current_lba=1, backup_lba=last,
                                                   entries_lba=2, disk_uuid=disk_id, **common)),
                             (1024, entries), ((last - 32) * 512, entries),
                             (last * 512, disk._gpt_header(current_lba=last, backup_lba=1,
                                                        entries_lba=last - 32,
                                                        disk_uuid=backup_disk or disk_id, **common)),
                             (disk.ALIGN, nx), (disk.ALIGN + 8192, b'opaque APFS fixture data'),
                             (3 * disk.ALIGN - 33, b'partition tail must survive')):
                f.seek(at); f.write(data)
            if efi:
                f.seek(4 * disk.ALIGN); f.write(b'preserve EFI content too')

    def parts(self):
        return tuple(p for source in self.sources for p in disk.read_partitions(source)[1])

    def compose(self, **kwargs):
        return disk.compose_offline(kwargs.get('output', self.output),
                                    kwargs.get('sources', self.sources),
                                    closed_backup=kwargs.get('closed_backup', True))

    def test_read_is_bounded_and_nonmutating(self):
        source = self.sources[0]
        before = source.read_bytes()
        identity, parts = disk.read_partitions(source)
        self.assertEqual(identity, self.ids[0])
        self.assertEqual(parts[0].container_uuid, self.containers[0])
        self.assertEqual(before, source.read_bytes())

    def test_canonical_plan_preserves_all_identities_and_lengths(self):
        parts = self.parts()
        size, places = disk.plan_primary_disk(parts)
        self.assertEqual([p.partition for p in places], list(parts))
        self.assertEqual(places[0].offset, 32 * disk.ALIGN)
        for a, b in zip(places, places[1:]):
            self.assertLessEqual(a.offset + a.partition.length, b.offset)
        self.assertLess(places[-1].offset + places[-1].partition.length, size - 33 * 512)

    def test_rejects_boot120_three_primary_devices_in_every_order(self):
        import itertools
        old = (('disk0', True, (disk.EFI, disk.SYSTEM)),
               ('disk1', True, (disk.RECOVERY,)), ('disk2', True, (disk.ISC,)))
        for order in itertools.permutations(old):
            with self.subTest(order=order), self.assertRaisesRegex(ValueError, 'exactly one'):
                disk.validate_primary_topology(order)

    def test_rejects_sibling_isc_even_if_mounted(self):
        with self.assertRaisesRegex(ValueError, 'same primary'):
            disk.validate_primary_topology((('disk0', True, (disk.SYSTEM,)),
                                             ('disk1', False, (disk.ISC, disk.RECOVERY))))

    def test_accepts_single_coherent_primary_and_external_data(self):
        self.assertEqual(disk.validate_primary_topology((
            ('disk0', True, (disk.ISC, disk.EFI, disk.SYSTEM, disk.RECOVERY)),
            ('disk1', False, (disk.SYSTEM,)))), 'disk0')

    def test_rejects_ambiguous_secondary_auxiliary_roles(self):
        for kind in (disk.ISC, disk.RECOVERY):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'ambiguous'):
                disk.validate_primary_topology((('root', True, (disk.ISC, disk.SYSTEM, disk.RECOVERY)),
                                                ('second', False, (kind,))))

    def test_rejects_bad_primary_classification_and_duplicate_names(self):
        for value in ((), (('x', 1, ()),), (('x', True, ()), ('x', False, ())),
                      (('x', False, ()),)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                disk.validate_primary_topology(value)

    def test_composition_preserves_every_partition_byte_and_source(self):
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in self.sources]
        result = self.compose()
        self.assertFalse(result['booted'])
        self.assertFalse(result['installed'])
        self.assertFalse(result['sources_modified'])
        self.assertEqual(result['disk_uuid'], str(self.ids[1]))
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in self.sources])
        _, combined = disk.read_partitions(self.output)
        for old, new in zip(self.parts(), combined):
            self.assertEqual((old.kind, old.identity, old.container_uuid, old.length),
                             (new.kind, new.identity, new.container_uuid, new.length))
            with old.source.open('rb') as f, self.output.open('rb') as g:
                f.seek(old.source_offset); g.seek(new.source_offset)
                self.assertEqual(f.read(old.length), g.read(new.length))
        disk.validate_primary_topology((('root', True, tuple(p.kind for p in combined)),))

    def test_composition_preserves_optional_efi(self):
        self.fixture(self.sources[1], disk.SYSTEM, self.ids[1], self.containers[1], efi=True)
        self.assertEqual(self.compose()['partition_count'], 4)
        parts = disk.read_partitions(self.output)[1]
        self.assertEqual([p.kind for p in parts], [disk.ISC, disk.EFI, disk.SYSTEM, disk.RECOVERY])
        with self.output.open('rb') as f:
            f.seek(parts[1].source_offset)
            expected = b'preserve EFI content too'
            self.assertEqual(f.read(len(expected)), expected)

    def test_no_live_migration_or_implicit_confirmation(self):
        for value in (False, None, 1, 'YES'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'closed backups'):
                self.compose(closed_backup=value)
        self.assertFalse(self.output.exists())

    def test_no_execution_outside_isolation(self):
        with patch.object(disk.os, 'uname') as uname:
            uname.return_value.nodename = 'production'
            with self.assertRaisesRegex(ValueError, 'isolated'):
                self.compose()

    def test_output_never_overwritten(self):
        self.output.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            self.compose()
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_symlink_and_hardlink_inputs_rejected(self):
        link = self.root / 'link.raw'
        link.symlink_to(self.sources[0])
        with self.assertRaises(ValueError):
            disk.read_partitions(link)
        hard = self.root / 'hard.raw'
        os.link(self.sources[0], hard)
        with self.assertRaises(ValueError):
            disk.read_partitions(hard)

    def test_symlink_output_and_parent_rejected(self):
        self.output.symlink_to(self.root / 'missing')
        with self.assertRaises(ValueError):
            self.compose()
        parent = self.root / 'alias'
        parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.compose(output=parent / 'different.raw')

    def test_duplicate_missing_and_wrong_input_order_rejected(self):
        for sources in (self.sources[:2], (self.sources[0],) * 3,
                        (self.sources[1], self.sources[0], self.sources[2])):
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                self.compose(sources=sources)
        self.assertFalse(self.output.exists())

    def test_missing_extra_duplicate_roles_rejected(self):
        parts = self.parts()
        for value in (parts[:2], parts + parts[:1],
                      (replace(parts[0], kind=disk.EFI), *parts[1:])):
            with self.subTest(value=value), self.assertRaises(ValueError):
                disk.plan_primary_disk(value)

    def test_duplicate_partition_or_container_id_rejected(self):
        parts = self.parts()
        for changed in (replace(parts[1], identity=parts[0].identity),
                        replace(parts[1], container_uuid=parts[0].container_uuid),
                        replace(parts[1], container_uuid=None)):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                disk.plan_primary_disk((parts[0], changed, parts[2]))

    def test_opaque_bounds_validation(self):
        parts = self.parts()
        for field, value in (('length', 0), ('length', 513), ('source_offset', 0),
                             ('source_offset', 32769), ('source_size', 1024)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                disk.plan_primary_disk((replace(parts[0], **{field: value}), *parts[1:]))

    def test_metadata_rejects_noncanonical_geometry(self):
        size, places = disk.plan_primary_disk(self.parts())
        for output_size, plan, identity in ((size + disk.ALIGN, places, self.ids[1]),
                                            (size, places[::-1], self.ids[1]),
                                            (size, places, uuid.UUID(int=0)),
                                            (size, (replace(places[0], offset=0), *places[1:]), self.ids[1])):
            with self.subTest(size=output_size), self.assertRaises(ValueError):
                disk.gpt_records(output_size, plan, identity)

    def test_unknown_type_attributes_and_bad_alignment_rejected(self):
        for options in ({'kind': uuid.uuid4()}, {'attrs': 1}, {'bounds': (2049, 6144)},
                        {'bounds': (16, 6143)}, {'bounds': (6143, 2048)},
                        {'bounds': (2048, self.SIZE // 512)}):
            kind = options.get('kind', disk.ISC)
            self.fixture(self.sources[0], kind, self.ids[0], self.containers[0],
                         **{k: v for k, v in options.items() if k != 'kind'})
            with self.subTest(options=options), self.assertRaises(ValueError):
                disk.read_partitions(self.sources[0])

    def test_corruption_rejected_at_all_metadata_layers(self):
        for offset in (450, 510, 512 + 16, 1024, self.SIZE - 512 + 16,
                       self.SIZE - 33 * 512, disk.ALIGN + 32, disk.ALIGN + 120):
            self.fixture(self.sources[0], disk.ISC, self.ids[0], self.containers[0])
            with self.sources[0].open('r+b') as f:
                f.seek(offset); b = f.read(1); f.seek(offset); f.write(bytes([b[0] ^ 1]))
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                disk.read_partitions(self.sources[0])

    def test_mismatched_gpt_uuid_and_apfs_overflow_rejected(self):
        for options in ({'backup_disk': uuid.uuid4()}, {'block_count': 0}, {'block_count': 100000}):
            self.fixture(self.sources[0], disk.ISC, self.ids[0], self.containers[0], **options)
            with self.subTest(options=options), self.assertRaises(ValueError):
                disk.read_partitions(self.sources[0])

    def test_duplicate_partition_uuid_rejected(self):
        self.fixture(self.sources[1], disk.SYSTEM, self.ids[1], self.containers[1],
                     efi=True, duplicate_identity=True)
        with self.assertRaisesRegex(ValueError, 'duplicate partition'):
            disk.read_partitions(self.sources[1])

    def test_no_launcher_or_disk_erasure_in_composer(self):
        source = (ROOT / 'tools/vmapple_primary_disk.py').read_text()
        for forbidden in ('qemu-system-', 'eraseDisk', 'newfs', 'chflags', 'defaults write', 'os.remove', 'unlink('):
            self.assertNotIn(forbidden, source)
        self.assertIn('macvm_require_debug_env', source)

    def test_legacy_split_install_refused_before_any_run_directory_write(self):
        source = (ROOT / 'scripts/run-ibec-usb-restore-smoke.sh').read_text()
        check = source.index('B016 split primary-disk installation topology is invalid')
        self.assertLess(check, source.index('mkdir -p "$RUN_DIR"'))
        self.assertLess(check, source.index('truncate -s 64M "$RUN_DIR/root.img"'))
        self.assertIn('[[ -n "$INSTALL_TARGET_IMAGE" && ( "$EXPOSE_ISC_VIRTIO" == "YES" || "$EXPOSE_RECOVERY_VIRTIO" == "YES" ) ]]', source)

    def test_real_runner_exits_before_touching_paths_or_starting_processes(self):
        for isc, recovery in (('YES', 'NO'), ('NO', 'YES'), ('YES', 'YES')):
            env = {**os.environ, 'MACVM_INSTALL_TARGET_IMAGE': str(self.root / 'never-open.raw'),
                   'MACVM_RUN_ROOT': str(self.root / 'never-created'),
                   'MACVM_EXPOSE_ISC_VIRTIO': isc, 'MACVM_EXPOSE_RECOVERY_VIRTIO': recovery}
            result = subprocess.run(['bash', str(ROOT / 'scripts/run-ibec-usb-restore-smoke.sh')],
                                    env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 78, result.stderr)
            self.assertIn('B016 split primary-disk installation topology is invalid', result.stderr)
            self.assertFalse((self.root / 'never-created').exists())

    def test_output_corruption_is_detected_and_partial_file_preserved(self):
        original = disk.read_partitions

        def inspect(path):
            if path == self.output:
                with path.open('r+b') as f:
                    f.seek(32 * disk.ALIGN + 8192)
                    f.write(b'corruption')
            return original(path)

        with patch.object(disk, 'read_partitions', side_effect=inspect):
            with self.assertRaisesRegex(ValueError, 'byte verification failed'):
                self.compose()
        self.assertTrue(self.output.exists())
        self.assertEqual(len(original(self.sources[0])[1]), 1)

    def test_truncated_or_nonsector_source_size_rejected(self):
        for size in (0, 512, disk.ALIGN + 1):
            with self.sources[0].open('wb') as f:
                f.truncate(size)
            with self.subTest(size=size), self.assertRaises(ValueError):
                disk.read_partitions(self.sources[0])

    def test_source_change_after_metadata_read_is_not_mistaken_for_closed_backup(self):
        original = disk.read_partitions

        def inspect(path):
            result = original(path)
            if path == self.sources[-1]:
                with self.sources[0].open('r+b') as f:
                    f.seek(disk.ALIGN + 8192)
                    f.write(b'changed after GPT inspection')
            return result

        with patch.object(disk, 'read_partitions', side_effect=inspect):
            with self.assertRaisesRegex(ValueError, 'backup identity changed'):
                self.compose()
        self.assertTrue(self.output.exists())  # Keep incomplete evidence, never silently delete it.


if __name__ == '__main__':
    unittest.main()
