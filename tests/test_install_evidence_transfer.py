import unittest
from pathlib import Path

from tools.receive_boot119_install_evidence import resolve_transfer, TRANSFER_KINDS


class InstallEvidenceTransferTests(unittest.TestCase):
    def test_existing_updatebrain_destination_unchanged(self):
        self.assertEqual(resolve_transfer('updatebrain'), (
            Path('/home/macvm/installation-data/install-analysis/updatebrain-25G83.zip'),
            '/updatebrain.zip',
        ))

    def test_existing_shutdown_destination_unchanged(self):
        self.assertEqual(resolve_transfer('shutdown-logs'), (
            Path('/home/macvm/installation-data/install-analysis/boot119-before-internal-logs.tar.gz'),
            '/shutdown-logs.tar.gz',
        ))

    def test_current_failure_has_separate_destination(self):
        self.assertEqual(resolve_transfer('boot120-personalization-logs'), (
            Path('/home/macvm/installation-data/install-analysis/boot120-personalization-20260903-logs.tar.gz'),
            '/boot120-personalization-logs.tar.gz',
        ))

    def test_destinations_and_endpoints_do_not_collide(self):
        transfers = [resolve_transfer(kind) for kind in TRANSFER_KINDS]
        self.assertEqual(len({p for p, _ in transfers}), len(transfers))
        self.assertEqual(len({e for _, e in transfers}), len(transfers))
        for path, endpoint in transfers:
            self.assertEqual(path.parent, Path('/home/macvm/installation-data/install-analysis'))
            self.assertTrue(endpoint.startswith('/'))
            self.assertEqual(endpoint.count('/'), 1)

    def test_local_prepare_crash_never_overwrites_first_failure(self):
        self.assertEqual(resolve_transfer('boot120-local-prepare-crash'), (
            Path('/home/macvm/installation-data/install-analysis/boot120-local-prepare-crash-20260903-1330.tar.gz'),
            '/boot120-local-prepare-crash.tar.gz',
        ))
        self.assertNotEqual(resolve_transfer('boot120-local-prepare-crash')[0],
                            resolve_transfer('boot120-personalization-logs')[0])

    def test_rejects_non_enum_inputs(self):
        for kind in ('', 'unknown', '../shutdown-logs', '/tmp/logs',
                     'boot120-personalization-logs/../x', 'http://example.com/logs'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                resolve_transfer(kind)


if __name__ == '__main__':
    unittest.main()
