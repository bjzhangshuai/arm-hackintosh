set pagination off
set confirm off
set architecture aarch64
set print thread-events off

# Standalone mode attaches this script after MACVM_IMGSRC_STATE_APPLIED, before
# recoveryosd runs mountrecursive.  Embedded mode is sourced by the BaseSystem
# post-GDB handoff trace before its first continue, so the same breakpoints are
# already armed when XNU reaches userspace.
python
try:
    int(gdb.parse_and_eval("$macvm_symlink_embedded_trace"))
except gdb.error:
    gdb.set_convenience_variable("macvm_symlink_embedded_trace", 0)
end

if $macvm_symlink_embedded_trace == 0
  target remote 127.0.0.1:12345
end

set $macvm_kernelcache_slide = 0x19344000
set $macvm_symlink_trace_limit = 8192
set $macvm_symlink_syscall_trace_count = 0
set $macvm_symlink_focus = 0
set $macvm_symlink_focus_thread = 0
set $macvm_symlink_focus_cred = 0
set $macvm_symlink_focus_dvp = 0
set $macvm_symlink_focus_cnp = 0
set $macvm_symlink_active_index = 0
set $macvm_symlink_packageslink_context_confirmed = 0
set $macvm_symlink_vnode_authorize_hits = 0
set $macvm_symlink_vnode_authattr_hits = 0
set $macvm_symlink_altlink_hits = 0
set $macvm_symlink_vnop_hits = 0
set $macvm_symlink_apfs_hits = 0
set $macvm_symlink_apfs_return_hits = 0
set $macvm_symlink_mac_create_count = 0
set $macvm_symlink_mac_create_hits = 0
set $macvm_symlink_mac_create_hook_trace_limit = 64
set $macvm_symlink_mac_create_hook_count = 0
set $macvm_symlink_mac_create_hook_hits = 0
set $macvm_symlink_pending_policy_hook = 0
set $macvm_symlink_apfs_rofs_mount = 0
set $macvm_symlink_apfs_rofs_tx_obj = 0
set $macvm_sandbox_pending_eval = 0
set $macvm_sandbox_eval_context = 0
set $macvm_sandbox_pending_rootless = 0
set $macvm_sandbox_rootless_action_ptr = 0
set $macvm_sandbox_rootless_action_before = 0
set $macvm_allow_packageslink_symlink = 0
set $macvm_allow_packageslink_rofs_bypass = 0
set $macvm_allow_packageslink_apfs_rofs_bypass = 0
set $macvm_symlink_detach_after_packageslink = 0
set $macvm_symlink_detach_requested = 0
set $macvm_proc_p_comm_offset = 0x5cc
set $macvm_proc_p_name_offset = 0x5dd

python
import os

if os.environ.get("MACVM_ALLOW_PACKAGESLINK_SYMLINK", "").upper() in ("1", "YES", "TRUE", "ON"):
    gdb.set_convenience_variable("macvm_allow_packageslink_symlink", 1)
if os.environ.get("MACVM_ALLOW_PACKAGESLINK_ROFS_BYPASS", "").upper() in ("1", "YES", "TRUE", "ON"):
    gdb.set_convenience_variable("macvm_allow_packageslink_rofs_bypass", 1)
if os.environ.get("MACVM_ALLOW_PACKAGESLINK_APFS_ROFS_BYPASS", "").upper() in ("1", "YES", "TRUE", "ON"):
    gdb.set_convenience_variable("macvm_allow_packageslink_apfs_rofs_bypass", 1)
if os.environ.get("MACVM_DETACH_AFTER_PACKAGESLINK", "").upper() in ("1", "YES", "TRUE", "ON"):
    gdb.set_convenience_variable("macvm_symlink_detach_after_packageslink", 1)
end

set $macvm_syscall_symlink_static = 0xfffffe0009e90fc8
set $macvm_syscall_symlinkat_static = 0xfffffe0009e9147c
set $macvm_mac_create_static = 0xfffffe000a508e08
set $macvm_hook_vnode_check_create_static = 0xfffffe00096e2034
set $macvm_vnode_authorize_static = 0xfffffe0009e80594
set $macvm_vnode_authattr_new_static = 0xfffffe0009e8158c
set $macvm_proc_use_alternative_symlink_ea_static = 0xfffffe000a1e3d7c
set $macvm_vnop_symlink_primary_static = 0xfffffe000884e174
set $macvm_vnop_symlink_secondary_static = 0xfffffe0008869948
set $macvm_apfs_vnop_symlink_static = 0xfffffe00098eec34
set $macvm_apfs_vnop_symlink_rofs_branch_static = 0xfffffe00098eecf8
set $macvm_apfs_vnop_symlink_rofs_fallthrough_static = 0xfffffe00098eed20
set $macvm_apfs_vnop_symlink_return_fast_static = 0xfffffe00098eed1c
set $macvm_apfs_vnop_symlink_return_slow_static = 0xfffffe00098ef3e4
set $macvm_mac_create_policy_return_static = 0xfffffe000a508ee0
set $macvm_mac_create_cond_policy_return_static = 0xfffffe000a5090d8
set $macvm_mac_create_final_return_static = 0xfffffe000a509038
set $macvm_altlink_return_static = 0xfffffe00098ee184
set $macvm_vnode_authorize_rofs_branch_static = 0xfffffe0009e7eb4c
set $macvm_vnode_authorize_rofs_fallthrough_static = 0xfffffe0009e7e98c
set $macvm_vnode_authorize_write_extattr_return_static = 0xfffffe0009718f34
set $macvm_symlinkat_mac_create_return_static = 0xfffffe0009e911d4
set $macvm_symlinkat_vnode_authorize_return_static = 0xfffffe0009e911f8
set $macvm_symlinkat_vnop_symlink_return_static = 0xfffffe0009e9126c
set $macvm_symlinkat_common_result_static = 0xfffffe0009e913e0
set $macvm_sandbox_evaluate_internal_static = 0xfffffe00096f2a80
set $macvm_sandbox_apply_rootless_modifier_static = 0xfffffe00097188e8
set $macvm_sandbox_apply_rootless_return_static = 0xfffffe00096f2bec
set $macvm_sandbox_hook_create_eval_return_static = 0xfffffe00096e2200

set $macvm_syscall_symlink = $macvm_syscall_symlink_static + $macvm_kernelcache_slide
set $macvm_syscall_symlinkat = $macvm_syscall_symlinkat_static + $macvm_kernelcache_slide
set $macvm_mac_create = $macvm_mac_create_static + $macvm_kernelcache_slide
set $macvm_hook_vnode_check_create = $macvm_hook_vnode_check_create_static + $macvm_kernelcache_slide
set $macvm_vnode_authorize = $macvm_vnode_authorize_static + $macvm_kernelcache_slide
set $macvm_vnode_authattr_new = $macvm_vnode_authattr_new_static + $macvm_kernelcache_slide
set $macvm_proc_use_alternative_symlink_ea = $macvm_proc_use_alternative_symlink_ea_static + $macvm_kernelcache_slide
set $macvm_vnop_symlink_primary = $macvm_vnop_symlink_primary_static + $macvm_kernelcache_slide
set $macvm_vnop_symlink_secondary = $macvm_vnop_symlink_secondary_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink = $macvm_apfs_vnop_symlink_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink_rofs_branch = $macvm_apfs_vnop_symlink_rofs_branch_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink_rofs_fallthrough = $macvm_apfs_vnop_symlink_rofs_fallthrough_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink_return_fast = $macvm_apfs_vnop_symlink_return_fast_static + $macvm_kernelcache_slide
set $macvm_apfs_vnop_symlink_return_slow = $macvm_apfs_vnop_symlink_return_slow_static + $macvm_kernelcache_slide
set $macvm_mac_create_policy_return = $macvm_mac_create_policy_return_static + $macvm_kernelcache_slide
set $macvm_mac_create_cond_policy_return = $macvm_mac_create_cond_policy_return_static + $macvm_kernelcache_slide
set $macvm_mac_create_final_return = $macvm_mac_create_final_return_static + $macvm_kernelcache_slide
set $macvm_altlink_return = $macvm_altlink_return_static + $macvm_kernelcache_slide
set $macvm_vnode_authorize_rofs_branch = $macvm_vnode_authorize_rofs_branch_static + $macvm_kernelcache_slide
set $macvm_vnode_authorize_rofs_fallthrough = $macvm_vnode_authorize_rofs_fallthrough_static + $macvm_kernelcache_slide
set $macvm_vnode_authorize_write_extattr_return = $macvm_vnode_authorize_write_extattr_return_static + $macvm_kernelcache_slide
set $macvm_symlinkat_mac_create_return = $macvm_symlinkat_mac_create_return_static + $macvm_kernelcache_slide
set $macvm_symlinkat_vnode_authorize_return = $macvm_symlinkat_vnode_authorize_return_static + $macvm_kernelcache_slide
set $macvm_symlinkat_vnop_symlink_return = $macvm_symlinkat_vnop_symlink_return_static + $macvm_kernelcache_slide
set $macvm_symlinkat_common_result = $macvm_symlinkat_common_result_static + $macvm_kernelcache_slide
set $macvm_sandbox_evaluate_internal = $macvm_sandbox_evaluate_internal_static + $macvm_kernelcache_slide
set $macvm_sandbox_apply_rootless_modifier = $macvm_sandbox_apply_rootless_modifier_static + $macvm_kernelcache_slide
set $macvm_sandbox_apply_rootless_return = $macvm_sandbox_apply_rootless_return_static + $macvm_kernelcache_slide
set $macvm_sandbox_hook_create_eval_return = $macvm_sandbox_hook_create_eval_return_static + $macvm_kernelcache_slide

