"""One live, read-only task snapshot without disturbing the armed GDB guard.

The exact 25G72 proc/task/thread offsets were established in
probe_allproc_names_live.gdb from this BootKC. Live lists may change during this
observation; reject broken back-links/task associations rather than retrying or
treating the output as an atomic snapshot. No guest code is executed.
"""
import datetime
import os
from pathlib import Path
import struct

from tools.arm64_user_memory import UserMemory16K, frame_chain
from tools.qmp_hmp_memory import HMPMemory
from tools.qmp_screendump import QMPClient
from tools.updatebrain_null_cleanup import CF_BASE, CF_UUID, verify_uuid

RUN = Path('/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot120-internal-install')
SLIDE = 0x19344000
MASK = (1 << 47) - 1


def canonical(value):
    if not value:
        raise ValueError('null kernel pointer')
    value = value & MASK | (((1 << 64) - 1) ^ MASK)
    if not 0xFFFFFE0000000000 <= value < 0xFFFFFF0000000000:
        raise ValueError('invalid kernel pointer')
    return value


def validate_wanted_pids(wanted_pids):
    if wanted_pids is not None and (
            not isinstance(wanted_pids, frozenset) or not 1 <= len(wanted_pids) <= 8
            or any(type(p) is not int or not 1 <= p <= 999999 for p in wanted_pids)):
        raise ValueError('optional target set must contain 1-8 exact positive PIDs')
    return wanted_pids


def main(*, wanted_pids=None):
    validate_wanted_pids(wanted_pids)
    if (os.uname().nodename != 'macvm-validation'
            or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'
            or Path('/proc/974460/exe').resolve() != Path('/home/macvm/src/macvm/build/qemu-boot119-graphics-storage/qemu-system-aarch64')
            or str(RUN / 'qmp.sock').encode() not in Path('/proc/974460/cmdline').read_bytes()):
        raise ValueError('not the exact isolated Boot120 VM')
    print('MACVM_QMP_TASK_SNAPSHOT_BEGIN', datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)
    with QMPClient(RUN / 'qmp.sock', 30) as client:
        if client.execute('query-status')['status'] != 'running':
            raise ValueError('guest not running; never resume it here')
        m = HMPMemory(client)
        for address, word in ((0xFFFFFE0009CF0B38, 0xD538D080),
                              (0xFFFFFE0009CF0B3C, 0xF941F401),
                              (0xFFFFFE000A35A220, 0xF9400C00)):
            if m.read(address + SLIDE, 4) != struct.pack('<I', word):
                raise ValueError('BootKC instruction mismatch')
        proc_size = m.u64(0xFFFFFE000A8E5B30 + SLIDE)
        if not 0x400 <= proc_size <= 0x2000:
            raise ValueError('invalid proc size')
        proc = canonical(m.u64(0xFFFFFE0007916C28 + SLIDE))
        seen = set()
        for _ in range(512):
            if proc in seen:
                break
            seen.add(proc)
            pid = struct.unpack('<I', m.read(proc + 0x60, 4))[0]
            if pid > 999999:
                break  # The allproc list head is not another struct proc.
            name = m.read(proc + 0x5CC, 17).split(b'\0', 1)[0].decode(errors='replace')
            selected = (pid in wanted_pids if wanted_pids is not None else name in {
                'Terminal', 'WindowServer', 'InstallAssistant', 'osinstallersetup', 'com.apple.Mobile'})
            if selected:
                task = proc + proc_size
                vm_map = canonical(m.u64(task + 0x28))
                pmap = canonical(m.u64(vm_map + 0x58))
                user = UserMemory16K(m.physical, m.u64(pmap + 8))
                verify_uuid(user.read, CF_BASE, CF_UUID)
                print(f'MACVM_TASK_MAP pid={pid} name={name!r} proc={proc:#x} task={task:#x}', flush=True)
                head = task + 0x50
                thread = m.u64(head)
                threads = set()
                for _ in range(16):
                    if thread == head or thread in threads:
                        break
                    thread = canonical(thread)
                    threads.add(thread)
                    tro = canonical(m.u64(thread + 0x3E8))
                    if canonical(m.u64(tro + 0x28)) != task:
                        raise ValueError('live thread/task association changed')
                    tid = m.u64(thread + 0x4E0)
                    state = m.u64(thread + 0x100)
                    if state:
                        state = canonical(state)
                        fp, lr, sp, pc = struct.unpack('<QQQQ', m.read(state + 0xF0, 32))
                        print(f'MACVM_THREAD_STATE pid={pid} tid={tid} pc={pc & MASK:#x} lr={lr & MASK:#x} sp={sp:#x}', flush=True)
                        try:
                            frames = [(hex(a), hex(b)) for a, b in frame_chain(user, fp, max_frames=24)]
                            print(f'MACVM_USER_STACK pid={pid} tid={tid} frames={frames!r}', flush=True)
                        except ValueError as error:
                            print(f'MACVM_USER_STACK_UNREADABLE pid={pid} tid={tid} error={error}', flush=True)
                    thread = m.u64(thread + 0x3D8)
            previous = m.u64(proc + 8)
            if not previous:
                break
            previous = canonical(previous)
            if m.u64(previous) != proc:
                break
            proc = previous
        print('MACVM_QMP_TASK_SNAPSHOT_END', client.execute('query-status'), 'remaining', m.remaining, flush=True)


if __name__ == '__main__':
    main()
