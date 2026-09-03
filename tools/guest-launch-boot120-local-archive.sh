#!/bin/bash
# One new UI launch after the local archive and both compatibility contracts
# are ready. Does not select a target, accept an error, or start a download.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
product=/Volumes/macos26/macvm-local-product-25G83
app='/private/tmp/macvm-local-installer-25G83/Install macOS Tahoe.app'
[[ -f "$product/LOCAL_ARCHIVE_READY" && -f "$product/UpdateBundle.zip" && ! -e "$product/ARCHIVE_UI_LAUNCH_REQUESTED" ]] || exit 78
[[ $(diskutil info -plist /Volumes/macos26 | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
skip=$(/usr/bin/defaults read com.apple.InstallAssistant IASkipUnarchivingMSU 2>/dev/null || true)
[[ -z $skip || $skip == 0 ]] || exit 78
if ps -axo comm | grep -E '/(InstallAssistant|osinstallersetupd)$'; then exit 78; fi
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_ARCHIVE_UI_BEGIN
/usr/bin/codesign --verify "$app/Contents/MacOS/InstallAssistant"
date -u >"$product/ARCHIVE_UI_LAUNCH_REQUESTED"
"$app/Contents/MacOS/InstallAssistant" >"$product/local-archive-installer-console.log" 2>&1 &
echo "MACVM_BOOT120_LOCAL_ARCHIVE_UI_PID=$!"
echo MACVM_BOOT120_LOCAL_ARCHIVE_UI_END
