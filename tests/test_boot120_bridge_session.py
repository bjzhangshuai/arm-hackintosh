from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/bridge_boot120_local_install.py'
ENV = {'MACVM_DEBUG_ENV_CONFIRMED': 'YES',
       'MACVM_LOCAL_INSTALL_BRIDGE': 'BOOT120_B010_B012',
       'MACVM_TMPFS_COMPAT_CONFIRMED': 'BOOT120_VERIFIED',
       'MACVM_NULL_CLEANUP_MODE': 'repair-once'}


class BridgeSessionTests(unittest.TestCase):
    def run_session(self, *, fail=None, environment=None, host='macvm-validation'):
        self.events, self.bps = [], []
        inferior = SimpleNamespace(pid=0)

        def attach():
            self.events.append('attach')
            inferior.pid = 1
            if fail == 'identity': raise ValueError('identity refused')

        def install():
            self.events.append('metadata-install')
            if fail == 'metadata': raise ValueError('anchor refused')

        def breakpoint(*args, **kwargs):
            if fail == 'breakpoint': raise ValueError('breakpoint refused')
            bp = SimpleNamespace(valid=True)
            bp.is_valid = lambda: bp.valid
            def delete():
                bp.valid = False
                self.events.append('null-delete')
            bp.delete = delete
            self.bps.append(bp)
            return bp

        def execute(command):
            self.events.append(command)
            if command == 'continue':
                if fail == 'interrupt': raise KeyboardInterrupt()
                if fail == 'continue': raise ValueError('continue refused')
                if fail in ('metadata-limit', 'limit-then-interrupt', 'empty-metadata-limit'):
                    if self.events.count('continue') == 1:
                        metadata.stop_reason = 'limit'
                        if fail != 'empty-metadata-limit': metadata.counts['extflags'] = 1
                        return
                    if fail == 'limit-then-interrupt': raise KeyboardInterrupt()
                if fail in ('metadata-error-stop', 'other-stop'):
                    metadata.stop_reason = 'error' if fail == 'metadata-error-stop' else None
                    return
                if fail == 'repaired-with-limit': metadata.stop_reason = 'limit'
                cleanup.repaired = True
            if command == 'detach': inferior.pid = 0

        cleanup = SimpleNamespace(attach_and_verify=attach, NullCleanup=breakpoint,
                                  CF_NULL=0x187C59468, repaired=False)
        metadata = SimpleNamespace(install_breakpoints=install,
                    remove_breakpoints=lambda: self.events.append('metadata-remove'),
                    stop_reason=None,
                    counts={'create': 0, 'existing': 0, 'extflags': 0, 'observed': 0})
        fakegdb = SimpleNamespace(BP_HARDWARE_BREAKPOINT=1, execute=execute,
                    selected_inferior=lambda: inferior, write=lambda text: None)
        with patch.dict('os.environ', environment or ENV, clear=True), \
             patch('os.uname', return_value=SimpleNamespace(nodename=host)), \
             patch.dict(sys.modules, {'gdb': fakegdb,
                   'bridge_boot120_null_cleanup': cleanup,
                   'compat_tmpfs_flags_live': metadata}), \
             patch.object(sys, 'path', sys.path.copy()):
            runpy.run_path(str(SCRIPT), run_name='__main__')

    def test_single_continue_and_clean_detach(self):
        self.run_session()
        self.assertEqual(self.events, ['attach', 'metadata-install', 'continue',
                                      'null-delete', 'metadata-remove', 'detach'])

    def test_identity_failure_detaches_without_mutators(self):
        with self.assertRaises(ValueError): self.run_session(fail='identity')
        self.assertEqual(self.events, ['attach', 'metadata-remove', 'detach'])

    def test_metadata_failure_detaches(self):
        with self.assertRaises(ValueError): self.run_session(fail='metadata')
        self.assertEqual(self.events[-2:], ['metadata-remove', 'detach'])
        self.assertNotIn('continue', self.events)

    def test_breakpoint_failure_removes_existing_metadata_breakpoints(self):
        with self.assertRaises(ValueError): self.run_session(fail='breakpoint')
        self.assertEqual(self.events[-2:], ['metadata-remove', 'detach'])

    def test_sigint_removes_all_breakpoints_and_detaches(self):
        with self.assertRaises(KeyboardInterrupt): self.run_session(fail='interrupt')
        self.assertEqual(self.events[-3:], ['null-delete', 'metadata-remove', 'detach'])

    def test_continue_error_removes_all_breakpoints_and_detaches(self):
        with self.assertRaises(ValueError): self.run_session(fail='continue')
        self.assertEqual(self.events[-3:], ['null-delete', 'metadata-remove', 'detach'])

    def test_other_host_rejected_before_attach(self):
        with self.assertRaises(RuntimeError): self.run_session(host='production')
        self.assertEqual(self.events, [])

    def test_no_existing_bundle_relabel_allowed(self):
        with self.assertRaises(RuntimeError):
            self.run_session(environment={**ENV, 'MACVM_TMPFS_REPAIR_EXISTING': 'YES'})
        self.assertEqual(self.events, [])

    def test_every_opt_in_required(self):
        for name in ENV:
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                self.run_session(environment={k: v for k, v in ENV.items() if k != name})
            self.assertEqual(self.events, [])

    def test_metadata_budget_retires_only_metadata_before_null_guard_finishes(self):
        self.run_session(fail='metadata-limit')
        self.assertEqual(self.events, ['attach', 'metadata-install', 'continue',
                                      'metadata-remove', 'continue', 'null-delete',
                                      'metadata-remove', 'detach'])

    def test_metadata_error_must_not_resume(self):
        self.run_session(fail='metadata-error-stop')
        self.assertEqual(self.events.count('continue'), 1)
        self.assertEqual(self.events[-3:], ['null-delete', 'metadata-remove', 'detach'])

    def test_metadata_budget_with_no_scoped_response_must_not_resume(self):
        self.run_session(fail='empty-metadata-limit')
        self.assertEqual(self.events.count('continue'), 1)
        self.assertEqual(self.events[-3:], ['null-delete', 'metadata-remove', 'detach'])

    def test_unknown_stop_must_not_resume(self):
        self.run_session(fail='other-stop')
        self.assertEqual(self.events.count('continue'), 1)

    def test_interrupt_after_metadata_retirement_still_cleans_up(self):
        with self.assertRaises(KeyboardInterrupt): self.run_session(fail='limit-then-interrupt')
        self.assertEqual(self.events.count('continue'), 2)
        self.assertEqual(self.events[-3:], ['null-delete', 'metadata-remove', 'detach'])

    def test_repaired_cleanup_does_not_resume_again_even_if_limit_recorded(self):
        self.run_session(fail='repaired-with-limit')
        self.assertEqual(self.events.count('continue'), 1)
