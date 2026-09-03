"""Read-only, exact-image Boot119 role-account staging evidence.

Run with gdb-multiarch inside guarded isolated Linux. Breakpoints never change
registers, instructions or metadata; stop at the first error reply and detach.
"""
import hashlib
import os
import struct
import sys
import time

import gdb

sys.path.insert(0, '/home/macvm/src/macvm/tools')
from arm64_user_memory import UserMemory16K

if os.environ.get('MACVM_ROLE_TRACE_CONFIRMED') != 'BOOT119_READ_ONLY':
    raise RuntimeError('explicit isolated Boot119 trace opt-in required')
BASE = 0x102D60000  # observed by Recovery sample, UUID verified below
PROC = 0xFFFFFE240B971588
PID = 5583
SLIDE = 0x19344000
IMAGE = '/home/macvm/analysis/basesystem-ro-inspect/root/usr/libexec/xpcroleaccountd'
with open(IMAGE, 'rb') as source:
    if hashlib.sha256(source.read()).hexdigest() != 'b25d5bd50c97efb7cf43643b91802fae701846bcd8e53eeae63666633eb87155':
        raise RuntimeError('wrong reference image')
SITES = {
    0x1934: ('staging-enter', 0xF0000000),
    0x1DDC: ('existing-cache-stat', 0x340000E0),
    0x21C0: ('copyfile-return', 0xAA0003F6),
    0x2B90: ('static-code-path', 0xAA0003F3),
    0x2BB0: ('static-code-url', 0xB4000280),
    0x2BC4: ('static-code-create-return', 0xAA0003F4),
    0x2A64: ('copy-callback', 0x7100083F),
    0x2AAC: ('copy-chown-return', 0x340001A0),
    0x2D04: ('signature-requirement-return', 0xAA0003F4),
    0x2288: ('signing-info-return', 0xAA0003F8),
    0x22E4: ('signed-info-plist-result', 0xB40007F8),
    0x2308: ('role-info-result', 0x36000716),
    0x1CF0: ('trusted-info-conversion-failed', 0x528009E8),
    0x1B98: ('error-reply', 0xB9800002),
}
breakpoints = []
started = time.monotonic()
hits = 0


def read(address, count):
    # GDB may expose high AArch64 registers as signed integers.
    address &= 0xFFFFFFFFFFFFFFFF
    return gdb.selected_inferior().read_memory(address, count).tobytes()


def u64(address):
    return struct.unpack('<Q', read(address, 8))[0]


def canonical(raw):
    bits = 64 - ((int(gdb.parse_and_eval('$TCR_EL1')) >> 16) & 63)
    if not 39 <= bits <= 48:
        raise ValueError('unexpected kernel translation width')
    mask = (1 << bits) - 1
    value = raw & mask | (0xFFFFFFFFFFFFFFFF ^ mask)
    if not 0xFFFFFE0000000000 <= value < 0xFFFFFF0000000000:
        raise ValueError('invalid kernel pointer')
    return value


def physical(address, count):
    # Page-table/data reads only; never read a device/MMIO address.
    if not 0x70000000 <= address or address + count > 0x480000000:
        raise ValueError('physical read outside Boot119 RAM bound')
    reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:1', to_string=True)
    if 'received: "OK"' not in reply:
        raise RuntimeError('physical read mode refused')
    try:
        return read(address, count)
    finally:
        reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:0', to_string=True)
        if 'received: "OK"' not in reply:
            raise RuntimeError('virtual read mode restore failed')


def memory():
    if struct.unpack('<I', read(PROC + 0x60, 4))[0] != PID:
        raise ValueError('process identity changed')
    if read(PROC + 0x5CC, 17).split(b'\0', 1)[0] != b'xpcroleaccountd':
        raise ValueError('process name mismatch')
    size = u64(0xFFFFFE000A8E5B30 + SLIDE)
    if not 0x400 <= size <= 0x2000:
        raise ValueError('unexpected process size')
    task_map = canonical(u64(PROC + size + 0x28))
    pmap = canonical(u64(task_map + 0x58))
    return UserMemory16K(physical, u64(pmap + 8))


