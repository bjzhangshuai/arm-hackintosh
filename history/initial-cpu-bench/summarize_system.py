#!/usr/bin/env python3
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
serial = (ROOT / "nested-arm64/serial-direct.log").read_text(errors="replace")

rows = []
run = None
capture = []
for raw_line in serial.splitlines():
    line = raw_line.strip()
    if line.startswith("SYSTEM_RUN "):
        run = int(line.split()[-1])
        capture.append(line)
    elif line.startswith("{") and run is not None:
        record = json.loads(line)
        rows.append({"mode": "arm64_system_tcg", "run": run, **record})
        capture.append(line)
    elif line == "SYSTEM_BENCH_DONE":
        capture.append(line)
        break

if len(rows) != 30 or {row["run"] for row in rows} != set(range(1, 6)):
    raise RuntimeError(f"expected 30 records across five runs, received {len(rows)}")

with (ROOT / "full-system-results.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(ROOT / "full-system-output.txt").write_text("\n".join(capture) + "\n")

user_rows = list(csv.DictReader((ROOT / "results.csv").open()))
cases = sorted({row["case"] for row in rows})
summary = []
for case in cases:
    def user_median(mode):
        return statistics.median(
            float(row["seconds"]) for row in user_rows
            if row["case"] == case and row["mode"] == mode
        )

    native = user_median("x86_vm_native")
    x86_tcg = user_median("x86_tcg")
    arm_user = user_median("arm64_tcg")
    arm_system = statistics.median(float(row["seconds"]) for row in rows if row["case"] == case)
    expected = {row["checksum"] for row in user_rows if row["case"] == case}
    actual = {row["checksum"] for row in rows if row["case"] == case}
    if actual != expected:
        raise RuntimeError(f"checksum mismatch for {case}: system={actual}, user={expected}")
    summary.append({
        "case": case,
        "x86_vm_native_s": native,
        "x86_user_tcg_s": x86_tcg,
        "arm64_user_tcg_s": arm_user,
        "arm64_system_tcg_s": arm_system,
        "arm64_system_over_x86_vm": arm_system / native,
        "arm64_system_over_arm64_user_tcg": arm_system / arm_user,
    })

non_atomic = [row for row in summary if row["case"] != "atomic"]
aggregate = {
    "geomean_arm64_system_over_x86_vm_excluding_atomic": math.prod(
        row["arm64_system_over_x86_vm"] for row in non_atomic
    ) ** (1 / len(non_atomic)),
    "geomean_arm64_system_over_arm64_user_tcg_excluding_atomic": math.prod(
        row["arm64_system_over_arm64_user_tcg"] for row in non_atomic
    ) ** (1 / len(non_atomic)),
}
combined = {
    "scope": "All modes ran inside the isolated 2-vCPU/8-GiB x86_64 test VM; ARM64 system TCG used one vCPU and 2 GiB.",
    "runs": 5,
    "checksum_consistent": True,
    "summary": summary,
    "aggregate": aggregate,
}
(ROOT / "combined-results.json").write_text(json.dumps(combined, indent=2) + "\n")

print("case,x86_vm_native_s,arm64_system_tcg_s,system/native,system/arm_user")
for row in summary:
    print(
        f'{row["case"]},{row["x86_vm_native_s"]:.6f},{row["arm64_system_tcg_s"]:.6f},'
        f'{row["arm64_system_over_x86_vm"]:.2f},{row["arm64_system_over_arm64_user_tcg"]:.2f}'
    )
print(json.dumps(aggregate, indent=2))
