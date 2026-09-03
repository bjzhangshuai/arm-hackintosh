"""Exercise the real breakpoint callback without importing/attaching GDB.

The synthetic process uses XNU's actual bounded name fields. The old callback
silently rejected this fixture before it ever reached the pure cleanup planner.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from tools.updatebrain_null_cleanup import (
    PROCESS, EXECUTABLE_UUID, CF_NULL, CF_RETURN, CALLER_RETURN, MASK47,
    is_updatebrain_proc,
)

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/bridge_boot120_null_cleanup.py'


class NullCleanupAdapterTests(unittest.TestCase):
    def setUp(self):
        self.proc, self.thread, self.tro = (0xFFFFFE28D5800000,
                                          0xFFFFFE28D5810000, 0xFFFFFE28D5820000)
        self.regs = {'cpsr': 0, 'TPIDR_EL1': self.thread,
                     'pc': CF_NULL, 'x0': 0, 'sp': 0x16F012000,
                     'x29': 0x16F012000, 'x30': 0x100D80000 + CALLER_RETURN}
        self.fields = {(self.proc + 0x5CC, 17): PROCESS.encode()[:16] + b'\0',
                       (self.proc + 0x5DD, 33): PROCESS.encode()[:32] + b'\0',
                       (self.proc + 0x608, 16): EXECUTABLE_UUID,
                       (self.proc + 0x60, 4): (10125).to_bytes(4, 'little')}
        self.writes, self.logs = [], []
        self.planner = Mock(return_value=CF_RETURN)
        self.user_read = Mock(return_value=bytes(0x204))
        self.memory = Mock(return_value=SimpleNamespace(read=self.user_read))

        def execute(command):
            self.writes.append(command)
            self.assertTrue(command.startswith('set $pc = '))
            self.regs['pc'] = int(command.split(' = ')[1], 0)

        self.scope = {
            'gdb': SimpleNamespace(Breakpoint=object, write=self.logs.append, execute=execute),
            'struct': __import__('struct'), 'reg': self.regs.__getitem__,
            'kernel': lambda a, n: self.fields[a, n],
            'u64': {self.thread + 0x3E8: self.tro, self.tro + 0x18: self.proc}.__getitem__,
            'canonical': lambda value: value,
            'memory': self.memory, 'plan_cleanup': self.planner,
            'is_updatebrain_proc': is_updatebrain_proc, 'PROCESS': PROCESS,
            'MASK47': MASK47, 'CALLER_RETURN': CALLER_RETURN,
            'reference': bytes(0x51510), 'repaired': False,
        }
        tree = ast.parse(SCRIPT.read_text())
        callback = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'NullCleanup')
        exec(compile(ast.Module(body=[callback], type_ignores=[]), str(SCRIPT), 'exec'), self.scope)
        self.bp = self.scope['NullCleanup']()

    def test_truncated_identity_reaches_planner_and_changes_only_pc(self):
        before = self.regs.copy()
        self.assertTrue(self.bp.stop())
        self.planner.assert_called_once()
        self.assertEqual(self.planner.call_args.kwargs['process'], PROCESS)
        self.memory.assert_called_once_with(self.proc)
        self.assertEqual(self.writes, [f'set $pc = {CF_RETURN:#x}'])
        self.assertEqual(self.regs, before | {'pc': CF_RETURN})
        self.assertTrue(self.scope['repaired'])

    def test_name_collision_without_executable_uuid_is_not_a_match(self):
        self.fields[self.proc + 0x608, 16] = bytes(16)
        self.assertFalse(self.bp.stop())
        self.planner.assert_not_called()
        self.memory.assert_not_called()
        self.assertEqual(self.writes, [])

    def test_kernel_mode_never_inspects_process_or_repairs(self):
        self.regs['cpsr'] = 5
        self.assertFalse(self.bp.stop())
        self.planner.assert_not_called()
        self.assertEqual(self.writes, [])

    def test_unrelated_caller_has_no_register_write(self):
        self.planner.return_value = None
        self.assertFalse(self.bp.stop())
        self.assertEqual(self.writes, [])

    def test_planner_contract_failure_stops_without_mutation(self):
        self.planner.side_effect = ValueError('frame mismatch')
        self.assertTrue(self.bp.stop())
        self.assertEqual(self.writes, [])
        self.assertFalse(self.scope['repaired'])
        self.assertIn('BRIDGE_REFUSED', ''.join(self.logs))

    def test_complete_caller_bytes_must_match(self):
        self.user_read.return_value = b'X' + bytes(0x203)
        self.assertTrue(self.bp.stop())
        self.assertEqual(self.writes, [])
        self.assertFalse(self.scope['repaired'])

    def test_repair_budget_is_one_not_one_per_pid(self):
        self.scope['repaired'] = True
        self.assertTrue(self.bp.stop())
        self.assertEqual(self.writes, [])

    def test_unreadable_identity_stops_without_write(self):
        del self.fields[self.proc + 0x608, 16]
        self.assertTrue(self.bp.stop())
        self.assertEqual(self.writes, [])
        self.planner.assert_not_called()
