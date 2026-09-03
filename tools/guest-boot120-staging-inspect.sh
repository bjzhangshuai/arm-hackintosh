#!/bin/bash
# Read-only identity and staging lookup, to bind diagnostics to this boot.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_STAGING_INSPECT_BEGIN
uname -a
sw_vers
diskutil list physical
diskutil info /Volumes/macos26
ioreg -r -k EmbeddedDeviceTypeRoot -l -w0 -d 2
ls -ldO /private/var/db/com.apple.xpc.roleaccountd.staging \
  /private/var/db/com.apple.xpc.roleaccountd.staging/exec \
  /private/var/db/com.apple.xpc.roleaccountd.staging/tmp
echo MACVM_BOOT120_STAGING_INSPECT_END
