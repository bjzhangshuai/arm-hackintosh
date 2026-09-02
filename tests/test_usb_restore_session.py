from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "usb_restore_session", ROOT / "tools" / "usb_restore_session.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class HostPacketTests(unittest.TestCase):
    def test_event_packet_0202_matches_known_ibec_bootstrap_frame(self) -> None:
        packet = MODULE.parse_host_packet_spec("0202")
        self.assertEqual(packet.header, bytes.fromhex("0202"))
        self.assertEqual(packet.payload, b"")
        self.assertEqual(packet.to_frame().hex(), "000000000202")

    def test_payload_length_is_little_endian_and_excludes_two_byte_header(self) -> None:
        packet = MODULE.parse_host_packet_spec("0102:aabbcc")
        self.assertEqual(packet.to_frame().hex(), "030000000102aabbcc")

    def test_endpoint_event_builder_uses_endpoint_kind_header(self) -> None:
        packet = MODULE.HostPacket.endpoint_event(0x04, 1, bytes.fromhex("aabb"))
        self.assertEqual(packet.endpoint, 0x04)
        self.assertEqual(packet.kind, 1)
        self.assertEqual(packet.header, bytes.fromhex("0401"))
        self.assertEqual(packet.to_frame().hex(), "020000000401aabb")

    def test_builds_libirecovery_getenv_command_as_ep0_control_out(self) -> None:
        packet = MODULE.build_recovery_command_packet("getenv build-version")
        self.assertEqual(packet.endpoint, 0x00)
        self.assertEqual(packet.kind, 1)
        self.assertEqual(
            packet.to_frame().hex(),
            "1d0000000001"
            "4000000000001500"
            "676574656e76206275696c642d76657273696f6e00",
        )

    def test_builds_libirecovery_bootx_command_with_request_one(self) -> None:
        packet = MODULE.build_recovery_command_packet("bootx")
        self.assertEqual(
            packet.to_frame().hex(),
            "0e0000000001"
            "4001000000000600"
            "626f6f747800",
        )

    def test_builds_control_in_setup_for_command_result_fetch(self) -> None:
        packet = MODULE.build_recovery_control_in_packet(0xFF)
        self.assertEqual(packet.endpoint, 0x00)
        self.assertEqual(packet.kind, 1)
        self.assertEqual(packet.to_frame().hex(), "080000000001c00000000000ff00")

    def test_builds_recovery_send_buffer_start_and_bulk_packets(self) -> None:
        self.assertEqual(
            MODULE.build_recovery_buffer_start_packet().to_frame().hex(),
            "0800000000014100000000000000",
        )
        self.assertEqual(
            MODULE.build_recovery_bulk_out_packet(bytes.fromhex("aabb")).to_frame().hex(),
            "020000000401aabb",
        )
        self.assertEqual(
            MODULE.build_recovery_bulk_out_packet().to_frame().hex(),
            "000000000401",
        )

    def test_builds_standard_usb_configuration_and_interface_setup_packets(self) -> None:
        self.assertEqual(
            MODULE.build_set_configuration_packet(1).to_frame().hex(),
            "0800000000010009010000000000",
        )
        self.assertEqual(
            MODULE.build_set_interface_packet(0).to_frame().hex(),
            "080000000001010b000000000000",
        )
        self.assertEqual(
            MODULE.build_set_interface_packet(1, 1).to_frame().hex(),
            "080000000001010b010001000000",
        )

    def test_recovery_open_sequence_has_confirmed_packets_and_acks(self) -> None:
        self.assertEqual(
            [(packet.to_frame().hex(), ack.hex()) for packet, ack in MODULE.recovery_open_sequence()],
            [
                ("0800000000010009010000000000", "0100"),
                ("080000000001010b000000000000", "0200"),
                ("080000000001010b010001000000", "0100"),
            ],
        )

    def test_rejects_invalid_standard_usb_setup_values(self) -> None:
        for value in (-1, 0x10000):
            with self.subTest(configuration=value):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.build_set_configuration_packet(value)
            with self.subTest(interface=value):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.build_set_interface_packet(value)
            with self.subTest(alt_setting=value):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.build_set_interface_packet(0, value)

    def test_rejects_invalid_recovery_command_and_control_in_length(self) -> None:
        for command in ("", "   ", "bad\x00command"):
            with self.subTest(command=command):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.build_recovery_command_packet(command)
        with self.assertRaisesRegex(MODULE.UsbRestoreError, "exceeds"):
            MODULE.build_recovery_command_packet("x" * MODULE.RECOVERY_COMMAND_MAX_BYTES)
        for length in (0, 0x10000):
            with self.subTest(length=length):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.build_recovery_control_in_packet(length)

    def test_parse_endpoint_event_spec_accepts_usb_style_hex_bytes(self) -> None:
        self.assertEqual(
            MODULE.parse_endpoint_event_spec("04,1:0000000000000800").to_frame().hex(),
            "0800000004010000000000000800",
        )
        self.assertEqual(
            MODULE.parse_endpoint_event_spec("0x81,0x3").to_frame().hex(),
            "000000008103",
        )

    def test_endpoint_event_rejects_invalid_selector_or_kind(self) -> None:
        for spec in (
            "",
            "04",
            "04,",
            "0401",
            "04,0",
            "04,4",
            "0x100,1",
            "04,1:abc",
        ):
            with self.subTest(spec=spec):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.parse_endpoint_event_spec(spec)

    def test_hex_parser_allows_spaces_underscores_and_0x_prefixes(self) -> None:
        packet = MODULE.parse_host_packet_spec("0x02 02: aa_bb")
        self.assertEqual(packet.to_frame().hex(), "020000000202aabb")

    def test_large_log_hex_fields_use_bounded_preview(self) -> None:
        small = bytes.fromhex("aabb")
        self.assertEqual(MODULE.log_hex_fields(small), {"hex": "aabb"})

        large = b"\xaa" * (MODULE.LOG_HEX_MAX_BYTES + 1)
        fields = MODULE.log_hex_fields(large)
        self.assertNotIn("hex", fields)
        self.assertEqual(fields["hex_prefix"], (b"\xaa" * MODULE.LOG_HEX_MAX_BYTES).hex())
        self.assertEqual(fields["hex_total_bytes"], len(large))
        self.assertTrue(fields["hex_truncated"])

    def test_rejects_header_that_is_not_two_bytes(self) -> None:
        for spec in ("02", "020203"):
            with self.subTest(spec=spec):
                with self.assertRaisesRegex(MODULE.UsbRestoreError, "exactly 2 bytes"):
                    MODULE.parse_host_packet_spec(spec)

    def test_rejects_invalid_hex_and_odd_hex(self) -> None:
        for spec in ("zzzz", "0202:abc"):
            with self.subTest(spec=spec):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.parse_host_packet_spec(spec)

    def test_round_trips_already_framed_host_packet(self) -> None:
        packet = MODULE.parse_host_frame_hex("030000000102aabbcc")
        self.assertEqual(packet, MODULE.HostPacket(bytes.fromhex("0102"), bytes.fromhex("aabbcc")))

    def test_rejects_short_frame_length_mismatch_and_payload_limit(self) -> None:
        with self.assertRaisesRegex(MODULE.UsbRestoreError, "shorter than 6 bytes"):
            MODULE.parse_host_frame(bytes.fromhex("0000000002"))
        with self.assertRaisesRegex(MODULE.UsbRestoreError, "length mismatch"):
            MODULE.parse_host_frame(bytes.fromhex("010000000202"))
        too_large = (MODULE.MAX_HOST_PAYLOAD + 1).to_bytes(4, "little") + bytes.fromhex("0202")
        with self.assertRaisesRegex(MODULE.UsbRestoreError, "exceeds"):
            MODULE.parse_host_frame(too_large)


