#!/bin/bash
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 ]] || exit 78
product=/Volumes/macos26/macvm-offline-25G83-boot120
[[ -f "$product/CLONE_COMPLETE" ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_INFO_EXPORT_BEGIN
curl --fail --silent --show-error --max-time 90 -X POST \
    --data-binary "@$product/UpdateBundle/Info.plist" \
    http://10.0.2.2:18567/boot120-local-product-info.plist
echo MACVM_BOOT120_LOCAL_INFO_EXPORT_END
