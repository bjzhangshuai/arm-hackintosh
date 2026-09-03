set pagination off
set confirm off
set architecture aarch64
set print thread-events off
set remotetimeout 30

# Observe-only process-list probe for the live vmapple kernel.
# It reads the exported kernproc pointer, walks the proc p_list chain, prints
# p_comm/p_name candidates, detaches, and continues execution.

python
import os
port = int(os.environ.get("MACVM_GDB_PORT", "12345"))
if not 1024 <= port <= 65535:
    raise ValueError("invalid validation GDB port")
gdb.execute(f"target remote 127.0.0.1:{port}")
end

thread apply all info registers pc x30

python
import gdb
import struct
import sys

sys.path.insert(0, "/home/macvm/src/macvm/tools")
from symlink_trace_contract import verify_instructions
from arm64_user_memory import UserMemory16K, frame_chain

KERNELCACHE_SLIDE = 0x19344000
KERNPROC_STATIC = 0xFFFFFE0007916C28
PROC_P_LIST_NEXT_OFFSET = 0x0
PROC_P_COMM_OFFSET = 0x5CC
PROC_P_NAME_OFFSET = 0x5DD
PROC_PID_OFFSET = 0x60

def _macvm_read(address, length):
    return gdb.selected_inferior().read_memory(address, length).tobytes()

def _macvm_read_u64(address):
    return struct.unpack("<Q", _macvm_read(address, 8))[0]

def _macvm_try_read_u64(address):
    try:
        return _macvm_read_u64(address)
    except Exception:
        return 0

def _macvm_try_read_c_string(address, limit):
    if not address:
        return "<null>"
    try:
        raw = _macvm_read(address, limit)
    except Exception as error:
        return f"<unreadable:{error}>"
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")

def _macvm_good_kernel_pointer(value):
    return 0xFFFFFE0000000000 <= value <= 0xFFFFFF0000000000

def _macvm_strip_data_pointer(value):
    # T1SZ is 17 in Boot112: PAC occupies bit 47 as well. Use the live
    # translation width rather than assuming 48-bit kernel addresses.
    tcr = int(gdb.parse_and_eval("$TCR_EL1"))
    bits = 64 - ((tcr >> 16) & 0x3F)
    if not 39 <= bits <= 48:
        raise ValueError("unexpected kernel translation width")
    mask = (1 << bits) - 1
    return (value & mask) | (0xFFFFFFFFFFFFFFFF ^ mask) if value else 0

def _macvm_read_physical(address, length):
    # Only switches the debugger's address interpretation, not CPU/MMU state.
    reply = gdb.execute("maintenance packet Qqemu.PhyMemMode:1", to_string=True)
    if 'received: "OK"' not in reply:
        raise ValueError("physical read mode refused")
    try:
        return _macvm_read(address, length)
    finally:
        reply = gdb.execute("maintenance packet Qqemu.PhyMemMode:0", to_string=True)
        if 'received: "OK"' not in reply:
            raise ValueError("virtual read mode restore failed")

def _macvm_kernel_frames(fp, low, high):
    frames = []
    for _ in range(40):
        if fp & 15 or not low <= fp <= high - 16:
            break
        previous, lr = struct.unpack("<QQ", _macvm_read(fp, 16))
        frames.append((hex(fp), hex(_macvm_strip_data_pointer(lr))))
        if previous <= fp:
            break
        fp = previous
    return frames

def _macvm_probe_kernel_stack(thread, pid, tid):
    if os.environ.get("MACVM_PROBE_KERNEL_STACKS") != "YES":
        return
    # ml_stack_remaining reads thread+0xe0; CHECK_KERNEL_STACK in the
    # actual BootKC reads thread+0x148. No register or memory writes.
    base = _macvm_read_u64(thread + 0xE0)
    saved = _macvm_strip_data_pointer(_macvm_read_u64(thread + 0x148))
    gdb.write(f"MACVM_KERNEL_STACK_META pid={pid} tid={tid} base=0x{base:x} saved=0x{saved:x}\n")
    if not base or not base <= saved < base + 0x4000:
        return
    original = gdb.selected_thread()
    try:
        for cpu in gdb.selected_inferior().threads():
            cpu.switch()
            if int(gdb.parse_and_eval("$TPIDR_EL1")) == thread:
                fp = int(gdb.parse_and_eval("$x29"))
                pc = int(gdb.parse_and_eval("$pc"))
                gdb.write(f"MACVM_KERNEL_STACK pid={pid} tid={tid} origin=cpu{cpu.num} pc=0x{pc:x} "
                          f"frames={_macvm_kernel_frames(fp, base, base + 0x4000)!r}\n")
                return
    finally:
        original.switch()
    fp, lr, sp = struct.unpack("<QQQ", _macvm_read(saved + 0x50, 24))
    gdb.write(f"MACVM_KERNEL_STACK pid={pid} tid={tid} origin=saved lr=0x{_macvm_strip_data_pointer(lr):x} "
              f"sp=0x{sp:x} frames={_macvm_kernel_frames(fp, base, base + 0x4000)!r}\n")

