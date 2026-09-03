"""One read-only observation of the new boot's protected tmpfs staging anchor.

Run in gdb-multiarch after the bootstrap debugger has detached. No register,
memory, filesystem metadata, signature or security policy writes are performed.
The evidence JSON is written only on the isolated Linux side.
"""
import json
import os
from pathlib import Path
import struct
import sys
import time

import gdb

sys.path.insert(0, '/home/macvm/src/macvm/tools')
from tmpfs_flags_contract import GETATTR_LOCKED, SF_RESTRICTED, verify_instructions

RUN = Path('/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot120-internal-install')
OUT = RUN / 'tmpfs-staging-anchor.json'
PID = 974460
SLIDE = 0x19344000
EXPECTED = Path('/home/macvm/src/macvm/build/qemu-boot119-graphics-storage/qemu-system-aarch64')
if (os.uname().nodename != 'macvm-validation'
        or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'
        or os.environ.get('MACVM_TMPFS_OBSERVE') != 'BOOT120_READ_ONLY'
        or Path(f'/proc/{PID}/exe').resolve(strict=True) != EXPECTED
        or OUT.exists()):
    raise RuntimeError('wrong environment, VM identity, opt-in, or existing evidence')


def reg(name):
    return int(gdb.parse_and_eval('$' + name)) & ((1 << 64) - 1)


def read(address, count):
    if not 0xfffffe0000000000 <= address < 0xffffff0000000000 or not 0 < count <= 4096:
        raise ValueError('read outside kernel data range')
    return gdb.selected_inferior().read_memory(address, count).tobytes()


def pointer(value):
    if not value:
        return 0
    bits = 64 - ((reg('TCR_EL1') >> 16) & 63)
    if not 39 <= bits <= 48:
        raise ValueError('unexpected kernel pointer width')
    mask = (1 << bits) - 1
    return (value & mask) | (((1 << 64) - 1) ^ mask)


def vnode_record(vnode):
    raw = read(vnode, 0xe8)
    nameptr, parent = struct.unpack_from('<QQ', raw, 0xb8)
    if not nameptr:
        return None
    name = read(pointer(nameptr), min(256, 0x4000 - (nameptr & 0x3fff))).split(b'\0', 1)[0].decode()
    node = pointer(struct.unpack_from('<Q', raw, 0xe0)[0])
    return name, pointer(parent), node


started = time.monotonic()
observations = 0
found = False


class Observe(gdb.Breakpoint):
    def stop(self):
        global observations, found
        observations += 1
        if observations > 50000 or time.monotonic() - started > 600:
            gdb.write('MACVM_BOOT120_ANCHOR_BUDGET_EXHAUSTED\n')
            return True
        try:
            vnode = reg('x20')
            record = vnode_record(vnode)
            if record is None or record[0] != 'com.apple.xpc.roleaccountd.staging':
                return False
            node = record[2]
            names = [record[0]]
            parent = record[1]
            for _ in range(3):
                record = vnode_record(parent)
                if record is None:
                    return False
                names.append(record[0]); parent = record[1]
            if names != ['com.apple.xpc.roleaccountd.staging', 'db', 'var', 'private']:
                return False
            kind, = struct.unpack('<I', read(node + 0x14, 4))
            flags, = struct.unpack('<I', read(node + 0x3c, 4))
            if kind != 2 or not flags & SF_RESTRICTED:
                raise ValueError('staging anchor is not an already protected tmpfs directory')
            evidence = {'boot': 120, 'qemu_pid': PID, 'slide': SLIDE,
                        'anchor_vnode': vnode, 'anchor_node': node, 'anchor_flags': flags,
                        'leaf_to_root': names, 'read_only_observation': True}
            with OUT.open('x') as output:
                json.dump(evidence, output, indent=2)
            found = True
            gdb.write('MACVM_BOOT120_ANCHOR_VERIFIED ' + json.dumps(evidence) + '\n')
            return True
        except (gdb.MemoryError, UnicodeDecodeError):
            return False
        except Exception as error:
            gdb.write(f'MACVM_BOOT120_ANCHOR_ERROR {error!r}\n')
            return True


bp = None
try:
    gdb.execute('set pagination off')
    gdb.execute('set confirm off')
    gdb.execute('set architecture aarch64')
    gdb.execute('set print thread-events off')
    gdb.execute('set remotetimeout 30')
    gdb.execute('target remote 127.0.0.1:12355')
    verify_instructions(lambda a: struct.unpack('<I', read(a, 4))[0], SLIDE)
    bp = Observe(f'*{GETATTR_LOCKED + SLIDE:#x}', gdb.BP_HARDWARE_BREAKPOINT, internal=True)
    gdb.write('MACVM_BOOT120_ANCHOR_OBSERVER_ARMED read_only=1\n')
    gdb.execute('continue')
finally:
    if bp is not None and bp.is_valid():
        bp.delete()
    if gdb.selected_inferior().pid:
        gdb.execute('detach')
    gdb.write(f'MACVM_BOOT120_ANCHOR_OBSERVER_DETACHED found={found} observations={observations}\n')
