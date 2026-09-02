from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))

from macvm_host.command import run_command  # noqa: E402


class CommandTests(unittest.TestCase):
    @patch("macvm_host.command.shutil.which", return_value=None)
    def test_missing_executable_is_reported_without_spawning(self, which) -> None:
        with patch("macvm_host.command.subprocess.run") as run:
            result = run_command(("not-installed", "--version"))

        self.assertFalse(result.available)
        self.assertIsNone(result.returncode)
        self.assertEqual(result.command, ("not-installed", "--version"))
        self.assertIn("command not found", result.stderr)
        run.assert_not_called()
        which.assert_called_once_with("not-installed")

    @patch("macvm_host.command.shutil.which", return_value="/usr/bin/tool")
    def test_success_preserves_stdout_stderr_and_environment(self, _which) -> None:
        completed = subprocess.CompletedProcess(
            args=("tool", "arg"), returncode=0, stdout="answer\n", stderr="warning\n"
        )
        with patch("macvm_host.command.subprocess.run", return_value=completed) as run:
            result = run_command(("tool", "arg"), timeout_seconds=7.5, env={"MODE": "test"})

        self.assertTrue(result.available)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "answer\n")
        self.assertEqual(result.stderr, "warning\n")
        run.assert_called_once_with(
            ("tool", "arg"),
            check=False,
            capture_output=True,
            text=True,
            timeout=7.5,
            env={"MODE": "test"},
        )

    @patch("macvm_host.command.shutil.which", return_value="/usr/bin/tool")
    def test_nonzero_exit_is_returned_not_swallowed(self, _which) -> None:
        completed = subprocess.CompletedProcess(
            args=("tool",), returncode=23, stdout="partial", stderr="failed"
        )
        with patch("macvm_host.command.subprocess.run", return_value=completed):
            result = run_command(("tool",))

        self.assertEqual(result.returncode, 23)
        self.assertEqual(result.stdout, "partial")
        self.assertEqual(result.stderr, "failed")

    @patch("macvm_host.command.shutil.which", return_value="/usr/bin/tool")
    def test_timeout_with_text_output_uses_distinct_exit_code(self, _which) -> None:
        timeout = subprocess.TimeoutExpired(("tool",), 1, output="partial", stderr="slow")
        with patch("macvm_host.command.subprocess.run", side_effect=timeout):
            result = run_command(("tool",), timeout_seconds=1)

        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.stdout, "partial")
        self.assertIn("slow", result.stderr)
        self.assertIn("timed out", result.stderr)

    @patch("macvm_host.command.shutil.which", return_value="/usr/bin/tool")
    def test_timeout_decodes_byte_output(self, _which) -> None:
        timeout = subprocess.TimeoutExpired(("tool",), 1, output=b"bytes", stderr=b"late")
        with patch("macvm_host.command.subprocess.run", side_effect=timeout):
            result = run_command(("tool",), timeout_seconds=1)

        self.assertEqual(result.stdout, "bytes")
        self.assertIn("late", result.stderr)


if __name__ == "__main__":
    unittest.main()
