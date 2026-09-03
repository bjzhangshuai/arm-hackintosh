#!/bin/bash
# Bounded, non-destructive metadata evidence in this ARM Recovery only.
# One new disposable directory tests ordinary tmpfs creation; existing objects
# are only read. No security policy, signatures, mounts or flags are changed.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_FILESYSTEM_EVIDENCE_BEGIN
date -u
staging=/private/var/db/com.apple.xpc.roleaccountd.staging
for location in "$staging" "$staging/tmp" "$staging/exec"; do
  ls -ldeO@ "$location"
  xattr -l "$location"
done
mount
df -h /private/tmp /Volumes/macos26
codesign -d --entitlements :- /usr/libexec/xpcroleaccountd
launchctl print system/com.apple.xpc.roleaccountd
umask 077
probe=$(mktemp -d /private/tmp/macvm-filesystem-probe.XXXXXX) || exit 1
printf 'MACVM_FS_NEW_PROBE %s\n' "$probe"
mkdir "$probe/ordinary-child"
printf 'MACVM_FS_ORDINARY_MKDIR_STATUS %s\n' "$?"
ls -ldeO@ "$probe" "$probe/ordinary-child"
# This separate root-shell probe does not share xpcroleaccountd's entitlements.
# Record that limitation; do not treat its errno as the daemon's errno.
mktemp -d "$staging/tmp/macvm-filesystem-probe.XXXXXX"
printf 'MACVM_FS_ROOT_SHELL_STAGING_MKDIR_STATUS %s\n' "$?"
echo MACVM_FILESYSTEM_EVIDENCE_END
