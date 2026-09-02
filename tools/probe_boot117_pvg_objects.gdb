set pagination off
set confirm off
set architecture aarch64
python
import gdb
import platform
import socket
import struct
import sys
from pathlib import Path

if platform.system() != 'Linux' or socket.gethostname() != 'macvm-validation':
    raise ValueError('isolated validation VM required')
sys.path.insert(0, '/home/macvm/src/macvm')
from tools.pvg_memory import PVGMemory

gdb.execute('target remote 127.0.0.1:12353')
# RAM range verified by this run's QMP `info mtree -f` (16 GiB at 0x70000000).
# No GPU MMIO reads: interrupt status 0x1014/0x1018 is clear-on-read.
def read_ram(address, count):
    if not 0x70000000 <= address <= 0x470000000 - count:
        raise ValueError('physical read outside Boot117 RAM')
    reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:1', to_string=True)
    if 'received: "OK"' not in reply:
        raise ValueError('physical read mode refused')
    try:
        return gdb.selected_inferior().read_memory(address, count).tobytes()
    finally:
        reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:0', to_string=True)
        if 'received: "OK"' not in reply:
            raise ValueError('virtual read mode restore failed')

try:
    # Run log identifies this exact live task-4 directory. Inspect low pages
    # for candidate lists; this is evidence gathering, not a product heuristic.
    memory = PVGMemory(read_ram, 0x8ecd4, 14)
    gdb.write(f'PVG_ROOT root={memory.root:#x} depth={memory.depth}\n')
    root_words = struct.unpack('<4096I', read_ram(memory.root << 14, 16384))
    roots = [(i, p & 0x7fffffff) for i, p in enumerate(root_words) if p & 0x7fffffff]
    gdb.write(f'PVG_ROOT_ENTRIES entries={roots!r}\n')
    for index, pfn in roots[:8]:
        leaf_words = struct.unpack('<4096I', read_ram(pfn << 14, 16384))
        leaves = [(i, p & 0x7fffffff) for i, p in enumerate(leaf_words) if p & 0x7fffffff]
        gdb.write(f'PVG_LEAF_ENTRIES root_index={index} entries={leaves!r}\n')
    for address in range(0, 0x20000, 0x4000):
        try:
            raw = memory.read(address, 4096)
        except Exception as error:
            gdb.write(f'PVG_PAGE address={address:#x} error={error}\n')
            continue
        entries = []
        for ref in range(1, 181):
            tag, descriptor = struct.unpack_from('<IQ', raw, ref * 12)
            kind, length = tag & 255, tag >> 8
            if 1 <= kind <= 16 and 8 <= length <= 8192 and 0 < descriptor < (1 << 38):
                entries.append((ref, kind, length, descriptor))
        gdb.write(f'PVG_LIST_CANDIDATE address={address:#x} entries={entries!r}\n')
        if len(entries) >= 20:
            for ref, kind, length, descriptor in entries:
                if kind == 12:
                    body = memory.read(descriptor, min(length, 1024))
                    gdb.write(f'PVG_DESCRIPTOR ref={ref} type={kind} length={length} gva={descriptor:#x} bytes={body.hex()}\n')
finally:
    gdb.execute('detach')
end
quit
