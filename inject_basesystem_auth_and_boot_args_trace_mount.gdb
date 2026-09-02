set pagination off
set confirm off
set architecture aarch64

# Diagnostic BaseSystem handoff at the verified final iBEC -> XNU callback.
target remote 127.0.0.1:12345

break *0x70087c8c
commands
  silent
  set $macvm_boot_args = $x1
  set $macvm_boot_args_revision = *(unsigned short *)$macvm_boot_args
  set $macvm_boot_args_version = *(unsigned short *)($macvm_boot_args + 2)
  set $macvm_command_line = $macvm_boot_args + 0x6c
  printf "MACVM_BASESYSTEM_HANDOFF_BEFORE addr=%#lx revision=%u version=%u\n", $macvm_boot_args, $macvm_boot_args_revision, $macvm_boot_args_version
  x/s $macvm_command_line

  if $macvm_boot_args_revision != 3 || $macvm_boot_args_version != 2
    printf "MACVM_BASESYSTEM_HANDOFF_REFUSED unexpected-layout\n"
    detach
    quit 70
  end

  if *(unsigned int *)$macvm_command_line != 0x6d3d6472 || *(unsigned short *)($macvm_command_line + 4) != 0x3064
    printf "MACVM_BASESYSTEM_HANDOFF_REFUSED unexpected-command-line\n"
    detach
    quit 71
  end

  set $macvm_basesystem_inject_ok = 0
  python
import gdb
import os
import struct
import sys

sys.path.insert(0, "/home/macvm/src/macvm/tools")
from apple_device_tree import (
    find_node,
    memory_map_region,
    parse_device_tree,
    replace_property_value_in_place,
    replace_properties_exact_span,
)
from validate_ramdisk_override import (
    validate_image_path,
    validate_physical_region,
)

