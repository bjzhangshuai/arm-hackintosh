"""Read-only batch stack symbolization from ipsw's A2S v2 index.

Format reference: https://github.com/blacktop/ipsw/blob/master/pkg/dyld/a2s.go
This reports nearest symbols, not inferred function boundaries. Verify ambiguous
matches against disassembly. The cache must belong to the exact guest build.
"""
import argparse
import mmap
import re
import struct
from pathlib import Path


class A2S:
    def __init__(self, data):
        self.data = data
        if len(data) < 12 or data[:4] != b'A2S\x02':
            raise ValueError('not an A2S v2 index')
        self.count, self.strings_size = struct.unpack_from('<II', data, 4)
        self.strings = 12 + self.count * 12
        if self.strings + self.strings_size != len(data):
            raise ValueError('A2S index extent mismatch')

    def address(self, index):
        return struct.unpack_from('<Q', self.data, 12 + index * 12)[0]

    def nearest(self, address, max_distance=0x10000):
        if address < 0 or max_distance < 0:
            raise ValueError('invalid lookup bound')
        lo, hi = 0, self.count
        while lo < hi:
            middle = (lo + hi) // 2
            if self.address(middle) <= address:
                lo = middle + 1
            else:
                hi = middle
        if not lo:
            return None
        index = lo - 1
        start = self.address(index)
        if address - start > max_distance:
            return None
        offset = struct.unpack_from('<I', self.data, 12 + index * 12 + 8)[0]
        if offset >= self.strings_size:
            raise ValueError('symbol string outside table')
        begin = self.strings + offset
        end = self.data.find(b'\0', begin, min(begin + 16384, len(self.data)))
        if end < 0:
            raise ValueError('unterminated or oversized symbol')
        return start, self.data[begin:end].decode('utf-8'), address - start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('log', type=Path)
    parser.add_argument('--slide', required=True, type=lambda s: int(s, 0))
    parser.add_argument('--pid', type=int, action='append', default=[])
    args = parser.parse_args()
    with args.cache.open('rb') as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
        table = A2S(data)
        for line in args.log.read_text().splitlines():
            match = re.match(r'MACVM_USER_STACK pid=(\d+) tid=(\d+) frames=', line)
            if not match or (args.pid and int(match[1]) not in args.pid):
                continue
            print(f'pid={match[1]} tid={match[2]}')
            for frame, lr in re.findall(r"\('(0x[0-9a-f]+)', '(0x[0-9a-f]+)'\)", line):
                address = int(lr, 0) - args.slide
                symbol = table.nearest(address) if 0x180000000 <= address < 0x300000000 else None
                print(f'  {lr}  ' + (f'nearest {symbol[1]} + {symbol[2]} [0x{symbol[0]:x}]' if symbol else 'unmapped/main image'))


if __name__ == '__main__':
    main()
