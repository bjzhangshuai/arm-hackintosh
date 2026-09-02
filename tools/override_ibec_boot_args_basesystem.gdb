set pagination off
set confirm off
set architecture aarch64

# Diagnostic BaseSystem boot at the verified final iBEC -> XNU callback.
# Refuse to write unless both the BootArgs layout and restore rd=md0 prefix match.
target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $macvm_boot_args = $x1
  set $macvm_boot_args_revision = *(unsigned short *)$macvm_boot_args
  set $macvm_boot_args_version = *(unsigned short *)($macvm_boot_args + 2)
  set $macvm_command_line = $macvm_boot_args + 0x6c
  printf "MACVM_BASESYSTEM_BOOT_ARGS_BEFORE addr=%#lx revision=%u version=%u\n", $macvm_boot_args, $macvm_boot_args_revision, $macvm_boot_args_version
  x/s $macvm_command_line

  if $macvm_boot_args_revision != 3 || $macvm_boot_args_version != 2
    printf "MACVM_BASESYSTEM_BOOT_ARGS_REFUSED unexpected-layout\n"
    detach
    quit 70
  end

  if *(unsigned int *)$macvm_command_line != 0x6d3d6472 || *(unsigned short *)($macvm_command_line + 4) != 0x3064
    printf "MACVM_BASESYSTEM_BOOT_ARGS_REFUSED unexpected-command-line\n"
    detach
    quit 71
  end

  python
import gdb

command_line = int(gdb.parse_and_eval("$macvm_command_line"))
override = b"rd=disk0s1 serial=3 -v -noprogress debug=0x144 keepsyms=1 wdt=-1\0"
gdb.selected_inferior().write_memory(command_line, override)
  end

  printf "MACVM_BASESYSTEM_BOOT_ARGS_AFTER\n"
  x/s $macvm_command_line
  detach
  quit
end

continue
