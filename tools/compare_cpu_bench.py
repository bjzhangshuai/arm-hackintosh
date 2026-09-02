#!/usr/bin/env python3
"""Validate and compare JSONL records embedded in QEMU serial logs."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import statistics
from typing import Iterable, Sequence


EXPECTED_CASES = (
    "integer",
    "branch",
    "memory_seq",
    "pointer_chase",
    "syscall",
    "atomic",
)


class BenchmarkFormatError(ValueError):
    """Raised when a serial log cannot support a valid comparison."""


@dataclass(frozen=True)
class Sample:
    case: str
    seconds: float
    work: int
    checksum: str


@dataclass(frozen=True)
class Comparison:
    case: str
    baseline_median_seconds: float
    candidate_median_seconds: float
    speedup: float
    improvement_percent: float
    baseline_samples: int
    candidate_samples: int
    baseline_cv_percent: float
    candidate_cv_percent: float
    work: int
    checksum: str


def parse_serial(path: Path) -> list[Sample]:
    text = path.read_text(encoding="utf-8", errors="replace").replace("\r", "")
    if "SYSTEM_BENCH_DONE" not in text.splitlines():
        raise BenchmarkFormatError(f"{path}: missing SYSTEM_BENCH_DONE")

    samples: list[Sample] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
            sample = Sample(
                case=str(value["case"]),
                seconds=float(value["seconds"]),
                work=int(value["work"]),
                checksum=str(value["checksum"]),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise BenchmarkFormatError(f"{path}:{line_number}: invalid benchmark JSON: {exc}") from exc
        if not math.isfinite(sample.seconds) or sample.seconds <= 0:
            raise BenchmarkFormatError(f"{path}:{line_number}: seconds must be finite and positive")
        if sample.work <= 0:
            raise BenchmarkFormatError(f"{path}:{line_number}: work must be positive")
        samples.append(sample)

    if not samples:
        raise BenchmarkFormatError(f"{path}: no benchmark records")
    return samples


def _group(samples: Iterable[Sample], expected_cases: Sequence[str]) -> dict[str, list[Sample]]:
    grouped = {case: [] for case in expected_cases}
    for sample in samples:
        if sample.case not in grouped:
            raise BenchmarkFormatError(f"unexpected benchmark case: {sample.case}")
        grouped[sample.case].append(sample)
    missing = [case for case, values in grouped.items() if not values]
    if missing:
        raise BenchmarkFormatError(f"missing benchmark cases: {', '.join(missing)}")
    return grouped


def _cv_percent(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values) / statistics.mean(values) * 100.0


def compare(
    baseline: Iterable[Sample],
    candidate: Iterable[Sample],
    expected_cases: Sequence[str] = EXPECTED_CASES,
) -> list[Comparison]:
    base = _group(baseline, expected_cases)
    cand = _group(candidate, expected_cases)
    output: list[Comparison] = []

    for case in expected_cases:
        base_values = base[case]
        cand_values = cand[case]
        if len(base_values) != len(cand_values):
            raise BenchmarkFormatError(
                f"{case}: unequal sample counts ({len(base_values)} baseline, {len(cand_values)} candidate)"
            )
        signatures = {(item.work, item.checksum) for item in base_values + cand_values}
        if len(signatures) != 1:
            raise BenchmarkFormatError(f"{case}: work or checksum mismatch")

        base_seconds = [item.seconds for item in base_values]
        cand_seconds = [item.seconds for item in cand_values]
        base_median = statistics.median(base_seconds)
        cand_median = statistics.median(cand_seconds)
        speedup = base_median / cand_median
        work, checksum = signatures.pop()
        output.append(
            Comparison(
                case=case,
                baseline_median_seconds=base_median,
                candidate_median_seconds=cand_median,
                speedup=speedup,
                improvement_percent=(speedup - 1.0) * 100.0,
                baseline_samples=len(base_values),
                candidate_samples=len(cand_values),
                baseline_cv_percent=_cv_percent(base_seconds),
                candidate_cv_percent=_cv_percent(cand_seconds),
                work=work,
                checksum=checksum,
            )
        )
    return output


def geometric_mean_speedup(rows: Sequence[Comparison]) -> float:
    if not rows:
        raise BenchmarkFormatError("cannot compute a geometric mean without comparisons")
    return math.exp(statistics.mean(math.log(row.speedup) for row in rows))


def _load(paths: Sequence[Path]) -> list[Sample]:
    return [sample for path in paths for sample in parse_serial(path)]


def _write_csv(path: Path, rows: Sequence[Comparison]) -> None:
    fields = list(asdict(rows[0]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, action="append", required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args(argv)

    rows = compare(_load(args.baseline), _load(args.candidate))
    _write_csv(args.csv, rows)
    payload = {
        "baseline_logs": [str(path) for path in args.baseline],
        "candidate_logs": [str(path) for path in args.candidate],
        "geometric_mean_speedup": geometric_mean_speedup(rows),
        "comparisons": [asdict(row) for row in rows],
    }
    args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