python
import gdb
import struct
import sys

sys.path.insert(0, "/home/macvm/src/macvm/tools")
from symlink_trace_contract import (
    is_completed_symlink, may_detach_after_result, same_transaction, verify_instructions,
)

_macvm_symlink_focus_origin = ""
_macvm_symlink_focus_name = ""
_macvm_symlink_instructions_verified = False

def _macvm_u64(expression):
    return int(gdb.parse_and_eval(expression)) & 0xFFFFFFFFFFFFFFFF

def _macvm_u32(expression):
    return int(gdb.parse_and_eval(expression)) & 0xFFFFFFFF

def _macvm_memory():
    return gdb.selected_inferior()

def _macvm_read_u32(address):
    return struct.unpack("<I", _macvm_memory().read_memory(address, 4).tobytes())[0]

def _macvm_read_u8(address):
    return struct.unpack("<B", _macvm_memory().read_memory(address, 1).tobytes())[0]

def _macvm_read_u64(address):
    return struct.unpack("<Q", _macvm_memory().read_memory(address, 8).tobytes())[0]

def _macvm_try_read_u8(address):
    try:
        return _macvm_read_u8(address)
    except Exception:
        return None

def _macvm_try_read_u32(address):
    try:
        return _macvm_read_u32(address)
    except Exception:
        return None

def _macvm_try_read_u64(address):
    try:
        return _macvm_read_u64(address)
    except Exception:
        return None

def _macvm_read_bytes(address, length):
    return _macvm_memory().read_memory(address, length).tobytes()

def _macvm_try_read_c_string(address, limit=512):
    if not address:
        return "<null>"
    try:
        data = _macvm_read_bytes(address, limit)
        return data.split(b"\0", 1)[0].decode("utf-8", errors="replace")
    except Exception as error:
        return f"<unreadable:{error}>"

def _macvm_read_proc_identity(proc):
    p_comm = _macvm_try_read_c_string(proc + _macvm_conv_int("macvm_proc_p_comm_offset"), 17)
    p_name = _macvm_try_read_c_string(proc + _macvm_conv_int("macvm_proc_p_name_offset"), 64)
    best = p_name if p_name and not p_name.startswith("<") else p_comm
    return p_comm, p_name, best

def _macvm_is_target_symlink_process(process_name):
    targets = (
        "mountrecursive",
        "recoveryosd",
        "OSInstaller",
        "InstallAssistant",
        "startosinstall",
    )
    return any(name in process_name for name in targets)

def _macvm_read_component_name(cnp):
    if not cnp:
        return "<null>"
    name_pointer = _macvm_try_read_u64(cnp + 0x28)
    name_length = _macvm_try_read_u32(cnp + 0x30)
    if not name_pointer or name_length is None:
        return "<unreadable>"
    try:
        return _macvm_read_bytes(name_pointer, min(name_length, 256)).decode(
            "utf-8", errors="replace"
        )
    except Exception as error:
        return f"<unreadable:{error}>"

def _macvm_conv_int(name):
    return int(gdb.parse_and_eval(f"${name}"))

def _macvm_set_conv(name, value):
    gdb.set_convenience_variable(name, int(value))

def _macvm_inc_conv(name):
    value = _macvm_conv_int(name) + 1
    _macvm_set_conv(name, value)
    return value

def _macvm_bp_number(name):
    return _macvm_conv_int(name)

def _macvm_current_thread_global_num():
    thread = gdb.selected_thread()
    if thread is None:
        return 0
    return int(getattr(thread, "global_num", None) or getattr(thread, "num", 0) or 0)

def _macvm_focus_thread_matches():
    focus_thread = _macvm_conv_int("macvm_symlink_focus_thread")
    return focus_thread == 0 or focus_thread == _macvm_current_thread_global_num()

def _macvm_ctx_cred(ctx):
    if not ctx:
        return 0
    return _macvm_try_read_u64(ctx + 8) or 0

def _macvm_focus_cred_matches(cred):
    focus_cred = _macvm_conv_int("macvm_symlink_focus_cred")
    return focus_cred == 0 or cred == 0 or focus_cred == cred

def _macvm_toggle_breakpoints(names, enabled):
    command = "enable" if enabled else "disable"
    for name in names:
        try:
            gdb.execute(f"{command} {_macvm_bp_number(name)}", to_string=True)
        except Exception as error:
            gdb.write(f"MACVM_SYMLINK_BREAKPOINT_TOGGLE_FAILED name={name} error={error}\n")

def _macvm_focus_breakpoint_names():
    return (
        "macvm_bp_hook_vnode_check_create",
        "macvm_bp_mac_create_policy_return",
        "macvm_bp_mac_create_cond_policy_return",
        "macvm_bp_mac_create_final_return",
        "macvm_bp_sandbox_evaluate_internal",
        "macvm_bp_sandbox_apply_rootless_modifier",
        "macvm_bp_sandbox_apply_rootless_return",
        "macvm_bp_sandbox_hook_create_eval_return",
        "macvm_bp_symlinkat_mac_create_return",
        "macvm_bp_symlinkat_vnode_authorize_return",
        "macvm_bp_symlinkat_vnop_symlink_return",
        "macvm_bp_symlinkat_common_result",
    )

def _macvm_optional_breakpoint_names():
    return (
        "macvm_bp_vnode_authorize",
        "macvm_bp_vnode_authattr_new",
        "macvm_bp_proc_use_alternative_symlink_ea",
        "macvm_bp_altlink_return",
        "macvm_bp_vnode_authorize_rofs_branch",
        "macvm_bp_vnode_authorize_write_extattr_return",
        "macvm_bp_vnop_symlink_primary",
        "macvm_bp_vnop_symlink_secondary",
        "macvm_bp_apfs_vnop_symlink",
        "macvm_bp_apfs_vnop_symlink_rofs_branch",
        "macvm_bp_apfs_vnop_symlink_return_fast",
        "macvm_bp_apfs_vnop_symlink_return_slow",
    )

def _macvm_set_focus_breakpoints(enabled):
    _macvm_toggle_breakpoints(_macvm_focus_breakpoint_names(), enabled)
    _macvm_toggle_breakpoints(_macvm_optional_breakpoint_names(), enabled)
    gdb.write(
        f"MACVM_SYMLINK_FOCUS_BREAKPOINTS {'ENABLED' if enabled else 'DISABLED'} "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"thread={_macvm_conv_int('macvm_symlink_focus_thread')} "
        f"cred=0x{_macvm_conv_int('macvm_symlink_focus_cred'):x}\n"
    )

def _macvm_reset_focus_counters():
    for name in (
        "macvm_symlink_vnode_authorize_hits",
        "macvm_symlink_vnode_authattr_hits",
        "macvm_symlink_altlink_hits",
        "macvm_symlink_vnop_hits",
        "macvm_symlink_apfs_hits",
        "macvm_symlink_apfs_return_hits",
        "macvm_symlink_pending_policy_hook",
        "macvm_symlink_packageslink_context_confirmed",
        "macvm_symlink_apfs_rofs_mount",
        "macvm_symlink_apfs_rofs_tx_obj",
        "macvm_sandbox_pending_eval",
        "macvm_sandbox_eval_context",
        "macvm_sandbox_pending_rootless",
        "macvm_sandbox_rootless_action_ptr",
        "macvm_sandbox_rootless_action_before",
    ):
        _macvm_set_conv(name, 0)

def _macvm_start_focus(origin, active_index, name, cred=0, dvp=0, cnp=0):
    global _macvm_symlink_focus_origin, _macvm_symlink_focus_name
    global _macvm_symlink_instructions_verified
    if not _macvm_symlink_instructions_verified:
        try:
            verify_instructions(_macvm_read_u32, _macvm_conv_int("macvm_kernelcache_slide"))
        except Exception as error:
            gdb.write(f"MACVM_SYMLINK_INSTRUCTION_CONTRACT_REFUSED {error}\n")
            raise
        _macvm_symlink_instructions_verified = True
        gdb.write("MACVM_SYMLINK_INSTRUCTION_CONTRACT_VERIFIED build=25G72\n")
    _macvm_reset_focus_counters()
    _macvm_symlink_focus_origin = origin
    _macvm_symlink_focus_name = name
    _macvm_set_conv("macvm_symlink_active_index", active_index)
    _macvm_set_conv("macvm_symlink_focus", 1)
    _macvm_set_conv("macvm_symlink_focus_thread", _macvm_current_thread_global_num())
    _macvm_set_conv("macvm_symlink_focus_cred", cred)
    _macvm_set_conv("macvm_symlink_focus_dvp", dvp)
    _macvm_set_conv("macvm_symlink_focus_cnp", cnp)
    gdb.write(
        f"MACVM_SYMLINK_FOCUS_START origin={origin} "
        f"index={active_index} thread={_macvm_current_thread_global_num()} "
        f"cred=0x{cred:x} name={name!r}\n"
    )
    _macvm_set_focus_breakpoints(True)

