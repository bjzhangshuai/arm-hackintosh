#!/usr/bin/env python3
"""Drive the vmapple USB restore chardev used by iBoot recovery.

QEMU's ``vmapple-bdif.usb-restore-chardev`` transports two related byte
streams:

* host -> iBEC packets are length-prefixed endpoint events:
  ``uint32_le(payload_len) + endpoint byte + kind byte + payload``.
* iBEC -> host packets are currently emitted as raw packet bytes.

This tool deliberately stays at the packet boundary that QEMU exposes.  It is
not a full libirecovery replacement yet; instead it provides a repeatable,
logged probe layer so QEMU device-model gaps can be debugged from evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import socket
import sys
import time
from typing import Sequence, TextIO


MAX_HOST_PAYLOAD = 16 * 1024 * 1024
HOST_PACKET_HEADER_LEN = 6
USB_CONTROL_SETUP_LEN = 8
RECOVERY_COMMAND_MAX_BYTES = 0x100
RECOVERY_UPLOAD_CHUNK_SIZE = 0x8000
LOG_HEX_MAX_BYTES = 256

# Confirmed from the macOS 26.6 VirtualMac2,1 iBEC session in the isolated
# validation VM.  Recovery transport must be opened before the 0x41
# send-buffer request; completing each request avoids closing the chardev
# while iBEC still owns queued completion packets.
RECOVERY_OPEN_ACKS = (b"\x01\x00", b"\x02\x00", b"\x01\x00")


class UsbRestoreError(ValueError):
    """Raised when a restore packet or script argument is invalid."""


class UsbRestoreTimeout(TimeoutError):
    """Raised when the restore chardev does not produce data in time."""


class UsbRestoreMismatch(UsbRestoreError):
    """Raised when a received guest packet does not match the expectation."""


@dataclass(frozen=True)
class HostPacket:
    """A host-to-iBEC USB restore packet."""

    header: bytes
    payload: bytes = b""

    def __post_init__(self) -> None:
        if len(self.header) != 2:
            raise UsbRestoreError("host packet header must be exactly 2 bytes")
        if len(self.payload) > MAX_HOST_PAYLOAD:
            raise UsbRestoreError(
                f"host packet payload exceeds {MAX_HOST_PAYLOAD} bytes"
            )

    def to_frame(self) -> bytes:
        return len(self.payload).to_bytes(4, "little") + self.header + self.payload

    @property
    def endpoint(self) -> int:
        return self.header[0]

    @property
    def kind(self) -> int:
        return self.header[1]

    @classmethod
    def endpoint_event(
        cls,
        endpoint: int,
        kind: int,
        payload: bytes = b"",
    ) -> "HostPacket":
        if not 0 <= endpoint <= 0xFF:
            raise UsbRestoreError(f"endpoint must fit in one byte, got: {endpoint!r}")
        if kind not in (1, 2, 3):
            raise UsbRestoreError(
                f"endpoint event kind must be 1, 2, or 3, got: {kind!r}"
            )
        return cls(bytes((endpoint, kind)), payload)


@dataclass(frozen=True)
class SessionStep:
    """One ordered CLI restore-session action."""

    action: str
    value: HostPacket | bytes | float | int | Path | None = None


def _strip_hex(text: str) -> str:
    clean = "".join(text.strip().replace("0x", "").replace("0X", "").split())
    clean = clean.replace("_", "")
    if len(clean) % 2:
        raise UsbRestoreError(f"hex string has odd length: {text!r}")
    try:
        bytes.fromhex(clean)
    except ValueError as exc:
        raise UsbRestoreError(f"invalid hex string: {text!r}") from exc
    return clean


def decode_hex(text: str) -> bytes:
    return bytes.fromhex(_strip_hex(text))


def log_hex_fields(data: bytes) -> dict[str, object]:
    if len(data) <= LOG_HEX_MAX_BYTES:
        return {"hex": data.hex()}
    return {
        "hex_prefix": data[:LOG_HEX_MAX_BYTES].hex(),
        "hex_total_bytes": len(data),
        "hex_truncated": True,
    }


def parse_host_packet_spec(spec: str) -> HostPacket:
    """Parse ``hhhh`` or ``hhhh:payload`` into a host packet.

    ``hhhh`` is the raw two-byte endpoint-event header in hex.  ``payload`` is
    optional arbitrary hex appended after the six-byte QEMU frame header.  This
    low-level parser deliberately permits invalid endpoint-event kinds so panic
    reproductions can be expressed exactly; prefer ``event:ENDPOINT,KIND`` for
    ordinary restore-session experiments.
    """

    if ":" in spec:
        header_hex, payload_hex = spec.split(":", 1)
    else:
        header_hex, payload_hex = spec, ""
    return HostPacket(header=decode_hex(header_hex), payload=decode_hex(payload_hex))


def _parse_u8_token(token: str, *, name: str) -> int:
    clean = token.strip()
    if not clean:
        raise UsbRestoreError(f"{name} must not be empty")
    try:
        if clean.lower().startswith("0x"):
            value = int(clean, 16)
        elif len(clean) <= 2:
            value = int(clean, 16)
        else:
            value = int(clean, 10)
    except ValueError as exc:
        raise UsbRestoreError(f"invalid {name}: {token!r}") from exc
    if not 0 <= value <= 0xFF:
        raise UsbRestoreError(f"{name} must fit in one byte, got: {token!r}")
    return value


def parse_endpoint_event_spec(spec: str) -> HostPacket:
    """Parse ``ENDPOINT,KIND`` or ``ENDPOINT,KIND:payload``.

    Endpoint and kind accept compact USB-style hex bytes such as ``04`` or
    ``81`` as well as explicit ``0x`` notation.  ``kind`` is restricted to the
    values that relocated iBEC's vmapple virt-usb dispatcher accepts before its
    line-514 validation panic: 1, 2, and 3.
    """

    if ":" in spec:
        selector, payload_hex = spec.split(":", 1)
    else:
        selector, payload_hex = spec, ""
    pieces = [piece.strip() for piece in selector.split(",")]
    if len(pieces) != 2:
        raise UsbRestoreError(
            "endpoint event must be ENDPOINT,KIND or ENDPOINT,KIND:PAYLOAD"
        )
    endpoint = _parse_u8_token(pieces[0], name="endpoint")
    kind = _parse_u8_token(pieces[1], name="kind")
    return HostPacket.endpoint_event(endpoint, kind, decode_hex(payload_hex))


def _parse_u16_token(token: str, *, name: str) -> int:
    clean = token.strip()
    if not clean:
        raise UsbRestoreError(f"{name} must not be empty")
    try:
        if clean.lower().startswith("0x") or any(c in "abcdefABCDEF" for c in clean):
            value = int(clean, 16)
        else:
            value = int(clean, 10)
    except ValueError as exc:
        raise UsbRestoreError(f"invalid {name}: {token!r}") from exc
    if not 0 <= value <= 0xFFFF:
        raise UsbRestoreError(f"{name} must fit in two bytes, got: {token!r}")
    return value


def build_usb_control_setup(
    bm_request_type: int,
    request: int,
    *,
    value: int = 0,
    index: int = 0,
    length: int = 0,
) -> bytes:
    """Build a USB setup packet in the little-endian layout iBEC parses."""

    for field_name, field_value in (
        ("bmRequestType", bm_request_type),
        ("bRequest", request),
    ):
        if not 0 <= field_value <= 0xFF:
            raise UsbRestoreError(f"{field_name} must fit in one byte")
    for field_name, field_value in (
        ("wValue", value),
        ("wIndex", index),
        ("wLength", length),
    ):
        if not 0 <= field_value <= 0xFFFF:
            raise UsbRestoreError(f"{field_name} must fit in two bytes")

    return (
        bytes((bm_request_type, request))
        + value.to_bytes(2, "little")
        + index.to_bytes(2, "little")
        + length.to_bytes(2, "little")
    )


def infer_recovery_command_request(command: str) -> int:
    """Mirror libirecovery's request selector for command-control transfers."""

    verb = command.split(maxsplit=1)[0] if command.split(maxsplit=1) else ""
    return 1 if verb in {"go", "bootx"} else 0


