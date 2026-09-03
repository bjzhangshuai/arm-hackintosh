#!/bin/bash
# Preserve volatile installation evidence before the approved planned shutdown.
# This does not stop any service, installer or VM.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_SHUTDOWN_LOGS_EXPORT_BEGIN
archive=/private/tmp/macvm-boot119-before-internal-logs.tar.gz
[[ ! -e "$archive" ]] || exit 73
tar -czf "$archive" -C / \
  private/var/log/install.log \
  private/var/log/system.log \
  System/Volumes/Data/MobileSoftwareUpdate/restore.log \
  Library/Logs/DiagnosticReports \
  private/tmp/macvm-updatebrain-target.sample
curl --fail --max-time 120 -H 'Content-Type: application/gzip' \
  --data-binary "@$archive" http://10.0.2.2:18567/shutdown-logs.tar.gz
echo MACVM_SHUTDOWN_LOGS_EXPORT_END
