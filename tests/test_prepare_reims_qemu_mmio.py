from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "prepare_reims_qemu_mmio.py"
PINNED_SHIM = (
    ROOT
    / "third_party"
    / "reims-vgpu"
    / "vendor"
    / "qemu"
    / "hw"
    / "display"
    / "reims-vgpu-mmio.c"
)

spec = importlib.util.spec_from_file_location("prepare_reims_qemu_mmio", TOOL)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrepareReimsQemuMmioTests(unittest.TestCase):
    def test_pinned_source_gets_linux_host_adapters_and_headless_poll(self) -> None:
        source = PINNED_SHIM.read_text(encoding="utf-8")
        result = module.prepare(source)

        self.assertIn('#include "exec/gdbstub.h"', result)
        self.assertIn("gdb_read_register(cs, reg, index)", result)
        self.assertIn("REIMS_VGPU_GUEST_PAGE_SHIFT_ARM64E", result)
        self.assertIn("hva != base + i * page", result)
        self.assertIn(".map_pages_stable = 1,", result)
        self.assertNotIn(".map_pages_stable = 0,", result)
        self.assertNotIn(
            "(void)index;\n    (void)out;\n    return -1;\n#endif",
            result,
        )
        self.assertIn("The poll loop is a device requirement", result)
        self.assertNotIn(module.WINDOW_TIMER_OLD, result)
        self.assertEqual(result.count("s->poll_timer = timer_new_ms("), 1)
        self.assertGreater(
            result.index("s->poll_timer = timer_new_ms("),
            result.index("host window unavailable rc=%d"),
        )

    def test_every_transform_is_single_occurrence(self) -> None:
        result = module.prepare(PINNED_SHIM.read_text(encoding="utf-8"))

        self.assertEqual(result.count("gdb_read_register(cs, reg, index)"), 1)
        self.assertEqual(result.count("static int reims_vgpu_mmio_map_pages("), 1)
        self.assertEqual(result.count(".map_pages_stable = 1,"), 1)
        self.assertEqual(result.count("The poll loop is a device requirement"), 1)

    def test_changed_source_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing start marker"):
            module.prepare('#include "hw/core/cpu.h"\n')

    def test_changed_timer_block_fails_closed(self) -> None:
        source = PINNED_SHIM.read_text(encoding="utf-8")
        changed = source.replace(
            "s->poll_timer = timer_new_ms(QEMU_CLOCK_HOST,",
            "s->poll_timer = timer_new_ns(QEMU_CLOCK_HOST,",
            1,
        )
        with self.assertRaisesRegex(ValueError, "window-coupled poll timer"):
            module.prepare(changed)

    def test_cli_writes_generated_source(self) -> None:
        source = PINNED_SHIM.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            source_path = Path(td) / "input.c"
            output_path = Path(td) / "output.c"
            source_path.write_text(source, encoding="utf-8")

            self.assertEqual(
                module.main.__module__,
                "prepare_reims_qemu_mmio",
            )
            output_path.write_text(module.prepare(source), encoding="utf-8")
            self.assertIn(
                "The poll loop is a device requirement",
                output_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
