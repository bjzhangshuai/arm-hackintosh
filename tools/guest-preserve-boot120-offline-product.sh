#!/bin/bash
# Preserve the already downloaded product before any new installer operation.
# Runs once in the existing ARM test guest; no download, installer or reboot.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
uuid=$(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -)
[[ $uuid == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
source_dir="$target/macOS Install Data"
preserved="$target/macvm-offline-25G83-boot120"
[[ -d "$source_dir/UpdateBundle" ]] || exit 78
for command in /bin/cp /sbin/md5 /usr/bin/stat; do [[ -x $command ]] || exit 78; done
case ${1:-new} in
    new) [[ ! -e "$preserved" ]] || exit 78 ;;
    resume-after-missing-cmp)
        [[ -d "$preserved/UpdateBundle" && -f "$preserved/index.sproduct" \
            && ! -e "$preserved/CLONE_COMPLETE" && ! -e "$preserved/file-sizes.txt" ]] || exit 78 ;;
    *) exit 78 ;;
esac
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_PRODUCT_PRESERVE_BEGIN
date -u
ps -axo pid,ppid,etime,comm | grep -E 'UpdateBrain|InstallAssistant|osinstallersetup' || true
if [[ ${1:-new} == new ]]; then
    mkdir -m 700 "$preserved"
# APFS clone-on-write: separate names/inodes, shared immutable extents until a
# writer changes them. This is not an independent disk/snapshot backup.
/bin/cp -cRp "$source_dir/UpdateBundle" "$preserved/UpdateBundle"
fi
# md5 is present in this minimal Recovery; cmp/shasum are not. These hashes
# compare a local clone, not authenticate Apple content or replace signatures.
same_file() { [[ $(/sbin/md5 -q "$1") == $(/sbin/md5 -q "$2") ]]; }
for name in index.sproduct InstallAssistant.pkg.integrityDataV1; do
    if [[ -f "$source_dir/$name" ]]; then
        if [[ ! -e "$preserved/$name" ]]; then
            /bin/cp -cp "$source_dir/$name" "$preserved/$name"
        fi
        same_file "$source_dir/$name" "$preserved/$name"
    fi
done
for name in Info.plist AssetData/boot/BuildManifest.plist AssetData/boot/SystemVersion.plist; do
    same_file "$source_dir/UpdateBundle/$name" "$preserved/UpdateBundle/$name"
done
(cd "$source_dir" && find UpdateBundle -type f -exec stat -f '%z %N' {} + | sort) >"$preserved/source-file-sizes.txt"
(cd "$preserved" && find UpdateBundle -type f -exec stat -f '%z %N' {} + | sort) >"$preserved/file-sizes.txt"
same_file "$preserved/source-file-sizes.txt" "$preserved/file-sizes.txt"
echo MACVM_BOOT120_LOCAL_PRODUCT_METADATA
for path in "$preserved/index.sproduct" "$preserved/UpdateBundle/Info.plist" \
    "$preserved/UpdateBundle/AssetData/Info.plist" \
    "$preserved/UpdateBundle/AssetData/boot/SystemVersion.plist"; do
    echo "METADATA $path"
    plutil -p "$path" | awk 'length($0) < 1800'
done
echo MACVM_BOOT120_LOCAL_PRODUCT_FILES
cat "$preserved/file-sizes.txt"
echo MACVM_BOOT120_SFR_STATE
ls -la /System/Volumes/iSCPreboot/SFR /System/Volumes/iSCPreboot/SFR/current 2>&1 || true
find /System/Volumes/iSCPreboot -maxdepth 5 -name apticket.der -exec ls -l {} \; || true
date -u >"$preserved/CLONE_COMPLETE"
echo MACVM_BOOT120_LOCAL_PRODUCT_PRESERVE_END