def _macvm_probe_recovery_threads(proc, pid, name):
    selected_names = {"recoveryosd", "securityd", "WindowServer", "opendirectoryd", "systemkeychain",
                    "applekeystored", "authd", "launchd", "mountrecursive",
                    "RecoveryOS Agent", "RecoverySpringbo", "OSInstaller", "lsd", "coreservicesd"}
    if os.environ.get("MACVM_PROBE_NAMES"):
        selected_names = set(os.environ["MACVM_PROBE_NAMES"].split(","))
        if len(selected_names) > 16 or any(not n or len(n) > 16 for n in selected_names):
            raise ValueError("invalid bounded process selection")
    if name not in selected_names:
        return
    # proc_task(), current_task(), thread_tid() and get_task_map() were
    # reviewed in this exact BootKC; read only, no function calls in guest.
    proc_size = _macvm_read_u64(0xFFFFFE000A8E5B30 + KERNELCACHE_SLIDE)
    if not 0x400 <= proc_size <= 0x2000:
        raise ValueError("unexpected proc size")
    task = proc + proc_size
    vm_map = _macvm_strip_data_pointer(_macvm_read_u64(task + 0x28))
    pmap = _macvm_strip_data_pointer(_macvm_read_u64(vm_map + 0x58))
    root = _macvm_read_u64(pmap + 8)
    tcr = int(gdb.parse_and_eval("$TCR_EL1"))
    if (tcr >> 14) & 3 != 2 or 64 - (tcr & 63) != 47:
        raise ValueError("unsupported user translation regime")
    user_memory = UserMemory16K(_macvm_read_physical, root)
    gdb.write(f"MACVM_TASK_MAP pid={pid} task=0x{task:x} map=0x{vm_map:x} pmap=0x{pmap:x} ttep=0x{root:x}\n")
    head = task + 0x50
    thread = _macvm_read_u64(head)
    seen = set()
    thread_limit = int(os.environ.get("MACVM_PROBE_THREAD_LIMIT", "24"))
    if not 1 <= thread_limit <= 512:
        raise ValueError("invalid bounded thread selection")
    for _ in range(thread_limit):
        if thread == head or thread in seen or not _macvm_good_kernel_pointer(thread):
            break
        seen.add(thread)
        tro = _macvm_read_u64(thread + 0x3E8)
        if _macvm_read_u64(tro + 0x28) != task:
            raise ValueError(f"thread/task mismatch for pid={pid}")
        tid = _macvm_read_u64(thread + 0x4E0)
        _macvm_probe_kernel_stack(thread, pid, tid)
        continuation = _macvm_strip_data_pointer(_macvm_read_u64(thread + 0xD0))
        if os.environ.get("MACVM_PROBE_KERNEL_STACKS") == "YES":
            gdb.write(f"MACVM_KERNEL_THREAD pid={pid} tid={tid} thread=0x{thread:x} "
                      f"continuation=0x{continuation:x}\n")
        context = _macvm_strip_data_pointer(_macvm_read_u64(thread + 0x100))
        if context:
            header = _macvm_read_u64(context)
            fp, lr, sp, pc = struct.unpack("<QQQQ", _macvm_read(context + 0xF0, 32))
            x16 = _macvm_read_u64(context + 0x88)
            gdb.write(f"MACVM_THREAD_STATE pid={pid} name={name!r} tid={tid} thread=0x{thread:x} "
                      f"continuation=0x{continuation:x} header=0x{header:x} "
                      f"user_pc=0x{pc:x} user_lr=0x{lr:x} user_fp=0x{fp:x} user_sp=0x{sp:x} x16=0x{x16:x}\n")
            if os.environ.get("MACVM_PROBE_USER_STACKS") == "YES":
                try:
                    frames = frame_chain(user_memory, fp)
                    gdb.write(f"MACVM_USER_STACK pid={pid} tid={tid} frames=" +
                              repr([(hex(a), hex(b)) for a, b in frames]) + "\n")
                except Exception as error:
                    gdb.write(f"MACVM_USER_STACK_UNREADABLE pid={pid} tid={tid} error={error}\n")
        thread = _macvm_read_u64(thread + 0x3D8)

