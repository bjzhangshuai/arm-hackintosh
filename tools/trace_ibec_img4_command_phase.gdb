set pagination off
set confirm off
set architecture aarch64

# Attach after the bootstrap GDB has already injected signed iBSS, LocalPolicy,
# and iBEC, then keep QEMU running while the restore helper sends recovery
# commands.  This captures recovery-command IMG4 validation, not the earlier
# iBEC handoff validation.
set $img4_validate_count = 0
set $img4_validate_caller = 0
set $img4_parse_ptr = 0
set $img4_parse_end = 0
set $img4_parse_aux0 = 0
set $img4_parse_aux1 = 0
set $bootx_final_switch_seen = 0
set $bootx_handoff_candidate_seen = 0
set $bootx_notify_b_seen = 0
set $bootx_notify_b_callback = 0
set $bootx_notify_b_callback_seen = 0
set $bootx_notify_b_callback_slot_hits = 0
set $bootx_tail_release_seen = 0
set $bootx_tail_release_wait_hits = 0
set $bootx_tail_release_status_cleared_hits = 0
set $bootx_notify_b_drain_wait1_hits = 0
set $bootx_notify_b_drain_wait2_hits = 0

target remote 127.0.0.1:12345

# macOS 26.6 (25G72) VirtualMac2,1 iBEC.runtime-last.bin relocated at
# 0x7006c000.  This is the common validator used by RestoreRamDisk and
# RestoreDeviceTree command handlers.
break *0x7008af74
commands
  silent
  set $img4_validate_count = $img4_validate_count + 1
  set $img4_validate_caller = $x30
  printf "IBEC_CMD_IMG4_VALIDATE_ENTER index=%u caller=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx\n", $img4_validate_count, $x30, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp
  continue
end

break *0x7008afec
commands
  silent
  set $img4_parse_ptr = $x0
  set $img4_parse_end = $x1
  set $img4_parse_aux0 = $x2
  set $img4_parse_aux1 = $x3
  printf "IBEC_CMD_IMG4_PARSE_RETURN index=%u caller=0x%lx ptr=0x%lx end=0x%lx aux0=0x%lx aux1=0x%lx w0=0x%x\n", $img4_validate_count, $img4_validate_caller, $x0, $x1, $x2, $x3, $w0
  if $x0 != 0
    x/8wx $x0
  end
  continue
end

break *0x7008b060
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_RETURN index=%u caller=0x%lx result=0x%lx w0=0x%x parsed=0x%lx parsed_end=0x%lx aux0=0x%lx aux1=0x%lx\n", $img4_validate_count, $img4_validate_caller, $x0, $w0, $img4_parse_ptr, $img4_parse_end, $img4_parse_aux0, $img4_parse_aux1
  continue
end

break *0x7008b090
commands
  silent
  printf "IBEC_CMD_IMG4_FAILURE_PATH index=%u caller=0x%lx parsed=0x%lx deep_result=0x%lx w0=0x%x\n", $img4_validate_count, $img4_validate_caller, $img4_parse_ptr, $x19, $w0
  continue
end

break *0x7008b098
commands
  silent
  printf "IBEC_CMD_IMG4_VALIDATE_RETURN index=%u caller=0x%lx final=0x%lx w0=0x%x parsed=0x%lx deep_result=0x%lx\n", $img4_validate_count, $img4_validate_caller, $x0, $w0, $img4_parse_ptr, $x19
  continue
end

break *0x7008a590
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_ENTER parsed=0x%lx lower=0x%lx upper=0x%lx load=0x%lx load_size=0x%lx out0=0x%lx out1=0x%lx out2=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $x30, $sp
  if $x0 != 0
    x/12wx $x0
  end
  continue
end

break *0x7008a74c
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_TYPE_CHECK parsed=0x%lx payload_len=0x%x tag=0x%x comp=0x%x mode=%u status_slot=0x%x\n", $x26, *(unsigned int *)$x26, *(unsigned int *)($x26 + 4), *(unsigned int *)($x26 + 8), $w19, *(unsigned int *)($x29 - 100)
  continue
end

break *0x7008a7ec
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_PAYLOAD_CALL parsed=0x%lx lower=0x%lx upper=0x%lx load=0x%lx load_size=0x%lx status_slot=0x%x\n", $x26, $x25, $x24, $x22, $x21, *(unsigned int *)($x29 - 100)
  continue
end

break *0x7008a7f0
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_PAYLOAD_RETURN result=0x%lx w0=0x%x status_slot=0x%x parsed=0x%lx\n", $x0, $w0, *(unsigned int *)($x29 - 100), $x26
  continue
end

break *0x7008a66c
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_STATUS_MAP_CALL input=0x%lx w0=0x%x status_slot=0x%x parsed=0x%lx\n", $x0, $w0, *(unsigned int *)($x29 - 100), $x26
  continue
end

break *0x7008a670
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_STATUS_MAP_RETURN result=0x%lx w0=0x%x status_slot=0x%x parsed=0x%lx\n", $x0, $w0, *(unsigned int *)($x29 - 100), $x26
  continue
