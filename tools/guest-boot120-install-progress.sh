#!/bin/bash
# Read-only observation of the existing Boot120 installation; no UI actions.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_INSTALL_PROGRESS_BEGIN
date -u
ps -p 703,734,1232 -o pid,ppid,pcpu,etime,comm
echo MACVM_BOOT120_INSTALL_DATA_FILES
ls -lah '/Volumes/macos26/macOS Install Data'
df -h /Volumes/macos26
echo MACVM_BOOT120_INSTALL_PROGRESS_LOG
tail -n 100 /var/log/install.log | awk 'length($0) < 1000'
echo MACVM_BOOT120_INSTALL_PROGRESS_UPDATE_LOG
tail -n 100 /System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log | awk 'length($0) < 1000'
echo MACVM_BOOT120_INSTALL_PROGRESS_END
