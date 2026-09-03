#!/bin/bash
# Export existing failure logs privately; never restart or modify installation.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_B012_EXPORT_BEGIN
archive=/private/tmp/macvm-boot120-personalization-20260903-logs.tar.gz
[[ ! -e "$archive" ]] || exit 73
tar -czf "$archive" -C / \
  private/var/log/install.log \
  private/var/log/system.log \
  System/Volumes/Data/MobileSoftwareUpdate/restore.log \
  System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log \
  Library/Logs/DiagnosticReports
curl --fail --max-time 120 -H 'Content-Type: application/gzip' \
  --data-binary "@$archive" http://10.0.2.2:18567/boot120-personalization-logs.tar.gz
echo MACVM_BOOT120_B012_EXPORT_END