end

break *0x7008a68c
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_FINAL_BRANCH result=0x%lx w0=0x%x status_slot=0x%x parsed=0x%lx\n", $x0, $w0, *(unsigned int *)($x29 - 100), $x26
  continue
end

break *0x7008a6bc
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_SUCCESS status_slot=0x%x parsed=0x%lx\n", *(unsigned int *)($x29 - 100), $x26
  continue
end

break *0x7008a6b4
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_FAIL_AFTER_STATUS_MAP mapped=0x%lx w0=0x%x status_slot=0x%x parsed=0x%lx\n", $x0, $w0, *(unsigned int *)($x29 - 100), $x26
  continue
end

break *0x7008a7f4
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_TYPE_REJECT parsed=0x%lx tag=0x%x comp=0x%x mode=%u\n", $x26, *(unsigned int *)($x26 + 4), *(unsigned int *)($x26 + 8), $w19
  continue
end

break *0x7008a804
commands
  silent
  printf "IBEC_CMD_IMG4_DEEP_BOUNDS_REJECT parsed=0x%lx lower=0x%lx upper=0x%lx load=0x%lx load_size=0x%lx mode=%u\n", $x26, $x25, $x24, $x22, $x21, $w19
  continue
end

break *0x70071990
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_VALIDATE_ENTER x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $x30, $sp
  continue
end

break *0x70071c50
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_COMPONENT_POLICY_CALL manifest=0x%lx component=0x%lx component_len=0x%x x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx\n", $x0, $x20, $w25, $x3, $x4, $x5, $x6, $x7
  continue
end

break *0x70071c54
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_COMPONENT_POLICY_RETURN result=0x%lx w0=0x%x component_len=0x%x manifest=0x%lx\n", $x0, $w0, $w25, $x20
  continue
end

break *0x70071c5c
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_EARLY_FAIL result=0x%lx w0=0x%x component_len=0x%x manifest=0x%lx\n", $x0, $w0, $w25, $x20
  continue
end

break *0x700726e0
commands
  silent
  printf "IBEC_CMD_IMG4_COMPONENT_POLICY_ENTER x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $x30, $sp
  if $x0 != 0
    x/12wx $x0
  end
  continue
end

break *0x70072730
commands
  silent
  printf "IBEC_CMD_IMG4_COMPONENT_TYPE_CHECK component=0x%lx payload_len=0x%x tag=0x%x comp=0x%x expected_len=0x%lx dest=0x%lx\n", $x24, *(unsigned int *)$x24, *(unsigned int *)($x24 + 4), *(unsigned int *)($x24 + 8), $x19, $x23
  continue
end

break *0x700727d8
commands
  silent
  printf "IBEC_CMD_IMG4_COMPONENT_ZMEM_PRECHECK_RETURN result=0x%lx w0=0x%x expected_len=0x%lx decoded_len_slot=0x%lx component=0x%lx\n", $x0, $w0, $x19, *(unsigned long long *)($sp + 48), $x24
  continue
end

break *0x70072800
commands
  silent
  printf "IBEC_CMD_IMG4_COMPONENT_ZMEM_LENGTH_CHECK decoded_len=0x%lx expected_len=0x%lx component=0x%lx\n", *(unsigned long long *)($sp + 48), $x19, $x24
  continue
end

break *0x70072844
commands
  silent
  printf "IBEC_CMD_IMG4_COMPONENT_ZMEM_COPY_OR_OK decoded_len=0x%lx expected_len=0x%lx dest=0x%lx component=0x%lx original_dest=0x%lx\n", *(unsigned long long *)($sp + 48), $x19, $x23, $x24, *(unsigned long long *)($x24 + 16)
  continue
end

break *0x70072818
commands
  silent
  printf "IBEC_CMD_IMG4_COMPONENT_FAIL_RETURN code=0x%lx w0=0x%x component=0x%lx expected_len=0x%lx decoded_len_slot=0x%lx\n", $x0, $w0, $x24, $x19, *(unsigned long long *)($sp + 48)
  continue
end

break *0x7007281c
commands
  silent
  printf "IBEC_CMD_IMG4_COMPONENT_RETURN result=0x%lx w0=0x%x component=0x%lx expected_len=0x%lx decoded_len_slot=0x%lx\n", $x0, $w0, $x24, $x19, *(unsigned long long *)($sp + 48)
  continue
end

break *0x700e5fa8
commands
  silent
  printf "IBEC_CMD_ERROR_HELPER_A code=0x%x caller=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx\n", $w0, $x30, $x1, $x2, $x3, $sp
  continue
end

break *0x700e6100
commands
  silent
  printf "IBEC_CMD_ERROR_HELPER_B code=0x%x caller=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx\n", $w0, $x30, $x1, $x2, $x3, $sp
  continue
end

break *0x70071cc4
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_AFTER_COMPONENT_OK component_len=0x%x dest=0x%lx out_ptr=0x%lx flags_byte13=0x%x\n", $w25, $x23, $x21, *(unsigned char *)($x20 + 13)
  continue
