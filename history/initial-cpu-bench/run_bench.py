#!/usr/bin/env python3
import csv
import json
import os
import platform
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = 5
MODES = {
    "x86_vm_native": ["taskset", "-c", "0", str(ROOT / "bench-x86_64")],
    "x86_tcg": ["taskset", "-c", "0", "qemu-x86_64", str(ROOT / "bench-x86_64")],
    "arm64_tcg": ["taskset", "-c", "0", "qemu-aarch64", str(ROOT / "bench-arm64")],
}


def invoke(command):
    started = time.perf_counter()
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    wall = time.perf_counter() - started
    records = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    if len(records) != 6:
        raise RuntimeError(f"expected six cases, received {len(records)}: {result.stdout!r}")
    return wall, records


def main():
    rows = []
    checksums = {}
    for mode, command in MODES.items():
        print(f"warmup {mode}", flush=True)
        invoke(command)
        for run in range(1, RUNS + 1):
            wall, records = invoke(command)
            print(f"run {run}/{RUNS} {mode}: wall={wall:.3f}s", flush=True)
            for record in records:
                key = record["case"]
                checksums.setdefault(key, set()).add(record["checksum"])
                rows.append({"mode": mode, "run": run, **record, "process_wall_seconds": wall})

    bad = {case: values for case, values in checksums.items() if len(values) != 1}
    if bad:
        raise RuntimeError(f"cross-architecture checksum mismatch: {bad}")

    raw_path = ROOT / "results.csv"
    with raw_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    cases = sorted({row["case"] for row in rows})
    summary = []
    medians = {}
    for case in cases:
        medians[case] = {}
        for mode in MODES:
            values = [float(row["seconds"]) for row in rows if row["case"] == case and row["mode"] == mode]
            medians[case][mode] = statistics.median(values)
        native = medians[case]["x86_vm_native"]
        x86_tcg = medians[case]["x86_tcg"]
        arm_tcg = medians[case]["arm64_tcg"]
        summary.append({
            "case": case,
            "x86_vm_native_s": native,
            "x86_tcg_s": x86_tcg,
            "arm64_tcg_s": arm_tcg,
            "x86_tcg_over_native": x86_tcg / native,
            "arm64_tcg_over_native": arm_tcg / native,
            "arm64_over_x86_tcg": arm_tcg / x86_tcg,
        })

    metadata = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "runs": RUNS,
        "commands": MODES,
        "checksum_consistent": True,
        "summary": summary,
    }
    (ROOT / "results.json").write_text(json.dumps(metadata, indent=2) + "\n")

    print("\ncase,x86_vm_native_s,x86_tcg_s,arm64_tcg_s,x86_tcg/native,arm64_tcg/native,arm64/x86_tcg")
    for row in summary:
        print(
            f'{row["case"]},{row["x86_vm_native_s"]:.6f},{row["x86_tcg_s"]:.6f},'
            f'{row["arm64_tcg_s"]:.6f},{row["x86_tcg_over_native"]:.2f},'
            f'{row["arm64_tcg_over_native"]:.2f},{row["arm64_over_x86_tcg"]:.2f}'
        )


if __name__ == "__main__":
    main()
