#!/bin/bash
# Read-only status in the known nested ARM Recovery, via the fixed controller.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_INSTALL_STATUS_BEGIN
date -u
ps -axo pid,ppid,comm | grep -E 'UpdateBrain|roleaccount|osinstallersetup|InstallAssistant' || true
tail -n 65 /var/log/install.log
echo MACVM_INSTALL_STATUS_END
