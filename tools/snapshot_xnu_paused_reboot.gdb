set pagination off
set confirm off
set architecture aarch64

# Used only with MACVM_PAUSE_ON_REBOOT=YES.  QEMU converts the guest reboot
# request into a paused shutdown action, preserving the requesting vCPU and
# guest memory.  This script is read-only and snapshots every vCPU because a
# secondary CPU, rather than CPU0, may be the panic/reboot initiator.

target remote 127.0.0.1:12345

printf "XNU_PAUSED_REBOOT_SELECTED pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x29=0x%lx x30=0x%lx sp=0x%lx cpsr=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x29, $x30, $sp, $cpsr
printf "XNU_PAUSED_REBOOT_THREADS\n"
info threads
printf "XNU_PAUSED_REBOOT_REGISTERS\n"
thread apply all info registers x0 x1 x2 x3 x4 x5 x6 x7 x8 x16 x17 x19 x20 x21 x22 x23 x24 x25 x26 x27 x28 x29 x30 sp pc cpsr

# QEMU's reboot=pause action leaves the requesting vCPU with the PSCI
# function ID in x0.  Select that thread before reading stack memory so an
# unrelated vCPU's near-page-boundary stack cannot abort the snapshot.
python
import gdb

gdb.set_convenience_variable("xnu_reboot_thread_found", 0)
for xnu_thread in gdb.selected_inferior().threads():
    xnu_thread.switch()
    try:
        xnu_function_id = int(gdb.parse_and_eval("$x0"))
    except gdb.error:
        continue
    if xnu_function_id == 0x84000009:
        gdb.set_convenience_variable("xnu_reboot_thread_found", 1)
        xnu_pc = int(gdb.parse_and_eval("$pc")) & 0xFFFFFFFFFFFFFFFF
        xnu_x29 = int(gdb.parse_and_eval("$x29")) & 0xFFFFFFFFFFFFFFFF
        xnu_x30 = int(gdb.parse_and_eval("$x30")) & 0xFFFFFFFFFFFFFFFF
        xnu_sp = int(gdb.parse_and_eval("$sp")) & 0xFFFFFFFFFFFFFFFF
        gdb.write(
            "XNU_PAUSED_REBOOT_REQUESTER thread=%d x0=0x%x pc=0x%x "
            "x29=0x%x x30=0x%x sp=0x%x\n"
            % (
                xnu_thread.num,
                xnu_function_id,
                xnu_pc,
                xnu_x29,
                xnu_x30,
                xnu_sp,
            )
        )
        break
end

if $xnu_reboot_thread_found == 1
  printf "XNU_PAUSED_REBOOT_REQUESTER_REGISTERS\n"
  info registers
  printf "XNU_PAUSED_REBOOT_EXCEPTION_REGISTERS esr_el1=0x%lx elr_el1=0x%lx far_el1=0x%lx\n", $ESR_EL1, $ELR_EL1, $FAR_EL1
  printf "XNU_PAUSED_REBOOT_FAULT_INSTRUCTION\n"
  x/wx $ELR_EL1
  printf "XNU_PAUSED_REBOOT_FAULT_DISASM\n"
  x/96i $ELR_EL1-0x80
  printf "XNU_PAUSED_REBOOT_CALLER_DISASM\n"
  x/256i 0xfffffe0021beee00
  printf "XNU_PAUSED_REBOOT_FRAME1_DISASM\n"
  x/192i 0xfffffe002311b700
  printf "XNU_PAUSED_REBOOT_BACKTRACES\n"
  bt
  printf "XNU_PAUSED_REBOOT_STACK_WORDS\n"
  x/64gx $sp
  printf "XNU_PAUSED_REBOOT_STACK_CHARS\n"
  x/512cb $sp
  printf "XNU_PAUSED_REBOOT_SAVED_STATE_X22_WORDS\n"
  x/96gx $x22
  printf "XNU_PAUSED_REBOOT_SAVED_STATE_X22_DWORDS\n"
  x/192wx $x22
  printf "XNU_PAUSED_REBOOT_DEBUGGER_STATE\n"
  python
