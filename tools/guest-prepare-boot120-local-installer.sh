#!/bin/bash
# One explicit local staging. Does NOT launch an installer or reboot.
# Final identity/signature checks are in guest-finalize-boot120-local-installer.sh.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 ]] || exit 78
[[ $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
uuid=$(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -)
[[ $uuid == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
master="$target/macvm-offline-25G83-boot120"
product="$target/macvm-local-product-25G83"
app_parent=/private/tmp/macvm-local-installer-25G83
app="$app_parent/Install macOS Tahoe.app"
original='/Install macOS Tahoe.app'
[[ -f "$master/CLONE_COMPLETE" && -d "$original" ]] || exit 78
[[ ! -e "$product" && ! -e "$app_parent" ]] || exit 78
for command in /bin/cp /usr/bin/ditto /usr/bin/defaults /usr/bin/codesign; do
    [[ -x $command ]] || exit 78
done
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_INSTALLER_PREPARE_BEGIN
date -u
mkdir -m 700 "$product" "$app_parent"
/bin/cp -cRp "$master/UpdateBundle" "$product/UpdateBundle-Static"
local_http=http://10.0.2.2:18566
# Only the isolated Linux VM's fixed local server; never Apple's CDN.
curl --fail --silent --show-error --max-time 180 "$local_http/boot120-local-catalog.plist" \
    -o "$product/com_apple_MobileAsset_MacSoftwareUpdate.xml"
curl --fail --silent --show-error --max-time 180 "$local_http/boot120-local-InstallInfo.plist" \
    -o "$product/InstallInfo.plist"
curl --fail --silent --show-error --max-time 300 "$local_http/boot120-local-UpdateBrain.zip" \
    -o "$product/UpdateBrain.zip"
/usr/bin/ditto -x -k "$product/UpdateBrain.zip" "$product/UpdateBrain-Static"
/usr/bin/ditto "$original" "$app"
[[ ! -e "$app/Contents/SharedSupport" ]] || exit 78
ln -s "$product" "$app/Contents/SharedSupport"
# Recovery's app bundle uses location-sensitive custom omit rules. The initial
# run stopped at bundle verification here. Never re-sign or disable validation;
# the separate finalizer compares all bytes with the verified original and
# verifies the actual executable/helper/UpdateBrain before setting local routing.
date -u >"$product/STAGED_LOCAL_ONLY"
echo MACVM_BOOT120_LOCAL_INSTALLER_PREPARE_END
