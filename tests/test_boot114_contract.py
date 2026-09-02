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

    def test_boot117_changes_only_verified_binary_storage_and_run_identity(self):
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        def settings(name):
            text = (scripts / name).read_text()
            tokens = shlex.split(text.replace('\\\n', ' '), comments=True)
            return text, dict(t.split('=', 1) for t in tokens if t.startswith(('MACVM_', 'REIMS_', 'VK_')))
        _, previous = settings('validation-boot116.sh')
        text, current = settings('validation-boot117.sh')
        changed = {k for k in previous.keys() | current.keys() if previous.get(k) != current.get(k)}
        self.assertEqual(changed, {'MACVM_QEMU_BIN', 'MACVM_ISC_IMAGE', 'MACVM_RUN_NAME',
                                  'MACVM_QEMU_DISPLAY', 'MACVM_GDB_PORT', 'MACVM_QEMU_TIMEOUT'})
        self.assertEqual(current['MACVM_QEMU_TIMEOUT'], '0s')
        self.assertEqual(current['MACVM_SMOKE_MEMORY_GIB'], '16')
        self.assertEqual(current['MACVM_SMOKE_VCPUS'], '8')
        self.assertIn('refusing to start while another validation ARM guest is running', text)
        self.assertIn('validation-isc-complete-v4-ean.img', current['MACVM_ISC_IMAGE'])

    def test_boot118_preserves_recovery_inputs_and_limits_renderer_changes(self):
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        def settings(name):
            text = (scripts / name).read_text()
            tokens = shlex.split(text.replace('\\\n', ' '), comments=True)
            return text, dict(t.split('=', 1) for t in tokens if t.startswith(('MACVM_', 'REIMS_', 'VK_')))
        _, previous = settings('validation-boot117.sh')
        text, current = settings('validation-boot118.sh')
        changed = {k for k in previous.keys() | current.keys() if previous.get(k) != current.get(k)}
        self.assertEqual(changed, {'MACVM_QEMU_BIN', 'MACVM_RUN_NAME', 'MACVM_QEMU_DISPLAY',
                                  'MACVM_GDB_PORT', 'REIMS_VGPU_CAPTURE_REJECTED_CONTRACTS'})
        self.assertEqual(current['MACVM_QEMU_BIN'], '/home/macvm/src/macvm/build/qemu-boot118-render-contract/qemu-system-aarch64')
        self.assertEqual(current['MACVM_QEMU_TIMEOUT'], '0s')
        self.assertEqual(current['MACVM_SMOKE_VCPUS'], '8')
        self.assertEqual(current['MACVM_SMOKE_MEMORY_GIB'], '16')
        self.assertEqual(current['REIMS_VGPU_CAPTURE_REJECTED_CONTRACTS'], 'YES')
        self.assertIn('refusing to start while another validation ARM guest is running', text)

    def test_boot119_changes_only_tested_binary_and_run_identity(self):
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        def settings(name):
            text = (scripts / name).read_text()
            tokens = shlex.split(text.replace('\\\n', ' '), comments=True)
            return text, dict(t.split('=', 1) for t in tokens if t.startswith(('MACVM_', 'REIMS_', 'VK_')))
        _, previous = settings('validation-boot118.sh')
        text, current = settings('validation-boot119.sh')
        changed = {k for k in previous.keys() | current.keys() if previous.get(k) != current.get(k)}
        self.assertEqual(changed, {'MACVM_QEMU_BIN', 'MACVM_RUN_NAME', 'MACVM_QEMU_DISPLAY', 'MACVM_GDB_PORT',
                                  'REIMS_VGPU_FAIL_LOG', 'REIMS_VGPU_DRAW_LOG_PATH'})
        self.assertEqual(current['MACVM_QEMU_BIN'], '/home/macvm/src/macvm/build/qemu-boot119-graphics-storage/qemu-system-aarch64')
        self.assertEqual(current['MACVM_QEMU_TIMEOUT'], '0s')
        self.assertEqual(current['MACVM_GDB_PORT'], '12355')
        run = '/home/macvm/runs/aux-26.6/' + current['MACVM_RUN_NAME']
        self.assertEqual(current['REIMS_VGPU_FAIL_LOG'], run + '/reims-fail.log')
        self.assertEqual(current['REIMS_VGPU_DRAW_LOG_PATH'], run + '/reims-draw.log')
        self.assertIn('refusing to start while another validation ARM guest is running', text)
