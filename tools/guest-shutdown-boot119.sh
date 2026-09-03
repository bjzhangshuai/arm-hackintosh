#!/bin/bash
# User-approved normal shutdown of the exact nested ARM Recovery guest only.
# Install has not started. QMP shutdown=pause preserves the shutdown boundary.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
diskutil info /Volumes/macos26 | grep -q '31209BA2-BC1F-4D51-99C1-4AFF986CB8AA' || exit 78
[[ -f /private/tmp/macvm-boot119-before-internal-logs.tar.gz ]] || exit 78
echo MACVM_BOOT119_APPROVED_NORMAL_SHUTDOWN
sync
/sbin/shutdown -h now