class SessionStepTests(unittest.TestCase):
    def test_parses_ordered_send_raw_expect_recv_and_sleep_steps(self) -> None:
        self.assertEqual(MODULE.parse_step("send:0202").value.to_frame().hex(), "000000000202")
        self.assertEqual(MODULE.parse_step("send:0102:aabb").value.to_frame().hex(), "020000000102aabb")
        self.assertEqual(MODULE.parse_step("event:04,1:aabb").value.to_frame().hex(), "020000000401aabb")
        self.assertEqual(
            MODULE.parse_step("command:getenv build-version").value.to_frame().hex(),
            "1d0000000001"
            "4000000000001500"
            "676574656e76206275696c642d76657273696f6e00",
        )
        self.assertEqual(
            MODULE.parse_step("control-in:0xff").value.to_frame().hex(),
            "080000000001c00000000000ff00",
        )
        self.assertEqual(
            MODULE.parse_step("control-in").value.to_frame().hex(),
            "080000000001c00000000000ff00",
        )
        self.assertEqual(
            MODULE.parse_step("set-configuration").value.to_frame().hex(),
            "0800000000010009010000000000",
        )
        self.assertEqual(
            MODULE.parse_step("set-configuration:1").value.to_frame().hex(),
            "0800000000010009010000000000",
        )
        self.assertEqual(
            MODULE.parse_step("set-interface:0").value.to_frame().hex(),
            "080000000001010b000000000000",
        )
        self.assertEqual(
            MODULE.parse_step("set-interface:1,1").value.to_frame().hex(),
            "080000000001010b010001000000",
        )
        self.assertEqual(
            MODULE.parse_step("recovery-open"),
            MODULE.SessionStep("recovery-open"),
        )
        self.assertEqual(
            MODULE.parse_step("buffer-start").value.to_frame().hex(),
            "0800000000014100000000000000",
        )
        self.assertEqual(MODULE.parse_step("bulk:aabb").value.to_frame().hex(), "020000000401aabb")
        self.assertEqual(MODULE.parse_step("bulk-zlp").value.to_frame().hex(), "000000000401")
        self.assertEqual(
            MODULE.parse_step("upload-file:/tmp/component.img4"),
            MODULE.SessionStep("upload-file", Path("/tmp/component.img4")),
        )
        self.assertEqual(MODULE.parse_step("raw:000000000202").value.to_frame().hex(), "000000000202")
        self.assertEqual(MODULE.parse_step("expect:0402"), MODULE.SessionStep("expect", bytes.fromhex("0402")))
        self.assertEqual(
            MODULE.parse_step("expect-prefix:0100"),
            MODULE.SessionStep("expect-prefix", bytes.fromhex("0100")),
        )
        self.assertEqual(MODULE.parse_step("recv"), MODULE.SessionStep("recv", 1))
        self.assertEqual(MODULE.parse_step("recv:0x10"), MODULE.SessionStep("recv", 16))
        self.assertEqual(MODULE.parse_step("timeout:15"), MODULE.SessionStep("timeout", 15.0))
        self.assertEqual(MODULE.parse_step("sleep:0.25"), MODULE.SessionStep("sleep", 0.25))

    def test_rejects_bad_ordered_steps(self) -> None:
        for spec in (
            "send",
            "event",
            "event:04,0",
            "command:",
            "control-in:0",
            "control-in:0x10000",
            "control-in:nope",
            "set-configuration:0x10000",
            "set-configuration:nope",
            "set-interface",
            "set-interface:",
            "set-interface:0x10000",
            "set-interface:0,0x10000",
            "set-interface:0,0,0",
            "buffer-start:",
            "bulk",
            "bulk:a",
            "bulk-zlp:",
            "upload-file",
            "upload-file:",
            "raw:010203",
            "expect:",
            "expect-prefix:",
            "recv:0",
            "recv:nope",
            "timeout:0",
            "timeout:nope",
            "sleep:-1",
            "sleep:nope",
            "unknown:0202",
        ):
            with self.subTest(spec=spec):
                with self.assertRaises(MODULE.UsbRestoreError):
                    MODULE.parse_step(spec)


