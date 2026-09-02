#!/usr/bin/env python3
"""Non-destructive validation for a prepared vmapple asset set."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
READY = ROOT / "assets" / "apple" / "ready"


def main() -> int:
    requirements = {
        "AVPBooter.vmapple2.bin": 64 * 1024,
        "aux.img.trimmed": 1 * 1024 * 1024,
        "disk.img": 1 * 1024 * 1024 * 1024,
        "ecid.txt": 1,
    }
    errors: list[str] = []
    for name, minimum_size in requirements.items():
        path = READY / name
        if not path.is_file():
            errors.append(f"missing: {path}")
        elif path.stat().st_size < minimum_size:
            errors.append(f"too small ({path.stat().st_size} bytes): {path}")

    ecid_path = READY / "ecid.txt"
    if ecid_path.is_file():
        value = ecid_path.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|[0-9]+)", value):
            errors.append("ecid.txt must contain one decimal or hexadecimal integer")
        else:
            parsed = int(value, 0)
            if parsed < 0 or parsed > (2**64 - 1):
                errors.append("ECID is outside uint64 range")

    if errors:
        print("vmapple asset preflight: NOT READY", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("vmapple asset preflight: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