end

break *0x70071cf4
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_RANGE_CHECK_RETURN result=0x%lx w0=0x%x base=0x%lx size=0x%lx limit=0x%lx\n", $x0, $w0, $x0, $x1, $x3
  continue
end

break *0x70071cf8
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_RANGE_CHECK_FAIL w0=0x%x\n", $w0
  continue
end

break *0x70071dac
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_DIGEST_OR_COPY_RETURN result=0x%lx w0=0x%x measured_len=0x%lx len_slot=0x%lx\n", $x0, $w0, $x1, *(unsigned long long *)($sp + 368)
  continue
end

break *0x70071dc8
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_MANIFEST_PARSE_RETURN result=0x%lx w0=0x%x manifest_ctx=0x%lx key_slot=0x%lx\n", $x0, $w0, $sp + 0x368, $sp + 0x15c
  continue
end

break *0x70071e4c
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_MANIFEST_PROPERTY_RETURN result=0x%lx w0=0x%x code_base=0x%x flag551=0x%x\n", $x0, $w0, $w24, *(unsigned char *)($sp + 551)
  continue
end

break *0x70071ebc
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_POLICY_BUNDLE_RETURN result=0x%lx w0=0x%x object_tag=0x%x lpol_like=0x%x\n", $x0, $w0, *(unsigned int *)($sp + 348), *(unsigned int *)($sp + 348)
  continue
end

break *0x70071fd0
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_TRUST_EVAL_RETURN result=0x%lx w0=0x%x object_tag=0x%x branch_flag=0x%x\n", $x0, $w0, *(unsigned int *)($sp + 348), *(unsigned char *)($sp + 863)
  continue
end

break *0x70071fd8
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_TRUST_EVAL_FAIL result=0x%lx w0=0x%x code_base=0x%x\n", $x0, $w0, $w24
  continue
end

break *0x70072038
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_4CC_LOOKUP_RETURN result=0x%lx w0=0x%x object_tag=0x%x wanted_ptr=0x%lx\n", $x0, $w0, *(unsigned int *)($sp + 348), $x21
  continue
end

break *0x700721bc
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_MEASURE_PREP_RETURN result=0x%lx w0=0x%x len_slot=0x%x data_slot=0x%lx\n", $x0, $w0, *(unsigned int *)($sp + 212), *(unsigned long long *)($sp + 160)
  continue
end

break *0x70072210
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_MEASURE_RETURN result=0x%lx w0=0x%x len=0x%lx object_tag=0x%x\n", $x0, $w0, $x5, *(unsigned int *)($sp + 348)
  continue
end

break *0x700722b4
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_CHIP_OR_DOMAIN_FAIL code_base=0x%x object_tag=0x%x byte812=0x%x byte813=0x%x\n", $w24, *(unsigned int *)($sp + 348), *(unsigned char *)($sp + 812), *(unsigned char *)($sp + 813)
  continue
end

break *0x700722e8
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_POLICY_MAIN_OK object_tag=0x%x len=0x%lx out_len=0x%lx\n", *(unsigned int *)($sp + 348), $x19, $x28
  continue
end

break *0x70072358
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_FINAL_MANIFEST_RETURN result=0x%lx w0=0x%x decoded_len=0x%lx expected_len=0x%lx\n", $x0, $w0, *(unsigned long long *)($sp + 360), *(unsigned long long *)($sp + 120)
  continue
end

break *0x70072390
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_BOARD_POLICY_RETURN result=0x%lx w0=0x%x object_tag=0x%x\n", $x0, $w0, *(unsigned int *)($sp + 348)
  continue
end

break *0x7007242c
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_COPY_DONE decoded_len=0x%lx expected_len=0x%lx dest=0x%lx object_tag=0x%x\n", $x28, $x19, $x22, *(unsigned int *)($sp + 348)
  continue
end

break *0x70072268
commands
  silent
  printf "IBEC_CMD_IMG4_PAYLOAD_SUCCESS_EXIT_PRE result=0x%lx w0=0x%x out_status_ptr=0x%lx object_tag=0x%x\n", $x0, $w0, $x26, *(unsigned int *)($sp + 348)
  continue
end

break *0x700b53dc
commands
  silent
  printf "IBEC_CMD_COMPARE_WRAPPER_ENTER x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx stack_len=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, *(unsigned long long *)$sp, $x30, $sp
  if $x0 != 0
    x/64bx $x0
  end
  if $x4 != 0
    x/64bx $x4
  end
  if $x6 != 0
    x/64bx $x6
  end
  continue
end

break *0x700b5430
commands
  silent
  printf "IBEC_CMD_COMPARE_BYTES lhs=0x%lx rhs=0x%lx len=0x%lx caller=0x%lx\n", $x0, $x1, $x2, $x30
  if $x0 != 0
    x/64bx $x0
  end
  if $x1 != 0
    x/64bx $x1
  end
  continue
end