class UnixSocketHarness:
    def __init__(
        self,
        *,
        recv_len: int = 0,
        response_chunks: tuple[bytes, ...] = (),
        delay_between_chunks: float = 0.0,
        hold_open: float = 0.0,
    ) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "restore.sock"
        self.recv_len = recv_len
        self.response_chunks = response_chunks
        self.delay_between_chunks = delay_between_chunks
        self.hold_open = hold_open
        self.received = b""
        self.ready = threading.Event()
        self.done = threading.Event()
        self.error: BaseException | None = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> "UnixSocketHarness":
        self.thread.start()
        self.assert_ready()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.done.wait(1)
        self.tempdir.cleanup()
        if self.error:
            raise self.error

    def assert_ready(self) -> None:
        if not self.ready.wait(1):
            raise AssertionError("socket server did not become ready")

    def _run(self) -> None:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(self.path))
            server.listen(1)
            self.ready.set()
            conn, _ = server.accept()
            with conn:
                while len(self.received) < self.recv_len:
                    chunk = conn.recv(self.recv_len - len(self.received))
                    if not chunk:
                        break
                    self.received += chunk
                for chunk in self.response_chunks:
                    if self.delay_between_chunks:
                        time.sleep(self.delay_between_chunks)
                    conn.sendall(chunk)
                if self.hold_open:
                    time.sleep(self.hold_open)
        except BaseException as exc:
            self.error = exc
        finally:
            server.close()
            self.done.set()


