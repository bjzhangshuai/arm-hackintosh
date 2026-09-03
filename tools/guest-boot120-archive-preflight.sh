#!/bin/bash
# One read-only preflight before the archive-backed installer is launched.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
[[ $(diskutil info -plist /Volumes/macos26 | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_ARCHIVE_PREFLIGHT_BEGIN
date -u
product=/Volumes/macos26/macvm-local-product-25G83
for name in UpdateBundle.zip LOCAL_ARCHIVE_READY OFFLINE_EXPORT_ACCEPTED ARCHIVE_UI_LAUNCH_REQUESTED; do
    [[ ! -f "$product/$name" ]] || stat -f '%z bytes %N' "$product/$name"
done
echo MACVM_BOOT120_STATIC_PREFERENCE
defaults read com.apple.InstallAssistant IASkipUnarchivingMSU 2>/dev/null || true
echo MACVM_BOOT120_STAGING_CHILDREN
stage=/private/var/db/com.apple.xpc.roleaccountd.staging
ls -ldO "$stage" "$stage/exec" "$stage/tmp"
ls -laO "$stage/exec" "$stage/tmp"
echo MACVM_BOOT120_RELEVANT_PROCESSES
ps -axo pid,ppid,etime,comm | grep -E 'InstallAssistant|osinstallersetupd|UpdateBrain|unzip|curl' || true
echo MACVM_BOOT120_PREPARED_LAUNCHER
[[ ! -f /tmp/l2 ]] || /sbin/md5 -q /tmp/l2
df -Pk /Volumes/macos26
echo MACVM_BOOT120_ARCHIVE_PREFLIGHT_END