break *0x700720a4
commands
  silent
  printf "IBEC_CMD_COMPARE_RETURN result=0x%lx w0=0x%x caller_after_compare=0x700720a4\n", $x0, $w0
  continue
end

# bootx/load_kernelcache path.  A direct recovery command named
# "kernelcache" returns a restore-status failure before reaching the IMG4
# validator; bootx is the path that references /boot/kernelcache and calls the
# kernelcache loader.
break *0x70070e80
commands
  silent
  printf "IBEC_CMD_BOOTX_KERNELCACHE_STAGE_ENTER x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $x30, $sp
  continue
end

break *0x70070ef4
commands
  silent
  printf "IBEC_CMD_BOOTX_KERNELCACHE_LOAD_CALL path=0x%lx name=0x%lx end=0x%lx tag=0x%x load=0x%lx load_size=0x%lx out=0x%lx\n", $x0, $x1, $x2, $w4, $x5, $x6, $x7
  x/s $x0
  x/s $x1
  continue
end

break *0x70070f00
commands
  silent
  printf "IBEC_CMD_BOOTX_KERNELCACHE_LOAD_RETURN result=0x%lx w0=0x%x kernelcache_cmd=0x%lx\n", $x0, $w0, $x26
  continue
end

break *0x700770e4
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_ENTER path=0x%lx name=0x%lx end=0x%lx args3=0x%lx tag=0x%x load=0x%lx load_size=0x%lx out=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $x2, $x3, $w4, $x5, $x6, $x7, $x30, $sp
  x/s $x0
  continue
end

break *0x70076e14
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_ENTER path=0x%lx name=0x%lx expected_tag=0x%x lower=0x%lx upper=0x%lx out=0x%lx caller=0x%lx sp=0x%lx\n", $x0, $x1, $w2, $x4, $x5, $x7, $x30, $sp
  x/s $x0
  continue
end

break *0x70076e64
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_OPEN_RETURN image=0x%lx lower=0x%lx upper=0x%lx aux=0x%lx\n", $x0, $x1, $x2, $x3
  continue
end

break *0x70076f60
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_VALIDATE_CALL image=0x%lx image_len=0x%lx load=0x%lx load_size=0x%lx out0=0x%lx out1=0x%lx out2=0x%lx tag_slot=0x%x\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, *(unsigned int *)($x29 - 100)
  continue
end

break *0x70076f64
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_VALIDATE_RETURN result=0x%lx w0=0x%x tag_slot=0x%x\n", $x0, $w0, *(unsigned int *)($x29 - 100)
  continue
end

break *0x70076f68
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_IMAGE_INVALID result=0x%lx w0=0x%x tag_slot=0x%x\n", $x0, $w0, *(unsigned int *)($x29 - 100)
  continue
end

break *0x700770ac
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_SUCCESS kernel_base=0x%lx kernel_len=0x%lx metadata=0x%lx\n", $x19, $x25, $x23
  continue
end

break *0x700770b0
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_RETURN result=0x%lx w0=0x%x kernel_base=0x%lx kernel_len=0x%lx\n", $x0, $w0, $x19, $x25
  continue
end

break *0x70077130
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_OPEN_RETURN x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx\n", $x0, $x1, $x2, $x3
  continue
end

break *0x7007722c
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_ALT_VALIDATE_CALL x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx tag_slot=0x%x\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, *(unsigned int *)($x29 - 100)
  continue
end

break *0x70077230
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_ALT_VALIDATE_RETURN result=0x%lx w0=0x%x tag_slot=0x%x\n", $x0, $w0, *(unsigned int *)($x29 - 100)
  continue
end

break *0x70077234
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_IMAGE_INVALID result=0x%lx w0=0x%x tag_slot=0x%x\n", $x0, $w0, *(unsigned int *)($x29 - 100)
  continue
end

break *0x700772cc
commands
  silent
  printf "IBEC_CMD_LOAD_KERNELCACHE_SUCCESS x0=0x%lx w0=0x%x kernel_ptr=0x%lx kernel_len=0x%lx\n", $x0, $w0, $x22, $x20
  continue
end

break *0x700c33c4
commands
  silent
  printf "IBEC_CMD_POST_BOOT_ALIGN_ENTER kind=0x%x slot=0x%lx value=0x%lx align=0x%lx caller=0x%lx sp=0x%lx\n", $w0, $x1, $x2, $x3, $x30, $sp
  continue
end

break *0x700c3414
commands
  silent
  printf "IBEC_CMD_POST_BOOT_ALIGN_FLAG flag=0x%x base=0x%lx slot_index=0x%lx align=0x%lx value=0x%lx\n", $w8, $x22, $x21, $x19, $x2
  continue
end

break *0x700c3440
commands
  silent
  printf "IBEC_CMD_POST_BOOT_ALIGN_REGISTER code=0x%x value=0x%lx align=0x%lx slot_index=0x%lx base=0x%lx\n", $w0, $x2, $x19, $x21, $x22
  continue
end

