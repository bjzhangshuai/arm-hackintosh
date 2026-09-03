#!/bin/bash
# One local-network copy into isolated Linux, not an internet upload/download.
# Start the fixed-size, loopback-only receiver first. Never uploads to GitHub.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
[[ $(diskutil info -plist /Volumes/macos26 | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
product=/Volumes/macos26/macvm-local-product-25G83
mode=${1:-verified}
[[ ! -e "$product/OFFLINE_EXPORT_ACCEPTED" ]] || exit 78
case $mode in
    verified)
        source_archive="$product/UpdateBundle.zip"
        [[ -f "$product/LOCAL_ARCHIVE_READY" && -f "$source_archive" ]] || exit 78 ;;
    closed-candidate)
        # The writer has exited: the packer's next synchronous process is the
        # already-observed read-only full CRC check. Copying can overlap that
        # check; neither the receipt nor the candidate is installation-ready.
        source_archive="$product/UpdateBundle.zip64.partial"
        [[ ! -e "$product/LOCAL_ARCHIVE_READY" && ! -e "$product/UpdateBundle.zip" ]] || exit 78
        [[ $(ps -ww -p 8673 -o command=) == "/usr/bin/unzip -tq $source_archive" ]] || exit 78
        [[ $(ps -p 8673 -o ppid= | tr -d ' ') == 8506 ]] || exit 78 ;;
    *) exit 78 ;;
esac
[[ -f "$source_archive" && ! -L "$source_archive" && $(stat -f %z "$source_archive") == 19203380932 ]] || exit 78
source_identity=$(stat -f '%d:%i:%z:%m' "$source_archive")
exec >/dev/console 2>&1
echo MACVM_BOOT120_OFFLINE_EXPORT_BEGIN
date -u
echo "MACVM_BOOT120_OFFLINE_EXPORT_MODE=$mode"
stat -f '%z bytes %N' "$source_archive"
curl --fail --silent --show-error --max-time 3500 --upload-file "$source_archive" \
    -X POST http://10.0.2.2:18567/boot120-local-UpdateBundle-25G83.zip
# The packer can atomically rename the same inode after its CRC passes.
[[ -f "$source_archive" ]] || source_archive="$product/UpdateBundle.zip"
[[ $(stat -f '%d:%i:%z:%m' "$source_archive") == "$source_identity" ]] || exit 78
date -u >"$product/OFFLINE_EXPORT_ACCEPTED"
echo MACVM_BOOT120_OFFLINE_EXPORT_END
