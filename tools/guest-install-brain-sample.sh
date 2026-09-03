#!/bin/bash
# Read-only runtime identity and target-resolution logs in the known Recovery.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_INSTALL_BRAIN_SAMPLE_BEGIN
date -u
ps -p 10501 -o pid,ppid,comm
sample 10501 1 1 -file /private/tmp/macvm-updatebrain-target.sample
grep -E '^Process:|^Path:|^Code Type:|^Identifier:|UpdateBrainLibrary|UpdateBrainService' \
  /private/tmp/macvm-updatebrain-target.sample | tail -n 20
ls -l /private/tmp/restore.log /var/log/restore.log /restore.log 2>&1
echo MACVM_INSTALL_BRAIN_RESTORE_LOG_BEGIN
tail -n 180 /System/Volumes/Data/MobileSoftwareUpdate/restore.log 2>&1
echo MACVM_INSTALL_BRAIN_RESTORE_LOG_END
ioreg -r -c IOMedia -l -w0 | grep -E 'EmbeddedDeviceType|Content|BSD Name|UUID|Whole|Size' | head -n 160
echo MACVM_INSTALL_BRAIN_SAMPLE_END
