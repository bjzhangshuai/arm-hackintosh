set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 restore probe.  Run only in the disposable
# Linux validation VM.  By default this starts at AVPBooter, injects signed
# iBSS at the verified AVPBooter receive point, and then chains the signed
# LocalPolicy and iBEC restore handlers in one stopped iBoot context so the
# manually entered handler does not fall back into the incomplete idle path.
set $start_from_avpbooter = 1
set $phase = 0
set $synthetic_handler_active = 0
set $ibss_payload_addr = 0x7006c000
set $ibss_payload_size = 320862
set $lpol_payload_addr = 0x72f00000
set $lpol_payload_size = 3046
set $ibec_payload_size = 381357
set $patch_restore_workspace_max = 1
set $restore_workspace_max_size = 0x200000
set $patch_ibec_window = 0
set $patched_ibec_window_size = 0x100000
set $use_external_ibec_bvx2_src = 0
set $external_ibec_bvx2_src_addr = 0x73000000
set $use_low_ibec_workspace = 0
set $low_ibec_workspace_addr = 0x73100000
set $low_ibec_workspace_size = 0x200000
set $dump_ibec_runtime = 1
set $ibss_stage_handoff_on_success = 1
set $direct_enter_ibec_on_success = 0
set $direct_enter_ibec_preferred_base = 1
set $ibec_preferred_base = 0x7006c000
set $dispatch_bounds_error = 0
set $ibec_runtime_addr = 0
set $ibec_runtime_size = 0
set $seen_svc7 = 0
set $ibec_manifest_ok_seen = 0
set $in_relocated_ibec = 0
set $ibec_root_build_return_seen = 0
set $synthetic_return_addr = 0x73fff000
init-if-undefined $stop_after_svc7_probe = 0
init-if-undefined $dump_final_callback = 0
init-if-undefined $stop_at_final_callback = 0
init-if-undefined $relocate_ibec_for_final_callback = 0
init-if-undefined $trace_relocated_ibec_halt = 0
init-if-undefined $trace_relocated_ibec_exceptions = 0
init-if-undefined $trace_relocated_ibec_init_failure = 0
init-if-undefined $trace_relocated_ibec_context_return = 0
init-if-undefined $inject_synthetic_root_descriptor = 0
init-if-undefined $trace_relocated_ibec_descriptor_table = 0
init-if-undefined $restore_relocated_ibec_descriptor_table = 0
init-if-undefined $restore_relocated_ibec_static_tail = 0
init-if-undefined $trace_relocated_ibec_root_build = 0
init-if-undefined $trace_relocated_ibec_descriptor_presence = 1
init-if-undefined $trace_relocated_ibec_map_checks = 1
init-if-undefined $trace_relocated_ibec_bdif_enum = 0
init-if-undefined $trace_relocated_ibec_usb_packets = 0
init-if-undefined $trace_ibec_allocator = 1
init-if-undefined $step_stage_allocator_return = 0
init-if-undefined $detach_after_ibec_aux_bdif_ready = 0
init-if-undefined $usb_req_task_poll_trace_limit = 16
set $usb_req_task_poll_count = 0

break *0x10de90
commands
  silent
  printf "IBSS_RECEIVE_ENTRY dest=0x%lx max=%u return=0x%lx\n", $x0, $w4, $x30
  restore /home/macvm/macos-restore/26.6/restore-chain/iBSS.fixed-rnd-713471fb.img4 binary $ibss_payload_addr
  set $x0 = $ibss_payload_size
  set $pc = 0x1007a8
  printf "IBSS_INJECTED addr=0x%lx size=%u\n", $ibss_payload_addr, $ibss_payload_size
  continue
end

break *0x1008d8
commands
  silent
  printf "IBSS_VERIFY_RETURN result=0x%x descriptor=0x%lx mode=%u\n", $w0, $x19, $w23
  if $w0 != 0
    detach
    quit
  end
  continue
end

break *0x105c94
commands
  silent
  printf "IBSS_HANDOFF_ENTRY arg0=0x%lx image=0x%lx arg2=0x%lx\n", $x0, $x1, $x2
  dump binary memory /home/macvm/macos-restore/26.6/restore-chain/iBSS.runtime-7006c000-70120000.bin 0x7006c000 0x70120000
  printf "IBSS_RUNTIME_DUMP path=/home/macvm/macos-restore/26.6/restore-chain/iBSS.runtime-7006c000-70120000.bin size=737280\n"
  printf "IBSS_HANDOFF_CONTINUE_TO_ENTRY\n"
  continue
end

break *0x7006e2cc
condition $bpnum $phase == 0
commands
  silent
  printf "IBSS_REMOTE_BOOT_ABORT_READY pc=0x%lx sp=0x%lx\n", $pc, $sp
  disable 1 2 3
  set $x0 = 0
  set $x1 = 0
  set $x2 = 0
  set $x3 = 0
  set $x30 = $synthetic_return_addr
  set $pc = 0x70073b98
  set $synthetic_handler_active = 1
  printf "LPOL_HANDLER_ENTER pc=0x%lx\n", $pc
  continue
end

break *0x70073bc0
commands
  silent
  printf "LPOL_FILESIZE_ORIGINAL value=%lu\n", $x0
  restore /home/macvm/macos-restore/26.6/local-policy-fixed-rnd-713471fb-bnch32/Ap.LocalPolicy.fixed-rnd-713471fb-bnch32.img4 binary $lpol_payload_addr
  set $x0 = $lpol_payload_size
  printf "LPOL_INJECTED addr=0x%lx size=%u\n", $lpol_payload_addr, $lpol_payload_size
  continue
end

break *0x70073bd0
commands
  silent
  printf "LPOL_LOADADDR_ORIGINAL value=0x%lx\n", $x0
  set $x0 = $lpol_payload_addr
  printf "LPOL_LOADADDR_INJECTED value=0x%lx\n", $x0
  continue
end

break *0x70073bf4
commands
  silent
  printf "LPOL_IMG4_VALIDATE_RETURN result=%u\n", $w0
  continue
end

break *0x70073bfc
commands
  silent
  printf "LPOL_TRUST_INSTALL_RETURN result=%u\n", $w0
  continue
end

break *0x70073c78
commands
  silent
  printf "LPOL_FIRST_STAGE_ACCEPTED\n"
  continue
end

break *0x7007287c
commands
  silent
  printf "LPOL_DATA_COMPARE_ENTER property=0x%lx descriptor=0x%lx expected_start=0x%lx expected_end=0x%lx\n", $x1, $x2, $x6, $x7
  continue
end

break *0x700728c4
commands
  silent
  set $parsed_ptr = *(unsigned long long *)($sp+8)
  set $parsed_size = *(unsigned int *)($sp+20)
  set $expected_size = *(unsigned long long *)($x29+32)
  printf "LPOL_DATA_PARSE_RETURN result=%u parsed=0x%lx parsed_size=%u expected_size=%lu\n", $w0, $parsed_ptr, $parsed_size, $expected_size
  continue
end

break *0x70072920
commands
  silent
  printf "LPOL_DATA_COMPARE_RETURN result=0x%x\n", $w0
  continue
end

break *0x70070dd4
commands
  silent
  printf "LPOL_PROPERTY_VALIDATE_RETURN result=0x%x\n", $w0
  continue
end

break *0x70078450
commands
  silent
  if $patch_restore_workspace_max
    printf "RESTORE_WORKSPACE_MAX_PATCH phase=%u caller=0x%lx old=0x80000 new=0x%lx\n", $phase, $x30, $restore_workspace_max_size
    set $w0 = $restore_workspace_max_size
    set $pc = 0x70078454
  end
  continue
end

break *0x70070874
condition $bpnum $phase == 1
commands
  silent
  printf "MANIFEST_OBJECT_CHECK phase=%u object=0x%lx lower=0x%lx upper=0x%lx limit_word=0x%x caller=0x%lx\n", $phase, $x20, $x22, $x21, *(unsigned int *)$x20, $x30
  x/12wx $x20
  x/12gx $x29+56
  if $patch_ibec_window && *(unsigned int *)$x20 == 0x69626563 && ($x21 - $x22) == 0x80000
    printf "IBEC_WINDOW_PATCH old_lower=0x%lx old_upper=0x%lx old_size=0x%lx stack_upper=0x%lx stack_size=0x%lx new_size=0x%lx\n", $x22, $x21, $x21 - $x22, *(unsigned long long *)($x29+72), *(unsigned long long *)($x29+88), $patched_ibec_window_size
    set $x21 = $x22 + $patched_ibec_window_size
    set *(unsigned long long *)($x29+72) = $x21
    set *(unsigned long long *)($x29+88) = $patched_ibec_window_size
    printf "IBEC_WINDOW_PATCH_APPLIED new_lower=0x%lx new_upper=0x%lx new_size=0x%lx stack_upper=0x%lx stack_size=0x%lx\n", $x22, $x21, $x21 - $x22, *(unsigned long long *)($x29+72), *(unsigned long long *)($x29+88)
    x/12gx $x29+56
  end
  continue
end

break *0x70070880
condition $bpnum $phase == 1
commands
  silent
  printf "MANIFEST_OBJECT_RANGE_ERROR phase=%u object=0x%lx first_word=0x%x cmp_limit=0x%lx caller=0x%lx\n", $phase, $x20, $w8, $x9, $x30
  x/12wx $x20
  continue
end

break *0x70070884
condition $bpnum $phase == 1
commands
  silent
  printf "MANIFEST_OBJECT_ERROR_BUILD phase=%u object=0x%lx w8=0x%x x8=0x%lx x9=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx caller=0x%lx\n", $phase, $x20, $w8, $x8, $x9, $x20, $x21, $x22, $x30
  x/12wx $x20
  x/12gx $x29+56
  continue
end

break *0x70071104
commands
  silent
  printf "IBEC_POLICY_FLAG_FAIL w28=0x%x current_tag=0x%x flag_828=%u flag_829=%u flag_709=%u flag_708=%u flag_808=%u flag_810=%u flag_879=%u flag_882=%u\n", $w28, *(unsigned int *)($sp+364), *(unsigned char *)($sp+828), *(unsigned char *)($sp+829), *(unsigned char *)($sp+709), *(unsigned char *)($sp+708), *(unsigned char *)($sp+808), *(unsigned char *)($sp+810), *(unsigned char *)($sp+879), *(unsigned char *)($sp+882)
  x/128bx $sp+0x1b8
  continue
end

break *0x70070bb0
commands
  silent
  printf "IBEC_SUBCHECK_700d24cc_RETURN w0=0x%x w8=0x%x w28=0x%x tag=0x%x x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx\n", $w0, $w8, $w28, *(unsigned int *)($sp+364), $x20, $x21, $x22, $x23
  x/96bx $sp+0x1b8
  if $patch_ibec_window && $phase == 1 && $w0 == 0 && ($x21 - $x22) == 0x80000
    printf "IBEC_WINDOW_PATCH_SUBCHECK old_lower=0x%lx old_upper=0x%lx old_size=0x%lx new_size=0x%lx\n", $x22, $x21, $x21 - $x22, $patched_ibec_window_size
    set $x21 = $x22 + $patched_ibec_window_size
    printf "IBEC_WINDOW_PATCH_SUBCHECK_APPLIED new_lower=0x%lx new_upper=0x%lx new_size=0x%lx\n", $x22, $x21, $x21 - $x22
  end
  continue
end

break *0x700714a8
commands
  silent
  printf "IBEC_RANGE_START w8=0x%lx x9=0x%lx x23=0x%lx x24=0x%lx x27=0x%lx w19=0x%x w28=0x%x tag=0x%x\n", $x8, $x9, $x23, $x24, $x27, $w19, $w28, *(unsigned int *)($sp+364)
  x/8gx $sp+120
  continue
end

break *0x700714e8
commands
  silent
  printf "IBEC_RANGE_CMP_A x8=0x%lx x9=0x%lx x23=0x%lx x24=0x%lx x27=0x%lx w19=0x%x w28=0x%x\n", $x8, $x9, $x23, $x24, $x27, $w19, $w28
  if $patch_ibec_window && $phase == 1 && $x9 == 0x80000 && $x8 <= $patched_ibec_window_size
    printf "IBEC_WINDOW_PATCH_CMP_A old_limit=0x%lx new_limit=0x%lx required=0x%lx\n", $x9, $patched_ibec_window_size, $x8
    set $x9 = $patched_ibec_window_size
  end
  continue
