#!/bin/bash
# One local-network copy into isolated Linux, not an internet upload/download.
# Start the fixed-size, loopback-only receiver first. Never uploads to GitHub.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
[[ $(diskutil info -plist /Volumes/macos26 | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
product=/Volumes/macos26/macvm-local-product-25G83
[[ -f "$product/LOCAL_ARCHIVE_READY" && -f "$product/UpdateBundle.zip" && ! -e "$product/OFFLINE_EXPORT_ACCEPTED" ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_OFFLINE_EXPORT_BEGIN
date -u
stat -f '%z bytes %N' "$product/UpdateBundle.zip"
curl --fail --silent --show-error --max-time 3500 --upload-file "$product/UpdateBundle.zip" \
    -X POST http://10.0.2.2:18567/boot120-local-UpdateBundle-25G83.zip
date -u >"$product/OFFLINE_EXPORT_ACCEPTED"
echo MACVM_BOOT120_OFFLINE_EXPORT_END
