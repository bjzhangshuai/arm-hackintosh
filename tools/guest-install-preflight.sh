#!/bin/bash
# Read-only inspection, intended ONLY for the nested ARM macOS Recovery guest.
# Serve this file from a loopback-only HTTP server in the isolated Linux VM.
# Do not execute it on the production Mac or Linux host.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 ]] || exit 78
[[ $(id -u) == 0 ]] || exit 78

exec >/dev/console 2>&1
echo MACVM_PREFLIGHT_BEGIN
trap 'echo MACVM_PREFLIGHT_END status=$?' EXIT
diskutil info disk6
ioreg -p IOUSB -l -w0 | grep -E 'USB Serial Number|QEMU USB HARDD'
ls -ldO /private/var /private/var/db \
  /private/var/db/com.apple.xpc.roleaccountd.staging \
  /private/var/db/com.apple.xpc.roleaccountd.staging/exec \
  /private/var/db/com.apple.xpc.roleaccountd.staging/exec/872415233.4126.xpc
ls -l /etc/rc.* || true
grep -n -E 'roleaccount|tmpfs|restricted' \
  /etc/rc.* /System/Library/Sandbox/rootless.conf || true
cat /etc/rc.cdrom.sh
ls -ldO /System/Library/Templates/Data/private/var/db/com.apple.xpc.roleaccountd.staging \
  /System/Library/Templates/Data/private/var/db/com.apple.xpc.roleaccountd.staging/exec || true
ls -l /usr/libexec/rootless-init /usr/libexec/xpcroleaccountd || true
strings /usr/libexec/rootless-init | grep -A 12 -B 3 -E 'usage:|Usage:' || true
