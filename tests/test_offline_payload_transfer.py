import unittest
from tools.receive_boot119_install_evidence import MAX_BYTES, TRANSFER_KINDS, transfer_policy


class OfflinePayloadTransferTests(unittest.TestCase):
    def test_only_fixed_offline_kind_accepts_large_exact_size(self):
        size = 19_203_000_000
        self.assertEqual(transfer_policy('boot120-offline-payload', size), (size, 3600, 120))

    def test_existing_endpoints_keep_original_limits(self):
        for kind in TRANSFER_KINDS:
            if kind != 'boot120-offline-payload':
                self.assertEqual(transfer_policy(kind), (MAX_BYTES, 600, 30))

    def test_size_cannot_expand_any_other_endpoint(self):
        for kind in TRANSFER_KINDS:
            if kind != 'boot120-offline-payload':
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    transfer_policy(kind, 19_203_000_000)

    def test_exact_size_mandatory_and_bounded(self):
        for size in [None, 0, -1, True, '19203000000', 19_203_000_000.0,
                     17_999_999_999, 21_000_000_001, 2**64]:
            with self.subTest(size=size), self.assertRaises(ValueError):
                transfer_policy('boot120-offline-payload', size)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError): transfer_policy('../payload', 19_203_000_000)