def build_recovery_command_packet(command: str) -> HostPacket:
    """Build a libirecovery-style EP0 OUT command packet.

    Recovery commands are USB control OUT transfers with bmRequestType 0x40.
    The command string is NUL-terminated in the setup payload, and iBEC returns
    a short EP0 status packet before any later control-IN data phase.
    """

    if "\x00" in command:
        raise UsbRestoreError("recovery command must not contain NUL bytes")
    command = command.strip()
    if not command:
        raise UsbRestoreError("recovery command must not be empty")

    command_bytes = command.encode("utf-8") + b"\x00"
    if len(command_bytes) > RECOVERY_COMMAND_MAX_BYTES:
        raise UsbRestoreError(
            f"recovery command exceeds {RECOVERY_COMMAND_MAX_BYTES} bytes including NUL"
        )

    request = infer_recovery_command_request(command)
    setup = build_usb_control_setup(
        0x40,
        request,
        length=len(command_bytes),
    )
    return HostPacket.endpoint_event(0x00, 1, setup + command_bytes)


def build_recovery_control_in_packet(length: int = 0xFF) -> HostPacket:
    """Build the EP0 IN setup packet used to fetch command results."""

    if length <= 0:
        raise UsbRestoreError("control-in length must be positive")
    setup = build_usb_control_setup(0xC0, 0, length=length)
    return HostPacket.endpoint_event(0x00, 1, setup)


