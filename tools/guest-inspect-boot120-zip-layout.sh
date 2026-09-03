#!/bin/bash
# Read-only ZIP layout/decoder inspection; no reconstruction or installer launch.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_ZIP_LAYOUT_BEGIN
date -u
/usr/bin/unzip -v
ps -axo pid,ppid,etime,comm | grep -E 'ditto|unzip|InstallAssistant|osinstallersetup' || true
/usr/bin/perl - '/Volumes/macos26/macvm-local-product-25G83/UpdateBundle.zip.partial' <<'PERL'
use strict;
use warnings;
my $file = shift; open(my $fh, '<', $file) or die $!; binmode($fh);
my $size = -s $fh; die "size" unless $size == 19204730974;
seek($fh, $size - 131072, 0) or die $!;
read($fh, my $tail, 131072) == 131072 or die "short tail";
my $end = rindex($tail, "PK\x05\x06"); die "EOCD missing" unless $end >= 0;
my @e = unpack('VvvvvVVv', substr($tail, $end, 22));
print "ZIP_SIZE=$size EOCD_ABSOLUTE=", $size - 131072 + $end, " FIELDS=@e\n";
print "FINAL_160_HEX=", unpack('H*', substr($tail, -160)), "\n";
print "ZIP64_EOCD_IN_TAIL=", rindex($tail, "PK\x06\x06"), " ZIP64_LOCATOR_IN_TAIL=", rindex($tail, "PK\x06\x07"), "\n";
for my $offset ($e[6], $size - 131072 + $end - $e[5]) {
    seek($fh, $offset, 0) or die $!;
    read($fh, my $header, 80) == 80 or die "short header";
    print "HEADER_AT=$offset HEX=", unpack('H*', $header), "\n";
}
close($fh);
PERL
echo MACVM_BOOT120_ZIP_LAYOUT_END
