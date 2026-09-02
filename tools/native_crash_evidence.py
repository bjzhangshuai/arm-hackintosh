"""Bounded executable-memory windows for a stopped validation QEMU.

This module is imported by GDB, not run against the production host. The pure
mapping parser also lets tests prove that non-executable/unmapped PCs are not
dumped. Dumps are private run artifacts, never repository fixtures.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def executable_window(maps: str, pc: int, limit: int = 65536) -> tuple[int, int] | None:
    if not 0 < pc < (1 << 64) or limit <= 0 or limit > 65536:
        return None
    matches = []
    for line in maps.splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        try:
            lo, hi = (int(s, 16) for s in fields[0].split("-"))
        except ValueError:
            continue
        if not 0 <= lo < hi <= (1 << 64) or not lo <= pc < hi:
            continue
        if len(fields[1]) != 4 or fields[1][0] != "r" or fields[1][2] != "x":
            return None
        start = max(lo, pc - limit // 2)
        end = min(hi, start + limit)
        matches.append((start, end))
    return matches[0] if len(matches) == 1 else None


def capture_stopped(gdb, output: Path) -> None:
    inferior = gdb.selected_inferior()
    pid = int(inferior.pid)
    maps = Path(f"/proc/{pid}/maps").read_text()
    output.mkdir(mode=0o700, exist_ok=False)

    def save(name: str, data: bytes) -> None:
        path = output / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        gdb.write(f"NATIVE_EVIDENCE path={path} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}\n")

    save("maps.txt", maps.encode())
    for command in ("info registers", "thread apply all bt 24", "info sharedlibrary", "x/48gx $rsp"):
        try:
            gdb.write(gdb.execute(command, to_string=True))
        except gdb.error as exc:
            gdb.write(f"NATIVE_EVIDENCE command={command!r} error={exc}\n")
    frame = gdb.newest_frame()
    windows = set()
    # The null RIP itself has no map. Its caller's executable window retains
    # the JIT call site that an ordinary backtrace loses on process exit.
    for _ in range(16):
        if frame is None:
            break
        try:
            window = executable_window(maps, int(frame.pc()))
            if window is not None and window not in windows:
                windows.add(window)
                lo, hi = window
                save(f"exec-{lo:x}-{hi:x}.bin", bytes(inferior.read_memory(lo, hi - lo)))
            frame = frame.older()
        except gdb.error as exc:
            gdb.write(f"NATIVE_EVIDENCE unwind_or_read_error={exc}\n")
            break
