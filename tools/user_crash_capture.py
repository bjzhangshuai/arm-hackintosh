"""Bounded, read-only crash evidence; one unreadable field never hides others."""

from tools.arm64_user_memory import frame_chain


def read_c_string(memory, address, limit=4096):
    if not 0 < limit <= 4096:
        raise ValueError("invalid string limit")
    chunks = []
    while limit:
        count = min(64, limit, 0x4000 - (address & 0x3fff))
        raw = memory.read(address, count)
        if len(raw) != count:
            raise ValueError("short string read")
        before, separator, _ = raw.partition(b"\0")
        chunks.append(before)
        if separator:
            return b"".join(chunks)
        address += count
        limit -= count
    return b"".join(chunks)


def capture(memory, registers):
    result = {"strings": {}, "errors": {}, "frames": []}
    for register in ("x0", "x1", "x4", "x5"):
        address = registers.get(register, 0) & ((1 << memory.va_bits) - 1)
        if address < 0x100000000:
            continue
        try:
            result["strings"][register] = read_c_string(memory, address)
        except Exception as error:
            result["errors"][register] = str(error)
    try:
        result["frames"] = frame_chain(memory, registers.get("x29", 0))
    except Exception as error:
        result["errors"]["frames"] = str(error)
    return result
