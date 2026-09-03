from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/compare_local_installer_copy.pl'


class InstallerCopyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a, self.b = self.root / 'a', self.root / 'b'
        (self.a / 'Contents').mkdir(parents=True)
        (self.a / 'Contents/code').write_bytes(b'test-data\x00' * 9000)
        (self.a / 'Contents/link').symlink_to('code')
        shutil.copytree(self.a, self.b, symlinks=True)
        (self.b / 'Contents/SharedSupport').symlink_to('/test-only-local-product')

    def run_compare(self):
        return subprocess.run(['perl', str(SCRIPT), str(self.a), str(self.b),
                               '/test-only-local-product'], capture_output=True)

    def test_byte_identical_copy(self):
        result = self.run_compare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'files=1 bytes=90000', result.stdout)

    def test_same_size_changed_bytes_rejected(self):
        (self.b / 'Contents/code').write_bytes(b'X' * 90000)
        self.assertNotEqual(self.run_compare().returncode, 0)

    def test_missing_and_extra_entries(self):
        (self.b / 'Contents/extra').write_text('x')
        self.assertNotEqual(self.run_compare().returncode, 0)
        (self.b / 'Contents/extra').unlink()
        (self.b / 'Contents/code').unlink()
        self.assertNotEqual(self.run_compare().returncode, 0)

    def test_symlink_target_rejected(self):
        p = self.b / 'Contents/SharedSupport'
        p.unlink()
        p.symlink_to('/wrong')
        self.assertNotEqual(self.run_compare().returncode, 0)

    def test_mode_change_rejected(self):
        (self.b / 'Contents/code').chmod(0o700)
        self.assertNotEqual(self.run_compare().returncode, 0)

    def test_other_symlink_change_rejected(self):
        p = self.b / 'Contents/link'
        p.unlink()
        p.symlink_to('/etc/passwd')
        self.assertNotEqual(self.run_compare().returncode, 0)