break *0x700c3478
commands
  silent
  printf "IBEC_CMD_POST_BOOT_ALIGN_REMAINDER_PRE stored=0x%lx align=0x%lx slot_index=0x%lx base=0x%lx\n", *(unsigned long long *)($x22 + $x21), $x19, $x21, $x22
  continue
end

break *0x700c34b0
commands
  silent
  printf "IBEC_CMD_POST_BOOT_ALIGN_REJECT stored=0x%lx align=0x%lx remainder=0x%lx slot_index=0x%lx base=0x%lx\n", $x0, $x19, $x8, $x21, $x22
  continue
end

break *0x700813d8
commands
  silent
  printf "IBEC_CMD_POST_BOOT_ALIGN_CALLER_RETURN_PRE result=0x%lx caller=0x%lx sp=0x%lx x29=0x%lx\n", $x19, $x30, $sp, $x29
  if $x30 >= 0x7006c000 && $x30 < 0x70130000
    x/24i $x30
  end
  continue
end

break *0x700813e4
commands
  silent
  printf "IBEC_CMD_POST_BOOT_ALIGN_CALLER_RETAB result=0x%lx caller=0x%lx sp=0x%lx x29=0x%lx\n", $x0, $x30, $sp, $x29
  continue
end

break *0x7006dfac
commands
  silent
  printf "IBEC_CMD_BOOTX_POST_ALIGN_OK pc=0x%lx result=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7006dfec
commands
  silent
  printf "IBEC_CMD_BOOTX_MAIN_HANDOFF_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp, $x30
  continue
end

break *0x7006ca4c
commands
  silent
  printf "IBEC_CMD_BOOTX_MAIN_HANDOFF_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x4=0x%lx x5=0x%lx x6=0x%lx x7=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $sp, $x30
  continue
end

break *0x7006cb00
commands
  silent
  printf "IBEC_CMD_BOOTX_BOOT_ARGS_RETURN result=0x%lx w0=0x%x sp=0x%lx x30=0x%lx\n", $x0, $w0, $sp, $x30
  continue
end

break *0x7006cb40
commands
  silent
  printf "IBEC_CMD_BOOTX_BOOT_ARGS_SUCCESS_BRANCH pc=0x%lx result=0x%lx w0=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x0, $w0, $sp, $x30
  continue
end

break *0x7006cb50
commands
  silent
  printf "IBEC_CMD_BOOTX_PREPARE_IBOOT_HANDOFF_CALL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70087dec
commands
  silent
  printf "IBEC_CMD_BOOTX_PREPARE_IBOOT_HANDOFF_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x7006cb60
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $sp, $x30
  continue
end

break *0x70087cc8
commands
  silent
  set $bootx_final_switch_seen = 1
  set $bootx_handoff_candidate_seen = 0
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x70087cf8
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_SVC6 pc=0x%lx kind=0x%lx payload=0x%lx aux=0x%lx x0=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x20, $x21, $x19, $x0, $x19, $x20, $x21, $x22, $sp, $x30, $cpsr
  x/i $pc
  continue
end

break *0x70087cfc
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_AFTER_SVC6 pc=0x%lx x0=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x0, $x19, $x20, $x21, $x22, $sp, $x30, $cpsr
  x/12i $pc
  continue
end

break *0x70087d00
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_POST_SVC_HELPER_RETURN pc=0x%lx x0=0x%lx w22=0x%x x19=0x%lx x20=0x%lx x21=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $w22, $x19, $x20, $x21, $sp, $x30
  continue
end

break *0x70087d18
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_ERROR_HELPER_B_CALL pc=0x%lx code=0x%x kind=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $w0, $x1, $sp, $x30
  continue
end

break *0x70087d40
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_KIND_NOTIFY_A pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70087d54
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_KIND_NOTIFY_B pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x700843d0
condition $bpnum $bootx_final_switch_seen
commands
  silent
  set $bootx_notify_b_seen = 1
  set $bootx_notify_b_drain_wait1_hits = 0
  set $bootx_notify_b_drain_wait2_hits = 0
  printf "IBEC_CMD_BOOTX_NOTIFY_B_ENTER pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x0, $sp, $x30, $cpsr
  continue
end

break *0x700843e8
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_AFTER_SET_KIND_FLAG pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x700843ec
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_HELPER_CALL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70090fc8
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_ENTER pc=0x%lx sp=0x%lx x30=0x%lx flag1=0x%x flag2=0x%x counter=0x%x\n", $pc, $sp, $x30, *(unsigned char *)0x70121df9, *(unsigned char *)0x70121dfa, *(unsigned int *)0x70121df4
  continue
end

break *0x70090fec
condition $bpnum $bootx_notify_b_seen && $bootx_notify_b_drain_wait1_hits < 8
commands
  silent
  set $bootx_notify_b_drain_wait1_hits = $bootx_notify_b_drain_wait1_hits + 1
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_WAIT_FLAG1 hit=%u flag1=0x%x flag2=0x%x counter=0x%x pc=0x%lx\n", $bootx_notify_b_drain_wait1_hits, *(unsigned char *)0x70121df9, *(unsigned char *)0x70121dfa, *(unsigned int *)0x70121df4, $pc
  continue