def build_recovery_buffer_start_packet() -> HostPacket:
    """Build libirecovery's recovery-mode send-buffer initiation transfer."""

    setup = build_usb_control_setup(0x41, 0)
    return HostPacket.endpoint_event(0x00, 1, setup)


def build_recovery_bulk_out_packet(payload: bytes = b"") -> HostPacket:
    """Build one recovery-mode bulk OUT chunk for endpoint 0x04."""

    return HostPacket.endpoint_event(0x04, 1, payload)


def build_set_configuration_packet(configuration: int = 1) -> HostPacket:
    """Build the standard USB SET_CONFIGURATION setup packet."""

    if not 0 <= configuration <= 0xFFFF:
        raise UsbRestoreError("configuration value must fit in two bytes")
    setup = build_usb_control_setup(0x00, 9, value=configuration)
    return HostPacket.endpoint_event(0x00, 1, setup)


def build_set_interface_packet(interface: int, alt_setting: int = 0) -> HostPacket:
    """Build the standard USB SET_INTERFACE setup packet."""

    if not 0 <= interface <= 0xFFFF:
        raise UsbRestoreError("interface number must fit in two bytes")
    if not 0 <= alt_setting <= 0xFFFF:
        raise UsbRestoreError("alternate setting must fit in two bytes")
    setup = build_usb_control_setup(0x01, 11, value=alt_setting, index=interface)
    return HostPacket.endpoint_event(0x00, 1, setup)


def recovery_open_sequence() -> tuple[tuple[HostPacket, bytes], ...]:
    """Return the mandatory macOS recovery USB-open sequence.

    libirecovery configures the device and claims interface 0 before every
    recovery upload; current iBEC additionally requires interface 1 alternate
    setting 1.  The completion bytes are guest-visible transport responses
    recorded from the supported VirtualMac2,1 restore chain.
    """

    return (
        (build_set_configuration_packet(1), RECOVERY_OPEN_ACKS[0]),
        (build_set_interface_packet(0, 0), RECOVERY_OPEN_ACKS[1]),
        (build_set_interface_packet(1, 1), RECOVERY_OPEN_ACKS[2]),
    )


def parse_host_frame(frame: bytes) -> HostPacket:
    if len(frame) < HOST_PACKET_HEADER_LEN:
        raise UsbRestoreError("host frame is shorter than 6 bytes")
    payload_len = int.from_bytes(frame[:4], "little")
    expected_len = HOST_PACKET_HEADER_LEN + payload_len
    if payload_len > MAX_HOST_PAYLOAD:
        raise UsbRestoreError(
            f"host frame payload exceeds {MAX_HOST_PAYLOAD} bytes"
        )
    if len(frame) != expected_len:
        raise UsbRestoreError(
            f"host frame length mismatch: prefix says {expected_len} bytes, "
            f"got {len(frame)}"
        )
    return HostPacket(header=frame[4:6], payload=frame[6:])


