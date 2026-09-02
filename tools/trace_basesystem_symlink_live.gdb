set pagination off
set confirm off
set architecture aarch64

# Attach this script after the BaseSystem pivot has completed.  The main
# post-GDB handoff script detaches once the BootKC/root-state patches are
# applied, so late Recovery userspace diagnostics need a separate live GDB
# session that remains blocked in `continue`.
target remote 127.0.0.1:12345

set $macvm_kernelcache_slide = 0x19344000
set $macvm_symlink_trace_count = 0
set $macvm_symlink_trace_limit = 8
set $macvm_symlink_last_apfs_index = 0
set $macvm_symlink_return_trace_count = 0

set $macvm_vnop_symlink_primary_static = 0xfffffe000884e174
set $macvm_vnop_symlink_secondary_static = 0xfffffe0008869948
set $macvm_apfs_vnop_symlink_static = 0xfffffe00098eec34
set $macvm_apfs_vnop_symlink_return_fast_static = 0xfffffe00098eed1c
set $macvm_apfs_vnop_symlink_return_slow_static = 0xfffffe00098ef3e4

set $macvm_vnop_symlink_primary = $macvm_vnop_symlink_primary_static + $macvm_kernelcache_slide
set $macvm_vnop_symlink_secondary = $macvm_vnop_symlink_secondary_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink = $macvm_apfs_vnop_symlink_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink_return_fast = $macvm_apfs_vnop_symlink_return_fast_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink_return_slow = $macvm_apfs_vnop_symlink_return_slow_static + $macvm_kernelcache_slide

python
import gdb
import struct

def _macvm_u64(expression):
    return int(gdb.parse_and_eval(expression)) & 0xFFFFFFFFFFFFFFFF

def _macvm_memory():
    return gdb.selected_inferior()

def _macvm_read_u32(address):
    return struct.unpack("<I", _macvm_memory().read_memory(address, 4).tobytes())[0]

def _macvm_read_u64(address):
    return struct.unpack("<Q", _macvm_memory().read_memory(address, 8).tobytes())[0]

def _macvm_read_bytes(address, length):
    return _macvm_memory().read_memory(address, length).tobytes()

def _macvm_read_c_string(address, limit=256):
    if address == 0:
        return "<null>"
    data = _macvm_read_bytes(address, limit)
    return data.split(b"\0", 1)[0].decode("utf-8", errors="replace")

def _macvm_read_component_name(cnp):
    if cnp == 0:
        return "<null>"
    name_pointer = _macvm_read_u64(cnp + 0x28)
    name_length = min(_macvm_read_u32(cnp + 0x30), 256)
    if name_pointer == 0:
        return "<null>"
    return _macvm_read_bytes(name_pointer, name_length).decode("utf-8", errors="replace")

def _macvm_emit_symlink_trace(marker):
    try:
        args = _macvm_u64("$x0")
        dvp = _macvm_read_u64(args + 0x08)
        vpp = _macvm_read_u64(args + 0x10)
        cnp = _macvm_read_u64(args + 0x18)
        vap = _macvm_read_u64(args + 0x20)
        target_pointer = _macvm_read_u64(args + 0x28)
        name = _macvm_read_component_name(cnp)
        target = _macvm_read_c_string(target_pointer)
        gdb.write(
            f"{marker} "
            f"index={int(gdb.parse_and_eval('$macvm_symlink_trace_count'))} "
            f"pc=0x{_macvm_u64('$pc'):x} args=0x{args:x} "
            f"dvp=0x{dvp:x} vpp=0x{vpp:x} cnp=0x{cnp:x} vap=0x{vap:x} "
            f"name={name!r} target={target!r}\n"
        )
    except Exception as error:
        gdb.write(
            f"{marker} "
            f"index={int(gdb.parse_and_eval('$macvm_symlink_trace_count'))} "
            f"decode-failed {error}\n"
        )
end

hbreak *$macvm_vnop_symlink_primary
commands
  silent
  if $macvm_symlink_trace_count < $macvm_symlink_trace_limit
    set $macvm_symlink_trace_count = $macvm_symlink_trace_count + 1
    python _macvm_emit_symlink_trace("MACVM_SYMLINK_VNOP_PRIMARY_ENTER")
  end
  continue
end

hbreak *$macvm_vnop_symlink_secondary
commands
  silent
  if $macvm_symlink_trace_count < $macvm_symlink_trace_limit
    set $macvm_symlink_trace_count = $macvm_symlink_trace_count + 1
    python _macvm_emit_symlink_trace("MACVM_SYMLINK_VNOP_SECONDARY_ENTER")
  end
  continue
end

hbreak *$macvm_apfs_vnop_symlink
commands
  silent
  if $macvm_symlink_trace_count < $macvm_symlink_trace_limit
    set $macvm_symlink_trace_count = $macvm_symlink_trace_count + 1
    set $macvm_symlink_last_apfs_index = $macvm_symlink_trace_count
    python _macvm_emit_symlink_trace("MACVM_SYMLINK_APFS_ENTER")
  end
  continue
end

hbreak *$macvm_apfs_vnop_symlink_return_fast
commands
  silent
  if $macvm_symlink_last_apfs_index != 0 && $macvm_symlink_return_trace_count < $macvm_symlink_trace_limit
    set $macvm_symlink_return_trace_count = $macvm_symlink_return_trace_count + 1
    printf "MACVM_SYMLINK_APFS_RETURN index=%u return=fast result=%u x0=0x%lx\n", $macvm_symlink_last_apfs_index, $w0, $x0
  end
  continue
end

hbreak *$macvm_apfs_vnop_symlink_return_slow
commands
  silent
  if $macvm_symlink_last_apfs_index != 0 && $macvm_symlink_return_trace_count < $macvm_symlink_trace_limit
    set $macvm_symlink_return_trace_count = $macvm_symlink_return_trace_count + 1
    printf "MACVM_SYMLINK_APFS_RETURN index=%u return=slow result=%u x0=0x%lx\n", $macvm_symlink_last_apfs_index, $w0, $x0
  end
  continue
end

printf "MACVM_SYMLINK_LIVE_TRACE_ARMED primary=%#lx secondary=%#lx apfs=%#lx\n", $macvm_vnop_symlink_primary, $macvm_vnop_symlink_secondary, $macvm_apfs_vnop_symlink
continue