end

break *0x70090ff4
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_FLAG1 pc=0x%lx w8=0x%x flag1=0x%x flag2=0x%x counter=0x%x\n", $pc, $w8, *(unsigned char *)0x70121df9, *(unsigned char *)0x70121dfa, *(unsigned int *)0x70121df4
  continue
end

break *0x70091010
condition $bpnum $bootx_notify_b_seen && $bootx_notify_b_drain_wait2_hits < 8
commands
  silent
  set $bootx_notify_b_drain_wait2_hits = $bootx_notify_b_drain_wait2_hits + 1
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_WAIT_FLAG2 hit=%u flag1=0x%x flag2=0x%x counter=0x%x pc=0x%lx\n", $bootx_notify_b_drain_wait2_hits, *(unsigned char *)0x70121df9, *(unsigned char *)0x70121dfa, *(unsigned int *)0x70121df4, $pc
  continue
end

break *0x70091018
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_FLAG2 pc=0x%lx flag1=0x%x flag2=0x%x counter=0x%x\n", $pc, *(unsigned char *)0x70121df9, *(unsigned char *)0x70121dfa, *(unsigned int *)0x70121df4
  continue
end

break *0x70090644
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_ENTER pc=0x%lx sp=0x%lx x30=0x%lx flag1=0x%x flag2=0x%x counter=0x%x\n", $pc, $sp, $x30, *(unsigned char *)0x70121df9, *(unsigned char *)0x70121dfa, *(unsigned int *)0x70121df4
  continue
end

break *0x70090654
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  x/i $pc
  continue
end

break *0x7009065c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_AFTER_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7009066c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_POST_BRANCH pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008e86c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_FINAL_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  x/i $pc
  continue
end

break *0x7008e874
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_FINAL_AFTER_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008e560
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_SLOT pc=0x%lx prior_x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008e56c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  set $bootx_notify_b_callback = $x0
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_LOADED pc=0x%lx callback=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $bootx_notify_b_callback, $sp, $x30
  continue
end

break *0x7008e578
condition $bpnum $bootx_notify_b_seen
commands
  silent
  set $bootx_notify_b_callback = $x0
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_BRAAZ pc=0x%lx callback=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $bootx_notify_b_callback, $sp, $x30
  x/32i $bootx_notify_b_callback
  continue
end

break *0x7008e57c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_MISSING pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7008d618
condition $bpnum $bootx_notify_b_seen
commands
  silent
  set $bootx_notify_b_callback_seen = 1
  set $bootx_notify_b_callback_slot_hits = 0
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_ENTER pc=0x%lx sp=0x%lx x30=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx\n", $pc, $sp, $x30, $x0, $x1, $x2, $x3
  continue
end

break *0x7008d630
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET0_CALL pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008d634
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET0_RETURN pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008d638
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET80_CALL pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008d63c
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET80_RETURN pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008d650
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_PENDING_RELEASE_CALL pc=0x%lx pending=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x8, $sp, $x30
  continue
end

break *0x7008d674
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_SLOT_LOOP_START pc=0x%lx table=0x%lx slot=0x%lx remaining=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x21, $x19, $x22, $sp, $x30
  continue
end

break *0x7008d69c
condition $bpnum $bootx_notify_b_callback_seen && $bootx_notify_b_callback_slot_hits < 16
commands
  silent
  set $bootx_notify_b_callback_slot_hits = $bootx_notify_b_callback_slot_hits + 1
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_SLOT hit=%u pc=0x%lx slot=0x%lx remaining=0x%lx active=0x%x sp=0x%lx x30=0x%lx\n", $bootx_notify_b_callback_slot_hits, $pc, $x19, $x22, *(unsigned int *)($x19 + 8), $sp, $x30
  continue
end

break *0x7008d6bc
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_SLOT_RELEASE_RETURN pc=0x%lx slot=0x%lx remaining=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x19, $x22, $x0, $sp, $x30
  continue
end

break *0x7008d6d0
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_LOOP_DONE pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7008d6ec
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAILCALL_C5B0 pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7008c5b0
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_ENTER pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7008c5e4
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_RELEASE_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x7008c5e8
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_RELEASE_RETURN pc=0x%lx x0=0x%lx x19=0x%lx flag1=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x0, $x19, *(unsigned char *)($x19 + 1), $sp, $x30
  continue
end

break *0x7008c5ec
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_FLAG_LOADED pc=0x%lx w8=0x%x x19=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $w8, $x19, $sp, $x30
  continue
end

break *0x7008c5f4
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_PATH pc=0x%lx x19=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x19, $sp, $x30
  continue
end

break *0x7008c600
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_AFTER_BOUND pc=0x%lx x0=0x%lx x9=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x9, $sp, $x30
  continue
end

