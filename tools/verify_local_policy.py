#!/usr/bin/env python3
"""Verify img4tool's structured summary for a signed LocalPolicy IMG4."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


TOOLS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_ROOT))

from probe_host import require_debug_environment  # noqa: E402
from build_vmapple_aux import load_ap_ticket  # noqa: E402


EMPTY_LOCAL_POLICY = bytes.fromhex(
    "30141604494d345016046c706f6c1603312e30040100"
)
EMPTY_LOCAL_POLICY_SHA384 = hashlib.sha384(EMPTY_LOCAL_POLICY).digest()


class LocalPolicyVerificationError(ValueError):
    """Raised when a LocalPolicy summary violates the expected restore identity."""


def _single_match(text: str, pattern: str, label: str) -> str:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if len(matches) != 1:
        raise LocalPolicyVerificationError(
            f"expected exactly one {label}, found {len(matches)}"
        )
    return matches[0]


def _hex_field(text: str, name: str, size: int) -> bytes:
    value = _single_match(
        text,
        rf"^\s*\[{re.escape(name)}\]:\s*{re.escape(name)}:\s*([0-9a-fA-F]+)\s*$",
        name,
    )
    try:
        decoded = bytes.fromhex(value)
    except ValueError as error:
        raise LocalPolicyVerificationError(f"{name} is not valid hexadecimal") from error
    if len(decoded) != size:
        raise LocalPolicyVerificationError(
            f"{name} must be exactly {size} bytes, got {len(decoded)}"
        )
    return decoded


def _integer_field(text: str, name: str) -> int:
    value = _single_match(
        text,
        rf"^\s*\[{re.escape(name)}\]:\s*{re.escape(name)}:\s*([0-9]+)\s*$",
        name,
    )
    return int(value, 10)


def _boolean_field(text: str, name: str) -> bool:
    value = _single_match(
        text,
        rf"^\s*\[{re.escape(name)}\]:\s*{re.escape(name)}:\s*(true|false)\s*$",
        name,
    )
    return value == "true"


def verify_local_policy_summary(
    text: str,
    *,
    expected_apnonce_hex: str,
    expected_board: int,
    expected_chip: int,
    expected_ecid: int,
    expected_next_stage_im4m_sha384: bytes,
) -> dict[str, int | str | bool]:
    """Validate identity and security fields in ``img4tool -a`` output."""

    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_apnonce_hex):
        raise LocalPolicyVerificationError(
            "expected ApNonce must be exactly 32 bytes of hexadecimal"
        )
    expected_apnonce = bytes.fromhex(expected_apnonce_hex)
    payload_type = _single_match(text, r"^type:\s*(\S+)\s*$", "IM4P type")
    bnch = _hex_field(text, "BNCH", 32)
    board = _integer_field(text, "BORD")
    chip = _integer_field(text, "CHIP")
    ecid = _integer_field(text, "ECID")
    production = _boolean_field(text, "CPRO")
    secure = _boolean_field(text, "CSEC")
    local_boot = _boolean_field(text, "lobo")
    next_stage_hash = _hex_field(text, "nsih", 48)
    payload_digest = _hex_field(text, "DGST", 48)

    if payload_type != "lpol":
        raise LocalPolicyVerificationError(
            f"IM4P payload type must be lpol, got {payload_type}"
        )
    if bnch != expected_apnonce:
        raise LocalPolicyVerificationError("BNCH does not match the expected ApNonce")
    for label, actual, expected in (
        ("BORD", board, expected_board),
        ("CHIP", chip, expected_chip),
        ("ECID", ecid, expected_ecid),
    ):
        if actual != expected:
            raise LocalPolicyVerificationError(
                f"{label} mismatch: expected {expected}, got {actual}"
            )
    if not production or not secure or local_boot:
        raise LocalPolicyVerificationError(
            "LocalPolicy must set CPRO=true, CSEC=true, and lobo=false"
        )
    if len(expected_next_stage_im4m_sha384) != 48:
        raise LocalPolicyVerificationError(
            "expected next-stage IM4M SHA-384 must be exactly 48 bytes"
        )
    if next_stage_hash != expected_next_stage_im4m_sha384:
        raise LocalPolicyVerificationError(
            "nsih does not match the current next-stage ApImg4Ticket SHA-384"
        )
    if payload_digest != EMPTY_LOCAL_POLICY_SHA384:
        raise LocalPolicyVerificationError(
            "DGST does not match the empty LocalPolicy IM4P SHA-384"
        )

    return {
        "status": "pass",
        "payload_type": payload_type,
        "bnch_bytes": len(bnch),
        "bnch_matches_expected": True,
        "board": board,
        "chip": chip,
        "ecid": ecid,
        "production_mode": production,
        "security_mode": secure,
        "local_boot": local_boot,
        "next_stage_hash_matches_expected": True,
        "payload_digest_matches_expected": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path, help="text captured from img4tool -a")
    parser.add_argument("--expected-apnonce", required=True)
    parser.add_argument("--expected-board", required=True, type=lambda value: int(value, 0))
    parser.add_argument("--expected-chip", required=True, type=lambda value: int(value, 0))
    parser.add_argument("--expected-ecid", required=True, type=lambda value: int(value, 0))
    parser.add_argument(
        "--current-tss",
        required=True,
        type=Path,
        help="SHSH2 or raw IM4M for the stage that LocalPolicy must authorize",
    )
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    require_debug_environment()
    try:
        text = args.summary.read_text(encoding="utf-8")
        current_ticket = load_ap_ticket(args.current_tss)
        result = verify_local_policy_summary(
            text,
            expected_apnonce_hex=args.expected_apnonce,
            expected_board=args.expected_board,
            expected_chip=args.expected_chip,
            expected_ecid=args.expected_ecid,
            expected_next_stage_im4m_sha384=hashlib.sha384(current_ticket).digest(),
        )
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.json_output:
            args.json_output.write_text(encoded, encoding="utf-8")
        sys.stdout.write(encoded)
    except (OSError, ValueError) as error:
        print(f"LocalPolicy verification failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
