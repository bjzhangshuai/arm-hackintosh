set pagination off
set confirm off
set architecture aarch64
set $error_count = 0

break *0x102b0c
commands
  silent
  printf "BNCH_PARSE_START tag=0x%lx manifest=0x%lx state=0x%lx\n", $x8, $x23, $x27
  x/16gx $x23
  continue
end

break *0x102b30
commands
  silent
  printf "BNCH_PARSE_RETURN result=%u parsed_ptr=0x%lx parsed_len=%lu\n", $w0, *(unsigned long long *)($sp+48), *(unsigned long long *)($sp+56)
  continue
end

break *0x102b40
commands
  silent
  printf "BNCH_PARSE_OK parsed_ptr=0x%lx parsed_len=%lu\n", *(unsigned long long *)($sp+48), *(unsigned long long *)($sp+56)
  continue
end

break *0x101de0
commands
  silent
  printf "IMAGE_READ_RETURN actual=%u expected=%u object=0x%lx\n", $w0, $w19, $x24
  continue
end

break *0x116d2c
commands
  silent
  set $error_count = $error_count + 1
  set $parent_lr = *(unsigned long long *)($x29 + 8)
  set $parent_fp = *(unsigned long long *)$x29
  set $grand_lr = *(unsigned long long *)($parent_fp + 8)
  printf "ERROR_CALL %u code=0x%x direct_lr=0x%lx parent_lr=0x%lx grand_lr=0x%lx\n", $error_count, $w0, $x30, $parent_lr, $grand_lr
  if $error_count == 20
    detach
    quit
  end
  continue
end

target remote 127.0.0.1:12345
continue
