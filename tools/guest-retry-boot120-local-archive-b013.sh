#!/bin/bash
# One explicitly authorized retry after B013. Run this wrapper under nohup.
# Follow install.log into the existing serial console; keep all GUI services.
# No timer, scheduled task, download of OS assets, reboot or automatic retry.
set -euo pipefail
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 && $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
product="$target/macvm-local-product-25G83"
app='/private/tmp/macvm-local-installer-25G83/Install macOS Tahoe.app'
[[ $(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -) == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
[[ -f "$product/LOCAL_ARCHIVE_READY" && -f "$product/OFFLINE_EXPORT_ACCEPTED" ]] || exit 78
[[ -f "$product/ARCHIVE_UI_LAUNCH_REQUESTED" && -f "$product/UpdateBundle.zip" ]] || exit 78
[[ $(stat -f %z "$product/UpdateBundle.zip") == 19203380932 ]] || exit 78
skip=$(/usr/bin/defaults read com.apple.InstallAssistant IASkipUnarchivingMSU 2>/dev/null || true)
[[ -z $skip || $skip == 0 ]] || exit 78
# A previously idle XPC helper is not an installer UI and is not killed.
if ps -axo comm | grep -E '/InstallAssistant$'; then exit 78; fi
/usr/bin/codesign --verify "$app/Contents/MacOS/InstallAssistant"
marker="$product/LOCAL_RETRY_B013_REQUESTED"
console="$product/b013-local-archive-installer-console.log"
[[ ! -e "$marker" && ! -e "$console" ]] || exit 73
# Exclusive creation prevents accidentally launching this retry twice.
(set -o noclobber; date -u >"$marker") || exit 73
(set -o noclobber; : >"$console") || exit 73
exec 3>/dev/console
echo MACVM_BOOT120_B013_LOG_STREAM_BEGIN >&3
date -u >&3
echo 'MACVM_PROGRESS_NOTE phase fractions are not overall installation percent; COMPLETED alone is not success' >&3
tail_pid=
finish_logs() {
    if [[ -n $tail_pid ]]; then
        kill "$tail_pid" 2>/dev/null || true
        wait "$tail_pid" 2>/dev/null || true
    fi
    echo MACVM_BOOT120_B013_LOG_STREAM_END >&3
}
trap finish_logs EXIT
# No system.log -> /dev/console feedback. -F tolerates install.log rotation.
# This reader belongs only to this launch and is stopped when the UI exits.
/usr/bin/tail -n 0 -F /var/log/install.log "$console" >&3 2>&3 &
tail_pid=$!
"$app/Contents/MacOS/InstallAssistant" >>"$console" 2>&1 &
installer_pid=$!
echo "MACVM_BOOT120_B013_INSTALLER_PID=$installer_pid LOG_READER_PID=$tail_pid" >&3
result=0
wait "$installer_pid" || result=$?
echo "MACVM_BOOT120_B013_INSTALLER_UI_EXIT=$result (not proof of OS installation success)" >&3
/usr/bin/tail -n 50 /var/log/install.log >&3
exit "$result"
