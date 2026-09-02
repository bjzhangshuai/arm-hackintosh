#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import struct
import sys


@dataclass(frozen=True)
class AddressRange:
    start: int
    end: int

    def contains(self, value: int) -> bool:
        return self.start <= value < self.end


@dataclass(frozen=True)
class Hit:
    kind: str
    va: int
    value: int
    detail: str


@dataclass(frozen=True)
class RegisterConstant:
    value: int | None
    va: int
    detail: str


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_range(value: str) -> AddressRange:
    if ":" not in value:
        raise argparse.ArgumentTypeError("range must be START:END")
    start_text, end_text = value.split(":", 1)
    start = parse_int(start_text)
    end = parse_int(end_text)
    if start >= end:
        raise argparse.ArgumentTypeError("range START must be lower than END")
    return AddressRange(start, end)


def in_any_range(value: int, ranges: list[AddressRange]) -> bool:
    return any(address_range.contains(value) for address_range in ranges)


def decode_move_wide(insn: int, previous: dict[int, int | None]) -> tuple[int, int | None, str] | None:
    if (insn & 0x1F800000) != 0x12800000:
        return None

    sf = (insn >> 31) & 1
    opc = (insn >> 29) & 0x3
    hw = (insn >> 21) & 0x3
    imm16 = (insn >> 5) & 0xFFFF
    rd = insn & 0x1F
    if rd == 31:
        return None

    width = 64 if sf else 32
    if not sf and hw >= 2:
        return None

    shift = hw * 16
    mask = (1 << width) - 1
    part_mask = (0xFFFF << shift) & mask
    part = (imm16 << shift) & mask

    if opc == 0:
        value = (~part) & mask
        mnemonic = "movn"
    elif opc == 2:
        value = part
        mnemonic = "movz"
    elif opc == 3:
        old_value = previous.get(rd)
        if old_value is None:
            value = None
        else:
            value = ((old_value & ~part_mask) | part) & mask
        mnemonic = "movk"
    else:
        return None

    register = f"{'x' if sf else 'w'}{rd}"
    detail = f"{mnemonic} {register}, #0x{imm16:x}, lsl #{shift}"
    return rd, value, detail


def scan_move_wide_constants(data: bytes, base: int, ranges: list[AddressRange]) -> list[Hit]:
    hits: list[Hit] = []
    registers: dict[int, RegisterConstant] = {}

    def flush_registers() -> None:
        for state in registers.values():
            if state.value is not None and in_any_range(state.value, ranges):
                hits.append(Hit("move-wide", state.va, state.value, state.detail))
        registers.clear()

    for offset in range(0, len(data) - len(data) % 4, 4):
        (insn,) = struct.unpack_from("<I", data, offset)
        previous_values = {
            register: state.value for register, state in registers.items()
        }
        decoded = decode_move_wide(insn, previous_values)
        va = base + offset
        if decoded is None:
            flush_registers()
            continue

        register, value, detail = decoded
        registers[register] = RegisterConstant(value, va, detail)

    flush_registers()

    return hits


def scan_raw_literals(data: bytes, base: int, ranges: list[AddressRange]) -> list[Hit]:
    hits: list[Hit] = []
    for width, fmt in ((4, "<I"), (8, "<Q")):
        for offset in range(0, len(data) - width + 1, 4):
            (value,) = struct.unpack_from(fmt, data, offset)
            if in_any_range(value, ranges):
                hits.append(Hit(f"literal-{width * 8}", base + offset, value, f"raw-width={width}"))
    return hits


def coalesce_hits(hits: list[Hit]) -> list[Hit]:
    seen: set[tuple[str, int, int, str]] = set()
    coalesced: list[Hit] = []
    for hit in sorted(hits, key=lambda item: (item.value, item.va, item.kind, item.detail)):
        key = (hit.kind, hit.va, hit.value, hit.detail)
        if key in seen:
            continue
        seen.add(key)
        coalesced.append(hit)
    return coalesced


def format_hit(hit: Hit) -> str:
    return f"{hit.kind}\tva=0x{hit.va:016x}\tvalue=0x{hit.value:016x}\t{hit.detail}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan an AArch64 binary blob for hard-coded MMIO-like constants."
    )
    parser.add_argument("binary", type=Path)
    parser.add_argument("--base", type=parse_int, default=0)
    parser.add_argument(
        "--range",
        dest="ranges",
        type=parse_range,
        action="append",
        default=[],
        help="Address range to report as START:END. May be repeated.",
    )
    parser.add_argument(
        "--raw-literals",
        action="store_true",
        help="Also scan raw aligned 32-bit and 64-bit literal values.",
    )
    args = parser.parse_args(argv)

    ranges = args.ranges or [AddressRange(0x10000000, 0x70000000)]
    data = args.binary.read_bytes()
    hits = scan_move_wide_constants(data, args.base, ranges)
    if args.raw_literals:
        hits.extend(scan_raw_literals(data, args.base, ranges))

    for hit in coalesce_hits(hits):
        print(format_hit(hit))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
