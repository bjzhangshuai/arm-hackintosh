#!/bin/bash
# Read-only evidence for this specific nested Recovery installation failure.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_ROLE_DIAGNOSTICS_BEGIN
date -u
ps -axo pid,comm | grep -E 'xpcroleaccountd|softwareupdated|InstallAssistant|osinstallersetupd'
mount
staging=/private/var/db/com.apple.xpc.roleaccountd.staging
ls -ldO "$staging" "$staging/exec" "$staging/tmp"
ls -laO "$staging/exec" "$staging/tmp"
source=/private/tmp/UpdateBrain-2WgUlaMr
find "$source" -name '*.xpc' -maxdepth 5 -print
find "$source" -name com.apple.MobileSoftwareUpdate.UpdateBrainService -maxdepth 8 -exec ls -lO '{}' \;
find "$source" -name '*.xpc' -maxdepth 5 -exec codesign --verify --strict --verbose=2 '{}' \;
echo MACVM_ROLE_SIGNATURE_DETAIL_BEGIN
bundle="$source/AssetData/com.apple.MobileSoftwareUpdate.UpdateBrainService.xpc"
codesign --verify --verbose=4 -R '= (anchor apple or (anchor apple generic and certificate leaf[field.1.2.840.113635.100.6.1.9])) and entitlement["com.apple.private.xpc.role-account"] exists' "$bundle"
codesign -d --entitlements :- "$bundle"
plutil -p "$bundle/Contents/Info.plist"
find "$bundle" -type l -ls
xattr -l "$staging"
echo MACVM_ROLE_SIGNATURE_DETAIL_END
sample 5583 1 1
echo MACVM_ROLE_LOG_BEGIN
log show --style compact --start '2026-09-03 04:40:00' --end '2026-09-03 04:43:00' --predicate 'process == "xpcroleaccountd"' 2>&1
echo MACVM_ROLE_DIAGNOSTICS_END
