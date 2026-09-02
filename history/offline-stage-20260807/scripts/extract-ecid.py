#!/usr/bin/env python3
"""Extract the ECID used by QEMU vmapple from a macosvm JSON export."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import plistlib
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("macosvm_json", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    document = json.loads(args.macosvm_json.read_text(encoding="utf-8"))
    encoded = document.get("machineId")
    if not isinstance(encoded, str) or not encoded:
        raise SystemExit("missing non-empty machineId in macosvm JSON")

    try:
        machine_id = plistlib.loads(base64.b64decode(encoded, validate=True))
    except (ValueError, plistlib.InvalidFileException) as error:
        raise SystemExit(f"invalid base64/plist machineId: {error}") from error

    ecid = machine_id.get("ECID") if isinstance(machine_id, dict) else None
    if not isinstance(ecid, int) or ecid < 0 or ecid > (2**64 - 1):
        raise SystemExit("machineId plist does not contain a uint64 ECID")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".ecid.", dir=args.output.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"{ecid}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, args.output)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

