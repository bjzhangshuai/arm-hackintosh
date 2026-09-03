#!/bin/bash
# Preserve the second personalization failure before any installer retry.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LOCAL_PREPARE_EXPORT_BEGIN
date -u
archive=/private/tmp/macvm-boot120-local-prepare-crash-20260903-1330.tar.gz
[[ ! -e "$archive" ]] || exit 73
sources=(private/var/log/install.log private/var/log/system.log Library/Logs/DiagnosticReports)
for source in System/Volumes/Data/MobileSoftwareUpdate/restore.log \
  System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log; do
  [[ ! -f "/$source" ]] || sources+=("$source")
done
tar -czf "$archive" -C / "${sources[@]}"
curl --fail --max-time 120 -H 'Content-Type: application/gzip' \
  --data-binary "@$archive" http://10.0.2.2:18567/boot120-local-prepare-crash.tar.gz
echo MACVM_BOOT120_LOCAL_PREPARE_EXPORT_END
