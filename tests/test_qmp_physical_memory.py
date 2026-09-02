from __future__ import annotations

import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from qmp_physical_memory import (  # noqa: E402
    QMPPhysicalMemoryError,
    parse_u64_literal,
    verify_physical_image,
)


class FakeQMP:
    def __init__(self, root: Path, physical: bytes, *, hmp_response: str = "") -> None:
        self.path = root / "qmp.sock"
        self.physical = physical
        self.hmp_response = hmp_response
        self.commands: list[dict[str, object]] = []
        self.error: BaseException | None = None
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(self.path))
        self.server.listen(1)
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self) -> "FakeQMP":
        self.thread.start()
        return self

    def __exit__(self, *args) -> None:
        self.thread.join(timeout=2)
        self.server.close()
        self.path.unlink(missing_ok=True)
        if self.error is not None:
            raise self.error

    def _serve(self) -> None:
        try:
            connection, _ = self.server.accept()
            with connection:
                stream = connection.makefile("rwb", buffering=0)
                stream.write(json.dumps({"QMP": {"version": {}}}).encode() + b"\n")
                capabilities = json.loads(stream.readline())
                self.commands.append(capabilities)
                stream.write(json.dumps({"return": {}}).encode() + b"\n")
                command = json.loads(stream.readline())
                self.commands.append(command)
                line = command["arguments"]["command-line"]
                output_literal = line.split('"', 2)[1]
                if not self.hmp_response:
                    Path(output_literal).write_bytes(self.physical)
                stream.write(json.dumps({"return": self.hmp_response}).encode() + b"\n")
        except BaseException as error:
            self.error = error


class QMPPhysicalMemoryTests(unittest.TestCase):
    def test_reads_physical_memory_and_matches_the_expected_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "trustcache-region.raw"
            expected.write_bytes(b"t" * 4096)
            output = root / "trustcache-physical.bin"
            with FakeQMP(root, expected.read_bytes()) as qmp:
                resolved, digest, size = verify_physical_image(
                    qmp_socket=str(qmp.path),
                    address=0x460000000,
                    expected_image=str(expected),
                    output=str(output),
                    allowed_root=str(root),
                )
            self.assertEqual(resolved, output)
            self.assertEqual(size, 4096)
            self.assertEqual(len(digest), 64)
            self.assertEqual(qmp.commands[0], {"execute": "qmp_capabilities"})
            hmp = qmp.commands[1]["arguments"]["command-line"]
            self.assertEqual(
                hmp,
                f'pmemsave 0x460000000 4096 "{output}"',
            )

    def test_rejects_hmp_error_and_mismatching_physical_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected.raw"
            expected.write_bytes(b"a" * 4096)
            with FakeQMP(root, b"a" * 4096, hmp_response="invalid address") as qmp:
                with self.assertRaisesRegex(QMPPhysicalMemoryError, "pmemsave failed"):
                    verify_physical_image(
                        qmp_socket=str(qmp.path),
                        address=0x1000,
                        expected_image=str(expected),
                        output=str(root / "error.bin"),
                        allowed_root=str(root),
                    )
            with FakeQMP(root, b"b" * 4096) as qmp:
                with self.assertRaisesRegex(QMPPhysicalMemoryError, "does not match"):
                    verify_physical_image(
                        qmp_socket=str(qmp.path),
                        address=0x1000,
                        expected_image=str(expected),
                        output=str(root / "mismatch.bin"),
                        allowed_root=str(root),
                    )

    def test_rejects_unsafe_paths_sizes_addresses_and_timeouts(self) -> None:
        self.assertEqual(parse_u64_literal("0x460000000"), 0x460000000)
        for value in ("bad", "-1", str(1 << 64)):
            with self.subTest(value=value):
                with self.assertRaises(QMPPhysicalMemoryError):
                    parse_u64_literal(value)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "empty.raw"
            expected.touch()
            not_socket = root / "not-a-socket"
            not_socket.touch()
            for timeout in (0, -1, 61):
                with self.subTest(timeout=timeout):
                    with self.assertRaises(QMPPhysicalMemoryError):
                        verify_physical_image(
                            qmp_socket=str(not_socket),
                            address=0,
                            expected_image=str(expected),
                            output=str(root / f"out-{timeout}"),
                            allowed_root=str(root),
                            timeout=timeout,
                        )
            with self.assertRaisesRegex(QMPPhysicalMemoryError, "unsafe size"):
                verify_physical_image(
                    qmp_socket=str(not_socket),
                    address=0,
                    expected_image=str(expected),
                    output=str(root / "out.bin"),
                    allowed_root=str(root),
                )

    def test_expected_image_and_output_cannot_escape_or_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "run"
            root.mkdir()
            outside = parent / "outside.raw"
            outside.write_bytes(b"x" * 4096)
            link = root / "escape.raw"
            link.symlink_to(outside)
            fake_socket = root / "qmp.sock"
            fake_socket.touch()
            with self.assertRaisesRegex(QMPPhysicalMemoryError, "inside"):
                verify_physical_image(
                    qmp_socket=str(fake_socket),
                    address=0,
                    expected_image=str(link),
                    output=str(root / "out.bin"),
                    allowed_root=str(root),
                )

            expected = root / "expected.raw"
            expected.write_bytes(b"x" * 4096)
            output = root / "existing.bin"
            output.touch()
            with self.assertRaisesRegex(QMPPhysicalMemoryError, "already exists"):
                verify_physical_image(
                    qmp_socket=str(fake_socket),
                    address=0,
                    expected_image=str(expected),
                    output=str(output),
                    allowed_root=str(root),
                )


if __name__ == "__main__":
    unittest.main()
