#!/usr/bin/env python3
"""Receive one fixed installer asset inside the isolated Linux VM only.

This is a bounded loopback-only diagnostic transfer, not a general upload API.
The Apple archive is private analysis input and must never enter the repository.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import argparse
import hashlib
import os
import platform
import time

DESTINATION = Path('/home/macvm/installation-data/install-analysis/updatebrain-25G83.zip')
MAX_BYTES = 64 * 1024 * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('updatebrain', 'shutdown-logs'), default='updatebrain')
    args = parser.parse_args()
    destination = (DESTINATION if args.kind == 'updatebrain' else
                   DESTINATION.parent / 'boot119-before-internal-logs.tar.gz')
    endpoint = '/updatebrain.zip' if args.kind == 'updatebrain' else '/shutdown-logs.tar.gz'
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or platform.node() != 'macvm-validation'
            or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'):
        raise RuntimeError('isolated Linux guard required')
    if 'MACVM_ISOLATED_VALIDATION_GUEST=YES' not in Path('/etc/macvm-validation-guest').read_text().splitlines():
        raise RuntimeError('isolated VM marker missing')
    if not Path('/home/macvm/installation-data').is_mount() or destination.exists():
        raise RuntimeError('data mount missing or evidence already exists; never overwrite')
    deadline = time.monotonic() + 600
    complete = False

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            nonlocal complete
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                size = 0
            if (self.path != endpoint or not 1 <= size <= MAX_BYTES
                    or self.headers.get('Transfer-Encoding') or complete):
                self.send_error(400, 'fixed archive endpoint and bounded Content-Length required')
                return
            try:
                # Exclusive create also rejects symlinks/existing files.
                with destination.open('xb') as output:
                    os.chmod(destination, 0o600)
                    self.connection.settimeout(30)
                    remaining = size
                    digest = hashlib.sha256()
                    while remaining:
                        data = self.rfile.read(min(remaining, 65536))
                        if not data:
                            raise EOFError('incomplete upload; preserve partial evidence')
                        output.write(data)
                        digest.update(data)
                        remaining -= len(data)
                    output.flush()
                    os.fsync(output.fileno())
                complete = True
                self.send_response(201)
                self.end_headers()
                self.wfile.write(b'archive received\n')
                print(f'MACVM_INSTALL_ARCHIVE_RECEIVED bytes={size} sha256={digest.hexdigest()} path={destination}', flush=True)
            except Exception as error:
                print(f'MACVM_INSTALL_ARCHIVE_FAILED {error!r}', flush=True)
                self.send_error(500, 'transfer failed; do not overwrite evidence')

    with HTTPServer(('127.0.0.1', 18567), Handler) as server:
        server.timeout = 1
        print('MACVM_INSTALL_ARCHIVE_LISTEN loopback=127.0.0.1:18567 timeout=600s', flush=True)
        while not complete and time.monotonic() < deadline:
            server.handle_request()
    if not complete:
        raise RuntimeError('no complete archive received')


if __name__ == '__main__':
    main()
