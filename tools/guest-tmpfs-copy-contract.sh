#!/bin/bash
# One signed-copy metadata contract, only in the known ARM Recovery guest.
# Does not launch the installer, replace a cache, or alter any security policy.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_TMPFS_COPY_CONTRACT_BEGIN
trap 'echo MACVM_TMPFS_COPY_CONTRACT_END status=$?' EXIT
date -u
staging=/private/var/db/com.apple.xpc.roleaccountd.staging
source=/private/tmp/UpdateBrain-8U3B9PWJ/AssetData/com.apple.MobileSoftwareUpdate.UpdateBrainService.xpc
destination="$staging/tmp/macvm-compat-20260903.xpc"
[[ -d "$source" && ! -e "$destination" ]] || exit 78
[[ $(xattr -p com.apple.rootless "$staging") == RoleAccountStaging ]] || exit 78
[[ $(stat -f %d "$staging") == $(stat -f %d /private/tmp) ]] || exit 78
(( $(stat -f %f "$staging/tmp") & 0x80000 )) || exit 78
codesign --verify --strict --verbose=2 "$source" || exit 1
ditto --persistRootless "$source" "$destination" || exit 1
for relative in '' Contents Contents/Info.plist Contents/MacOS \
  Contents/MacOS/com.apple.MobileSoftwareUpdate.UpdateBrainService \
  Contents/MacOS/UpdateBrainLibrary.dylib; do
  item="$destination${relative:+/$relative}"
  [[ -e "$item" ]] || exit 1
  stat -f '%N flags=%f mode=%p' "$item" || exit 1
  (( $(stat -f %f "$item") & 0x80000 )) || exit 1
done
codesign --verify --strict --verbose=2 -R '= (anchor apple or (anchor apple generic and certificate leaf[field.1.2.840.113635.100.6.1.9])) and entitlement["com.apple.private.xpc.role-account"] exists' "$destination" || exit 1
echo MACVM_TMPFS_COPY_CONTRACT_PASS
