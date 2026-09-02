set pagination off
set confirm off
set architecture aarch64
set print thread-events off
python
import gdb
import struct
import sys

sys.path.insert(0, '/home/macvm/src/macvm/tools')
sys.path.insert(0, '/home/macvm/src/macvm')
from symlink_trace_contract import verify_instructions
from arm64_user_memory import UserMemory16K
from tools.user_crash_capture import capture

SLIDE = 0x19344000
DYLD_SLIDE = 0x4d88000
gdb.execute('target remote 127.0.0.1:12352')

def read(address, count):
    return gdb.selected_inferior().read_memory(address & ((1 << 64) - 1), count).tobytes()

def u64(address):
    return struct.unpack('<Q', read(address, 8))[0]

def strip_kernel(value):
    bits = 64 - ((int(gdb.parse_and_eval('$TCR_EL1')) >> 16) & 63)
    if not 39 <= bits <= 48:
        raise ValueError('unexpected kernel translation width')
    mask = (1 << bits) - 1
    return (value & mask) | ((1 << 64) - 1 ^ mask)

verify_instructions(lambda a: struct.unpack('<I', read(a, 4))[0], SLIDE)
# Exact BootKC current_proc() -> current_thread_ro() instruction contracts.
for address, instruction in ((0xfffffe0009cf0b38, 0xd538d080),
                             (0xfffffe0009cf0b3c, 0xf941f401),
                             (0xfffffe000a35a220, 0xf9400c00)):
    if struct.unpack('<I', read(address + SLIDE, 4))[0] != instruction:
        raise ValueError('current_proc instruction mismatch')

def read_physical(address, length):
    reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:1', to_string=True)
    if 'received: "OK"' not in reply:
        raise ValueError('physical read mode refused')
    try:
        return read(address, length)
    finally:
        reply = gdb.execute('maintenance packet Qqemu.PhyMemMode:0', to_string=True)
        if 'received: "OK"' not in reply:
            raise ValueError('virtual read mode restore failed')

class CrashProbe(gdb.Breakpoint):
    def __init__(self, label, address):
        super().__init__(f'*0x{address + DYLD_SLIDE:x}', gdb.BP_HARDWARE_BREAKPOINT)
        self.label = label
        self.silent = True

    def stop(self):
        try:
            thread = int(gdb.parse_and_eval('$TPIDR_EL1'))
            tro = strip_kernel(u64(thread + 0x3e8))
            proc = strip_kernel(u64(tro + 0x18))
            name = read(proc + 0x5cc, 17).split(b'\0', 1)[0].decode(errors='replace')
            if name != 'mobileactivation':
                return False
            pid = struct.unpack('<I', read(proc + 0x60, 4))[0]
            gdb.write(f'MACVM_USER_CRASH label={self.label} pid={pid} proc=0x{proc:x} name={name}\n')
            gdb.execute('info registers pc sp x0 x1 x2 x3 x4 x5 x6 x7 x16 x19 x20 x21 x29 x30')
            # The debugger's selected CPU cannot reliably translate another
            # process's userspace. Walk this exact proc's pmap, as in the
            # already-validated allproc stack probe; never change CPU/MMU state.
            proc_size = u64(0xfffffe000a8e5b30 + SLIDE)
            if not 0x400 <= proc_size <= 0x2000:
                raise ValueError('unexpected proc size')
            task = proc + proc_size
            vm_map = strip_kernel(u64(task + 0x28))
            pmap = strip_kernel(u64(vm_map + 0x58))
            root = u64(pmap + 8)
            tcr = int(gdb.parse_and_eval('$TCR_EL1'))
            if (tcr >> 14) & 3 != 2 or 64 - (tcr & 63) != 47:
                raise ValueError('unsupported user translation regime')
            gdb.write(f'MACVM_CRASH_PMAP root=0x{root:x} task=0x{task:x}\n')
            registers = {r: int(gdb.parse_and_eval('$' + r)) for r in ('x0', 'x1', 'x4', 'x5', 'x29')}
            evidence = capture(UserMemory16K(read_physical, root), registers)
            for register, raw in evidence['strings'].items():
                gdb.write(f'MACVM_CRASH_ARGUMENT register={register} bytes={raw!r}\n')
            gdb.write(f'MACVM_USER_STACK pid={pid} tid=0 frames=' + repr([(hex(a), hex(b)) for a,b in evidence['frames']]) + '\n')
            for field, error in evidence['errors'].items():
                gdb.write(f'MACVM_CRASH_FIELD_ERROR field={field} error={error}\n')
            return True
        except Exception as error:
            gdb.write(f'MACVM_CRASH_PROBE_ERROR {error}\n')
            return True

probes = [CrashProbe('_os_crash', 0x180398628),
          CrashProbe('__abort_with_payload', 0x18045cb08),
          CrashProbe('_dispatch_assert_queue_fail', 0x18030d484),
          CrashProbe('__assert_rtn', 0x180398ab8)]
gdb.write('MACVM_USER_CRASH_WATCH_ARMED observe_only=1 process=mobileactivation\n')
end
continue
delete breakpoints
detach
quit
