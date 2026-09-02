from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compare_cpu_bench", ROOT / "tools" / "compare_cpu_bench.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sample(case: str, seconds: float, checksum: str = "ok", work: int = 100):
    return MODULE.Sample(case=case, seconds=seconds, work=work, checksum=checksum)


class ParseSerialTests(unittest.TestCase):
    def write_log(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "serial.log"
        path.write_text(text, encoding="utf-8")
        return path

    def test_parses_crlf_and_ignores_non_json_console_lines(self) -> None:
        path = self.write_log(
            "booting\r\nSYSTEM_RUN 1\r\n"
            '{"case":"integer","seconds":1.25,"work":100,"checksum":"abc"}\r\n'
            "SYSTEM_BENCH_DONE\r\n"
        )
        self.assertEqual(
            MODULE.parse_serial(path),
            [MODULE.Sample("integer", 1.25, 100, "abc")],
        )

    def test_rejects_missing_completion_marker(self) -> None:
        path = self.write_log('{"case":"integer","seconds":1,"work":1,"checksum":"x"}\n')
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "missing SYSTEM_BENCH_DONE"):
            MODULE.parse_serial(path)

    def test_rejects_malformed_record(self) -> None:
        path = self.write_log('{"case":"integer",broken}\nSYSTEM_BENCH_DONE\n')
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "invalid benchmark JSON"):
            MODULE.parse_serial(path)

    def test_rejects_missing_record_field(self) -> None:
        path = self.write_log('{"case":"integer","seconds":1}\nSYSTEM_BENCH_DONE\n')
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "invalid benchmark JSON"):
            MODULE.parse_serial(path)

    def test_rejects_zero_negative_nan_and_infinite_seconds(self) -> None:
        for value in ("0", "-1", '"NaN"', '"Infinity"'):
            with self.subTest(value=value):
                path = self.write_log(
                    f'{{"case":"integer","seconds":{value},"work":1,"checksum":"x"}}\n'
                    "SYSTEM_BENCH_DONE\n"
                )
                with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "seconds must be"):
                    MODULE.parse_serial(path)

    def test_rejects_non_positive_work(self) -> None:
        path = self.write_log(
            '{"case":"integer","seconds":1,"work":0,"checksum":"x"}\nSYSTEM_BENCH_DONE\n'
        )
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "work must be positive"):
            MODULE.parse_serial(path)

    def test_rejects_log_without_records(self) -> None:
        path = self.write_log("SYSTEM_BENCH_DONE\n")
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "no benchmark records"):
            MODULE.parse_serial(path)


class CompareTests(unittest.TestCase):
    def complete(self, seconds: float, **overrides):
        return [
            sample(case, seconds, **overrides)
            for case in MODULE.EXPECTED_CASES
        ]

    def test_computes_median_speedup_improvement_and_cv(self) -> None:
        baseline = self.complete(2.0) + self.complete(4.0)
        candidate = self.complete(1.0) + self.complete(3.0)
        rows = MODULE.compare(baseline, candidate)
        self.assertEqual(len(rows), len(MODULE.EXPECTED_CASES))
        self.assertAlmostEqual(rows[0].baseline_median_seconds, 3.0)
        self.assertAlmostEqual(rows[0].candidate_median_seconds, 2.0)
        self.assertAlmostEqual(rows[0].speedup, 1.5)
        self.assertAlmostEqual(rows[0].improvement_percent, 50.0)
        self.assertGreater(rows[0].baseline_cv_percent, 0.0)
        self.assertGreater(rows[0].candidate_cv_percent, 0.0)

    def test_geometric_mean_uses_all_rows(self) -> None:
        rows = MODULE.compare(self.complete(4.0), self.complete(2.0))
        self.assertAlmostEqual(MODULE.geometric_mean_speedup(rows), 2.0)

    def test_rejects_unexpected_case(self) -> None:
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "unexpected benchmark case"):
            MODULE.compare(self.complete(1.0) + [sample("unknown", 1.0)], self.complete(1.0))

    def test_rejects_missing_case(self) -> None:
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "missing benchmark cases"):
            MODULE.compare(self.complete(1.0)[:-1], self.complete(1.0))

    def test_rejects_unequal_sample_counts(self) -> None:
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "unequal sample counts"):
            MODULE.compare(self.complete(1.0) + [sample("integer", 1.0)], self.complete(1.0))

    def test_rejects_checksum_mismatch(self) -> None:
        candidate = self.complete(1.0)
        candidate[0] = sample("integer", 1.0, checksum="wrong")
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "work or checksum mismatch"):
            MODULE.compare(self.complete(1.0), candidate)

    def test_rejects_work_mismatch(self) -> None:
        candidate = self.complete(1.0)
        candidate[0] = sample("integer", 1.0, work=101)
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "work or checksum mismatch"):
            MODULE.compare(self.complete(1.0), candidate)

    def test_single_sample_cv_is_zero(self) -> None:
        rows = MODULE.compare(self.complete(2.0), self.complete(1.0))
        self.assertEqual(rows[0].baseline_cv_percent, 0.0)
        self.assertEqual(rows[0].candidate_cv_percent, 0.0)

    def test_empty_geometric_mean_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.BenchmarkFormatError, "without comparisons"):
            MODULE.geometric_mean_speedup([])


class CliTests(unittest.TestCase):
    def test_cli_combines_repeated_logs_and_writes_json_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            paths: list[Path] = []
            for name, seconds in (("b1", 4), ("b2", 4), ("c1", 2), ("c2", 2)):
                path = directory / f"{name}.log"
                records = [
                    json.dumps({"case": case, "seconds": seconds, "work": 100, "checksum": "ok"})
                    for case in MODULE.EXPECTED_CASES
                ]
                path.write_text("\n".join(records + ["SYSTEM_BENCH_DONE", ""]), encoding="utf-8")
                paths.append(path)
            csv_path = directory / "result.csv"
            json_path = directory / "result.json"
            result = MODULE.main(
                [
                    "--baseline", str(paths[0]), "--baseline", str(paths[1]),
                    "--candidate", str(paths[2]), "--candidate", str(paths[3]),
                    "--csv", str(csv_path), "--json", str(json_path),
                ]
            )
            self.assertEqual(result, 0)
            self.assertEqual(len(csv_path.read_text(encoding="utf-8").splitlines()), 7)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertAlmostEqual(payload["geometric_mean_speedup"], 2.0)
            self.assertEqual(payload["comparisons"][0]["baseline_samples"], 2)


if __name__ == "__main__":
    unittest.main()