def _macvm_clear_focus(reason):
    global _macvm_symlink_focus_origin, _macvm_symlink_focus_name
    if _macvm_conv_int("macvm_symlink_focus") != 0:
        gdb.write(
            f"MACVM_SYMLINK_FOCUS_CLEAR reason={reason} "
            f"origin={_macvm_symlink_focus_origin} "
            f"index={_macvm_conv_int('macvm_symlink_active_index')} "
            f"thread={_macvm_conv_int('macvm_symlink_focus_thread')} "
            f"cred=0x{_macvm_conv_int('macvm_symlink_focus_cred'):x} "
            f"name={_macvm_symlink_focus_name!r}\n"
        )
    _macvm_set_focus_breakpoints(False)
    _macvm_set_conv("macvm_symlink_focus", 0)
    _macvm_set_conv("macvm_symlink_focus_thread", 0)
    _macvm_set_conv("macvm_symlink_focus_cred", 0)
    _macvm_set_conv("macvm_symlink_focus_dvp", 0)
    _macvm_set_conv("macvm_symlink_focus_cnp", 0)
    _macvm_set_conv("macvm_symlink_active_index", 0)
    _macvm_set_conv("macvm_symlink_pending_policy_hook", 0)
    _macvm_set_conv("macvm_symlink_packageslink_context_confirmed", 0)
    _macvm_set_conv("macvm_symlink_apfs_rofs_mount", 0)
    _macvm_set_conv("macvm_symlink_apfs_rofs_tx_obj", 0)
    _macvm_set_conv("macvm_sandbox_pending_eval", 0)
    _macvm_set_conv("macvm_sandbox_eval_context", 0)
    _macvm_set_conv("macvm_sandbox_pending_rootless", 0)
    _macvm_set_conv("macvm_sandbox_rootless_action_ptr", 0)
    _macvm_set_conv("macvm_sandbox_rootless_action_before", 0)
    _macvm_symlink_focus_origin = ""
    _macvm_symlink_focus_name = ""

def _macvm_request_detach_after_packageslink(reason):
    if _macvm_conv_int("macvm_symlink_detach_after_packageslink") == 0:
        return
    if _macvm_conv_int("macvm_symlink_detach_requested") != 0:
        return
    _macvm_set_conv("macvm_symlink_detach_requested", 1)
    gdb.write(
        "MACVM_SYMLINK_DETACH_AFTER_PACKAGESLINK "
        f"reason={reason!r} "
        f"origin={_macvm_symlink_focus_origin!r} "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')} "
        f"name={_macvm_symlink_focus_name!r}\n"
    )

def _macvm_mark_packageslink_context_confirmed(reason):
    if "PackagesLink" not in _macvm_symlink_focus_name:
        return
    if _macvm_conv_int("macvm_symlink_packageslink_context_confirmed") != 0:
        return
    _macvm_set_conv("macvm_symlink_packageslink_context_confirmed", 1)
    gdb.write(
        "MACVM_SYMLINK_PACKAGESLINK_CONTEXT_CONFIRMED "
        f"reason={reason!r} "
        f"origin={_macvm_symlink_focus_origin!r} "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')} "
        f"name={_macvm_symlink_focus_name!r}\n"
    )

def _macvm_log_ignored_focus(marker, reason, detail=""):
    gdb.write(
        f"MACVM_SYMLINK_FOCUS_IGNORED marker={marker} reason={reason} "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')} "
        f"focus_cred=0x{_macvm_conv_int('macvm_symlink_focus_cred'):x}"
        f"{detail}\n"
    )

def _macvm_decode_symlink_args(kind):
    proc = _macvm_u64("$x0")
    uap = _macvm_u64("$x1")
    target_ptr = _macvm_try_read_u64(uap)
    link_ptr = _macvm_try_read_u64(uap + 8)
    fd = None
    link_ptr_aligned = None
    link_ptr_packed = None
    if kind == "symlinkat":
        fd = _macvm_try_read_u32(uap + 8)
        link_ptr_aligned = _macvm_try_read_u64(uap + 16)
        link_ptr_packed = _macvm_try_read_u64(uap + 12)
        link_ptr = link_ptr_aligned if link_ptr_aligned else link_ptr_packed
    return {
        "proc": proc,
        "uap": uap,
        "target_ptr": target_ptr or 0,
        "link_ptr": link_ptr or 0,
        "fd": fd,
        "link_ptr_aligned": link_ptr_aligned,
        "link_ptr_packed": link_ptr_packed,
    }

def _macvm_begin_symlink_syscall(kind):
    index = _macvm_inc_conv("macvm_symlink_syscall_trace_count")
    focus_was_active = _macvm_conv_int("macvm_symlink_focus") != 0
    if not focus_was_active:
        _macvm_reset_focus_counters()
        _macvm_set_conv("macvm_symlink_active_index", index)
    fields = _macvm_decode_symlink_args(kind)
    p_comm, p_name, process_name = _macvm_read_proc_identity(fields["proc"])
    process_focus = _macvm_is_target_symlink_process(process_name)
    path_probe = process_focus or index <= _macvm_conv_int("macvm_symlink_trace_limit")
    target = _macvm_try_read_c_string(fields["target_ptr"]) if path_probe else "<skipped>"
    link = _macvm_try_read_c_string(fields["link_ptr"]) if path_probe else "<skipped>"
    focus = 1 if (
        "PackagesLink" in link
        or "Image Volume/Packages" in target
    ) else 0
    if focus:
        _macvm_start_focus("syscall", index, link if "PackagesLink" in link else target, 0)
    should_log = focus or index <= _macvm_conv_int("macvm_symlink_trace_limit")
    if not should_log:
        return
    details = (
        f"MACVM_SYMLINK_SYSCALL_ENTER kind={kind} index={index} "
        f"pc=0x{_macvm_u64('$pc'):x} proc=0x{fields['proc']:x} "
        f"lr=0x{_macvm_u64('$x30'):x} "
        f"p_comm={p_comm!r} p_name={p_name!r} "
        f"uap=0x{fields['uap']:x} target_ptr=0x{fields['target_ptr']:x} "
        f"link_ptr=0x{fields['link_ptr']:x} target={target!r} link={link!r} "
        f"focus={focus}"
    )
    if kind == "symlinkat":
        details += (
            f" fd={fields['fd']} "
            f"link_ptr_aligned={fields['link_ptr_aligned']} "
            f"link_ptr_packed={fields['link_ptr_packed']}"
        )
    gdb.write(details + "\n")

def _macvm_trace_mac_create_entry():
    index = _macvm_inc_conv("macvm_symlink_mac_create_count")
    ctx = _macvm_u64("$x0")
    cnp = _macvm_u64("$x2")
    name = _macvm_read_component_name(cnp)
    focus = 1 if "PackagesLink" in name else 0
    cred = _macvm_ctx_cred(ctx)
    if focus:
        hit = _macvm_inc_conv("macvm_symlink_mac_create_hits")
        _macvm_start_focus("mac-create", 2000000 + hit, name, cred, _macvm_u64("$x1"), cnp)
    should_log = focus or index <= _macvm_conv_int("macvm_symlink_mac_create_hook_trace_limit")
    if not should_log:
        return
    gdb.write(
        f"MACVM_SYMLINK_MAC_CREATE_ENTER index={index} "
        f"pc=0x{_macvm_u64('$pc'):x} caller_return=0x{_macvm_u64('$x30'):x} "
        f"ctx=0x{ctx:x} cred=0x{cred:x} dvp=0x{_macvm_u64('$x1'):x} "
        f"cnp=0x{cnp:x} vap=0x{_macvm_u64('$x3'):x} "
        f"name={name!r} focus={focus}\n"
    )

