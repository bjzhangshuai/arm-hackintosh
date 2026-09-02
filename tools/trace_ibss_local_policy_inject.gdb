set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 restore probe.  Run only in the
# disposable Linux validation VM after signed iBSS reaches remote boot.  The
# policy is signed by a dedicated Apple TSS request whose nsih binds it to the
# current iBSS-stage ticket.
set $payload_addr = 0x72e00000
set $payload_size = 3046

break *0x70073bc0
commands
  silent
  printf "LPOL_FILESIZE_ORIGINAL value=%lu\n", $x0
  restore /home/macvm/macos-restore/26.6/local-policy-fixed-rnd-713471fb-bnch32/Ap.LocalPolicy.fixed-rnd-713471fb-bnch32.img4 binary $payload_addr
  set $x0 = $payload_size
  printf "LPOL_INJECTED addr=0x%lx size=%u\n", $payload_addr, $payload_size
  continue
end

break *0x70073bd0
commands
  silent
  printf "LPOL_LOADADDR_ORIGINAL value=0x%lx\n", $x0
  set $x0 = $payload_addr
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

break *0x700c56c8
commands
  silent
  printf "LPOL_HANDLER_RETURN x0=0x%lx w0=0x%x pc=0x%lx\n", $x0, $w0, $pc
  detach
  quit
end

break *0x7007e6dc
commands
  silent
  printf "LPOL_MANIFEST_VALIDATE addr=0x%lx size=%lu ctx=0x%lx mode=%u\n", $x0, $x1, $x2, $w4
  x/8gx $sp
  continue
end

break *0x7007e124
commands
  silent
  printf "LPOL_MANIFEST_OBJECT_CREATE addr=0x%lx size=%lu end=0x%lx mode=%u slot=%u\n", $x0, $x1, $x2, $w4, $w5
  continue
end

break *0x7007e1f4
commands
  silent
  printf "LPOL_MANIFEST_OBJECT_RETURN result=0x%x detail=0x%x object=0x%lx\n", $w0, *(unsigned int *)($sp+52), $x19
  continue
end

break *0x7007e754
commands
  silent
  printf "LPOL_MANIFEST_OBJECT_RESULT object=0x%lx span_start=0x%lx span_end=0x%lx\n", $x0, $x1, $x2
  continue
end

break *0x700cfc60
commands
  silent
  printf "LPOL_ERROR_CODE code=0x%x caller=0x%lx\n", $w0, $x30
  continue
end

break *0x7007226c
commands
  silent
  printf "LPOL_PROPERTY_ERROR code=0x%x descriptor=0x%lx manifest=0x%lx context=0x%lx\n", $w0, $x20, $x21, $x22
  info registers x19 x20 x21 x22 x23 x24 x25 x26 x27 x28
  printf "LPOL_CURRENT_BNCH_HASH\n"
  x/48bx $sp+0x70
  set $manifest_bnch = *(unsigned long long *)($x20+0x88)
  set $manifest_bnch_size = *(unsigned long long *)($x20+0x90)
  printf "LPOL_MANIFEST_BNCH ptr=0x%lx size=%lu\n", $manifest_bnch, $manifest_bnch_size
  if $manifest_bnch != 0
    x/48bx $manifest_bnch
  end
  x/32gx $x20
  continue
end

# Trace the BNCH data-property comparison without changing its result.  This
# distinguishes ticket contents from malformed range/context arguments caused
# by entering the command handler on the wrong iBoot task.
break *0x7007287c
commands
  silent
  printf "LPOL_DATA_COMPARE_ENTER mode=%lu property=0x%lx descriptor=0x%lx context=0x%lx expected_start=0x%lx expected_end=0x%lx\n", $x0, $x1, $x2, $x3, $x6, $x7
  continue
end

break *0x700728c4
commands
  silent
  set $parsed_ptr = *(unsigned long long *)($sp+8)
  set $parsed_size = *(unsigned int *)($sp+20)
  set $expected_size = *(unsigned long long *)($x29+32)
  printf "LPOL_DATA_PARSE_RETURN result=%u parsed=0x%lx parsed_size=%u expected_size=%lu\n", $w0, $parsed_ptr, $parsed_size, $expected_size
  if $parsed_ptr != 0
    x/48bx $parsed_ptr
  end
  continue
end

break *0x700728f4
commands
  silent
  printf "LPOL_DATA_COMPARE_CALL parsed=0x%lx parsed_end=0x%lx expected_start=0x%lx expected_end=0x%lx expected_size=%lu\n", $x0, $x0+$x8, $x6, $x7, $x8
  x/48bx $x0
  if $x6 != 0
    x/48bx $x6
  end
  continue
end

break *0x700a34dc
condition $bpnum $x30 == 0x700728f8
commands
  silent
  printf "LPOL_RANGE_COMPARE_ENTER data=0x%lx data_start=0x%lx data_end=0x%lx context=0x%lx expected_start=0x%lx expected_end=0x%lx aux_start=0x%lx aux_end=0x%lx\n", $x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7
  x/48bx $x0
  if $x4 != 0
    x/48bx $x4
  end
  continue
end

break *0x70072920
commands
  silent
  printf "LPOL_DATA_COMPARE_RETURN result=0x%x\n", $w0
  continue
end

break *0x70075520
commands
  silent
  printf "LPOL_PROPERTY_VALIDATE_A manifest=0x%lx expected=0x%lx context=0x%lx callback=0x%lx\n", $x0, $x1, $x3, $x4
  x/48bx $x1
  continue
end

break *0x700d25fc
commands
  silent
  printf "LPOL_PROPERTY_VALIDATE_B manifest=0x%lx expected=0x%lx context=0x%lx output=0x%lx\n", $x0, $x1, $x3, $x4
  x/48bx $x1
  continue
end

break *0x70070dd4
commands
  silent
  printf "LPOL_PROPERTY_VALIDATE_RETURN result=0x%x manifest=0x%lx expected=0x%lx\n", $w0, $x25, $sp+0x378
  x/48bx $sp+0x378
  continue
end

target remote 127.0.0.1:12345

# Enter the registered `lpolrestore` handler on the idle command-task stack.
set $x0 = 0
set $x1 = 0
set $x2 = 0
set $x3 = 0
set $x30 = 0x700c56c8
set $pc = 0x70073b98
continue
