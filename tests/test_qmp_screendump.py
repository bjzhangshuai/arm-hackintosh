from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "qmp_screendump.py"
SPEC = importlib.util.spec_from_file_location("qmp_screendump", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeQMP:
    def __init__(self, socket_path: Path, output_path: Path, *, command_error: bool = False) -> None:
        self.socket_path = socket_path
        self.output_path = output_path
        self.command_error = command_error
        self.requests: list[dict[str, object]] = []
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self) -> "FakeQMP":
        self.thread.start()
        self.ready.wait(2)
        return self

    def __exit__(self, *_: object) -> None:
        self.thread.join(2)

    def _serve(self) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(self.socket_path))
            server.listen(1)
            self.ready.set()
            conn, _ = server.accept()
            with conn, conn.makefile("rb") as reader:
                conn.sendall(b'{"QMP":{"version":{},"capabilities":[]}}\r\n')
                for index in range(2):
                    request = json.loads(reader.readline())
                    self.requests.append(request)
                    if index == 1 and self.command_error:
                        conn.sendall(b'{"error":{"class":"GenericError","desc":"no display"}}\r\n')
                    else:
                        if index == 1:
                            self.output_path.write_bytes(b"P6\n1 1\n255\n\0\0\0")
                        conn.sendall(b'{"return":{}}\r\n')


class QMPScreendumpTests(unittest.TestCase):
    def test_capture_negotiates_capabilities_and_requests_screendump(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            socket_path = directory / "qmp.sock"
            output_path = directory / "screen.ppm"
            with FakeQMP(socket_path, output_path) as fake:
                MODULE.capture(socket_path, output_path, 2.0)
            self.assertEqual(fake.requests[0], {"execute": "qmp_capabilities"})
            self.assertEqual(
                fake.requests[1],
                {"execute": "screendump", "arguments": {"filename": str(output_path)}},
            )
            self.assertTrue(output_path.read_bytes().startswith(b"P6\n"))

    def test_capture_propagates_qmp_command_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            socket_path = directory / "qmp.sock"
            output_path = directory / "screen.ppm"
            with FakeQMP(socket_path, output_path, command_error=True):
                with self.assertRaisesRegex(MODULE.QMPError, "no display"):
                    MODULE.capture(socket_path, output_path, 2.0)

    def test_capture_requires_existing_socket(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with self.assertRaisesRegex(MODULE.QMPError, "does not exist"):
                MODULE.capture(directory / "missing.sock", directory / "screen.ppm", 1.0)

    def test_capture_requires_absolute_ppm_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            socket_path = Path(temp) / "qmp.sock"
            socket_path.touch()
            with self.assertRaisesRegex(MODULE.QMPError, "absolute"):
                MODULE.capture(socket_path, Path("screen.ppm"), 1.0)
            with self.assertRaisesRegex(MODULE.QMPError, r"\.ppm"):
                MODULE.capture(socket_path, Path(temp) / "screen.png", 1.0)

    def test_cli_rejects_nonpositive_timeout(self) -> None:
        with self.assertRaises(SystemExit):
            MODULE.parse_args(["/tmp/qmp.sock", "/tmp/screen.ppm", "--timeout", "0"])


if __name__ == "__main__":
    unittest.main()
