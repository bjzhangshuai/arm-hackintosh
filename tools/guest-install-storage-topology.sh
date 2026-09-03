#!/bin/bash
# Read-only embedded/internal storage inventory for UpdateBrain target resolution.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_INSTALL_TOPOLOGY_BEGIN
date -u
ioreg -r -k EmbeddedDeviceTypeRoot -l -w0 -d 2
diskutil list physical
diskutil info disk0
diskutil info disk1
echo MACVM_INSTALL_TOPOLOGY_END
