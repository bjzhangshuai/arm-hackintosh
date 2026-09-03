#!/bin/bash
# One bounded read-only sample of the already running Boot120 installer service.
# Not a benchmark; the temporary metadata debugger can affect timing.
set -u
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_CATALOG_SAMPLE_BEGIN
date -u
ps -p 734 -o pid,ppid,pcpu,etime,comm
[[ $(ps -p 734 -o comm=) == '/Install macOS Tahoe.app/Contents/Frameworks/OSInstallerSetup.framework/Resources/osinstallersetupd' ]] || exit 78
macvm_sample=/private/tmp/macvm-boot120-catalog.sample
[[ ! -e "$macvm_sample" ]] || exit 73
sample 734 3 20 -file "$macvm_sample"
macvm_sample_rc=$?
if [[ $macvm_sample_rc == 0 ]]; then
  head -n 260 "$macvm_sample"
fi
tail -n 25 /var/log/install.log
echo MACVM_BOOT120_CATALOG_SAMPLE_END
exit "$macvm_sample_rc"
