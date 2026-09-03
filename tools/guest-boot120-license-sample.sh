#!/bin/bash
# Bounded observation of the existing UI and target-service wait, no restart.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_LICENSE_SAMPLE_BEGIN
date -u
[[ $(ps -p 703 -o comm=) == InstallAssistant ]] || exit 78
[[ $(ps -p 1232 -o comm=) == */872415233.3794.xpc/Contents/MacOS/com.apple.MobileSoftwareUpdate.UpdateBrainService ]] || exit 78
for macvm_pid in 703 1232; do
  macvm_sample=/private/tmp/macvm-boot120-license-$macvm_pid.sample
  [[ ! -e "$macvm_sample" ]] || exit 73
  ps -p "$macvm_pid" -o pid,ppid,pcpu,etime,comm
  if sample "$macvm_pid" 2 20 -file "$macvm_sample"; then
    head -n 180 "$macvm_sample"
  else
    echo MACVM_BOOT120_SAMPLE_FAILED
    exit 1
  fi
done
echo MACVM_BOOT120_LICENSE_SAMPLE_END
