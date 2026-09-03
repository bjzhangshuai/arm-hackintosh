import unittest
from unittest.mock import patch

from tools.observe_boot120_tasks_qmp import main, validate_wanted_pids


class TaskSelectionTests(unittest.TestCase):
    def test_default_and_bounded_exact_pids(self):
        self.assertIsNone(validate_wanted_pids(None))
        for pids in (frozenset({1}), frozenset(range(1, 9)), frozenset({999999})):
            self.assertIs(validate_wanted_pids(pids), pids)

    def test_invalid_scope_rejected_before_environment_or_qmp(self):
        for value in ({1}, [1], 1, frozenset(), frozenset(range(1, 10)),
                      frozenset({0}), frozenset({-1}), frozenset({1000000}),
                      frozenset({True}), frozenset({1.0}), frozenset({'1'})):
            with self.subTest(value=value), patch('tools.observe_boot120_tasks_qmp.QMPClient') as qmp:
                with self.assertRaises(ValueError):
                    main(wanted_pids=value)
                qmp.assert_not_called()


if __name__ == '__main__':
    unittest.main()
