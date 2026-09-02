#!/usr/bin/env python3
"""Inspect an Apple restore IPSW without extracting guest payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import sys
import zipfile


TOOLS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_ROOT))

from probe_host import require_debug_environment  # noqa: E402


MAX_MANIFEST_BYTES = 64 * 1024 * 1024


class IPSWError(ValueError):
    """Raised when an IPSW cannot satisfy the validation contract."""


def _manifest_member(archive: zipfile.ZipFile, basename: str) -> zipfile.ZipInfo:
    try:
        member = archive.getinfo(basename)
    except KeyError:
        member = None
    if member is not None:
        if member.file_size > MAX_MANIFEST_BYTES:
            raise IPSWError(f"{basename} exceeds {MAX_MANIFEST_BYTES} bytes")
        return member

    matches = [item for item in archive.infolist() if Path(item.filename).name == basename]
    if not matches:
        raise IPSWError(f"missing {basename}")
    if len(matches) != 1:
        raise IPSWError(f"ambiguous {basename}: found {len(matches)} entries")
    if matches[0].file_size > MAX_MANIFEST_BYTES:
        raise IPSWError(f"{basename} exceeds {MAX_MANIFEST_BYTES} bytes")
    return matches[0]


def _load_plist(archive: zipfile.ZipFile, basename: str) -> dict[object, object]:
    member = _manifest_member(archive, basename)
    try:
        value = plistlib.loads(archive.read(member))
    except (OSError, plistlib.InvalidFileException, ValueError) as error:
        raise IPSWError(f"invalid {basename}: {error}") from error
    if not isinstance(value, dict):
        raise IPSWError(f"invalid {basename}: top-level value is not a dictionary")
    return value


def _strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_ipsw(
    path: Path,
    *,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    expected_version: str | None = None,
    expected_build: str | None = None,
    required_product: str | None = None,
) -> dict[str, object]:
    if not path.is_file():
        raise IPSWError(f"IPSW is not a file: {path}")

    size = path.stat().st_size
    if expected_size is not None and size != expected_size:
        raise IPSWError(f"size mismatch: expected {expected_size}, got {size}")

    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise IPSWError(f"ZIP CRC failure: {bad_member}")
            restore = _load_plist(archive, "Restore.plist")
            build = _load_plist(archive, "BuildManifest.plist")
            members = len(archive.infolist())
    except zipfile.BadZipFile as error:
        raise IPSWError(f"invalid IPSW ZIP: {error}") from error

    version = restore.get("ProductVersion")
    build_version = restore.get("ProductBuildVersion")
    if not isinstance(version, str) or not version:
        raise IPSWError("Restore.plist has no ProductVersion")
    if not isinstance(build_version, str) or not build_version:
        raise IPSWError("Restore.plist has no ProductBuildVersion")
    if expected_version is not None and version != expected_version:
        raise IPSWError(f"version mismatch: expected {expected_version}, got {version}")
    if expected_build is not None and build_version != expected_build:
        raise IPSWError(f"build mismatch: expected {expected_build}, got {build_version}")

    products = sorted(
        {
            item
            for item in (*_strings(restore), *_strings(build))
            if re.fullmatch(r"VirtualMac[0-9]+,[0-9]+", item)
        }
    )
    if required_product is not None and required_product not in products:
        raise IPSWError(f"required product is absent: {required_product}")

    sha256 = None
    if expected_sha256 is not None:
        normalized = expected_sha256.lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise IPSWError("expected SHA-256 must be 64 hexadecimal characters")
        sha256 = _sha256(path)
        if sha256 != normalized:
            raise IPSWError(f"SHA-256 mismatch: expected {normalized}, got {sha256}")

    return {
        "path": str(path),
        "size": size,
        "sha256": sha256,
        "product_version": version,
        "product_build_version": build_version,
        "virtual_mac_products": products,
        "zip_members": members,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipsw", type=Path)
    parser.add_argument("--expected-size", type=int)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-build")
    parser.add_argument("--require-product")
    args = parser.parse_args()

    require_debug_environment()
    try:
        result = inspect_ipsw(
            args.ipsw,
            expected_size=args.expected_size,
            expected_sha256=args.expected_sha256,
            expected_version=args.expected_version,
            expected_build=args.expected_build,
            required_product=args.require_product,
        )
    except IPSWError as error:
        print(f"macvm: IPSW validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
