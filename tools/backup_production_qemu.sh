#!/usr/bin/env bash
# Explicitly authorized production backup only. Never launches a VM, installs
# packages, changes device bindings, or restores files over the live system.
set -euo pipefail
umask 077

[[ "${MACVM_PRODUCTION_BACKUP_ONLY:-}" == YES ]] || exit 78
[[ "$EUID" == 0 && "$(hostname)" == jansuzhang-LC2 ]] || exit 78
[[ "$(uname -sm)" == 'Linux x86_64' ]] || exit 78
base=/home/jansurezhang/apple-m-macos-vm/production-qemu-backups
[[ -d /home/jansurezhang/apple-m-macos-vm ]] || exit 78
[[ ! -L /home/jansurezhang/apple-m-macos-vm && ! -L "$base" ]] || exit 78
for tool in tar zstd sha256sum readelf ldd dpkg-query find sort stat fuser; do
    command -v "$tool" >/dev/null
done
mkdir -p -- "$base"
chmod 700 -- "$base"
chown jansurezhang:jansurezhang -- "$base"
out=$(mktemp -d "$base/production-qemu-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
printf 'BACKUP_DIRECTORY=%s\n' "$out"
trap 'code=$?; if ((code != 0)); then printf "BACKUP_INCOMPLETE exit=%s directory=%s\n" "$code" "$out" >&2; fi' EXIT

list="$out/files.unsorted.nul"
elfs="$out/elf.unsorted.nul"
touch "$list" "$elfs"
add() {
    local path=$1
    if [[ -e "$path" || -L "$path" ]]; then
        if [[ -d "$path" && ! -L "$path" ]]; then
            find "$path" -xdev \( -type d -o -type f -o -type l \) -print0 >> "$list"
        else
            printf '%s\0' "$path" >> "$list"
        fi
    fi
}
add_elf() {
    local path=$1 resolved
    add "$path"
    resolved=$(readlink -f -- "$path")
    add "$resolved"
    if readelf -h "$resolved" >/dev/null 2>&1; then
        printf '%s\0' "$resolved" >> "$elfs"
    fi
}

# Preserve the installed bytes, including local patches, not just package names.
shopt -s nullglob
for path in /usr/bin/qemu* /usr/local/bin/qemu* /usr/libexec/qemu*; do
    [[ -f "$path" ]] && add_elf "$path"
done
for path in /usr/lib/x86_64-linux-gnu/qemu /usr/lib/qemu /usr/share/qemu /usr/share/OVMF /usr/share/seabios; do
    add "$path"
    if [[ -d "$path" ]]; then
        while IFS= read -r -d '' module; do
            add_elf "$module"
        done < <(find "$path" -type f -name '*.so*' -print0)
    fi
done

# Capture loaded optional libraries and the exact executable of every QEMU,
# even if QEMU changed its process name with -name ...,debug-threads=on.
touch "$out/qemu-processes.tsv" "$out/qemu-cmdlines.nul"
for proc in /proc/[0-9]*; do
    exe=$(readlink "$proc/exe" 2>/dev/null || true)
    case "$exe" in
        */qemu-system-*|*/qemu-kvm)
            add_elf "$exe"
            printf '%s\t%s\n' "${proc##*/}" "$exe" >> "$out/qemu-processes.tsv"
            printf '%s\0' "${proc##*/}" >> "$out/qemu-cmdlines.nul"
            cp -- "$proc/cmdline" "$out/cmdline-${proc##*/}.nul"
            cp -- "$proc/maps" "$out/maps-${proc##*/}.txt"
            while IFS= read -r lib; do add "$lib"; done < <(
                awk '$6 ~ /^\// && $6 ~ /\.so/ {print $6}' "$proc/maps" | sort -u
            )
            ;;
    esac
done

sort -zu "$elfs" -o "$out/elf.nul"
while IFS= read -r -d '' exe; do
    printf '\nELF %s\n' "$exe" >> "$out/ldd.txt"
    ldd "$exe" >> "$out/ldd.txt" 2>&1
done < "$out/elf.nul"
if grep -q 'not found' "$out/ldd.txt"; then
    printf 'Refusing incomplete dependency backup; see ldd.txt\n' >&2
    exit 78
fi
while IFS= read -r lib; do
    add "$lib"
    add "$(readlink -f -- "$lib")"
done < <(awk '$2 == "=>" && $3 ~ /^\// {print $3} $1 ~ /^\// {print $1}' "$out/ldd.txt" | sort -u)

# Existing production scripts, manager source/runtime, firmware and boot state.
# Deliberately do not copy the OS disk, recovery installers, logs or user keys.
for path in \
    /home/jansurezhang/macvm-scripts \
    /home/jansurezhang/src/mac-manager \
    /home/jansurezhang/.macvm/settings.json \
    /home/jansurezhang/.macvm/vms/5016c857ab39/config.json \
    /home/jansurezhang/.macvm/vms/5016c857ab39/efi \
    /home/jansurezhang/.macvm/vms/5016c857ab39/pending-kexts \
    /home/jansurezhang/.macvm/roms; do add "$path"; done
for path in \
    /home/jansurezhang/.macvm/vms/5016c857ab39/OpenCore.qcow2 \
    /home/jansurezhang/.macvm/vms/5016c857ab39/OVMF_VARS.fd; do
    if [[ -f "$path" ]]; then
        # psmisc fuser does not accept a standalone -- on every supported
        # release. These fixed absolute paths cannot be interpreted as options.
        if fuser -s "$path" 2> "$out/fuser-${path##*/}.stderr"; then
            printf 'Active boot-state file; no inconsistent backup: %s\n' "$path" >&2
            exit 78
        fi
        if [[ -s "$out/fuser-${path##*/}.stderr" ]]; then
            printf 'Unable to verify boot-state file ownership: %s\n' "$path" >&2
            exit 78
        fi
        add "$path"
    fi
