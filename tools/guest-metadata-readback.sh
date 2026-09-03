#!/bin/bash
# Read-only validation of shell status semantics and the APFS copy evidence.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_METADATA_READBACK_BEGIN
printf 'SHELL_VERSION=%s options=%s\n' "$BASH_VERSION" "$-"
head -n 12 /tmp/m
shasum -a 256 /tmp/m
false
printf 'FALSE_STATUS=%s\n' "$?"
[[ x == y ]]
printf 'UNEQUAL_STATUS=%s\n' "$?"
((0))
printf 'ZERO_ARITH_STATUS=%s\n' "$?"
if [[ x == y ]]; then echo CONDITIONAL_BROKEN; else echo CONDITIONAL_OK; fi
/bin/bash -c 'set -e; false; echo ERREXIT_UNEXPECTED_CONTINUE'
printf 'ERREXIT_CHILD_STATUS=%s\n' "$?"
env | grep '^DITTO' || true
volume=/Volumes/macvm-staging
template=/System/Library/Templates/Data/private/var/db/com.apple.xpc.roleaccountd.staging
stat -f '%N flags=%f mode=%p' "$template" "$volume" "$volume/tmp" "$volume/exec"
xattr -l "$template"
xattr -l "$volume"
DITTO_TEST_OPTIONS=1 ditto --persistRootless "$template" "$volume"
echo MACVM_METADATA_READBACK_END
