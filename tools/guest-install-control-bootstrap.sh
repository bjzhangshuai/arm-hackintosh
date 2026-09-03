#!/bin/bash
# Preload the two fixed reviewed helpers before enabling a guest debugger.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
curl -f -o /private/tmp/macvm-tmpfs-copy-contract.sh http://10.0.2.2:18566/copy-contract.sh || exit 1
curl -f -o /private/tmp/macvm-install-controller.sh http://10.0.2.2:18566/control.sh || exit 1
bash /private/tmp/macvm-install-controller.sh