done
for path in \
    /etc/modprobe.d /etc/modules /etc/modules-load.d \
    /etc/sysctl.conf /etc/sysctl.d /etc/default/grub /etc/default/grub.d \
    /etc/initramfs-tools /etc/udev/rules.d /etc/ld.so.conf /etc/ld.so.conf.d \
    /etc/apt/sources.list /etc/apt/sources.list.d /etc/apt/preferences /etc/apt/preferences.d \
    /etc/systemd/system/macvm* /usr/local/sbin/macvm* /usr/local/bin/macvm* \
    /var/lib/dpkg/status /var/lib/dpkg/diversions /var/lib/dpkg/statoverride \
    /var/lib/dpkg/alternatives /boot; do add "$path"; done

dpkg-query -W -f='${binary:Package}\t${Version}\t${db:Status-Abbrev}\n' > "$out/packages-all.tsv"
sort -zu "$list" -o "$out/files-initial.nul"
touch "$out/package-owners.raw"
while IFS= read -r -d '' path; do
    case "$path" in
        /usr/bin/qemu*|/usr/lib/*|/lib/*|/usr/share/qemu/*|/usr/share/OVMF/*|/usr/share/seabios/*)
            if [[ -f "$path" || -L "$path" ]]; then
                dpkg-query -S "$path" >> "$out/package-owners.raw" 2>/dev/null || true
            fi
            ;;
    esac
done < "$out/files-initial.nul"
sed 's/: \/.*$//' "$out/package-owners.raw" > "$out/package-names.raw"
awk '$3 ~ /^ii/ && ($1 ~ /^qemu/ || $1 ~ /^(ovmf|seabios|ipxe-qemu)(:|$)/) {print $1}' \
    "$out/packages-all.tsv" >> "$out/package-names.raw"
sort -u "$out/package-names.raw" > "$out/dependency-packages.txt"
while IFS= read -r pkg; do
    [[ "$pkg" =~ ^[a-zA-Z0-9.+:-]+$ ]] || continue
    # Save complete installed package contents, including optional ROMs,
    # helpers and dependency data files. A package directory is just a
    # directory entry: NEVER recursively walk / or /usr from dpkg's list.
    while IFS= read -r path; do
        [[ "$path" == /* && "$path" != / && "$path" != /. ]] || continue
        if [[ -f "$path" || -d "$path" || -L "$path" ]]; then
            printf '%s\0' "$path" >> "$list"
        fi
    done < <(dpkg-query -L "$pkg")
    for path in /var/lib/dpkg/info/"$pkg".*; do add "$path"; done
done < "$out/dependency-packages.txt"
for path in /var/cache/apt/archives/qemu*.deb /var/cache/apt/archives/ovmf*.deb; do add "$path"; done

uname -a > "$out/uname.txt"
cp -- /proc/cmdline "$out/kernel-cmdline.txt"
cp -- /proc/meminfo "$out/meminfo.txt"
lspci -nnk > "$out/pci.txt"
lsmod > "$out/modules.txt"
sysctl vm.nr_hugepages vm.nr_overcommit_hugepages vm.swappiness vm.overcommit_memory \
    vm.max_map_count kernel.numa_balancing > "$out/sysctl-selected.txt"
systemctl show macvm-hugepages.service macvm-cstate-policy.service > "$out/services.txt"
find /sys/kernel/iommu_groups -type l -printf '%p -> %l\n' > "$out/iommu-groups.txt"

sort -zu "$list" -o "$out/files.nul"
touch "$out/regular-files.nul" "$out/archive-relative.nul"
while IFS= read -r -d '' path; do
    [[ "$path" == /* && "$path" != / ]] || exit 78
    printf '%s\0' "${path#/}" >> "$out/archive-relative.nul"
    if [[ -f "$path" && ! -L "$path" ]]; then
        printf '%s\0' "$path" >> "$out/regular-files.nul"
    fi
done < "$out/files.nul"
xargs -0 -r sha256sum --zero < "$out/regular-files.nul" > "$out/source-before.sha256.nul"
tar --create --file="$out/production-qemu.tar.zst" --use-compress-program='zstd -T1 -3' \
    --acls --xattrs --numeric-owner --no-recursion --null \
    --directory=/ --files-from="$out/archive-relative.nul"
xargs -0 -r sha256sum --zero < "$out/regular-files.nul" > "$out/source-after.sha256.nul"
cmp "$out/source-before.sha256.nul" "$out/source-after.sha256.nul"
tar --compare --file="$out/production-qemu.tar.zst" --use-compress-program=zstd --directory=/ \
    > "$out/archive-compare.txt" 2>&1
sha256sum "$out/production-qemu.tar.zst" > "$out/archive.sha256"
printf '%s\n' \
    'VERIFIED: source hashes stable before/after; archive compared with source.' \
    'Backup only: no QEMU, service, package, binding, kernel parameter or VM changed.' \
    'Private backup: do not publish configs, command lines, firmware or ROM files.' \
    'Not a full OS-disk backup. The existing macOS disk and installers remain untouched.' \
    'Restore into a staging directory first; NEVER blindly extract over /.' \
    'Package metadata is for reference; NEVER overwrite the global dpkg database.' \
    > "$out/VERIFIED.txt"
chmod 700 "$out"
chown -R jansurezhang:jansurezhang -- "$out"
printf 'BACKUP_VERIFIED=%s\n' "$out"
stat -c 'ARCHIVE_BYTES=%s' "$out/production-qemu.tar.zst"
sha256sum /usr/bin/qemu-system-x86_64 "$out/production-qemu.tar.zst"
