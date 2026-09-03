#!/usr/bin/env python3
"""Read-only ZIP64/CRC/inventory check of the preserved local Apple payload.

This verifies packaging and byte consistency, not Apple's signing decisions.
CLI execution is restricted to the isolated Linux validation guest.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import struct
import zipfile


def verify_zip64_footer(stream):
    stream.seek(0, io.SEEK_END)
    length = stream.tell()
    stream.seek(max(0, length - 65557))
    tail = stream.read()
    at = tail.rfind(b'PK\x05\x06')
    if at < 0 or len(tail) - at < 22:
        raise ValueError('ZIP end record missing')
    end = struct.unpack_from('<4s4H2IH', tail, at)
    if at + 22 + end[-1] != len(tail) or end[1:3] != (0, 0):
        raise ValueError('trailing bytes or multi-disk ZIP')
    end_offset = length - len(tail) + at
    if end_offset < 20:
        raise ValueError('ZIP64 locator missing')
    stream.seek(end_offset - 20)
    locator = struct.unpack('<4sIQI', stream.read(20))
    if locator[0] != b'PK\x06\x07' or locator[1] != 0 or locator[3] != 1:
        raise ValueError('ZIP64 locator missing or multi-disk')
    if not 0 <= locator[2] <= end_offset - 20 - 56:
        raise ValueError('ZIP64 record offset out of bounds')
    stream.seek(locator[2])
    record = struct.unpack('<4sQ2H2I4Q', stream.read(56))
    if record[0] != b'PK\x06\x06' or record[1] < 44:
        raise ValueError('ZIP64 end record invalid')
    if locator[2] + 12 + record[1] != end_offset - 20:
        raise ValueError('ZIP64 end record size mismatch')
    if record[4:6] != (0, 0) or record[6] != record[7]:
        raise ValueError('multi-disk ZIP64')
    count, cd_size, cd_offset = record[7:10]
    if cd_offset + cd_size != locator[2]:
        raise ValueError('central directory has a wrapped or invalid offset')
    for small, large, sentinel in ((end[3], count, 0xffff),
                                    (end[4], count, 0xffff),
                                    (end[5], cd_size, 0xffffffff),
                                    (end[6], cd_offset, 0xffffffff)):
        if small != sentinel and small != large:
            raise ValueError('classic and ZIP64 directory records disagree')
    return {'archive_bytes': length, 'entries': count,
            'central_directory_offset': cd_offset, 'central_directory_bytes': cd_size}


def verify_archive(stream, expected_info, expected_files, expected_bytes):
    result = verify_zip64_footer(stream)
    with zipfile.ZipFile(stream) as archive:
        entries = archive.infolist()
        if len(entries) != result['entries']:
            raise ValueError('directory entry count mismatch')
        seen = set()
        regular = []
        info_entry = None
        for entry in entries:
            name = entry.filename
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name:
                raise ValueError('unsafe archive path')
            key = str(path)
            if key in seen:
                raise ValueError('duplicate normalized archive path')
            seen.add(key)
            kind = stat.S_IFMT(entry.external_attr >> 16)
            if entry.flag_bits & 1:
                raise ValueError('unexpected encrypted payload')
            if not entry.is_dir() and kind in (0, stat.S_IFREG):
                regular.append(entry)
            if key == 'Info.plist':
                if entry.file_size != len(expected_info):
                    raise ValueError('source Info.plist size differs')
                info_entry = entry
        if len(regular) != expected_files or sum(e.file_size for e in regular) != expected_bytes:
            raise ValueError('source regular-file inventory differs')
        if info_entry is None or archive.read(info_entry) != expected_info:
            raise ValueError('source Info.plist bytes differ')
        failed = archive.testzip()
        if failed is not None:
            raise ValueError('CRC failed: ' + failed)
    result.update(regular_files=len(regular), regular_bytes=expected_bytes,
                  info_sha256=hashlib.sha256(expected_info).hexdigest(),
                  crc='all entries passed', apple_signatures='not evaluated')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('source_info', type=Path)
    args = parser.parse_args()
    if (platform.system(), platform.machine(), platform.node()) != ('Linux', 'x86_64', 'macvm-validation'):
        raise RuntimeError('isolated Linux guest required')
    if os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES':
        raise RuntimeError('debug environment confirmation required')
    if 'MACVM_ISOLATED_VALIDATION_GUEST=YES' not in Path('/etc/macvm-validation-guest').read_text().splitlines():
        raise RuntimeError('isolated VM marker missing')
    with args.archive.open('rb') as stream:
        print(json.dumps(verify_archive(stream, args.source_info.read_bytes(),
                                        2233, 19_202_615_016), indent=2))


if __name__ == '__main__':
    main()
