#!/bin/bash
# The initial BOM/ditto writer wrapped 64-bit offsets: preserve that artifact,
# test the existing libarchive writer on a tiny ZIP64 fixture, then package once.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
[[ $(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
master="$target/macvm-offline-25G83-boot120"
product="$target/macvm-local-product-25G83"
bad="$product/UpdateBundle.zip.partial"
rejected="$target/macvm-rejected-bom-archive-25G83.zip"
partial="$product/UpdateBundle.zip64.partial"
archive="$product/UpdateBundle.zip"
probe="$product/zip64-probe.zip"
probe_extract="$product/zip64-probe-libarchive"
mode=${1:-new}
[[ -f "$master/CLONE_COMPLETE" && -f "$product/PREPARED_LOCAL_ONLY" ]] || exit 78
[[ ! -e "$partial" && ! -e "$archive" && ! -e "$probe_extract" ]] || exit 78
case $mode in
    new)
        [[ -f "$bad" && $(stat -f %z "$bad") == 19204730974 && ! -e "$rejected" && ! -e "$probe" ]] || exit 78 ;;
    resume-after-reader-check)
        [[ ! -e "$bad" && -f "$probe" && -f "$rejected" && $(stat -f %z "$rejected") == 19204730974 ]] || exit 78 ;;
    *) exit 78 ;;
esac
available=$(df -Pk "$target" | awk 'NR==2 {print $4}')
[[ $available =~ ^[0-9]+$ && $available -gt 25165824 ]] || exit 78
exec >/dev/console 2>&1
echo "MACVM_BOOT120_ZIP64_PACK_BEGIN mode=$mode"
date -u
# Stop only our now-proven-invalid CRC test, never the installer or VM.
if [[ $mode == new ]]; then
crc_command=$(ps -ww -p 8357 -o command= || true)
if [[ -n $crc_command ]]; then
    [[ $crc_command == "/usr/bin/unzip -tq $bad" ]] || exit 78
    kill -TERM 8357
    for ((attempt=0; attempt<20; attempt++)); do
        [[ -z $(ps -p 8357 -o pid= || true) ]] && break
        sleep 1
    done
    [[ -z $(ps -p 8357 -o pid= || true) ]] || exit 78
fi
mv -n "$bad" "$rejected"
echo MACVM_BOOT120_INVALID_BOM_ARCHIVE_PRESERVED
fi
/usr/bin/tar --version
if [[ $mode == new ]]; then
/usr/bin/tar --format zip --options zip:zip64=1,zip:compression=store -cf "$probe" -C "$master/UpdateBundle" Info.plist
fi
/usr/bin/unzip -tq "$probe"
/usr/bin/perl - "$probe" <<'PERL'
use strict; use warnings;
open(my $fh, '<', shift) or die $!; binmode($fh);
seek($fh, -200, 2) or die $!;
read($fh, my $tail, 200) == 200 or die "short ZIP64 tail";
die "ZIP64 footer/locator missing" unless index($tail, "PK\x06\x06") >= 0 && index($tail, "PK\x06\x07") >= 0;
print "MACVM_BOOT120_ZIP64_WRITER_PROBE_PASS crc=valid zip64_footer=present zip64_locator=present\n";
PERL
# Source: OSISStreamingZipExtractor at 0x2333c calls _unzipViaLibarchiveWithError,
# NOT ditto/BOM. Both bsdtar and that implementation use libarchive.2.dylib.
mkdir -m 700 "$probe_extract"
/usr/bin/tar -xf "$probe" -C "$probe_extract"
[[ $(/sbin/md5 -q "$probe_extract/Info.plist") == $(/sbin/md5 -q "$master/UpdateBundle/Info.plist") ]] || exit 78
echo MACVM_BOOT120_ZIP64_LIBARCHIVE_READER_PROBE_PASS
# No compression, no fake CRC, no signature edits and no remote source.
/usr/bin/tar --format zip --options zip:zip64=1,zip:compression=store -cf "$partial" -C "$master/UpdateBundle" .
echo MACVM_BOOT120_ZIP64_ARCHIVE_WRITTEN
stat -f '%z bytes %N' "$partial"
/usr/bin/unzip -tq "$partial"
echo MACVM_BOOT120_ZIP64_ARCHIVE_CRC_VALID
[[ ! -e "$archive" ]] || exit 78
mv -n "$partial" "$archive"
domain=$(<"$product/previous-unarchive-default-domain.txt")
[[ $domain == com.apple.InstallAssistant && $(/usr/bin/defaults read "$domain" IASkipUnarchivingMSU) == 1 ]] || exit 78
case $(<"$product/previous-unarchive-default-state.txt") in
    absent) /usr/bin/defaults delete "$domain" IASkipUnarchivingMSU ;;
    present)
        value=$(<"$product/previous-unarchive-default.txt")
        [[ $value == 0 || $value == 1 ]] || exit 78
        /usr/bin/defaults write "$domain" IASkipUnarchivingMSU -bool "$value" ;;
    *) exit 78 ;;
esac
date -u >"$product/LOCAL_ARCHIVE_READY"
echo MACVM_BOOT120_ZIP64_PACK_END
