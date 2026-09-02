#!/usr/bin/env python3
"""Capture one QEMU display surface through a run-scoped QMP socket."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any


class QMPError(RuntimeError):
    pass


class QMPClient:
    def __init__(self, socket_path: Path, timeout: float) -> None:
        self.socket_path = socket_path
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.reader: Any = None

    def __enter__(self) -> "QMPClient":
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(os.fspath(self.socket_path))
            self.sock = sock
            self.reader = sock.makefile("rb")
            greeting = self._read_message()
            if "QMP" not in greeting:
                raise QMPError(f"invalid QMP greeting: {greeting!r}")
            self.execute("qmp_capabilities")
            return self
        except Exception:
            sock.close()
            raise

    def __exit__(self, *_: object) -> None:
        if self.reader is not None:
            self.reader.close()
        if self.sock is not None:
            self.sock.close()

    def _read_message(self) -> dict[str, Any]:
        assert self.reader is not None
        while True:
            line = self.reader.readline()
            if not line:
                raise QMPError("QMP connection closed before a response arrived")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise QMPError(f"invalid JSON from QMP: {line!r}") from exc
            if isinstance(message, dict) and "event" in message:
                continue
            if not isinstance(message, dict):
                raise QMPError(f"invalid QMP message: {message!r}")
            return message

    def execute(self, command: str, arguments: dict[str, Any] | None = None) -> Any:
        assert self.sock is not None
        request: dict[str, Any] = {"execute": command}
        if arguments:
            request["arguments"] = arguments
        self.sock.sendall(json.dumps(request, separators=(",", ":")).encode() + b"\r\n")
        response = self._read_message()
        if "error" in response:
            raise QMPError(f"{command} failed: {response['error']!r}")
        if "return" not in response:
            raise QMPError(f"{command} returned an invalid response: {response!r}")
        return response["return"]


def capture(socket_path: Path, output_path: Path, timeout: float) -> None:
    if not output_path.is_absolute():
        raise QMPError(f"output path must be absolute: {output_path}")
    if output_path.suffix.lower() != ".ppm":
        raise QMPError("output path must use the .ppm extension")
    if not socket_path.is_socket():
        raise QMPError(f"QMP socket does not exist: {socket_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with QMPClient(socket_path, timeout) as client:
        client.execute("screendump", {"filename": os.fspath(output_path)})
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise QMPError(f"QEMU did not create a non-empty screenshot: {output_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("socket", type=Path, help="run-scoped QMP Unix socket")
    parser.add_argument("output", type=Path, help="absolute .ppm output path")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        capture(args.socket, args.output, args.timeout)
    except (OSError, QMPError) as exc:
        print(f"macvm: screenshot failed: {exc}", file=sys.stderr)
        return 70
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