class ScriptedUnixSocketHarness:
    def __init__(self, actions: tuple[tuple[str, bytes | int], ...]) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "restore.sock"
        self.actions = actions
        self.received: list[bytes] = []
        self.ready = threading.Event()
        self.done = threading.Event()
        self.error: BaseException | None = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> "ScriptedUnixSocketHarness":
        self.thread.start()
        if not self.ready.wait(1):
            raise AssertionError("socket server did not become ready")
        return self

    def __exit__(self, *_exc: object) -> None:
        self.done.wait(1)
        self.tempdir.cleanup()
        if self.error:
            raise self.error

    def _recv_exact(self, conn: socket.socket, count: int) -> bytes:
        data = b""
        while len(data) < count:
            chunk = conn.recv(count - len(data))
            if not chunk:
                break
            data += chunk
        return data

    def _run(self) -> None:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(self.path))
            server.listen(1)
            self.ready.set()
            conn, _ = server.accept()
            with conn:
                for action, value in self.actions:
                    if action == "recv":
                        assert isinstance(value, int)
                        self.received.append(self._recv_exact(conn, value))
                    elif action == "send":
                        assert isinstance(value, bytes)
                        conn.sendall(value)
                    else:
                        raise AssertionError(f"unknown scripted socket action: {action}")
        except BaseException as exc:
            self.error = exc
        finally:
            server.close()
            self.done.set()