break *0x7008c604
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_RELEASE_CALL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x700a4b44
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  set $bootx_tail_release_seen = 1
  set $bootx_tail_release_wait_hits = 0
  set $bootx_tail_release_status_cleared_hits = 0
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_ENTER pc=0x%lx desc=0x%lx lower=0x%lx upper=0x%lx base=0x%lx status404=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, *(unsigned long long *)$x0, *(unsigned int *)(*(unsigned long long *)$x0 + 0x404), $sp, $x30
  continue
end

break *0x700a4bd8
condition $bpnum $bootx_tail_release_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_WAIT_SETUP pc=0x%lx desc=0x%lx base=0x%lx slots=0x%x status404=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x21, *(unsigned long long *)$x21, *(unsigned char *)($x21 + 12), *(unsigned int *)(*(unsigned long long *)$x21 + 0x404), $sp, $x30
  continue
end

break *0x700a4be8
condition $bpnum $bootx_tail_release_seen && $bootx_tail_release_status_cleared_hits < 12
commands
  silent
  set $bootx_tail_release_status_cleared_hits = $bootx_tail_release_status_cleared_hits + 1
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_STATUS_CLEARED hit=%u pc=0x%lx desc=0x%lx base=0x%lx status404=0x%x sp=0x%lx x30=0x%lx\n", $bootx_tail_release_status_cleared_hits, $pc, $x21, *(unsigned long long *)$x21, *(unsigned int *)(*(unsigned long long *)$x21 + 0x404), $sp, $x30
  continue
end

break *0x700a4bf4
condition $bpnum $bootx_tail_release_seen && $bootx_tail_release_wait_hits < 12
commands
  silent
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_STATUS_READ_CALL hit=%u pc=0x%lx desc=0x%lx base=0x%lx status404=0x%x sp=0x%lx x30=0x%lx\n", $bootx_tail_release_wait_hits + 1, $pc, $x21, *(unsigned long long *)$x21, *(unsigned int *)(*(unsigned long long *)$x21 + 0x404), $sp, $x30
  continue
end

break *0x700a4bf8
condition $bpnum $bootx_tail_release_seen && $bootx_tail_release_wait_hits < 12
commands
  silent
  set $bootx_tail_release_wait_hits = $bootx_tail_release_wait_hits + 1
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_STATUS_READ_RETURN hit=%u pc=0x%lx value=0x%x desc=0x%lx base=0x%lx status404=0x%x sp=0x%lx x30=0x%lx\n", $bootx_tail_release_wait_hits, $pc, $w0, $x21, *(unsigned long long *)$x21, *(unsigned int *)(*(unsigned long long *)$x21 + 0x404), $sp, $x30
  continue
end

break *0x700a4c00
condition $bpnum $bootx_tail_release_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_WAIT_DONE pc=0x%lx desc=0x%lx base=0x%lx status404=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x21, *(unsigned long long *)$x21, *(unsigned int *)(*(unsigned long long *)$x21 + 0x404), $sp, $x30
  continue
end

break *0x700a4c08
condition $bpnum $bootx_tail_release_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_RETURN_VALUE pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x700a4c24
condition $bpnum $bootx_tail_release_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_TAIL_RELEASE_RETAB pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7008c608
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_RELEASE_RETURN pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7008c60c
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_BUFFER_RELEASE_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  continue
end

break *0x7008c620
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_RETURN pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7008c62c
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_BOUNDS_FAIL pc=0x%lx x0=0x%lx x9=0x%lx x19=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x9, $x19, $sp, $x30
  continue
end

break *0x700976e4
condition $bpnum $bootx_notify_b_callback_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_OUTER_RETURN pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x700968a0
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_FALLBACK_ENTER pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70090670
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_RETURN_PREP pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70090688
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_RETURN_BRANCH pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7009161c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_RETAB_SHIM pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7009101c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_CLEANUP_A pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7009078c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_B_ENTER pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x7009079c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_B_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  x/i $pc
  continue
end

break *0x700907a4
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_B_AFTER_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70091020
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_CLEANUP_B pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70091024
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x7009102c
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_SVC_C5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70091050
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_RETURN pc=0x%lx flag1=0x%x flag2=0x%x counter=0x%x sp=0x%lx x30=0x%lx\n", $pc, *(unsigned char *)0x70121df9, *(unsigned char *)0x70121dfa, *(unsigned int *)0x70121df4, $sp, $x30
  continue
end

break *0x700843f0
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_SVC5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x0, $sp, $x30, $cpsr
  x/i $pc
  continue
end

break *0x700843f4
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_AFTER_SVC5 pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x0, $sp, $x30, $cpsr
  continue
end

break *0x700843f8
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_CALL pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70084088
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_ENTER pc=0x%lx x0=0x%lx x1=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $sp, $x30
  continue
end

break *0x700840b4
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_STATE_MMIO_WRITE pc=0x%lx mmio=0x%lx w0=0x%x w1=0x%x w2=0x%x w3=0x%x old0=0x%x old4=0x%x\n", $pc, $x10, $w0, $w1, $w2, $w3, *(unsigned int *)$x10, *(unsigned int *)($x10 + 4)
  continue
