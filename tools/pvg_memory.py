"""Bounded, read-only PVG task-GVA walker for evidence capture.

The 4-byte PFN entries and explicit page geometry mirror reims-vgpu-wire's
page_table.rs. These are GPU page tables, not the CPU's ARM page tables.
The caller must supply a RAM-only physical reader; this module has no write API.
"""

import struct


class PVGMemory:
    def __init__(self, read_physical, directory_pfn, page_shift):
        if page_shift not in (12, 14) or not 0 < directory_pfn < 0x80000000:
            raise ValueError("invalid PVG directory/geometry")
        self.read_physical = read_physical
        self.page_shift = page_shift
        self.root, self.depth = struct.unpack(
            "<II", self._physical(directory_pfn << page_shift, 8)
        )
        if not 0 < self.root < 0x80000000 or not 1 <= self.depth <= 4:
            raise ValueError("invalid PVG root/depth")

    def _physical(self, address, size):
        data = self.read_physical(address, size)
        if len(data) != size:
            raise ValueError("short PVG physical read")
        return data

    def translate(self, address):
        bits = self.page_shift - 2
        if not 0 <= address < min(1 << 64, 1 << (self.page_shift + bits * self.depth)):
            raise ValueError("PVG address out of range")
        page = address >> self.page_shift
        pfn = self.root
        for level in range(self.depth):
            index = (page >> ((self.depth - level - 1) * bits)) & ((1 << bits) - 1)
            raw, = struct.unpack("<I", self._physical((pfn << self.page_shift) + 4 * index, 4))
            pfn = raw & 0x7fffffff
            if not pfn:
                raise ValueError("PVG page absent" if raw == 0 else "PVG malformed PTE")
        return (pfn << self.page_shift) | (address & ((1 << self.page_shift) - 1))

    def read(self, address, count):
        if not 0 <= count <= 65536:
            raise ValueError("PVG capture length exceeds bound")
        self.translate(address)
        if count:
            self.translate(address + count - 1)
        output = bytearray()
        while len(output) < count:
            cursor = address + len(output)
            size = min(count - len(output), (1 << self.page_shift) - (cursor & ((1 << self.page_shift) - 1)))
            output.extend(self._physical(self.translate(cursor), size))
        return bytes(output)
