#!/bin/bash
# One explicit, read-only check; never schedules or retries any operation.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_ARCHIVE_PROGRESS_BEGIN
date -u
product=/Volumes/macos26/macvm-local-product-25G83
for name in UpdateBundle.zip.partial UpdateBundle.zip64.partial UpdateBundle.zip LOCAL_ARCHIVE_READY ARCHIVE_UI_LAUNCH_REQUESTED OFFLINE_EXPORT_ACCEPTED; do
    [[ ! -f "$product/$name" ]] || stat -f '%z bytes %N' "$product/$name"
done
df -Pk /Volumes/macos26
ps -axo pid,ppid,etime,comm | grep -E 'ditto|unzip|UpdateBrain|InstallAssistant|osinstallersetup' || true
echo MACVM_LOCAL_ARCHIVE_CONSOLE
[[ ! -f "$product/local-archive-installer-console.log" ]] || tail -n 50 "$product/local-archive-installer-console.log"
echo MACVM_LOCAL_ARCHIVE_INSTALL_LOG
tail -n 120 /var/log/install.log | awk 'length($0) < 1400'
echo MACVM_BOOT120_ARCHIVE_PROGRESS_END
