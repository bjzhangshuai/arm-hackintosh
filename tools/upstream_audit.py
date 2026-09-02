#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tomllib
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def audit(lock_path: Path) -> dict[str, Any]:
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    ok = True

    for entry in lock.get("upstream", []):
        path = REPO_ROOT / entry["path"]
        issues: list[str] = []
        if not path.is_dir():
            issues.append("submodule directory is missing")
            actual_commit = None
            actual_url = None
        else:
            rc, actual_commit, error = _git(path, "rev-parse", "HEAD")
            if rc != 0:
                issues.append(f"cannot read HEAD: {error}")
                actual_commit = None
            rc, actual_url, error = _git(path, "remote", "get-url", "origin")
            if rc != 0:
                issues.append(f"cannot read origin URL: {error}")
                actual_url = None

        if actual_commit != entry["commit"]:
            issues.append(f"commit mismatch: expected {entry['commit']}, got {actual_commit}")
        if actual_url != entry["url"]:
            issues.append(f"URL mismatch: expected {entry['url']}, got {actual_url}")

        missing_paths = [
            relative for relative in entry.get("required_paths", []) if not (path / relative).exists()
        ]
        if missing_paths:
            issues.append("missing required paths: " + ", ".join(missing_paths))

        record = {
            "name": entry["name"],
            "path": entry["path"],
            "expected_commit": entry["commit"],
            "actual_commit": actual_commit,
            "origin": actual_url,
            "status": "ok" if not issues else "error",
            "issues": issues,
        }
        records.append(record)
        ok = ok and not issues

    return {"schema_version": 1, "ok": ok, "upstreams": records}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify pinned MacVM upstream source trees")
    parser.add_argument("--lock", type=Path, default=REPO_ROOT / "upstreams.lock.toml")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    result = audit(args.lock)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for upstream in result["upstreams"]:
            print(f"{upstream['status'].upper():5} {upstream['name']} {upstream['actual_commit']}")
            for issue in upstream["issues"]:
                print(f"      {issue}", file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
