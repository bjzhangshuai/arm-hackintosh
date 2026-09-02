from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import upstream_audit  # noqa: E402


class UpstreamAuditTests(unittest.TestCase):
    def test_repository_lock_is_satisfied(self) -> None:
        result = upstream_audit.audit(ROOT / "upstreams.lock.toml")
        self.assertTrue(result["ok"], result)

    def test_reports_missing_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "lock.toml"
            lock_path.write_text(
                '''[[upstream]]
name = "missing"
path = "third_party/not-there"
url = "https://example.invalid/repo.git"
commit = "deadbeef"
required_paths = ["README.md"]
''',
                encoding="utf-8",
            )
            result = upstream_audit.audit(lock_path)
        self.assertFalse(result["ok"])
        self.assertIn("submodule directory is missing", result["upstreams"][0]["issues"])

    def _write_lock(
        self,
        directory: Path,
        *,
        commit: str = "a" * 40,
        url: str = "https://example.invalid/upstream.git",
        required_paths: str = '["README.md"]',
    ) -> Path:
        lock = directory / "upstreams.lock.toml"
        lock.write_text(
            f'''schema_version = 1
[[upstream]]
name = "fixture"
path = "third_party/fixture"
url = "{url}"
commit = "{commit}"
required_paths = {required_paths}
''',
            encoding="utf-8",
        )
        return lock

    def test_matching_commit_url_and_required_paths_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            repo = directory / "third_party" / "fixture"
            repo.mkdir(parents=True)
            (repo / "README.md").write_text("fixture", encoding="utf-8")
            lock = self._write_lock(directory)

            def fake_git(_repo: Path, *args: str):
                if args == ("rev-parse", "HEAD"):
                    return 0, "a" * 40, ""
                if args == ("remote", "get-url", "origin"):
                    return 0, "https://example.invalid/upstream.git", ""
                raise AssertionError(args)

            with (
                patch.object(upstream_audit, "REPO_ROOT", directory),
                patch.object(upstream_audit, "_git", side_effect=fake_git),
            ):
                result = upstream_audit.audit(lock)

        self.assertTrue(result["ok"])
        self.assertEqual(result["upstreams"][0]["status"], "ok")
        self.assertEqual(result["upstreams"][0]["issues"], [])

    def test_commit_and_url_mismatches_are_both_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            repo = directory / "third_party" / "fixture"
            repo.mkdir(parents=True)
            (repo / "README.md").write_text("fixture", encoding="utf-8")
            lock = self._write_lock(directory)

            def fake_git(_repo: Path, *args: str):
                if args == ("rev-parse", "HEAD"):
                    return 0, "b" * 40, ""
                return 0, "https://wrong.invalid/repo.git", ""

            with (
                patch.object(upstream_audit, "REPO_ROOT", directory),
                patch.object(upstream_audit, "_git", side_effect=fake_git),
            ):
                result = upstream_audit.audit(lock)

        issues = result["upstreams"][0]["issues"]
        self.assertTrue(any("commit mismatch" in issue for issue in issues))
        self.assertTrue(any("URL mismatch" in issue for issue in issues))

    def test_missing_required_paths_are_reported_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            (directory / "third_party" / "fixture").mkdir(parents=True)
            lock = self._write_lock(
                directory,
                required_paths='["README.md", "src/lib.rs"]',
            )

            def fake_git(_repo: Path, *args: str):
                value = "a" * 40 if args == ("rev-parse", "HEAD") else "https://example.invalid/upstream.git"
                return 0, value, ""

            with (
                patch.object(upstream_audit, "REPO_ROOT", directory),
                patch.object(upstream_audit, "_git", side_effect=fake_git),
            ):
                result = upstream_audit.audit(lock)

        issue_text = "\n".join(result["upstreams"][0]["issues"])
        self.assertIn("README.md", issue_text)
        self.assertIn("src/lib.rs", issue_text)

    def test_existing_non_git_directory_reports_git_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            (directory / "third_party" / "fixture").mkdir(parents=True)
            lock = self._write_lock(directory, required_paths="[]")
            with patch.object(upstream_audit, "REPO_ROOT", directory):
                result = upstream_audit.audit(lock)

        issues = result["upstreams"][0]["issues"]
        self.assertTrue(any("cannot read HEAD" in issue for issue in issues))
        self.assertTrue(any("cannot read origin URL" in issue for issue in issues))

    def test_empty_lock_is_valid_and_has_no_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            lock = Path(directory_name) / "empty.toml"
            lock.write_text("schema_version = 1\n", encoding="utf-8")
            result = upstream_audit.audit(lock)

        self.assertTrue(result["ok"])
        self.assertEqual(result["upstreams"], [])


if __name__ == "__main__":
    unittest.main()