def _macvm_trace_mac_create_hook():
    index = _macvm_inc_conv("macvm_symlink_mac_create_hook_count")
    cred = _macvm_u64("$x0")
    cnp = _macvm_u64("$x3")
    name = _macvm_read_component_name(cnp)
    focus = 1 if "PackagesLink" in name else 0
    if focus and _macvm_conv_int("macvm_symlink_focus") == 0:
        hook_hits = _macvm_inc_conv("macvm_symlink_mac_create_hook_hits")
        _macvm_start_focus("mac-policy-hook", 1000000 + hook_hits, name, cred, _macvm_u64("$x1"), cnp)
    if _macvm_conv_int("macvm_symlink_focus") != 0:
        if not _macvm_focus_cred_matches(cred):
            _macvm_log_ignored_focus(
                "MACVM_SYMLINK_MAC_CREATE_HOOK_ENTER",
                "cred-mismatch",
                f" cred=0x{cred:x}",
            )
            return
        _macvm_set_conv("macvm_symlink_pending_policy_hook", _macvm_conv_int("macvm_symlink_active_index"))
        focus = 1
    should_log = focus or index <= _macvm_conv_int("macvm_symlink_mac_create_hook_trace_limit")
    if not should_log:
        return
    gdb.write(
        f"MACVM_SYMLINK_MAC_CREATE_HOOK_ENTER hook_index={index} "
        f"pc=0x{_macvm_u64('$pc'):x} cred=0x{cred:x} "
        f"lr=0x{_macvm_u64('$x30'):x} "
        f"dvp=0x{_macvm_u64('$x1'):x} dlabel=0x{_macvm_u64('$x2'):x} "
        f"cnp=0x{cnp:x} vap=0x{_macvm_u64('$x4'):x} "
        f"name={name!r} focus={focus}\n"
    )

def _macvm_kauth_vnode_action_names(action):
    names = []
    for bit, name in (
        (1 << 1, "READ_DATA"),
        (1 << 2, "WRITE_DATA/ADD_FILE"),
        (1 << 3, "EXECUTE/SEARCH"),
        (1 << 4, "DELETE"),
        (1 << 5, "APPEND_DATA/ADD_SUBDIRECTORY"),
        (1 << 6, "DELETE_CHILD"),
        (1 << 7, "READ_ATTRIBUTES"),
        (1 << 8, "WRITE_ATTRIBUTES"),
        (1 << 9, "READ_EXTATTRIBUTES"),
        (1 << 10, "WRITE_EXTATTRIBUTES"),
        (1 << 11, "READ_SECURITY"),
        (1 << 12, "WRITE_SECURITY"),
        (1 << 13, "TAKE_OWNERSHIP"),
        (1 << 20, "SYNCHRONIZE"),
        (1 << 25, "LINKTARGET"),
        (1 << 26, "CHECKIMMUTABLE"),
        (1 << 30, "NOIMMUTABLE"),
        (1 << 31, "ACCESS"),
    ):
        if action & bit:
            names.append(name)
    return "|".join(names) if names else "0"

def _macvm_vnode_summary(vp):
    if not vp:
        return "vp=0x0"
    v_type = _macvm_try_read_u8(vp + 0x71)
    v_flag = _macvm_try_read_u32(vp + 0x54)
    v_name_ptr = _macvm_try_read_u64(vp + 0xB8)
    v_name = _macvm_try_read_c_string(v_name_ptr, 128) if v_name_ptr else "<null>"
    mount = _macvm_try_read_u64(vp + 0xD8) or 0
    mnt_flag = _macvm_try_read_u32(mount + 0x70) if mount else None
    mnt_kern_flag = _macvm_try_read_u32(mount + 0x74) if mount else None
    return (
        f"vp=0x{vp:x} v_type={v_type if v_type is not None else -1} "
        f"v_flag=0x{v_flag if v_flag is not None else 0:x} "
        f"v_name={v_name!r} v_mount_raw=0x{mount:x} "
        f"mnt_flag=0x{mnt_flag if mnt_flag is not None else 0:x} "
        f"mnt_rdonly={1 if (mnt_flag is not None and (mnt_flag & 1)) else 0} "
        f"mnt_kern_flag=0x{mnt_kern_flag if mnt_kern_flag is not None else 0:x}"
    )

def _macvm_trace_authorize(marker):
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    if (
        marker not in (
            "MACVM_SYMLINK_VNODE_AUTHORIZE_ENTER",
            "MACVM_SYMLINK_VNODE_AUTHATTR_ENTER",
        )
        and not _macvm_focus_thread_matches()
    ):
        _macvm_log_ignored_focus(marker, "thread-mismatch")
        return
    process = ""
    if marker == "MACVM_SYMLINK_VNODE_AUTHORIZE_ENTER":
        _macvm_inc_conv("macvm_symlink_vnode_authorize_hits")
        action = _macvm_u64("$x2")
        ctx = _macvm_u64("$x3")
        ctx_cred = _macvm_ctx_cred(ctx)
        if not _macvm_focus_cred_matches(ctx_cred):
            _macvm_log_ignored_focus(
                marker,
                "cred-mismatch",
                f" ctx=0x{ctx:x} ctx_cred=0x{ctx_cred:x}",
            )
            return
        process = (
            f" action={_macvm_kauth_vnode_action_names(action)} "
            f"ctx_cred=0x{ctx_cred:x} {_macvm_vnode_summary(_macvm_u64('$x0'))}"
        )
    elif marker == "MACVM_SYMLINK_VNODE_AUTHATTR_ENTER":
        _macvm_inc_conv("macvm_symlink_vnode_authattr_hits")
        ctx = _macvm_u64("$x3")
        ctx_cred = _macvm_ctx_cred(ctx)
        if not _macvm_focus_cred_matches(ctx_cred):
            _macvm_log_ignored_focus(
                marker,
                "cred-mismatch",
                f" ctx=0x{ctx:x} ctx_cred=0x{ctx_cred:x}",
            )
            return
        process = (
            f" ctx_cred=0x{ctx_cred:x} "
            f"{_macvm_vnode_summary(_macvm_u64('$x0'))}"
        )
    elif marker == "MACVM_SYMLINK_ALTLINK_ENTER":
        _macvm_inc_conv("macvm_symlink_altlink_hits")
        p_comm, p_name, process_name = _macvm_read_proc_identity(_macvm_u64("$x0"))
        if not _macvm_is_target_symlink_process(process_name):
            _macvm_log_ignored_focus(
                marker,
                "process-mismatch",
                f" p_comm={p_comm!r} p_name={p_name!r}",
            )
            return
        process = f" p_comm={p_comm!r} p_name={p_name!r}"
    gdb.write(
        f"{marker} index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} x0=0x{_macvm_u64('$x0'):x} "
        f"lr=0x{_macvm_u64('$x30'):x} "
        f"x1=0x{_macvm_u64('$x1'):x} x2=0x{_macvm_u64('$x2'):x} "
        f"x3=0x{_macvm_u64('$x3'):x}{process}\n"
    )

def _macvm_trace_vnode_authorize_rofs_branch():
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    ctx = _macvm_u64("$x22")
    ctx_cred = _macvm_ctx_cred(ctx)
    if not _macvm_focus_cred_matches(ctx_cred):
        _macvm_log_ignored_focus(
            "MACVM_SYMLINK_VNODE_AUTHORIZE_ROFS_BRANCH",
            "cred-mismatch",
            f" ctx=0x{ctx:x} ctx_cred=0x{ctx_cred:x}",
        )
        return
    vp = _macvm_u64("$x20")
    action = _macvm_u64("$x21")
    mount = _macvm_u64("$x16")
    pc = _macvm_u64("$pc")
    resume_pc = pc
    mnt_flag = _macvm_try_read_u32(mount + 0x70) if mount else None
    mnt_kern_flag = _macvm_try_read_u32(mount + 0x74) if mount else None
    v_type = _macvm_try_read_u8(vp + 0x71)
    v_name_ptr = _macvm_try_read_u64(vp + 0xB8)
    v_name = _macvm_try_read_c_string(v_name_ptr, 128) if v_name_ptr else ""
    allow_enabled = _macvm_conv_int("macvm_allow_packageslink_rofs_bypass") != 0
    allow_applied = 0
    allow_reason = "disabled"
    new_mnt_flag = mnt_flag
    if allow_enabled:
        if "PackagesLink" not in _macvm_symlink_focus_name:
            allow_reason = "focus-name-mismatch"
        elif _macvm_conv_int("macvm_symlink_packageslink_context_confirmed") == 0:
            allow_reason = "packageslink-context-not-confirmed"
        elif vp != _macvm_conv_int("macvm_symlink_focus_dvp"):
            allow_reason = "parent-vnode-mismatch"
        elif (action & 0x4) == 0:
            allow_reason = "action-mismatch"
        elif v_type != 2:
            allow_reason = "vtype-mismatch"
        elif mnt_flag is None or (mnt_flag & 1) == 0:
            allow_reason = "mnt-rdonly-absent"
        else:
            allow_reason = "packageslink-focused-mnt-rdonly"
            new_mnt_flag = mnt_flag & ~1
            _macvm_memory().write_memory(mount + 0x70, struct.pack("<I", new_mnt_flag))
            if _macvm_read_u32(mount + 0x70) != new_mnt_flag:
                raise RuntimeError("PackagesLink ROFS bypass mnt_flag write did not persist")
            gdb.execute(
                f"set $pc = 0x{_macvm_conv_int('macvm_vnode_authorize_rofs_fallthrough'):x}",
                to_string=True,
            )
            resume_pc = _macvm_conv_int("macvm_vnode_authorize_rofs_fallthrough")
            allow_applied = 1
    gdb.write(
        "MACVM_SYMLINK_VNODE_AUTHORIZE_ROFS_BRANCH "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{pc:x} resume_pc=0x{resume_pc:x} vp=0x{vp:x} "
        f"ctx=0x{ctx:x} ctx_cred=0x{ctx_cred:x} "
        f"action={_macvm_kauth_vnode_action_names(action)} "
        f"authenticated_mount=0x{mount:x} "
        f"mnt_flag=0x{mnt_flag if mnt_flag is not None else 0:x} "
        f"mnt_rdonly={1 if (mnt_flag is not None and (mnt_flag & 1)) else 0} "
        f"new_mnt_flag=0x{new_mnt_flag if new_mnt_flag is not None else 0:x} "
        f"mnt_kern_flag=0x{mnt_kern_flag if mnt_kern_flag is not None else 0:x} "
        f"context_confirmed={_macvm_conv_int('macvm_symlink_packageslink_context_confirmed')} "
        f"focus_name={_macvm_symlink_focus_name!r} "
        f"allow_enabled={1 if allow_enabled else 0} "
        f"allow_applied={allow_applied} allow_reason={allow_reason!r} "
        f"{_macvm_vnode_summary(vp)}\n"
    )

