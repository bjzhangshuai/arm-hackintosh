#!/bin/bash
# Preserve B015's SIGABRT and installation logs before changing or retrying it.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
product=/Volumes/macos26/macvm-local-product-25G83
[[ -f "$product/LOCAL_RETRY_B015_REQUESTED" ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_B015_CRASH_EXPORT_BEGIN
date -u
archive=/private/tmp/macvm-boot120-b015-crash-20260903-1540.tar.gz
[[ ! -e "$archive" ]] || exit 73
sources=(private/var/log/install.log private/var/log/system.log Library/Logs/DiagnosticReports)
for source in System/Volumes/Data/MobileSoftwareUpdate/restore.log \
    System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log \
    Volumes/macos26/macvm-local-product-25G83/b015-local-archive-installer-console.log; do
    [[ ! -f "/$source" ]] || sources+=("$source")
done
tar -czf "$archive" -C / "${sources[@]}"
[[ $(stat -f %z "$archive") -le 67108864 ]] || exit 78
curl --fail --max-time 120 -H 'Content-Type: application/gzip' \
    --data-binary "@$archive" http://10.0.2.2:18567/boot120-b015-crash.tar.gz
echo MACVM_B015_CRASH_EXPORT_END
