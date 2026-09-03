#!/usr/bin/env python3
"""Add one NEW 1 GiB scratch disk to the running isolated Boot119 only.

Does not format, remove, resize or replace any disk. Run through the repository
Linux isolation guard. This is an installation filesystem-contract test disk,
not an extra physical-host resource or the macos26 installation target.
"""
from pathlib import Path
import json
import os
import platform
import subprocess

from qmp_screendump import QMPClient

RUN = Path('/home/macvm/runs/aux-26.6/xnu-imgsrc-reims-boot119-graphics-storage')
IMAGE = Path('/home/macvm/installation-data/metadata-contract-20260903.raw')
NODE = 'macvm-metadata-contract'
DEVICE = 'macvm-metadata-usb'
SERIAL = 'MACVMMETA20260903'
SIZE = 1073741824


def main():
    if not 1 <= len(SERIAL) <= 20 or not SERIAL.isalnum():
        raise RuntimeError('invalid USB storage serial/device_id contract')
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or platform.node() != 'macvm-validation'
            or os.environ.get('MACVM_METADATA_DISK_CONFIRMED') != 'BOOT119_NEW_1G'
            or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'):
        raise RuntimeError('wrong environment or missing explicit opt-in')
    marker = Path('/etc/macvm-validation-guest').read_text().splitlines()
    if 'MACVM_ISOLATED_VALIDATION_GUEST=YES' not in marker:
        raise RuntimeError('missing isolated VM marker')
    expected = Path('/home/macvm/src/macvm/build/qemu-boot119-graphics-storage/qemu-system-aarch64')
    if Path('/proc/925112/exe').resolve() != expected:
        raise RuntimeError('live QEMU identity changed')
    if not IMAGE.parent.is_mount():
        raise RuntimeError('approved data filesystem is not mounted')
    with QMPClient(RUN / 'qmp.sock', timeout=15) as qmp:
        if not qmp.execute('query-status').get('running'):
            raise RuntimeError('Boot119 is not running')
        nodes = qmp.execute('query-named-block-nodes')
        existing = os.environ.get('MACVM_METADATA_ATTACH_EXISTING') == 'YES'
        if existing:
            matches = [n for n in nodes if n.get('node-name') == NODE]
            if (not IMAGE.is_file() or IMAGE.stat().st_size != SIZE or len(matches) != 1
                    or matches[0].get('drv') != 'raw'
                    or matches[0].get('image', {}).get('filename') != str(IMAGE)):
                raise RuntimeError('existing unformatted test disk identity mismatch')
            if any(b.get('inserted', {}).get('node-name') == NODE for b in qmp.execute('query-block')):
                raise RuntimeError('existing disk already attached; inspect, do not duplicate')
        else:
            if IMAGE.exists() or any(n.get('node-name') in (NODE, NODE + '-file') for n in nodes):
                raise RuntimeError('disk/node already exists; inspect it, never recreate')
            os.umask(0o077)
            subprocess.run(['qemu-img', 'create', '-f', 'raw', str(IMAGE), str(SIZE)], check=True)
            if IMAGE.stat().st_size != SIZE:
                raise RuntimeError('new image size mismatch')
            qmp.execute('blockdev-add', {
                'driver': 'raw', 'node-name': NODE,
                'file': {'driver': 'file', 'node-name': NODE + '-file', 'filename': str(IMAGE)},
            })
        qmp.execute('device_add', {
            # Explicit root port avoids usb_claim_port's automatic hub when
            # only one root port remains. Boot119's Apple xHCI hub path is not
            # validated; never move existing keyboard/tablet/system disk.
            'driver': 'usb-storage', 'id': DEVICE, 'bus': 'usb-bus.0', 'port': '4',
            'drive': NODE, 'serial': SERIAL, 'logical_block_size': 512,
            'physical_block_size': 4096, 'werror': 'stop', 'rerror': 'report',
        })
        blocks = qmp.execute('query-block')
        matches = [b for b in blocks if b.get('inserted', {}).get('node-name') == NODE]
        if len(matches) != 1 or matches[0]['inserted']['image']['filename'] != str(IMAGE):
            raise RuntimeError('post-attach identity mismatch; preserve disk for inspection')
        print(json.dumps({'image': str(IMAGE), 'size': SIZE, 'serial': SERIAL,
                          'blocks': matches, 'formatted': False}, indent=2))


if __name__ == '__main__':
    main()
