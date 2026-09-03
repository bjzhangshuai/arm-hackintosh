#!/bin/bash
# Read-only target-preflight evidence in the current isolated ARM Recovery.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_INSTALL_TARGET_BEGIN
date -u
diskutil info /Volumes/macos26
diskutil apfs list
ps -axo pid,ppid,comm | grep -E 'UpdateBrain|roleaccount|osinstallersetup|InstallAssistant' || true
tail -n 90 /var/log/install.log
echo MACVM_INSTALL_TARGET_UNIFIED_BEGIN
/usr/bin/log show --last 15m --style compact --info --predicate \
  'process == "osinstallersetupd" OR process == "InstallAssistant" OR process == "com.apple.MobileSoftwareUpdate.UpdateBrainService"' \
  2>&1 | tail -n 160
echo MACVM_INSTALL_TARGET_LOG_PATHS
ls -la /var/log /private/var/MobileSoftwareUpdate /private/var/db/softwareupdate /Library/Logs 2>&1
find /private/var/log /private/var/MobileSoftwareUpdate /private/tmp \
  -maxdepth 3 -type f \( -iname '*log*' -o -iname '*error*' \) 2>/dev/null | head -n 100
echo MACVM_INSTALL_TARGET_ASL_BEGIN
grep -i -E 'MobileSoftware|UpdateBrain|MSU|preflight|target.*volume|LiveFS|disk7s1|macos26' \
  /var/log/system.log.T1788416904 /var/log/system.log /var/log/recoveryos.log \
  2>/dev/null | tail -n 140
echo MACVM_INSTALL_TARGET_END
