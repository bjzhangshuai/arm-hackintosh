#!/bin/bash
# One explicit read-only staging/process snapshot. No installer launch/cleanup.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_B014_STAGING_EVIDENCE_BEGIN
date -u
ps -axo pid,ppid,etime,comm | grep -E 'UpdateBrain|InstallAssistant|osinstallersetup|xpcroleaccount' || true
stage=/private/var/db/com.apple.xpc.roleaccountd.staging
ls -ldO "$stage" "$stage/exec" "$stage/tmp"
ls -laO "$stage/exec" "$stage/tmp"
stat -f 'inode=%i flags=%f path=%N' "$stage" "$stage/exec" "$stage/tmp"
echo MACVM_B014_STAGING_EVIDENCE_END
