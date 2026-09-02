#!/usr/bin/env python3
"""Extract the restore assets iBEC needs from an Apple VirtualMac IPSW.

This tool deliberately does not decrypt or transform Apple payloads.  It only
selects the correct VirtualMac build identity, validates the member paths, and
stages the restore kernelcache, DeviceTree, ramdisk, and trust cache so later
QEMU/iBEC experiments can construct a real restore descriptor table instead of
guessing at missing objects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import sys
import tempfile
import zipfile


TOOLS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_ROOT))

from probe_host import require_debug_environment  # noqa: E402


MAX_MANIFEST_BYTES = 64 * 1024 * 1024
CHUNK_BYTES = 8 * 1024 * 1024

REQUIRED_RESTORE_ASSETS = (
    "RestoreKernelCache",
    "RestoreDeviceTree",
    "RestoreRamDisk",
    "RestoreTrustCache",
)

OPTIONAL_RESTORE_ASSETS = (
    "OS",
    "BaseSystem",
    "StaticTrustCache",
)


class RestoreBundleError(ValueError):
    """Raised when an IPSW cannot provide a valid restore bundle."""


def _safe_archive_path(path: object, *, role: str) -> str:
    if not isinstance(path, str) or not path:
        raise RestoreBundleError(f"{role} has no archive path")
    if "\\" in path:
        raise RestoreBundleError(f"{role} uses a non-POSIX archive path: {path!r}")
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise RestoreBundleError(f"{role} uses an unsafe archive path: {path!r}")
    return path


def _manifest_member(archive: zipfile.ZipFile, basename: str) -> zipfile.ZipInfo:
    try:
        member = archive.getinfo(basename)
    except KeyError:
        member = None
    if member is not None:
        if member.file_size > MAX_MANIFEST_BYTES:
            raise RestoreBundleError(f"{basename} exceeds {MAX_MANIFEST_BYTES} bytes")
        return member

    matches = [item for item in archive.infolist() if PurePosixPath(item.filename).name == basename]
    if not matches:
        raise RestoreBundleError(f"missing {basename}")
    if len(matches) != 1:
        raise RestoreBundleError(f"ambiguous {basename}: found {len(matches)} entries")
    if matches[0].file_size > MAX_MANIFEST_BYTES:
        raise RestoreBundleError(f"{basename} exceeds {MAX_MANIFEST_BYTES} bytes")
    return matches[0]


def _load_plist(archive: zipfile.ZipFile, basename: str) -> dict[object, object]:
    member = _manifest_member(archive, basename)
    try:
        value = plistlib.loads(archive.read(member))
    except (OSError, plistlib.InvalidFileException, ValueError) as error:
        raise RestoreBundleError(f"invalid {basename}: {error}") from error
    if not isinstance(value, dict):
        raise RestoreBundleError(f"invalid {basename}: top-level value is not a dictionary")
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


def _component_path(identity: dict[object, object], role: str) -> str | None:
    manifest = identity.get("Manifest")
    if not isinstance(manifest, dict):
        return None
    component = manifest.get(role)
    if not isinstance(component, dict):
        return None
    info = component.get("Info")
    if not isinstance(info, dict):
        return None
    path = info.get("Path")
    if path is None:
        return None
    return _safe_archive_path(path, role=role)


def _identity_info(identity: dict[object, object]) -> dict[object, object]:
    info = identity.get("Info")
    if not isinstance(info, dict):
        return {}
    return info


def _variant_text(identity: dict[object, object]) -> str:
    info = _identity_info(identity)
    values: list[str] = []
    for key in ("Variant", "RestoreBehavior", "Description"):
        value = info.get(key)
        if isinstance(value, str):
            values.append(value)
    contents = info.get("VariantContents")
    if isinstance(contents, (list, tuple)):
        values.extend(item for item in contents if isinstance(item, str))
    return " ".join(values).lower()


def _matches_variant(identity: dict[object, object], variant: str) -> bool:
    if variant == "any":
        return True
    text = _variant_text(identity)
    if variant == "erase":
        return "erase" in text
    if variant == "upgrade":
        return "upgrade" in text or "update" in text
    raise RestoreBundleError(f"unsupported variant selector: {variant}")


def _identity_matches(
    identity: dict[object, object],
    *,
    product: str,
    device_class: str,
    variant: str,
    build_manifest: dict[object, object],
) -> bool:
    info = _identity_info(identity)
    if info.get("DeviceClass") != device_class:
        return False

    all_strings = set(_strings(identity)) | set(_strings(build_manifest.get("SupportedProductTypes")))
    if product not in all_strings:
        return False

    if not _matches_variant(identity, variant):
        return False

    return all(_component_path(identity, role) is not None for role in REQUIRED_RESTORE_ASSETS)


def _select_identity(
    build_manifest: dict[object, object],
    *,
    product: str,
    device_class: str,
    variant: str,
) -> tuple[int, dict[object, object]]:
    identities = build_manifest.get("BuildIdentities")
    if not isinstance(identities, list):
        raise RestoreBundleError("BuildManifest.plist has no BuildIdentities array")

    candidates: list[tuple[int, dict[object, object]]] = []
    rejected_for_missing_assets = False
    for index, item in enumerate(identities):
        if not isinstance(item, dict):
            continue
        info = _identity_info(item)
        if info.get("DeviceClass") != device_class:
            continue
        if product not in (set(_strings(item)) | set(_strings(build_manifest.get("SupportedProductTypes")))):
            continue
        if not _matches_variant(item, variant):
            continue
        missing = [role for role in REQUIRED_RESTORE_ASSETS if _component_path(item, role) is None]
        if missing:
            rejected_for_missing_assets = True
            continue
        candidates.append((index, item))

    if not candidates:
        detail = " but matching identities lacked required restore assets" if rejected_for_missing_assets else ""
        raise RestoreBundleError(
            f"no {product} {device_class} {variant} restore build identity{detail}"
        )
    if len(candidates) > 1:
        indexes = ", ".join(str(index) for index, _ in candidates)
        raise RestoreBundleError(
            f"ambiguous {product} {device_class} {variant} restore build identity: {indexes}"
        )
    return candidates[0]


def _zip_member(archive: zipfile.ZipFile, member_path: str, *, role: str) -> zipfile.ZipInfo:
    member_path = _safe_archive_path(member_path, role=role)
    try:
        info = archive.getinfo(member_path)
    except KeyError as error:
        raise RestoreBundleError(f"{role} member is missing from IPSW: {member_path}") from error
    if info.is_dir():
        raise RestoreBundleError(f"{role} member is a directory: {member_path}")
    unsafe_name = _safe_archive_path(info.filename, role=role)
    if unsafe_name != member_path:
        raise RestoreBundleError(f"{role} member path mismatch: {unsafe_name!r} != {member_path!r}")
    return info


def _destination_for(out_dir: Path, archive_path: str, *, role: str) -> Path:
    leaf = PurePosixPath(archive_path).name
    if not leaf or leaf in (".", ".."):
        raise RestoreBundleError(f"{role} has no safe output file name: {archive_path!r}")
    destination = out_dir / leaf
    try:
        destination.relative_to(out_dir)
    except ValueError as error:
        raise RestoreBundleError(f"{role} output path escapes bundle directory") from error
    return destination


def _sha256_existing(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    destination: Path,
    *,
    force: bool,
) -> tuple[int, str]:
    digest = hashlib.sha256()
    if destination.exists() and not force:
        existing_size = destination.stat().st_size
        existing_digest = _sha256_existing(destination)
        if existing_size == info.file_size:
            with archive.open(info) as source:
                for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
                    digest.update(chunk)
            if digest.hexdigest() == existing_digest:
                return existing_size, existing_digest
        raise RestoreBundleError(f"refusing to overwrite existing asset without --force: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with archive.open(info) as source:
            with tempfile.NamedTemporaryFile(
                "wb",
                delete=False,
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
            ) as output:
                temp_name = output.name
                written = 0
                for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
                    output.write(chunk)
                    digest.update(chunk)
                    written += len(chunk)
        if written != info.file_size:
            raise RestoreBundleError(
                f"short read while extracting {info.filename}: expected {info.file_size}, got {written}"
            )
        os.replace(temp_name, destination)
        temp_name = None
        return written, digest.hexdigest()
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _member_digest(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> tuple[int, str]:
    digest = hashlib.sha256()
    read_bytes = 0
    with archive.open(info) as source:
        for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
            digest.update(chunk)
            read_bytes += len(chunk)
    if read_bytes != info.file_size:
        raise RestoreBundleError(
            f"short read while hashing {info.filename}: expected {info.file_size}, got {read_bytes}"
        )
    return read_bytes, digest.hexdigest()


def _asset_record(
    *,
    role: str,
    archive_path: str,
    zip_info: zipfile.ZipInfo,
    size: int,
    digest: str | None,
    output_path: Path | None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "role": role,
        "archive_path": archive_path,
        "size": size,
    }
    if digest is not None:
        record["sha256"] = digest
    if output_path is not None:
        record["output_path"] = str(output_path)
    record["zip_compress_size"] = zip_info.compress_size
    return record


def extract_restore_bundle(
    ipsw: Path,
    *,
    out_dir: Path | None,
    product: str = "VirtualMac2,1",
    device_class: str = "vma2macosap",
    variant: str = "erase",
    force: bool = False,
    dry_run: bool = False,
    hash_optional_assets: bool = False,
) -> dict[str, object]:
    if not ipsw.is_file():
        raise RestoreBundleError(f"IPSW is not a file: {ipsw}")
    if not dry_run and out_dir is None:
        raise RestoreBundleError("--out-dir is required unless --dry-run is used")
    if out_dir is not None:
        out_dir = out_dir.resolve()

    try:
        with zipfile.ZipFile(ipsw) as archive:
            restore = _load_plist(archive, "Restore.plist")
            build_manifest = _load_plist(archive, "BuildManifest.plist")
            identity_index, identity = _select_identity(
                build_manifest,
                product=product,
                device_class=device_class,
                variant=variant,
            )
            info = _identity_info(identity)

            assets: dict[str, dict[str, object]] = {}
            for role in REQUIRED_RESTORE_ASSETS:
                archive_path = _component_path(identity, role)
                if archive_path is None:
                    raise RestoreBundleError(f"{role} is missing from selected identity")
                zip_info = _zip_member(archive, archive_path, role=role)
                output_path = None if dry_run else _destination_for(out_dir, archive_path, role=role)
                if dry_run:
                    size, digest = _member_digest(archive, zip_info)
                else:
                    assert output_path is not None
                    size, digest = _copy_member(archive, zip_info, output_path, force=force)
                assets[role] = _asset_record(
                    role=role,
                    archive_path=archive_path,
                    zip_info=zip_info,
                    size=size,
                    digest=digest,
                    output_path=output_path,
                )

            optional_assets: dict[str, dict[str, object]] = {}
            for role in OPTIONAL_RESTORE_ASSETS:
                archive_path = _component_path(identity, role)
                if archive_path is None:
                    continue
                zip_info = _zip_member(archive, archive_path, role=role)
                if hash_optional_assets:
                    size, digest = _member_digest(archive, zip_info)
                else:
                    size, digest = zip_info.file_size, None
                optional_assets[role] = _asset_record(
                    role=role,
                    archive_path=archive_path,
                    zip_info=zip_info,
                    size=size,
                    digest=digest,
                    output_path=None,
                )
    except zipfile.BadZipFile as error:
        raise RestoreBundleError(f"invalid IPSW ZIP: {error}") from error

    metadata: dict[str, object] = {
        "ipsw": str(ipsw),
        "output_dir": None if out_dir is None else str(out_dir),
        "dry_run": dry_run,
        "hash_optional_assets": hash_optional_assets,
        "product": product,
        "device_class": device_class,
        "requested_variant": variant,
        "product_version": restore.get("ProductVersion"),
        "product_build_version": restore.get("ProductBuildVersion"),
        "selected_identity": {
            "index": identity_index,
            "variant": info.get("Variant"),
            "restore_behavior": info.get("RestoreBehavior"),
            "device_class": info.get("DeviceClass"),
        },
        "assets": assets,
        "optional_assets": optional_assets,
    }

    if not dry_run and out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = out_dir / "restore-bundle.json"
        metadata["metadata_path"] = str(metadata_path)
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipsw", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--product", default="VirtualMac2,1")
    parser.add_argument("--device-class", default="vma2macosap")
    parser.add_argument("--variant", choices=("erase", "upgrade", "any"), default="erase")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--hash-optional-assets",
        action="store_true",
        help="also hash optional large OS/BaseSystem/static trust cache assets",
    )
    args = parser.parse_args()

    require_debug_environment()
    try:
        result = extract_restore_bundle(
            args.ipsw,
            out_dir=args.out_dir,
            product=args.product,
            device_class=args.device_class,
            variant=args.variant,
            force=args.force,
            dry_run=args.dry_run,
            hash_optional_assets=args.hash_optional_assets,
        )
    except RestoreBundleError as error:
        print(f"macvm: restore bundle extraction failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