def _macvm_probe_allproc_names():
    kernproc_global = KERNPROC_STATIC + KERNELCACHE_SLIDE
    kernproc = _macvm_try_read_u64(kernproc_global)
    gdb.write(
        f"MACVM_ALLPROC_PROBE_BEGIN kernproc_global=0x{kernproc_global:x} "
        f"kernproc=0x{kernproc:x}\n"
    )
    if not _macvm_good_kernel_pointer(kernproc):
        gdb.write("MACVM_ALLPROC_PROBE_REFUSED invalid-kernproc\n")
        return
    # kernproc is the tail of allproc; walk LIST_ENTRY.le_prev backward.
    # Each le_prev points to the preceding proc's first (le_next) field.
    proc = kernproc
    seen = set()
    for index in range(512):
        if proc in seen or not _macvm_good_kernel_pointer(proc):
            break
        seen.add(proc)
        pid = struct.unpack("<I", _macvm_read(proc + PROC_PID_OFFSET, 4))[0]
        if pid > 999999:
            break  # reached the list head rather than another proc
        p_comm = _macvm_try_read_c_string(proc + PROC_P_COMM_OFFSET, 17)
        p_name = _macvm_try_read_c_string(proc + PROC_P_NAME_OFFSET, 64)
        if p_comm or p_name:
            gdb.write(
                f"MACVM_ALLPROC_ENTRY index={index} pid={pid} proc=0x{proc:x} "
                f"p_comm={p_comm!r} p_name={p_name!r}\n"
            )
            _macvm_probe_recovery_threads(proc, pid, p_comm)
        previous = _macvm_try_read_u64(proc + 8)
        if not _macvm_good_kernel_pointer(previous) or _macvm_try_read_u64(previous) != proc:
            break
        proc = previous
    gdb.write(f"MACVM_ALLPROC_PROBE_END count={len(seen)} next=0x{proc:x}\n")

verify_instructions(lambda addr: struct.unpack("<I", _macvm_read(addr, 4))[0], KERNELCACHE_SLIDE)
gdb.write("MACVM_LIVE_INSTRUCTION_CONTRACT_VERIFIED build=25G72\n")
_macvm_probe_allproc_names()
extra_threads = os.environ.get("MACVM_EXTRA_THREADS", "").split(",")
if len(extra_threads) > 8:
    raise ValueError("too many explicit thread snapshots")
for value in extra_threads:
    if value:
        thread = int(value, 0)
        if not _macvm_good_kernel_pointer(thread) or thread & 15:
            raise ValueError("invalid explicit thread address")
        _macvm_probe_kernel_stack(thread, -1, _macvm_read_u64(thread + 0x4E0))
if os.environ.get("MACVM_PROBE_UTIL_REGIONS") == "YES":
    from apple_device_tree import parse_device_tree, find_node
    address = int(os.environ["MACVM_DT_PHYSICAL"], 0)
    size = int(os.environ["MACVM_DT_SIZE"], 0)
    if not 0x70000000 <= address < 0x80000000 or not 4096 <= size <= 1048576:
        raise ValueError("invalid bounded DeviceTree snapshot")
    tree = parse_device_tree(_macvm_read_physical(address, size), allow_zero_padding=True)
    util = find_node(tree, "/device-tree/product/util")
    regions = util.property("regions").value
    if len(regions) > 132 or len(regions) % 12:
        raise ValueError("invalid util region entry extent")
    gdb.write("MACVM_UTIL_REGIONS raw=" + regions.hex() + " entries=" +
              repr(list(struct.iter_unpack("<III", regions))) + "\n")
end

detach
quit
