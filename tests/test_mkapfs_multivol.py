"""Opt-in real formatter/checker tests; isolated Linux validation VM only."""
import os
from pathlib import Path
import platform
import struct
import subprocess
import tempfile
import unittest
import uuid

from tools.build_vmapple_isc import fletcher64


@unittest.skipUnless(os.environ.get("MACVM_TEST_MKAPFS") == "YES", "explicit formatter opt-in required")
class MultiVolumeFormatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (platform.system(), platform.machine(), platform.node()) != ("Linux", "x86_64", "macvm-validation"):
            raise RuntimeError("formatter tests require isolated macvm-validation")
        base = Path(__file__).resolve().parents[1] / "third_party/apfsprogs-validation"
        cls.formatter = base / "mkapfs/mkapfs"
        cls.checker = base / "apfsck/apfsck"
        for binary in (cls.formatter, cls.checker):
            if not binary.is_file():
                raise RuntimeError(f"missing binary: {binary}")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="macvm-multivol-")
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "fresh.apfs"
        self.image.touch(exist_ok=False)

    def format(self, specs, size=2 * 1024**3, extra=()):
        with self.image.open("r+b") as out:
            out.truncate(size)
        args = [str(self.formatter), *extra]
        for spec in specs:
            args += ["-V", spec]
        return subprocess.run([*args, str(self.image)], capture_output=True, timeout=30)

    def block(self, number):
        with self.image.open("rb") as stream:
            stream.seek(number * 4096)
            data = stream.read(4096)
        self.assertEqual(len(data), 4096)
        self.assertEqual(struct.unpack_from("<Q", data)[0], fletcher64(data[8:]))
        return data

    def omap(self, number):
        omap = self.block(number)
        root = self.block(struct.unpack_from("<Q", omap, 0x30)[0])
        count = struct.unpack_from("<I", root, 0x24)[0]
        table_off, table_len = struct.unpack_from("<HH", root, 0x28)
        records = []
        for i in range(count):
            keyoff, valoff = struct.unpack_from("<HH", root, 0x38 + table_off + 4*i)
            key = struct.unpack_from("<Q", root, 0x38 + table_off + table_len + keyoff)[0]
            physical = struct.unpack_from("<Q", root, 4096 - 40 - valoff + 8)[0]
            records.append((key, physical))
        self.assertEqual(records, sorted(records))
        return records

    def test_one_through_four_volumes_pass_independent_checker_and_maps(self):
        roles = [0x100, 0x10, 0x140, 0]
        names = ["xART", "iSCPreboot", "Hardware", "Spare"]
        for count in range(1, 5):
            with self.subTest(count=count):
                ids = [uuid.uuid4() for _ in range(count)]
                specs = [f"{names[i]},{ids[i]},{roles[i]}" for i in range(count)]
                result = self.format(specs)
                self.assertEqual(result.returncode, 0, result.stderr)
                checked = subprocess.run([str(self.checker), "-cuw", str(self.image)], capture_output=True, timeout=30)
                self.assertEqual(checked.returncode, 0, checked.stderr + checked.stdout)
                nx = self.block(0)
                nx_ids = struct.unpack_from("<4Q", nx, 0xb8)
                records = self.omap(struct.unpack_from("<Q", nx, 0xa0)[0])
                self.assertEqual([oid for oid, _ in records], list(nx_ids[:count]))
                self.assertEqual(list(nx_ids[count:]), [0] * (4 - count))
                catalog_blocks = set()
                for i, (oid, physical) in enumerate(records):
                    volume = self.block(physical)
                    self.assertEqual(volume[0x20:0x24], b"APSB")
                    self.assertEqual(struct.unpack_from("<I", volume, 0x24)[0], i)
                    self.assertEqual(struct.unpack_from("<H", volume, 0x3c4)[0], roles[i])
                    self.assertEqual(volume[0xf0:0x100], ids[i].bytes)
                    self.assertEqual(volume[0x2c0:0x3c0].split(b"\0")[0], names[i].encode())
                    catalog = self.omap(struct.unpack_from("<Q", volume, 0x80)[0])
                    self.assertEqual(len(catalog), 1)
                    self.assertEqual(catalog[0][0], struct.unpack_from("<Q", volume, 0x88)[0])
                    self.block(catalog[0][1])
                    catalog_blocks.add(catalog[0][1])
                self.assertEqual(len(catalog_blocks), count)
                # Every case starts with a new zero-filled sparse file.
                with self.image.open("wb"):
                    pass

    def test_legacy_single_volume(self):
        result = self.format([], size=32 * 1024**2, extra=("-L", "legacy"))
        self.assertEqual(result.returncode, 0, result.stderr)
        checked = subprocess.run([str(self.checker), "-cuw", str(self.image)], capture_output=True, timeout=30)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def assert_rejected_without_write(self, specs, *, extra=(), size=2 * 1024**3):
        marker = b"NOT A FILESYSTEM" * 256
        self.image.write_bytes(marker)
        result = self.format(specs, size=size, extra=extra)
        self.assertNotEqual(result.returncode, 0)
        with self.image.open("rb") as stream:
            self.assertEqual(stream.read(len(marker)), marker)

    def test_malformed_specs_rejected_before_write(self):
        good = str(uuid.uuid4())
        for spec in ["", "x", f"x,{good}", f",{good},0", f"{'x'*256},{good},0",
                     "x,not-a-uuid,0", f"x,{good},-1", f"x,{good},9999999999999999999999",
                     f"x,{good},0x10junk", f"x,{good},1", f"x,{good},0,extra"]:
            with self.subTest(spec=spec):
                self.assert_rejected_without_write([spec])

    def test_duplicate_uuid_and_overlimit_rejected(self):
        uid = str(uuid.uuid4())
        self.assert_rejected_without_write([f"a,{uid},0", f"b,{uid.upper()},0"])
        self.assert_rejected_without_write([f"v{i},{uuid.uuid4()},0" for i in range(5)])
        self.assert_rejected_without_write([f"a,{uid},0"], extra=("-U", uid))

    def test_legacy_conflict_and_small_container_rejected(self):
        specs = [f"v{i},{uuid.uuid4()},0" for i in range(3)]
        self.assert_rejected_without_write(specs, extra=("-L", "conflict"))
        self.assert_rejected_without_write(specs, extra=("-u", str(uuid.uuid4())))
        self.assert_rejected_without_write(specs, size=32 * 1024**2)


if __name__ == "__main__":
    unittest.main()