def _macvm_wait_for_packageslink_final_result():
    return (os.environ.get("MACVM_DETACH_AFTER_PACKAGESLINK_RESULT") == "YES"
            and "PackagesLink" in _macvm_symlink_focus_name)

def _macvm_trace_static_return(marker, *, result_is_errno=True, reset_always=False):
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    thread_mismatch = not _macvm_focus_thread_matches()
    if thread_mismatch and marker != "MACVM_SYMLINK_MAC_CREATE_POLICY_RETURN":
        _macvm_log_ignored_focus(marker, "thread-mismatch")
        return
    if marker == "MACVM_SYMLINK_MAC_CREATE_POLICY_RETURN":
        if _macvm_conv_int("macvm_symlink_pending_policy_hook") != _macvm_conv_int("macvm_symlink_active_index"):
            _macvm_log_ignored_focus(marker, "no-pending-policy-hook")
            return
        _macvm_set_conv("macvm_symlink_pending_policy_hook", 0)
    result = _macvm_u32("$w0")
    gdb.write(
        f"{marker} index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} result={result} "
        f"x0=0x{_macvm_u64('$x0'):x} lr=0x{_macvm_u64('$x30'):x} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )
    if (reset_always or (result_is_errno and result != 0)) and not _macvm_wait_for_packageslink_final_result():
        _macvm_clear_focus(f"{marker}:result={result}")

def _macvm_trace_symlinkat_checkpoint(marker, *, clear_on_error=False, clear_always=False):
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    # QEMU GDB threads are vCPUs, not Darwin threads. Bind this return to
    # the parent vnode and nameidata component captured at MAC create.
    matches = same_transaction(
        _macvm_u64("$x23"), _macvm_u64("$x26") + 0x150,
        _macvm_conv_int("macvm_symlink_focus_dvp"),
        _macvm_conv_int("macvm_symlink_focus_cnp"),
    )
    if not matches:
        _macvm_log_ignored_focus(marker, "transaction-mismatch")
        return
    result = _macvm_u32("$w0")
    gdb.write(
        f"{marker} index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} result={result} "
        f"x0=0x{_macvm_u64('$x0'):x} x21=0x{_macvm_u64('$x21'):x} "
        f"x23=0x{_macvm_u64('$x23'):x} x24=0x{_macvm_u64('$x24'):x} "
        f"lr=0x{_macvm_u64('$x30'):x} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )
    if (
        may_detach_after_result(marker, result, matches,
            include_failure=os.environ.get("MACVM_DETACH_AFTER_PACKAGESLINK_RESULT") == "YES")
        and "PackagesLink" in _macvm_symlink_focus_name
    ):
        gdb.write(f"MACVM_SYMLINK_PACKAGESLINK_FINAL success={int(is_completed_symlink(marker, result, matches))} errno={result}\n")
        _macvm_request_detach_after_packageslink(f"{marker}:result={result}")
    if clear_always or (clear_on_error and result != 0 and not _macvm_wait_for_packageslink_final_result()):
        _macvm_clear_focus(f"{marker}:result={result}")

def _macvm_sandbox_op_name(op):
    return {
        0x14: "file-mknod",
        0x22: "file-write-create",
    }.get(op, f"op-0x{op:x}")

def _macvm_packageslink_allow_enabled():
    return _macvm_conv_int("macvm_allow_packageslink_symlink") != 0

def _macvm_sandbox_context_is_packageslink_symlink_create(context):
    if not context:
        return False, "context-null"
    kind = _macvm_try_read_u32(context)
    va_type = _macvm_try_read_u32(context + 0x170)
    name_pointer = _macvm_try_read_u64(context + 0xD0)
    name = _macvm_try_read_c_string(name_pointer, 256) if name_pointer else "<null>"
    if kind != 1:
        return False, f"kind={kind}"
    if va_type != 5:
        return False, f"va_type={va_type}"
    if name != "PackagesLink":
        return False, f"name={name!r}"
    if "PackagesLink" not in _macvm_symlink_focus_name:
        return False, f"focus_name={_macvm_symlink_focus_name!r}"
    return True, "packageslink-vlnk"

def _macvm_policy_summary(mpc):
    if not mpc:
        return "mpc=0x0 policy_name='<null>' policy_fullname='<null>' policy_ops=0x0"
    name_pointer = _macvm_try_read_u64(mpc)
    fullname_pointer = _macvm_try_read_u64(mpc + 0x8)
    ops = _macvm_try_read_u64(mpc + 0x20) or 0
    name = _macvm_try_read_c_string(name_pointer, 128) if name_pointer else "<null>"
    fullname = _macvm_try_read_c_string(fullname_pointer, 192) if fullname_pointer else "<null>"
    return (
        f"mpc=0x{mpc:x} policy_name={name!r} "
        f"policy_fullname={fullname!r} policy_ops=0x{ops:x}"
    )

def _macvm_mac_create_call_summary():
    cred = _macvm_u64("$x22")
    dvp = _macvm_u64("$x21")
    cnp = _macvm_u64("$x20")
    vap = _macvm_u64("$x19")
    name = _macvm_read_component_name(cnp)
    va_type = _macvm_try_read_u32(vap + 0xE0) if vap else None
    return cred, dvp, cnp, vap, name, va_type

def _macvm_mac_create_step_is_packageslink():
    cred, dvp, cnp, vap, name, va_type = _macvm_mac_create_call_summary()
    if "PackagesLink" not in _macvm_symlink_focus_name:
        return False, "focus-name-mismatch"
    if name != "PackagesLink":
        return False, f"name={name!r}"
    if va_type != 5:
        return False, f"va_type={va_type}"
    if not _macvm_focus_cred_matches(cred):
        return False, f"cred-mismatch:0x{cred:x}"
    return True, "packageslink-mac-create"

def _macvm_trace_mac_create_policy_step_return(stage):
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    if stage == "static":
        mpc = _macvm_u64("$x24")
        aggregate_before = _macvm_u32("$w23")
        policy_index = _macvm_u64("$x25")
    else:
        mpc = _macvm_u64("$x23")
        aggregate_before = _macvm_u32("$w26")
        policy_index = _macvm_u32("$w25")
    hook = _macvm_u64("$x27")
    result = _macvm_u32("$w0")
    original_x0 = _macvm_u64("$x0")
    cred, dvp, cnp, vap, name, va_type = _macvm_mac_create_call_summary()
    allow_enabled = _macvm_packageslink_allow_enabled()
    allow_applied = 0
    allow_reason = "disabled"
    if allow_enabled:
        should_allow, allow_reason = _macvm_mac_create_step_is_packageslink()
        if should_allow:
            _macvm_mark_packageslink_context_confirmed(allow_reason)
        if result != 0 and should_allow:
            gdb.execute("set $x0 = 0", to_string=True)
            result = _macvm_u32("$w0")
            allow_applied = 1
            gdb.write(
                "MACVM_SYMLINK_MAC_CREATE_POLICY_ALLOW_APPLIED "
                f"index={_macvm_conv_int('macvm_symlink_active_index')} "
                f"stage={stage} pc=0x{_macvm_u64('$pc'):x} "
                f"original_result={original_x0 & 0xffffffff} "
                f"original_x0=0x{original_x0:x} aggregate_before={aggregate_before} "
                f"reason={allow_reason!r} {_macvm_policy_summary(mpc)} "
                f"hook=0x{hook:x} policy_index={policy_index} "
                f"cred=0x{cred:x} dvp=0x{dvp:x} cnp=0x{cnp:x} vap=0x{vap:x} "
                f"name={name!r} va_type={va_type if va_type is not None else -1}\n"
            )
    gdb.write(
        "MACVM_SYMLINK_MAC_CREATE_POLICY_RETURN "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"stage={stage} pc=0x{_macvm_u64('$pc'):x} result={result} "
        f"x0=0x{_macvm_u64('$x0'):x} original_x0=0x{original_x0:x} "
        f"aggregate_before={aggregate_before} "
        f"allow_enabled={1 if allow_enabled else 0} allow_applied={allow_applied} "
        f"allow_reason={allow_reason!r} {_macvm_policy_summary(mpc)} "
        f"hook=0x{hook:x} policy_index={policy_index} "
        f"cred=0x{cred:x} dvp=0x{dvp:x} cnp=0x{cnp:x} vap=0x{vap:x} "
        f"name={name!r} va_type={va_type if va_type is not None else -1} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )

def _macvm_trace_mac_create_final_return():
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    result = _macvm_u32("$w23")
    original_x23 = _macvm_u64("$x23")
    cred, dvp, cnp, vap, name, va_type = _macvm_mac_create_call_summary()
    allow_enabled = _macvm_packageslink_allow_enabled()
    allow_applied = 0
    allow_reason = "disabled"
    if allow_enabled:
        should_allow, allow_reason = _macvm_mac_create_step_is_packageslink()
        if should_allow:
            _macvm_mark_packageslink_context_confirmed(allow_reason)
        if result != 0 and should_allow:
            gdb.execute("set $x23 = 0", to_string=True)
            result = _macvm_u32("$w23")
            allow_applied = 1
            gdb.write(
                "MACVM_SYMLINK_MAC_CREATE_FINAL_ALLOW_APPLIED "
                f"index={_macvm_conv_int('macvm_symlink_active_index')} "
                f"pc=0x{_macvm_u64('$pc'):x} original_result={original_x23 & 0xffffffff} "
                f"original_x23=0x{original_x23:x} reason={allow_reason!r} "
                f"cred=0x{cred:x} dvp=0x{dvp:x} cnp=0x{cnp:x} vap=0x{vap:x} "
                f"name={name!r} va_type={va_type if va_type is not None else -1}\n"
            )
    gdb.write(
        "MACVM_SYMLINK_MAC_CREATE_FINAL_RETURN "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} result={result} "
        f"x23=0x{_macvm_u64('$x23'):x} original_x23=0x{original_x23:x} "
        f"allow_enabled={1 if allow_enabled else 0} allow_applied={allow_applied} "
        f"allow_reason={allow_reason!r} "
        f"cred=0x{cred:x} dvp=0x{dvp:x} cnp=0x{cnp:x} vap=0x{vap:x} "
        f"name={name!r} va_type={va_type if va_type is not None else -1} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )

def _macvm_filter_context_summary(context):
    kind = _macvm_try_read_u32(context)
    flags = _macvm_try_read_u32(context + 4)
    cred = _macvm_try_read_u64(context + 0x18)
    dvp = _macvm_try_read_u64(context + 0xC8)
    name_pointer = _macvm_try_read_u64(context + 0xD0)
    va_type = _macvm_try_read_u32(context + 0x170)
    name = _macvm_try_read_c_string(name_pointer, 256) if name_pointer else "<null>"
    return (
        f"context=0x{context:x} kind={kind if kind is not None else -1} "
        f"flags=0x{flags if flags is not None else 0:x} "
        f"cred=0x{cred if cred is not None else 0:x} "
        f"dvp=0x{dvp if dvp is not None else 0:x} "
        f"name_ptr=0x{name_pointer if name_pointer is not None else 0:x} "
        f"name={name!r} va_type={va_type if va_type is not None else -1}"
    )

def _macvm_trace_sandbox_eval_enter():
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    op = _macvm_u32("$w1")
    context = _macvm_u64("$x2")
    if op != 0x22:
        _macvm_log_ignored_focus(
            "MACVM_SYMLINK_SANDBOX_EVAL_ENTER",
            "operation-mismatch",
            f" op=0x{op:x} op_name={_macvm_sandbox_op_name(op)}",
        )
        return
    should_track, context_reason = _macvm_sandbox_context_is_packageslink_symlink_create(context)
    if not should_track:
        _macvm_log_ignored_focus(
            "MACVM_SYMLINK_SANDBOX_EVAL_ENTER",
            "context-mismatch",
            f" reason={context_reason!r} {_macvm_filter_context_summary(context)}",
        )
        return
    _macvm_mark_packageslink_context_confirmed(context_reason)
    _macvm_set_conv("macvm_sandbox_pending_eval", _macvm_conv_int("macvm_symlink_active_index"))
    _macvm_set_conv("macvm_sandbox_eval_context", context)
    gdb.write(
        f"MACVM_SYMLINK_SANDBOX_EVAL_ENTER "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} sandbox=0x{_macvm_u64('$x0'):x} "
        f"op=0x{op:x} op_name={_macvm_sandbox_op_name(op)} "
        f"context_reason={context_reason!r} "
        f"{_macvm_filter_context_summary(context)} "
        f"callback_context=0x{_macvm_u64('$x3'):x} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )

def _macvm_trace_sandbox_rootless_enter():
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    if _macvm_conv_int("macvm_sandbox_pending_eval") != _macvm_conv_int("macvm_symlink_active_index"):
        _macvm_log_ignored_focus("MACVM_SYMLINK_ROOTLESS_MODIFIER_ENTER", "no-pending-sandbox-eval")
        return
    op = _macvm_u32("$w0")
    if op != 0x22:
        _macvm_log_ignored_focus(
            "MACVM_SYMLINK_ROOTLESS_MODIFIER_ENTER",
            "operation-mismatch",
            f" op=0x{op:x} op_name={_macvm_sandbox_op_name(op)}",
        )
        return
    action_ptr = _macvm_u64("$x2")
    action_before = _macvm_try_read_u64(action_ptr) or 0
    _macvm_set_conv("macvm_sandbox_pending_rootless", _macvm_conv_int("macvm_symlink_active_index"))
    _macvm_set_conv("macvm_sandbox_rootless_action_ptr", action_ptr)
    _macvm_set_conv("macvm_sandbox_rootless_action_before", action_before)
    gdb.write(
        f"MACVM_SYMLINK_ROOTLESS_MODIFIER_ENTER "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} op=0x{op:x} op_name={_macvm_sandbox_op_name(op)} "
        f"context=0x{_macvm_u64('$x1'):x} action_ptr=0x{action_ptr:x} "
        f"action_before=0x{action_before:x} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )

def _macvm_trace_sandbox_rootless_return():
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    if _macvm_conv_int("macvm_sandbox_pending_rootless") != _macvm_conv_int("macvm_symlink_active_index"):
        _macvm_log_ignored_focus("MACVM_SYMLINK_ROOTLESS_MODIFIER_RETURN", "no-pending-rootless")
        return
    action_ptr = _macvm_conv_int("macvm_sandbox_rootless_action_ptr")
    action_before = _macvm_conv_int("macvm_sandbox_rootless_action_before")
    action_after = _macvm_try_read_u64(action_ptr) or 0
    gdb.write(
        f"MACVM_SYMLINK_ROOTLESS_MODIFIER_RETURN "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} action_ptr=0x{action_ptr:x} "
        f"action_before=0x{action_before:x} action_after=0x{action_after:x} "
        f"changed={1 if action_before != action_after else 0} "
        f"x0=0x{_macvm_u64('$x0'):x} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )
    _macvm_set_conv("macvm_sandbox_pending_rootless", 0)
    _macvm_set_conv("macvm_sandbox_rootless_action_ptr", 0)
    _macvm_set_conv("macvm_sandbox_rootless_action_before", 0)

def _macvm_trace_sandbox_eval_result():
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    if _macvm_conv_int("macvm_sandbox_pending_eval") != _macvm_conv_int("macvm_symlink_active_index"):
        _macvm_log_ignored_focus("MACVM_SYMLINK_SANDBOX_EVAL_RETURN", "no-pending-sandbox-eval")
        return
    result = _macvm_u32("$w0")
    original_x0 = _macvm_u64("$x0")
    context = _macvm_conv_int("macvm_sandbox_eval_context")
    summary = _macvm_filter_context_summary(context) if context else "context=0x0"
    allow_enabled = _macvm_packageslink_allow_enabled()
    allow_applied = 0
    allow_reason = "disabled"
    if result != 0 and allow_enabled:
        should_allow, allow_reason = _macvm_sandbox_context_is_packageslink_symlink_create(context)
        if should_allow:
            _macvm_mark_packageslink_context_confirmed(allow_reason)
            gdb.execute("set $x0 = 0", to_string=True)
            result = _macvm_u32("$w0")
            allow_applied = 1
            gdb.write(
                f"MACVM_SYMLINK_PACKAGESLINK_ALLOW_APPLIED "
                f"index={_macvm_conv_int('macvm_symlink_active_index')} "
                f"pc=0x{_macvm_u64('$pc'):x} original_result={original_x0 & 0xffffffff} "
                f"original_x0=0x{original_x0:x} reason={allow_reason!r} {summary}\n"
            )
    gdb.write(
        f"MACVM_SYMLINK_SANDBOX_EVAL_RETURN "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} result={result} "
        f"x0=0x{_macvm_u64('$x0'):x} original_x0=0x{original_x0:x} "
        f"allow_enabled={1 if allow_enabled else 0} allow_applied={allow_applied} "
        f"allow_reason={allow_reason!r} {summary} "
        f"thread={_macvm_current_thread_global_num()} "
        f"focus_thread={_macvm_conv_int('macvm_symlink_focus_thread')}\n"
    )
    _macvm_set_conv("macvm_sandbox_pending_eval", 0)
    _macvm_set_conv("macvm_sandbox_eval_context", 0)

def _macvm_return_marker_for_vnop(marker):
    return {
        "MACVM_SYMLINK_VNOP_PRIMARY_ENTER": "MACVM_SYMLINK_VNOP_PRIMARY_RETURN",
        "MACVM_SYMLINK_VNOP_SECONDARY_ENTER": "MACVM_SYMLINK_VNOP_SECONDARY_RETURN",
        "MACVM_SYMLINK_APFS_ENTER": "MACVM_SYMLINK_APFS_RETURN",
    }[marker]

def _macvm_emit_vnop_symlink_trace(marker):
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    if not _macvm_focus_thread_matches():
        _macvm_log_ignored_focus(marker, "thread-mismatch")
        return
    if marker.startswith("MACVM_SYMLINK_APFS_"):
        _macvm_inc_conv("macvm_symlink_apfs_hits")
    else:
        _macvm_inc_conv("macvm_symlink_vnop_hits")
    try:
        args = _macvm_u64("$x0")
        dvp = _macvm_read_u64(args + 0x08)
        vpp = _macvm_read_u64(args + 0x10)
        cnp = _macvm_read_u64(args + 0x18)
        vap = _macvm_read_u64(args + 0x20)
        target_pointer = _macvm_read_u64(args + 0x28)
        name = _macvm_read_component_name(cnp)
        target = _macvm_try_read_c_string(target_pointer)
        gdb.write(
            f"{marker} index={_macvm_conv_int('macvm_symlink_active_index')} "
            f"pc=0x{_macvm_u64('$pc'):x} args=0x{args:x} "
            f"lr=0x{_macvm_u64('$x30'):x} "
            f"dvp=0x{dvp:x} vpp=0x{vpp:x} cnp=0x{cnp:x} vap=0x{vap:x} "
            f"name={name!r} target={target!r}\n"
        )
    except Exception as error:
        gdb.write(
            f"{marker} index={_macvm_conv_int('macvm_symlink_active_index')} "
            f"decode-failed {error}\n"
        )

def _macvm_decode_vnop_symlink_args(args):
    dvp = _macvm_read_u64(args + 0x08)
    vpp = _macvm_read_u64(args + 0x10)
    cnp = _macvm_read_u64(args + 0x18)
    vap = _macvm_read_u64(args + 0x20)
    target_pointer = _macvm_read_u64(args + 0x28)
    return {
        "args": args,
        "dvp": dvp,
        "vpp": vpp,
        "cnp": cnp,
        "vap": vap,
        "target_pointer": target_pointer,
        "name": _macvm_read_component_name(cnp),
        "target": _macvm_try_read_c_string(target_pointer),
    }

def _macvm_trace_apfs_rofs_branch():
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    pc = _macvm_u64("$pc")
    resume_pc = pc
    allow_enabled = _macvm_conv_int("macvm_allow_packageslink_apfs_rofs_bypass") != 0
    allow_applied = 0
    allow_reason = "disabled"
    args = _macvm_u64("$x19")
    apfs_mount = _macvm_u64("$x20")
    apfs_node = _macvm_u64("$x21")
    apfs_mount_ro = _macvm_try_read_u32(apfs_mount + 0x35c) if apfs_mount else None
    tx_obj = _macvm_try_read_u64(apfs_mount + 0xD0) if apfs_mount else None
    tx_ro_byte = _macvm_try_read_u8(tx_obj + 0x15B) if tx_obj else None
    apfs_node_flags = _macvm_try_read_u8(apfs_node + 0x9d) if apfs_node else None
    new_apfs_mount_ro = apfs_mount_ro
    new_tx_ro_byte = tx_ro_byte
    new_apfs_node_flags = apfs_node_flags
    try:
        decoded = _macvm_decode_vnop_symlink_args(args)
    except Exception as error:
        decoded = {
            "args": args,
            "dvp": 0,
            "vpp": 0,
            "cnp": 0,
            "vap": 0,
            "target_pointer": 0,
            "name": f"<decode-failed:{error}>",
            "target": "<decode-failed>",
        }
    rofs_present = (
        (apfs_mount_ro is not None and apfs_mount_ro != 0)
        or (tx_ro_byte is not None and (tx_ro_byte & 0x1) != 0)
        or (apfs_node_flags is not None and (apfs_node_flags & 0xC0) != 0)
    )
    if allow_enabled:
        if "PackagesLink" not in _macvm_symlink_focus_name:
            allow_reason = "focus-name-mismatch"
        elif decoded["name"] != "PackagesLink":
            allow_reason = "component-name-mismatch"
        elif "Image Volume/Packages" not in decoded["target"]:
            allow_reason = "target-mismatch"
        elif not rofs_present:
            allow_reason = "apfs-rofs-condition-absent"
        else:
            allow_reason = "packageslink-apfs-rofs-state-cleared"
            if apfs_mount_ro is not None and apfs_mount_ro != 0:
                new_apfs_mount_ro = 0
                _macvm_memory().write_memory(
                    apfs_mount + 0x35c, struct.pack("<I", new_apfs_mount_ro)
                )
                if _macvm_read_u32(apfs_mount + 0x35c) != new_apfs_mount_ro:
                    raise RuntimeError("PackagesLink APFS mount RO write did not persist")
            if tx_ro_byte is not None and (tx_ro_byte & 0x1) != 0:
                new_tx_ro_byte = tx_ro_byte & ~0x1
                _macvm_memory().write_memory(
                    tx_obj + 0x15B, struct.pack("<B", new_tx_ro_byte)
                )
                if _macvm_read_u8(tx_obj + 0x15B) != new_tx_ro_byte:
                    raise RuntimeError("PackagesLink APFS tx RO write did not persist")
            if apfs_node_flags is not None and (apfs_node_flags & 0xC0) != 0:
                new_apfs_node_flags = apfs_node_flags & ~0xC0
                _macvm_memory().write_memory(
                    apfs_node + 0x9d, struct.pack("<B", new_apfs_node_flags)
                )
                if _macvm_read_u8(apfs_node + 0x9d) != new_apfs_node_flags:
                    raise RuntimeError("PackagesLink APFS node flags write did not persist")
            _macvm_set_conv("macvm_symlink_apfs_rofs_mount", apfs_mount)
            _macvm_set_conv("macvm_symlink_apfs_rofs_tx_obj", tx_obj or 0)
            gdb.execute(
                f"set $pc = 0x{_macvm_conv_int('macvm_apfs_vnop_symlink_rofs_fallthrough'):x}",
                to_string=True,
            )
            resume_pc = _macvm_conv_int("macvm_apfs_vnop_symlink_rofs_fallthrough")
            allow_applied = 1
    gdb.write(
        "MACVM_SYMLINK_APFS_ROFS_BRANCH "
        f"index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{pc:x} resume_pc=0x{resume_pc:x} "
        f"allow_enabled={1 if allow_enabled else 0} "
        f"allow_applied={allow_applied} allow_reason={allow_reason!r} "
        f"args=0x{decoded['args']:x} dvp=0x{decoded['dvp']:x} "
        f"vpp=0x{decoded['vpp']:x} cnp=0x{decoded['cnp']:x} "
        f"vap=0x{decoded['vap']:x} target_pointer=0x{decoded['target_pointer']:x} "
        f"name={decoded['name']!r} target={decoded['target']!r} "
        f"apfs_mount=0x{apfs_mount:x} "
        f"apfs_mount_ro=0x{apfs_mount_ro if apfs_mount_ro is not None else 0:x} "
        f"new_apfs_mount_ro=0x{new_apfs_mount_ro if new_apfs_mount_ro is not None else 0:x} "
        f"tx_obj=0x{tx_obj if tx_obj is not None else 0:x} "
        f"tx_ro_byte=0x{tx_ro_byte if tx_ro_byte is not None else 0:x} "
        f"new_tx_ro_byte=0x{new_tx_ro_byte if new_tx_ro_byte is not None else 0:x} "
        f"apfs_node=0x{apfs_node:x} "
        f"apfs_node_flags=0x{apfs_node_flags if apfs_node_flags is not None else 0:x} "
        f"new_apfs_node_flags=0x{new_apfs_node_flags if new_apfs_node_flags is not None else 0:x} "
        f"rofs_present={1 if rofs_present else 0}\n"
    )

def _macvm_emit_apfs_return(marker):
    if _macvm_conv_int("macvm_symlink_focus") == 0:
        return
    if not _macvm_focus_thread_matches():
        _macvm_log_ignored_focus(marker, "thread-mismatch")
        return
    _macvm_inc_conv("macvm_symlink_apfs_return_hits")
    gdb.write(
        f"{marker} index={_macvm_conv_int('macvm_symlink_active_index')} "
        f"pc=0x{_macvm_u64('$pc'):x} result={_macvm_u32('$w0')} "
        f"x0=0x{_macvm_u64('$x0'):x}\n"
    )
end

hbreak *$macvm_syscall_symlink
set $macvm_bp_syscall_symlink = $bpnum
commands
  silent
  python _macvm_begin_symlink_syscall("symlink")
  continue
end

hbreak *$macvm_syscall_symlinkat
set $macvm_bp_syscall_symlinkat = $bpnum
commands
  silent
  python _macvm_begin_symlink_syscall("symlinkat")
  continue
end

hbreak *$macvm_mac_create
set $macvm_bp_mac_create = $bpnum
commands
  silent
  python _macvm_trace_mac_create_entry()
  continue
end

hbreak *$macvm_hook_vnode_check_create
set $macvm_bp_hook_vnode_check_create = $bpnum
commands
  silent
  python _macvm_trace_mac_create_hook()
  continue
end

hbreak *$macvm_vnode_authorize
set $macvm_bp_vnode_authorize = $bpnum
commands
  silent
  python _macvm_trace_authorize("MACVM_SYMLINK_VNODE_AUTHORIZE_ENTER")
  continue
end

hbreak *$macvm_vnode_authattr_new
set $macvm_bp_vnode_authattr_new = $bpnum
commands
  silent
  python _macvm_trace_authorize("MACVM_SYMLINK_VNODE_AUTHATTR_ENTER")
  continue
end

hbreak *$macvm_vnode_authorize_rofs_branch
set $macvm_bp_vnode_authorize_rofs_branch = $bpnum
commands
  silent
  python _macvm_trace_vnode_authorize_rofs_branch()
  continue
end

hbreak *$macvm_proc_use_alternative_symlink_ea
set $macvm_bp_proc_use_alternative_symlink_ea = $bpnum
commands
  silent
  python _macvm_trace_authorize("MACVM_SYMLINK_ALTLINK_ENTER")
  continue
end

hbreak *$macvm_mac_create_policy_return
set $macvm_bp_mac_create_policy_return = $bpnum
commands
  silent
  python _macvm_trace_mac_create_policy_step_return("static")
  continue
end

hbreak *$macvm_mac_create_cond_policy_return
set $macvm_bp_mac_create_cond_policy_return = $bpnum
commands
  silent
  python _macvm_trace_mac_create_policy_step_return("conditional")
  continue
end

hbreak *$macvm_mac_create_final_return
set $macvm_bp_mac_create_final_return = $bpnum
commands
  silent
  python _macvm_trace_mac_create_final_return()
  continue
end

hbreak *$macvm_sandbox_evaluate_internal
set $macvm_bp_sandbox_evaluate_internal = $bpnum
commands
  silent
  python _macvm_trace_sandbox_eval_enter()
  continue
end

hbreak *$macvm_sandbox_apply_rootless_modifier
set $macvm_bp_sandbox_apply_rootless_modifier = $bpnum
commands
  silent
  python _macvm_trace_sandbox_rootless_enter()
  continue
end

hbreak *$macvm_sandbox_apply_rootless_return
set $macvm_bp_sandbox_apply_rootless_return = $bpnum
commands
  silent
  python _macvm_trace_sandbox_rootless_return()
  continue
end

hbreak *$macvm_sandbox_hook_create_eval_return
set $macvm_bp_sandbox_hook_create_eval_return = $bpnum
commands
  silent
  python _macvm_trace_sandbox_eval_result()
  continue
end

hbreak *$macvm_altlink_return
set $macvm_bp_altlink_return = $bpnum
commands
  silent
  python _macvm_trace_static_return("MACVM_SYMLINK_ALTLINK_RETURN", result_is_errno=False)
  continue
end

hbreak *$macvm_vnode_authorize_write_extattr_return
set $macvm_bp_vnode_authorize_write_extattr_return = $bpnum
commands
  silent
  python _macvm_trace_static_return("MACVM_SYMLINK_VNODE_AUTHORIZE_WRITE_EXTATTR_RETURN", result_is_errno=True)
  continue
end

hbreak *$macvm_symlinkat_mac_create_return
set $macvm_bp_symlinkat_mac_create_return = $bpnum
commands
  silent
  python _macvm_trace_symlinkat_checkpoint("MACVM_SYMLINK_SYMLINKAT_MAC_CREATE_RETURN", clear_on_error=True)
  continue
end

hbreak *$macvm_symlinkat_vnode_authorize_return
set $macvm_bp_symlinkat_vnode_authorize_return = $bpnum
commands
  silent
  python _macvm_trace_symlinkat_checkpoint("MACVM_SYMLINK_SYMLINKAT_VNODE_AUTHORIZE_RETURN", clear_on_error=True)
  continue
end

hbreak *$macvm_symlinkat_vnop_symlink_return
set $macvm_bp_symlinkat_vnop_symlink_return = $bpnum
commands
  silent
  python _macvm_trace_symlinkat_checkpoint("MACVM_SYMLINK_SYMLINKAT_VNOP_SYMLINK_RETURN", clear_on_error=True)
  if $macvm_symlink_detach_requested != 0
    detach
    quit
  end
  continue
end

hbreak *$macvm_symlinkat_common_result
set $macvm_bp_symlinkat_common_result = $bpnum
commands
  silent
  python _macvm_trace_symlinkat_checkpoint("MACVM_SYMLINK_SYMLINKAT_COMMON_RESULT", clear_always=True)
  if $macvm_symlink_detach_requested != 0
    detach
    quit
  end
  continue
end

hbreak *$macvm_vnop_symlink_primary
set $macvm_bp_vnop_symlink_primary = $bpnum
commands
  silent
  python _macvm_emit_vnop_symlink_trace("MACVM_SYMLINK_VNOP_PRIMARY_ENTER")
  continue
end

hbreak *$macvm_vnop_symlink_secondary
set $macvm_bp_vnop_symlink_secondary = $bpnum
commands
  silent
  python _macvm_emit_vnop_symlink_trace("MACVM_SYMLINK_VNOP_SECONDARY_ENTER")
  continue
end

hbreak *$macvm_apfs_vnop_symlink
set $macvm_bp_apfs_vnop_symlink = $bpnum
commands
  silent
  python _macvm_emit_vnop_symlink_trace("MACVM_SYMLINK_APFS_ENTER")
  continue
end

hbreak *$macvm_apfs_vnop_symlink_rofs_branch
set $macvm_bp_apfs_vnop_symlink_rofs_branch = $bpnum
commands
  silent
  python _macvm_trace_apfs_rofs_branch()
  if $macvm_symlink_detach_requested != 0
    detach
    quit
  end
  continue
end

hbreak *$macvm_apfs_vnop_symlink_return_fast
set $macvm_bp_apfs_vnop_symlink_return_fast = $bpnum
commands
  silent
  python _macvm_emit_apfs_return("MACVM_SYMLINK_APFS_RETURN_FAST")
  continue
end

hbreak *$macvm_apfs_vnop_symlink_return_slow
set $macvm_bp_apfs_vnop_symlink_return_slow = $bpnum
commands
  silent
  python _macvm_emit_apfs_return("MACVM_SYMLINK_APFS_RETURN_SLOW")
  continue
end

python _macvm_toggle_breakpoints(_macvm_optional_breakpoint_names(), False)
python _macvm_set_focus_breakpoints(False)
printf "MACVM_SYMLINK_PREFLIGHT_TRACE_ARMED symlink=%#lx symlinkat=%#lx mac_create=%#lx policy_hook=%#lx mac_policy_return=%#lx mac_cond_policy_return=%#lx mac_final_return=%#lx sandbox_eval=%#lx rootless_modifier=%#lx rootless_return=%#lx hook_eval_return=%#lx symlinkat_mac_return=%#lx symlinkat_authorize_return=%#lx symlinkat_vnop_return=%#lx symlinkat_common=%#lx apfs_rofs_branch=%#lx apfs_rofs_fallthrough=%#lx\n", $macvm_syscall_symlink, $macvm_syscall_symlinkat, $macvm_mac_create, $macvm_hook_vnode_check_create, $macvm_mac_create_policy_return, $macvm_mac_create_cond_policy_return, $macvm_mac_create_final_return, $macvm_sandbox_evaluate_internal, $macvm_sandbox_apply_rootless_modifier, $macvm_sandbox_apply_rootless_return, $macvm_sandbox_hook_create_eval_return, $macvm_symlinkat_mac_create_return, $macvm_symlinkat_vnode_authorize_return, $macvm_symlinkat_vnop_symlink_return, $macvm_symlinkat_common_result, $macvm_apfs_vnop_symlink_rofs_branch, $macvm_apfs_vnop_symlink_rofs_fallthrough
if $macvm_symlink_embedded_trace == 0
  continue
end
