#!/bin/bash
# One-shot inspection; no installation, mount changes, network downloads or retry.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_SOURCE_STATE_BEGIN
date -u
mount
ls -la /Volumes
ls -la '/Volumes/Shared Support' 2>&1 || true
find '/Volumes/macos26/macOS Install Data/Locked Files' -maxdepth 8 -type f 2>/dev/null | head -50
find /var/tmp -maxdepth 5 -type f \( -name 'InstallInfo.plist' -o -name '*.zip' -o -name '*.dmg' \) 2>/dev/null | head -50
ps -axo pid,ppid,etime,comm | grep -E 'UpdateBrain|InstallAssistant|osinstallersetup' || true
echo MACVM_BOOT120_LOCAL_SOURCE_STATE_END
