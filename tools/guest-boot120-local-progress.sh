#!/bin/bash
# One explicit read-only local-installer status capture, never a timer.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_PROGRESS_BEGIN
date -u
ps -axo pid,ppid,etime,comm | grep -E 'UpdateBrain|InstallAssistant|osinstallersetup' || true
echo MACVM_LOCAL_APP_CONSOLE
tail -n 60 /Volumes/macos26/macvm-local-product-25G83/local-installer-console.log | awk 'length($0) < 1600'
echo MACVM_LOCAL_INSTALL_LOG
tail -n 170 /var/log/install.log | awk 'length($0) < 1400'
echo MACVM_BOOT120_LOCAL_PROGRESS_END
