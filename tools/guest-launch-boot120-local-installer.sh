#!/bin/bash
# One explicit launch of the verified, unchanged InstallAssistant executable.
# This opens the UI only. It does not accept a target, start a download or reboot.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
product=/Volumes/macos26/macvm-local-product-25G83
app='/private/tmp/macvm-local-installer-25G83/Install macOS Tahoe.app'
[[ -f "$product/PREPARED_LOCAL_ONLY" && ! -e "$product/UI_LAUNCH_REQUESTED" ]] || exit 78
[[ $(diskutil info -plist /Volumes/macos26 | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
[[ $(/usr/bin/defaults read com.apple.InstallAssistant IASkipUnarchivingMSU) == 1 ]] || exit 78
if ps -axo comm | grep -E '/(InstallAssistant|osinstallersetupd)$'; then exit 78; fi
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_UI_LAUNCH_BEGIN
/usr/bin/codesign --verify "$app/Contents/MacOS/InstallAssistant"
date -u >"$product/UI_LAUNCH_REQUESTED"
# Recovery's secondary executable verifies normally. Its Apple signature and
# normal dyld/AMFI/library validation are not changed. No DYLD overrides.
"$app/Contents/MacOS/InstallAssistant" >"$product/local-installer-console.log" 2>&1 &
echo "MACVM_BOOT120_LOCAL_UI_PID=$!"
echo MACVM_BOOT120_LOCAL_UI_LAUNCH_END
