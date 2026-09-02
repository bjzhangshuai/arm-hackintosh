"""Empty EAN v1 metadata for an isolated VM's unused AUX region.

Layout checked against the 25G72 AppleVirtIOStorage binary:
verifyHeaderCRC (0xfffffe0008885280), updateHeaderFields (...8885334),
and addImage (...8885b38). This is metadata, not Apple firmware or keys.
"""

import struct
import zlib
import argparse
import hashlib
import os
from pathlib import Path
import shutil

HEADER_SIZE = 4096
CRC_OFFSET = 4092
EAN_OFFSET = 0x1A00000  # /product/util type 6, not the APFS xART-role volume
EAN_SIZE = 0x600000


def empty_header():
    data = bytearray(HEADER_SIZE)
    # version, magic, item count, total bytes, next free byte.
    # next_free must exclude the header: addImage writes at this offset.
    struct.pack_into('<5I', data, 0, 1, 0xEAEAEAEA, 0, EAN_SIZE, HEADER_SIZE)
    struct.pack_into('<I', data, CRC_OFFSET, zlib.crc32(data[:CRC_OFFSET]))
    return bytes(data)


def validate_empty_header(data):
    if len(data) != HEADER_SIZE:
        raise ValueError('EAN header must be exactly 4096 bytes')
    if struct.unpack_from('<5I', data) != (1, 0xEAEAEAEA, 0, EAN_SIZE, HEADER_SIZE):
        raise ValueError('unexpected empty EAN header fields')
    if any(data[20:CRC_OFFSET]):
        raise ValueError('empty EAN header has nonzero reserved/entry bytes')
    if struct.unpack_from('<I', data, CRC_OFFSET)[0] != zlib.crc32(data[:CRC_OFFSET]):
        raise ValueError('EAN header CRC mismatch')


def require_blank_region(data):
    if len(data) != EAN_SIZE or data not in (bytes(EAN_SIZE), b'\xff' * EAN_SIZE):
        raise ValueError('refusing to initialize nonblank EAN storage')


def initialize_copy(source, output):
    # The source is a prepared offline template, never a live VM block file.
    from build_vmapple_isc import inspect_isc_image, require_validation_environment
    from vmapple_util_layout import validate_isc_report
    require_validation_environment()
    source = Path(source).resolve(strict=True)
    output = Path(output)
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise ValueError('EAN output must be a new absolute path')
    parent = output.parent.resolve(strict=True)
    allowed = Path('/home/macvm/macos-restore/26.6').resolve(strict=True)
    if parent != allowed or source.parent != allowed:
        raise ValueError('EAN initialization is restricted to offline validation templates')
    report = inspect_isc_image(source)
    validate_isc_report(report)
    with source.open('rb') as src:
        src.seek(EAN_OFFSET)
        require_blank_region(src.read(EAN_SIZE))
        src.seek(0)
        # Exclusive creation: do not truncate an existing image on a race.
        with output.open('xb') as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
    header = empty_header()
    with output.open('r+b') as dst:
        dst.seek(EAN_OFFSET)
        dst.write(header)
        dst.flush()
        os.fsync(dst.fileno())
    # Compare every byte against the unchanged source, permitting exactly
    # the one reviewed header replacement. Neither firmware nor APFS changes.
    with source.open('rb') as src, output.open('rb') as dst:
        offset = 0
        digest = hashlib.sha256()
        while original := src.read(1024 * 1024):
            expected = bytearray(original)
            if offset <= EAN_OFFSET < offset + len(expected):
                at = EAN_OFFSET - offset
                expected[at:at + HEADER_SIZE] = header
            actual = dst.read(len(expected))
            if actual != expected:
                raise ValueError('unexpected write outside EAN header; preserve output for inspection')
            digest.update(actual)
            offset += len(expected)
        if dst.read(1):
            raise ValueError('EAN output size changed')
    validate_isc_report(inspect_isc_image(output))
    return digest.hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    print(initialize_copy(args.source, args.output))
