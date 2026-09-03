#!/bin/bash
# Repackage preserved, unchanged files locally. No CDN download or installer.
# RETIRED: this Recovery's BOM/ditto writer truncates offsets above 4 GiB.
# Kept as evidence only; use the source-reviewed libarchive ZIP64 workflow.
echo 'Refusing retired BOM archive writer: known 32-bit offset truncation' >&2
exit 78
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
[[ $(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
master="$target/macvm-offline-25G83-boot120"
product="$target/macvm-local-product-25G83"
archive="$product/UpdateBundle.zip"
[[ -f "$master/CLONE_COMPLETE" && -f "$product/PREPARED_LOCAL_ONLY" && ! -e "$archive" && ! -e "$archive.partial" ]] || exit 78
[[ -x /usr/bin/unzip && -x /usr/bin/ditto ]] || exit 78
available=$(df -Pk "$target" | awk 'NR==2 {print $4}')
[[ $available =~ ^[0-9]+$ && $available -gt 25165824 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_ARCHIVE_BEGIN
date -u
echo MACVM_LOCAL_STAGING_CURRENT
ls -ldO /private/var/db/com.apple.xpc.roleaccountd.staging \
    /private/var/db/com.apple.xpc.roleaccountd.staging/exec \
    /private/var/db/com.apple.xpc.roleaccountd.staging/tmp
# Standard ZIP64/BOMArchive format, zero compression to avoid unnecessary TCG
# compression work. Preserve resource metadata. Apple payload/signature bytes
# are unchanged; this is NOT claimed to be Apple's original ZIP bitstream.
/usr/bin/ditto -c -k --sequesterRsrc --zlibCompressionLevel 0 "$master/UpdateBundle" "$archive.partial"
echo MACVM_BOOT120_LOCAL_ARCHIVE_WRITTEN
stat -f '%z bytes %N' "$archive.partial"
/usr/bin/unzip -tq "$archive.partial"
echo MACVM_BOOT120_LOCAL_ARCHIVE_CRC_VALID
[[ ! -e "$archive" ]] || exit 78
mv -n "$archive.partial" "$archive"
# Full _setDefaultDestinationPaths control flow shows Recovery takes getenv's
# branch before the static-path preference. Restore only our own unused flag.
domain=$(<"$product/previous-unarchive-default-domain.txt")
[[ $domain == com.apple.InstallAssistant && $(/usr/bin/defaults read "$domain" IASkipUnarchivingMSU) == 1 ]] || exit 78
case $(<"$product/previous-unarchive-default-state.txt") in
    absent) /usr/bin/defaults delete "$domain" IASkipUnarchivingMSU ;;
    present)
        value=$(<"$product/previous-unarchive-default.txt")
        [[ $value == 0 || $value == 1 ]] || exit 78
        /usr/bin/defaults write "$domain" IASkipUnarchivingMSU -bool "$value" ;;
    *) exit 78 ;;
esac
date -u >"$product/LOCAL_ARCHIVE_READY"
echo MACVM_BOOT120_LOCAL_ARCHIVE_END
