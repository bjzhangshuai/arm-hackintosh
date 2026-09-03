#!/bin/bash
# One local retry, only after the operator verifies actual scoped bridge output
# from the preflight mode. The preflight never starts an installer or writes a
# launch marker. No automatic retry, reboot, OS download or preference changes.
set -euo pipefail
case ${1-} in preflight|launch) mode=$1 ;; *) exit 64 ;; esac
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
product="$target/macvm-local-product-25G83"
app='/private/tmp/macvm-local-installer-25G83/Install macOS Tahoe.app'
[[ $(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
[[ -f "$product/LOCAL_ARCHIVE_READY" && -f "$product/OFFLINE_EXPORT_ACCEPTED" && -f "$product/LOCAL_RETRY_B013_REQUESTED" ]] || exit 78
[[ -f "$product/UpdateBundle.zip" && $(stat -f %z "$product/UpdateBundle.zip") == 19203380932 ]] || exit 78
skip=$(/usr/bin/defaults read com.apple.InstallAssistant IASkipUnarchivingMSU 2>/dev/null || true)
[[ -z $skip || $skip == 0 ]] || exit 78
if ps -axo comm | grep -E '/(InstallAssistant|osinstallersetupd)$'; then exit 78; fi
/usr/bin/codesign --verify "$app/Contents/MacOS/InstallAssistant"
/usr/bin/codesign --verify "$app/Contents/Frameworks/OSInstallerSetup.framework/Versions/A/Resources/osinstallersetupd"
exec 3>/dev/console
if [[ $mode == preflight ]]; then
    echo MACVM_B015_PREFLIGHT_BEGIN >&3
    date -u >&3
    stage=/private/var/db/com.apple.xpc.roleaccountd.staging
    ls -ldO "$stage" "$stage/exec" "$stage/tmp" >&3
    echo MACVM_B015_PREFLIGHT_LOOKUP_DONE_VERIFY_BRIDGE_LOG_BEFORE_LAUNCH >&3
    exit 0
fi
marker="$product/LOCAL_RETRY_B015_REQUESTED"
console="$product/b015-local-archive-installer-console.log"
[[ ! -e "$marker" && ! -e "$console" ]] || exit 73
(set -o noclobber; date -u >"$marker") || exit 73
(set -o noclobber; : >"$console") || exit 73
echo MACVM_BOOT120_B015_LOG_STREAM_BEGIN >&3
date -u >&3
echo 'MACVM_PROGRESS_NOTE phase fractions are not overall installation percent; COMPLETED alone is not success' >&3
tail_pid=
finish_logs() {
    if [[ -n $tail_pid ]]; then
        kill "$tail_pid" 2>/dev/null || true
        wait "$tail_pid" 2>/dev/null || true
    fi
    echo MACVM_BOOT120_B015_LOG_STREAM_END >&3
}
trap finish_logs EXIT
/usr/bin/tail -n 0 -F /var/log/install.log "$console" >&3 2>&3 &
tail_pid=$!
"$app/Contents/MacOS/InstallAssistant" >>"$console" 2>&1 &
installer_pid=$!
echo "MACVM_BOOT120_B015_INSTALLER_PID=$installer_pid LOG_READER_PID=$tail_pid" >&3
result=0
wait "$installer_pid" || result=$?
echo "MACVM_BOOT120_B015_INSTALLER_UI_EXIT=$result (not proof of OS installation success)" >&3
/usr/bin/tail -n 50 /var/log/install.log >&3
exit "$result"
