"""Bounded read-only HMP memory adapter; never reads physical device MMIO."""
import re
import struct


def decode_words(reply, address, count):
    words = []
    for line in reply.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'([0-9a-fA-F]+):((?: 0x[0-9a-fA-F]{16})+)', line.strip())
        if not match or int(match[1], 16) != address + 8 * len(words):
            raise ValueError('unexpected HMP memory response')
        words.extend(int(w, 16) for w in match[2].split())
    if len(words) != count:
        raise ValueError('short or excessive HMP memory response')
    return struct.pack('<' + 'Q' * count, *words)


class HMPMemory:
    def __init__(self, client, *, budget=2 * 1024 * 1024):
        self.client = client
        self.remaining = budget

    def read(self, address, size, *, physical=False):
        if not isinstance(size, int) or not 0 < size <= 4096:
            raise ValueError('invalid read size')
        low, high = ((0x70000000, 0x470000000) if physical else
                     (0xFFFFFE0000000000, 0xFFFFFF0000000000))
        if not low <= address < address + size <= high:
            raise ValueError('read outside allowed memory range')
        start = address & ~7
        count = (address + size - start + 7) // 8
        self.remaining -= count * 8
        if self.remaining < 0:
            raise ValueError('read budget exceeded')
        command = f'{"xp" if physical else "x"}/{count}gx 0x{start:x}'
        reply = self.client.execute('human-monitor-command', {'command-line': command})
        data = decode_words(reply, start, count)
        return data[address - start:address - start + size]

    def u64(self, address):
        return struct.unpack('<Q', self.read(address, 8))[0]

    def physical(self, address, size):
        return self.read(address, size, physical=True)
