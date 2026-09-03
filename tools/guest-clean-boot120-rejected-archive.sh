#!/bin/bash
# Remove only this task's invalid BOM ZIP, after the replacement and its local
# Linux backup are verified. Preserve its structural evidence and all OS assets.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
[[ $(diskutil info -plist /Volumes/macos26 | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
product=/Volumes/macos26/macvm-local-product-25G83
master=/Volumes/macos26/macvm-offline-25G83-boot120
bad=/Volumes/macos26/macvm-rejected-bom-archive-25G83.zip
evidence="$master/rejected-bom-zip-structure"
[[ -f "$master/CLONE_COMPLETE" && -f "$product/LOCAL_ARCHIVE_READY" && -f "$product/OFFLINE_EXPORT_ACCEPTED" ]] || exit 78
[[ $(stat -f %z "$product/UpdateBundle.zip") == 19203380932 ]] || exit 78
[[ -f "$bad" && ! -L "$bad" && $(stat -f %z "$bad") == 19204730974 && ! -e "$evidence" ]] || exit 78
# The local server exposes this report only after the Linux validator succeeds.
report=$(mktemp /private/tmp/macvm-boot120-archive-validation.XXXXXX)
curl --fail --silent --show-error --max-time 120 \
    http://10.0.2.2:18566/boot120-local-archive-validation.json -o "$report"
[[ $(plutil -extract archive_bytes raw -o - "$report") == 19203380932 ]] || exit 78
[[ $(plutil -extract regular_files raw -o - "$report") == 2233 ]] || exit 78
[[ $(plutil -extract regular_bytes raw -o - "$report") == 19202615016 ]] || exit 78
[[ $(plutil -extract crc raw -o - "$report") == 'all entries passed' ]] || exit 78
[[ $(plutil -extract info_sha256 raw -o - "$report") == 8659fdc115aa7e26a3bce2b7637eccf748c94cfb89712f0d28b76e78eded14a1 ]] || exit 78
[[ -z $(ps -p 8357 -o pid= || true) ]] || exit 78
before=$(stat -f '%d:%i:%z:%m' "$bad")
exec >/dev/console 2>&1
mkdir -m 700 "$evidence"
dd if="$bad" of="$evidence/archive-prefix.bin" bs=4096 count=1
tail -c 316905 "$bad" >"$evidence/central-directory-and-eocd.bin"
[[ $(stat -f %z "$evidence/archive-prefix.bin") == 4096 && $(stat -f %z "$evidence/central-directory-and-eocd.bin") == 316905 ]] || exit 78
[[ $(stat -f '%d:%i:%z:%m' "$bad") == "$before" ]] || exit 78
# Exact, observed, task-generated invalid artifact; never a source package,
# image, working archive, installation disk or production resource.
rm -- /Volumes/macos26/macvm-rejected-bom-archive-25G83.zip
[[ ! -e "$bad" && -f "$master/CLONE_COMPLETE" && -f "$product/UpdateBundle.zip" ]] || exit 78
echo MACVM_BOOT120_INVALID_BOM_ZIP_REMOVED_BYTES_19204730974
echo MACVM_BOOT120_SOURCE_PAYLOAD_VALID_ARCHIVE_AND_LINUX_COPY_PRESERVED
df -Pk /Volumes/macos26