def parse_host_frame_hex(spec: str) -> HostPacket:
    return parse_host_frame(decode_hex(spec))


def parse_step(spec: str) -> SessionStep:
    """Parse an ordered ``--step`` action.

    Supported forms:

    * ``send:0202`` or ``send:0102:aabb`` for host packets.
    * ``event:02,2`` or ``event:04,1:aabb`` for validated endpoint events.
    * ``command:getenv build-version`` for a libirecovery EP0 OUT command.
    * ``control-in:0xff`` for the matching EP0 IN command-result setup.
    * ``set-configuration:1`` and ``set-interface:1,1`` for USB setup.
    * ``recovery-open`` for configuration plus both required interface claims.
    * ``buffer-start`` for libirecovery's recovery send-buffer 0x41 setup.
    * ``bulk:aabb`` or ``bulk-zlp`` for endpoint-0x04 recovery upload data.
    * ``upload-file:/path/to/component`` for a complete recovery upload.
    * ``raw:000000000202`` for an already length-prefixed host frame.
    * ``expect:0402`` for an exact raw guest packet.
    * ``expect-prefix:0100`` for a raw guest packet beginning with bytes.
    * ``recv`` or ``recv:4`` for any raw guest packet of at least N bytes.
    * ``timeout:30`` to change the receive timeout for later steps.
    * ``sleep:0.5`` for pacing experiments.
    """

    action, sep, value = spec.partition(":")
    if action == "send" and sep:
        return SessionStep("send", parse_host_packet_spec(value))
    if action == "event" and sep:
        return SessionStep("send", parse_endpoint_event_spec(value))
    if action == "command" and sep:
        return SessionStep("send", build_recovery_command_packet(value))
    if action == "control-in":
        if sep:
            length = _parse_u16_token(value, name="control-in length")
        else:
            length = 0xFF
        return SessionStep("send", build_recovery_control_in_packet(length))
    if action == "set-configuration":
        if sep:
            configuration = _parse_u16_token(value, name="configuration value")
        else:
            configuration = 1
        return SessionStep("send", build_set_configuration_packet(configuration))
    if action == "set-interface" and sep:
        pieces = [piece.strip() for piece in value.split(",")]
        if len(pieces) == 1:
            interface = _parse_u16_token(pieces[0], name="interface number")
            alt_setting = 0
        elif len(pieces) == 2:
            interface = _parse_u16_token(pieces[0], name="interface number")
            alt_setting = _parse_u16_token(pieces[1], name="alternate setting")
        else:
            raise UsbRestoreError(
                "set-interface must be INTERFACE or INTERFACE,ALT_SETTING"
            )
        return SessionStep("send", build_set_interface_packet(interface, alt_setting))
    if action == "recovery-open" and not sep:
        return SessionStep("recovery-open")
    if action == "buffer-start" and not sep:
        return SessionStep("send", build_recovery_buffer_start_packet())
    if action == "bulk" and sep:
        return SessionStep("send", build_recovery_bulk_out_packet(decode_hex(value)))
    if action == "bulk-zlp" and not sep:
        return SessionStep("send", build_recovery_bulk_out_packet())
    if action == "upload-file" and sep:
        if not value.strip():
            raise UsbRestoreError("upload-file path must not be empty")
        path = Path(value)
        return SessionStep("upload-file", path)
    if action == "raw" and sep:
        return SessionStep("send", parse_host_frame_hex(value))
    if action == "expect" and sep:
        expected = decode_hex(value)
        if not expected:
            raise UsbRestoreError("expected guest packet must not be empty")
        return SessionStep("expect", expected)
    if action == "expect-prefix" and sep:
        expected = decode_hex(value)
        if not expected:
            raise UsbRestoreError("expected guest packet prefix must not be empty")
        return SessionStep("expect-prefix", expected)
    if action == "recv":
        if not sep:
            return SessionStep("recv", 1)
        try:
            min_bytes = int(value, 0)
        except ValueError as exc:
            raise UsbRestoreError(f"invalid recv byte count: {value!r}") from exc
        if min_bytes <= 0:
            raise UsbRestoreError("recv byte count must be positive")
        return SessionStep("recv", min_bytes)
    if action == "timeout" and sep:
        try:
            seconds = float(value)
        except ValueError as exc:
            raise UsbRestoreError(f"invalid timeout seconds: {value!r}") from exc
        if seconds <= 0:
            raise UsbRestoreError("timeout seconds must be positive")
        return SessionStep("timeout", seconds)
    if action == "sleep" and sep:
        try:
            seconds = float(value)
        except ValueError as exc:
            raise UsbRestoreError(f"invalid sleep seconds: {value!r}") from exc
        if seconds < 0:
            raise UsbRestoreError("sleep seconds must not be negative")
        return SessionStep("sleep", seconds)
    raise UsbRestoreError(f"invalid step: {spec!r}")