import gdb
import struct

xnu_debugger_state = int(gdb.parse_and_eval("$x27")) & 0xFFFFFFFFFFFFFFFF
try:
    xnu_debugger_raw = bytes(gdb.selected_inferior().read_memory(xnu_debugger_state, 72))
    xnu_debugger_fields = struct.unpack("<9Q", xnu_debugger_raw)
    (
        xnu_panic_options,
        xnu_op_and_sync,
        xnu_message_ptr,
        xnu_panic_str_ptr,
        xnu_panic_args_ptr,
        xnu_panic_data_ptr,
        xnu_panic_caller,
        xnu_panic_initiator_ptr,
        xnu_count_and_return,
    ) = xnu_debugger_fields
    xnu_panic_format = ""
    if xnu_panic_str_ptr:
        xnu_panic_format_raw = bytes(
            gdb.selected_inferior().read_memory(xnu_panic_str_ptr, 1024)
        )
        xnu_panic_format = (
            xnu_panic_format_raw.split(b"\0", 1)[0].decode("utf-8", "replace")
        )
    gdb.write(
        "XNU_PAUSED_REBOOT_DEBUGGER_FIELDS base=0x%x options=0x%x "
        "op_sync=0x%x message=0x%x panic_str=0x%x args=0x%x data=0x%x "
        "caller=0x%x initiator=0x%x count_return=0x%x\n"
        % (
            xnu_debugger_state,
            xnu_panic_options,
            xnu_op_and_sync,
            xnu_message_ptr,
            xnu_panic_str_ptr,
            xnu_panic_args_ptr,
            xnu_panic_data_ptr,
            xnu_panic_caller,
            xnu_panic_initiator_ptr,
            xnu_count_and_return,
        )
    )
    for xnu_label, xnu_string_ptr in (
        ("MESSAGE", xnu_message_ptr),
        ("PANIC_STRING", xnu_panic_str_ptr),
        ("INITIATOR", xnu_panic_initiator_ptr),
    ):
        if xnu_string_ptr:
            gdb.write("XNU_PAUSED_REBOOT_DEBUGGER_%s\n" % xnu_label)
            try:
                gdb.execute("x/s 0x%x" % xnu_string_ptr)
            except gdb.error as xnu_string_error:
                gdb.write("XNU_PAUSED_REBOOT_DEBUGGER_%s_ERROR %s\n" % (xnu_label, xnu_string_error))
    if xnu_panic_args_ptr:
        gdb.write("XNU_PAUSED_REBOOT_DEBUGGER_ARGS\n")
        try:
            gdb.execute("x/24gx 0x%x" % xnu_panic_args_ptr)
        except gdb.error as xnu_args_error:
            gdb.write("XNU_PAUSED_REBOOT_DEBUGGER_ARGS_ERROR %s\n" % xnu_args_error)
        if xnu_panic_format.startswith("Undefined kernel instruction:"):
            try:
                # osfmk's panic varargs save area starts 24 bytes after the
                # debugger_state pointer recorded above.  For the undefined-
                # instruction panic, argument 0 is the original fault PC and
                # argument 1 is the 32-bit instruction word.
                xnu_panic_arg_raw = bytes(
                    gdb.selected_inferior().read_memory(
                        xnu_panic_args_ptr + 24, 32
                    )
                )
                (
                    xnu_original_pc,
                    xnu_original_instruction,
                    xnu_original_file,
                    xnu_original_line,
                ) = struct.unpack("<4Q", xnu_panic_arg_raw)
                gdb.write(
                    "XNU_PAUSED_REBOOT_ORIGINAL_UNDEFINED pc=0x%x instr=0x%x "
                    "file=0x%x line=%d\n"
                    % (
                        xnu_original_pc,
                        xnu_original_instruction,
                        xnu_original_file,
                        xnu_original_line,
                    )
                )
                if xnu_original_pc >= 0xFFFF000000000000:
                    gdb.write("XNU_PAUSED_REBOOT_ORIGINAL_UNDEFINED_DISASM\n")
                    gdb.execute("x/128i 0x%x" % (xnu_original_pc - 0x100))
                if xnu_original_file:
                    gdb.write("XNU_PAUSED_REBOOT_ORIGINAL_UNDEFINED_FILE\n")
                    gdb.execute("x/s 0x%x" % xnu_original_file)
            except (gdb.error, struct.error) as xnu_original_error:
                gdb.write(
                    "XNU_PAUSED_REBOOT_ORIGINAL_UNDEFINED_ERROR %s\n"
                    % xnu_original_error
                )
        elif "implementation specific error" in xnu_panic_format:
            try:
                xnu_impl_arg_raw = bytes(
                    gdb.selected_inferior().read_memory(
                        xnu_panic_args_ptr + 24, 72
                    )
                )
                (
                    xnu_saved_state_ptr,
                    xnu_panic_esr,
                    xnu_panic_far,
                    xnu_lsu_err_sts,
                    xnu_fed_err_sts,
                    xnu_mmu_err_sts,
                    xnu_llc_err_sts,
                    xnu_llc_err_adr,
                    xnu_llc_err_inf,
                ) = struct.unpack("<9Q", xnu_impl_arg_raw)
                xnu_saved_state_raw = bytes(
                    gdb.selected_inferior().read_memory(xnu_saved_state_ptr, 304)
                )
                xnu_state_flavor, xnu_state_count = struct.unpack_from(
                    "<II", xnu_saved_state_raw, 0
                )
                xnu_state_gprs = struct.unpack_from("<29Q", xnu_saved_state_raw, 8)
                (
                    xnu_state_fp,
                    xnu_state_lr,
                    xnu_state_sp,
                    xnu_state_pc,
                ) = struct.unpack_from("<4Q", xnu_saved_state_raw, 240)
                xnu_state_cpsr, _ = struct.unpack_from(
                    "<II", xnu_saved_state_raw, 272
                )
                xnu_state_far, xnu_state_esr = struct.unpack_from(
                    "<2Q", xnu_saved_state_raw, 280
                )
                gdb.write(
                    "XNU_PAUSED_REBOOT_IMPL_ERROR state=0x%x flavor=%d count=%d "
                    "panic_esr=0x%x panic_far=0x%x state_pc=0x%x "
                    "state_cpsr=0x%x state_far=0x%x state_esr=0x%x\n"
                    % (
                        xnu_saved_state_ptr,
                        xnu_state_flavor,
                        xnu_state_count,
                        xnu_panic_esr,
                        xnu_panic_far,
                        xnu_state_pc,
                        xnu_state_cpsr,
                        xnu_state_far,
                        xnu_state_esr,
                    )
                )
                gdb.write(
                    "XNU_PAUSED_REBOOT_IMPL_ERROR_STATUS "
                    "lsu=0x%x fed=0x%x mmu=0x%x llc_sts=0x%x "
                    "llc_adr=0x%x llc_inf=0x%x\n"
                    % (
                        xnu_lsu_err_sts,
                        xnu_fed_err_sts,
                        xnu_mmu_err_sts,
                        xnu_llc_err_sts,
                        xnu_llc_err_adr,
                        xnu_llc_err_inf,
                    )
                )
                for xnu_gpr_start in range(0, 29, 8):
                    xnu_gpr_values = xnu_state_gprs[
                        xnu_gpr_start : xnu_gpr_start + 8
                    ]
                    gdb.write(
                        "XNU_PAUSED_REBOOT_IMPL_ERROR_GPRS "
                        + " ".join(
                            "x%d=0x%x" % (xnu_gpr_start + xnu_offset, xnu_value)
                            for xnu_offset, xnu_value in enumerate(xnu_gpr_values)
                        )
                        + "\n"
                    )
                gdb.write(
                    "XNU_PAUSED_REBOOT_IMPL_ERROR_FRAME fp=0x%x lr=0x%x sp=0x%x\n"
                    % (xnu_state_fp, xnu_state_lr, xnu_state_sp)
                )
                gdb.write("XNU_PAUSED_REBOOT_IMPL_ERROR_GVA_TO_GPA\n")
                try:
                    gdb.execute("monitor gva2gpa 0x%x" % xnu_state_far)
                except gdb.error as xnu_gva_error:
                    gdb.write(
                        "XNU_PAUSED_REBOOT_IMPL_ERROR_GVA_TO_GPA_ERROR %s\n"
                        % xnu_gva_error
                    )
                if xnu_state_pc >= 0xFFFF000000000000:
                    gdb.write("XNU_PAUSED_REBOOT_IMPL_ERROR_PC_DISASM\n")
                    gdb.execute("x/128i 0x%x" % (xnu_state_pc - 0x100))
                gdb.write("XNU_PAUSED_REBOOT_IMPL_ERROR_STATE_WORDS\n")
                gdb.execute("x/40gx 0x%x" % xnu_saved_state_ptr)
            except (gdb.error, struct.error) as xnu_impl_error:
                gdb.write(
                    "XNU_PAUSED_REBOOT_IMPL_ERROR_DECODE_ERROR %s\n"
                    % xnu_impl_error
                )
        else:
            gdb.write(
                "XNU_PAUSED_REBOOT_UNRECOGNIZED_PANIC_FORMAT %s\n"
                % xnu_panic_format
            )
    if xnu_panic_data_ptr >= 0xFFFF000000000000:
        gdb.write("XNU_PAUSED_REBOOT_DEBUGGER_DATA\n")
        try:
            gdb.execute("x/64gx 0x%x" % xnu_panic_data_ptr)
        except gdb.error as xnu_data_error:
            gdb.write("XNU_PAUSED_REBOOT_DEBUGGER_DATA_ERROR %s\n" % xnu_data_error)
