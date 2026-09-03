"""Exercise the actual live metadata callback without GDB or a guest."""
import ast
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from tools.tmpfs_flags_contract import VA_EXTFLAGS_ACTIVE as E, extended_flags_response


class TmpfsLiveAdapterTests(unittest.TestCase):
    def setUp(self):
        self.vnode, self.node, self.attrs = 0x1000, 0x2000, 0x3000
        self.values = {self.vnode + 0xE0: self.node, self.attrs: 0,
                       self.attrs + 8: 0x200020000603,
                       self.attrs + 0x1A8: 0xDEADBEEF,
                       self.node + 0x14: 2, self.node + 0x3C: 0x80000}
        self.writes = []
        self.counts = {'create': 0, 'existing': 0, 'extflags': 0, 'observed': 0}
        self.lineage = Mock(return_value=(('exec',), [], 0x4000, 0x5000))

        def write(address, data):
            self.assertIn(address, (self.attrs, self.attrs + 0x1A8))
            self.assertEqual(len(data), 8)
            self.writes.append((address, data))
            self.values[address] = struct.unpack('<Q', data)[0]

        self.scope = {
            'gdb': SimpleNamespace(Breakpoint=object, MemoryError=MemoryError,
                selected_inferior=lambda: SimpleNamespace(write_memory=write), write=Mock()),
            'counts': self.counts, 'time': SimpleNamespace(monotonic=lambda: 1),
            'started': 0, 'stop_reason': None, 'struct': struct,
            'reg': {'x20': self.vnode, 'x19': self.node, 'x22': self.attrs}.__getitem__,
            'u64': self.values.__getitem__, 'u32': self.values.__getitem__,
            'repair_existing': False, 'VA_EXTFLAGS_ACTIVE': E,
            'lineage': self.lineage, 'extended_flags_response': extended_flags_response,
        }
        source = Path(__file__).resolve().parents[1] / 'tools/compat_tmpfs_flags_live.py'
        node = next(n for n in ast.parse(source.read_text()).body
                    if isinstance(n, ast.ClassDef) and n.name == 'Bridge')
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), self.scope)
        self.bp = object.__new__(self.scope['Bridge'])
        self.bp.kind = 'existing'

    def test_actual_live_query_shape_receives_only_missing_attribute(self):
        before = self.values.copy()
        self.assertFalse(self.bp.stop())
        self.assertEqual(self.values, before | {self.attrs: E, self.attrs + 0x1A8: 0})
        self.assertEqual(self.counts['extflags'], 1)
        self.assertEqual(self.counts['existing'], 0)
        self.assertEqual([a for a, _ in self.writes], [self.attrs + 0x1A8, self.attrs])

    def test_other_supported_bits_survive(self):
        self.values[self.attrs] = 0x1600450
        self.assertFalse(self.bp.stop())
        self.assertEqual(self.values[self.attrs], 0x1600450 | E)

    def test_outside_anchor_never_writes(self):
        self.lineage.return_value = None
        self.assertFalse(self.bp.stop())
        self.assertEqual(self.writes, [])

    def test_already_supported_does_not_touch_value(self):
        self.values[self.attrs] = E
        self.assertFalse(self.bp.stop())
        self.assertEqual(self.writes, [])
        self.lineage.assert_not_called()

    def test_unrequested_attribute_never_writes(self):
        self.values[self.attrs + 8] = 0x152F7FF
        self.assertFalse(self.bp.stop())
        self.assertEqual(self.writes, [])

    def test_node_mismatch_and_wrong_kind_never_write(self):
        for key, value in ((self.vnode + 0xE0, 0x9999), (self.node + 0x14, 3)):
            original = self.values[key]
            self.values[key] = value
            self.assertFalse(self.bp.stop())
            self.assertEqual(self.writes, [])
            self.values[key] = original

    def test_expired_global_budget_stops_before_scope_or_mutation(self):
        self.counts['observed'] = 100000
        self.assertTrue(self.bp.stop())
        self.assertEqual(self.scope['stop_reason'], 'limit')
        self.assertEqual(self.writes, [])
        self.lineage.assert_not_called()

    def test_contract_error_stops_not_success(self):
        self.lineage.side_effect = ValueError('anchor invalid')
        self.assertTrue(self.bp.stop())
        self.assertEqual(self.scope['stop_reason'], 'error')
        self.assertEqual(self.writes, [])


if __name__ == '__main__':
    unittest.main()
