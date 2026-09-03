#!/bin/bash
# Export only the downloaded current installer archive to isolated Linux.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_INSTALL_BRAIN_EXPORT_BEGIN
archive=/var/tmp/OSISPredicateUpdateProductTemp/UpdateBrain.zip
[[ -f "$archive" ]] || exit 1
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$archive"
elif command -v openssl >/dev/null 2>&1; then
  openssl dgst -sha256 "$archive"
else
  echo MACVM_INSTALL_SOURCE_HASH_UNAVAILABLE_RECEIVER_HASH_REQUIRED
fi
curl --fail --max-time 120 -H 'Content-Type: application/zip' \
  --data-binary "@$archive" http://10.0.2.2:18567/updatebrain.zip
echo MACVM_INSTALL_BRAIN_EXPORT_END