class Observe(gdb.Breakpoint):
    def __init__(self, offset, label):
        super().__init__(f'*{BASE + offset:#x}', gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        self.label = label

    def stop(self):
        global hits
        try:
            thread = int(gdb.parse_and_eval('$TPIDR_EL1'))
            current = canonical(u64(canonical(u64(thread + 0x3E8)) + 0x18))
            if current != PROC:
                return False
            if time.monotonic() - started > 1200:
                gdb.write('MACVM_ROLE_TRACE_LIMIT\n')
                return True
            # Ignore normal copy callback/progress traffic before expensive
            # user-page reads and before counting meaningful observations.
            value0 = int(gdb.parse_and_eval('$x0')) & 0xFFFFFFFFFFFFFFFF
            value1 = int(gdb.parse_and_eval('$x1')) & 0xFFFFFFFFFFFFFFFF
            if self.label == 'copy-chown-return' and value0 == 0:
                return False
            if self.label == 'copy-callback' and value1 != 3:
                return False
            hits += 1
            if hits > 200:
                gdb.write('MACVM_ROLE_TRACE_LIMIT\n')
                return True
            mem = memory()
            regs = {r: int(gdb.parse_and_eval('$' + r)) & 0xFFFFFFFFFFFFFFFF
                    for r in ('pc', 'sp', 'x0', 'x1', 'x2', 'x3', 'x4', 'x19', 'x20', 'x21', 'x22', 'x23', 'x24', 'x26', 'x28')}
            gdb.write(f'MACVM_ROLE_STAGE label={self.label} regs={regs!r}\n')
            if self.label == 'copy-callback':
                for field in ('x3', 'x4'):
                    pointer = regs[field]
                    if 0 < pointer < 2**47:
                        value = mem.read(pointer, min(1024, 0x4000 - (pointer & 0x3FFF))).split(bytes([0]), 1)[0]
                        gdb.write(f'MACVM_ROLE_COPY_ERROR_PATH {field}={value!r}\n')
            if self.label == 'static-code-path':
                pointer = regs['x0']
                if 0 < pointer < 2**47:
                    text = mem.read(pointer, min(1024, 0x4000 - (pointer & 0x3FFF))).split(bytes([0]), 1)[0]
                    gdb.write(f'MACVM_ROLE_STATIC_CODE_PATH {text!r}\n')
            if self.label == 'staging-enter':
                for field in ('x26', 'x28'):
                    pointer = regs[field]
                    if 0 < pointer < 2**47:
                        text = mem.read(pointer, min(1024, 0x4000 - (pointer & 0x3FFF))).split(bytes([0]), 1)[0]
                        gdb.write(f'MACVM_ROLE_SOURCE {field}={text!r}\n')
            if self.label == 'existing-cache-stat':
                gdb.write(f'MACVM_ROLE_CACHE_PATH {mem.read(regs["sp"] + 0xE0, 1024).split(bytes([0]), 1)[0]!r}\n')
            if self.label == 'copy-chown-return':
                pointer = regs['x19']
                gdb.write(f'MACVM_ROLE_COPY_PATH {mem.read(pointer, min(1024, 0x4000 - (pointer & 0x3FFF))).split(bytes([0]), 1)[0]!r}\n')
            if self.label == 'error-reply':
                error = struct.unpack('<I', mem.read(regs['x0'], 4))[0]
                gdb.write(f'MACVM_ROLE_ERROR_REPLY errno={error}\n')
                return True
            return False
        except Exception as error:
            gdb.write(f'MACVM_ROLE_TRACE_ERROR {error!r}\n')
            return True


try:
    gdb.execute('set pagination off')
    gdb.execute('set confirm off')
    gdb.execute('set architecture aarch64')
    gdb.execute('set print thread-events off')
    gdb.execute('target remote 127.0.0.1:12355')
    mem = memory()
    header = mem.read(BASE, 0x800)
    if header[:4] != bytes.fromhex('cffaedfe') or bytes.fromhex('863a20ec173932379d85e5bd71a4c904') not in header:
        raise ValueError('live Mach-O header/UUID mismatch')
    for offset, (label, word) in SITES.items():
        if struct.unpack('<I', mem.read(BASE + offset, 4))[0] != word:
            raise ValueError(f'live instruction mismatch at {offset:#x}')
        breakpoints.append(Observe(offset, label))
    gdb.write('MACVM_ROLE_TRACE_ARMED pid=5583 read_only=1\n')
    gdb.execute('continue')
finally:
    for bp in breakpoints:
        if bp.is_valid():
            bp.delete()
    if gdb.selected_inferior().pid:
        gdb.execute('detach')
    gdb.write(f'MACVM_ROLE_TRACE_DETACHED hits={hits}\n')
