from pathlib import Path
import unittest
from tools.check_vmapple_timebase import EXPECTED_HZ, parse_memory, validate_sample


class TimebaseContractTests(unittest.TestCase):
    def test_actual_counter_and_expiry(self):
        first = [EXPECTED_HZ, 100, 5_000_100, 0, 0]
        last = [EXPECTED_HZ, 100, 53_780_588, 24_000_102, 1]
        self.assertAlmostEqual(validate_sample(first, last, 2), 24_390_244)

    def test_reject_wrong_register_rate_and_expiry(self):
        first = [EXPECTED_HZ, 100, 5_000_100, 0, 0]
        last = [EXPECTED_HZ, 100, 53_780_588, 24_000_102, 1]
        for slot, value in ((0, 1_000_000_000), (2, 2_000_000_100), (2, 0), (3, 24_000_099), (4, 0)):
            bad = last.copy()
            bad[slot] = value
            with self.subTest(slot=slot, value=value), self.assertRaises(ValueError):
                validate_sample(first, bad, 2)
        with self.assertRaises(ValueError):
            validate_sample(first, last, 0)

    def test_monitor_values_exclude_addresses(self):
        text = '0000000070000000: 0x1 0x2\n0000000070000010: 0x3 0x4\n0000000070000020: 0x5\n'
        self.assertEqual(parse_memory(text), [1, 2, 3, 4, 5])
        with self.assertRaises(ValueError):
            parse_memory('bad response')

    def test_board_only_tcg_and_pre_realization_patch(self):
        root = Path(__file__).resolve().parents[1]
        patch = (root / 'patches/qemu/0033-vmapple-match-tcg-counter-to-apple-timebase.patch').read_text()
        self.assertIn('+        if (tcg_enabled()) {', patch)
        self.assertIn('+            object_property_set_int(cpu, "cntfrq", 24000000, &error_fatal);', patch)
        self.assertIn('cpu = object_new(possible_cpus->cpus[n].type)', patch)
        self.assertNotIn('diff --git a/target/arm/helper.c', patch)
