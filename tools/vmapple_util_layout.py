"""Bounds contract for the observed 25G72 firmware AUX utility regions."""

import struct

REGIONS_25G72 = (
    (1, 0, 0xA00000),
    (2, 0xA00000, 0x100000),
    (3, 0xB00000, 0x500000),
    (7, 0x1000000, 0x1000),
    (4, 0x1001000, 0x4FF000),
    (5, 0x1500000, 0x500000),
    (6, 0x1A00000, 0x600000),
)
UTIL_END = 0x2000000


def validate_regions(raw, *, partition_start=UTIL_END, disk_size=0x4000000):
    if not raw or len(raw) > 132 or len(raw) % 12:
        raise ValueError("malformed AUX utility region array")
    entries = tuple(struct.iter_unpack('<III', raw))
    # Fail closed on a different firmware layout rather than mapping it over
    # the APFS iSC volume. Another build requires its own reviewed contract.
    if entries != REGIONS_25G72:
        raise ValueError("AUX utility layout differs from the reviewed 25G72 layout")
    if not UTIL_END <= partition_start < disk_size:
        raise ValueError("AUX utility regions overlap iSC or exceed storage")
    return entries


def validate_isc_report(report):
    return validate_regions(
        b''.join(struct.pack('<III', *item) for item in REGIONS_25G72),
        partition_start=report['partition_start_lba'] * 512,
        disk_size=report['size_bytes'],
    )
