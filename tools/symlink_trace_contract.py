"""Instruction contracts for the reviewed macOS 26.6 (25G72) BootKC.

The return at ...91230 is attribute preparation, not VNOP_SYMLINK.  Verify
both the preceding BL target and the return instruction before enabling any
mutating diagnostic. Addresses come from the matching extracted BootKC.
"""

from __future__ import annotations

from collections.abc import Callable

PROC_COMM_OFFSET = 0x5CC
PROC_NAME_OFFSET = PROC_COMM_OFFSET + 17

# name, return address, actual callee, instruction at return address
CALL_RETURNS = (
    ("mac_create", 0xFFFFFE0009E911D4, 0xFFFFFE000A508E08, 0x35000E40),
    ("vnode_authorize", 0xFFFFFE0009E911F8, 0xFFFFFE0009E80594, 0x34000100),
    ("authattr", 0xFFFFFE0009E91230, 0xFFFFFE0009E7E1DC, 0xAA0003F8),
    ("vnop_symlink", 0xFFFFFE0009E9126C, 0xFFFFFE0009EB52B4, 0xF94017E3),
)
COMMON_RESULT = 0xFFFFFE0009E913E0


def bl_target(address: int, instruction: int) -> int:
    if instruction & 0xFC000000 != 0x94000000:
        raise ValueError(f"0x{address:x}: expected BL, got 0x{instruction:08x}")
    immediate = instruction & 0x03FFFFFF
    if immediate & 0x02000000:
        immediate -= 0x04000000
    return (address + immediate * 4) & 0xFFFFFFFFFFFFFFFF


def verify_instructions(read_u32: Callable[[int], int], slide: int) -> None:
    for name, ret, callee, return_instruction in CALL_RETURNS:
        call = ret + slide - 4
        actual = bl_target(call, read_u32(call))
        if actual != callee + slide:
            raise ValueError(f"{name}: callee 0x{actual:x} != 0x{callee + slide:x}")
        if read_u32(ret + slide) != return_instruction:
            raise ValueError(f"{name}: return instruction differs from reviewed BootKC")
    # The final errno is restored from x21 before cleanup of the path buffer.
    if read_u32(COMMON_RESULT + slide - 4) != 0xAA1503E0:
        raise ValueError("common result: expected mov x0, x21")
    if read_u32(COMMON_RESULT + slide) != 0xB40001F4:
        raise ValueError("common result: unexpected cleanup entry")
    # proc_name() copies from proc + 0x5cc. Reject old, guessed proc offsets.
    if read_u32(0xFFFFFE000A1DF89C + slide) != 0x91173001:
        raise ValueError("proc_name: unexpected proc.p_comm offset")


def same_transaction(dvp: int, cnp: int, expected_dvp: int, expected_cnp: int) -> bool:
    """Match kernel objects across vCPU migration, never a host GDB thread id."""
    return bool(expected_dvp and expected_cnp and dvp == expected_dvp and cnp == expected_cnp)


def is_completed_symlink(marker: str, result: int, matches: bool) -> bool:
    return matches and marker == "MACVM_SYMLINK_SYMLINKAT_COMMON_RESULT" and result == 0


def may_detach_after_result(marker: str, result: int, matches: bool, *, include_failure=False) -> bool:
    return bool(matches and marker == "MACVM_SYMLINK_SYMLINKAT_COMMON_RESULT"
                and (result == 0 or include_failure))
