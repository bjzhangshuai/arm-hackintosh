from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from tmpfs_flags_contract import ANCHOR, SF_RESTRICTED, verified_boot120_identity


class BootIdentityTests(unittest.TestCase):
    def good(self):
        return {'boot': 120, 'qemu_pid': 974460, 'slide': 0x19344000,
                'anchor_vnode': 0xfffffe1000001000, 'anchor_node': 0xfffffe1000002000,
                'anchor_flags': SF_RESTRICTED, 'leaf_to_root': list(ANCHOR),
                'read_only_observation': True}

    def test_separate_new_boot_observation(self):
        self.assertEqual(verified_boot120_identity(self.good()),
                         (0x19344000, 0xfffffe1000001000, 0xfffffe1000002000))

    def test_reject_wrong_identity_and_missing_provenance(self):
        for field, value in [('boot', 119), ('boot', True), ('qemu_pid', 925112),
                             ('qemu_pid', '974460'), ('slide', 0), ('slide', '0x19344000'),
                             ('read_only_observation', False), ('read_only_observation', 1),
                             ('leaf_to_root', ['tmp'] + list(ANCHOR)),
                             ('anchor_flags', 0), ('anchor_flags', True)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                verified_boot120_identity({**self.good(), field: value})

    def test_reject_unbounded_or_unaligned_pointers(self):
        for field in ('anchor_vnode', 'anchor_node'):
            for value in (0, -1, 0x30201014, 0xfffffe1000001001, 1 << 64, None, True):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    verified_boot120_identity({**self.good(), field: value})

    def test_reject_missing_fields(self):
        for field in self.good():
            record = self.good(); del record[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                verified_boot120_identity(record)

    def test_reject_non_records(self):
        for record in (None, [], True, 974460):
            with self.subTest(record=record), self.assertRaises(ValueError):
                verified_boot120_identity(record)


if __name__ == '__main__':
    unittest.main()