class SessionTests(unittest.TestCase):
    def test_session_sends_host_frame_and_receives_partial_guest_response(self) -> None:
        stream = io.StringIO()
        with UnixSocketHarness(
            recv_len=6,
            response_chunks=(bytes.fromhex("04"), bytes.fromhex("02")),
        ) as harness:
            with MODULE.JsonlLogger(stream=stream) as logger:
                with MODULE.UsbRestoreSession(
                    harness.path,
                    connect_timeout=1,
                    logger=logger,
                ) as session:
                    session.send_host_packet(MODULE.parse_host_packet_spec("0202"))
                    self.assertEqual(
                        session.recv_guest_packet(
                            expected=bytes.fromhex("0402"),
                            timeout=1,
                        ),
                        bytes.fromhex("0402"),
                    )
            self.assertEqual(harness.received.hex(), "000000000202")

        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual([event["event"] for event in events], [
            "connected",
            "send-host",
            "recv-guest",
            "recv-match",
            "closed",
        ])
        self.assertEqual(events[1]["hex"], "000000000202")
        self.assertEqual(events[1]["endpoint"], 2)
        self.assertEqual(events[1]["packet_kind"], 2)
        self.assertEqual(events[1]["payload_bytes"], 0)
        self.assertEqual(events[2]["hex"], "0402")

    def test_session_rejects_guest_mismatch(self) -> None:
        with UnixSocketHarness(response_chunks=(bytes.fromhex("0403"),)) as harness:
            with MODULE.UsbRestoreSession(harness.path, connect_timeout=1) as session:
                with self.assertRaisesRegex(MODULE.UsbRestoreMismatch, "expected 0402"):
                    session.recv_guest_packet(expected=bytes.fromhex("0402"), timeout=1)

    def test_session_accepts_guest_prefix_with_payload(self) -> None:
        stream = io.StringIO()
        response = bytes.fromhex("0100") + b"mBoot-18000.161.9\x00"
        with UnixSocketHarness(response_chunks=(response,)) as harness:
            with MODULE.JsonlLogger(stream=stream) as logger:
                with MODULE.UsbRestoreSession(
                    harness.path,
                    connect_timeout=1,
                    logger=logger,
                ) as session:
                    self.assertEqual(
                        session.recv_guest_packet(
                            expected_prefix=bytes.fromhex("0100"),
                            timeout=1,
                        ),
                        response,
                    )

        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(events[1]["event"], "recv-guest")
        self.assertEqual(events[2]["event"], "recv-prefix-match")
        self.assertEqual(events[2]["expected_prefix"], "0100")
        self.assertEqual(events[2]["actual"], response.hex())

    def test_session_rejects_guest_prefix_mismatch(self) -> None:
        with UnixSocketHarness(response_chunks=(bytes.fromhex("0500"),)) as harness:
            with MODULE.UsbRestoreSession(harness.path, connect_timeout=1) as session:
                with self.assertRaisesRegex(MODULE.UsbRestoreMismatch, "prefix 0100"):
                    session.recv_guest_packet(
                        expected_prefix=bytes.fromhex("0100"),
                        timeout=1,
                    )

    def test_session_times_out_waiting_for_guest_packet(self) -> None:
        with UnixSocketHarness(hold_open=0.2) as harness:
            with MODULE.UsbRestoreSession(harness.path, connect_timeout=1) as session:
                with self.assertRaisesRegex(MODULE.UsbRestoreTimeout, "timed out"):
                    session.recv_guest_packet(expected=bytes.fromhex("0402"), timeout=0.01)

    def test_session_can_receive_any_minimum_guest_bytes(self) -> None:
        with UnixSocketHarness(response_chunks=(bytes.fromhex("aabbcc"),)) as harness:
            with MODULE.UsbRestoreSession(harness.path, connect_timeout=1) as session:
                self.assertEqual(
                    session.recv_guest_packet(min_bytes=3, timeout=1),
                    bytes.fromhex("aabbcc"),
                )

    def test_upload_file_sends_buffer_start_chunks_progress_and_no_zlp_when_unaligned(self) -> None:
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as directory_name:
            upload_path = Path(directory_name) / "component.img4"
            upload_path.write_bytes(b"abc")
            buffer_start_frame = MODULE.build_recovery_buffer_start_packet().to_frame()
            bulk_frame = MODULE.build_recovery_bulk_out_packet(b"abc").to_frame()
            actions = (
                ("recv", len(buffer_start_frame)),
                ("send", bytes.fromhex("0100")),
                ("recv", len(bulk_frame)),
                ("send", bytes.fromhex("0104")),
            )
            with ScriptedUnixSocketHarness(actions) as harness:
                with MODULE.JsonlLogger(stream=stream) as logger:
                    with MODULE.UsbRestoreSession(
                        harness.path,
                        connect_timeout=1,
                        logger=logger,
                    ) as session:
                        session.upload_file(upload_path, timeout=1)

                self.assertEqual(harness.received, [buffer_start_frame, bulk_frame])

        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(events[1]["event"], "upload-file-start")
        self.assertEqual(events[1]["bytes"], 3)
        self.assertEqual(events[5]["hex"], bulk_frame.hex())
        self.assertEqual(events[8]["event"], "upload-file-progress")
        self.assertEqual(events[8]["bytes"], 3)
        self.assertEqual(events[9]["event"], "upload-file-complete")

    def test_upload_file_sends_zlp_when_size_is_512_aligned(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            upload_path = Path(directory_name) / "component.img4"
            payload = b"x" * 512
            upload_path.write_bytes(payload)
            buffer_start_frame = MODULE.build_recovery_buffer_start_packet().to_frame()
            bulk_frame = MODULE.build_recovery_bulk_out_packet(payload).to_frame()
            zlp_frame = MODULE.build_recovery_bulk_out_packet().to_frame()
            actions = (
                ("recv", len(buffer_start_frame)),
                ("send", bytes.fromhex("0100")),
                ("recv", len(bulk_frame)),
                ("send", bytes.fromhex("0104")),
                ("recv", len(zlp_frame)),
                ("send", bytes.fromhex("0104")),
            )
            with ScriptedUnixSocketHarness(actions) as harness:
                with MODULE.UsbRestoreSession(harness.path, connect_timeout=1) as session:
                    session.upload_file(upload_path, timeout=1)

            self.assertEqual(harness.received, [buffer_start_frame, bulk_frame, zlp_frame])

    def test_upload_file_rejects_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            missing_path = Path(directory_name) / "missing.img4"
            with UnixSocketHarness() as harness:
                with MODULE.UsbRestoreSession(harness.path, connect_timeout=1) as session:
                    with self.assertRaisesRegex(MODULE.UsbRestoreError, "not a readable file"):
                        session.upload_file(missing_path, timeout=1)

    def test_connect_timeout_reports_socket_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "missing.sock"
            session = MODULE.UsbRestoreSession(path, connect_timeout=0.01)
            with self.assertRaisesRegex(MODULE.UsbRestoreTimeout, "missing.sock"):
                session.connect()


class CliTests(unittest.TestCase):
    def test_cli_sends_packet_receives_expected_response_and_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            log_path = Path(directory_name) / "session.jsonl"
            with UnixSocketHarness(
                recv_len=8,
                response_chunks=(bytes.fromhex("0402"),),
            ) as harness:
                stderr = io.StringIO()
                result = MODULE._run(
                    MODULE.build_parser().parse_args(
                        [
                            "--socket",
                            str(harness.path),
                            "--send-host",
                            "0202:aabb",
                            "--expect-guest",
                            "0402",
                            "--connect-timeout",
                            "1",
                            "--recv-timeout",
                            "1",
                            "--jsonl",
                            str(log_path),
                        ]
                    ),
                    stdout=io.StringIO(),
                    stderr=stderr,
                )
                self.assertEqual(result, 0, stderr.getvalue())
                self.assertEqual(harness.received.hex(), "020000000202aabb")

            events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["event"], "connected")
            self.assertEqual(events[1]["event"], "send-host")
            self.assertEqual(events[2]["event"], "recv-guest")
            self.assertEqual(events[3]["event"], "recv-match")

    def test_cli_returns_two_on_invalid_packet(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "unused.sock"
            stderr = io.StringIO()
            result = MODULE._run(
                MODULE.build_parser().parse_args(
                    [
                        "--socket",
                        str(path),
                        "--send-host",
                        "02",
                        "--connect-timeout",
                        "0.01",
                    ]
                ),
                stdout=io.StringIO(),
                stderr=stderr,
            )
            self.assertEqual(result, 2)
            self.assertIn("usb_restore_session:", stderr.getvalue())

    def test_cli_ordered_steps_interleave_send_expect_and_recv(self) -> None:
        actions = (
            ("recv", 6),
            ("send", bytes.fromhex("0402")),
            ("recv", 8),
            ("send", bytes.fromhex("aabbcc")),
        )
        with ScriptedUnixSocketHarness(actions) as harness:
            stdout = io.StringIO()
            stderr = io.StringIO()
            result = MODULE._run(
                MODULE.build_parser().parse_args(
                    [
                        "--socket",
                        str(harness.path),
                        "--step",
                        "send:0202",
                        "--step",
                        "expect:0402",
                        "--step",
                        "timeout:1",
                        "--step",
                        "event:01,2:aabb",
                        "--step",
                        "expect-prefix:aabb",
                        "--connect-timeout",
                        "1",
                        "--recv-timeout",
                        "1",
                        "--jsonl",
                        "-",
                    ]
                ),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(result, 0, stderr.getvalue())
            self.assertEqual([item.hex() for item in harness.received], [
                "000000000202",
                "020000000102aabb",
            ])
            events = [json.loads(line) for line in stdout.getvalue().splitlines()]
            self.assertEqual(events[1]["event"], "send-host")
            self.assertEqual(events[2]["event"], "recv-guest")
            self.assertEqual(events[4]["event"], "timeout")
            self.assertEqual(events[5]["event"], "send-host")
            self.assertEqual(events[5]["endpoint"], 1)
            self.assertEqual(events[5]["packet_kind"], 2)
            self.assertEqual(events[5]["payload_bytes"], 2)
            self.assertEqual(events[6]["hex"], "aabbcc")
            self.assertEqual(events[7]["event"], "recv-prefix-match")
            self.assertEqual(events[7]["expected_prefix"], "aabb")

    def test_cli_semantic_recovery_steps_emit_ep0_control_frames(self) -> None:
        getenv_frame = bytes.fromhex(
            "1d0000000001"
            "4000000000001500"
            "676574656e76206275696c642d76657273696f6e00"
        )
        control_in_frame = bytes.fromhex("080000000001c00000000000ff00")
        getenv_response = bytes.fromhex("0100") + b"mBoot-18000.161.9\x00"
        actions = (
            ("recv", len(getenv_frame)),
            ("send", bytes.fromhex("0100")),
            ("recv", len(control_in_frame)),
            ("send", getenv_response),
        )
        with ScriptedUnixSocketHarness(actions) as harness:
            stdout = io.StringIO()
            stderr = io.StringIO()
            result = MODULE._run(
                MODULE.build_parser().parse_args(
                    [
                        "--socket",
                        str(harness.path),
                        "--step",
                        "command:getenv build-version",
                        "--step",
                        "expect:0100",
                        "--step",
                        "control-in:0xff",
                        "--step",
                        "expect-prefix:0100",
                        "--connect-timeout",
                        "1",
                        "--recv-timeout",
                        "1",
                        "--jsonl",
                        "-",
                    ]
                ),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(result, 0, stderr.getvalue())
            self.assertEqual(harness.received, [getenv_frame, control_in_frame])
            events = [json.loads(line) for line in stdout.getvalue().splitlines()]
            self.assertEqual(events[1]["endpoint"], 0)
            self.assertEqual(events[1]["packet_kind"], 1)
            self.assertEqual(events[1]["payload_bytes"], 29)
            self.assertEqual(events[2]["hex"], "0100")
            self.assertEqual(events[4]["payload_bytes"], 8)
            self.assertEqual(events[5]["hex"], getenv_response.hex())
            self.assertEqual(events[6]["event"], "recv-prefix-match")

    def test_cli_semantic_upload_steps_emit_buffer_start_bulk_and_zlp(self) -> None:
        buffer_start_frame = bytes.fromhex("0800000000014100000000000000")
        bulk_frame = bytes.fromhex("020000000401aabb")
        bulk_zlp_frame = bytes.fromhex("000000000401")
        actions = (
            ("recv", len(buffer_start_frame)),
            ("send", bytes.fromhex("0100")),
            ("recv", len(bulk_frame)),
            ("send", bytes.fromhex("0104")),
            ("recv", len(bulk_zlp_frame)),
            ("send", bytes.fromhex("0104")),
        )
        with ScriptedUnixSocketHarness(actions) as harness:
            stdout = io.StringIO()
            stderr = io.StringIO()
            result = MODULE._run(
                MODULE.build_parser().parse_args(
                    [
                        "--socket",
                        str(harness.path),
                        "--step",
                        "buffer-start",
                        "--step",
                        "expect:0100",
                        "--step",
                        "bulk:aabb",
                        "--step",
                        "expect:0104",
                        "--step",
                        "bulk-zlp",
                        "--step",
                        "expect:0104",
                        "--connect-timeout",
                        "1",
                        "--recv-timeout",
                        "1",
                        "--jsonl",
                        "-",
                    ]
                ),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(result, 0, stderr.getvalue())
            self.assertEqual(harness.received, [buffer_start_frame, bulk_frame, bulk_zlp_frame])
            events = [json.loads(line) for line in stdout.getvalue().splitlines()]
            self.assertEqual(events[1]["endpoint"], 0)
            self.assertEqual(events[1]["payload_bytes"], 8)
            self.assertEqual(events[4]["endpoint"], 4)
            self.assertEqual(events[4]["payload_bytes"], 2)
            self.assertEqual(events[7]["endpoint"], 4)
            self.assertEqual(events[7]["payload_bytes"], 0)

    def test_cli_recovery_open_sends_each_setup_and_drains_its_ack(self) -> None:
        sequence = MODULE.recovery_open_sequence()
        actions = tuple(
            action
            for packet, ack in sequence
            for action in (("recv", len(packet.to_frame())), ("send", ack))
        )
        with ScriptedUnixSocketHarness(actions) as harness:
            stderr = io.StringIO()
            result = MODULE._run(
                MODULE.build_parser().parse_args(
                    [
                        "--socket", str(harness.path),
                        "--step", "recovery-open",
                        "--connect-timeout", "1",
                        "--recv-timeout", "1",
                    ]
                ),
                stdout=io.StringIO(),
                stderr=stderr,
            )
            self.assertEqual(result, 0, stderr.getvalue())
            self.assertEqual(
                harness.received,
                [packet.to_frame() for packet, _ack in sequence],
            )

    def test_cli_upload_file_step_sends_complete_recovery_upload(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            upload_path = Path(directory_name) / "component.img4"
            upload_path.write_bytes(b"abc")
            buffer_start_frame = MODULE.build_recovery_buffer_start_packet().to_frame()
            bulk_frame = MODULE.build_recovery_bulk_out_packet(b"abc").to_frame()
            actions = (
                ("recv", len(buffer_start_frame)),
                ("send", bytes.fromhex("0100")),
                ("recv", len(bulk_frame)),
                ("send", bytes.fromhex("0104")),
            )
            with ScriptedUnixSocketHarness(actions) as harness:
                stdout = io.StringIO()
                stderr = io.StringIO()
                result = MODULE._run(
                    MODULE.build_parser().parse_args(
                        [
                            "--socket",
                            str(harness.path),
                            "--step",
                            f"upload-file:{upload_path}",
                            "--connect-timeout",
                            "1",
                            "--recv-timeout",
                            "1",
                            "--jsonl",
                            "-",
                        ]
                    ),
                    stdout=stdout,
                    stderr=stderr,
                )
                self.assertEqual(result, 0, stderr.getvalue())
                self.assertEqual(harness.received, [buffer_start_frame, bulk_frame])
                events = [json.loads(line) for line in stdout.getvalue().splitlines()]
                self.assertEqual(events[1]["event"], "upload-file-start")
                self.assertEqual(events[9]["event"], "upload-file-complete")

    def test_cli_rejects_mixing_ordered_steps_with_legacy_options(self) -> None:
        stderr = io.StringIO()
        result = MODULE._run(
            MODULE.build_parser().parse_args(
                [
                    "--socket",
                    "/tmp/unused.sock",
                    "--step",
                    "send:0202",
                    "--send-host",
                    "0202",
                ]
            ),
            stdout=io.StringIO(),
            stderr=stderr,
        )
        self.assertEqual(result, 2)
        self.assertIn("cannot be mixed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
