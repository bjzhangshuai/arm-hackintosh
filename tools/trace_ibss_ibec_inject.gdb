set pagination off
set confirm off
set architecture aarch64

# macOS 26.6 (25G72) VirtualMac2,1 restore probe.  Run only in the
# disposable Linux validation VM after the signed iBSS has reached its remote
# boot wait loop.  This substitutes the missing VZ host transport but leaves
# iBSS's IMG4 authentication and handoff path intact.
set $payload_size = 381357

break *0x7006eeb0
commands
  silent
  printf "IBEC_BUFFER addr=0x%lx\n", $x0
  restore /home/macvm/macos-restore/26.6/restore-chain/iBEC.fixed-rnd-713471fb.img4 binary $x0
  printf "IBEC_INJECTED addr=0x%lx size=%u\n", $x0, $payload_size
  continue
end

break *0x7006eebc
commands
  silent
  printf "IBEC_FILESIZE_ORIGINAL value=%u\n", $w0
  set $w0 = $payload_size
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

break *0x7006d554
commands
  silent
  printf "IBEC_MANIFEST_VALIDATE_RETURN result=%u\n", $w0
  continue
end

break *0x7006d3c0
commands
  silent
  printf "IBEC_PAYLOAD_CALLBACK target=0x%lx type=0x%x arg1=0x%lx arg2=0x%lx arg3=0x%lx\n", $x6, $w0, $x1, $x2, $x3
  continue
end

break *0x70070874
commands
  silent
  printf "IBEC_MANIFEST_OBJECT_CHECK object=0x%lx lower=0x%lx upper=0x%lx limit_word=0x%x caller=0x%lx\n", $x20, $x22, $x21, *(unsigned int *)$x20, $x30
  x/12wx $x20
  x/12gx $x29+56
  continue
end

break *0x70070884
commands
  silent
  printf "IBEC_MANIFEST_OBJECT_ERROR_BUILD object=0x%lx w8=0x%x x8=0x%lx x9=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx caller=0x%lx\n", $x20, $w8, $x8, $x9, $x20, $x21, $x22, $x30
  x/12wx $x20
  x/12gx $x29+56
  continue
end

break *0x700cfc60
commands
  silent
  printf "IBOOT_ERROR_A code=0x%x caller=0x%lx\n", $w0, $x30
  if $x30 == 0x7007088c
    printf "IBOOT_ERROR_A_OBJECT object=0x%lx x8=0x%lx x9=0x%lx x20=0x%lx x21=0x%lx x22=0x%lx\n", $x20, $x8, $x9, $x20, $x21, $x22
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
  detach
  quit
end

target remote 127.0.0.1:12345

# Borrow the currently idle iBSS task stack and enter the registered
# `firmware` command handler with argc=0.  PACIBSP signs the supplied return
# address; on a clean handoff the handler does not return here.
set $x0 = 0
set $x1 = 0
set $x2 = 0
set $x3 = 0
set $x30 = 0x700c56c8
set $pc = 0x7006ee5c
continue
