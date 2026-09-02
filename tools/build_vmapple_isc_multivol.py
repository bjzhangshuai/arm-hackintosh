#!/usr/bin/env python3
"""Create a NEW isolated iSC template; never edit an existing/live image."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import uuid

import build_vmapple_isc as isc
from vmapple_ean import EAN_OFFSET, empty_header, validate_empty_header
from vmapple_util_layout import validate_isc_report

BASE = Path('/home/macvm/macos-restore/26.6')
TOOLS = Path('/home/macvm/src/macvm/third_party/apfsprogs-validation')


def build(output):
    isc.require_validation_environment()
    if platform.node() != 'macvm-validation':
        raise ValueError('requires isolated macvm-validation')
    output = Path(output)
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise ValueError('output must be a new absolute file path')
    if output.parent.resolve(strict=True) != BASE.resolve(strict=True):
        raise ValueError('output must be an offline restore template, not a run image')
    size = 2048 * 1024**2
    layout = isc._layout(size)
    ids = [("xART", isc.DEFAULT_VOLUME_UUID, 0x100),
           ("iSCPreboot", uuid.uuid5(isc.DEFAULT_CONTAINER_UUID, 'iSCPreboot'), 0x10),
           ("Hardware", uuid.uuid5(isc.DEFAULT_CONTAINER_UUID, 'Hardware'), 0x140)]
    with tempfile.TemporaryDirectory(prefix='.isc-complete-', dir=output.parent) as temp:
        container = Path(temp) / 'isc.apfs'
        with container.open('xb') as stream:
            stream.truncate(layout['partition_bytes'])
        command = [str(TOOLS / 'mkapfs/mkapfs'), '-U', str(isc.DEFAULT_CONTAINER_UUID)]
        for name, identity, role in ids:
            command += ['-V', f'{name},{identity},{role}']
        subprocess.run([*command, str(container)], check=True, timeout=60)
        subprocess.run([str(TOOLS / 'apfsck/apfsck'), '-cuw', str(container)], check=True, timeout=60)
        staged = Path(temp) / 'complete.img'
        isc._write_gpt_image(staged, container, size_bytes=size,
                             disk_uuid=isc.DEFAULT_DISK_UUID,
                             partition_uuid=isc.DEFAULT_PARTITION_UUID)
        header = empty_header()
        with staged.open('r+b') as stream:
            stream.seek(EAN_OFFSET)
            if stream.read(len(header)) != bytes(len(header)):
                raise ValueError('new template EAN header is not blank')
            stream.seek(EAN_OFFSET)
            stream.write(header)
            stream.flush()
            os.fsync(stream.fileno())
        validate_empty_header(header)
        report = isc.inspect_isc_image(staged)
        validate_isc_report(report)
        if len(report['apfs_volumes']) != 3:
            raise ValueError('missing required iSC volume')
        # Exclusive publication, including against a concurrent creator.
        os.link(staged, output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    print(json.dumps(build(parser.parse_args().output), indent=2))