try:
    inferior = gdb.selected_inferior()
    boot_args = int(gdb.parse_and_eval("$macvm_boot_args"))
    memory_fields = inferior.read_memory(boot_args + 0x08, 24).tobytes()
    virt_base, phys_base, memory_size = struct.unpack("<QQQ", memory_fields)
    dt_fields = inferior.read_memory(boot_args + 0x60, 12).tobytes()
    device_tree_virtual, device_tree_length = struct.unpack("<QI", dt_fields)
    if memory_size < 1024 * 1024 * 1024 or memory_size > 36 * 1024 * 1024 * 1024:
        raise ValueError(f"unsafe BootArgs memory size {memory_size}")
    if not virt_base <= device_tree_virtual < virt_base + memory_size:
        raise ValueError(
            f"DeviceTree virtual address 0x{device_tree_virtual:x} is outside BootArgs RAM"
        )
    device_tree_physical = device_tree_virtual - virt_base + phys_base
    if not phys_base <= device_tree_physical < phys_base + memory_size:
        raise ValueError(
            f"DeviceTree physical address 0x{device_tree_physical:x} is outside BootArgs RAM"
        )
    if device_tree_length < 4096 or device_tree_length > 1024 * 1024:
        raise ValueError(f"unexpected DeviceTree length {device_tree_length}")
    flattened = inferior.read_memory(device_tree_physical, device_tree_length).tobytes()
    root = parse_device_tree(flattened, allow_zero_padding=True)
    logical_tree = flattened[:root.end]
    mapped_base, capacity = memory_map_region(logical_tree, "DeviceTree")
    if mapped_base != device_tree_physical:
        raise ValueError(
            f"DeviceTree memory-map base 0x{mapped_base:x} != physical 0x{device_tree_physical:x}"
        )
    if capacity < device_tree_length or capacity > 1024 * 1024:
        raise ValueError(
            f"unsafe DeviceTree capacity {capacity} for length {device_tree_length}"
        )

    blob_path = os.environ.get("MACVM_BASESYSTEM_AUTH_BLOB", "")
    if not blob_path.startswith("/home/macvm/macos-restore/26.6/"):
        raise ValueError("MACVM_BASESYSTEM_AUTH_BLOB is outside the staged restore tree")
    with open(blob_path, "rb") as handle:
        auth_blob = handle.read(4097)
    if not auth_blob or len(auth_blob) > 4096:
        raise ValueError(f"unexpected BaseSystem auth blob length {len(auth_blob)}")
    if b"\x16\x04IM4P\x16\x04csys" not in auth_blob[:32]:
        raise ValueError("BaseSystem auth blob is not a csys IM4P")

    ramdisk_path = os.environ.get("MACVM_RAMDISK_OVERRIDE_IMAGE", "")
    ramdisk_address_literal = os.environ.get("MACVM_RAMDISK_OVERRIDE_ADDRESS", "")
    if not ramdisk_address_literal:
        raise ValueError("MACVM_RAMDISK_OVERRIDE_ADDRESS is required")
    ramdisk_resolved, ramdisk_size = validate_image_path(
        ramdisk_path, allowed_root="/home/macvm/macos-restore/26.6"
    )
    try:
        ramdisk_address = int(ramdisk_address_literal, 0)
    except ValueError as error:
        raise ValueError("MACVM_RAMDISK_OVERRIDE_ADDRESS is not an integer") from error
    validate_physical_region(
        address=ramdisk_address,
        size=ramdisk_size,
        memory_base=phys_base,
        memory_size=memory_size,
    )

    current_ramdisk = memory_map_region(logical_tree, "RAMDisk")
    current_reservation = memory_map_region(logical_tree, "MemoryMapReserved-0")
    if current_ramdisk[1] == 0:
        raise ValueError("firmware RAMDisk mapping is unexpectedly empty")
    if current_reservation != (0, 0):
        raise ValueError("MemoryMapReserved-0 is already in use")

    secure_boot_hashes = find_node(
        root, "/device-tree/chosen/secure-boot-hashes"
    )
    replaced_hash_names = ("rtsc", "rdsk", "rdtr", "rkrn")
    replaced_hashes = tuple(
        secure_boot_hashes.property(name) for name in replaced_hash_names
    )
    if any(item.length != 48 for item in replaced_hashes):
        raise ValueError("unexpected restore secure-boot hash length")

    updated = replace_properties_exact_span(
        logical_tree,
        node_path="/device-tree/chosen/secure-boot-hashes",
        old_names=replaced_hash_names,
        replacements=(
            # Do not set bit 31 in the encoded length.  This XNU DeviceTree
            # walker consumes the raw uint32 length; bit 31 made its next
            # pointer exactly 0x80000000 bytes out of bounds in boot13.
            ("base-system-volume-auth-blob", auth_blob, False),
            ("macvm-auth-padding", b"\0" * 32, False),
        ),
    )
    if len(updated) != len(logical_tree):
        raise ValueError("exact-span replacement changed the DeviceTree length")
    injected = find_node(
        parse_device_tree(updated), "/device-tree/chosen/secure-boot-hashes"
    ).property("base-system-volume-auth-blob")
    if injected.secure or injected.length != len(auth_blob):
        raise ValueError("BaseSystem auth property has an unsafe encoded length")
    # The remote-restore DeviceTree has no boot-objects-path.  XNU reads it
    # directly from /chosen before honoring bsdmgpath.  Reuse the all-zero,
    # invalid apfs-preboot-uuid slot at exactly the same encoded size so no
    # signed DeviceTree offset moves.
    updated = replace_properties_exact_span(
        updated,
        node_path="/device-tree/chosen",
        old_names=("apfs-preboot-uuid",),
        replacements=(("boot-objects-path", b"/\0" + b"\0" * 36, False),),
    )
    boot_objects_path = find_node(
        parse_device_tree(updated), "/device-tree/chosen"
    ).property("boot-objects-path")
    if (
        boot_objects_path.secure
        or boot_objects_path.length != 38
        or boot_objects_path.value[:2] != b"/\0"
        or any(boot_objects_path.value[2:])
    ):
        raise ValueError("boot-objects-path injection is malformed")

    ramdisk_mapping = struct.pack("<QQ", ramdisk_address, ramdisk_size)
    updated = replace_property_value_in_place(
        updated,
        node_path="/device-tree/chosen/memory-map",
        name="RAMDisk",
        value=ramdisk_mapping,
    )
    updated = replace_property_value_in_place(
        updated,
        node_path="/device-tree/chosen/memory-map",
        name="MemoryMapReserved-0",
        value=ramdisk_mapping,
    )
    if memory_map_region(updated, "RAMDisk") != (ramdisk_address, ramdisk_size):
        raise ValueError("RAMDisk DeviceTree mapping did not persist")
    if memory_map_region(updated, "MemoryMapReserved-0") != (
        ramdisk_address,
        ramdisk_size,
    ):
        raise ValueError("RAMDisk reservation did not persist")
    updated_allocation = updated.ljust(device_tree_length, b"\0")
    inferior.write_memory(device_tree_physical, updated_allocation)

    # The synthetic validation RAMDisk is deliberately a single APFS volume.
    # It therefore does not advertise membership in a System/Data volume group
    # and cannot provide the separate Recovery-role volume that production
    # Apple media normally mounts here.  Patch only those two volume-group bit
    # tests and the bsd_find_basesystem_dmg call to vfs_mount_recovery(), after
    # validating the BootKC mapping and every exact macOS 26.6 instruction.
    # The subsequent Apple BaseSystem lookup, authentication, mount and root
    # pivot remain unmodified.
    bootkc_base, bootkc_ro_size = memory_map_region(logical_tree, "BootKC-ro")
    nop_instruction = bytes.fromhex("1f2003d5")
    kernel_patches = (
        ("volume-group-capability", 0x318442C, bytes.fromhex("48200036"), nop_instruction),
        ("volume-group-validity", 0x3184434, bytes.fromhex("0820c036"), nop_instruction),
        ("recovery-mount", 0x318449C, bytes.fromhex("b9bef397"), bytes.fromhex("00008052")),
        # Avoid probing the known APFS BaseSystem device as HFS.  Boot22 proved
        # this probe was not the source of EBUSY, but returning EINVAL here
        # removes an invalid cross-filesystem probe while preserving the APFS
        # fallback and all authentication checks.
        ("skip-hfs-probe", 0x329B81C, bytes.fromhex("4b99ef97"), bytes.fromhex("c0028052")),
    )
    if bootkc_base & 0xFFF:
        raise ValueError(f"BootKC-ro base 0x{bootkc_base:x} is not page aligned")
    if bootkc_ro_size < max(item[1] for item in kernel_patches) + 4 or bootkc_ro_size > 128 * 1024 * 1024:
        raise ValueError(f"unexpected BootKC-ro size 0x{bootkc_ro_size:x}")
    validate_physical_region(
        address=bootkc_base,
        size=bootkc_ro_size,
        memory_base=phys_base,
        memory_size=memory_size,
    )
    if inferior.read_memory(bootkc_base, 4).tobytes() != bytes.fromhex("cffaedfe"):
        raise ValueError("BootKC-ro does not begin with a Mach-O header")
    patched_addresses = {}
    for patch_name, patch_offset, expected_instruction, replacement_instruction in kernel_patches:
        patch_address = bootkc_base + patch_offset
        observed_instruction = inferior.read_memory(patch_address, 4).tobytes()
        if observed_instruction != expected_instruction:
            raise ValueError(
                f"macOS 26.6 {patch_name} instruction does not match the reviewed BootKC"
            )
        inferior.write_memory(patch_address, replacement_instruction)
        if inferior.read_memory(patch_address, 4).tobytes() != replacement_instruction:
            raise ValueError(f"{patch_name} BootKC patch did not persist")
        patched_addresses[patch_name] = patch_address
    recovery_mount_call = patched_addresses["recovery-mount"]

    command_line = boot_args + 0x6c
    override = (
        b"rd=md0 serial=3 -v -noprogress debug=0x144 keepsyms=1 wdt=-1 "
        # Boot23b proved that di_root_image_ext reused md0's already-mounted
        # APFS container for the nested BaseSystem image.  XNU's dedicated
        # imageboot path copies the image to an independent RAM block device,
        # preventing that container/volume alias without bypassing root auth.
        b"-bsdmgroot -bsdmgroot-ramdisk\0"
    )
    inferior.write_memory(command_line, override)
    gdb.write(
        "MACVM_BASESYSTEM_AUTH_INJECTED "
        f"dt_virtual=0x{device_tree_virtual:x} dt_physical=0x{device_tree_physical:x} "
        f"old_logical_length={len(logical_tree)} new_logical_length={len(updated)} "
        f"bootargs_length={device_tree_length} capacity={capacity} blob={len(auth_blob)} "
        f"phys_base=0x{phys_base:x} memory_size=0x{memory_size:x} "
        f"ramdisk={ramdisk_resolved} ramdisk_address=0x{ramdisk_address:x} "
        f"ramdisk_size=0x{ramdisk_size:x} bootkc_base=0x{bootkc_base:x} "
        f"recovery_mount_call=0x{recovery_mount_call:x}\n"
    )
    gdb.set_convenience_variable("macvm_basesystem_inject_ok", 1)
