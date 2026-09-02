#!/usr/bin/env python3
"""Exercise bundle guards and asset helpers without running QEMU or touching host resources."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(*args: str | Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        tuple(map(str, args)),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"unexpected exit {result.returncode}, wanted {expected}: {args}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def main() -> int:
    for script in SCRIPTS.glob("*.sh"):
        run("bash", "-n", script)

    run("python3", SCRIPTS / "preflight-assets.py", expected=1)
    run("bash", SCRIPTS / "launch-vmapple-tcg.sh", expected=64)
    run("bash", SCRIPTS / "install-offline-debs.sh", expected=64)

    with tempfile.TemporaryDirectory(prefix="macvm-bundle-self-check.") as directory_name:
        directory = Path(directory_name)
        plist = plistlib.dumps({"ECID": 0x1234})
        export = directory / "macosvm.json"
        export.write_text(
            json.dumps({"machineId": base64.b64encode(plist).decode("ascii")}),
            encoding="utf-8",
        )
        ecid = directory / "ecid.txt"
        run("python3", SCRIPTS / "extract-ecid.py", export, ecid)
        if ecid.read_text(encoding="ascii") != "4660\n":
            raise RuntimeError("ECID extraction produced an unexpected value")

        aux = directory / "aux.img"
        aux.write_bytes(bytes(range(256)) * 257)
        trimmed = directory / "aux.img.trimmed"
        run("bash", SCRIPTS / "trim-aux.sh", aux, trimmed)
        if trimmed.read_bytes() != aux.read_bytes()[0x4000:]:
            raise RuntimeError("AUX trim did not remove exactly 0x4000 bytes")
        run("bash", SCRIPTS / "trim-aux.sh", aux, trimmed, expected=73)

    print("bundle self-check: PASS (no QEMU launch, install, or Apple asset required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

