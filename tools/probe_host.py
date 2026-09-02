#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "host"))

from macvm_host.probe import write_capabilities  # noqa: E402


def require_debug_environment() -> None:
    if os.environ.get("MACVM_DEBUG_ENV_CONFIRMED") != "YES":
        raise SystemExit(
            "macvm: refusing host probe; confirm the dedicated debug host with "
            "MACVM_DEBUG_ENV_CONFIRMED=YES"
        )
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("macvm: host probe requires the dedicated Linux x86_64 debug host")
    marker = Path(os.environ.get("MACVM_DEBUG_MARKER", "/etc/macvm-validation-guest"))
    try:
        marker_lines = marker.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SystemExit(f"macvm: missing isolated validation guest marker: {marker}") from error
    if "MACVM_ISOLATED_VALIDATION_GUEST=YES" not in marker_lines:
        raise SystemExit(f"macvm: invalid isolated validation guest marker: {marker}")
    try:
        detected = subprocess.run(
            ("systemd-detect-virt", "--vm", "--quiet"),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as error:
        raise SystemExit("macvm: systemd-detect-virt is required for the debug-host guard") from error
    if detected.returncode != 0:
        raise SystemExit("macvm: refusing host probe on a physical or unverified host")


def main() -> int:
    require_debug_environment()
    parser = argparse.ArgumentParser(description="Collect MacVM host capabilities as JSON")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "build" / "host-capabilities.json",
    )
    args = parser.parse_args()
    capabilities = write_capabilities(args.output)
    print(json.dumps({"output": str(args.output), "host": capabilities["host"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
