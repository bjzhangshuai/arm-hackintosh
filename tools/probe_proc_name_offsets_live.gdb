set pagination off
set confirm off
set architecture aarch64

# Attach to the live vmapple kernel and scan a known struct proc pointer for
# printable process-name fields.  This is observe-only: it reads target memory,
# prints candidate offsets, detaches, and continues execution.
#
# Usage:
#   gdb-multiarch -q \
#     -ex 'set $macvm_proc_probe_address = 0xfffffe240c031ce8' \
#     -x tools/probe_proc_name_offsets_live.gdb

target remote 127.0.0.1:12345

python
import gdb
import string

PRINTABLE = set(bytes(string.printable, "ascii")) - {0x0b, 0x0c}

def _macvm_probe_u64(name, default=0):
    try:
        return int(gdb.parse_and_eval(name)) & 0xFFFFFFFFFFFFFFFF
    except Exception:
        return default

def _macvm_read(address, length):
    return gdb.selected_inferior().read_memory(address, length).tobytes()

def _macvm_is_proc_name_candidate(raw):
    raw = raw.split(b"\0", 1)[0]
    if not (2 <= len(raw) <= 64):
        return False
    if any(byte not in PRINTABLE for byte in raw):
        return False
    text = raw.decode("ascii", errors="ignore")
    if text.strip() != text:
        return False
    if not any(ch.isalpha() for ch in text):
        return False
    return True

def _macvm_emit_proc_name_candidates():
    proc = _macvm_probe_u64("$macvm_proc_probe_address")
    if not proc:
        gdb.write("MACVM_PROC_NAME_PROBE_MISSING address=0\n")
        return
    gdb.write(f"MACVM_PROC_NAME_PROBE_BEGIN proc=0x{proc:x}\n")
    try:
        data = _macvm_read(proc, 0x3000)
    except Exception as error:
        gdb.write(f"MACVM_PROC_NAME_PROBE_READ_FAILED error={error}\n")
        return
    seen = set()
    for offset in range(0, len(data) - 2):
        raw = data[offset : offset + 65]
        if not _macvm_is_proc_name_candidate(raw):
            continue
        text = raw.split(b"\0", 1)[0].decode("ascii", errors="ignore")
        key = (offset, text)
        if key in seen:
            continue
        seen.add(key)
        gdb.write(f"MACVM_PROC_NAME_CANDIDATE offset=0x{offset:x} text={text!r}\n")
    gdb.write("MACVM_PROC_NAME_PROBE_END\n")

_macvm_emit_proc_name_candidates()
end

detach
quit
