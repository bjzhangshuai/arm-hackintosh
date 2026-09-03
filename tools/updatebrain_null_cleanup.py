"""Exact-image mitigation for B012's invalid CFRelease(NULL) cleanup call.

This pure planner performs no writes. It permits only a jump from CFRelease's
NULL-only failure block to its own normal, authenticated-return epilogue, for
one identified UpdateBrain cleanup call. Non-NULL releases and all signature,
ticket, ownership and authorization decisions remain unmodified.
"""
import struct

PROCESS = 'com.apple.MobileSoftwareUpdate.UpdateBrainService'
EXECUTABLE_UUID = bytes.fromhex('ab89a9684a2b3b7a845b78dbb8af3b32')
# set_proc_name uses sizeof(field)-1: p_comm[17], p_name[33]. Neither
# stores this 49-byte executable name. Name prefixes are only a prefilter;
# the kernel's LC_UUID and the caller image/code/frame checks are mandatory.
PROC_COMM_OFFSET, PROC_NAME_OFFSET, PROC_UUID_OFFSET = 0x5CC, 0x5DD, 0x608
PROCESS_LAYOUT_WORDS = {
    0xFFFFFE000A1DF89C: 0x91173001,  # proc_name: p_comm +0x5cc
    0xFFFFFE000A1DFB3C: 0x52800429,  # proc_selfname: bound 33
    0xFFFFFE000A1DFB48: 0x91177501,  # proc_selfname: p_name +0x5dd
    0xFFFFFE000A28A9FC: 0x91182008,  # originator UUID: p_uuid +0x608
    0xFFFFFE000A28AA00: 0x3DC00100,  # load the complete 16-byte UUID
}
CF_BASE = 0x187C4F000
CF_UUID = bytes.fromhex('fdba2243a7ab35249b94f3034ac36e41')
UB_UUID = bytes.fromhex('8bb113cf7583355482b4b4c009a16a16')
CF_NULL = 0x187C59468
CF_RETURN = 0x187C593A0
CALLER_RETURN = 0x514FC
MASK47 = (1 << 47) - 1
CF_WORDS = {
    0xA314: 0xD503237F, 0xA318: 0xA9BF7BFD,
    0xA31C: 0x910003FD, 0xA320: 0xB4000A40,
    0xA3A0: 0xA8C17BFD, 0xA3A4: 0xD65F0FFF,
    0xA468: 0x94078D24,
}
UB_WORDS = {
    0x5130C: 0xD503237F, 0x51310: 0xD10143FF,
    0x5131C: 0xA9047BFD, 0x51320: 0x910103FD,
    0x51328: 0xF9000FFF, 0x51368: 0x940256A3,
    0x5136C: 0x34000100, 0x51388: 0x14000054,
    0x514E8: 0x9408EBCA, 0x514F0: 0x9408EBC8,
    0x514F4: 0xF9400FE0, 0x514F8: 0x9408EBC6,
    0x514FC: 0xA9447BFD, 0x51500: 0xA9434FF4,
    0x51504: 0xA94257F6, 0x51508: 0x910143FF,
    0x5150C: 0xD65F0FFF,
}


def is_updatebrain_proc(read, proc):
    """Bounded kernel identity check; never identify by a truncated name alone."""
    if (type(proc) is not int or proc & 7
            or not 0xFFFFFE0000000000 <= proc < 0xFFFFFF0000000000 - 0x618):
        raise ValueError('invalid proc identity address')
    name = PROCESS.encode('ascii')
    if read(proc + PROC_COMM_OFFSET, 17) != name[:16] + b'\0':
        return False
    if read(proc + PROC_NAME_OFFSET, 33) != name[:32] + b'\0':
        return False
    return read(proc + PROC_UUID_OFFSET, 16) == EXECUTABLE_UUID


def verify_uuid(read, base, expected):
    header = read(base, 32)
    magic, cpu, subtype, _, count, size, _, _ = struct.unpack('<8I', header)
    if magic != 0xFEEDFACF or cpu != 0x100000C or subtype & 0xFFFFFF != 2:
        raise ValueError('wrong ARM64e Mach-O image')
    if not 1 <= count <= 256 or not 8 <= size <= 32768:
        raise ValueError('invalid Mach-O command bounds')
    commands = read(base + 32, size)
    offset, uuids = 0, []
    for _ in range(count):
        if offset + 8 > size:
            raise ValueError('truncated Mach-O command')
        cmd, extent = struct.unpack_from('<II', commands, offset)
        if extent < 8 or extent % 8 or offset + extent > size:
            raise ValueError('invalid Mach-O command size')
        if cmd == 0x1B:
            if extent != 24:
                raise ValueError('invalid UUID command')
            uuids.append(commands[offset + 8:offset + 24])
        offset += extent
    if offset != size or uuids != [expected]:
        raise ValueError('image UUID mismatch or duplicate')


def verify_words(read, base, words):
    for offset, expected in words.items():
        if read(base + offset, 4) != struct.pack('<I', expected):
            raise ValueError(f'instruction mismatch at {offset:#x}')


def plan_cleanup(read, *, process, pc, x0, sp, fp, lr):
    """Return only the safe PC destination, or None for unrelated/non-NULL calls.

    Caller supplies this exact task's read-only address-space walker. PAC bits
    are masked for *identity comparison only*; the original signed LR is never
    changed. CFRelease's real RETAB instruction still authenticates the return.
    """
    if process != PROCESS or pc != CF_NULL or x0 != 0:
        return None
    if not 0 < sp < MASK47 - 0x60 or sp & 15 or fp != sp:
        raise ValueError('unexpected CFRelease stack frame')
    saved_fp, saved_lr = struct.unpack('<QQ', read(sp, 16))
    if saved_fp != sp + 0x50 or saved_lr != lr:
        raise ValueError('caller frame/LR mismatch')
    base = (saved_lr & MASK47) - CALLER_RETURN
    if not 0x100000000 <= base < 0x180000000 or base & 0x3FFF:
        raise ValueError('not the exact UpdateBrain callsite')
    # CFRelease pushed 16 bytes; the caller's ticket local is at its SP+0x18.
    if struct.unpack('<Q', read(sp + 0x28, 8))[0] != 0:
        raise ValueError('caller ticket local is not NULL')
    verify_uuid(read, CF_BASE, CF_UUID)
    verify_uuid(read, base, UB_UUID)
    verify_words(read, CF_BASE, CF_WORDS)
    verify_words(read, base, UB_WORDS)
    return CF_RETURN
