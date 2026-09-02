from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("macvm_probe_cli", ROOT / "tools" / "probe_host.py")
assert SPEC and SPEC.loader
PROBE_CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE_CLI)


class PythonEnvironmentGuardTests(unittest.TestCase):
    def test_refuses_without_explicit_confirmation(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "refusing host probe"):
                PROBE_CLI.require_debug_environment()

    def test_refuses_confirmed_non_linux_host(self) -> None:
        with (
            patch.dict(os.environ, {"MACVM_DEBUG_ENV_CONFIRMED": "YES"}, clear=True),
            patch.object(PROBE_CLI.platform, "system", return_value="Darwin"),
            patch.object(PROBE_CLI.platform, "machine", return_value="x86_64"),
        ):
            with self.assertRaisesRegex(SystemExit, "Linux x86_64"):
                PROBE_CLI.require_debug_environment()

    def test_refuses_confirmed_non_x86_linux_host(self) -> None:
        with (
            patch.dict(os.environ, {"MACVM_DEBUG_ENV_CONFIRMED": "YES"}, clear=True),
            patch.object(PROBE_CLI.platform, "system", return_value="Linux"),
            patch.object(PROBE_CLI.platform, "machine", return_value="aarch64"),
        ):
            with self.assertRaisesRegex(SystemExit, "Linux x86_64"):
                PROBE_CLI.require_debug_environment()

    def test_accepts_explicitly_confirmed_linux_x86_64(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker"
            marker.write_text("MACVM_ISOLATED_VALIDATION_GUEST=YES\n", encoding="utf-8")
            with (
                patch.dict(
                    os.environ,
                    {
                        "MACVM_DEBUG_ENV_CONFIRMED": "YES",
                        "MACVM_DEBUG_MARKER": str(marker),
                    },
                    clear=True,
                ),
                patch.object(PROBE_CLI.platform, "system", return_value="Linux"),
                patch.object(PROBE_CLI.platform, "machine", return_value="x86_64"),
                patch.object(
                    PROBE_CLI.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess((), 0),
                ),
            ):
                PROBE_CLI.require_debug_environment()

    def test_refuses_without_isolated_guest_marker(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "MACVM_DEBUG_ENV_CONFIRMED": "YES",
                    "MACVM_DEBUG_MARKER": "/definitely/missing/macvm-marker",
                },
                clear=True,
            ),
            patch.object(PROBE_CLI.platform, "system", return_value="Linux"),
            patch.object(PROBE_CLI.platform, "machine", return_value="x86_64"),
        ):
            with self.assertRaisesRegex(SystemExit, "missing isolated validation guest marker"):
                PROBE_CLI.require_debug_environment()

    def test_refuses_malformed_isolated_guest_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker"
            marker.write_text("MACVM_ISOLATED_VALIDATION_GUEST=NO\n", encoding="utf-8")
            with (
                patch.dict(
                    os.environ,
                    {
                        "MACVM_DEBUG_ENV_CONFIRMED": "YES",
                        "MACVM_DEBUG_MARKER": str(marker),
                    },
                    clear=True,
                ),
                patch.object(PROBE_CLI.platform, "system", return_value="Linux"),
                patch.object(PROBE_CLI.platform, "machine", return_value="x86_64"),
            ):
                with self.assertRaisesRegex(SystemExit, "invalid isolated validation guest marker"):
                    PROBE_CLI.require_debug_environment()

    def test_refuses_physical_host_even_with_valid_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker"
            marker.write_text("MACVM_ISOLATED_VALIDATION_GUEST=YES\n", encoding="utf-8")
            with (
                patch.dict(
                    os.environ,
                    {
                        "MACVM_DEBUG_ENV_CONFIRMED": "YES",
                        "MACVM_DEBUG_MARKER": str(marker),
                    },
                    clear=True,
                ),
                patch.object(PROBE_CLI.platform, "system", return_value="Linux"),
                patch.object(PROBE_CLI.platform, "machine", return_value="x86_64"),
                patch.object(
                    PROBE_CLI.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess((), 1),
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "physical or unverified host"):
                    PROBE_CLI.require_debug_environment()


class ShellEnvironmentGuardContractTests(unittest.TestCase):
    def test_all_execution_entrypoints_use_the_debug_host_guard(self) -> None:
        guarded_scripts = (
            "build.sh",
            "build-performance.sh",
            "check-vmapple-machine.sh",
            "probe-host.sh",
            "run-ibec-usb-restore-smoke.sh",
            "test.sh",
        )
        for name in guarded_scripts:
            with self.subTest(script=name):
                text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
                self.assertIn('source "$SCRIPT_DIR/lib/require-debug-env.sh"', text)
                self.assertIn("macvm_require_debug_env", text)

    def test_guard_requires_exact_confirmation_not_truthy_value(self) -> None:
        text = (ROOT / "scripts" / "lib" / "require-debug-env.sh").read_text(encoding="utf-8")
        self.assertIn('${MACVM_DEBUG_ENV_CONFIRMED:-}" != "YES"', text)
        self.assertIn('"$(uname -s)" != "Linux"', text)
        self.assertIn('"$(uname -m)" != "x86_64"', text)
        self.assertIn("MACVM_ISOLATED_VALIDATION_GUEST=YES", text)
        self.assertIn("systemd-detect-virt --vm --quiet", text)


if __name__ == "__main__":
    unittest.main()
