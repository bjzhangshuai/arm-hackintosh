set pagination off
set confirm off
set print thread-events off
set debuginfod enabled off
handle SIGUSR1 nostop noprint pass
handle SIGUSR2 nostop noprint pass
handle SIGPIPE nostop noprint pass
handle SIGSEGV stop print pass
handle SIGABRT stop print pass
python
import gdb
import os
import pathlib
import sys

if os.uname().nodename != 'macvm-validation' or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES':
    raise gdb.GdbError('native watch requires the isolated validation VM')
pid = int(os.environ['MACVM_NATIVE_QEMU_PID'])
expected = pathlib.Path(os.environ['MACVM_NATIVE_QEMU_BIN']).resolve(strict=True)
builds = pathlib.Path('/home/macvm/src/macvm/build').resolve(strict=True)
if pid <= 1 or expected.name != 'qemu-system-aarch64' or builds not in expected.parents:
    raise gdb.GdbError('native watch target is outside validation builds')
if pathlib.Path(f'/proc/{pid}/exe').resolve(strict=True) != expected:
    raise gdb.GdbError('native watch PID does not match the selected binary')
output = pathlib.Path(os.environ['MACVM_NATIVE_CRASH_OUT']).absolute()
root = pathlib.Path('/home/macvm/runs/aux-26.6').resolve(strict=True)
if root not in output.parent.resolve(strict=True).parents:
    raise gdb.GdbError('native evidence must be under a validation run')
sys.path.insert(0, '/home/macvm/src/macvm/tools')
from native_crash_evidence import capture_stopped

signal_seen = []
def stopped(event):
    if isinstance(event, gdb.SignalEvent):
        signal_seen.append(event.stop_signal)
gdb.events.stop.connect(stopped)
attached = False
try:
    gdb.execute(f'attach {pid}')
    attached = True
    while gdb.selected_inferior().pid:
        signal_seen.clear()
        gdb.execute('continue')
        if any(s in ('SIGSEGV', 'SIGABRT') for s in signal_seen):
            capture_stopped(gdb, output)
            break
finally:
    gdb.events.stop.disconnect(stopped)
    if attached and gdb.selected_inferior().pid:
        # Detach preserves the pending signal's normal disposition. No kill,
        # forced stop, register patch or suppression of a guest crash.
        gdb.execute('detach')
end
