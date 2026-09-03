import unittest
from unittest.mock import Mock

from tools.qmp_keyboard import accepted_events, key_event, press, text_keys, type_text
from tools.qmp_screendump import QMPError


class KeyboardTests(unittest.TestCase):
    def test_success_once(self):
        c = Mock()
        accepted_events(c, [key_event('a', True)])
        c.execute.assert_called_once_with('input-send-event', {'events': [key_event('a', True)]})

    def test_only_explicit_pre_delivery_rejection_can_repeat(self):
        c, sleep = Mock(), Mock()
        c.execute.side_effect = [QMPError("{'desc': 'VM not running'}"), {}]
        accepted_events(c, [key_event('a', True)], sleep=sleep)
        self.assertEqual(c.execute.call_count, 2)
        self.assertEqual(c.execute.call_args_list[0], c.execute.call_args_list[1])
        sleep.assert_called_once_with(0.05)

    def test_rejections_are_bounded(self):
        c = Mock()
        c.execute.side_effect = QMPError("{'desc': 'VM not running'}")
        with self.assertRaises(QMPError):
            accepted_events(c, [], sleep=Mock(), attempts=3)
        self.assertEqual(c.execute.call_count, 3)

    def test_unknown_errors_never_repeat(self):
        for error in (QMPError('input handler missing'), OSError('connection closed')):
            c = Mock()
            c.execute.side_effect = error
            with self.subTest(error=error), self.assertRaises(type(error)):
                accepted_events(c, [], sleep=Mock())
            self.assertEqual(c.execute.call_count, 1)

    def test_modifier_released_in_reverse_order(self):
        c = Mock()
        press(c, ['ctrl', 'u'], sleep=Mock())
        self.assertEqual(c.execute.call_args_list[0].args[1]['events'],
                         [key_event('ctrl', True), key_event('u', True)])
        self.assertEqual(c.execute.call_args_list[1].args[1]['events'],
                         [key_event('u', False), key_event('ctrl', False)])

    def test_mapping(self):
        self.assertEqual(text_keys('aA1 :>&_'),
                         [['a'], ['shift', 'a'], ['1'], ['spc'], ['shift', 'semicolon'],
                          ['shift', 'dot'], ['shift', '7'], ['shift', 'minus']])

    def test_validate_all_before_clearing_or_typing(self):
        c = Mock()
        with self.assertRaises(ValueError):
            type_text(c, 'abc\n', clear=True, sleep=Mock())
        c.execute.assert_not_called()

    def test_no_implicit_enter_resume_or_reset(self):
        c = Mock()
        type_text(c, 'abc', clear=True, sleep=Mock())
        self.assertEqual(c.execute.call_count, 8)
        for call in c.execute.call_args_list:
            self.assertEqual(call.args[0], 'input-send-event')
            self.assertNotIn('ret', [e['data']['key']['data'] for e in call.args[1]['events']])


if __name__ == '__main__':
    unittest.main()
