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

    def test_b015_preflight_exits_before_creating_retry_marker(self):
        source = (Path(__file__).resolve().parents[1] / 'tools' /
                  'guest-retry-boot120-local-archive-b015.sh').read_text()
        self.assertIn('case ${1-} in preflight|launch)', source)
        branch = source[source.index('if [[ $mode == preflight ]]'):source.index('marker=')]
        self.assertIn('VERIFY_BRIDGE_LOG_BEFORE_LAUNCH', branch)
        self.assertIn('exit 0', branch)
        self.assertNotIn('InstallAssistant"', branch)
        self.assertIn('LOCAL_RETRY_B015_REQUESTED', source)
        self.assertIn('set -o noclobber', source)
        for forbidden in ('defaults write', 'killall', 'pkill', 'curl ', 'while '):
            self.assertNotIn(forbidden, source)


class B015ProgressSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / 'tools' /
                      'guest-boot120-b015-progress.sh').read_text()

    def test_guest_target_and_attempt_verified_before_output(self):
        guard = self.source[:self.source.index('exec >/dev/console')]
        for token in ('Darwin', 'arm64', 'VirtualMac2,1', '25G72', 'id -u',
                      '31209BA2-BC1F-4D51-99C1-4AFF986CB8AA',
                      'LOCAL_RETRY_B015_REQUESTED', 'LOCAL_ARCHIVE_READY'):
            self.assertIn(token, guard)

    def test_one_shot_readonly_not_installer_or_timer(self):
        for token in ('defaults write', 'kill ', 'killall', 'pkill', 'curl ',
                      'while ', 'sleep ', 'launchctl ', 'crontab ', 'tail -F',
                      'tail -f', 'screendump', 'reboot', 'rm ', 'touch '):
            self.assertNotIn(token, self.source)
        self.assertIn('MACVM_B015_ACTUAL_PROGRESS_END', self.source)

    def test_exact_helper_and_no_false_percent(self):
        self.assertIn('ps -p 10793 -o comm=', self.source)
        self.assertIn('*/osinstallersetupd)', self.source)
        self.assertIn('lsof -nP -o -p 10793', self.source)
        self.assertIn('NO_LSOF', self.source)
        self.assertIn('OFFSETS_NOT_OVERALL_PERCENT', self.source)
        self.assertIn('b015-local-archive-installer-console.log', self.source)


if __name__ == '__main__':
    unittest.main()