end

break *0x70071530
commands
  silent
  printf "IBEC_RANGE_AFTER_COPY w27=0x%x x23=0x%lx x24=0x%lx x19=0x%lx w19=0x%x x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx w28=0x%x\n", $w27, $x23, $x24, $x19, $w19, $x0, $x1, $x2, $x3, $x4, $x5, $w28
  continue
end

break *0x7007154c
commands
  silent
  printf "IBEC_DECOMPRESS_CALL dst=0x%lx dst_size=0x%lx src=0x%lx src_size=0x%lx work=0x%lx algo=0x%x\n", $x0, $x1, $x2, $x3, $x4, $w5
  x/16wx $x2
  x/64bx $x2
  if $use_external_ibec_bvx2_src && $phase == 1 && $w5 == 0x891 && $x3 == 0x5bb20
    restore /home/macvm/macos-restore/26.6/restore-chain/iBEC.vma2.RELEASE.bvx2 binary $external_ibec_bvx2_src_addr
    set $x2 = $external_ibec_bvx2_src_addr
    printf "IBEC_DECOMPRESS_SRC_RELOCATED src=0x%lx size=0x%lx\n", $x2, $x3
    x/16wx $x2
  end
  if $patch_ibec_window && $phase == 1 && $w5 == 0x891 && $x4 >= $x0 && $x4 < ($x0 + $x1)
    printf "IBEC_DECOMPRESS_WORK_RELOCATE old_work=0x%lx dst=0x%lx dst_end=0x%lx\n", $x4, $x0, $x0 + $x1
    set $x4 = $x0 + $x1
    printf "IBEC_DECOMPRESS_WORK_RELOCATED new_work=0x%lx\n", $x4
  end
  continue
end

break *0x70071550
commands
  silent
  printf "IBEC_RANGE_CMP_B x0=0x%lx x19=0x%lx x23=0x%lx x24=0x%lx w27=0x%x w28=0x%x\n", $x0, $x19, $x23, $x24, $w27, $w28
  continue
end

break *0x700dda80
commands
  silent
  printf "IBEC_BVX2_ENTER dst=0x%lx dst_size=0x%lx src=0x%lx src_size=0x%lx work=0x%lx algo=0x%x\n", $x0, $x1, $x2, $x3, $x4, $w5
  x/16wx $x2
  continue
end

break *0x700ddaf0
commands
  silent
  printf "IBEC_BVX2_CORE_RETURN w0=0x%x state=0x%lx produced_candidate=0x%lx src_cur=0x%lx src_end=0x%lx dst_base=0x%lx dst_cur=0x%lx\n", $w0, $x19, *(unsigned long long *)($x19+24) - $x21, *(unsigned long long *)$x19, *(unsigned long long *)($x19+16), $x21, *(unsigned long long *)($x19+24)
  x/16gx $x19
  continue
end

break *0x700ddb0c
commands
  silent
  printf "IBEC_BVX2_RETURN x0=0x%lx produced=0x%lx\n", $x0, $x20
  set $ibec_runtime_addr = $x21
  set $ibec_runtime_size = $x20
  if $dump_ibec_runtime && $x20 > 0
    dump binary memory /home/macvm/macos-restore/26.6/restore-chain/iBEC.runtime-last.bin $x21 $x21 + $x20
    printf "IBEC_RUNTIME_DUMP path=/home/macvm/macos-restore/26.6/restore-chain/iBEC.runtime-last.bin addr=0x%lx size=0x%lx\n", $x21, $x20
  end
  continue
end

break *0x70071564
commands
  silent
  printf "IBEC_RANGE_ERROR_SOURCE x0=0x%lx x8=0x%lx x9=0x%lx x19=0x%lx x23=0x%lx x24=0x%lx x27=0x%lx w27=0x%x w28=0x%x\n", $x0, $x8, $x9, $x19, $x23, $x24, $x27, $w27, $w28
  continue
end

break *0x7006eeb0
commands
  silent
  printf "IBEC_BUFFER addr=0x%lx\n", $x0
  restore /home/macvm/macos-restore/26.6/restore-chain/iBEC.fixed-rnd-713471fb.img4 binary $x0
  printf "IBEC_INJECTED addr=0x%lx size=%u\n", $x0, $ibec_payload_size
  continue
end

break *0x7006eebc
commands
  silent
  printf "IBEC_FILESIZE_ORIGINAL value=%u\n", $w0
  set $w0 = $ibec_payload_size
  printf "IBEC_FILESIZE_INJECTED value=%u\n", $w0
  continue
end

break *0x7007d198
commands
  silent
  printf "IBEC_IMG4_VALIDATE addr=0x%lx end=0x%lx size=%lu\n", $x0, $x2, $x4
  continue
end

break *0x7006eee0
commands
  silent
  printf "IBEC_IMG4_VALIDATE_RETURN result=%u\n", $w0
  continue
end

break *0x7006d400
commands
  silent
  printf "IBEC_FIRMWARE_DISPATCH addr=0x%lx size=%lu\n", $x0, $x1
  continue
end

break *0x700d5440
condition $bpnum $phase == 1 && $ibec_manifest_ok_seen && ($x2 - $x1) == 0x80000 && $trace_ibec_allocator
commands
  silent
  printf "IBEC_ALLOC_HELPER_ENTER x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx span=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x2 - $x1
  x/12gx $x4
  continue
end

break *0x700d5734
condition $bpnum $phase == 1 && $ibec_manifest_ok_seen && ($x21 - $x22) == 0x80000 && $trace_ibec_allocator
commands
  silent
  printf "IBEC_ALLOC_HELPER_RETURN_PRE x19=0x%lx qword_30=0x%lx x6=0x%lx x22=0x%lx x21=0x%lx x20=0x%lx size=0x%lx x30=0x%lx\n", $x19, *(unsigned long long *)($x19 + 48), $x6, $x22, $x21, $x20, $x21 - $x22, $x30
  continue
end

break *0x700d575c
condition $bpnum $phase == 1 && $ibec_manifest_ok_seen && $trace_ibec_allocator
commands
  silent
  printf "IBEC_ALLOC_HELPER_RETAB pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x30=0x%lx sp=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30, $sp
  if $step_stage_allocator_return
    x/i $pc
    stepi
    printf "IBEC_ALLOC_HELPER_AFTER_RET pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x30=0x%lx sp=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30, $sp
  end
  continue
end

break *0x7006d4d4
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_WORKSPACE_SOURCE_CALL_PRE x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $sp
  x/20gx $sp+128
  continue
end

break *0x7006d4d8
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_WORKSPACE_SOURCE_CALL_RETURN x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $sp
  x/20gx $sp+128
  continue
end

break *0x7006d4dc
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_WORKSPACE_RETURN_ORIGINAL x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx size=0x%lx\n", $x0, $x1, $x2, $x3, $x2 - $x1
  if $use_low_ibec_workspace
    set $x0 = $low_ibec_workspace_addr
    set $x1 = $low_ibec_workspace_addr
    set $x2 = $low_ibec_workspace_addr + $low_ibec_workspace_size
    printf "IBEC_WORKSPACE_RETURN_RELOCATED x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx size=0x%lx\n", $x0, $x1, $x2, $x3, $x2 - $x1
  end
  continue
end

break *0x7006d554
commands
  silent
  printf "IBEC_MANIFEST_VALIDATE_RETURN result=%u\n", $w0
  if $phase == 1 && $w0 == 0
    set $ibec_manifest_ok_seen = 1
  end
  if $ibss_stage_handoff_on_success && $phase == 1 && $w0 == 0
    printf "IBEC_STAGE_HANDOFF tag=0x69626563 entry_payload=0x%lx size=0x%lx via=0x7006c644\n", $ibec_runtime_addr, $ibec_runtime_size
    set $x0 = 0x69626563
    set $x1 = 1
    set $x2 = $ibec_runtime_addr
    set $x3 = 0
    set $x4 = 0
    set $x5 = 0
    set $x6 = 0
    set $x7 = 0
    set $x30 = $synthetic_return_addr
    set $pc = 0x7006c644
  else
  if $direct_enter_ibec_on_success && $phase == 1 && $w0 == 0
    if $direct_enter_ibec_preferred_base
      restore /home/macvm/macos-restore/26.6/restore-chain/iBEC.runtime-last.bin binary $ibec_preferred_base
      printf "IBEC_DIRECT_ENTRY_PREFERRED src=0x%lx dst=0x%lx size=0x%lx\n", $x21, $ibec_preferred_base, 0xb4448
      set $pc = $ibec_preferred_base
    else
      printf "IBEC_DIRECT_ENTRY addr=0x%lx size=0x%lx preferred_base=0x%lx\n", $x21, *(unsigned long long *)$sp, $ibec_preferred_base
      set $pc = $x21
    end
    delete
    detach
    quit
  end
  end
  continue
end

break *0x7007b8b0
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_TYPE2_ENTER type=0x%x payload=0x%lx aux=0x%lx caller=0x%lx\n", $w0, $x1, $x2, $x30
  continue
end

break *0x7007b8e8
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_AFTER_SVC6 x0=0x%lx type=0x%x payload=0x%lx aux=0x%lx\n", $x0, $w22, $x21, $x19
  continue
end

break *0x7007b8f8
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_AFTER_MODE_SETUP type=0x%x payload=0x%lx aux=0x%lx\n", $w22, $x21, $x19
  continue
end

break *0x700d0598
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_RESTORE_INFO_ENTER caller=0x%lx\n", $x30
  continue
end

break *0x700d0618
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_RESTORE_INFO_RETURN x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $x3, $x30
  continue
end

break *0x7007b94c
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_PRE_FINAL type=0x%x payload=0x%lx aux=0x%lx\n", $w22, $x21, $x19
  continue
end

break *0x700d0048
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONFIG_HELPER_ENTER pc=0x%lx return=0x%lx type=0x%x payload=0x%lx aux=0x%lx sp=0x%lx\n", $pc, $x30, $w22, $x21, $x19, $sp
  printf "IBEC_RESTORE_GLOBALS_PRE ready=%u flag_7010f010=%u append_ready=%u append_mode=%u deferred_state=%u deferred_enabled=%u ctx=0x7010f038 ctx_len=0x%lx deferred=0x%lx saved=0x%lx limit=0x%lx\n", *(unsigned char *)0x7010f088, *(unsigned char *)0x7010f010, *(unsigned char *)0x7010f089, *(unsigned char *)0x7010f08c, *(unsigned char *)0x7010f08b, *(unsigned char *)0x7010f08c, *(unsigned long long *)0x7010f078, *(unsigned long long *)0x7010f018, *(unsigned long long *)0x7010f038, *(unsigned long long *)0x7010f040
  x/20gx 0x7010f000
  continue
end

break *0x700d0054
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONFIG_HELPER_FLAG_CHECK pc=0x%lx ready_cmp=%u saved_return=0x%lx type=0x%x payload=0x%lx aux=0x%lx sp=0x%lx\n", $pc, $cpsr, $x4, $w22, $x21, $x19, $sp
  continue
end

break *0x700d0098
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONFIG_HELPER_AFTER_CONTEXT_BUILD pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x700d00d8
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONFIG_HELPER_RETURN pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x700d00dc
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONTEXT_BUILD_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  printf "IBEC_RESTORE_GLOBALS_ENTER ready=%u ctx_base=0x%lx ctx_end=0x%lx ctx_limit=0x%lx ctx_arg=0x%lx ctx_written=0x%lx deferred=0x%lx deferred_tuple=0x%lx:0x%lx:0x%lx:0x%lx append_count=0x%lx\n", *(unsigned char *)0x7010f088, *(unsigned long long *)0x7010f038, *(unsigned long long *)0x7010f040, *(unsigned long long *)0x7010f048, *(unsigned long long *)0x7010f050, *(unsigned long long *)0x7010f078, *(unsigned long long *)0x7010f018, *(unsigned long long *)0x7010f020, *(unsigned long long *)0x7010f028, *(unsigned long long *)0x7010f030, *(unsigned long long *)0x7010f038, *(unsigned long long *)0x7010f080
  x/20gx 0x7010f038
  continue