except Exception as error:
    gdb.write(f"MACVM_BASESYSTEM_HANDOFF_REFUSED {error}\n")
  end

  if $macvm_basesystem_inject_ok != 1
    detach
    quit 72
  end

  printf "MACVM_BASESYSTEM_HANDOFF_AFTER\n"
  x/s $macvm_command_line
  continue
end

# macOS 26.6 ARM64_VMAPPLE uses the deterministic 0x19344000 BootKC slide in
# this validation environment.  Keep the signed restore chain and the handoff
# mutations above unchanged, then observe the exact VFS/APFS path which returns
# EBUSY while imageboot pivots to arm64eBaseSystem.dmg.  These breakpoints only
# read registers and guest memory.
hbreak *0xfffffe00231cafa4
commands 2
  silent
  printf "XNU_MOUNT_COMMON_BEFORE devvp=%#lx mp=%#lx ctx=%#lx\n", $x19, $x26, $x23
  if $x19 != 0
    x/32gx $x19
  end
  if $x26 != 0
    x/16gx $x26
  end
  continue
end

hbreak *0xfffffe00231cafb0
commands 3
  silent
  printf "XNU_MOUNT_COMMON_VCOUNT devvp=%#lx mp=%#lx vcount=%u mnt_flag_byte=%#x\n", $x19, $x26, $w0, *(unsigned char *)($x26 + 0x71)
  continue
