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
import uuid

sys.path.insert(0, "/home/macvm/src/macvm/tools")
from apple_device_tree import (
    find_node,
    memory_map_region,
    parse_device_tree,
    replace_property_value_in_place,
    replace_properties_exact_span,
    replace_zero_filled_property_with_prefix,
)
from basesystem_auth import BaseSystemAuthError, extract_csys_auth_payload
from validate_ramdisk_override import (
    validate_image_path,
    validate_physical_region,
)
from trustcache_region import (
    PAGE_SIZE as TRUSTCACHE_PAGE_SIZE,
    load_region_image,
    parse_u64_literal as parse_trustcache_address,
    regions_overlap,
    validate_physical_region as validate_trustcache_physical_region,
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
    if os.environ.get("MACVM_EXPOSE_UTIL_VIRTIO") == "YES":
        from vmapple_util_layout import validate_regions
        util_regions = find_node(root, "/device-tree/product/util").property("regions").value
        validate_regions(util_regions)
        gdb.write("MACVM_UTIL_REGIONS_VERIFIED build=25G72 end=0x2000000 isc_start=0x2000000\n")
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
        auth_container = handle.read(4097)
    if not auth_container or len(auth_container) > 4096:
        raise ValueError(
            f"unexpected BaseSystem auth container length {len(auth_container)}"
        )
    try:
        auth_payload = extract_csys_auth_payload(auth_container)
    except BaseSystemAuthError as error:
        raise ValueError(f"invalid BaseSystem auth container: {error}") from error

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

    trustcache_path = os.environ.get("MACVM_TRUSTCACHE_OVERRIDE_IMAGE", "")
    trustcache_address_literal = os.environ.get(
        "MACVM_TRUSTCACHE_OVERRIDE_ADDRESS", ""
    )
    if not trustcache_address_literal:
        raise ValueError("MACVM_TRUSTCACHE_OVERRIDE_ADDRESS is required")
    trustcache_resolved, trustcache_bytes, trustcache_region = load_region_image(
        trustcache_path, allowed_root="/home/macvm/runs/aux-26.6"
    )
    trustcache_address = parse_trustcache_address(
        trustcache_address_literal, name="TrustCache address"
    )
    validate_trustcache_physical_region(
        address=trustcache_address,
        size=len(trustcache_bytes),
        memory_base=phys_base,
        memory_size=memory_size,
    )
    if regions_overlap(
        trustcache_address, len(trustcache_bytes), ramdisk_address, ramdisk_size
    ):
        raise ValueError("TrustCache override overlaps the BaseSystem RAMDisk")

    current_ramdisk = memory_map_region(logical_tree, "RAMDisk")
    current_reservation = memory_map_region(logical_tree, "MemoryMapReserved-0")
    current_trustcache = memory_map_region(logical_tree, "TrustCache")
    if current_ramdisk[1] == 0:
        raise ValueError("firmware RAMDisk mapping is unexpectedly empty")
    if current_reservation != (0, 0):
        raise ValueError("MemoryMapReserved-0 is already in use")
    if current_trustcache[1] == 0:
        raise ValueError("firmware TrustCache mapping is unexpectedly empty")

    bootkc_layout_base, _ = memory_map_region(logical_tree, "BootKC-ro")
    if device_tree_length != capacity:
        raise ValueError("BootArgs and DeviceTree allocation lengths differ")
    if device_tree_physical + device_tree_length != current_trustcache[0]:
        raise ValueError("firmware DeviceTree and TrustCache are not contiguous")
    if current_trustcache[0] + current_trustcache[1] != bootkc_layout_base:
        raise ValueError("firmware TrustCache does not end at BootKC-ro")
    expected_trustcache_address = bootkc_layout_base - len(trustcache_bytes)
    if trustcache_address != expected_trustcache_address:
        raise ValueError(
            f"TrustCache must end at BootKC-ro: expected 0x{expected_trustcache_address:x}"
        )
    relocated_device_tree_physical = trustcache_address - device_tree_length
    relocation_distance = device_tree_physical - relocated_device_tree_physical
    if (
        relocation_distance <= 0
        or relocation_distance > 1024 * 1024
        or relocation_distance % TRUSTCACHE_PAGE_SIZE
    ):
        raise ValueError(f"unsafe DeviceTree relocation distance 0x{relocation_distance:x}")
    if (
        relocated_device_tree_physical % TRUSTCACHE_PAGE_SIZE
        or trustcache_address % TRUSTCACHE_PAGE_SIZE
        or bootkc_layout_base % TRUSTCACHE_PAGE_SIZE
        or len(trustcache_bytes) % TRUSTCACHE_PAGE_SIZE
    ):
        raise ValueError("DeviceTree, TrustCache, and BootKC layout is not 16 KiB aligned")
    validate_physical_region(
        address=relocated_device_tree_physical,
        size=device_tree_length,
        memory_base=phys_base,
        memory_size=memory_size,
    )
    relocated_device_tree_virtual = (
        relocated_device_tree_physical - phys_base + virt_base
    )
    if relocated_device_tree_physical + device_tree_length != trustcache_address:
        raise ValueError("relocated DeviceTree does not end at TrustCache")

    memory_map_node = find_node(root, "/device-tree/chosen/memory-map")
    ignored_regions = {"DeviceTree", "TrustCache", "MemoryMapReserved-0"}
    combined_address = relocated_device_tree_physical
    combined_size = device_tree_length + len(trustcache_bytes)
    if regions_overlap(
        combined_address,
        combined_size,
        ramdisk_address,
        ramdisk_size,
    ):
        raise ValueError("relocated DeviceTree/TrustCache overlaps the BaseSystem RAMDisk")
    for item in memory_map_node.properties:
        if item.name in ignored_regions or item.length != 16:
            continue
        other_address, other_size = struct.unpack("<QQ", item.value)
        if regions_overlap(
            combined_address,
            combined_size,
            other_address,
            other_size,
        ):
            raise ValueError(
                f"relocated DeviceTree/TrustCache overlaps memory-map region {item.name}"
            )

    secure_boot_hashes = find_node(
        root, "/device-tree/chosen/secure-boot-hashes"
    )
    replaced_hash_names = ("rtsc", "rdsk", "rdtr", "rkrn")
    replaced_hashes = tuple(
        secure_boot_hashes.property(name) for name in replaced_hash_names
    )
    if any(item.length != 48 for item in replaced_hashes):
        raise ValueError("unexpected restore secure-boot hash length")
    # The previous, validated exact-span layout used the 229-byte DER
    # container plus 32 bytes of padding. APFS validates its 208-byte inner
    # auth payload; transfer the 21-byte difference to padding so following
    # signed DeviceTree offsets stay unchanged.
    auth_padding_length = len(auth_container) - len(auth_payload) + 32
    if auth_padding_length < 32 or auth_padding_length > 4096:
        raise ValueError(f"unsafe BaseSystem auth padding length {auth_padding_length}")

    updated = replace_properties_exact_span(
        logical_tree,
        node_path="/device-tree/chosen/secure-boot-hashes",
        old_names=replaced_hash_names,
        replacements=(
            # Do not set bit 31 in the encoded length.  This XNU DeviceTree
            # walker consumes the raw uint32 length; bit 31 made its next
            # pointer exactly 0x80000000 bytes out of bounds in boot13.
            # APFS 2811.160.7's `basesystem ? 1` branch reads this exact
            # DeviceTree key while it authenticates arm64eBaseSystem.dmg.
            # Keep it in the existing
            # fixed-span secure-boot-hashes slot so signed DT offsets do not
            # move.
            ("base-system-volume-auth-blob", auth_payload, False),
            ("macvm-auth-padding", b"\0" * auth_padding_length, False),
        ),
    )
    if len(updated) != len(logical_tree):
        raise ValueError("exact-span replacement changed the DeviceTree length")
    injected = find_node(
        parse_device_tree(updated), "/device-tree/chosen/secure-boot-hashes"
    ).property("base-system-volume-auth-blob")
    if injected.secure or injected.length != len(auth_payload):
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

    # prebootensurer 753.100.4 reads /chosen/boot-uuid as either CFData or a
    # CFString, copies exactly the first 36 bytes, and then constructs an
    # AppleAPFSVolume match for that UUID plus role Recovery (0x4).  The
    # remote-restore DeviceTree has no boot-uuid.  Its 128-byte
    # host-os-information placeholder is entirely zero and is not carrying
    # host metadata in this restore path, so reuse that exact record without
    # moving any signed DeviceTree offset.  Keep the property's original
    # length: the reviewed consumer intentionally ignores bytes after 36.
    recovery_uuid_literal = os.environ.get("MACVM_RECOVERY_VOLUME_UUID", "")
    try:
        recovery_uuid = str(uuid.UUID(recovery_uuid_literal)).upper()
    except (AttributeError, ValueError) as error:
        raise ValueError("MACVM_RECOVERY_VOLUME_UUID is not a UUID") from error
    updated = replace_zero_filled_property_with_prefix(
        updated,
        node_path="/device-tree/chosen",
        old_name="host-os-information",
        new_name="boot-uuid",
        prefix=recovery_uuid.encode("ascii"),
    )
    boot_uuid_property = find_node(
        parse_device_tree(updated), "/device-tree/chosen"
    ).property("boot-uuid")
    if (
        boot_uuid_property.secure
        or boot_uuid_property.length != 128
        or boot_uuid_property.value[:36] != recovery_uuid.encode("ascii")
        or any(boot_uuid_property.value[36:])
    ):
        raise ValueError("boot-uuid injection is malformed")

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
    device_tree_mapping = struct.pack(
        "<QQ", relocated_device_tree_physical, device_tree_length
    )
    updated = replace_property_value_in_place(
        updated,
        node_path="/device-tree/chosen/memory-map",
        name="DeviceTree",
        value=device_tree_mapping,
    )
    trustcache_mapping = struct.pack(
        "<QQ", trustcache_address, len(trustcache_bytes)
    )
    updated = replace_property_value_in_place(
        updated,
        node_path="/device-tree/chosen/memory-map",
        name="TrustCache",
        value=trustcache_mapping,
    )
    if memory_map_region(updated, "RAMDisk") != (ramdisk_address, ramdisk_size):
        raise ValueError("RAMDisk DeviceTree mapping did not persist")
    if memory_map_region(updated, "MemoryMapReserved-0") != (
        ramdisk_address,
        ramdisk_size,
    ):
        raise ValueError("RAMDisk reservation did not persist")
    if memory_map_region(updated, "DeviceTree") != (
        relocated_device_tree_physical,
        device_tree_length,
    ):
        raise ValueError("relocated DeviceTree mapping did not persist")
    if memory_map_region(updated, "TrustCache") != (
        trustcache_address,
        len(trustcache_bytes),
    ):
        raise ValueError("TrustCache DeviceTree mapping did not persist")
    updated_allocation = updated.ljust(device_tree_length, b"\0")

    # The synthetic validation RAMDisk is deliberately a single APFS volume.
    # It therefore does not advertise membership in a System/Data volume group
    # and cannot provide the separate Recovery-role volume that production
    # Apple media normally mounts here.  Patch only those two volume-group bit
    # tests and the bsd_find_basesystem_dmg call to vfs_mount_recovery(), after
    # validating the BootKC mapping and every exact macOS 26.6 instruction.
    # The subsequent Apple BaseSystem lookup, authentication, mount and root
    # pivot remain unmodified.
    bootkc_base, bootkc_ro_size = memory_map_region(logical_tree, "BootKC-ro")
    if bootkc_base != bootkc_layout_base:
        raise ValueError("BootKC-ro base changed during handoff validation")
    nop_instruction = bytes.fromhex("1f2003d5")
    kernel_patches = [
        ("volume-group-capability", 0x318442C, bytes.fromhex("48200036"), nop_instruction),
        ("volume-group-validity", 0x3184434, bytes.fromhex("0820c036"), nop_instruction),
        ("recovery-mount", 0x318449C, bytes.fromhex("b9bef397"), bytes.fromhex("00008052")),
        # Avoid probing the known APFS BaseSystem device as HFS.  Boot22 proved
        # this probe was not the source of EBUSY, but returning EINVAL here
        # removes an invalid cross-filesystem probe while preserving the APFS
        # fallback and all authentication checks.
        ("skip-hfs-probe", 0x329B81C, bytes.fromhex("4b99ef97"), bytes.fromhex("c0028052")),
    ]
    allow_basesystem_rw_root = os.environ.get(
        "MACVM_ALLOW_BASESYSTEM_RW_ROOT", ""
    ).upper() in ("1", "YES", "TRUE", "ON")
    if allow_basesystem_rw_root:
        # In the synthetic single-volume validation media, recoveryosd's
        # mountrecursive creates /System/Installation/PackagesLink after the
        # BaseSystem pivot.  The reviewed imageboot_pivot_image() mount call
        # passes VFS flags 0x81 (MNT_RDONLY | MNT_DONTBROWSE), so XNU's
        # vnode_authorize_callback_int rejects that exact ADD_FILE request with
        # EROFS before APFS VNOP_SYMLINK can run.  For this validation path only,
        # clear MNT_RDONLY while preserving MNT_DONTBROWSE and the APFS
        # authentication/root-pivot flow.
        kernel_patches.append(
            (
                "basesystem-rw-mount-flags",
                0x329B86C,
                bytes.fromhex("27108052"),
                bytes.fromhex("07108052"),
            )
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
    patch_plan = []
    for patch_name, patch_offset, expected_instruction, replacement_instruction in kernel_patches:
        patch_address = bootkc_base + patch_offset
        observed_instruction = inferior.read_memory(patch_address, 4).tobytes()
        if observed_instruction != expected_instruction:
            raise ValueError(
                f"macOS 26.6 {patch_name} instruction does not match the reviewed BootKC"
            )
        patched_addresses[patch_name] = patch_address
        patch_plan.append((patch_name, patch_address, replacement_instruction))
    recovery_mount_call = patched_addresses["recovery-mount"]

    # Commit only after every signed-media, layout, range, and instruction
    # precondition has passed.  XNU release kernels require locked DeviceTree
    # EXTRADATA immediately followed by TrustCache and both below BootKC.
    inferior.write_memory(relocated_device_tree_physical, updated_allocation)
    if inferior.read_memory(
        relocated_device_tree_physical, device_tree_length
    ).tobytes() != updated_allocation:
        raise ValueError("relocated DeviceTree bytes did not persist")
    inferior.write_memory(trustcache_address, trustcache_bytes)
    if inferior.read_memory(
        trustcache_address, len(trustcache_bytes)
    ).tobytes() != trustcache_bytes:
        raise ValueError("TrustCache handoff bytes did not persist")
    inferior.write_memory(
        boot_args + 0x60, struct.pack("<Q", relocated_device_tree_virtual)
    )
    if struct.unpack(
        "<Q", inferior.read_memory(boot_args + 0x60, 8).tobytes()
    )[0] != relocated_device_tree_virtual:
        raise ValueError("relocated BootArgs DeviceTree pointer did not persist")
    for patch_name, patch_address, replacement_instruction in patch_plan:
        inferior.write_memory(patch_address, replacement_instruction)
        if inferior.read_memory(patch_address, 4).tobytes() != replacement_instruction:
            raise ValueError(f"{patch_name} BootKC patch did not persist")

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
        f"old_dt_virtual=0x{device_tree_virtual:x} old_dt_physical=0x{device_tree_physical:x} "
        f"dt_virtual=0x{relocated_device_tree_virtual:x} "
        f"dt_physical=0x{relocated_device_tree_physical:x} "
        f"dt_relocation=0x{relocation_distance:x} "
        f"old_logical_length={len(logical_tree)} new_logical_length={len(updated)} "
        f"bootargs_length={device_tree_length} capacity={capacity} "
        f"auth_container={len(auth_container)} auth_payload={len(auth_payload)} "
        f"auth_padding={auth_padding_length} "
        f"phys_base=0x{phys_base:x} memory_size=0x{memory_size:x} "
        f"ramdisk={ramdisk_resolved} ramdisk_address=0x{ramdisk_address:x} "
        f"ramdisk_size=0x{ramdisk_size:x} bootkc_base=0x{bootkc_base:x} "
        f"old_trustcache_address=0x{current_trustcache[0]:x} "
        f"old_trustcache_size=0x{current_trustcache[1]:x} "
        f"trustcache={trustcache_resolved} "
        f"trustcache_address=0x{trustcache_address:x} "
        f"trustcache_size=0x{len(trustcache_bytes):x} "
        f"trustcache_logical=0x{trustcache_region.logical_length:x} "
        f"trustcache_entries={trustcache_region.modules[0].num_entries},"
        f"{trustcache_region.modules[1].num_entries} "
        f"recovery_uuid={recovery_uuid} "
        f"basesystem_rw_root={int(allow_basesystem_rw_root)} "
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

# macOS 26.6's APFS KEXT has a global `_rootedRamdisk()` fast path.  It is
# correct for the /dev/md0 root mount, but must not replace the device vnode
# passed by imageboot_pivot_image() for KERNEL_MOUNT_BASESYSTEMROOT.  Boot41 and
# Boot42 proved that iSC/md0 enumeration changes the number of earlier calls,
# so a call counter is not a valid discriminator.  Instead, arm a one-shot
# guard at XNU's exact APFS kernel_mount call and consume it at APFS's immediate
# post-_rootedRamdisk cbz.  Disk-image, APFS and authentication code otherwise
# remain untouched.
set $macvm_rooted_ramdisk_calls = 0
set $macvm_basesystem_pivot_active = 0
set $macvm_basesystem_pivot_guard_applied = 0

# imageboot_pivot_image()'s APFS kernel_mount call in the extracted macOS 26.6
# com.apple.kernel image.  The preceding instructions construct mount flags
# 0x00100001 (KERNEL_MOUNT_NOAUTH | KERNEL_MOUNT_BASESYSTEMROOT) and VFS flags
# 0x81 (MNT_RDONLY | MNT_DONTBROWSE).  Calculate the runtime address from the
# verified static address and KernelCache slide.
set $macvm_imageboot_apfs_mount_static = 0xfffffe000a29f870
set $macvm_kernelcache_slide = 0x19344000
set $macvm_imageboot_apfs_mount_call = $macvm_imageboot_apfs_mount_static + $macvm_kernelcache_slide
hbreak *$macvm_imageboot_apfs_mount_call
commands 2
  silent
  if $macvm_basesystem_pivot_active != 0 || $macvm_basesystem_pivot_guard_applied != 0
    printf "MACVM_PIVOT_GUARD_REFUSED duplicate-basesystem-apfs-mount\n"
    detach
    quit 73
  end
  set $macvm_basesystem_pivot_active = 1
  printf "XNU_BASESYSTEM_APFS_MOUNT_ENTER pc=%#lx flags=%#x kernel_flags=%#x\n", $pc, $w7, $w6
  continue
end

# _container_rootmount() return from _rootedRamdisk().  Calculate the
# runtime address rather than transcribing it: the static address is
# 0xfffffe00098beed8 and the verified 26.6 KernelCache slide is 0x19344000,
# producing 0xfffffe0022c02ed8.  This lies in the loaded APFS kext range
# reported by the kernel; it is not a separately slid image.
set $macvm_apfs_static_rooted_ramdisk_return = 0xfffffe00098beed8
set $macvm_rooted_ramdisk_return = $macvm_apfs_static_rooted_ramdisk_return + $macvm_kernelcache_slide
hbreak *$macvm_rooted_ramdisk_return
commands 3
  silent
  set $macvm_rooted_ramdisk_calls = $macvm_rooted_ramdisk_calls + 1
  printf "XNU_ROOTED_RAMDISK_DECISION index=%u result=%u pivot_active=%u\n", $macvm_rooted_ramdisk_calls, $w0, $macvm_basesystem_pivot_active
  if $macvm_basesystem_pivot_active == 1
    if $w0 != 1
      printf "MACVM_PIVOT_GUARD_REFUSED basesystem-rooted-ramdisk-was-not-active\n"
      detach
      quit 74
    end
    # The next instruction is cbz w0.  A false return selects the device vnode
    # already supplied for the attached BaseSystem disk image instead of md0.
    set $w0 = 0
    set $macvm_basesystem_pivot_active = 0
    set $macvm_basesystem_pivot_guard_applied = 1
    printf "MACVM_PIVOT_GUARD_APPLIED index=%u use-explicit-disk-image=1\n", $macvm_rooted_ramdisk_calls
  end
  continue
end

# Tahoe 26.6's imageboot_pivot_image() authenticates and switches to the
# BaseSystem root, but unlike imageboot_mount_image() it does not preserve the
# outgoing Recovery root in imgsrc_rootvnodes[].  recoveryosd's mountrecursive
# subsequently reads kern.imgsrcinfo and fails with "no device info".  Recreate
# the source-derived bookkeeping as one guarded transaction while QEMU's
# all-stop GDB stub has every vCPU paused:
#
#   1. immediately before imageboot_pivot_image() calls vfs_switch_root(), after
#      rootvnode's PAC-signed mount pointer has been loaded from the x17 field
#      address and authenticated by autda into x16, validate the outgoing
#      mount-list links and retain the old root vnode;
#   2. only after imageboot_pivot_image() returns success, validate that the
#      root really changed, remove the outgoing mount from the global list,
#      transfer the root/backing flags, and publish imgsrc_rootvnodes[0].
#
# Every live pointer, link, reference count, flag, and global is validated by
# xnu_imgsrc_state.py before the first post-pivot list write.  A failed pivot or
# pre-commit validation rolls back only the extra vnode retain.  A write error
# after list mutation is fatal and deliberately does not attempt a guessed
# partial repair.
set $macvm_imgsrc_prepared = 0
set $macvm_imgsrc_applied = 0
set $macvm_imgsrc_prepare_ok = 0
set $macvm_imgsrc_commit_ok = 0

set $macvm_imageboot_old_root_mount_ready_static = 0xfffffe000a29f91c
set $macvm_imageboot_pivot_return_static = 0xfffffe000a29f940
set $macvm_rootvnode_static = 0xfffffe000a992d78
set $macvm_imgsrc_rootvnodes_static = 0xfffffe000a9881d0
set $macvm_mountlist_tail_static = 0xfffffe000a9881b8
set $macvm_nummounts_static = 0xfffffe000a9beab0

set $macvm_imageboot_old_root_mount_ready = $macvm_imageboot_old_root_mount_ready_static + $macvm_kernelcache_slide
set $macvm_imageboot_pivot_return = $macvm_imageboot_pivot_return_static + $macvm_kernelcache_slide
set $macvm_rootvnode = $macvm_rootvnode_static + $macvm_kernelcache_slide
set $macvm_imgsrc_rootvnodes = $macvm_imgsrc_rootvnodes_static + $macvm_kernelcache_slide
set $macvm_mountlist_tail = $macvm_mountlist_tail_static + $macvm_kernelcache_slide
set $macvm_nummounts = $macvm_nummounts_static + $macvm_kernelcache_slide

hbreak *$macvm_imageboot_old_root_mount_ready
commands 4
  silent
  if $macvm_basesystem_pivot_guard_applied == 1 && $macvm_imgsrc_applied == 0
    if $macvm_imgsrc_prepared != 0
      printf "MACVM_IMGSRC_STATE_REFUSED duplicate-root-switch-before-pivot-return\n"
      detach
      quit 75
    end
    set $macvm_imgsrc_prepare_ok = 0
    python
import gdb
import struct
import sys

sys.path.insert(0, "/home/macvm/src/macvm/tools")
from xnu_imgsrc_state import retain_outgoing_root

class MacvmGdbMemory:
    def __init__(self, inferior):
        self.inferior = inferior
        self.writes_started = False

    def read_u32(self, address):
        return struct.unpack("<I", self.inferior.read_memory(address, 4).tobytes())[0]

    def read_u64(self, address):
        return struct.unpack("<Q", self.inferior.read_memory(address, 8).tobytes())[0]

    def write_u32(self, address, value):
        self.writes_started = True
        self.inferior.write_memory(address, struct.pack("<I", value))

    def write_u64(self, address, value):
        self.writes_started = True
        self.inferior.write_memory(address, struct.pack("<Q", value))

def u64_eval(expression):
    # GDB Python can expose high-bit AArch64 register values as signed Python
    # integers.  Normalize them before XNU pointer validation.
    return int(gdb.parse_and_eval(expression)) & 0xFFFFFFFFFFFFFFFF

try:
    inferior = gdb.selected_inferior()
    memory = MacvmGdbMemory(inferior)
    pc = u64_eval("$pc")
    x16 = u64_eval("$x16")
    x17 = u64_eval("$x17")
    rootvnode_address = u64_eval("$macvm_rootvnode")
    imgsrc_address = u64_eval("$macvm_imgsrc_rootvnodes")
    tail_address = u64_eval("$macvm_mountlist_tail")
    old_root_vnode = memory.read_u64(rootvnode_address)
    root_mount_field_address = old_root_vnode + 0xD8
    root_mount_field_value = memory.read_u64(root_mount_field_address)
    outgoing_mount = x16
    retained = retain_outgoing_root(
        memory,
        old_root_vnode=old_root_vnode,
        outgoing_mount=outgoing_mount,
        imgsrc_rootvnode=imgsrc_address,
        mountlist_tail=tail_address,
    )
    gdb._macvm_imgsrc_retained = retained
    gdb.write(
        "MACVM_IMGSRC_STATE_PREPARED "
        f"vnode=0x{retained.vnode:x} mount=0x{retained.mount:x} "
        f"usecount={retained.original_usecount}->{retained.original_usecount + 1}\n"
    )
    gdb.set_convenience_variable("macvm_imgsrc_prepare_ok", 1)
except Exception as error:
    try:
        context = (
            f"pc=0x{pc:x} x16=0x{x16:x} x17=0x{x17:x} "
            f"rootvnode_slot=0x{rootvnode_address:x} old_root_vnode=0x{old_root_vnode:x} "
            f"root_mnt_slot=0x{root_mount_field_address:x} "
            f"root_mnt_value=0x{root_mount_field_value:x} "
            f"imgsrc_slot=0x{imgsrc_address:x} mountlist_tail=0x{tail_address:x}"
        )
    except Exception:
        context = "context-unavailable"
    gdb.write(f"MACVM_IMGSRC_STATE_REFUSED pre-switch {context} {error}\n")
    end
    if $macvm_imgsrc_prepare_ok != 1
      detach
      quit 76
    end
    set $macvm_imgsrc_prepared = 1
  end
  continue
end

hbreak *$macvm_imageboot_pivot_return
commands 5
  silent
  if $macvm_basesystem_pivot_guard_applied == 1 && $macvm_imgsrc_applied == 0
    if $macvm_imgsrc_prepared != 1
      printf "MACVM_IMGSRC_STATE_REFUSED pivot-return-without-retain\n"
      detach
      quit 77
    end
    set $macvm_imgsrc_commit_ok = 0
    python
import gdb
import struct
import sys

sys.path.insert(0, "/home/macvm/src/macvm/tools")
from xnu_imgsrc_state import commit_imgsrc_transfer, rollback_retained_root

class MacvmGdbMemory:
    def __init__(self, inferior):
        self.inferior = inferior
        self.writes_started = False

    def read_u32(self, address):
        return struct.unpack("<I", self.inferior.read_memory(address, 4).tobytes())[0]

    def read_u64(self, address):
        return struct.unpack("<Q", self.inferior.read_memory(address, 8).tobytes())[0]

    def write_u32(self, address, value):
        self.writes_started = True
        self.inferior.write_memory(address, struct.pack("<I", value))

    def write_u64(self, address, value):
        self.writes_started = True
        self.inferior.write_memory(address, struct.pack("<Q", value))

def u64_eval(expression):
    return int(gdb.parse_and_eval(expression)) & 0xFFFFFFFFFFFFFFFF

inferior = gdb.selected_inferior()
memory = MacvmGdbMemory(inferior)
retained = getattr(gdb, "_macvm_imgsrc_retained", None)
try:
    if retained is None:
        raise ValueError("retained root state is absent")
    pivot_result = int(gdb.parse_and_eval("$w0")) & 0xFFFFFFFF
    if pivot_result != 0:
        rollback_retained_root(memory, retained)
        raise ValueError(f"imageboot pivot returned {pivot_result}")
    rootvnode_address = u64_eval("$macvm_rootvnode")
    current_root_vnode = memory.read_u64(rootvnode_address)
    result = commit_imgsrc_transfer(
        memory,
        retained=retained,
        current_root_vnode=current_root_vnode,
        imgsrc_rootvnode=u64_eval("$macvm_imgsrc_rootvnodes"),
        mountlist_tail=u64_eval("$macvm_mountlist_tail"),
        mount_count=u64_eval("$macvm_nummounts"),
    )
    gdb.write(
        "MACVM_IMGSRC_STATE_APPLIED "
        f"vnode=0x{result.vnode:x} mount=0x{result.mount:x} "
        f"next=0x{result.next_mount:x} nummounts={result.old_mount_count}->{result.old_mount_count - 1}\n"
    )
    gdb.set_convenience_variable("macvm_imgsrc_commit_ok", 1)
except Exception as error:
    if retained is not None and not memory.writes_started:
        try:
            rollback_retained_root(memory, retained)
            gdb.write("MACVM_IMGSRC_STATE_ROLLED_BACK pre-commit\n")
        except Exception as rollback_error:
            gdb.write(f"MACVM_IMGSRC_STATE_ROLLBACK_FAILED {rollback_error}\n")
    gdb.write(
        "MACVM_IMGSRC_STATE_REFUSED "
        f"post-pivot writes_started={int(memory.writes_started)} {error}\n"
    )
    end
    if $macvm_imgsrc_commit_ok != 1
      detach
      quit 78
    end
    set $macvm_imgsrc_applied = 1
  end
  continue
end

set $macvm_symlink_embedded_trace = 1
source /home/macvm/src/macvm/tools/trace_basesystem_symlink_preflight_live.gdb
set $macvm_symlink_embedded_trace = 0

continue
