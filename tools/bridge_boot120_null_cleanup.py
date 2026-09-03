"""One-shot B012 NULL-cleanup bridge, inside the already-running test VM only.

No disk/code/security-policy writes. After exact identity/frame/code checks,
the only permitted guest write is PC to CFRelease's authenticated epilogue.
Set MACVM_NULL_CLEANUP_MODE=verify for a read-only live contract check instead.
Run under a bounded SIGINT timeout, with QMP status checked before and afterward.
"""
import hashlib
import os
from pathlib import Path
import struct
import sys

import gdb

sys.path.insert(0, '/home/macvm/src/macvm/tools')
from arm64_user_memory import UserMemory16K
from updatebrain_null_cleanup import (
    CF_BASE, CF_NULL, CF_UUID, CF_WORDS, CALLER_RETURN, MASK47, PROCESS,
    UB_UUID, UB_WORDS, plan_cleanup, verify_uuid, verify_words,
)

RUN = Path('/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot120-internal-install')
EXE = Path('/home/macvm/src/macvm/build/qemu-boot119-graphics-storage/qemu-system-aarch64')
REF = Path('/home/macvm/installation-data/install-analysis/updatebrain-25G83/UpdateBrainLibrary.dylib.arm64e')
PID = 974460
SLIDE = 0x19344000
MODE = os.environ.get('MACVM_NULL_CLEANUP_MODE')
if (os.uname().nodename != 'macvm-validation'
        or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'
        or os.environ.get('MACVM_NULL_CLEANUP_CONFIRMED') != 'BOOT120_NULL_CLEANUP_25G83'
        or MODE not in ('verify', 'repair-once')
        or Path(f'/proc/{PID}/exe').resolve(strict=True) != EXE
        or str(RUN / 'qmp.sock').encode() not in Path(f'/proc/{PID}/cmdline').read_bytes()):
    raise RuntimeError('wrong VM identity, mode or opt-in')
reference = REF.read_bytes()
if hashlib.sha256(reference).hexdigest() != '0d680541b7c6f2e6911cdf2a83e4144892cf3c0ad10325b041c3b6b7a254475b':
    raise RuntimeError('wrong private reference image')
# The __TEXT VM address and file offset are both zero in this checked image.
verify_uuid(lambda a, n: reference[a:a+n], 0, UB_UUID)
verify_words(lambda a, n: reference[a:a+n], 0, UB_WORDS)


def reg(name):
    return int(gdb.parse_and_eval('$' + name)) & ((1 << 64) - 1)


def raw(address, size):
    return gdb.selected_inferior().read_memory(address, size).tobytes()


def kernel(address, size):
    if not 0xFFFFFE0000000000 <= address < 0xFFFFFF0000000000 or not 0 < size <= 4096:
        raise ValueError('invalid kernel read')
    return raw(address, size)


def u64(address):
    return struct.unpack('<Q', kernel(address, 8))[0]


def canonical(value):
    bits = 64 - ((reg('TCR_EL1') >> 16) & 63)
    if bits != 47 or not value:
        raise ValueError('unexpected kernel address regime')
    result = value & MASK47 | ((1 << 64) - 1 ^ MASK47)
    if not 0xFFFFFE0000000000 <= result < 0xFFFFFF0000000000:
        raise ValueError('invalid kernel pointer')
    return result


def physical(address, size):
    if not 0x70000000 <= address or address + size > 0x480000000:
        raise ValueError('physical read outside RAM; never inspect device MMIO')
    reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:1', to_string=True)
    if 'received: "OK"' not in reply:
        raise ValueError('physical mode refused')
    try:
        return raw(address, size)
    finally:
        reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:0', to_string=True)
        if 'received: "OK"' not in reply:
            raise ValueError('virtual mode restore failed')


def memory(proc):
    size = u64(0xFFFFFE000A8E5B30 + SLIDE)
    if not 0x400 <= size <= 0x2000:
        raise ValueError('wrong proc layout')
    vm_map = canonical(u64(proc + size + 0x28))
    pmap = canonical(u64(vm_map + 0x58))
    tcr = reg('TCR_EL1')
    if (tcr >> 14) & 3 != 2 or 64 - (tcr & 63) != 47:
        raise ValueError('wrong user address regime')
    return UserMemory16K(physical, u64(pmap + 8))