end

hbreak *0xfffffe0022c579e8
commands 4
  silent
  printf "XNU_APFS_VFSOP_MOUNT_ENTER mp=%#lx devvp=%#lx data=%#lx ctx=%#lx\n", $x0, $x1, $x2, $x3
  if $x1 != 0
    x/32gx $x1
  end
  if $x0 != 0
    x/20gx $x0
  end
  continue
end

hbreak *0xfffffe0022c58590
commands 5
  silent
  printf "XNU_APFS_MOUNT_CALL nx=%#lx args=%#lx options=%#lx out=%#lx outer_mp=%#lx outer_devvp=%#lx\n", $x27, $x24, $x2, $x3, $x20, $x22
  if $x27 != 0
    x/40gx $x27
  end
  if $x19 != 0
    x/24gx $x19
  end
  if $x22 != 0
    x/24gx $x22
  end
  continue
end

hbreak *0xfffffe0022c58594
commands 6
  silent
  printf "XNU_APFS_MOUNT_RETURN error=%u nx=%#lx args=%#lx outer_mp=%#lx outer_devvp=%#lx\n", $w0, $x27, $x24, $x20, $x22
  continue
end

hbreak *0xfffffe0022ca9ee4
commands 7
  silent
  printf "XNU_APFS_OBJ_GET_RETURN error=%u nx=%#lx args=%#lx object_slot=%#lx object=%#lx\n", $w0, $x22, $x19, $sp + 0x30, *(unsigned long *)($sp + 0x30)
  continue
end

hbreak *0xfffffe0022ca9f38
commands 8
  silent
  printf "XNU_APFS_EXISTING_OBJECT_BUSY object=%#lx state150=%#lx stateca0=%#lx flags128=%#lx state364=%#x\n", $x19, *(unsigned long *)($x19 + 0x150), *(unsigned long *)($x19 + 0xca0), *(unsigned long *)($x19 + 0x128), *(unsigned int *)($x19 + 0x364)
  continue
end

hbreak *0xfffffe0022ca9f80
commands 9
  silent
  printf "XNU_APFS_EXISTING_OBJECT_EBUSY object=%#lx state150=%#lx stateca0=%#lx flags128=%#lx state364=%#x\n", $x19, *(unsigned long *)($x19 + 0x150), *(unsigned long *)($x19 + 0xca0), *(unsigned long *)($x19 + 0x128), *(unsigned int *)($x19 + 0x364)
  continue
