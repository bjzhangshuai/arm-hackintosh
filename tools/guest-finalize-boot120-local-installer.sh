#!/bin/bash
# Complete only the previously staged local product. Does not launch/reboot.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
[[ $(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
product="$target/macvm-local-product-25G83"
app='/private/tmp/macvm-local-installer-25G83/Install macOS Tahoe.app'
[[ -f "$target/macvm-offline-25G83-boot120/CLONE_COMPLETE" && -d "$product/UpdateBundle-Static" && ! -e "$product/PREPARED_LOCAL_ONLY" ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_FINALIZE_BEGIN
date -u
# Recovery's original bundle passes. The moved bundle's custom omit rules do
# not; do not disable that check or re-sign it. Compare every original byte,
# file mode and symlink, and verify the actual signed executable separately.
/usr/bin/codesign --verify --deep '/Install macOS Tahoe.app'
curl --fail --silent --show-error --max-time 60 http://10.0.2.2:18566/b012-compare.pl -o /tmp/b012-compare.pl
/usr/bin/perl /tmp/b012-compare.pl '/Install macOS Tahoe.app' "$app" "$product"
/usr/bin/codesign --verify "$app/Contents/MacOS/InstallAssistant"
/usr/bin/codesign --verify "$app/Contents/Frameworks/OSInstallerSetup.framework/Versions/A/Resources/osinstallersetupd"
/usr/bin/codesign --verify --deep "$product/UpdateBrain-Static/AssetData/com.apple.MobileSoftwareUpdate.UpdateBrainService.xpc"
echo MACVM_BOOT120_LOCAL_EXECUTABLE_SIGNATURES_VALID
# Exact helper init at 0x1000014dc/0x100001504 adds this common defaults suite.
# The GUI uses the same suite. No force-success/security defaults are set.
domain=com.apple.InstallAssistant
if /usr/bin/defaults read "$domain" IASkipUnarchivingMSU >"$product/previous-unarchive-default.txt" 2>/dev/null; then
    echo present >"$product/previous-unarchive-default-state.txt"
else
    echo absent >"$product/previous-unarchive-default-state.txt"
fi
echo "$domain" >"$product/previous-unarchive-default-domain.txt"
/usr/bin/defaults write "$domain" IASkipUnarchivingMSU -bool YES
[[ $(/usr/bin/defaults read "$domain" IASkipUnarchivingMSU) == 1 ]] || exit 78
date -u >"$product/PREPARED_LOCAL_ONLY"
echo MACVM_BOOT120_LOCAL_FINALIZE_END
