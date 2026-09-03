#!/bin/bash
# Read-only target/preflight evidence; no old Boot119 disk numbers or PIDs.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_TARGET_STATE_BEGIN
date -u
diskutil info /Volumes/macos26
diskutil apfs list
echo MACVM_BOOT120_TARGET_INSTALL_LOG
tail -n 80 /var/log/install.log
echo MACVM_BOOT120_TARGET_RESTORE_LOG
tail -n 180 /System/Volumes/Data/MobileSoftwareUpdate/restore.log
echo MACVM_BOOT120_TARGET_UPDATE_RESTORE_LOG
# The original log records this exact migration after selecting the target's
# normal APFS container; retaining only the old log would hide later progress.
diskutil info /System/Volumes/Data/private/tmp/tmp-mount-S6DjuV
tail -n 180 /System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log | awk 'length($0) < 1000'
echo MACVM_BOOT120_TARGET_STATE_END