except gdb.error as xnu_debugger_error:
    gdb.write("XNU_PAUSED_REBOOT_DEBUGGER_STATE_ERROR base=0x%x error=%s\n" % (xnu_debugger_state, xnu_debugger_error))
end
  printf "XNU_PAUSED_REBOOT_FRAME_POINTERS\n"
  python
import gdb

xnu_fp = int(gdb.parse_and_eval("$x29")) & 0xFFFFFFFFFFFFFFFF
for xnu_index in range(16):
    if xnu_fp < 0xFFFF000000000000:
        break
    try:
        xnu_next_fp = int(gdb.parse_and_eval("*(unsigned long long *)0x%x" % xnu_fp)) & 0xFFFFFFFFFFFFFFFF
        xnu_saved_lr = int(gdb.parse_and_eval("*(unsigned long long *)0x%x" % (xnu_fp + 8))) & 0xFFFFFFFFFFFFFFFF
    except gdb.error as xnu_error:
        gdb.write("XNU_PAUSED_REBOOT_FRAME_READ_ERROR index=%d fp=0x%x error=%s\n" % (xnu_index, xnu_fp, xnu_error))
        break
    xnu_canonical_lr = 0xFFFF000000000000 | (xnu_saved_lr & 0x0000FFFFFFFFFFFF)
    gdb.write(
        "XNU_PAUSED_REBOOT_FRAME index=%d fp=0x%x next_fp=0x%x "
        "saved_lr=0x%x canonical_lr=0x%x\n"
        % (xnu_index, xnu_fp, xnu_next_fp, xnu_saved_lr, xnu_canonical_lr)
    )
    xnu_fp = xnu_next_fp
end
else
  printf "XNU_PAUSED_REBOOT_REQUESTER_NOT_FOUND\n"
end

detach
quit