class JsonlLogger:
    def __init__(self, path: Path | None = None, stream: TextIO | None = None) -> None:
        if path is not None and stream is not None:
            raise ValueError("pass either path or stream, not both")
        self._path = path
        self._stream = stream
        self._owned: TextIO | None = None

    def __enter__(self) -> "JsonlLogger":
        if self._path is not None:
            self._owned = self._path.open("w", encoding="utf-8")
            self._stream = self._owned
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._owned is not None:
            self._owned.close()

    def event(self, kind: str, **fields: object) -> None:
        if self._stream is None:
            return
        payload = {"event": kind, **fields}
        self._stream.write(json.dumps(payload, sort_keys=True) + "\n")
        self._stream.flush()


class UsbRestoreSession:
    def __init__(
        self,
        socket_path: Path,
        *,
        connect_timeout: float = 10.0,
        logger: JsonlLogger | None = None,
    ) -> None:
        self.socket_path = socket_path
        self.connect_timeout = connect_timeout
        self.logger = logger
        self.sock: socket.socket | None = None

    def __enter__(self) -> "UsbRestoreSession":
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _log(self, kind: str, **fields: object) -> None:
        if self.logger is not None:
            self.logger.event(kind, **fields)

    def connect(self) -> None:
        if self.sock is not None:
            return

        deadline = time.monotonic() + self.connect_timeout
        last_error: OSError | None = None
        while True:
            candidate = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                candidate.connect(str(self.socket_path))
            except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
                candidate.close()
                last_error = exc
                if time.monotonic() >= deadline:
                    raise UsbRestoreTimeout(
                        f"timed out connecting to {self.socket_path}: {exc}"
                    ) from last_error
                time.sleep(0.05)
                continue
            self.sock = candidate
            self._log("connected", socket=str(self.socket_path))
            return

    def close(self) -> None:
        if self.sock is None:
            return
        self.sock.close()
        self.sock = None
        self._log("closed")

    def send_host_packet(self, packet: HostPacket) -> None:
        frame = packet.to_frame()
        self.send_host_frame(frame)

    def send_host_frame(self, frame: bytes) -> None:
        packet = parse_host_frame(frame)
        if self.sock is None:
            raise UsbRestoreError("session is not connected")
        self.sock.sendall(frame)
        self._log(
            "send-host",
            bytes=len(frame),
            **log_hex_fields(frame),
            endpoint=packet.endpoint,
            packet_kind=packet.kind,
            payload_bytes=len(packet.payload),
        )

    def recv_guest_packet(
        self,
        *,
        expected: bytes | None = None,
        expected_prefix: bytes | None = None,
        min_bytes: int | None = None,
        timeout: float = 5.0,
        max_bytes: int = 65536,
    ) -> bytes:
        if self.sock is None:
            raise UsbRestoreError("session is not connected")
        if expected is not None and not expected:
            raise UsbRestoreError("expected guest packet must not be empty")
        if expected_prefix is not None and not expected_prefix:
            raise UsbRestoreError("expected guest packet prefix must not be empty")
        if expected is not None and expected_prefix is not None:
            raise UsbRestoreError("pass either expected or expected_prefix, not both")
        if min_bytes is not None and min_bytes <= 0:
            raise UsbRestoreError("minimum guest packet bytes must be positive")

        deadline = time.monotonic() + timeout
        chunks: list[bytes] = []
        if expected is not None:
            target_len = len(expected)
        elif expected_prefix is not None:
            target_len = len(expected_prefix)
        else:
            target_len = min_bytes or 1
        total = 0

        while total < target_len:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                got = b"".join(chunks)
                self._log("recv-timeout", bytes=len(got), hex=got.hex())
                raise UsbRestoreTimeout(
                    f"timed out waiting for guest packet; received {got.hex() or '<none>'}"
                )
            self.sock.settimeout(remaining)
            try:
                chunk = self.sock.recv(min(max_bytes - total, 4096))
            except socket.timeout as exc:
                got = b"".join(chunks)
                self._log("recv-timeout", bytes=len(got), hex=got.hex())
                raise UsbRestoreTimeout(
                    f"timed out waiting for guest packet; received {got.hex() or '<none>'}"
                ) from exc
            if not chunk:
                got = b"".join(chunks)
                raise UsbRestoreTimeout(
                    f"restore chardev closed; received {got.hex() or '<none>'}"
                )
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise UsbRestoreError(f"guest packet exceeds {max_bytes} bytes")

        data = b"".join(chunks)
        self._log("recv-guest", bytes=len(data), **log_hex_fields(data))
        if expected is not None:
            if data != expected:
                self._log("recv-mismatch", expected=expected.hex(), actual=data.hex())
                raise UsbRestoreMismatch(
                    f"guest packet mismatch: expected {expected.hex()}, got {data.hex()}"
                )
            self._log("recv-match", expected=expected.hex())
        if expected_prefix is not None:
            if not data.startswith(expected_prefix):
                self._log(
                    "recv-prefix-mismatch",
                    expected_prefix=expected_prefix.hex(),
                    actual=data.hex(),
                )
                raise UsbRestoreMismatch(
                    "guest packet prefix mismatch: "
                    f"expected prefix {expected_prefix.hex()}, got {data.hex()}"
                )
            self._log(
                "recv-prefix-match",
                expected_prefix=expected_prefix.hex(),
                actual=data.hex(),
            )
        return data

    def upload_file(
        self,
        path: Path,
        *,
        timeout: float = 5.0,
        chunk_size: int = RECOVERY_UPLOAD_CHUNK_SIZE,
    ) -> None:
        if chunk_size <= 0 or chunk_size > MAX_HOST_PAYLOAD:
            raise UsbRestoreError("upload chunk size is outside the supported range")
        if not path.is_file():
            raise UsbRestoreError(f"upload-file path is not a readable file: {path}")

        total_size = path.stat().st_size
        self._log(
            "upload-file-start",
            path=str(path),
            bytes=total_size,
            chunk_size=chunk_size,
        )
        self.send_host_packet(build_recovery_buffer_start_packet())
        self.recv_guest_packet(expected=bytes.fromhex("0100"), timeout=timeout)

        offset = 0
        chunk_index = 0
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                self.send_host_packet(build_recovery_bulk_out_packet(chunk))
                self.recv_guest_packet(expected=bytes.fromhex("0104"), timeout=timeout)
                offset += len(chunk)
                chunk_index += 1
                self._log(
                    "upload-file-progress",
                    path=str(path),
                    bytes=offset,
                    total_bytes=total_size,
                    chunks=chunk_index,
                )

        if total_size % 512 == 0:
            self.send_host_packet(build_recovery_bulk_out_packet())
            self.recv_guest_packet(expected=bytes.fromhex("0104"), timeout=timeout)
            self._log("upload-file-zlp", path=str(path), bytes=total_size)

        self._log(
            "upload-file-complete",
            path=str(path),
            bytes=total_size,
            chunks=chunk_index,
        )

    def open_recovery_transport(self, *, timeout: float = 5.0) -> None:
        """Configure iBEC recovery USB and drain each completion response."""

        for packet, expected in recovery_open_sequence():
            self.send_host_packet(packet)
            self.recv_guest_packet(expected=expected, timeout=timeout)
        self._log("recovery-open-complete")


