#!/bin/bash
# Read-only launch-domain and role-account requirement checks, Recovery only.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_ROLE_LAUNCH_STATE_BEGIN
launchctl print pid/7027
launchctl print system/com.apple.xpc.roleaccountd
bundle=/private/tmp/UpdateBrain-2WgUlaMr/AssetData/com.apple.MobileSoftwareUpdate.UpdateBrainService.xpc
codesign --verify --verbose=4 -R '= (anchor apple or (anchor apple generic and certificate leaf[field.1.2.840.113635.100.6.1.9])) and entitlement["com.apple.private.xpc.role-account"] exists' "$bundle"
echo MACVM_ROLE_LAUNCH_STATE_END