def find_terminal():
    proc = canonical(u64(0xFFFFFE0007916C28 + SLIDE))
    seen = set()
    for _ in range(512):
        if proc in seen: break
        seen.add(proc)
        pid = struct.unpack('<I', kernel(proc + 0x60, 4))[0]
        name = kernel(proc + 0x5CC, 17).split(b'\0', 1)[0]
        if pid == 339 and name == b'Terminal': return proc
        prev = canonical(u64(proc + 8))
        if u64(prev) != proc: break
        proc = prev
    raise ValueError('known Recovery Terminal identity absent')


repaired = False
bp = None


class NullCleanup(gdb.Breakpoint):
    def stop(self):
        global repaired
        try:
            # EL0 only. The stub's breakpoint is virtual-address based, so
            # identify the current task before looking at any userspace data.
            if reg('cpsr') & 15:
                return False
            thread = canonical(reg('TPIDR_EL1'))
            proc = canonical(u64(canonical(u64(thread + 0x3E8)) + 0x18))
            name = kernel(proc + 0x5DD, 64).split(b'\0', 1)[0].decode('ascii')
            if name != PROCESS:
                return False
            pid = struct.unpack('<I', kernel(proc + 0x60, 4))[0]
            mem = memory(proc)
            registers = {n: reg(n) for n in ('pc', 'x0', 'sp', 'x29', 'x30')}
            destination = plan_cleanup(mem.read, process=name,
                                       pc=registers['pc'], x0=registers['x0'],
                                       sp=registers['sp'], fp=registers['x29'],
                                       lr=registers['x30'])
            if destination is None:
                return False
            base = (registers['x30'] & MASK47) - CALLER_RETURN
            if mem.read(base + 0x5130C, 0x204) != reference[0x5130C:0x51510]:
                raise ValueError('complete caller-function bytes mismatch')
            if repaired:
                raise ValueError('one-shot repair already consumed')
            gdb.write(f'MACVM_B012_EXACT_NULL_CONFIRMED pid={pid} proc={proc:#x} image={base:#x} registers={registers!r}\n')
            gdb.execute(f'set $pc = {destination:#x}')
            if reg('pc') != destination:
                raise ValueError('PC readback mismatch')
            for name, value in registers.items():
                if name != 'pc' and reg(name) != value:
                    raise ValueError(f'unexpected register change: {name}')
            repaired = True
            gdb.write('MACVM_B012_NULL_CLEANUP_REPAIRED_ONCE disk_text_writes=0 signature_changes=0 authenticated_return_preserved=1\n')
            return True
        except Exception as error:
            gdb.write(f'MACVM_B012_BRIDGE_REFUSED {error!r}\n')
            return True


def attach_and_verify():
    for command in ('set pagination off', 'set confirm off', 'set architecture aarch64',
                    'set print thread-events off', 'set remotetimeout 30'):
        gdb.execute(command)
    gdb.execute('target remote 127.0.0.1:12355')
    for address, word in ((0xFFFFFE0009CF0B38, 0xD538D080),
                          (0xFFFFFE0009CF0B3C, 0xF941F401),
                          (0xFFFFFE000A35A220, 0xF9400C00)):
        if kernel(address + SLIDE, 4) != struct.pack('<I', word):
            raise ValueError('current_proc instruction contract mismatch')
    mem = memory(find_terminal())
    verify_uuid(mem.read, CF_BASE, CF_UUID)
    verify_words(mem.read, CF_BASE, CF_WORDS)
    gdb.write(f'MACVM_B012_LIVE_CF_CONTRACT_VERIFIED mode={MODE}\n')


def run():
    global bp
    try:
        attach_and_verify()
        if MODE == 'repair-once':
            bp = NullCleanup(f'*{CF_NULL:#x}', gdb.BP_HARDWARE_BREAKPOINT, internal=True)
            bp.silent = True
            gdb.write('MACVM_B012_NULL_CLEANUP_ARMED max_repairs=1\n')
            gdb.execute('continue')
    finally:
        if bp is not None and bp.is_valid(): bp.delete()
        if gdb.selected_inferior().pid: gdb.execute('detach')
        gdb.write(f'MACVM_B012_BRIDGE_DETACHED repaired={repaired}\n')


if __name__ == '__main__':
    run()
