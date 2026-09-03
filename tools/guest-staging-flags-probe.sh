#!/bin/bash
# Bounded metadata-inheritance probe ONLY in the nested ARM Recovery guest.
# Creates one disposable probe directory; never changes an existing service.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 ]] || exit 78
[[ $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_FLAGS_PROBE_BEGIN
trap 'echo MACVM_FLAGS_PROBE_END status=$?' EXIT
staging=/private/var/db/com.apple.xpc.roleaccountd.staging/exec
[[ -d "$staging" && ! -L "$staging" ]] || exit 78
ls -ldO "$staging"
probe=$(mktemp -d "$staging/macvm-flags-probe.XXXXXX")
printf 'Probe path: %s\n' "$probe"
ls -ldO "$probe"
mkdir "$probe/child"
touch "$probe/child/empty"
chflags restricted "$probe/child/empty"
ls -ldO "$probe/child" "$probe/child/empty"
codesign -d -vvvv /bin/bash 2>&1 | head -35
