"""One bounded session covering both established B010 and B012 contracts.

Use only after the current local archive is ready. This is not an installation
loop or timer: it attaches to the existing inner VM and stops at one NULL repair,
contract mismatch or external SIGINT. A normal metadata observation limit retires
only those metadata breakpoints; the separate one-shot NULL guard stays armed.
No signature/policy decision or guest instruction byte is changed.
"""
import os
import sys

import gdb

sys.path.insert(0, '/home/macvm/src/macvm/tools')
if (os.uname().nodename != 'macvm-validation'
        or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'
        or os.environ.get('MACVM_LOCAL_INSTALL_BRIDGE') != 'BOOT120_B010_B012'
        or os.environ.get('MACVM_TMPFS_COMPAT_CONFIRMED') != 'BOOT120_VERIFIED'
        or os.environ.get('MACVM_TMPFS_REPAIR_EXISTING') == 'YES'
        or os.environ.get('MACVM_NULL_CLEANUP_MODE') != 'repair-once'):
    raise RuntimeError('combined bridge requires exact opt-ins; no old-bundle relabelling')

import bridge_boot120_null_cleanup as cleanup
import compat_tmpfs_flags_live as metadata

null_bp = None
try:
    cleanup.attach_and_verify()
    metadata.install_breakpoints()
    null_bp = cleanup.NullCleanup(f'*{cleanup.CF_NULL:#x}', gdb.BP_HARDWARE_BREAKPOINT, internal=True)
    null_bp.silent = True
    gdb.write('MACVM_BOOT120_LOCAL_BRIDGE_ARMED null_repairs_max=1 existing_relabels=0 metadata_observation_max=100000\n')
    gdb.execute('continue')
    if not cleanup.repaired and metadata.stop_reason == 'limit':
        # Boot120's original metadata session actually reached 100001
        # observations. Its independent budget must not disarm the later
        # preflight cleanup guard. Never resume a contract error or unknown stop.
        metadata.remove_breakpoints()
        if not (metadata.counts['create'] or metadata.counts['extflags']):
            # A verified anchor/installed breakpoint does not establish that
            # the installer received any required filesystem response.
            gdb.write('MACVM_BOOT120_METADATA_COVERAGE_MISSING no_scoped_response=1 continuation_refused=1\n')
        else:
            gdb.write('MACVM_BOOT120_METADATA_BUDGET_RETIRED null_guard_still_armed=1 metadata_writes_enabled=0\n')
            gdb.execute('continue')
finally:
    if null_bp is not None and null_bp.is_valid():
        null_bp.delete()
    metadata.remove_breakpoints()
    if gdb.selected_inferior().pid:
        gdb.execute('detach')
    gdb.write(f'MACVM_BOOT120_LOCAL_BRIDGE_DETACHED null_repaired={cleanup.repaired} metadata={metadata.counts!r}\n')
