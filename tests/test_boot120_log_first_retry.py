"""Static safety contracts; execute these checks only in macvm-validation."""
from pathlib import Path
import unittest


class LogFirstRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / 'tools' /
                      'guest-retry-boot120-local-archive-b013.sh').read_text()

    def test_exact_guest_and_target_guards(self):
        for token in ('Darwin', 'arm64', 'VirtualMac2,1', '25G72',
                      '31209BA2-BC1F-4D51-99C1-4AFF986CB8AA'):
            self.assertIn(token, self.source)

    def test_archive_is_reused_and_verification_not_disabled(self):
        self.assertIn('19203380932', self.source)
        self.assertIn('OFFLINE_EXPORT_ACCEPTED', self.source)
        self.assertIn('[[ -z $skip || $skip == 0 ]]', self.source)
        self.assertIn('codesign --verify', self.source)
        self.assertNotIn('defaults write', self.source)
        self.assertNotIn('curl ', self.source)

    def test_exclusive_unique_retry(self):
        self.assertIn('LOCAL_RETRY_B013_REQUESTED', self.source)
        self.assertIn('set -o noclobber', self.source)
        self.assertEqual(self.source.count('"$app/Contents/MacOS/InstallAssistant" >>'), 1)
        self.assertNotIn('rm ', self.source)

    def test_log_reader_lifecycle_only(self):
        self.assertIn('tail -n 0 -F /var/log/install.log "$console"', self.source)
        self.assertIn('wait "$installer_pid"', self.source)
        self.assertIn('kill "$tail_pid"', self.source)
        self.assertNotIn('kill "$installer_pid"', self.source)
        self.assertIn('trap finish_logs EXIT', self.source)
        for token in ('pkill', 'killall', 'launchctl ', 'crontab ', 'screendump', 'while '):
            self.assertNotIn(token, self.source)

    def test_no_false_completion_claim(self):
        self.assertIn('phase fractions are not overall installation percent', self.source)
        self.assertIn('COMPLETED alone is not success', self.source)
        self.assertIn('not proof of OS installation success', self.source)


if __name__ == '__main__':
    unittest.main()
