#!/bin/bash
# Read-only SFR volume-discovery evidence after B015; never retry or mutate disks.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
[[ $(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
[[ -f "$target/macvm-local-product-25G83/LOCAL_RETRY_B015_REQUESTED" ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_B016_SFR_STATE_BEGIN
date -u
ps -axo pid,ppid,etime,comm | grep -E 'UpdateBrain|InstallAssistant|osinstallersetup' || true
diskutil list
diskutil apfs list
diskutil info /System/Volumes/iSCPreboot
mount | grep -E 'iSC|macos26|Recovery|tmp-mount' || true
ls -lad /System/Volumes/iSCPreboot /System/Volumes/iSCPreboot/SFR /System/Volumes/iSCPreboot/SFR/current 2>&1 || true
find /System/Volumes/iSCPreboot -maxdepth 3 -type d -print 2>/dev/null | head -n 60
echo MACVM_B016_RECOVERY_RESTORE_LOG
restore=/System/Volumes/Data/private/tmp/tmp-mount-OASW3q/restore.log
if [[ -f $restore ]]; then
    tail -n 200 "$restore" | awk 'length($0) < 1600'
fi
echo MACVM_B016_SFR_STATE_END
