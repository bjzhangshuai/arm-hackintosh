#!/bin/bash
# One-shot, read-only B012/cache inspection in the existing ARM Recovery guest.
# Does not acknowledge dialogs, relaunch the installer, delete caches or reboot.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 && $(id -u) == 0 ]] || exit 78
target=/Volumes/macos26
volume_uuid=$(diskutil info -plist "$target" | plutil -extract VolumeUUID raw -o - -)
[[ "$volume_uuid" == 31209BA2-BC1F-4D51-99C1-4AFF986CB8AA ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_BOOT120_B012_EVIDENCE_BEGIN
date -u
ps -axo pid,ppid,pcpu,etime,comm | grep -E 'UpdateBrain|InstallAssistant|osinstallersetup|personaliz' || true
echo MACVM_BOOT120_B012_LOCAL_CACHE
ls -lah "$target/macOS Install Data"
find "$target/macOS Install Data" -maxdepth 4 -type f \
  \( -name '*.pkg' -o -name '*.partial' -o -name '*.dmg' -o -name '*.sproduct' -o -name '*.plist' \) \
  -exec stat -f '%z bytes %N' {} \;
df -h "$target"
echo MACVM_BOOT120_B012_INSTALL_LOG
tail -n 180 /var/log/install.log | awk 'length($0) < 1800'
echo MACVM_BOOT120_B012_RESTORE_ERRORS
restore=/System/Volumes/Data/private/tmp/tmp-mount-S6DjuV/restore.log
if [[ -f "$restore" ]]; then
  grep -n -i -E 'error|fail|personaliz|preparepackage|result|TSS|AMAuthInstall' "$restore" \
    | awk 'length($0) < 1800' | tail -n 100 || true
  echo MACVM_BOOT120_B012_RESTORE_TAIL
  tail -n 80 "$restore" | awk 'length($0) < 1800'
fi
echo MACVM_BOOT120_B012_EVIDENCE_END
