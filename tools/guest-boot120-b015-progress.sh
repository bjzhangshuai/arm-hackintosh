#!/bin/bash
# One explicitly requested read-only snapshot of B015; never a polling loop.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
product="$target/macvm-local-product-25G83"
[[ $(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
[[ -f "$product/LOCAL_RETRY_B015_REQUESTED" && -f "$product/LOCAL_ARCHIVE_READY" ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_B015_ACTUAL_PROGRESS_BEGIN
date -u
ps -axo pid,ppid,pcpu,etime,comm | grep -E 'UpdateBrain|InstallAssistant|osinstallersetup|ditto|unzip' || true
echo MACVM_B015_OPEN_ARCHIVE_OFFSETS_NOT_OVERALL_PERCENT
# Only query the exact already-established B015 helper if its identity is intact.
helper_comm=$(ps -p 10793 -o comm= 2>/dev/null || true)
case $helper_comm in
    */osinstallersetupd)
        /usr/sbin/lsof -nP -o -p 10793 2>/dev/null | grep -E '(^COMMAND|UpdateBundle|ExtractedFiles|macOS Install Data)' || true
        ;;
    *) echo MACVM_B015_HELPER_IDENTITY_CHANGED_NO_LSOF ;;
esac
df -Pk "$target"
echo MACVM_B015_CURRENT_INSTALL_LOG
tail -n 90 /var/log/install.log | awk 'length($0) < 1600'
echo MACVM_B015_CURRENT_CONSOLE_LOG
tail -n 70 "$product/b015-local-archive-installer-console.log" | awk 'length($0) < 1600'
echo MACVM_B015_CURRENT_RESTORE_LOG
restore=/System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log
[[ ! -f $restore ]] || tail -n 70 "$restore" | awk 'length($0) < 1600'
echo MACVM_B015_ACTUAL_PROGRESS_END
