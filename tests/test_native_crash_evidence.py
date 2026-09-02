import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('native_crash_evidence', Path(__file__).resolve().parents[1] / 'tools/native_crash_evidence.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NativeCrashEvidenceTests(unittest.TestCase):
    def test_only_readable_executable_mappings_are_eligible(self):
        maps = '1000-9000 r-xp 00000000 00:00 0\n9000-a000 rw-p 00000000 00:00 0'
        self.assertEqual(module.executable_window(maps, 0x1200), (0x1000, 0x9000))
        for pc in (0, -1, 0x9000, 0xa000, 1 << 64):
            self.assertIsNone(module.executable_window(maps, pc))
        self.assertIsNone(module.executable_window('1000-9000 --xp 0 0 0', 0x2000))

    def test_windows_are_bounded_even_for_large_jit_mappings(self):
        maps = '1000-80000000 r-xp 00000000 00:00 0'
        for pc in (0x1000, 0x15000, 0x7fffffff):
            lo, hi = module.executable_window(maps, pc)
            self.assertLessEqual(hi - lo, 65536)
            self.assertLessEqual(lo, pc)
            self.assertLess(pc, hi)
        for limit in (0, -1, 65537):
            self.assertIsNone(module.executable_window(maps, 0x1500, limit))

    def test_malformed_or_ambiguous_mappings_do_not_select_a_window(self):
        for maps in ('garbage', '0-garbage r-xp', '9000-1000 r-xp', '1000-9000 r-xp\n1000-9000 r-xp'):
            self.assertIsNone(module.executable_window(maps, 0x2000))
