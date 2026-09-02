#!/usr/bin/env python3
"""Wrap one IM4P payload with an AP IMG4 ticket.

This is the reusable personalization step needed by the recovery-side upload
probes: the IPSW contains component IM4P payloads, while iBoot recovery
commands generally expect IMG4 containers carrying the matching IM4M ticket.
For restore aliases such as RestoreDeviceTree, idevicerestore also rewrites the
payload's IM4P tag before stitching; this tool mirrors that behavior for the
components we exercise in the QEMU restore path.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


TOOLS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_ROOT))

from build_vmapple_aux import (  # noqa: E402
    AuxiliaryStorageError,
    _der_element_size,
    _der_length,
    load_ap_ticket,
    load_generator,
    wrap_img4,
)
from probe_host import require_debug_environment  # noqa: E402


COMPONENT_TAGS = {
    "RestoreDeviceTree": b"rdtr",
    "RestoreKernelCache": b"rkrn",
    "RestoreLogo": b"rlgo",
    "RestoreRamDisk": b"rdsk",
    "RestoreSEP": b"rsep",
    "RestoreTrustCache": b"rtsc",
}


def retag_im4p_payload(payload: bytes, component: str | None) -> bytes:
    if component is None:
        return payload
    tag = COMPONENT_TAGS.get(component)
    if tag is None:
        raise AuxiliaryStorageError(f"unsupported restore component tag: {component}")

    marker = b"\x16\x04IM4P\x16\x04"
    offset = payload.find(marker)
    if offset < 0:
        raise AuxiliaryStorageError("IM4P payload tag field was not found")
    tag_offset = offset + len(marker)
    if tag_offset + 4 > len(payload):
        raise AuxiliaryStorageError("IM4P payload tag field is truncated")
    return payload[:tag_offset] + tag + payload[tag_offset + 4 :]


def stitch_img4(payload: bytes, ticket: bytes) -> bytes:
    _der_element_size(payload, "IM4P payload")
    _der_element_size(ticket, "IM4M ticket")
    if b"IM4P" not in payload[:64]:
        raise AuxiliaryStorageError("payload is not an IM4P object")
    if b"IM4M" not in ticket[:64]:
        raise AuxiliaryStorageError("ticket is not an IM4M object")
    manifest = b"\xa0" + _der_length(len(ticket)) + ticket
    content = b"\x16\x04IMG4" + payload + manifest
    return b"\x30" + _der_length(len(content)) + content


def wrap_img4_payload_file(
    *,
    im4p: Path,
    ap_ticket: Path,
    output: Path,
    component: str | None = None,
    generator: int | None = None,
    include_restore_properties: bool = False,
    force: bool = False,
) -> int:
    if output.exists() and not force:
        raise AuxiliaryStorageError(f"output already exists: {output}")

    ticket = load_ap_ticket(ap_ticket)

    try:
        payload = im4p.read_bytes()
    except OSError as error:
        raise AuxiliaryStorageError(f"cannot read IM4P payload: {error}") from error

    payload = retag_im4p_payload(payload, component)
    if include_restore_properties:
        if generator is None:
            generator = load_generator(ap_ticket)
        if generator is None:
            raise AuxiliaryStorageError(
                "an IMG4 generator is required when restore properties are requested"
            )
        image = wrap_img4(payload, ticket, generator)
    else:
        image = stitch_img4(payload, ticket)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(image)
    except OSError as error:
        raise AuxiliaryStorageError(f"cannot write IMG4 output: {error}") from error
    return len(image)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--im4p", required=True, type=Path)
    parser.add_argument("--ap-ticket", required=True, type=Path)
    parser.add_argument(
        "--component",
        choices=sorted(COMPONENT_TAGS),
        help="restore component name whose IM4P tag should be rewritten before stitching",
    )
    parser.add_argument(
        "--generator",
        type=lambda value: int(value, 0),
        help="64-bit IMG4 generator; defaults to the generator stored in SHSH2",
    )
    parser.add_argument(
        "--include-restore-properties",
        action="store_true",
        help="append BNCN restore properties; not used by idevicerestore for ordinary restore components",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output file",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    require_debug_environment()
    try:
        size = wrap_img4_payload_file(
            im4p=args.im4p,
            ap_ticket=args.ap_ticket,
            output=args.output,
            component=args.component,
            generator=args.generator,
            include_restore_properties=args.include_restore_properties,
            force=args.force,
        )
    except (OSError, AuxiliaryStorageError) as error:
        print(f"macvm: IMG4 wrap failed: {error}", file=sys.stderr)
        return 1
    print(f"wrote {args.output} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
