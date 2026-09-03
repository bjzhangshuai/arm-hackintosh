#!/bin/bash
# This helper runs only in the known nested ARM Recovery. Inventory by default.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_METADATA_CONTRACT_BEGIN
trap 'echo MACVM_METADATA_CONTRACT_END status=$?' EXIT
date -u
volume=/Volumes/macvm-staging
verify_apfs_scratch() {
  local info plist
  info=$(mktemp /private/tmp/macvm-metadata-volume.XXXXXX)
  plist=/usr/libexec/PlistBuddy
  diskutil info -plist "$volume" > "$info" || return 78
  [[ $($plist -c 'Print :VolumeUUID' "$info") == 2DEFBA24-3C0E-4BC2-BA2D-A66AF5879A3A ]] || return 78
  [[ $($plist -c 'Print :DeviceIdentifier' "$info") == disk9s1 ]] || return 78
  [[ $($plist -c 'Print :APFSPhysicalStores:0:APFSPhysicalStore' "$info") == disk8s1 ]] || return 78
  [[ $($plist -c 'Print :FilesystemType' "$info") == apfs ]] || return 78
  [[ $($plist -c 'Print :GlobalPermissionsEnabled' "$info") == true ]] || return 78
  [[ $($plist -c 'Print :MountPoint' "$info") == "$volume" ]] || return 78
}
case "${1:-inventory}" in
  inventory)
    diskutil list /dev/disk8
    diskutil info -plist /dev/disk8
    ioreg -p IOUSB -l -w0 | grep -E 'USB Serial Number|USB Product Name|locationID|\+-o'
    ;;
  format-new-1g)
    echo 'Already formatted. Erase action permanently retired for this run.'
    exit 78 ;;
  apfs-copy-contract)
    echo 'Retired: existing-root ditto omitted metadata; the earlier PASS marker is invalid.'
    exit 78 ;;
  apfs-new-anchor)
    verify_apfs_scratch || exit 78
    template=/System/Library/Templates/Data/private/var/db/com.apple.xpc.roleaccountd.staging
    anchor="$volume/contract-anchor"
    [[ -d "$template" && ! -e "$anchor" ]] || exit 78
    ditto -V --persistRootless "$template" "$anchor" || exit 1
    ls -ldeO@ "$anchor"
    xattr -l "$anchor"
    [[ $(xattr -p com.apple.rootless "$anchor") == RoleAccountStaging ]] || exit 1
    (( $(stat -f %f "$anchor") & 0x80000 )) || exit 1
    echo MACVM_APFS_NEW_ANCHOR_PASS
    ;;
  db-inventory)
    ls -ldeO@ /private/var/db
    ls -laO /private/var/db
    mount | grep -E ' on /private/var/db| on /System/Volumes/Data|macvm-staging'
    ;;
  prepare-role-volume)
    echo 'Already created disk9s2. Volume creation permanently retired for this run.'
    exit 78 ;;
  mount-role-volume)
    # Preserve the previous staging tree underneath an ordinary APFS mount.
    # This action changes no signatures, SIP configuration, or daemon process.
    verify_apfs_scratch || exit 78
    role=/Volumes/macvm-role-staging
    staging=/private/var/db/com.apple.xpc.roleaccountd.staging
    info=$(mktemp /private/tmp/macvm-role-volume.XXXXXX) || exit 1
    plist=/usr/libexec/PlistBuddy
    diskutil info -plist "$role" > "$info" || exit 78
    [[ $($plist -c 'Print :VolumeUUID' "$info") == 489C9422-DAD7-4130-8DBC-9C934B031438 ]] || exit 78
    [[ $($plist -c 'Print :DeviceIdentifier' "$info") == disk9s2 ]] || exit 78
    [[ $($plist -c 'Print :APFSPhysicalStores:0:APFSPhysicalStore' "$info") == disk8s1 ]] || exit 78
    [[ $($plist -c 'Print :MountPoint' "$info") == "$role" ]] || exit 78
    [[ -d "$staging" && ! -L "$staging" ]] || exit 78
    [[ $(stat -f %d "$staging") == $(stat -f %d /private/tmp) ]] || exit 78
    [[ $(xattr -p com.apple.rootless "$staging") == RoleAccountStaging ]] || exit 78
    [[ ! -e "$role/tmp" && ! -e "$role/exec" ]] || exit 78
    ls -ldeO@ "$staging" "$staging/exec" "$staging/tmp"
    diskutil unmount /dev/disk9s2 || exit 1
    if /System/Library/Filesystems/apfs.fs/Contents/Resources/mount_apfs -o owners /dev/disk9s2 "$staging"; then
      diskutil info -plist "$staging"
      echo MACVM_ROLE_VOLUME_MOUNTED
    else
      echo MACVM_ROLE_VOLUME_MOUNT_FAILED_OLD_TREE_PRESERVED
      diskutil mount /dev/disk9s2
      exit 1
    fi
    ;;
  initialize-role-volume)
    staging=/private/var/db/com.apple.xpc.roleaccountd.staging
    info=$(mktemp /private/tmp/macvm-role-mounted.XXXXXX) || exit 1
    plist=/usr/libexec/PlistBuddy
    diskutil info -plist "$staging" > "$info" || exit 78
    [[ $($plist -c 'Print :VolumeUUID' "$info") == 489C9422-DAD7-4130-8DBC-9C934B031438 ]] || exit 78
    [[ $($plist -c 'Print :DeviceIdentifier' "$info") == disk9s2 ]] || exit 78
    [[ ! -e "$staging/tmp" && ! -e "$staging/exec" ]] || exit 78
    # Exact vendor startup entry point and unmodified rootless.conf; restores
    # prescribed protections, never disables enforcement or rewrites policy.
    /usr/libexec/rootless-init -b
    printf 'MACVM_ROOTLESS_INIT_STATUS=%s\n' "$?"
    ls -ldeO@ "$staging"
    xattr -l "$staging"
    [[ $(xattr -p com.apple.rootless "$staging") == RoleAccountStaging ]] || exit 1
    (( $(stat -f %f "$staging") & 0x80000 )) || exit 1
    echo MACVM_ROLE_VOLUME_PROTECTION_PASS
    ;;
  *) echo 'Unknown metadata contract action'; exit 64 ;;
esac