end

break *0x700d0268
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONTEXT_BUILD_RETURN pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  printf "IBEC_RESTORE_GLOBALS_POST ready=%u ctx_base=0x%lx ctx_end=0x%lx ctx_limit=0x%lx ctx_arg=0x%lx ctx_written=0x%lx saved0=0x%lx saved1=0x%lx saved2=0x%lx saved3=0x%lx append_count=0x%lx\n", *(unsigned char *)0x7010f088, *(unsigned long long *)0x7010f038, *(unsigned long long *)0x7010f040, *(unsigned long long *)0x7010f048, *(unsigned long long *)0x7010f050, *(unsigned long long *)0x7010f078, *(unsigned long long *)0x7010f058, *(unsigned long long *)0x7010f060, *(unsigned long long *)0x7010f068, *(unsigned long long *)0x7010f070, *(unsigned long long *)0x7010f080
  x/20gx 0x7010f038
  continue
end

break *0x700d0568
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONTEXT_APPEND_RETURN pc=0x%lx x0=0x%lx x8=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x8, $x21, $x22, $x23, $x24, $sp, $x30
  continue
end

break *0x700d0584
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONTEXT_APPEND_RETAB pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x30=0x%lx sp=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30, $sp
  continue
end

break *0x700d0588
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONTEXT_APPEND_LIMIT_FAIL pc=0x%lx count=0x%lx limit=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x24, $x8, $x21, $sp, $x30
  continue
end

break *0x700d0594
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONTEXT_APPEND_BOUNDS_FAIL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x7007b96c
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONFIG_HELPER_RETURNED_TO_CALLER pc=0x%lx type=0x%x payload=0x%lx aux=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $w22, $x21, $x19, $sp, $x30
  continue
end

break *0x7007b970
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_CONFIGURE_TYPE type=0x%x payload=0x%lx aux=0x%lx\n", $w22, $x21, $x19
  continue
end

break *0x7007b988
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_BEFORE_FINAL_HELPERS type=0x%x payload=0x%lx aux=0x%lx\n", $w22, $x21, $x19
  continue
end

break *0x7007b9c8
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_BEFORE_SVC7 payload=0x%lx arg1=0x%lx type=0x%x\n", $x21, $x19, $w20
  continue
end

break *0x7007b9e8
condition $bpnum $phase == 1
commands
  silent
  set $seen_svc7 = 1
  printf "IBEC_STAGE_SVC7 payload=0x%lx arg1=0x%lx type=0x%lx x3=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $x3, $x30
  if $stop_after_svc7_probe
    x/i $pc
    stepi
    printf "IBEC_STAGE_AFTER_SVC7_STEP pc=0x%lx sp=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x30=0x%lx\n", $pc, $sp, $x0, $x1, $x2, $x3, $x30
    info registers x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x16 x17 x18 x19 x20 x21 x22 x23 x24 x25 x26 x27 x28 x29 x30 sp pc cpsr
    detach
    quit
  end
  continue
end

break *0x700be548
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_SVC7_HANDLER_ENTER payload=0x%lx arg1=0x%lx type=0x%lx raw_x3=0x%lx sp=0x%lx\n", $x20, $x21, $x23, $x26, $sp
  continue
end

break *0x700c035c
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_ENTER payload=0x%lx arg1=0x%lx type=0x%lx flag=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $x30, $sp
  continue
end

break *0x700c0384
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_ENV_FLAG flag_byte=0x%x x8=0x%lx sp=0x%lx\n", $w8, $x8, $sp
  continue
end

break *0x700c0394
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_ACTIVE_FLAG active=0x%x addr=0x%lx sp=0x%lx\n", $w8, $x21, $sp
  continue
end

break *0x700c03c0
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_TYPE_CHECK requested=0x%lx expected=0x%lx desc=0x%lx\n", $x20, $x8, $x8
  continue
end

break *0x700c0414
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_ZERO_FLAG_PATH fallback_ptr=0x%lx\n", $x8
  continue
end

break *0x700c0454
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_MARK_ACTIVE scratch0=0x%lx scratch1=0x%lx payload=0x%lx arg1=0x%lx\n", *(unsigned long long *)$sp, *(unsigned long long *)($sp + 16), *(unsigned long long *)($sp + 32), *(unsigned long long *)($sp + 40)
  continue
end

break *0x700c0550
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_CONTEXT_BOUNDS_CHECK x0=0x%lx x1=0x%lx x2=0x%lx x22=0x%lx\n", $x0, $x1, $x2, $x22
  continue
end

break *0x700c0628
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_FINAL_DESCRIPTOR descriptor=0x%lx base=0x%lx lower=0x%lx upper=0x%lx\n", $x24, $x22, $x19, $x20
  continue
end

break *0x700c0648
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_FAIL_RANGE_A line=0x1cbf x0=0x%lx x1=0x%lx x22=0x%lx x25=0x%lx x26=0x%lx\n", $x0, $x1, $x22, $x25, $x26
  continue
end

break *0x700c065c
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_FAIL_RANGE_B line=0x1cd9 x0=0x%lx x5=0x%lx x22=0x%lx\n", $x0, $x5, $x22
  continue
end

break *0x700c0670
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_FAIL_PRECHECK line=0x1c82 payload=0x%lx arg1=0x%lx type=0x%lx flag=0x%lx caller=0x%lx\n", $x23, $x22, $x20, $x19, $x30
  continue
end

break *0x700c0684
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_FAIL_MISSING_DESCRIPTOR line=0x1c8d payload=0x%lx type=0x%lx fallback_ptr=0x%lx\n", $x23, $x20, $x8
  continue
end

break *0x700c0738
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SWITCH_FINAL_CALL payload=0x%lx arg1=0x%lx type=0x%lx frame_arg=0x%lx callback_arg=0x%lx\n", $x0, $x1, $x2, $x3, $x4
  continue
end

break *0x7007b7bc
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_FINAL_HANDOFF_ENTER payload=0x%lx arg1=0x%lx type=0x%lx frame_arg=0x%lx callback_arg=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x30
  continue
end

break *0x7007b858
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_FINAL_HANDOFF_CALLBACK callback=0x%lx payload=0x%lx arg1=0x%lx type=0x%lx frame_arg=0x%lx callback_arg=0x%lx\n", $x24, $x22, $x21, $x23, $x20, $x19
  continue
end

