"""Bounded read-only tmpfs query observer; never installs a metadata mutator.

Run only with no other guest debugger attached. Observe the already verified
anchor and protected descendants during one manually requested guest lookup.
"""
import os
import struct
import sys
import time

import gdb

sys.path.insert(0, '/home/macvm/src/macvm/tools')
if (os.uname().nodename != 'macvm-validation'
        or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'
        or os.environ.get('MACVM_TMPFS_QUERY_OBSERVE') != 'BOOT120_READ_ONLY'
        or os.environ.get('MACVM_TMPFS_COMPAT_CONFIRMED') != 'BOOT120_VERIFIED'):
    raise RuntimeError('exact isolated read-only opt-ins required')

import compat_tmpfs_flags_live as metadata
from tmpfs_flags_contract import GETATTR_LOCKED, VA_EXTFLAGS_ACTIVE, verify_instructions

started = time.monotonic()
seen = set()
observations = 0
scoped = 0
bp = None


class Observe(gdb.Breakpoint):
    def stop(self):
        global observations, scoped
        observations += 1
        if observations > 20000 or time.monotonic() - started > 180:
            gdb.write(f'MACVM_B014_QUERY_LIMIT observations={observations} scoped={scoped}\n')
            return True
        try:
            vnode, node, attrs = (metadata.reg(r) for r in ('x20', 'x19', 'x22'))
            if not node or metadata.u64(vnode + 0xE0) != node:
                return False
            context = metadata.lineage(vnode)
            if context is None:
                return False
            scoped += 1
            relative = context[0]
            supported, requested = metadata.u64(attrs), metadata.u64(attrs + 8)
            thread = metadata.reg('TPIDR_EL1')
            proc = metadata.pointer(metadata.u64(metadata.pointer(metadata.u64(thread + 0x3E8)) + 0x18))
            name = metadata.read(proc + 0x5CC, 17).split(b'\0', 1)[0]
            pid = metadata.u32(proc + 0x60)
            record = (relative, name, pid, supported, requested)
            if record not in seen:
                seen.add(record)
                gdb.write(f'MACVM_B014_QUERY path={relative!r} process={name!r} pid={pid} '
                          f'vnode={vnode:#x} node={node:#x} flags={metadata.u32(node + 0x3C):#x} '
                          f'supported={supported:#x} requested={requested:#x} '
                          f'needs_extflags={bool(requested & VA_EXTFLAGS_ACTIVE and not supported & VA_EXTFLAGS_ACTIVE)}\n')
            return len(seen) >= 24
        except (gdb.MemoryError, UnicodeDecodeError):
            return False
        except Exception as error:
            gdb.write(f'MACVM_B014_QUERY_ERROR {error!r}\n')
            return True


try:
    for command in ('set pagination off', 'set confirm off', 'set architecture aarch64',
                    'set print thread-events off', 'set remotetimeout 30'):
        gdb.execute(command)
    gdb.execute('target remote 127.0.0.1:12355')
    verify_instructions(metadata.u32, metadata.SLIDE)
    anchor = metadata.lineage(metadata.EXPECTED_ANCHOR_VNODE)
    if anchor is None or anchor[0] != ():
        raise ValueError('live anchor mismatch')
    bp = Observe(f'*{GETATTR_LOCKED + metadata.SLIDE:#x}', gdb.BP_HARDWARE_BREAKPOINT, internal=True)
    bp.silent = True
    gdb.write('MACVM_B014_QUERY_ARMED read_only=1\n')
    gdb.execute('continue')
finally:
    if bp is not None and bp.is_valid():
        bp.delete()
    if gdb.selected_inferior().pid:
        gdb.execute('detach')
    gdb.write(f'MACVM_B014_QUERY_DETACHED read_only=1 observations={observations} scoped={scoped}\n')