def _run(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        if args.step and (args.send_host or args.send_host_frame or args.expect_guest):
            raise UsbRestoreError("--step cannot be mixed with legacy send/expect options")
        if args.step:
            steps = [parse_step(spec) for spec in args.step]
        else:
            steps = [
                *(SessionStep("send", parse_host_packet_spec(spec)) for spec in args.send_host),
                *(SessionStep("send", parse_host_frame_hex(spec)) for spec in args.send_host_frame),
                *(SessionStep("expect", decode_hex(spec)) for spec in args.expect_guest),
            ]
    except UsbRestoreError as exc:
        print(f"usb_restore_session: {exc}", file=stderr)
        return 2

    logger_cm: JsonlLogger
    if args.jsonl is not None and str(args.jsonl) == "-":
        logger_cm = JsonlLogger(stream=stdout)
    else:
        logger_cm = JsonlLogger(path=args.jsonl) if args.jsonl else JsonlLogger()

    try:
        with logger_cm as logger:
            with UsbRestoreSession(
                args.socket,
                connect_timeout=args.connect_timeout,
                logger=logger,
            ) as session:
                recv_timeout = args.recv_timeout
                for step in steps:
                    if step.action == "send":
                        assert isinstance(step.value, HostPacket)
                        session.send_host_packet(step.value)
                    elif step.action == "expect":
                        assert isinstance(step.value, bytes)
                        session.recv_guest_packet(
                            expected=step.value,
                            timeout=recv_timeout,
                        )
                    elif step.action == "expect-prefix":
                        assert isinstance(step.value, bytes)
                        session.recv_guest_packet(
                            expected_prefix=step.value,
                            timeout=recv_timeout,
                        )
                    elif step.action == "recv":
                        assert isinstance(step.value, int)
                        session.recv_guest_packet(
                            min_bytes=step.value,
                            timeout=recv_timeout,
                        )
                    elif step.action == "upload-file":
                        assert isinstance(step.value, Path)
                        session.upload_file(
                            step.value,
                            timeout=recv_timeout,
                        )
                    elif step.action == "recovery-open":
                        session.open_recovery_transport(timeout=recv_timeout)
                    elif step.action == "timeout":
                        assert isinstance(step.value, float)
                        recv_timeout = step.value
                        logger.event("timeout", seconds=step.value)
                    elif step.action == "sleep":
                        assert isinstance(step.value, float)
                        logger.event("sleep", seconds=step.value)
                        time.sleep(step.value)
                    else:
                        raise AssertionError(f"unknown step action: {step.action}")
    except (UsbRestoreError, UsbRestoreTimeout) as exc:
        print(f"usb_restore_session: {exc}", file=stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument(
        "--send-host",
        action="append",
        default=[],
        metavar="HEADER[:PAYLOAD]",
        help="send a host packet; e.g. 0202 or 0001:48656c6c6f",
    )
    parser.add_argument(
        "--send-host-frame",
        action="append",
        default=[],
        metavar="HEX",
        help="send an already length-prefixed host frame, e.g. 000000000202",
    )
    parser.add_argument(
        "--expect-guest",
        action="append",
        default=[],
        metavar="HEX",
        help="receive and require this raw guest packet, e.g. 0402",
    )
    parser.add_argument(
        "--step",
        action="append",
        default=[],
        metavar="ACTION",
        help=(
            "ordered action: send:0202, event:04,1:aabb, raw:000000000202, "
            "command:getenv build-version, control-in[:LEN], set-configuration[:N], "
            "set-interface:IFACE[,ALT], recovery-open, buffer-start, bulk:HEX, bulk-zlp, "
            "upload-file:PATH, expect:0402, expect-prefix:0100, recv[:N], "
            "timeout:SECONDS, or sleep:SECONDS"
        ),
    )
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--recv-timeout", type=float, default=5.0)
    parser.add_argument("--jsonl", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    return _run(parser.parse_args(argv), stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
