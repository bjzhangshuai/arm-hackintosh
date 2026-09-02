#!/usr/bin/env python3
"""Verify a QEMU loader image by reading it back from physical guest RAM."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
import stat


MAX_IMAGE_BYTES = 16 * 1024 * 1024
MAX_QMP_LINE_BYTES = 1024 * 1024
UINT64_LIMIT = 1 << 64


class QMPPhysicalMemoryError(ValueError):
    """QMP physical-memory verification could not be completed safely."""


def parse_u64_literal(value: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as error:
        raise QMPPhysicalMemoryError(f"address must be a uint64 literal: {value}") from error
    if not 0 <= parsed < UINT64_LIMIT:
        raise QMPPhysicalMemoryError(f"address must fit in uint64: {value}")
    return parsed


def _resolve_under_root(path: str, *, allowed_root: str, role: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise QMPPhysicalMemoryError(f"{role} path must be absolute")
    try:
        root = Path(allowed_root).resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise QMPPhysicalMemoryError(f"{role} path cannot be resolved: {error}") from error
    if resolved != root and root not in resolved.parents:
        raise QMPPhysicalMemoryError(f"{role} path must remain inside {root}")
    return resolved


def _resolve_new_output(path: str, *, allowed_root: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise QMPPhysicalMemoryError("physical dump path must be absolute")
    if any(character in path for character in ('"', "\\", "\n", "\r")):
        raise QMPPhysicalMemoryError("physical dump path contains unsafe HMP characters")
    try:
        root = Path(allowed_root).resolve(strict=True)
        parent = candidate.parent.resolve(strict=True)
    except OSError as error:
        raise QMPPhysicalMemoryError(f"physical dump parent cannot be resolved: {error}") from error
    resolved = parent / candidate.name
    if resolved != root and root not in resolved.parents:
        raise QMPPhysicalMemoryError(f"physical dump path must remain inside {root}")
    if resolved.exists() or resolved.is_symlink():
        raise QMPPhysicalMemoryError("physical dump path already exists")
    return resolved


def _read_message(stream) -> dict[str, object]:
    line = stream.readline(MAX_QMP_LINE_BYTES + 1)
    if not line:
        raise QMPPhysicalMemoryError("QMP closed the connection")
    if len(line) > MAX_QMP_LINE_BYTES:
        raise QMPPhysicalMemoryError("QMP response exceeds the size limit")
    try:
        message = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QMPPhysicalMemoryError("QMP returned malformed JSON") from error
    if not isinstance(message, dict):
        raise QMPPhysicalMemoryError("QMP response is not an object")
    return message


def _call(stream, command: dict[str, object]) -> object:
    stream.write(json.dumps(command, separators=(",", ":")).encode("utf-8") + b"\n")
    while True:
        message = _read_message(stream)
        if "error" in message:
            raise QMPPhysicalMemoryError(f"QMP command failed: {message['error']}")
        if "return" in message:
            return message["return"]


def verify_physical_image(
    *,
    qmp_socket: str,
    address: int,
    expected_image: str,
    output: str,
    allowed_root: str,
    timeout: float = 5.0,
) -> tuple[Path, str, int]:
    if not isinstance(address, int) or isinstance(address, bool) or not 0 <= address < UINT64_LIMIT:
        raise QMPPhysicalMemoryError("address must be a uint64 integer")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0 or timeout > 60:
        raise QMPPhysicalMemoryError("QMP timeout must be greater than zero and at most 60 seconds")

    expected = _resolve_under_root(
        expected_image, allowed_root=allowed_root, role="expected image"
    )
    if not expected.is_file() or not os.access(expected, os.R_OK):
        raise QMPPhysicalMemoryError("expected image is not a readable regular file")
    expected_size = expected.stat().st_size
    if expected_size <= 0 or expected_size > MAX_IMAGE_BYTES:
        raise QMPPhysicalMemoryError("expected image has an unsafe size")
    if address + expected_size > UINT64_LIMIT:
        raise QMPPhysicalMemoryError("physical read range overflows uint64")
    output_path = _resolve_new_output(output, allowed_root=allowed_root)

    socket_path = Path(qmp_socket)
    if not socket_path.is_absolute():
        raise QMPPhysicalMemoryError("QMP socket path must be absolute")
    try:
        socket_mode = socket_path.stat().st_mode
    except OSError as error:
        raise QMPPhysicalMemoryError(f"QMP socket cannot be inspected: {error}") from error
    if not stat.S_ISSOCK(socket_mode):
        raise QMPPhysicalMemoryError("QMP path is not a Unix socket")

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(float(timeout))
    stream = None
    try:
        client.connect(str(socket_path))
        stream = client.makefile("rwb", buffering=0)
        greeting = _read_message(stream)
        if "QMP" not in greeting:
            raise QMPPhysicalMemoryError("QMP greeting is missing")
        _call(stream, {"execute": "qmp_capabilities"})
        hmp = f'pmemsave 0x{address:x} {expected_size} "{output_path}"'
        response = _call(
            stream,
            {
                "execute": "human-monitor-command",
                "arguments": {"command-line": hmp},
            },
        )
        if response not in ("", None):
            raise QMPPhysicalMemoryError(f"pmemsave failed: {response}")
    except (OSError, socket.timeout) as error:
        raise QMPPhysicalMemoryError(f"QMP physical read failed: {error}") from error
    finally:
        if stream is not None:
            stream.close()
        client.close()

    if not output_path.is_file() or output_path.stat().st_size != expected_size:
        raise QMPPhysicalMemoryError("QMP physical dump has the wrong size")
    expected_bytes = expected.read_bytes()
    observed_bytes = output_path.read_bytes()
    if not hmac.compare_digest(expected_bytes, observed_bytes):
        raise QMPPhysicalMemoryError("QMP physical dump does not match the loader image")
    digest = hashlib.sha256(observed_bytes).hexdigest()
    return output_path, digest, expected_size


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--address", required=True)
    parser.add_argument("--expected-image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allowed-root", required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        output, digest, size = verify_physical_image(
            qmp_socket=args.socket,
            address=parse_u64_literal(args.address),
            expected_image=args.expected_image,
            output=args.output,
            allowed_root=args.allowed_root,
            timeout=args.timeout,
        )
    except QMPPhysicalMemoryError as error:
        parser.error(str(error))
    print(f"{output}\t{size}\t{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
