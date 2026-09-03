#!/bin/bash
# Bounded foreground control helper for this nested ARM Recovery guest only.
# The server is loopback-only in the isolated Linux VM. Commands are an enum,
# never shell-evaluated server text. No account credentials are transported.
set -eu
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || exit 78
[[ $(sysctl -n hw.model) == VirtualMac2,1 ]] || exit 78
[[ $(sw_vers -buildVersion) == 25G72 ]] || exit 78
[[ $(id -u) == 0 ]] || exit 78
exec >/dev/console 2>&1
echo MACVM_INSTALL_CONTROL_READY
previous=
for ((iteration=0; iteration<1800; iteration++)); do
  action=$(curl -fsS --max-time 5 http://10.0.2.2:18566/action.txt 2>/dev/null) || action=
  if [[ -n "$action" && "$action" != "$previous" ]]; then
    previous=$action
    case "$action" in
      refresh)
        echo MACVM_FLAGS_REFRESH_BEGIN
        staging=/private/var/db/com.apple.xpc.roleaccountd.staging
        bundle="$staging/exec/872415233.4126.xpc"
        if codesign --verify --strict --verbose=2 "$bundle"; then
          ls -ldO "$staging/exec" "$staging/tmp"
          ls -lOR "$bundle"
          codesign --verify --strict --verbose=2 "$bundle"
          touch /private/tmp/macvm-flags-repair-done
          echo MACVM_FLAGS_REFRESH_END
        else
          echo MACVM_FLAGS_REFRESH_SIGNATURE_FAILED
        fi
        ;;
      inspect)
        echo MACVM_INSTALL_INSPECT_BEGIN
        diskutil info /Volumes/macos26
        tail -n 100 /var/log/install.log
        ls -lt /Library/Logs/DiagnosticReports | head -12
        echo MACVM_INSTALL_INSPECT_END
        ;;
      copy-contract)
        # This script is fetched once before enabling the metadata debugger.
        # Enum actions never evaluate arbitrary server-provided shell text.
        if [[ -f /private/tmp/macvm-tmpfs-copy-contract.sh ]]; then
          if bash /private/tmp/macvm-tmpfs-copy-contract.sh; then
            echo MACVM_COPY_CONTRACT_STATUS_0
          else
            printf 'MACVM_COPY_CONTRACT_STATUS %s\n' "$?"
          fi
        else
          echo MACVM_COPY_CONTRACT_SCRIPT_MISSING
        fi
        ;;
      role-inspect)
        echo MACVM_ROLE_INSPECT_BEGIN
        ps -axo pid,ppid,comm | grep -E 'UpdateBrain|roleaccount|osinstallersetup|InstallAssistant' || true
        launchctl print pid/8384 || true
        launchctl print pid/8347 || true
        echo MACVM_ROLE_INSPECT_END
        ;;
      run-probe)
        # Fixed, task-owned loopback resource containing a reviewed guest-only
        # diagnostic. No action text is interpolated into a shell command.
        if curl -f -o /private/tmp/macvm-reviewed-probe.sh http://10.0.2.2:18566/probe.sh && \
            bash -n /private/tmp/macvm-reviewed-probe.sh; then
          if bash /private/tmp/macvm-reviewed-probe.sh; then
            echo MACVM_REVIEWED_PROBE_STATUS_0
          else
            printf 'MACVM_REVIEWED_PROBE_STATUS %s\n' "$?"
          fi
        else
          echo MACVM_REVIEWED_PROBE_FETCH_FAILED
        fi
        ;;
      idle) : ;;
      installer)
        echo MACVM_INSTALL_OPEN_BEGIN
        '/Install macOS Tahoe.app/Contents/MacOS/InstallAssistant_springboard' &
        printf 'MACVM_INSTALL_PID %s\n' "$!"
        echo MACVM_INSTALL_OPEN_END
        ;;
      stop)
        echo MACVM_INSTALL_CONTROL_DONE
        exit 0
        ;;
      *) echo MACVM_INSTALL_CONTROL_UNKNOWN_ACTION ;;
    esac
  fi
  sleep 2
done
echo MACVM_INSTALL_CONTROL_EXPIRED
