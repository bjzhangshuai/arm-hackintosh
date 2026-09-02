"""Isolated-VM-only actual ARM64 counter/timer regression; retains all artifacts."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

EXPECTED_HZ = 24_000_000


def validate_sample(first, last, seconds):
    if len(first) != 5 or len(last) != 5 or seconds <= 0:
        raise ValueError('invalid timer sample')
    if first[0] != EXPECTED_HZ or last[0] != EXPECTED_HZ:
        raise ValueError('firmware counter-frequency register is not 24 MHz')
    rate = (last[2] - first[2]) / seconds
    # Existing QEMU uses a 41 ns integer scale: expected measured rate is
    # approximately 24.390244 MHz, not precisely 24 MHz. Allow scheduling noise.
    if not EXPECTED_HZ * 0.96 <= rate <= EXPECTED_HZ * 1.08:
        raise ValueError(f'actual counter rate mismatch: {rate}')
    if last[4] != 1 or not EXPECTED_HZ <= last[3] - last[1] <= EXPECTED_HZ * 1.12:
        raise ValueError('virtual timer did not expire at its programmed count')
    return rate


def parse_memory(text):
    values = []
    for line in text.splitlines():
        values.extend(int(v, 16) for v in re.findall(r'0x([0-9a-fA-F]+)', line.partition(':')[2]))
    if len(values) != 5:
        raise ValueError('unexpected monitor memory response')
    return values


def main():
    from build_vmapple_isc import require_validation_environment
    from qmp_screendump import QMPClient
    require_validation_environment()
    if socket.gethostname() != 'macvm-validation':
        raise SystemExit('dedicated validation VM required')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    output = args.output
    if not binary.is_relative_to('/home/macvm/src/macvm/build'):
        raise ValueError('only project-built QEMU binaries permitted')
    if not output.is_absolute() or output.exists() or not output.parent.resolve().is_relative_to('/home/macvm/runs'):
        raise ValueError('new isolated-run output path required')
    output.mkdir()
    fixture = Path(__file__).resolve().parents[1] / 'tests/fixtures/vmapple-timer.S'
    subprocess.run(['llvm-mc', '-triple=aarch64', '-filetype=obj', str(fixture), '-o', str(output / 'timer.o')], check=True)
    subprocess.run(['llvm-objcopy', '-O', 'binary', '--only-section=.text', str(output / 'timer.o'), str(output / 'firmware.bin')], check=True)
    for name in ('aux.img', 'root.img'):
        with (output / name).open('xb') as block:
            block.truncate(64 * 1024 * 1024)
    sock = output / 'qmp.sock'
    command = [str(binary), '-machine', 'vmapple', '-accel', 'tcg,thread=multi',
               '-cpu', 'max', '-smp', '8', '-m', '1G', '-S', '-bios', str(output / 'firmware.bin'),
               '-drive', f'if=pflash,index=0,format=raw,file={output / "aux.img"}',
               '-drive', f'if=pflash,index=1,format=raw,file={output / "root.img"}',
               '-display', 'none', '-serial', 'none', '-monitor', 'none',
               '-qmp', f'unix:{sock},server=on,wait=off']
    (output / 'command.json').write_text(json.dumps(command, indent=2))
    with (output / 'qemu.log').open('x') as log:
        child = subprocess.Popen(command, cwd=output, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 10
            while not sock.exists():
                if child.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('QEMU did not open its isolated QMP socket')
                time.sleep(0.05)
            with QMPClient(sock, 10) as qmp:
                cpus = qmp.execute('query-cpus-fast')
                frequencies = [qmp.execute('qom-get', {'path': cpu['qom-path'], 'property': 'cntfrq'}) for cpu in cpus]
                if frequencies != [EXPECTED_HZ] * 8:
                    raise ValueError(f'per-CPU frequency mismatch: {frequencies}')
                def sample():
                    before = time.monotonic()
                    values = parse_memory(qmp.execute('human-monitor-command', {'command-line': 'xp /5gx 0x70000000'}))
                    return (before + time.monotonic()) / 2, values
                qmp.execute('cont')
                time.sleep(0.2)
                start, first = sample()
                time.sleep(2)
                end, last = sample()
                rate = validate_sample(first, last, end - start)
                result = {'cpu_hz': frequencies, 'first': first, 'last': last,
                          'seconds': end - start, 'actual_ticks_per_second': rate,
                          'remaining_integer_scale_drift_percent': (rate / EXPECTED_HZ - 1) * 100,
                          'timer_expired': True}
                (output / 'result.json').write_text(json.dumps(result, indent=2))
                print(json.dumps(result))
                qmp.execute('quit')
            child.wait(timeout=10)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == '__main__':
    main()
