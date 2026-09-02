from pathlib import Path
import shlex
import unittest


class Boot114ContractTests(unittest.TestCase):
    def setUp(self):
        self.text = (Path(__file__).resolve().parents[1] / 'scripts' /
                     'validation-boot114.sh').read_text()
        tokens = shlex.split(self.text.replace('\\\n', ' '), comments=True)
        self.env = dict(token.split('=', 1) for token in tokens if token.startswith('MACVM_'))

    def test_isolated_resources_and_unique_run(self):
        self.assertIn('[[ "$(hostname)" == "macvm-validation" ]] || exit 78', self.text)
        self.assertEqual(self.env['MACVM_DEBUG_ENV_CONFIRMED'], 'YES')
        self.assertEqual(self.env['MACVM_SMOKE_VCPUS'], '8')
        self.assertEqual(self.env['MACVM_SMOKE_MEMORY_GIB'], '16')
        self.assertEqual(self.env['MACVM_RUN_NAME'], 'xnu-imgsrc-reims-boot114-ean-ro-root')

    def test_no_packageslink_write_or_authorization_bypass(self):
        for key in ('MACVM_ALLOW_BASESYSTEM_RW_ROOT', 'MACVM_ALLOW_PACKAGESLINK_SYMLINK',
                    'MACVM_ALLOW_PACKAGESLINK_ROFS_BYPASS',
                    'MACVM_ALLOW_PACKAGESLINK_APFS_ROFS_BYPASS'):
            self.assertEqual(self.env[key], 'NO', key)

    def test_aux_with_prepared_ean_and_isc(self):
        self.assertEqual(self.env['MACVM_EXPOSE_ISC_VIRTIO'], 'YES')
        self.assertEqual(self.env['MACVM_EXPOSE_UTIL_VIRTIO'], 'YES')
        self.assertEqual(self.env['MACVM_ISC_IMAGE'],
                         '/home/macvm/macos-restore/26.6/validation-isc-xart-v3-ean.img')

    def test_release_debugger_on_actual_final_result_not_intermediate_success(self):
        self.assertEqual(self.env['MACVM_DETACH_AFTER_PACKAGESLINK'], 'YES')
        self.assertEqual(self.env['MACVM_DETACH_AFTER_PACKAGESLINK_RESULT'], 'YES')
        self.assertEqual(self.env['MACVM_KEEP_QEMU_RUNNING_AFTER_HELPER'], 'YES')

    def test_boot115_changes_only_binary_and_run_identity(self):
        text = (Path(__file__).resolve().parents[1] / 'scripts' / 'validation-boot115.sh').read_text()
        tokens = shlex.split(text.replace('\\\n', ' '), comments=True)
        env = dict(token.split('=', 1) for token in tokens if token.startswith('MACVM_'))
        changed = {key for key in self.env.keys() | env.keys() if self.env.get(key) != env.get(key)}
        self.assertEqual(changed, {'MACVM_QEMU_BIN', 'MACVM_RUN_NAME', 'MACVM_QEMU_DISPLAY'})
        self.assertEqual(env['MACVM_QEMU_BIN'], '/home/macvm/src/macvm/build/qemu-boot115-timebase/qemu-system-aarch64')

    def test_boot116_keeps_recovery_inputs_and_enables_graphics_validation(self):
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        def settings(name):
            tokens = shlex.split((scripts / name).read_text().replace('\\\n', ' '), comments=True)
            return dict(t.split('=', 1) for t in tokens if t.startswith(('MACVM_', 'REIMS_', 'VK_')))
        previous = settings('validation-boot115.sh')
        current = settings('validation-boot116.sh')
        changed = {key for key in previous.keys() | current.keys() if previous.get(key) != current.get(key)}
        self.assertEqual(changed, {'MACVM_QEMU_BIN', 'MACVM_RUN_NAME', 'MACVM_QEMU_DISPLAY',
                                   'MACVM_GDB_PORT', 'VK_INSTANCE_LAYERS'})
        self.assertEqual(current['MACVM_GDB_PORT'], '12352')
        self.assertEqual(current['MACVM_QEMU_BIN'], '/home/macvm/src/macvm/build/qemu-boot116-attachments/qemu-system-aarch64')
        self.assertEqual(current['VK_INSTANCE_LAYERS'], 'VK_LAYER_KHRONOS_validation')