end

hbreak *0xfffffe0022ca9f9c
commands 10
  silent
  printf "XNU_APFS_RESTORE_STATE_CONFLICT object=%#lx flags129=%#x state364=%#x\n", $x19, *(unsigned char *)($x19 + 0x129), *(unsigned int *)($x19 + 0x364)
  continue
end

hbreak *0xfffffe0022caa15c
commands 11
  silent
  printf "XNU_APFS_INCOMPATIBLE_FEATURES_EBUSY object=%#lx feature_word=%#lx\n", $x19, *(unsigned long *)($x19 + 0x128)
  continue
end

hbreak *0xfffffe0022ca9fd0
commands 12
  silent
  printf "XNU_APFS_EBUSY_RETURN object=%#lx nx=%#lx options=%#lx out=%#lx\n", $x19, $x22, $x21, $x20
  if $x19 != 0
    x/48gx $x19
  end
  if $x22 != 0
    x/32gx $x22
  end
  bt 20
  detach
  quit
end

# Distinguish XNU's normal image path from the requested independent ramfile
# path.  These three locations are the macOS 26.6 imageboot boolean branch,
# its true branch, and its false branch respectively.  They are observational:
# this probe neither changes the parsed flag nor alters device attachment.
hbreak *0xfffffe00235db6a4
commands 13
  silent
  printf "XNU_IMAGEBOOT_RAMDISK_ARG value=%u\n", $w27
  continue
end

hbreak *0xfffffe00235db6a8
commands 14
  silent
  printf "XNU_IMAGEBOOT_RAMDISK_PATH\n"
  continue
end

hbreak *0xfffffe00235db6fc
commands 15
  silent
  printf "XNU_IMAGEBOOT_FILE_PATH\n"
  continue
end

# apfs_vfsop_mount has just obtained the target vnode's dev_t.  Recording it
# before vfs_iterate lets us compare the root and BaseSystem identities, rather
# than inferring them from their shared md0 log name.
hbreak *0xfffffe0022c57d60
commands 16
  silent
  printf "XNU_APFS_TARGET_DEVT devvp=%#lx devt=%#x\n", $x26, $w0
  continue
end

# Trace the exact vfs_iterate candidate that apfs_fsid_to_apfs_callback
# considers equivalent.  $x19 is the callback context, $x20 the candidate
# mount and $x0 the candidate statfs result at this instruction.  Every memory
# read is pointer-guarded so a diagnostic can never fault a guest merely while
# inspecting an early or malformed mount.
hbreak *0xfffffe0022c5b55c
commands 17
  silent
  if $x19 != 0 && $x20 != 0 && $x0 != 0 && *(unsigned long *)$x19 != 0
    printf "XNU_APFS_FSID_CANDIDATE candidate_mp=%#lx target_devt=%#x target_typenum=%#x candidate_devt=%#x candidate_typenum=%#x callback_flag=%#x\n", $x20, *(unsigned int *)*(unsigned long *)$x19, *((unsigned int *)*(unsigned long *)$x19 + 1), *(unsigned int *)($x0 + 0x3c), *(unsigned int *)($x0 + 0x40), *(unsigned char *)($x19 + 0x10)
  end
  continue
end

hbreak *0xfffffe0022c5b59c
commands 18
  silent
  if $x19 != 0 && *(unsigned long *)$x19 != 0
    printf "XNU_APFS_FSID_BACKING_DEVT candidate_mp=%#lx candidate_devt=%#x target_devt=%#x callback_flag=%#x\n", $x20, $w0, *(unsigned int *)*(unsigned long *)$x19, *(unsigned char *)($x19 + 0x10)
  end
  continue
end

hbreak *0xfffffe0022c5b5b0
commands 19
  silent
  if $x19 != 0 && *(unsigned long *)$x19 != 0
    printf "XNU_APFS_FSID_MATCH candidate_mp=%#lx selected_object=%#lx target_devt=%#x callback_flag=%#x\n", $x20, *(unsigned long *)($x20 + 0x8), *(unsigned int *)*(unsigned long *)$x19, *(unsigned char *)($x19 + 0x10)
  end
  continue
end

continue
