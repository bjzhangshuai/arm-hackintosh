#!/bin/bash
# Read the remainder of the existing sample; do not resample or restart anything.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_CATALOG_READBACK_BEGIN
sed -n '250,480p' /private/tmp/macvm-boot120-catalog.sample
tail -n 25 /var/log/install.log
echo MACVM_BOOT120_CATALOG_READBACK_END
