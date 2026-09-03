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
TRANSFER_KINDS = {
    'updatebrain': ('updatebrain-25G83.zip', '/updatebrain.zip'),
    'shutdown-logs': ('boot119-before-internal-logs.tar.gz', '/shutdown-logs.tar.gz'),
    'boot120-personalization-logs': (
        'boot120-personalization-20260903-logs.tar.gz',
        '/boot120-personalization-logs.tar.gz',
    ),
    'boot120-local-prepare-crash': (
        'boot120-local-prepare-crash-20260903-1330.tar.gz',
        '/boot120-local-prepare-crash.tar.gz',
    ),
    'boot120-b015-crash': (
        'boot120-b015-crash-20260903-1540.tar.gz',
        '/boot120-b015-crash.tar.gz',
    ),
    'boot120-local-product-info': (
        'boot120-local-product-25G83-Info.plist',
        '/boot120-local-product-info.plist',
    ),
    'boot120-offline-payload': (
        'boot120-local-UpdateBundle-25G83.zip',
        '/boot120-local-UpdateBundle-25G83.zip',
    ),
}


def resolve_transfer(kind):
    """Select only a fixed private destination; never accept caller-supplied paths."""
    if kind not in TRANSFER_KINDS:
        raise ValueError('unknown evidence kind')
    name, endpoint = TRANSFER_KINDS[kind]
    return DESTINATION.parent / name, endpoint


def transfer_policy(kind, expected_bytes=None):
    """Only the explicit offline payload gets a larger, exact length limit."""
    resolve_transfer(kind)
    if kind == 'boot120-offline-payload':
        if type(expected_bytes) is not int or not 18_000_000_000 <= expected_bytes <= 21_000_000_000:
            raise ValueError('exact observed 25G83 archive size required')
        return expected_bytes, 3600, 120
    if expected_bytes is not None:
        raise ValueError('large transfer sizing is not valid for evidence endpoints')
    return MAX_BYTES, 600, 30


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=tuple(TRANSFER_KINDS), default='updatebrain')
    parser.add_argument('--expected-bytes', type=int,
                        help='required exact observed size for offline payload only')
    args = parser.parse_args()
    destination, endpoint = resolve_transfer(args.kind)
    maximum, duration, socket_timeout = transfer_policy(args.kind, args.expected_bytes)
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or platform.node() != 'macvm-validation'
            or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'):
        raise RuntimeError('isolated Linux guard required')
    if 'MACVM_ISOLATED_VALIDATION_GUEST=YES' not in Path('/etc/macvm-validation-guest').read_text().splitlines():
        raise RuntimeError('isolated VM marker missing')
    if not Path('/home/macvm/installation-data').is_mount() or destination.exists():
        raise RuntimeError('data mount missing or evidence already exists; never overwrite')
    capacity = os.statvfs(destination.parent)
    if args.expected_bytes is not None and capacity.f_bavail * capacity.f_frsize < maximum + 1024**3:
        raise RuntimeError('insufficient isolated data capacity for offline copy')
    deadline = time.monotonic() + duration
    complete = False

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            nonlocal complete
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                size = 0
            if (self.path != endpoint or not 1 <= size <= maximum
                    or (args.expected_bytes is not None and size != args.expected_bytes)
                    or self.headers.get('Transfer-Encoding') or complete):
                self.send_error(400, 'fixed archive endpoint and bounded Content-Length required')
                return
            try:
                # Exclusive create also rejects symlinks/existing files.
                with destination.open('xb') as output:
                    os.chmod(destination, 0o600)
                    self.connection.settimeout(socket_timeout)
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
        print(f'MACVM_INSTALL_ARCHIVE_LISTEN loopback=127.0.0.1:18567 timeout={duration}s max_bytes={maximum}', flush=True)
        while not complete and time.monotonic() < deadline:
            server.handle_request()
    if not complete:
        raise RuntimeError('no complete archive received')


if __name__ == '__main__':
    main()
