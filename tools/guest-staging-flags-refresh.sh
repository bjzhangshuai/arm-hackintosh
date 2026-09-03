#!/bin/bash
# Request ordinary stat calls for the exact known Apple cache. A separately
# opted-in, instruction-validated debugger bridge restores lost tmpfs metadata.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 ]] || exit 78
[[ $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_FLAGS_REFRESH_BEGIN
staging=/private/var/db/com.apple.xpc.roleaccountd.staging
bundle="$staging/exec/872415233.4126.xpc"
codesign --verify --strict --verbose=2 "$bundle"
ls -ldO "$staging/exec" "$staging/tmp"
ls -lOR "$bundle"
codesign --verify --strict --verbose=2 "$bundle"
touch /private/tmp/macvm-flags-repair-done
echo MACVM_FLAGS_REFRESH_END
