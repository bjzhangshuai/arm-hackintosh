#!/bin/bash
# Read-only comparison of the original Apple app and its local copy.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 ]] || exit 78
[[ $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_SIGNATURE_INSPECTION_BEGIN
date -u
for app in '/Install macOS Tahoe.app' '/private/tmp/macvm-local-installer-25G83/Install macOS Tahoe.app'; do
    echo "APP=$app"
    /usr/bin/codesign --verify --deep "$app"
    echo "BUNDLE_VERIFY_RC=$?"
    /usr/bin/codesign -d -vvvv "$app"
    /sbin/md5 "$app/Contents/MacOS/InstallAssistant" "$app/Contents/Info.plist" "$app/Contents/_CodeSignature/CodeResources"
    /usr/bin/codesign --verify "$app/Contents/MacOS/InstallAssistant"
    echo "EXECUTABLE_VERIFY_RC=$?"
    plutil -extract rules2 xml1 -o - "$app/Contents/_CodeSignature/CodeResources"
done
product=/Volumes/macos26/macvm-local-product-25G83
/usr/bin/codesign --verify --deep "$product/UpdateBrain-Static/AssetData/com.apple.MobileSoftwareUpdate.UpdateBrainService.xpc"
echo "UPDATEBRAIN_VERIFY_RC=$?"
ls -ld "$product" "$product/UpdateBundle-Static" "$product/UpdateBrain-Static"
ps -axo pid,ppid,etime,comm | grep -E 'ditto|codesign|InstallAssistant|osinstallersetup' || true
echo MACVM_BOOT120_LOCAL_SIGNATURE_INSPECTION_END