break *0x7007b874
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_FINAL_HANDOFF_CALLING_CALLBACK callback=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx\n", $x24, $x0, $x1, $x2, $x3, $x4
  if $dump_final_callback
    x/32i $x24
    x/16gx $x24 + 0x240
    dump binary memory /home/macvm/runs/aux-26.6/ibec-handoff-callback-aca00000.bin 0xaca00000 0xaca01000
    printf "IBEC_CALLBACK_DUMP_PATH path=/home/macvm/runs/aux-26.6/ibec-handoff-callback-aca00000.bin start=0xaca00000 size=0x1000\n"
  end
  if $stop_at_final_callback
    detach
    quit
  end
  if $relocate_ibec_for_final_callback
    delete
    restore /home/macvm/macos-restore/26.6/restore-chain/iBEC.runtime-last.bin binary $ibec_preferred_base
    set $x0 = $ibec_preferred_base
    set $x1 = 0
    set $x3 = 0
    set $x4 = 0
    set $pc = $x24
    set $in_relocated_ibec = 1
    printf "IBEC_FINAL_HANDOFF_RELOCATED src=0x%lx dst=0x%lx size=0x%lx callback=0x%lx frame_arg=0x%lx\n", $ibec_runtime_addr, $ibec_preferred_base, $ibec_runtime_size, $x24, $x2
    if $trace_relocated_ibec_halt
      break *0x70080178
      commands
        silent
        printf "POST_IBEC_ENTRY pc=0x%lx sp=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $sp, $x0, $x1, $x2, $x3, $x4, $x30, $cpsr
        x/8i $pc
        continue
      end
      if $trace_relocated_ibec_usb_packets
        break *0x7008c0d8
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_SLOT_REGISTER pc=0x%lx slot=0x%x endpoint=0x%x caller=0x%lx\n", $pc, $w0, $w1, $x30
          continue
        end
        break *0x7008d3d0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_SLOT_REGISTER pc=0x%lx slot=0x%x mode=0x%x endpoint_or_len=0x%x byte3=0x%x arg4=0x%lx arg5=0x%lx arg6=0x%lx arg7=0x%lx caller=0x%lx\n", $pc, $w0, $w1, $w2, $w3, $x4, $x5, $x6, $x7, $x30
          continue
        end
        break *0x7008c428
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND2_CALLBACK pc=0x%lx callback=0x%lx frame=0x%lx payload_len=0x%x endpoint=0x%x kind=0x%x caller=0x%lx\n", $pc, $x8, $x26, *(unsigned int *)$x26, *(unsigned char *)($x26 + 4), *(unsigned char *)($x26 + 5), $x30
          continue
        end
        break *0x7008c53c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND1_CALLBACK pc=0x%lx callback=0x%lx frame=0x%lx payload_len=0x%x endpoint=0x%x kind=0x%x caller=0x%lx\n", $pc, $x8, $x26, *(unsigned int *)$x26, *(unsigned char *)($x26 + 4), *(unsigned char *)($x26 + 5), $x30
          continue
        end
        break *0x7008c378
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND1_QUEUE_CHECK pc=0x%lx endpoint=0x%x slot=0x%lx queued=0x%lx pending_before=0x%x frame=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x26 + 4), $x8, $x23, *(unsigned short *)($x8 + 2), $x26, $x30
          continue
        end
        break *0x7008c510
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND1_EMPTY_QUEUE_CREDIT pc=0x%lx endpoint=0x%x slot=0x%lx pending_before=0x%x frame=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x26 + 4), $x8, *(unsigned short *)($x8 + 2), $x26, $x30
          continue
        end
        break *0x7008c51c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND1_ACK_PATH pc=0x%lx endpoint=0x%x frame=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x26 + 4), $x26, $x30
          continue
        end
        break *0x7008c480
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND3_PENDING_CHECK pc=0x%lx endpoint=0x%x slot=0x%lx pending_before=0x%x frame=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x26 + 4), $x27, *(unsigned short *)($x27 + 2), $x26, $x30
          continue
        end
        break *0x7008c488
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND3_CLEAR_PENDING pc=0x%lx endpoint=0x%x slot=0x%lx pending_before=0x%x queue_head=0x%lx frame=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x26 + 4), $x27, *(unsigned short *)($x27 + 2), *(unsigned long long *)($x27 + 8), $x26, $x30
          continue
        end
        break *0x7008c498
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND3_QUEUE_HEAD pc=0x%lx endpoint=0x%x slot=0x%lx queued=0x%lx pending_now=0x%x frame=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x26 + 4), $x27, $x20, *(unsigned short *)($x27 + 2), $x26, $x30
          continue
        end
        break *0x7008c504
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_KIND3_EMPTY_OR_INVALID pc=0x%lx endpoint=0x%x slot=0x%lx frame=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x26 + 4), $x27, $x26, $x30
          if $x27 >= 0x70000000 && $x27 < 0x180000000
            printf "POST_IBEC_USB_KIND3_EMPTY_OR_INVALID_SLOT pending_now=0x%x queue_head=0x%lx\n", *(unsigned short *)($x27 + 2), *(unsigned long long *)($x27 + 8)
          end
          continue
        end
        break *0x7008c6bc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_STATUS_REPLY_BUILD pc=0x%lx endpoint=0x%x status=0x%x caller=0x%lx\n", $pc, $w0, $w1, $x30
          continue
        end
        break *0x7008c814
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_QUEUE_OR_SEND pc=0x%lx span0=0x%lx span0_upper=0x%lx span1=0x%lx span1_len=0x%lx tag=0x%x endpoint=0x%x caller=0x%lx\n", $pc, $x0, $x1, $x3, $x4, $w4, $w5, $x30
          continue
        end
        break *0x7008c8b0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_QUEUE_PENDING_CHECK pc=0x%lx endpoint=0x%x slot=0x%lx pending_before=0x%x caller=0x%lx\n", $pc, $w24, $x28, *(unsigned short *)($x28 + 2), $x30
          continue
        end
        break *0x7008c900
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_QUEUE_ENQUEUE pc=0x%lx endpoint=0x%x slot=0x%lx queued_span0=0x%lx queued_len=0x%x caller=0x%lx\n", $pc, $w24, $x28, $x22, $w23, $x30
          continue
        end
        break *0x7008c8bc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_QUEUE_SEND_IMMEDIATE pc=0x%lx endpoint=0x%x slot=0x%lx caller=0x%lx\n", $pc, $w24, $x28, $x30
          if $x28 >= 0x70000000 && $x28 < 0x180000000
            printf "POST_IBEC_USB_ENDPOINT_QUEUE_SEND_IMMEDIATE_SLOT pending_now=0x%x\n", *(unsigned short *)($x28 + 2)
          end
          continue
        end
        break *0x7008d4cc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_ENTRY pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx x8=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx x26=0x%lx x27=0x%lx x28=0x%lx sp=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $x8, $x19, $x20, $x21, $x22, $x23, $x24, $x25, $x26, $x27, $x28, $sp, $x30
          if ($x0 >= 0x70000000 && $x0 < 0x180000000) || ($x0 >= 0xfffffc0000000000 && $x0 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_CALLBACK_X0_BYTES\n"
            x/64bx $x0
          end
          if ($x1 >= 0x70000000 && $x1 < 0x180000000) || ($x1 >= 0xfffffc0000000000 && $x1 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_CALLBACK_X1_BYTES\n"
            x/64bx $x1
          end
          if ($x26 >= 0x70000000 && $x26 < 0x180000000) || ($x26 >= 0xfffffc0000000000 && $x26 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_CALLBACK_FRAME_BYTES\n"
            x/64bx $x26
          end
          continue
        end
        break *0x7008d4f8
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_KIND2_DISPATCH pc=0x%lx endpoint=0x%x payload_len=0x%x caller=0x%lx\n", $pc, $w5, $w4, $x30
          continue
        end
        break *0x7008d520
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_KIND1_PAYLOAD_ENTRY pc=0x%lx endpoint=0x%x payload=0x%lx payload_len=0x%x bounds=[0x%lx,0x%lx) caller=0x%lx\n", $pc, $w5, $x0, $w4, $x1, $x2, $x30
          continue
        end
        break *0x7008d578
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_KIND1_SLOT_STATE pc=0x%lx endpoint=0x%x slot=0x%lx active=0x%x mode=0x%x max_packet=0x%x state=0x%x caller=0x%lx\n", $pc, $w5, $x24, *(unsigned int *)($x24 + 8), *(unsigned char *)($x24 + 3), *(unsigned short *)($x24 + 4), *(unsigned int *)($x24 + 12), $x30
          continue
        end
        break *0x7008d584
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_KIND1_LENGTH_CLASSIFY pc=0x%lx endpoint=0x%x slot=0x%lx payload_len=0x%x mode=0x%x caller=0x%lx\n", $pc, $w5, $x24, $w22, *(unsigned char *)($x24 + 3), $x30
          continue
        end
        break *0x7008d598
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_KIND1_SETUP_SPLIT pc=0x%lx endpoint=0x%x frame=0x%lx payload=0x%lx payload_len=0x%x caller=0x%lx\n", $pc, *(unsigned char *)($x21 + 4), $x21, $x23, $w22, $x30
          if ($x23 >= 0x70000000 && $x23 < 0x180000000) || ($x23 >= 0xfffffc0000000000 && $x23 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_CALLBACK_KIND1_SETUP_BYTES\n"
            x/16bx $x23
          end
          continue
        end
        break *0x7008d5cc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_KIND1_QUEUE_PAYLOAD pc=0x%lx endpoint=0x%x frame=0x%lx queue=0x%lx payload=0x%lx queued_len=0x%x payload_len=0x%x caller=0x%lx\n", $pc, *(unsigned char *)($x21 + 4), $x21, $x0, $x3, $w7, $w22, $x30
          if ($x3 >= 0x70000000 && $x3 < 0x180000000) || ($x3 >= 0xfffffc0000000000 && $x3 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_CALLBACK_KIND1_QUEUE_PAYLOAD_BYTES\n"
            x/32bx $x3
          end
          continue
        end
        break *0x7008d5d0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CALLBACK_KIND1_QUEUE_DONE pc=0x%lx endpoint=0x%x slot=0x%lx queue_head=0x%lx queue_tail=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x21 + 4), $x24, *(unsigned long long *)($x24 + 48), *(unsigned long long *)($x24 + 32), $x30
          continue
        end
        break *0x7008d7f4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_ENGINE_SIGNAL pc=0x%lx signal_handle=0x%x caller=0x%lx\n", $pc, *(unsigned short *)0x70121c82, $x30
          continue
        end
        break *0x7008ce88
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_ENGINE_ENTRY pc=0x%lx arg0=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30
          continue
        end
        break *0x7008ced0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_ENGINE_WAIT pc=0x%lx control=0x%lx active=0x%x signal_handle=0x%x caller=0x%lx\n", $pc, $x19, *(unsigned char *)$x19, *(unsigned short *)($x19 + 2), $x30
          continue
        end
        break *0x7008ced8
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_ENGINE_WAIT_RETURN pc=0x%lx control=0x%lx wait_result=0x%lx active=0x%x caller=0x%lx\n", $pc, $x19, $x0, *(unsigned char *)$x19, $x30
          continue
        end
        break *0x7008cf50
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_ENGINE_SLOT pc=0x%lx slot_index=0x%lx slot=0x%lx endpoint=0x%x active=0x%x mode=0x%x state=0x%x queue_head=0x%lx send_head=0x%lx caller=0x%lx\n", $pc, *(unsigned long long *)($sp + 16), $x27, *(unsigned char *)($x27 + 2), *(unsigned int *)($x27 + 8), *(unsigned char *)($x27 + 3), *(unsigned int *)($x27 + 12), *(unsigned long long *)($x27 + 48), *(unsigned long long *)($x27 + 16), $x30
          continue
        end
        break *0x7008d000
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_ENGINE_COPY_HOST_PAYLOAD pc=0x%lx endpoint=0x%x slot=0x%lx payload=0x%lx copied=0x%x transfer=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x27 + 2), $x27, $x23, $w19, $x22, $x30
          continue
        end
        break *0x7008d144
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_ENGINE_SEND_GUEST_PACKET pc=0x%lx endpoint=0x%x slot=0x%lx packet=0x%lx packet_len=0x%x transfer=0x%lx caller=0x%lx\n", $pc, *(unsigned char *)($x27 + 2), $x27, $x0, $w4, $x22, $x30
          continue
        end
        break *0x7008e1f0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_INPUT_QUEUE_ENQUEUE pc=0x%lx queue=0x%lx lower=0x%lx upper=0x%lx payload=0x%lx meta0=0x%lx meta1=0x%lx meta2=0x%lx queued_len=0x%x caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $w7, $x30
          if ($x4 >= 0x70000000 && $x4 < 0x180000000) || ($x4 >= 0xfffffc0000000000 && $x4 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_INPUT_QUEUE_ENQUEUE_FRAME endpoint=0x%x kind=0x%x frame=0x%lx\n", *(unsigned char *)($x4 + 4), *(unsigned char *)($x4 + 5), $x4
          end
          continue
        end
        break *0x7008ea08
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQ_BUILD_ENTER pc=0x%lx req_byte=0x%x caller=0x%lx\n", $pc, $w0, $x30
          continue
        end
        break *0x7008ea9c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQ_BUILD_CALL_WAIT pc=0x%lx req_type=0x%lx handle=0x%lx data_buf=0x%lx data_len=0x%x caller=0x%lx\n", $pc, $x0, $x3, $x3, $w4, $x30
          continue
        end
        break *0x7008eaa0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQ_BUILD_WAIT_RETURN pc=0x%lx result=0x%x caller=0x%lx\n", $pc, $w0, $x30
          continue
        end
        break *0x7008c4b4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_EVENT_PAYLOAD_BRANCH pc=0x%lx x0=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx x26=0x%lx x27=0x%lx x28=0x%lx sp=0x%lx caller=0x%lx\n", $pc, $x0, $x19, $x20, $x21, $x22, $x23, $x24, $x25, $x26, $x27, $x28, $sp, $x30
          continue
        end
        break *0x7008c654
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_EVENT_REPLY_BUILD pc=0x%lx x0=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx x26=0x%lx x27=0x%lx x28=0x%lx sp=0x%lx caller=0x%lx\n", $pc, $x0, $x19, $x20, $x21, $x22, $x23, $x24, $x25, $x26, $x27, $x28, $sp, $x30
          continue
        end
        break *0x7008c988
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_EVENT_LARGE_BUFFER_PATH pc=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx x26=0x%lx x27=0x%lx x28=0x%lx sp=0x%lx caller=0x%lx\n", $pc, $x19, $x20, $x21, $x22, $x23, $x24, $x25, $x26, $x27, $x28, $sp, $x30
          continue
        end
        break *0x7008cad0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_EVENT_COMMIT pc=0x%lx committed=0x%lx slot_ptr=0x%lx state=0x%lx x19=0x%lx x20=0x%lx x24=0x%lx x25=0x%lx x26=0x%lx sp=0x%lx caller=0x%lx\n", $pc, $x24, $x9, $x19, $x19, $x20, $x24, $x25, $x26, $sp, $x30
          continue
        end
        break *0x7008ec60
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_TYPE0_HANDLER_ENTER pc=0x%lx packet=0x%lx lower=0x%lx upper=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x30
          if ($x0 >= 0x70000000 && $x0 < 0x180000000) || ($x0 >= 0xfffffc0000000000 && $x0 < 0xfffffd0000000000)
            x/32bx $x0
          end
          continue
        end
        break *0x7008f980
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQUEST_ENGINE_ENTER pc=0x%lx arg0=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx arg4=0x%lx arg5=0x%lx arg6=0x%lx arg7=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $x30
          continue
        end
        break *0x700902d0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_STATE_ADVANCE pc=0x%lx state=0x%x caller=0x%lx\n", $pc, $w0, $x30
          continue
        end
        break *0x700902fc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_STATE1_BRANCH pc=0x%lx caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x7009034c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_STATE1_CALLBACK pc=0x%lx endpoint_index=0x%lx endpoint_slot=0x%lx callback=0x%lx device=0x%lx caller=0x%lx\n", $pc, $x19, $x21, $x9, $x20, $x30
          continue
        end
        break *0x70090360
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_STATE2_BRANCH pc=0x%lx caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x700903c4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_STATE2_CALLBACK pc=0x%lx endpoint_index=0x%lx endpoint_slot=0x%lx callback=0x%lx device=0x%lx caller=0x%lx\n", $pc, $x20, $x21, $x9, $x19, $x30
          continue
        end
        break *0x700903d4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_STATE3_BRANCH pc=0x%lx caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x70090404
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_ENDPOINT_STATE3_DESC_READY pc=0x%lx device=0x%lx count=0x%x active=0x%x mode=0x%x caller=0x%lx\n", $pc, $x19, *(unsigned int *)($x19 + 32), *(unsigned int *)($x19 + 36), *(unsigned int *)($x19 + 24), $x30
          continue
        end
        break *0x700909cc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_TASKS_INIT_ENTER pc=0x%lx caller=0x%lx sp=0x%lx\n", $pc, $x30, $sp
          continue
        end
        break *0x70090a4c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_RPC_TASK_CREATE pc=0x%lx task_name=usb-rpc callback=0x70090bcc caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x70090ad0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CMD_TASK_CREATE pc=0x%lx task_name=usb-cmd callback=0x70090c40 caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x70090bcc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_RPC_TASK_ENTRY pc=0x%lx arg0=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30
          continue
        end
        break *0x70090c40
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CMD_TASK_ENTRY pc=0x%lx arg0=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30
          continue
        end
        break *0x70090d14
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CMD_TASK_STATUS_CALL pc=0x%lx handle=0x%x out0=0x%lx out1=0x%lx out2=0x%lx out3=0x%lx caller=0x%lx\n", $pc, $w0, $x1, $x4, $x7, *(unsigned long long *)$sp, $x30
          continue
        end
        break *0x70090d7c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CMD_TASK_DISPATCH_PACKET pc=0x%lx packet=0x%lx packet_len=0x%lx queue_entry=0x%lx caller=0x%lx\n", $pc, $x23, $x5, $x2, $x30
          if ($x23 >= 0x70000000 && $x23 < 0x180000000) || ($x23 >= 0xfffffc0000000000 && $x23 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_CMD_TASK_DISPATCH_BYTES\n"
            x/32bx $x23
          end
          continue
        end
        break *0x70090da4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CMD_TASK_SVC81 pc=0x%lx handle=0x%x tag=0x%x data=0x%lx data_len=0x%lx status=0x%lx caller=0x%lx\n", $pc, $w0, $w3, $x4, $x5, $x6, $x30
          continue
        end
        break *0x70090da8
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_CMD_TASK_SVC81_RETURN pc=0x%lx result=0x%lx caller=0x%lx\n", $pc, $x0, $x30
          continue
        end
        break *0x700914d0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_STATUS_WAIT_ENTER pc=0x%lx handle=0x%x out0=0x%lx out1=0x%lx out2=0x%lx out3=0x%lx caller=0x%lx\n", $pc, $w0, $x1, $x4, $x7, *(unsigned long long *)$sp, $x30
          continue
        end
        break *0x70091524
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_STATUS_WAIT_SVC82 pc=0x%lx handle=0x%x timeout=0x%lx mode=0x%x caller=0x%lx\n", $pc, $w0, $x1, $w2, $x30
          continue
        end
        break *0x70091528
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_STATUS_WAIT_SVC82_RETURN pc=0x%lx result=0x%lx out0=0x%lx out1=0x%lx out2=0x%lx out3=0x%lx caller=0x%lx\n", $pc, $x0, $x3, $x4, $x5, $x6, $x30
          continue
        end
        break *0x70091584
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_STATUS_WAIT_READY pc=0x%lx result=0x%lx caller=0x%lx\n", $pc, $x0, $x30
          continue
        end
        break *0x70091620
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQ_TASK_INIT_ENTER pc=0x%lx caller=0x%lx sp=0x%lx\n", $pc, $x30, $sp
          continue
        end
        break *0x7009168c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQ_TASK_CREATE pc=0x%lx task_name=usb-req callback=0x700916f0 caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x700916f0
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQ_TASK_ENTRY pc=0x%lx arg0=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30
          continue
        end
        break *0x70091744
        condition $bpnum $in_relocated_ibec
        commands
          silent
          set $usb_req_task_poll_count = $usb_req_task_poll_count + 1
          if $usb_req_task_poll_count <= $usb_req_task_poll_trace_limit
            printf "POST_IBEC_USB_REQ_TASK_POLL_BYTE pc=0x%lx poll=0x%lx ptr=0x%lx byte=0x%x caller=0x%lx\n", $pc, $usb_req_task_poll_count, $x8, *(unsigned char *)$x8, $x30
          end
          continue
        end
        break *0x70091774
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQ_TASK_CONSUME_BYTE pc=0x%lx ptr=0x%lx byte=0x%x caller=0x%lx\n", $pc, $x8, $w0, $x30
          continue
        end
        break *0x700917dc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_VBUS_POLL_TASK_CREATE pc=0x%lx task_name=vbus-poll callback=0x70091888 caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x70091834
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_VBUS_TASK_CREATE pc=0x%lx task_name=usb-vbus callback=0x70091890 caller=0x%lx\n", $pc, $x30
          continue
        end
        break *0x70091890
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_VBUS_TASK_ENTRY pc=0x%lx arg0=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x30
          continue
        end
        break *0x7008ed44
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_TYPE0_ARMED pc=0x%lx packet=0x%lx setup_id=0x%x data_len=0x%x request_dir=0x%x state=0x%lx\n", $pc, $x19, *(unsigned short *)($x19 + 2), *(unsigned short *)($x19 + 6), *(unsigned char *)($x19 + 1), $x24
          continue
        end
        break *0x7008ee3c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_ENQUEUE_ENTER pc=0x%lx tag=0x%x arg0=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx arg4=0x%lx arg5=0x%lx arg6=0x%lx caller=0x%lx\n", $pc, $w0, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x30
          set $usb_enqueue_span0_len = $x3 - $x1
          if (($x1 >= 0x70000000 && $x1 < 0x180000000) || ($x1 >= 0xfffffc0000000000 && $x1 < 0xfffffd0000000000)) && $x3 >= $x1 && $usb_enqueue_span0_len > 0 && $usb_enqueue_span0_len <= 0x100
            printf "POST_IBEC_USB_PACKET_ENQUEUE_SPAN0 start=0x%lx end=0x%lx len=0x%lx\n", $x1, $x3, $usb_enqueue_span0_len
            x/32bx $x1
          end
          if (($x4 >= 0x70000000 && $x4 < 0x180000000) || ($x4 >= 0xfffffc0000000000 && $x4 < 0xfffffd0000000000)) && $x5 > 0 && $x5 <= 0x100
            printf "POST_IBEC_USB_PACKET_ENQUEUE_SPAN1 start=0x%lx len=0x%lx\n", $x4, $x5
            x/32bx $x4
          end
          continue
        end
        break *0x7008eed4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_ENQUEUE_RETURN pc=0x%lx packet=0x%lx\n", $pc, $x0
          if ($x0 >= 0x70000000 && $x0 < 0x180000000) || ($x0 >= 0xfffffc0000000000 && $x0 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_PACKET_ENQUEUE_BYTES tag=0x%x\n", *(unsigned char *)$x0
            x/64bx $x0
          end
          continue
        end
        break *0x700912d4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQUEST_WAIT_ENTER pc=0x%lx req_type=0x%lx out0=0x%lx out1=0x%lx out2=0x%lx out3=0x%lx data_len=0x%lx data_buf=0x%lx caller=0x%lx\n", $pc, $x0, $x5, $x6, $x7, *(unsigned long long *)$sp, $x4, $x3, $x30
          continue
        end
        break *0x700913e4
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQUEST_SVC81 pc=0x%lx handle=0x%x tag=0x%x data=0x%lx data_len=0x%lx x1=0x%lx x2=0x%lx x6=0x%lx\n", $pc, $w0, $w3, $x4, $x5, $x1, $x2, $x6
          if ($x4 >= 0x70000000 && $x4 < 0x180000000) || ($x4 >= 0xfffffc0000000000 && $x4 < 0xfffffd0000000000)
            x/32bx $x4
          end
          continue
        end
        break *0x700913e8
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQUEST_SVC81_RETURN pc=0x%lx result=0x%lx w0=0x%x\n", $pc, $x0, $w0
          continue
        end
        break *0x70091428
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQUEST_STATUS_CALL pc=0x%lx status_handle=0x%x out_result=0x%lx out_tag=0x%lx out_len=0x%lx out_extra=0x%lx\n", $pc, $w0, $x1, $x4, $x7, *(unsigned long long *)$sp
          continue
        end
        break *0x7009142c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQUEST_STATUS_RETURN pc=0x%lx ok=0x%x sp_result=0x%lx sp_tag=0x%lx sp_len=0x%lx sp_extra=0x%lx\n", $pc, $w0, *(unsigned long long *)($sp + 80), *(unsigned long long *)($sp + 72), *(unsigned long long *)($sp + 64), *(unsigned long long *)($sp + 88)
          continue
        end
        break *0x70091484
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_REQUEST_WAIT_RETURN pc=0x%lx result=0x%lx status_byte=0x%x data_len=0x%x\n", $pc, $x0, *(unsigned char *)$x19, *(unsigned int *)$x19
          continue
        end
        break *0x7009190c
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_DISPATCH_ENTER pc=0x%lx packet=0x%lx lower=0x%lx upper=0x%lx arg3=0x%lx count=0x%lx table=0x%lx table_upper=0x%lx caller=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x30
          if ($x0 >= 0x70000000 && $x0 < 0x180000000) || ($x0 >= 0xfffffc0000000000 && $x0 < 0xfffffd0000000000)
            printf "POST_IBEC_USB_PACKET_DISPATCH_BYTES first=0x%x type=0x%x second=0x%x seq=0x%x endpoint=0x%x len=0x%x\n", *(unsigned char *)$x0, (*(unsigned char *)$x0) & 0x1f, *(unsigned char *)($x0 + 1), *(unsigned short *)($x0 + 2), *(unsigned short *)($x0 + 4), *(unsigned short *)($x0 + 6)
            x/32bx $x0
          end
          continue
        end
        break *0x70091980
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_DISPATCH_TYPE0 pc=0x%lx packet=0x%lx\n", $pc, $x20
          continue
        end
        break *0x70091990
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_DISPATCH_TYPE1 pc=0x%lx packet=0x%lx endpoint_index=0x%x count=0x%x table=0x%lx\n", $pc, $x20, *(unsigned short *)($x20 + 4), $w26, $x25
          continue
        end
        break *0x700919cc
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_DISPATCH_CALL_ENDPOINT pc=0x%lx callback=0x%lx packet=0x%lx endpoint_index=0x%x\n", $pc, $x8, $x20, $w27
          continue
        end
        break *0x70091a28
        condition $bpnum $in_relocated_ibec
        commands
          silent
          printf "POST_IBEC_USB_PACKET_DISPATCH_RETURN pc=0x%lx result=0x%x endpoint_index=0x%x packet=0x%lx\n", $pc, $w0, $w27, $x20
          continue
        end
      end
      if $trace_relocated_ibec_init_failure
        if $trace_relocated_ibec_descriptor_table || $restore_relocated_ibec_descriptor_table
          break *0x700d1070
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_TABLE_BEFORE_OPTIONAL_RESTORE pc=0x%lx entry24_base=0x%lx entry24_span=0x%lx entry24_selector=0x%x sp=0x%lx x30=0x%lx\n", $pc, *(unsigned long long *)0x7011d6c0, *(unsigned long long *)0x7011d6d0, *(unsigned short *)0x7011d6d8, $sp, $x30
            if $restore_relocated_ibec_static_tail
              restore /home/macvm/macos-restore/26.6/restore-chain/iBEC.runtime-last.bin binary 0x7006c000 0xb0000 0xb4448
              printf "POST_IBEC_STATIC_TAIL_RESTORED base=0x7011c000 end=0x70120448 entry24_base=0x%lx entry24_span=0x%lx entry24_selector=0x%x firebloom_meta0=0x%lx firebloom_meta1=0x%lx\n", *(unsigned long long *)0x7011d6c0, *(unsigned long long *)0x7011d6d0, *(unsigned short *)0x7011d6d8, *(unsigned long long *)0x7011fc80, *(unsigned long long *)0x7011fc88
            end
            if $restore_relocated_ibec_descriptor_table
              restore /home/macvm/macos-restore/26.6/restore-chain/iBEC.descriptor-table.bin binary 0x7011d0c0
              printf "POST_IBEC_DESCRIPTOR_TABLE_RESTORED addr=0x7011d0c0 size=0xb80 entry24_base=0x%lx entry24_span=0x%lx entry24_selector=0x%x\n", *(unsigned long long *)0x7011d6c0, *(unsigned long long *)0x7011d6d0, *(unsigned short *)0x7011d6d8
            end
            continue
          end
        end
        break *0x700d1218
        commands
          silent
          printf "POST_IBEC_INIT_CHECK_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp, $x30
          x/32gx $sp
          continue
        end
        break *0x700d1220
        commands
          silent
          printf "POST_IBEC_INIT_CHECK_RETURN pc=0x%lx result=0x%lx w0=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x0, $w0, $sp, $x30
          continue
        end
        break *0x700d127c
        commands
          silent
          printf "POST_IBEC_ROOT_LOOKUP_REQUEST pc=0x%lx selector=0x%x chosen_slot=0x%lx root_lower=0x%lx root_upper=0x%lx x26=0x%lx x28=0x%lx sp=0x%lx\n", $pc, $w0, $x9, $x20, $x22, $x26, $x28, $sp
          x/40gx $x26
          x/32gx $sp + 80
          if $trace_relocated_ibec_descriptor_table
            printf "POST_IBEC_STATIC_DESCRIPTOR_ENTRY24 addr=0x7011d6c0 base=0x%lx zero=0x%lx span=0x%lx selector=0x%x type=0x%x flags=0x%x\n", *(unsigned long long *)0x7011d6c0, *(unsigned long long *)0x7011d6c8, *(unsigned long long *)0x7011d6d0, *(unsigned short *)0x7011d6d8, *(unsigned short *)0x7011d6da, *(unsigned int *)0x7011d6dc
            x/8gx 0x7011d6c0
          end
          continue
        end
        if $trace_relocated_ibec_descriptor_table
          break *0x700dbe0c
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_TABLE_READY pc=0x%lx wanted=0x%x count=%u begin=0x%lx lower=0x%lx upper=0x%lx aux=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $w19, *(unsigned int *)($sp + 12), *(unsigned long long *)($sp + 16), *(unsigned long long *)($sp + 24), *(unsigned long long *)($sp + 32), *(unsigned long long *)($sp + 40), $sp, $x30
            printf "POST_IBEC_DESCRIPTOR_TABLE_ENTRY24 base=0x%lx zero=0x%lx span=0x%lx selector=0x%x type=0x%x flags=0x%x\n", *(unsigned long long *)0x7011d6c0, *(unsigned long long *)0x7011d6c8, *(unsigned long long *)0x7011d6d0, *(unsigned short *)0x7011d6d8, *(unsigned short *)0x7011d6da, *(unsigned int *)0x7011d6dc
            continue
          end
          break *0x700dbe28
          condition $bpnum $w19 == 0xa7
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_TABLE_SCAN pc=0x%lx wanted=0x%x candidate=0x%lx candidate_selector=0x%x candidate_type=0x%x candidate_base=0x%lx candidate_span=0x%lx remaining=%u\n", $pc, $w19, $x0, *(unsigned short *)($x0 + 24), *(unsigned short *)($x0 + 26), *(unsigned long long *)$x0, *(unsigned long long *)($x0 + 16), $w8
            continue
          end
          break *0x700dbe58
          condition $bpnum $w19 == 0xa7
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_TABLE_FOUND pc=0x%lx wanted=0x%x desc=0x%lx desc_base=0x%lx desc_span=0x%lx aux=0x%lx sp=0x%lx\n", $pc, $w19, $x0, *(unsigned long long *)$x0, *(unsigned long long *)($x0 + 16), *(unsigned long long *)($sp + 40), $sp
            continue
          end
          break *0x700dbe44
          condition $bpnum $w19 == 0xa7
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_TABLE_NOT_FOUND pc=0x%lx wanted=0x%x count_now=%u cursor=0x%lx lower=0x%lx upper=0x%lx sp=0x%lx\n", $pc, $w19, $w8, $x0, $x1, $x2, $sp
            continue
          end
        end
        break *0x700d1294
        commands
          silent
          if $inject_synthetic_root_descriptor && $x0 == 0
            set $synthetic_root_desc_addr = $sp - 0x180
            set $synthetic_root_desc_span = $x22 - $x28
            set *(unsigned long long *)$synthetic_root_desc_addr = $x28
            set *(unsigned long long *)($synthetic_root_desc_addr + 8) = 0
            set *(unsigned long long *)($synthetic_root_desc_addr + 16) = $synthetic_root_desc_span
            set *(unsigned short *)($synthetic_root_desc_addr + 24) = *(unsigned int *)($sp + 208)
            set *(unsigned short *)($synthetic_root_desc_addr + 26) = 0x102
            set *(unsigned int *)($synthetic_root_desc_addr + 28) = 1
            set $x0 = $synthetic_root_desc_addr
            set $x1 = $synthetic_root_desc_addr
            set $x2 = $synthetic_root_desc_addr + 0x20
            set $x3 = 0x7011bf60
            printf "POST_IBEC_SYNTHETIC_ROOT_DESCRIPTOR_INJECTED desc=0x%lx base=0x%lx span=0x%lx selector=0x%x table_upper=0x%lx\n", $x0, *(unsigned long long *)$x0, *(unsigned long long *)($x0 + 16), *(unsigned short *)($x0 + 24), $x2
          end
          printf "POST_IBEC_ROOT_DESCRIPTOR_CHECK_CALL pc=0x%lx desc=0x%lx desc_lower=0x%lx desc_upper=0x%lx extra=0x%lx root_tag_ptr=0x%lx root_tag_end=0x%lx root_aux=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, *(unsigned long long *)($sp + 96), $x21, $sp, $x30
          if $x0 >= 0x70000000 && $x0 < 0x70140000
            x/8gx $x0
          end
          continue
        end
        if $trace_relocated_ibec_bdif_enum
          break *0x700a48fc
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_ENTER pc=0x%lx obj=0x%lx lower=0x%lx upper=0x%lx reg_names=0x%lx expected_cfg=0x%x count=0x%x finalize=0x%x caller=0x%lx sp=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $w4, $w5, $w6, $x30, $sp
            if $x0 >= 0x70000000 && $x0 < 0x70140000
              x/16gx $x0
            end
            continue
          end
          break *0x700a493c
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_STATUS_RETURN pc=0x%lx status=0x%x obj=0x%lx lower=0x%lx upper=0x%lx caller=0x%lx sp=0x%lx\n", $pc, $w0, $x22, $x20, $x19, $x30, $sp
            continue
          end
          break *0x700a4960
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_UNK2_RETURN pc=0x%lx unk2=0x%x obj=0x%lx expected_cfg=0x%x caller=0x%lx sp=0x%lx\n", $pc, $w0, $x22, $w24, $x30, $sp
            continue
          end
          break *0x700a4974
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_CFG_RETURN pc=0x%lx cfg=0x%x expected_cfg=0x%x obj=0x%lx caller=0x%lx sp=0x%lx\n", $pc, $w0, $w24, $x22, $x30, $sp
            continue
          end
          break *0x700a497c
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_CFG_ACCEPTED pc=0x%lx obj=0x%lx lower=0x%lx upper=0x%lx count=0x%x finalize=0x%x sp=0x%lx\n", $pc, $x22, $x20, $x19, $w23, $w21, $sp
            if $x22 >= 0x70000000 && $x22 < 0x70140000
              x/16gx $x22
            end
            continue
          end
          break *0x700a4988
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_LOAD_MMIO_BASE pc=0x%lx obj=0x%lx lower=0x%lx upper=0x%lx sp=0x%lx\n", $pc, $x22, $x20, $x19, $sp
            if $x22 >= 0x70000000 && $x22 < 0x70140000
              x/4gx $x22
            end
            continue
          end
          break *0x700a498c
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_MMIO_BASE_LOADED pc=0x%lx mmio=0x%lx obj=0x%lx sp=0x%lx\n", $pc, $x8, $x22, $sp
            continue
          end
          break *0x700a4990
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_UNK1_CAP_LOADED pc=0x%lx cap=0x%lx obj=0x%lx sp=0x%lx\n", $pc, $x8, $x22, $sp
            continue
          end
          break *0x700a4a68
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_CFG_MISMATCH pc=0x%lx cfg=0x%x expected_cfg=0x%x obj=0x%lx sp=0x%lx\n", $pc, $w0, $w24, $x22, $sp
            continue
          end
          break *0x700a4ab4
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_BDIF_ENUM_SUCCESS_RETURN pc=0x%lx obj=0x%lx type_count=0x%x finalize=0x%x expected_cfg=0x%x sp=0x%lx\n", $pc, $x22, $w23, $w21, $w24, $sp
            if $x22 >= 0x70000000 && $x22 < 0x70140000
              x/16gx $x22
            end
            if $detach_after_ibec_aux_bdif_ready && $w23 == 0x2 && $w21 == 0x0
              printf "POST_IBEC_AUX_BDIF_READY_DETACH pc=0x%lx obj=0x%lx type_count=0x%x finalize=0x%x expected_cfg=0x%x\n", $pc, $x22, $w23, $w21, $w24
              detach
              quit
            end
            continue
          end
          break *0x7008b35c
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_USB_ENUM_RETURN pc=0x%lx result=0x%x x0=0x%lx usb_obj=0x%lx lower=0x%lx upper=0x%lx sp=0x%lx\n", $pc, $w0, $x0, $x27, $x20, $x21, $sp
            if $x27 >= 0x70000000 && $x27 < 0x70140000
              x/20gx $x27
            end
            continue
          end
          break *0x7008b370
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_USB_ENUM_ACCEPTED pc=0x%lx usb_obj=0x%lx mmio=0x%lx unit_offset=0x%x sp=0x%lx\n", $pc, $x19, *(unsigned long long *)($x19 + 96), *(unsigned int *)($x19 + 104), $sp
            x/24gx $x19
            continue
          end
        end
        if $trace_relocated_ibec_descriptor_presence
          break *0x700dbd3c
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_PRESENT_ENTER pc=0x%lx desc=0x%lx lower=0x%lx upper=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $sp, $x30
            if $x0 >= 0x70000000 && $x0 < 0x70140000
              x/8gx $x0
            end
            continue
          end
          break *0x700dbd58
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_PRESENT_BASIC_CHECK pc=0x%lx basic_ok=%u desc=0x%lx lower=0x%lx upper=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx\n", $pc, $w0, $x19, $x21, $x20, $x19, $x20, $x21
            if $x19 >= 0x70000000 && $x19 < 0x70140000
              x/8gx $x19
            end
            continue
          end
          break *0x700dbd80
          commands
            silent
            printf "POST_IBEC_DESCRIPTOR_PRESENT_FAIL pc=0x%lx desc=0x%lx lower=0x%lx upper=0x%lx sp=0x%lx\n", $pc, $x19, $x21, $x20, $sp
            if $x19 >= 0x70000000 && $x19 < 0x70140000
              printf "POST_IBEC_DESCRIPTOR_PRESENT_FAIL_FIELDS first=0x%lx size_or_end=0x%lx\n", *(unsigned long long *)$x19, *(unsigned long long *)($x19 + 16)
            end
            continue
          end
        end
        if $trace_relocated_ibec_root_build
          break *0x700d12e4
          commands
            silent
            printf "POST_IBEC_ROOT_TAG_TYPE_CHECK pc=0x%lx tag_ptr=0x%lx tag_type=0x%x root_tag_end=0x%lx root_aux=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x19, *(unsigned short *)($x19 + 26), *(unsigned long long *)($sp + 96), $x21, $sp, $x30
            continue
          end
          break *0x700d1344
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx root_tuple=0x%lx descriptor_tuple=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $sp + 0x88, $sp + 0x68, $sp, $x30
            x/24gx $sp + 0x68
            continue
          end
          break *0x700d1348
          commands
            silent
            set $ibec_root_build_return_seen = 1
            printf "POST_IBEC_ROOT_BUILD_RETURN pc=0x%lx result=0x%lx built_ptr=0x%lx built_end=0x%lx tuple0=0x%lx tuple1=0x%lx tuple2=0x%lx tuple3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, *(unsigned long long *)($sp + 104), *(unsigned long long *)($sp + 112), *(unsigned long long *)($sp + 136), *(unsigned long long *)($sp + 144), *(unsigned long long *)($sp + 152), *(unsigned long long *)($sp + 160), $sp, $x30
            x/24gx $sp + 0x68
            continue
          end
          break *0x700d7dac
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_CALLEE_RETURN pc=0x%lx result=0x%lx root_state=0x%lx image_ptr=0x%lx image_size=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x19, $x20, $x24, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7dd0
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7DD0 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7ddc
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7DDC pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7de8
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7DE8 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d15d8
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_EMPTY_FAIL pc=0x%lx built_ptr=0x%lx built_end=0x%lx sp=0x%lx x30=0x%lx\n", $pc, *(unsigned long long *)($sp + 104), *(unsigned long long *)($sp + 112), $sp, $x30
            continue
          end
          break *0x700d7df4
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7DF4 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e00
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E00 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e0c
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E0C pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e18
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E18 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e24
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E24 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e30
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E30 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e3c
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E3C pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e48
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E48 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e4c
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E4C pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7e58
          commands
            silent
            printf "POST_IBEC_ROOT_BUILD_FAIL_7E58 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x19, $x20, $x21, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700eeac0
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_FATAL_ABORT_HELPER_ENTRY pc=0x%lx caller=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x29=0x%lx\n", $pc, $x30, $x0, $x1, $x2, $x3, $sp, $x29
            x/48gx $sp
            continue
          end
          break *0x700a5158
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_EXCEPTION_VECTOR_INIT_ENTER pc=0x%lx base_arg=0x%lx global=0x70121ea0 old_begin=0x%lx old_current=0x%lx old_end=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, *(unsigned long long *)0x70121ea0, *(unsigned long long *)0x70121ea8, *(unsigned long long *)0x70121eb0, $sp, $x30
            continue
          end
          break *0x700a516c
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_EXCEPTION_VECTOR_INIT_STORE_PAIR pc=0x%lx base_arg=0x%lx begin=0x%lx current=0x%lx end_candidate=0x%lx global_reg=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x8, $x8, $x9, $x10, $sp, $x30
            continue
          end
          break *0x700a5170
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_EXCEPTION_VECTOR_INIT_STORE_LIMIT pc=0x%lx end_candidate=0x%lx global=0x70121ea0 stored_begin=0x%lx stored_current=0x%lx old_end=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x9, *(unsigned long long *)0x70121ea0, *(unsigned long long *)0x70121ea8, *(unsigned long long *)0x70121eb0, $sp, $x30
            continue
          end
          break *0x700a51cc
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_EXCEPTION_VECTOR_APPEND_LOAD pc=0x%lx global=0x70121ea0 begin=0x%lx current=0x%lx end=0x%lx value=0x%lx arg1=0x%lx arg2=0x%lx arg3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, *(unsigned long long *)0x70121ea0, *(unsigned long long *)0x70121ea8, *(unsigned long long *)0x70121eb0, $x0, $x1, $x2, $x3, $sp, $x30
            continue
          end
          break *0x700a51e8
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_EXCEPTION_VECTOR_APPEND_STORE pc=0x%lx dst=0x%lx loaded_begin=0x%lx loaded_end=0x%lx global_begin=0x%lx global_current=0x%lx global_end=0x%lx value=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x8, $x10, $x9, *(unsigned long long *)0x70121ea0, *(unsigned long long *)0x70121ea8, *(unsigned long long *)0x70121eb0, $x0, $sp, $x30
            continue
          end
          break *0x700a5264
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_EXCEPTION_VECTOR_APPEND_BOUNDS_FAIL pc=0x%lx global=0x70121ea0 begin=0x%lx current=0x%lx end=0x%lx value=0x%lx sp=0x%lx x30=0x%lx\n", $pc, *(unsigned long long *)0x70121ea0, *(unsigned long long *)0x70121ea8, *(unsigned long long *)0x70121eb0, $x0, $sp, $x30
            continue
          end
          break *0x700b50fc
          condition $bpnum $in_relocated_ibec && !$ibec_root_build_return_seen
          commands
            silent
            printf "POST_IBEC_FIREBLOOM_SLICE_VALIDATE_ENTER pc=0x%lx tuple=0x%lx requested=0x%lx caller=0x%lx sp=0x%lx x29=0x%lx\n", $pc, $x0, $x1, $x30, $sp, $x29
            if $x0 >= 0x70000000 && $x0 < 0x70140000
              printf "POST_IBEC_FIREBLOOM_SLICE_VALIDATE_TUPLE "
              x/4gx $x0
            end
            continue
          end
          break *0x700b5190
          condition $bpnum $in_relocated_ibec && !$ibec_root_build_return_seen
          commands
            silent
            printf "POST_IBEC_FIREBLOOM_SLICE_VALIDATE_FAIL pc=0x%lx tuple=0x%lx requested=0x%lx first=0x%lx current=0x%lx end=0x%lx metadata=0x%lx sp=0x%lx x29=0x%lx caller=0x%lx\n", $pc, $x20, $x19, *(unsigned long long *)$x20, *(unsigned long long *)($x20 + 8), *(unsigned long long *)($x20 + 16), *(unsigned long long *)($x20 + 24), $sp, $x29, $x30
            x/32gx $sp
            continue
          end
          break *0x700b5194
          condition $bpnum $in_relocated_ibec && !$ibec_root_build_return_seen
          commands
            silent
            printf "POST_IBEC_FIREBLOOM_UNALIGNED_PTR_PANIC pc=0x%lx tuple=0x%lx requested=0x%lx first=0x%lx current=0x%lx end=0x%lx metadata=0x%lx sp=0x%lx x29=0x%lx caller=0x%lx\n", $pc, $x20, $x19, *(unsigned long long *)$x20, *(unsigned long long *)($x20 + 8), *(unsigned long long *)($x20 + 16), *(unsigned long long *)($x20 + 24), $sp, $x29, $x30
            if *(unsigned long long *)($x20 + 24) >= 0x70000000 && *(unsigned long long *)($x20 + 24) < 0x70140000
              printf "POST_IBEC_FIREBLOOM_UNALIGNED_PTR_METADATA "
              x/8gx *(unsigned long long *)($x20 + 24)
            end
            continue
          end
          break *0x70088a20
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_PANIC_REPORT_ENTRY pc=0x%lx caller=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx x29=0x%lx\n", $pc, $x30, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp, $x29
            if $x0 >= 0x70000000 && $x0 < 0x70140000
              printf "POST_IBEC_PANIC_REPORT_STRING_X0 "
              x/s $x0
            end
            if $x1 >= 0x70000000 && $x1 < 0x70140000
              printf "POST_IBEC_PANIC_REPORT_STRING_X1 "
              x/s $x1
            end
            if $x3 >= 0x70000000 && $x3 < 0x70140000
              printf "POST_IBEC_PANIC_REPORT_STACK_X3\n"
              x/24gx $x3
            end
            x/64gx $sp
            continue
          end
          break *0x70088df0
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_PANIC_REPORT_FINAL_FORMAT_CALL pc=0x%lx caller_frame=0x%lx saved_caller=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx\n", $pc, $x29, *(unsigned long long *)($x29 + 8), $x0, $x1, $x2, $x3, $x20, $x21, $x22, $x23, $x24, $x25
            if $x20 >= 0x70000000 && $x20 < 0x70140000
              printf "POST_IBEC_PANIC_REPORT_BUFFER_X20 "
              x/s $x20
            end
            if $x22 >= 0x70000000 && $x22 < 0x70140000
              printf "POST_IBEC_PANIC_REPORT_STRING_X22 "
              x/s $x22
            end
            x/96gx $sp
            continue
          end
          break *0x70088e14
          condition $bpnum $in_relocated_ibec
          commands
            silent
            printf "POST_IBEC_PANIC_REPORT_RESET_CALL pc=0x%lx caller_frame=0x%lx saved_caller=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx\n", $pc, $x29, *(unsigned long long *)($x29 + 8), $x0, $x1, $x2, $x3, $x20, $x21, $x22, $x23, $x24, $x25
            if $x20 >= 0x70000000 && $x20 < 0x70140000
              printf "POST_IBEC_PANIC_REPORT_FINAL_TEXT "
              x/s $x20
            end
            x/96gx $sp
            continue
          end
          break *0x70085038
          commands
            silent
            printf "POST_IBEC_FATAL_RESET_ENTRY pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x70085078
          commands
            silent
            printf "POST_IBEC_FATAL_RESET_SYSTEM_RESET_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
            info registers x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x19 x20 x21 x22 x23 x24 x25 x26 x27 x28 x29 x30 sp pc
            if $x20 >= 0x70000000 && $x20 < 0x70140000
              printf "POST_IBEC_FATAL_RESET_STRING_X20 "
              x/s $x20
            end
            if $x22 >= 0x70000000 && $x22 < 0x70140000
              printf "POST_IBEC_FATAL_RESET_STRING_X22 "
              x/s $x22
            end
            x/96gx $sp
            continue
          end
          break *0x70086764
          commands
            silent
            printf "POST_IBEC_SERVICE_CALL_8_WRAPPER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
            continue
          end
          break *0x700866d8
          commands
            silent
            printf "POST_IBEC_SERVICE_CALL_9_WRAPPER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
            continue
          end
          break *0x70086718
          commands
            silent
            printf "POST_IBEC_SERVICE_CALL_0x84000000 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
            continue
          end
          break *0x700866fc
          commands
            silent
            printf "POST_IBEC_SERVICE_CALL_9_SVC pc=0x%lx svc=0xa0 x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
            continue
          end
          break *0x70086728
          commands
            silent
            printf "POST_IBEC_SERVICE_CALL_BOOTSTRAP_SVC pc=0x%lx svc=0xa0 x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
            continue
          end
        end
        if $trace_relocated_ibec_map_checks
          break *0x700d32b0
          commands
            silent
            printf "POST_IBEC_MAP_REQUEST_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d7f98
          commands
            silent
            printf "POST_IBEC_MAP_VALIDATE_ENTER pc=0x%lx base=0x%lx limit=0x%lx flags=0x%lx attr=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp, $x30
            x/32gx $sp
            continue
          end
          break *0x700d802c
          commands
            silent
            printf "POST_IBEC_MAP_VALIDATE_PRECHECK pc=0x%lx start=0x%lx end=0x%lx span=0x%lx flags=0x%x type=0x%x attr=0x%x map_ptr=0x%lx aux_ptr=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx\n", $pc, $x19, $x28, $x27, $w21, $w24, $w23, $x20, $x22, $x20, $x21, $sp
            continue
          end
          break *0x700d8374
          commands
            silent
            printf "POST_IBEC_MAP_VALIDATE_SUCCESS pc=0x%lx result=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x21, $sp, $x30
            continue
          end
          break *0x700d838c
          commands
            silent
            printf "POST_IBEC_MAP_VALIDATE_FAIL_PRECHECK line=3012 start=0x%lx end=0x%lx span=0x%lx flags=0x%x type=0x%x attr=0x%x map_ptr=0x%lx aux_ptr=0x%lx w9=0x%x w8=0x%x sp=0x%lx\n", $x19, $x28, $x27, $w21, $w24, $w23, $x20, $x22, $w9, $w8, $sp
            continue
          end
          break *0x700d83a4
          commands
            silent
            printf "POST_IBEC_MAP_VALIDATE_FAIL_MATCH line=3024 start=0x%lx end=0x%lx span=0x%lx flags=0x%x type=0x%x attr=0x%x map_ptr=0x%lx aux_ptr=0x%lx sp=0x%lx\n", $x19, $x28, $x27, $w21, $w24, $w23, $x20, $x22, $sp
            continue
          end
          break *0x700d83b0
          commands
            silent
            printf "POST_IBEC_MAP_VALIDATE_FAIL_KIND line=3031 start=0x%lx end=0x%lx span=0x%lx flags=0x%x type=0x%x attr=0x%x map_ptr=0x%lx aux_ptr=0x%lx sp=0x%lx\n", $x19, $x28, $x27, $w21, $w24, $w23, $x20, $x22, $sp
            continue
          end
          break *0x700d83bc
          commands
            silent
            printf "POST_IBEC_MAP_VALIDATE_FAIL_CAPABILITY line=3019 start=0x%lx end=0x%lx span=0x%lx flags=0x%x type=0x%x attr=0x%x map_ptr=0x%lx aux_ptr=0x%lx sp=0x%lx\n", $x19, $x28, $x27, $w21, $w24, $w23, $x20, $x22, $sp
            continue
          end
        end
      end
      if $trace_relocated_ibec_context_return
        break *0x700d15ac
        commands
          silent
          printf "POST_IBEC_CONTEXT_RETURN_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x8=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x8, $sp, $x30
          x/32gx $sp
          continue
        end
        break *0x700cc0e4
        commands
          silent
          printf "POST_IBEC_CONTEXT_RESTORE_FRAME pc=0x%lx frame_sp=0x%lx active_word=0x%x saved_lr=0x%lx saved_elr=0x%lx saved_spsr=0x%lx saved_ttbr1=0x%lx\n", $pc, $sp, *(unsigned int *)($sp + 312), *(unsigned long long *)($sp + 240), *(unsigned long long *)($sp + 248), *(unsigned long long *)($sp + 264), *(unsigned long long *)($sp + 304)
          x/14gx $sp + 224
          continue
        end
        break *0x700cc138
        commands
          silent
          printf "POST_IBEC_CONTEXT_RESTORE_ELR pc=0x%lx frame_sp=0x%lx restored_lr=0x%lx restored_elr=0x%lx saved_spsr=0x%lx sp=0x%lx\n", $pc, $sp, $x30, $x0, *(unsigned long long *)($sp + 264), $sp
          continue
        end
        break *0x700cc218
        commands
          silent
          printf "POST_IBEC_CONTEXT_ERET pc=0x%lx frame_sp=0x%lx restored_elr=0x%lx restored_spsr=0x%lx x0=0x%lx x1=0x%lx x30=0x%lx\n", $pc, $sp, *(unsigned long long *)($sp + 248), *(unsigned long long *)($sp + 264), $x0, $x1, $x30
          continue
        end
        break *0x700d15b0
        commands
          silent
          printf "POST_IBEC_CONTEXT_RETURNED_TO_PANIC pc=0x%lx sp=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x30=0x%lx\n", $pc, $sp, $x0, $x1, $x2, $x3, $x30
          continue
        end
      end
      if $trace_relocated_ibec_exceptions
        break *0x700cc818
        commands
          silent
          set $post_ibec_esr = $x8
          set $post_ibec_far = $x9
          set $post_ibec_elr = *(unsigned long long *)($x19 + 240)
          set $post_ibec_ec = ($post_ibec_esr >> 26) & 0x3f
          set $post_ibec_il = ($post_ibec_esr >> 25) & 0x1
          set $post_ibec_iss = $post_ibec_esr & 0x1ffffff
          printf "POST_IBEC_EXCEPTION_ESR_FAR pc=0x%lx frame=0x%lx esr=0x%lx ec=0x%lx il=%lu iss=0x%lx far=0x%lx saved_elr=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x19, $post_ibec_esr, $post_ibec_ec, $post_ibec_il, $post_ibec_iss, $post_ibec_far, $post_ibec_elr, $sp, $x30, $cpsr
          x/16gx $x19 + 224
          if $post_ibec_elr >= 0x7006c000 && $post_ibec_elr < 0x70130000
            x/8i $post_ibec_elr
          end
          continue
        end
        break *0x700cc82c
        commands
          silent
          printf "POST_IBEC_EXCEPTION_ELR_CLEANUP pc=0x%lx frame=0x%lx saved_elr=0x%lx saved_esr=0x%lx saved_far=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x19, *(unsigned long long *)($x19 + 240), *(unsigned long long *)($x19 + 848), *(unsigned long long *)($x19 + 856), $sp, $x30
          continue
        end
        break *0x700cc850
        commands
          silent
          printf "POST_IBEC_EXCEPTION_SECONDARY pc=0x%lx sp=0x%lx x0=0x%lx x1=0x%lx x30=0x%lx\n", $pc, $sp, $x0, $x1, $x30
          continue
        end
        break *0x700882e8
        commands
          silent
          printf "POST_IBEC_PANIC_LOG_ENTRY pc=0x%lx arg0=0x%lx line=%u sp=0x%lx x30=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx\n", $pc, $x0, $w1, $sp, $x30, $x19, $x20, $x21
          x/6gx $sp
          continue
        end
      end
      break *0x70088adc
      commands
        silent
        printf "POST_IBEC_TERMINAL pc=0x%lx sp=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x8=0x%lx x9=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx x23=0x%lx x24=0x%lx x25=0x%lx x26=0x%lx x27=0x%lx x28=0x%lx x29=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $sp, $x0, $x1, $x2, $x3, $x4, $x8, $x9, $x19, $x20, $x21, $x22, $x23, $x24, $x25, $x26, $x27, $x28, $x29, $x30, $cpsr
        x/48gx $sp
        continue
      end
      break *0x70088ae0
      commands
        silent
        printf "POST_IBEC_TERMINAL_RETURN pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
        continue
      end
      break *0x7006c438
      commands
        silent
        printf "POST_IBEC_HALT_LOOP pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
        detach
        quit
      end
    else
      detach
      quit
    end
  end
  continue
end

break *0x7007b878
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_FINAL_HANDOFF_CALLBACK_RETURNED x0=0x%lx pc=0x%lx\n", $x0, $pc
  continue
end

break *0x7007b880
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_FINAL_HANDOFF_FAIL_NO_READY_FRAME line=0x60 payload=0x%lx type=0x%lx\n", $x22, $x23
  continue
end

break *0x7007b898
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_FINAL_HANDOFF_FAIL_NO_CALLBACK line=0x84 payload=0x%lx type=0x%lx\n", $x22, $x23
  continue
end

break *0x7007ba00
condition $bpnum $phase == 1 && $seen_svc7
commands
  silent
  printf "IBEC_STAGE_SVC7_RETURNED_TO_PANIC payload=0x%lx arg1=0x%lx type=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $x30
  continue
end

break *0x700bfce4
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_STAGE_ASSERT_7232_PRE caller=0x%lx x0=0x%lx x1=0x%lx x8=0x%lx x9=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx sp=0x%lx\n", $x30, $x0, $x1, $x8, $x9, $x19, $x20, $x21, $x22, $sp
  x/16gx $sp
  continue
end

break *0x7006d5a0
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_DISPATCH_CALL desc=0x%lx lower=0x%lx upper=0x%lx wanted_tag=0x%x arg4=0x%lx arg5=0x%lx callback=0x%lx arg7=0x%lx stack_arg=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $w3, $x4, $x5, $x6, $x7, *(unsigned long long *)$sp, $x30
  x/16gx $x0
  set $dispatch_tag_base = *(unsigned long long *)$x0
  set $dispatch_tag_end = *(unsigned long long *)($x0 + 8)
  set $dispatch_object_base = *(unsigned long long *)($x0 + 32)
  set $dispatch_object_end = *(unsigned long long *)($x0 + 40)
  printf "IBEC_DISPATCH_TABLE tag_base=0x%lx tag_end=0x%lx object_base=0x%lx object_end=0x%lx count_word=%u\n", $dispatch_tag_base, $dispatch_tag_end, $dispatch_object_base, $dispatch_object_end, *(unsigned int *)($x0 + 68)
  x/32wx $dispatch_tag_base
  x/24gx $dispatch_object_base
  continue
end

break *0x7006d260
condition $bpnum $phase == 1
commands
  silent
  set $dispatch_bounds_error = 0
  printf "IBEC_DISPATCH_ENTER desc=0x%lx lower=0x%lx upper=0x%lx wanted_tag=0x%x arg4=0x%lx arg5=0x%lx callback=0x%lx arg7=0x%lx stack_arg=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $w3, $x4, $x5, $x6, $x7, *(unsigned long long *)$sp, $x30
  continue
end

break *0x7006d2e0
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_DISPATCH_SCAN index=%lu tag=0x%x wanted_tag=0x%x next_tag_offset=0x%lx object_offset=0x%lx desc=0x%lx\n", ($x8 / 4) - 1, $w11, $w21, $x8, $x9, $x0
  continue
end

break *0x7006d304
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_DISPATCH_MATCH tag=0x%x object=0x%lx object_offset=0x%lx desc=0x%lx\n", $w21, $x19, $x9, $x0
  x/16gx $x19
  x/32wx $x19
  continue
end

break *0x7006d378
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_DISPATCH_OBJECT object=0x%lx flag64=%u callback=0x%lx wanted_tag=0x%x arg1=0x%lx arg2=0x%lx arg3=0x%lx arg4=0x%lx arg5=0x%lx\n", $x19, *(unsigned char *)($x19 + 64), $x6, $w21, $x24, $x22, $x20, $x7, $x23
  continue
end

break *0x7006d3c4
condition $bpnum $phase == 1
commands
  silent
  set $dispatch_bounds_error = 1
  printf "IBEC_DISPATCH_BOUNDS_OR_TABLE_ERROR desc=0x%lx lower=0x%lx upper=0x%lx wanted_tag=0x%x x8=0x%lx x9=0x%lx x10=0x%lx x11=0x%lx x12=0x%lx x13=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $w21, $x8, $x9, $x10, $x11, $x12, $x13, $x30
  continue
end

break *0x7006d3c8
condition $bpnum $phase == 1
commands
  silent
  printf "IBEC_DISPATCH_NO_MATCH_OR_ERROR bounds_error=%u desc=0x%lx wanted_tag=0x%x last_scan_offset=0x%lx last_object_offset=0x%lx caller=0x%lx\n", $dispatch_bounds_error, $x0, $w21, $x8, $x9, $x30
  continue
end

break *0x7006d3c0
commands
  silent
  printf "IBEC_PAYLOAD_CALLBACK target=0x%lx type=0x%x arg1=0x%lx arg2=0x%lx arg3=0x%lx\n", $x6, $w0, $x1, $x2, $x3
  continue
end

break *0x700cfc60
commands
  silent
  printf "IBOOT_ERROR_A code=0x%x caller=0x%lx w28=0x%x tag=0x%x\n", $w0, $x30, $w28, *(unsigned int *)($sp+364)
  if $x30 == 0x7007088c
    printf "IBOOT_ERROR_A_OBJECT phase=%u object=0x%lx x8=0x%lx x9=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx flags=%u/%u/%u/%u/%u/%u/%u/%u\n", $phase, $x20, $x8, $x9, $x20, $x21, $x22, *(unsigned char *)($sp+828), *(unsigned char *)($sp+829), *(unsigned char *)($sp+709), *(unsigned char *)($sp+708), *(unsigned char *)($sp+808), *(unsigned char *)($sp+810), *(unsigned char *)($sp+879), *(unsigned char *)($sp+882)
    x/12wx $x20
    x/12gx $x29+56
  end
  continue
end

break *0x700cfdb8
commands
  silent
  printf "IBOOT_ERROR_B code=0x%x detail=0x%x caller=0x%lx\n", $w0, $w1, $x30
  continue
end

break *0x700b19ac
commands
  silent
  printf "IBEC_ALLOC_EMPTY x8=0x%lx x9=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx caller=0x%lx\n", $x8, $x9, $x20, $x21, $x22, $x30
  continue
end

break *0x7007be9c
commands
  silent
  printf "IBOOT_PANIC line=%u arg0=0x%lx caller=0x%lx pc=0x%lx\n", $w1, $x0, $x30, $pc
  info registers x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 x19 x20 x21 x22 x23 x24 x25 x26 x27 x28 x29 x30 sp pc
  bt
  detach
  quit
end

break *0x73fff000
commands
  silent
  if !$synthetic_handler_active
    continue
  end
  if $phase == 0
    printf "LPOL_HANDLER_RETURN x0=0x%lx w0=0x%x pc=0x%lx sentinel=0x%lx x30=0x%lx sp=0x%lx\n", $x0, $w0, $pc, $synthetic_return_addr, $x30, $sp
    set $phase = 1
    set $x0 = 0
    set $x1 = 0
    set $x2 = 0
    set $x3 = 0
    set $x30 = $synthetic_return_addr
    set $pc = 0x7006ee5c
    printf "IBEC_HANDLER_ENTER pc=0x%lx\n", $pc
    continue
  end
  printf "RESTORE_HANDLER_RETURN phase=%u x0=0x%lx w0=0x%x pc=0x%lx sentinel=0x%lx x30=0x%lx sp=0x%lx\n", $phase, $x0, $w0, $pc, $synthetic_return_addr, $x30, $sp
  set $synthetic_handler_active = 0
  detach
  quit
end

target remote 127.0.0.1:12345

# Enter the registered `lpolrestore` handler first.  On success the synthetic
# return breakpoint above immediately chains into the registered `firmware`
# handler for signed iBEC.
if !$start_from_avpbooter
  set $x0 = 0
  set $x1 = 0
  set $x2 = 0
  set $x3 = 0
  set $x30 = $synthetic_return_addr
  set $pc = 0x70073b98
end
continue
