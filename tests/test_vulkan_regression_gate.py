import unittest
from tools.vulkan_regression_gate import check


class VulkanRegressionGateTests(unittest.TestCase):
    CLEAN = 'test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;'

    def test_clean_log(self):
        self.assertEqual(check(self.CLEAN, 0, 14)['passed'], 14)

    def test_success_exit_with_driver_error_or_skip_is_not_pass(self):
        for bad in ('VUID-vkDestroyPipeline-pipeline-00765', 'Validation Error: driver',
                    'SKIP: no glslc', 'test result: FAILED.'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                check(self.CLEAN + '\n' + bad, 0, 14)

    def test_process_failure_or_timeout_is_not_pass(self):
        for code in (1, 124, 134, 139, -11):
            with self.assertRaises(ValueError):
                check(self.CLEAN, code, 14)

    def test_incomplete_wrong_count_and_unapproved_ignore_rejected(self):
        for log in ('', 'running 14 tests', self.CLEAN.replace('14 passed', '0 passed'),
                    self.CLEAN.replace('0 ignored', '1 ignored'),
                    self.CLEAN.replace('0 failed', '1 failed')):
            with self.assertRaises(ValueError):
                check(log, 0, 14)

    def test_multiple_suites_and_explicit_performance_ignore(self):
        log = self.CLEAN + '\ntest result: ok. 48 passed; 0 failed; 1 ignored;'
        self.assertEqual(check(log, 0, 62, 1)['ignored'], 1)
        with self.assertRaises(ValueError):
            check(log, 0, 14)
