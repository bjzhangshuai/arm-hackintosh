from pathlib import Path
import unittest


class GDBPythonSyntaxTests(unittest.TestCase):
    def test_embedded_python_blocks_compile_without_executing(self):
        root = Path(__file__).resolve().parents[1] / 'tools'
        for name in ('probe_allproc_names_live.gdb',
                     'probe_timebase_live.gdb',
                     'inject_basesystem_auth_and_boot_args_trace_mount.gdb',
                     'trace_basesystem_symlink_preflight_live.gdb'):
            with self.subTest(name=name):
                blocks = []
                current = None
                for line in (root / name).read_text().splitlines():
                    if current is None and line.strip() == 'python':
                        current = []
                    elif current is not None and line.strip() == 'end':
                        blocks.append('\n'.join(current))
                        current = None
                    elif current is not None:
                        current.append(line)
                self.assertIsNone(current, 'unterminated GDB Python block')
                self.assertTrue(blocks)
                for index, block in enumerate(blocks):
                    compile(block, f'{name}:python-block-{index}', 'exec')