end

break *0x700840cc
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_RETURN pc=0x%lx w0=0x%x w1=0x%x sp=0x%lx x30=0x%lx\n", $pc, $w0, $w1, $sp, $x30
  continue
end

break *0x700843fc
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_RETURNED pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70084404
condition $bpnum $bootx_notify_b_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_NOTIFY_B_RETURN pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70087d58
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_FLUSH_A_CALL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70087d5c
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_FLUSH_B_CALL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70087d60
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_PANIC_OR_LOG_CALL pc=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $sp, $x30
  continue
end

break *0x70087d88
condition $bpnum $bootx_final_switch_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_FINAL_SWITCH_LOG_CALL pc=0x%lx x0=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $sp, $x30
  continue
end

break *0x70087d8c
condition $bpnum $bootx_final_switch_seen
commands
  silent
  set $bootx_handoff_candidate_seen = 1
  printf "IBEC_CMD_BOOTX_HANDOFF_KIND_CHECK kind=0x%x payload=0x%lx aux=0x%lx raw_kind=0x%lx sp=0x%lx x30=0x%lx\n", $w22, $x21, $x19, $x20, $sp, $x30
  continue
end

break *0x70087d94
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_NON_STAGE2_FLAG_CALL kind=0x%x sp=0x%lx x30=0x%lx\n", $w22, $sp, $x30
  continue
end

break *0x70086020
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_SET_BOOT_FLAG pc=0x%lx x8=0x%lx w9=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x8, $w9, $sp, $x30
  continue
end

break *0x70086518
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_BOOT_FLAG_WRITE pc=0x%lx x8=0x%lx w9=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x8, $w9, $sp, $x30
  continue
end

break *0x70087d98
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_ARGS_PREP pc=0x%lx payload=0x%lx aux=0x%lx kind=0x%x sp=0x%lx x30=0x%lx\n", $pc, $x21, $x19, $w20, $sp, $x30
  continue
end

break *0x70087da4
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_WRAPPER_CALL pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $sp, $x30
  continue
end

break *0x70087da8
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_WRAPPER_ENTER pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  x/16i $pc
  continue
end

break *0x70087db8
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_SVC7 pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  x/i $pc
  continue
end

break *0x70087dbc
condition $bpnum $bootx_handoff_candidate_seen
commands
  silent
  printf "IBEC_CMD_BOOTX_HANDOFF_SVC7_RETURNED pc=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x0, $x1, $x2, $x3, $sp, $x30
  x/24i $pc
  continue
end

break *0x700cc818
commands
  silent
  set $post_ibec_esr = $x8
  set $post_ibec_far = $x9
  set $post_ibec_elr = *(unsigned long long *)($x19 + 240)
  set $post_ibec_ec = ($post_ibec_esr >> 26) & 0x3f
  set $post_ibec_il = ($post_ibec_esr >> 25) & 0x1
  set $post_ibec_iss = $post_ibec_esr & 0x1ffffff
  printf "IBEC_CMD_EXCEPTION_ESR_FAR pc=0x%lx frame=0x%lx esr=0x%lx ec=0x%lx il=%lu iss=0x%lx far=0x%lx saved_elr=0x%lx sp=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $x19, $post_ibec_esr, $post_ibec_ec, $post_ibec_il, $post_ibec_iss, $post_ibec_far, $post_ibec_elr, $sp, $x30, $cpsr
  x/16gx $x19 + 224
  if $post_ibec_elr >= 0x7006c000 && $post_ibec_elr < 0x70130000
    x/24i $post_ibec_elr
  end
  continue
end

break *0x700cc82c
commands
  silent
  printf "IBEC_CMD_EXCEPTION_ELR_CLEANUP pc=0x%lx frame=0x%lx saved_elr=0x%lx saved_esr=0x%lx saved_far=0x%lx sp=0x%lx x30=0x%lx\n", $pc, $x19, *(unsigned long long *)($x19 + 240), *(unsigned long long *)($x19 + 848), *(unsigned long long *)($x19 + 856), $sp, $x30
  continue
end

break *0x7006c438
commands
  silent
  printf "IBEC_CMD_HALT_LOOP pc=0x%lx sp=0x%lx x0=0x%lx x1=0x%lx x2=0x%lx x3=0x%lx x30=0x%lx cpsr=0x%lx\n", $pc, $sp, $x0, $x1, $x2, $x3, $x30, $cpsr
  continue
end

break *0x700882e8
commands
  silent
  printf "IBEC_CMD_PANIC_LOG_ENTRY pc=0x%lx arg0=0x%lx line=%u sp=0x%lx x30=0x%lx x19=0x%lx x20=0x%lx x21=0x%lx\n", $pc, $x0, $w1, $sp, $x30, $x19, $x20, $x21
  x/6gx $sp
  continue
end

# Keep the inferior running until the smoke runner terminates this post-boot
# tracer after the restore helper finishes.
continue
