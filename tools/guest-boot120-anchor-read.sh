#!/bin/bash
# Trigger one read-only lookup for the separately bounded Boot120 observer.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_ANCHOR_READ_BEGIN
ls -ldO /private/var/db/com.apple.xpc.roleaccountd.staging
macvm_anchor_read_rc=$?
echo MACVM_BOOT120_ANCHOR_READ_END
exit "$macvm_anchor_read_rc"
