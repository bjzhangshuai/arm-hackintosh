"""Read-only 16 KiB AArch64 page-table walker for validation snapshots.

Supports the 47-bit, non-LPA2 translation regime observed in Boot112.
The caller supplies physical reads; this module never writes guest memory.
"""

import struct


class TranslationError(ValueError):
    pass


class UserMemory16K:
    def __init__(self, read_physical, root, *, va_bits=47):
        if va_bits != 47 or root <= 0 or root >= (1 << 48) or root & 0x3FFF:
            raise TranslationError("unsupported address regime or unaligned root")
        self.read_physical = read_physical
        self.root = root
        self.va_bits = va_bits
        self.entries = {}

    def translate(self, address):
        if not 0 <= address < (1 << self.va_bits):
            raise TranslationError("noncanonical user address")
        table = self.root
        for level, shift in ((1, 36), (2, 25), (3, 14)):
            slot = table + ((address >> shift) & 0x7FF) * 8
            if slot not in self.entries:
                self.entries[slot] = struct.unpack("<Q", self.read_physical(slot, 8))[0]
            entry = self.entries[slot]
            kind = entry & 3
            if kind == 3 and level < 3:
                table = entry & 0x0000FFFFFFFFC000
                if not table:
                    raise TranslationError("null next-level table")
                continue
            if (level == 2 and kind == 1) or (level == 3 and kind == 3):
                mask = (1 << shift) - 1
                base = entry & 0x0000FFFFFFFFFFFF & ~mask
                return base | (address & mask)
            raise TranslationError(f"invalid descriptor level={level} entry=0x{entry:x}")
        raise TranslationError("unterminated table walk")

    def read(self, address, size):
        if not 0 <= size <= 65536 or address < 0 or address + size > (1 << self.va_bits):
            raise TranslationError("invalid bounded read")
        chunks = []
        while size:
            count = min(size, 0x4000 - (address & 0x3FFF))
            chunk = self.read_physical(self.translate(address), count)
            if len(chunk) != count:
                raise TranslationError("short physical read")
            chunks.append(chunk)
            address += count
            size -= count
        return b"".join(chunks)


def frame_chain(memory, fp, *, max_frames=24):
    """Return bounded frame records, stripping user instruction PAC bits."""
    if not 1 <= max_frames <= 64:
        raise ValueError("invalid frame bound")
    frames = []
    mask = (1 << memory.va_bits) - 1
    for _ in range(max_frames):
        if not fp or fp & 15 or fp > mask - 15:
            break
        previous, lr = struct.unpack("<QQ", memory.read(fp, 16))
        frames.append((fp, lr & mask))
        if previous <= fp or previous - fp > 1024 * 1024:
            break
        fp = previous
    return frames
