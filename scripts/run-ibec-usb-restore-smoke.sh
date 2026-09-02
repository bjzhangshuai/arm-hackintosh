#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/lib/require-debug-env.sh"
macvm_require_debug_env

PYTHON_BIN="${PYTHON_BIN:-python3}"
QEMU_BIN="${MACVM_QEMU_BIN:-$REPO_ROOT/build/qemu/qemu-system-aarch64}"
QEMU_IMG_BIN="${MACVM_QEMU_IMG_BIN:-qemu-img}"
GDB_BIN="${MACVM_GDB_BIN:-gdb-multiarch}"
RESTORE_DIR="${MACVM_RESTORE_DIR:-/home/macvm/macos-restore/26.6}"
RUN_ROOT="${MACVM_RUN_ROOT:-/home/macvm/runs/aux-26.6}"
POST_TRACE_SCRIPT="${MACVM_GDB_POST_TRACE_SCRIPT:-}"
FINAL_TRACE_SCRIPT="${MACVM_GDB_FINAL_TRACE_SCRIPT:-}"
BASESYSTEM_TRACE_SCRIPT="$REPO_ROOT/tools/inject_basesystem_auth_and_boot_args_trace_mount.gdb"
SYMLINK_ONLY_TRACE_SCRIPT="$REPO_ROOT/tools/trace_basesystem_symlink_preflight_live.gdb"
if [[ -n "${MACVM_GDB_TRACE_SCRIPT:-}" ]]; then
  TRACE_SCRIPT="$MACVM_GDB_TRACE_SCRIPT"
elif [[ -n "$POST_TRACE_SCRIPT" ]]; then
  # A two-stage run must release the bootstrap GDB connection once iBEC's AUX
  # BDIF is ready.  The regular light trace intentionally remains attached at
  # the recovery prompt and would deadlock the runner before the command-phase
  # helper and POST_TRACE_SCRIPT can start.
  TRACE_SCRIPT="$REPO_ROOT/tools/trace_ibec_usb_restore_bootstrap_detach.gdb"
else
  TRACE_SCRIPT="$REPO_ROOT/tools/trace_ibec_usb_restore_light.gdb"
fi
SESSION_TOOL="${MACVM_SESSION_TOOL:-$REPO_ROOT/tools/usb_restore_session.py}"
VCPUS="${MACVM_SMOKE_VCPUS:-4}"
MEMORY_GIB="${MACVM_SMOKE_MEMORY_GIB:-4}"
ECID="${MACVM_SMOKE_ECID:-0x1122334455667788}"
VMAPPLE_CFG_SERIAL="${MACVM_VMAPPLE_CFG_SERIAL:-}"
VMAPPLE_CFG_MODEL="${MACVM_VMAPPLE_CFG_MODEL:-}"
VMAPPLE_CFG_SOC_NAME="${MACVM_VMAPPLE_CFG_SOC_NAME:-}"
GDB_PORT="${MACVM_GDB_PORT:-12345}"
QEMU_TIMEOUT="${MACVM_QEMU_TIMEOUT:-210s}"
GDB_TIMEOUT="${MACVM_GDB_TIMEOUT:-180s}"
POST_GDB_TIMEOUT="${MACVM_POST_GDB_TIMEOUT:-$GDB_TIMEOUT}"
FINAL_GDB_TIMEOUT="${MACVM_FINAL_GDB_TIMEOUT:-30s}"
QEMU_DISPLAY="${MACVM_QEMU_DISPLAY:-none}"
POST_GDB_ATTACH_GRACE_SECONDS="${MACVM_POST_GDB_ATTACH_GRACE_SECONDS:-1}"
STAGE2_PROMPT_TIMEOUT_SECONDS="${MACVM_STAGE2_PROMPT_TIMEOUT_SECONDS:-45}"
SESSION_CONNECT_TIMEOUT="${MACVM_SESSION_CONNECT_TIMEOUT:-45}"
SESSION_RECV_TIMEOUT="${MACVM_SESSION_RECV_TIMEOUT:-90}"
SESSION_STEPS_FILE="${MACVM_SESSION_STEPS_FILE:-}"
POST_HELPER_GRACE_SECONDS="${MACVM_POST_HELPER_GRACE_SECONDS:-2}"
POST_GDB_MILESTONE_TIMEOUT_SECONDS="${MACVM_POST_GDB_MILESTONE_TIMEOUT_SECONDS:-600}"
RUN_NAME="${MACVM_RUN_NAME:-ibec-usb-restore-smoke-$(date +%Y%m%d-%H%M%S)}"
TRACE_VERBOSE="${MACVM_SMOKE_TRACE_VERBOSE:-NO}"
PAUSE_ON_REBOOT="${MACVM_PAUSE_ON_REBOOT:-NO}"
KEEP_QEMU_RUNNING_AFTER_HELPER="${MACVM_KEEP_QEMU_RUNNING_AFTER_HELPER:-NO}"
QEMU_LOG_ITEMS="${MACVM_QEMU_LOG_ITEMS:-}"
ROOT_IMAGE="${MACVM_ROOT_IMAGE:-}"
EXPOSE_ROOT_VIRTIO="${MACVM_EXPOSE_ROOT_VIRTIO:-NO}"
ISC_IMAGE="${MACVM_ISC_IMAGE:-}"
LEGACY_EXPOSE_AUX_VIRTIO="${MACVM_EXPOSE_AUX_VIRTIO:-}"
EXPOSE_ISC_VIRTIO="${MACVM_EXPOSE_ISC_VIRTIO:-${LEGACY_EXPOSE_AUX_VIRTIO:-NO}}"
EXPOSE_UTIL_VIRTIO="${MACVM_EXPOSE_UTIL_VIRTIO:-NO}"
ISC_VALIDATOR="${MACVM_ISC_VALIDATOR:-$REPO_ROOT/tools/build_vmapple_isc.py}"
RECOVERY_IMAGE="${MACVM_RECOVERY_IMAGE:-}"
RECOVERY_VOLUME_UUID="${MACVM_RECOVERY_VOLUME_UUID:-}"
EXPOSE_RECOVERY_VIRTIO="${MACVM_EXPOSE_RECOVERY_VIRTIO:-NO}"
RECOVERY_VALIDATOR="${MACVM_RECOVERY_VALIDATOR:-$REPO_ROOT/tools/build_vmapple_recovery.py}"
RAMDISK_OVERRIDE_IMAGE="${MACVM_RAMDISK_OVERRIDE_IMAGE:-}"
RAMDISK_OVERRIDE_ADDRESS="${MACVM_RAMDISK_OVERRIDE_ADDRESS:-}"
RAMDISK_OVERRIDE_VALIDATOR="${MACVM_RAMDISK_OVERRIDE_VALIDATOR:-$REPO_ROOT/tools/validate_ramdisk_override.py}"
RESTORE_TRUSTCACHE_IMAGE="${MACVM_RESTORE_TRUSTCACHE_IMAGE:-}"
BASESYSTEM_TRUSTCACHE_IMAGE="${MACVM_BASESYSTEM_TRUSTCACHE_IMAGE:-}"
TRUSTCACHE_OVERRIDE_ADDRESS="${MACVM_TRUSTCACHE_OVERRIDE_ADDRESS:-}"
TRUSTCACHE_REGION_TOOL="${MACVM_TRUSTCACHE_REGION_TOOL:-$REPO_ROOT/tools/trustcache_region.py}"
UNIX_SOCKET_PATH_MAX=100
STAGE2_PROMPT="Entering iBootStage2 recovery mode, starting command prompt"

require_file() {
  local path="$1"
  if [[ ! -r "$path" ]]; then
    echo "macvm: required restore asset is missing: $path" >&2
    exit 66
  fi
}

require_executable() {
  local path="$1"
  if ! command -v "$path" >/dev/null 2>&1 && [[ ! -x "$path" ]]; then
    echo "macvm: required executable is missing: $path" >&2
    exit 69
  fi
}

require_uint_range() {
  local name="$1"
  local value="$2"
  local min="$3"
  local max="$4"

  if [[ ! "$value" =~ ^[0-9]+$ ]] || (( value < min || value > max )); then
    echo "macvm: $name must be an integer from $min through $max, got: $value" >&2
    exit 64
  fi
}

require_u64_literal() {
  local name="$1"
  local value="$2"

  if ! "$PYTHON_BIN" - "$name" "$value" <<'PY'
import sys

name, value = sys.argv[1], sys.argv[2]
try:
    parsed = int(value, 0)
except ValueError:
    print(f"macvm: {name} must be a uint64 literal, got: {value}", file=sys.stderr)
    raise SystemExit(1)

if parsed < 0 or parsed > 0xFFFFFFFFFFFFFFFF:
    print(f"macvm: {name} must fit in uint64, got: {value}", file=sys.stderr)
    raise SystemExit(1)
PY
  then
    exit 64
  fi
}

require_vmapple_cfg_string() {
  local name="$1"
  local value="$2"

  if [[ -z "$value" ]]; then
    return 0
  fi

  if (( ${#value} > 31 )); then
    echo "macvm: $name must fit in the vmapple-cfg 31-byte string field, got ${#value} characters" >&2
    exit 64
  fi

  if [[ "$value" == *$'\n'* || "$value" == *$'\r'* ]]; then
    echo "macvm: $name must be a single-line vmapple-cfg string" >&2
    exit 64
  fi
}

validate_basesystem_post_trace_coupling() {
  local requires_basesystem_injection="NO"
  local post_trace_basename

  if [[ -n "$RAMDISK_OVERRIDE_IMAGE" || -n "$RESTORE_TRUSTCACHE_IMAGE" || \
        -n "$BASESYSTEM_TRUSTCACHE_IMAGE" || -n "$TRUSTCACHE_OVERRIDE_ADDRESS" ]]; then
    requires_basesystem_injection="YES"
  fi

  if [[ "$requires_basesystem_injection" == "NO" ]]; then
    return 0
  fi

  if [[ -z "$POST_TRACE_SCRIPT" ]]; then
    echo "macvm: BaseSystem RAMDisk/TrustCache overrides require an injecting post-GDB trace" >&2
    echo "macvm: set MACVM_GDB_POST_TRACE_SCRIPT=$BASESYSTEM_TRACE_SCRIPT" >&2
    exit 64
  fi

  post_trace_basename="${POST_TRACE_SCRIPT##*/}"
  if [[ "$POST_TRACE_SCRIPT" == "$SYMLINK_ONLY_TRACE_SCRIPT" || \
        "$post_trace_basename" == "trace_basesystem_symlink_preflight_live.gdb" ]]; then
    echo "macvm: BaseSystem RAMDisk/TrustCache overrides cannot use the symlink-only post-GDB trace" >&2
    echo "macvm: symlink-only tracing does not inject rd=md0, BaseSystem auth, or TrustCache handoff state" >&2
    echo "macvm: set MACVM_GDB_POST_TRACE_SCRIPT=$BASESYSTEM_TRACE_SCRIPT" >&2
    exit 64
  fi

  if [[ "$post_trace_basename" == "inject_basesystem_auth_and_boot_args_trace_mount.gdb" || \
        "$post_trace_basename" == "inject_basesystem_auth_and_boot_args.gdb" ]]; then
    if [[ -z "${MACVM_BASESYSTEM_AUTH_BLOB:-}" ]]; then
      echo "macvm: MACVM_BASESYSTEM_AUTH_BLOB is required by the BaseSystem injecting post-GDB trace" >&2
      exit 64
    fi
  fi
}

wait_for_socket() {
  local socket_path="$1"
  local attempt

  for attempt in {1..400}; do
    if [[ -S "$socket_path" ]]; then
      return 0
    fi
    sleep 0.05
  done

  echo "macvm: timed out waiting for restore socket: $socket_path" >&2
  return 70
}

wait_for_log_pattern() {
  local log_path="$1"
  local pattern="$2"
  local timeout_seconds="$3"
  local deadline

  deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if [[ -r "$log_path" ]] && grep -Fq "$pattern" "$log_path"; then
      return 0
    fi
    sleep 0.25
  done

  echo "macvm: timed out waiting for log pattern in $log_path: $pattern" >&2
  return 70
}

is_yes_like() {
  case "${1:-}" in
    1|[Yy][Ee][Ss]|[Tt][Rr][Uu][Ee]|[Oo][Nn])
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

stop_process() {
  local pid="${1:-}"

  if [[ -z "$pid" ]]; then
    return 0
  fi

  # GNU timeout creates an isolated process group whose ID is its own PID.
  # Signal that exact group when present so QEMU/GDB cannot survive if the
  # wrapper is interrupted; ordinary helpers fall back to their exact PID.
  if kill -0 -- "-$pid" >/dev/null 2>&1; then
    kill -TERM -- "-$pid" >/dev/null 2>&1 || true
  elif kill -0 "$pid" >/dev/null 2>&1; then
    kill -TERM "$pid" >/dev/null 2>&1 || true
  fi
}

collect_status() {
  local name="$1"
  local pid="$2"
  local status_file="$3"
  local rc

  set +e
  wait "$pid"
  rc=$?
  set -e
  printf '%s=%s\n' "$name" "$rc" >"$status_file"
  return 0
}

prepare_gdb_trace_script() {
  local source_script="$1"
  local output_name="$2"
  local output_script

  if [[ -z "$source_script" ]]; then
    printf '\n'
    return 0
  fi

  output_script="$RUN_DIR/$output_name"
  "$PYTHON_BIN" - "$source_script" "$output_script" "$GDB_PORT" <<'PY'
from pathlib import Path
import hashlib
import re
import sys

source = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2])
port = sys.argv[3]
source_re = re.compile(r"^(?P<indent>\s*)source\s+(?P<path>\S+)(?P<tail>.*)$")
remote_re = re.compile(r"target remote 127[.]0[.]0[.]1:[0-9]+")
copied: dict[Path, Path] = {}


def nested_target_for(path: Path) -> Path:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
    return target.parent / f"{target.name}.d" / f"{digest}-{path.name}"


def copy_gdb_source(path: Path, out: Path) -> None:
    path = path.resolve()
    if path in copied:
        return
    copied[path] = out
    text = path.read_text(encoding="utf-8")
    text = remote_re.sub(f"target remote 127.0.0.1:{port}", text)
    rendered = []
    for line in text.splitlines():
        match = source_re.match(line)
        if match:
            raw = match.group("path")
            nested = Path(raw)
            if not nested.is_absolute():
                nested = path.parent / nested
            if nested.exists():
                nested_out = copied.get(nested.resolve()) or nested_target_for(nested.resolve())
                copy_gdb_source(nested, nested_out)
                line = f"{match.group('indent')}source {nested_out}{match.group('tail')}"
        rendered.append(line)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rendered) + "\n", encoding="utf-8")
    out.with_suffix(out.suffix + ".source").write_text(str(path) + "\n", encoding="utf-8")


copy_gdb_source(source, target)
PY
  printf '%s\n' "$output_script"
}

run_final_gdb_trace() {
  local rc

  if [[ -z "$FINAL_TRACE_SCRIPT" ]]; then
    return 0
  fi

  set +e
  timeout "$FINAL_GDB_TIMEOUT" "$GDB_BIN" -q -batch -x "$FINAL_TRACE_SCRIPT_RUN" \
    >"$RUN_DIR/final-gdb.log" 2>&1
  rc=$?
  set -e
  printf 'FINAL_GDB_RC=%s\n' "$rc" >"$RUN_DIR/final-gdb.status"

  if [[ "$rc" != "0" ]]; then
    echo "macvm: final natural-run GDB snapshot failed with exit code $rc" >&2
    echo "macvm: evidence retained at $RUN_DIR" >&2
    return 70
  fi
}

validate_restore_session_evidence() {
  local helper_rc

  helper_rc="$(sed -n 's/^HELPER_RC=//p' "$RUN_DIR/helper.status")"
  if [[ "$helper_rc" != "0" ]]; then
    echo "macvm: restore socket helper failed with exit code $helper_rc" >&2
    echo "macvm: evidence retained at $RUN_DIR" >&2
    exit 70
  fi

  if ! grep -Fq '"event": "recv-match"' "$RUN_DIR/session.jsonl"; then
    echo "macvm: restore socket did not receive the expected 0402 response" >&2
    echo "macvm: evidence retained at $RUN_DIR" >&2
    exit 70
  fi

  if ! grep -Fq "$STAGE2_PROMPT" "$RUN_DIR/serial.log"; then
    echo "macvm: iBEC did not reach the Stage2 recovery prompt" >&2
    echo "macvm: evidence retained at $RUN_DIR" >&2
    exit 70
  fi

  if ! grep -Fq "bdif_usb_restore_packet action=chardev-in" "$RUN_DIR/trace.log" ||
     ! grep -Fq "bdif_usb_restore_packet action=chardev-out" "$RUN_DIR/trace.log"; then
    echo "macvm: QEMU did not trace both restore chardev directions" >&2
    echo "macvm: evidence retained at $RUN_DIR" >&2
    exit 70
  fi
}

required_post_gdb_milestone() {
  local post_trace_basename

  if [[ -z "$POST_TRACE_SCRIPT" ]]; then
    return 0
  fi

  post_trace_basename="${POST_TRACE_SCRIPT##*/}"
  if [[ "$post_trace_basename" != "inject_basesystem_auth_and_boot_args_trace_mount.gdb" ]]; then
    return 0
  fi

  if is_yes_like "${MACVM_DETACH_AFTER_PACKAGESLINK:-}"; then
    printf '%s\n' "MACVM_SYMLINK_DETACH_AFTER_PACKAGESLINK"
  else
    printf '%s\n' "MACVM_IMGSRC_STATE_APPLIED"
  fi
}

collect_post_gdb_status_if_needed() {
  if [[ -n "$POST_GDB_PID" ]]; then
    collect_status "POST_GDB_RC" "$POST_GDB_PID" "$RUN_DIR/post-gdb.status"
    POST_GDB_PID=""
  fi
}

wait_for_post_gdb_milestone_if_needed() {
  local pattern
  local deadline

  pattern="$(required_post_gdb_milestone)"
  if [[ -z "$pattern" ]]; then
    sleep "$POST_HELPER_GRACE_SECONDS"
    return 0
  fi

  deadline=$((SECONDS + POST_GDB_MILESTONE_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if [[ -r "$RUN_DIR/post-gdb.log" ]] && grep -Fq "$pattern" "$RUN_DIR/post-gdb.log"; then
      return 0
    fi

    if [[ -r "$RUN_DIR/post-gdb.log" ]] && \
       grep -Eq 'Cannot execute this command while the target is running|MACVM_(BASESYSTEM_HANDOFF_REFUSED|PIVOT_GUARD_REFUSED|IMGSRC_STATE_REFUSED|IMGSRC_STATE_ROLLBACK_FAILED)' "$RUN_DIR/post-gdb.log"
    then
      echo "macvm: post-GDB hit a fatal BaseSystem trace failure before required milestone: $pattern" >&2
      echo "macvm: evidence retained at $RUN_DIR" >&2
      exit 70
    fi

    if [[ -n "$POST_GDB_PID" ]] && ! kill -0 "$POST_GDB_PID" >/dev/null 2>&1; then
      collect_post_gdb_status_if_needed
      echo "macvm: post-GDB exited before required milestone: $pattern" >&2
      echo "macvm: evidence retained at $RUN_DIR" >&2
      exit 70
    fi

    sleep 0.5
  done

  echo "macvm: timed out waiting for required post-GDB milestone: $pattern" >&2
  echo "macvm: evidence retained at $RUN_DIR" >&2
  exit 70
}

resume_qemu_if_debug_paused() {
  "$PYTHON_BIN" - "$QMP_SOCK" <<'PY' >"$RUN_DIR/qmp-resume.log" 2>&1
from __future__ import annotations

import json
import socket
import sys
import time


socket_path = sys.argv[1]


def qmp_command(sock: socket.socket, command: dict[str, object]) -> dict[str, object]:
    sock.sendall((json.dumps(command) + "\r\n").encode())
    buffer = b""
    while True:
        chunk = sock.recv(8192)
        if not chunk:
            raise RuntimeError("QMP socket closed while waiting for a response")
        buffer += chunk
        while b"\r\n" in buffer:
            line, buffer = buffer.split(b"\r\n", 1)
            if not line:
                continue
            response = json.loads(line.decode("utf-8", errors="replace"))
            if "return" in response or "error" in response:
                return response


with socket.socket(socket.AF_UNIX) as sock:
    sock.settimeout(10)
    sock.connect(socket_path)
    greeting = sock.recv(8192)
    print(json.dumps({"greeting": bool(greeting)}, sort_keys=True))
    print(json.dumps({"qmp_capabilities": qmp_command(sock, {"execute": "qmp_capabilities"})}, sort_keys=True))
    before = qmp_command(sock, {"execute": "query-status"})
    print(json.dumps({"before": before}, sort_keys=True))
    status = before.get("return", {})
    if isinstance(status, dict) and not status.get("running", False):
        print(json.dumps({"cont": qmp_command(sock, {"execute": "cont"})}, sort_keys=True))
        time.sleep(0.25)
    after = qmp_command(sock, {"execute": "query-status"})
    print(json.dumps({"after": after}, sort_keys=True))
    after_status = after.get("return", {})
    if isinstance(after_status, dict) and not after_status.get("running", False):
        raise RuntimeError(f"QEMU remained paused after QMP cont: {after_status}")
PY
}

validate_qemu_exit_status() {
  local qemu_rc
  qemu_rc="$(sed -n 's/^QEMU_RC=//p' "$RUN_DIR/qemu.status")"
  if [[ "$qemu_rc" == "0" ]]; then
    return 0
  fi
  # The short smoke path deliberately sends TERM after collecting its evidence.
  # A continuing boot has no expected signal exit, and timeout is not success.
  if [[ "$KEEP_QEMU_RUNNING_AFTER_HELPER" == "NO" && "$qemu_rc" == "143" ]]; then
    return 0
  fi
  echo "macvm: QEMU exited unsuccessfully (QEMU_RC=${qemu_rc:-missing}); restore helper success does not imply boot success" >&2
  echo "macvm: evidence retained at $RUN_DIR" >&2
  return 70
}

finish_qemu_after_helper() {
  if [[ "$KEEP_QEMU_RUNNING_AFTER_HELPER" == "YES" ]]; then
    resume_qemu_if_debug_paused
    echo "macvm: keeping QEMU running after restore helper until it exits or MACVM_QEMU_TIMEOUT expires"
    collect_status "QEMU_RC" "$QEMU_PID" "$RUN_DIR/qemu.status"
    QEMU_PID=""
    validate_qemu_exit_status
    return
  fi

  run_final_gdb_trace
  stop_process "$QEMU_PID"
  collect_status "QEMU_RC" "$QEMU_PID" "$RUN_DIR/qemu.status"
  QEMU_PID=""
  validate_qemu_exit_status
}

session_step_args=()
if [[ -n "${MACVM_SESSION_STEPS:-}" && -n "$SESSION_STEPS_FILE" ]]; then
  echo "macvm: MACVM_SESSION_STEPS and MACVM_SESSION_STEPS_FILE are mutually exclusive" >&2
  exit 64
elif [[ -n "$SESSION_STEPS_FILE" ]]; then
  if [[ "$SESSION_STEPS_FILE" != /* ]]; then
    echo "macvm: MACVM_SESSION_STEPS_FILE must be an absolute path, got: $SESSION_STEPS_FILE" >&2
    exit 64
  fi
  if [[ ! -r "$SESSION_STEPS_FILE" ]]; then
    echo "macvm: MACVM_SESSION_STEPS_FILE is not readable: $SESSION_STEPS_FILE" >&2
    exit 66
  fi
  while IFS= read -r step || [[ -n "$step" ]]; do
    if [[ -n "$step" && ! "$step" =~ ^[[:space:]]*# ]]; then
      session_step_args+=(--step "$step")
    fi
  done < "$SESSION_STEPS_FILE"
elif [[ -n "${MACVM_SESSION_STEPS:-}" ]]; then
  while IFS= read -r step; do
    if [[ -n "$step" && ! "$step" =~ ^[[:space:]]*# ]]; then
      session_step_args+=(--step "$step")
    fi
  done <<< "$MACVM_SESSION_STEPS"
else
  session_step_args=(
    --step send:0202
    --step expect:0402
  )
fi

require_uint_range "MACVM_SMOKE_VCPUS" "$VCPUS" 1 16
require_uint_range "MACVM_SMOKE_MEMORY_GIB" "$MEMORY_GIB" 1 36
require_uint_range "MACVM_GDB_PORT" "$GDB_PORT" 1024 65535
require_uint_range "MACVM_STAGE2_PROMPT_TIMEOUT_SECONDS" "$STAGE2_PROMPT_TIMEOUT_SECONDS" 1 300
require_uint_range "MACVM_POST_GDB_MILESTONE_TIMEOUT_SECONDS" "$POST_GDB_MILESTONE_TIMEOUT_SECONDS" 1 3600
require_executable "$PYTHON_BIN"
require_u64_literal "MACVM_SMOKE_ECID" "$ECID"
require_vmapple_cfg_string "MACVM_VMAPPLE_CFG_SERIAL" "$VMAPPLE_CFG_SERIAL"
require_vmapple_cfg_string "MACVM_VMAPPLE_CFG_MODEL" "$VMAPPLE_CFG_MODEL"
require_vmapple_cfg_string "MACVM_VMAPPLE_CFG_SOC_NAME" "$VMAPPLE_CFG_SOC_NAME"

if [[ "$PAUSE_ON_REBOOT" != "YES" && "$PAUSE_ON_REBOOT" != "NO" ]]; then
  echo "macvm: MACVM_PAUSE_ON_REBOOT must be YES or NO, got: $PAUSE_ON_REBOOT" >&2
  exit 64
fi

if [[ "$KEEP_QEMU_RUNNING_AFTER_HELPER" != "YES" && "$KEEP_QEMU_RUNNING_AFTER_HELPER" != "NO" ]]; then
  echo "macvm: MACVM_KEEP_QEMU_RUNNING_AFTER_HELPER must be YES or NO, got: $KEEP_QEMU_RUNNING_AFTER_HELPER" >&2
  exit 64
fi

if [[ "$EXPOSE_ROOT_VIRTIO" != "YES" && "$EXPOSE_ROOT_VIRTIO" != "NO" ]]; then
  echo "macvm: MACVM_EXPOSE_ROOT_VIRTIO must be YES or NO, got: $EXPOSE_ROOT_VIRTIO" >&2
  exit 64
fi

if [[ -n "${MACVM_EXPOSE_ISC_VIRTIO:-}" && -n "$LEGACY_EXPOSE_AUX_VIRTIO" && \
      "$MACVM_EXPOSE_ISC_VIRTIO" != "$LEGACY_EXPOSE_AUX_VIRTIO" ]]; then
  echo "macvm: MACVM_EXPOSE_ISC_VIRTIO conflicts with legacy MACVM_EXPOSE_AUX_VIRTIO" >&2
  exit 64
fi

if [[ "$EXPOSE_ISC_VIRTIO" != "YES" && "$EXPOSE_ISC_VIRTIO" != "NO" ]]; then
  echo "macvm: MACVM_EXPOSE_ISC_VIRTIO must be YES or NO, got: $EXPOSE_ISC_VIRTIO" >&2
  exit 64
fi

if [[ "$EXPOSE_UTIL_VIRTIO" != "YES" && "$EXPOSE_UTIL_VIRTIO" != "NO" ]]; then
  echo "macvm: MACVM_EXPOSE_UTIL_VIRTIO must be YES or NO, got: $EXPOSE_UTIL_VIRTIO" >&2
  exit 64
fi
if [[ "$EXPOSE_UTIL_VIRTIO" == "YES" && "$EXPOSE_ISC_VIRTIO" != "YES" ]]; then
  echo "macvm: AUX utility frontend currently requires the validated iSC topology" >&2
  exit 64
fi

if [[ "$EXPOSE_RECOVERY_VIRTIO" != "YES" && "$EXPOSE_RECOVERY_VIRTIO" != "NO" ]]; then
  echo "macvm: MACVM_EXPOSE_RECOVERY_VIRTIO must be YES or NO, got: $EXPOSE_RECOVERY_VIRTIO" >&2
  exit 64
fi

if [[ -n "$ROOT_IMAGE" ]]; then
  if [[ "$ROOT_IMAGE" != /* ]]; then
    echo "macvm: MACVM_ROOT_IMAGE must be an absolute path, got: $ROOT_IMAGE" >&2
    exit 64
  fi
  require_file "$ROOT_IMAGE"
elif [[ "$EXPOSE_ROOT_VIRTIO" == "YES" ]]; then
  echo "macvm: MACVM_EXPOSE_ROOT_VIRTIO=YES requires MACVM_ROOT_IMAGE" >&2
  exit 64
fi

if [[ -n "$ISC_IMAGE" ]]; then
  if [[ "$ISC_IMAGE" != /* ]]; then
    echo "macvm: MACVM_ISC_IMAGE must be an absolute path, got: $ISC_IMAGE" >&2
    exit 64
  fi
  require_file "$ISC_IMAGE"
  require_file "$ISC_VALIDATOR"
  if ! "$PYTHON_BIN" "$ISC_VALIDATOR" inspect "$ISC_IMAGE" >/dev/null; then
    echo "macvm: MACVM_ISC_IMAGE failed structural validation: $ISC_IMAGE" >&2
    exit 64
  fi
  if [[ "$EXPOSE_UTIL_VIRTIO" == "YES" ]]; then
    PYTHONPATH="$REPO_ROOT/tools" "$PYTHON_BIN" -c \
      'import sys; from pathlib import Path; from build_vmapple_isc import inspect_isc_image; from vmapple_util_layout import validate_isc_report; validate_isc_report(inspect_isc_image(Path(sys.argv[1])))' \
      "$ISC_IMAGE"
  fi
elif [[ "$EXPOSE_ISC_VIRTIO" == "YES" ]]; then
  echo "macvm: MACVM_EXPOSE_ISC_VIRTIO=YES requires MACVM_ISC_IMAGE" >&2
  exit 64
fi

if [[ "$EXPOSE_RECOVERY_VIRTIO" == "YES" ]]; then
  if [[ -z "$RECOVERY_IMAGE" || -z "$RECOVERY_VOLUME_UUID" ]]; then
    echo "macvm: MACVM_EXPOSE_RECOVERY_VIRTIO=YES requires MACVM_RECOVERY_IMAGE and MACVM_RECOVERY_VOLUME_UUID" >&2
    exit 64
  fi
  if [[ "$RECOVERY_IMAGE" != /* ]]; then
    echo "macvm: MACVM_RECOVERY_IMAGE must be an absolute path, got: $RECOVERY_IMAGE" >&2
    exit 64
  fi
  require_file "$RECOVERY_IMAGE"
  require_file "$RECOVERY_VALIDATOR"
  if ! "$PYTHON_BIN" "$RECOVERY_VALIDATOR" inspect "$RECOVERY_IMAGE" \
    --expected-volume-uuid "$RECOVERY_VOLUME_UUID" >/dev/null
  then
    echo "macvm: MACVM_RECOVERY_IMAGE failed structural or UUID validation: $RECOVERY_IMAGE" >&2
    exit 64
  fi
  export MACVM_RECOVERY_VOLUME_UUID="$RECOVERY_VOLUME_UUID"
  require_executable "$QEMU_IMG_BIN"
elif [[ -n "$RECOVERY_IMAGE" || -n "$RECOVERY_VOLUME_UUID" ]]; then
  echo "macvm: Recovery image settings require MACVM_EXPOSE_RECOVERY_VIRTIO=YES" >&2
  exit 64
fi

if [[ -n "$RAMDISK_OVERRIDE_IMAGE" || -n "$RAMDISK_OVERRIDE_ADDRESS" ]]; then
  if [[ -z "$RAMDISK_OVERRIDE_IMAGE" || -z "$RAMDISK_OVERRIDE_ADDRESS" ]]; then
    echo "macvm: RAMDisk override image and address must be provided together" >&2
    exit 64
  fi
  require_file "$RAMDISK_OVERRIDE_VALIDATOR"
  if ! "$PYTHON_BIN" "$RAMDISK_OVERRIDE_VALIDATOR" \
    --image "$RAMDISK_OVERRIDE_IMAGE" \
    --address "$RAMDISK_OVERRIDE_ADDRESS" \
    --memory-gib "$MEMORY_GIB" \
    --allowed-root "$RESTORE_DIR" >/dev/null
  then
    exit 64
  fi
fi

if [[ -n "$RESTORE_TRUSTCACHE_IMAGE" || -n "$BASESYSTEM_TRUSTCACHE_IMAGE" || -n "$TRUSTCACHE_OVERRIDE_ADDRESS" ]]; then
  if [[ -z "$RESTORE_TRUSTCACHE_IMAGE" || -z "$BASESYSTEM_TRUSTCACHE_IMAGE" || -z "$TRUSTCACHE_OVERRIDE_ADDRESS" ]]; then
    echo "macvm: Restore, BaseSystem, and address TrustCache overrides must be provided together" >&2
    exit 64
  fi
  require_file "$TRUSTCACHE_REGION_TOOL"
  require_file "$RESTORE_TRUSTCACHE_IMAGE"
  require_file "$BASESYSTEM_TRUSTCACHE_IMAGE"
  require_u64_literal "MACVM_TRUSTCACHE_OVERRIDE_ADDRESS" "$TRUSTCACHE_OVERRIDE_ADDRESS"
fi

if [[ -n "$QEMU_LOG_ITEMS" && ! "$QEMU_LOG_ITEMS" =~ ^[a-z0-9_,]+$ ]]; then
  echo "macvm: MACVM_QEMU_LOG_ITEMS contains unsupported characters: $QEMU_LOG_ITEMS" >&2
  exit 64
fi

validate_basesystem_post_trace_coupling

if [[ -z "$QEMU_DISPLAY" || ! "$QEMU_DISPLAY" =~ ^[A-Za-z0-9_=,.:/+%-]+$ ]]; then
  echo "macvm: MACVM_QEMU_DISPLAY must be a single QEMU display backend token, got: $QEMU_DISPLAY" >&2
  exit 64
fi

if [[ "$RUN_ROOT" != /* ]]; then
  echo "macvm: MACVM_RUN_ROOT must be an absolute path, got: $RUN_ROOT" >&2
  exit 64
fi

AVPBOOTER="$RESTORE_DIR/AVPBooter.vmapple2.bin"
require_file "$AVPBOOTER"
require_file "$RESTORE_DIR/restore-chain/iBSS.fixed-rnd-713471fb.img4"
require_file "$RESTORE_DIR/local-policy-fixed-rnd-713471fb-bnch32/Ap.LocalPolicy.fixed-rnd-713471fb-bnch32.img4"
require_file "$RESTORE_DIR/restore-chain/iBEC.fixed-rnd-713471fb.img4"
require_file "$RESTORE_DIR/restore-chain/iBEC.runtime-last.bin"
require_file "$RESTORE_DIR/restore-chain/iBEC.descriptor-table.bin"
require_file "$TRACE_SCRIPT"
if [[ -n "$POST_TRACE_SCRIPT" ]]; then
  require_file "$POST_TRACE_SCRIPT"
fi
if [[ -n "$FINAL_TRACE_SCRIPT" ]]; then
  require_file "$FINAL_TRACE_SCRIPT"
fi
require_file "$SESSION_TOOL"
require_executable "$QEMU_BIN"
require_executable "$GDB_BIN"

mkdir -p "$RUN_ROOT"
RUN_DIR="$RUN_ROOT/$RUN_NAME"
if [[ -e "$RUN_DIR" ]]; then
  echo "macvm: run directory already exists: $RUN_DIR" >&2
  exit 73
fi
mkdir -p "$RUN_DIR"

TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script "$TRACE_SCRIPT" "gdb-trace.gdb")"
POST_TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script "$POST_TRACE_SCRIPT" "post-gdb-trace.gdb")"
FINAL_TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script "$FINAL_TRACE_SCRIPT" "final-gdb-trace.gdb")"

if [[ -n "$SESSION_STEPS_FILE" ]]; then
  printf '%s\n' "$SESSION_STEPS_FILE" >"$RUN_DIR/session-steps.path"
  cp -- "$SESSION_STEPS_FILE" "$RUN_DIR/session-steps.input"
fi

if [[ -z "${REIMS_VGPU_FAIL_LOG:-}" ]]; then
  export REIMS_VGPU_FAIL_LOG="$RUN_DIR/reims-vgpu-fail.log"
fi
printf '%s\n' "$REIMS_VGPU_FAIL_LOG" >"$RUN_DIR/reims-vgpu-fail.path"

USBRESTORE_SOCK="$RUN_DIR/usbrestore.sock"
SOCKET_TMP_DIR=""
if (( ${#USBRESTORE_SOCK} > UNIX_SOCKET_PATH_MAX )); then
  SOCKET_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/macvm-usbrestore.XXXXXX")"
  USBRESTORE_SOCK="$SOCKET_TMP_DIR/u.sock"
  printf '%s\n' "$USBRESTORE_SOCK" >"$RUN_DIR/usbrestore-socket.path"
fi

QMP_SOCK="$RUN_DIR/qmp.sock"
QMP_SOCKET_TMP_DIR=""
if (( ${#QMP_SOCK} > UNIX_SOCKET_PATH_MAX )); then
  QMP_SOCKET_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/macvm-qmp.XXXXXX")"
  QMP_SOCK="$QMP_SOCKET_TMP_DIR/q.sock"
  printf '%s\n' "$QMP_SOCK" >"$RUN_DIR/qmp-socket.path"
fi

TRACE_EVENTS="$RUN_DIR/trace-events"
if [[ -n "${MACVM_TRACE_EVENTS:-}" ]]; then
  printf '%s\n' "$MACVM_TRACE_EVENTS" >"$TRACE_EVENTS"
elif [[ "$TRACE_VERBOSE" == "YES" ]]; then
  cat >"$TRACE_EVENTS" <<'TRACE_EVENTS_VERBOSE_EOF'
bdif_read
bdif_write
bdif_access
bdif_vblk_cmd
bdif_vblk_desc
bdif_vblk_sector
bdif_vblk_read
bdif_vblk_error
bdif_usb_restore_packet
TRACE_EVENTS_VERBOSE_EOF
else
  cat >"$TRACE_EVENTS" <<'TRACE_EVENTS_MINIMAL_EOF'
bdif_vblk_error
bdif_usb_restore_packet
TRACE_EVENTS_MINIMAL_EOF
fi

truncate -s 64M "$RUN_DIR/root.img"
truncate -s 64M "$RUN_DIR/usb.img"

if [[ -n "$ROOT_IMAGE" ]]; then
  ROOT_DRIVE="$ROOT_IMAGE"
  printf '%s\n' "$ROOT_DRIVE" >"$RUN_DIR/root-image.path"
else
  ROOT_DRIVE="$RUN_DIR/root.img"
fi

ISC_DRIVE=""
if [[ -n "$ISC_IMAGE" ]]; then
  # iBoot's pflash AUX writes and XNU's iSC disk I/O must land in one coherent
  # storage object.  The validated template remains immutable: both QEMU front
  # ends receive only this run-scoped writable copy.
  ISC_DRIVE="$RUN_DIR/aux.img"
  cp --reflink=auto --sparse=always -- "$ISC_IMAGE" "$ISC_DRIVE"
  chmod u+rw "$ISC_DRIVE"
  printf '%s\n' "$ISC_IMAGE" >"$RUN_DIR/isc-template.path"
  printf '%s\n' "$ISC_DRIVE" >"$RUN_DIR/isc-image.path"
else
  truncate -s 64M "$RUN_DIR/aux.img"
fi

AUX_PFLASH_DRIVE="if=pflash,index=0,format=raw,file=$RUN_DIR/aux.img"
if [[ "$EXPOSE_ISC_VIRTIO" == "YES" ]]; then
  # QEMU opens the same run-scoped file through two block backends.  Disable
  # only the intra-process file locks required for that topology; share-rw on
  # the virtio device below makes the intentional sharing explicit.
  AUX_PFLASH_DRIVE+=",file.locking=off"
fi

if [[ -n "$RAMDISK_OVERRIDE_IMAGE" ]]; then
  printf '%s\n' "$RAMDISK_OVERRIDE_IMAGE" >"$RUN_DIR/ramdisk-override.path"
  printf '%s\n' "$RAMDISK_OVERRIDE_ADDRESS" >"$RUN_DIR/ramdisk-override.address"
fi

RECOVERY_DRIVE=""
if [[ "$EXPOSE_RECOVERY_VIRTIO" == "YES" ]]; then
  # prebootensurer performs a read-write APFS mount while repairing Preboot.
  # Keep the validated Recovery template immutable and expose only this
  # run-scoped copy-on-write layer as a writable virtio block device.
  RECOVERY_DRIVE="$RUN_DIR/recovery-overlay.qcow2"
  "$QEMU_IMG_BIN" create -q -f qcow2 -F raw \
    -b "$RECOVERY_IMAGE" "$RECOVERY_DRIVE"
  chmod u+rw "$RECOVERY_DRIVE"
  "$QEMU_IMG_BIN" info --output=json "$RECOVERY_DRIVE" \
    >"$RUN_DIR/recovery-overlay.info.json"
  printf '%s\n' "$RECOVERY_IMAGE" >"$RUN_DIR/recovery-template.path"
  printf '%s\n' "$RECOVERY_DRIVE" >"$RUN_DIR/recovery-image.path"
  printf '%s\n' "$RECOVERY_VOLUME_UUID" >"$RUN_DIR/recovery-volume-uuid"
fi

TRUSTCACHE_REGION_IMAGE=""
if [[ -n "$RESTORE_TRUSTCACHE_IMAGE" ]]; then
  # Build a run-scoped XNU offset table from Apple's unmodified rtsc and bstc
  # IM4P payloads.  The tool validates both module versions and entry counts,
  # refuses overwrite, page-pads the region, and bounds it to guest RAM.
  TRUSTCACHE_REGION_IMAGE="$RUN_DIR/trustcache-region.raw"
  "$PYTHON_BIN" "$TRUSTCACHE_REGION_TOOL" build \
    --restore "$RESTORE_TRUSTCACHE_IMAGE" \
    --basesystem "$BASESYSTEM_TRUSTCACHE_IMAGE" \
    --allowed-root "$RESTORE_DIR" \
    --output "$TRUSTCACHE_REGION_IMAGE" \
    --address "$TRUSTCACHE_OVERRIDE_ADDRESS" \
    --memory-gib "$MEMORY_GIB" \
    >"$RUN_DIR/trustcache-region.build"
  printf '%s\n' "$RESTORE_TRUSTCACHE_IMAGE" >"$RUN_DIR/restore-trustcache.path"
  printf '%s\n' "$BASESYSTEM_TRUSTCACHE_IMAGE" >"$RUN_DIR/basesystem-trustcache.path"
  printf '%s\n' "$TRUSTCACHE_OVERRIDE_ADDRESS" >"$RUN_DIR/trustcache-override.address"
  export MACVM_TRUSTCACHE_OVERRIDE_IMAGE="$TRUSTCACHE_REGION_IMAGE"
  export MACVM_TRUSTCACHE_OVERRIDE_ADDRESS="$TRUSTCACHE_OVERRIDE_ADDRESS"
fi

QEMU_PID=""
GDB_PID=""
POST_GDB_PID=""
HELPER_PID=""
cleanup() {
  stop_process "$HELPER_PID"
  stop_process "$POST_GDB_PID"
  stop_process "$GDB_PID"
  stop_process "$QEMU_PID"
  if [[ -n "$SOCKET_TMP_DIR" ]]; then
    rm -f "$USBRESTORE_SOCK"
    rmdir "$SOCKET_TMP_DIR" 2>/dev/null || true
  fi
  if [[ -n "$QMP_SOCKET_TMP_DIR" ]]; then
    rm -f "$QMP_SOCK"
    rmdir "$QMP_SOCKET_TMP_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

qemu_args=(
  -machine "vmapple,uuid=$ECID,rnd=0x713471fb,svc-a0-psci=on,iboot-low-scratch=on"
  -accel "tcg,thread=multi"
  -cpu max
  -smp "$VCPUS"
  -m "${MEMORY_GIB}G"
  -S
  -gdb "tcp:127.0.0.1:$GDB_PORT"
  -bios "$AVPBOOTER"
  -drive "$AUX_PFLASH_DRIVE"
  -drive "if=pflash,index=1,format=raw,file=$RUN_DIR/root.img"
  -drive "if=pflash,index=2,format=raw,file=$RUN_DIR/usb.img"
  -display "$QEMU_DISPLAY"
  -serial "file:$RUN_DIR/serial.log"
  -monitor none
  -qmp "unix:$QMP_SOCK,server=on,wait=off"
  -chardev "socket,id=usbrestore,path=$USBRESTORE_SOCK,server=on,wait=off"
  -global "vmapple-bdif.usb-restore-chardev=usbrestore"
  -global "vmapple-bdif.block-writes=on"
  -trace "events=$TRACE_EVENTS,file=$RUN_DIR/trace.log"
)

if [[ -n "$VMAPPLE_CFG_SERIAL" || -n "$VMAPPLE_CFG_MODEL" || -n "$VMAPPLE_CFG_SOC_NAME" ]]; then
  {
    printf 'serial=%s\n' "$VMAPPLE_CFG_SERIAL"
    printf 'model=%s\n' "$VMAPPLE_CFG_MODEL"
    printf 'soc_name=%s\n' "$VMAPPLE_CFG_SOC_NAME"
  } >"$RUN_DIR/vmapple-cfg-overrides.env"
fi

if [[ -n "$VMAPPLE_CFG_SERIAL" ]]; then
  qemu_args+=(-global "vmapple-cfg.serial=$VMAPPLE_CFG_SERIAL")
fi

if [[ -n "$VMAPPLE_CFG_MODEL" ]]; then
  qemu_args+=(-global "vmapple-cfg.model=$VMAPPLE_CFG_MODEL")
fi

if [[ -n "$VMAPPLE_CFG_SOC_NAME" ]]; then
  qemu_args+=(-global "vmapple-cfg.soc_name=$VMAPPLE_CFG_SOC_NAME")
fi

if [[ -n "$RAMDISK_OVERRIDE_IMAGE" ]]; then
  # Load an isolated, run-specific APFS ramdisk into guest RAM.  The final
  # iBEC handoff script reserves this exact range and redirects /chosen's
  # RAMDisk mapping only after Apple has validated every signed restore asset.
  qemu_args+=(
    -device "loader,file=$RAMDISK_OVERRIDE_IMAGE,addr=$RAMDISK_OVERRIDE_ADDRESS,force-raw=on"
  )
fi

if [[ "$EXPOSE_ROOT_VIRTIO" == "YES" ]]; then
  # The restore chain uploads its boot objects through iBEC, so BDIF keeps its
  # run-scoped scratch root while XNU receives the staged BaseSystem through
  # the matching Apple virtio block function.  The source remains read-only.
  qemu_args+=(
    -drive "if=none,id=macvm-root-virtio,format=raw,file=$ROOT_DRIVE,readonly=on"
    -device "vmapple-virtio-blk-pci,variant=root,drive=macvm-root-virtio"
  )
fi

if [[ "$EXPOSE_RECOVERY_VIRTIO" == "YES" ]]; then
  # prebootensurer resolves /chosen/boot-uuid only against an IOKit-published
  # AppleAPFSVolume with role Recovery (0x4), and separately recognizes the
  # parent IOMedia Content UUID 52637672-7900-11AA-AA11-00306543ECAC.
  # prebootensurer then mounts it read-write to repair Preboot, so QEMU must
  # expose the run-scoped overlay without VIRTIO_BLK_F_RO.  The validated raw
  # template remains an immutable backing file.
  qemu_args+=(
    -drive "if=none,id=macvm-recovery-virtio,format=qcow2,file=$RECOVERY_DRIVE"
    -device "vmapple-virtio-blk-pci,variant=root,drive=macvm-recovery-virtio"
  )
fi

if [[ "$EXPOSE_ISC_VIRTIO" == "YES" ]]; then
  # macOS 26's AppleVirtIOStorageDevice::createBlockStorageDevice maps device
  # role 1 (root) to AppleVirtIODiskStorageDevice, but role 2 (aux) to
  # AppleVirtIOUtilStorageDevice.  apfs_boot_util requires an AppleAPFSVolume
  # published through the disk/IOMedia stack, so an iSC image must use root
  # even though this run-scoped file also backs the firmware AUX pflash.
  qemu_args+=(
    -drive "if=none,id=macvm-isc-virtio,format=raw,file=$ISC_DRIVE,file.locking=off"
    -device "vmapple-virtio-blk-pci,variant=root,drive=macvm-isc-virtio,share-rw=on"
  )
fi

if [[ "$EXPOSE_UTIL_VIRTIO" == "YES" ]]; then
  # A distinct AUX role is required for AppleVirtIOUtilStorageDevice to
  # publish AppleNVMeEAN. The root-role iSC disk above remains unchanged.
  # Firmware utility regions occupy [0,32 MiB); iSC starts at 32 MiB.
  # Only the existing run-scoped AUX copy is writable through this frontend.
  qemu_args+=(
    -drive "if=none,id=macvm-util-virtio,format=raw,file=$RUN_DIR/aux.img,file.locking=off"
    -device "vmapple-virtio-blk-pci,variant=aux,drive=macvm-util-virtio,share-rw=on"
  )
fi

if [[ -n "$QEMU_LOG_ITEMS" ]]; then
  qemu_args+=(
    -d "$QEMU_LOG_ITEMS"
    -D "$RUN_DIR/qemu-debug.log"
  )
fi

if [[ "$PAUSE_ON_REBOOT" == "YES" ]]; then
  # Preserve the requesting vCPU and guest memory before QEMU performs the
  # reset.  This is a debug-only run action; the default remains a real reset.
  qemu_args+=(
    -action "reboot=shutdown,shutdown=pause"
  )
fi

printf '%q ' "$QEMU_BIN" "${qemu_args[@]}" >"$RUN_DIR/qemu.command"
printf '\n' >>"$RUN_DIR/qemu.command"

timeout "$QEMU_TIMEOUT" "$QEMU_BIN" "${qemu_args[@]}" \
  >"$RUN_DIR/qemu.stdout" 2>"$RUN_DIR/qemu.stderr" &
QEMU_PID=$!

wait_for_socket "$USBRESTORE_SOCK"

if [[ -n "$POST_TRACE_SCRIPT" ]]; then
  timeout "$GDB_TIMEOUT" "$GDB_BIN" -q -batch -x "$TRACE_SCRIPT_RUN" \
    >"$RUN_DIR/gdb.log" 2>&1 &
  GDB_PID=$!

  collect_status "GDB_RC" "$GDB_PID" "$RUN_DIR/gdb.status"
  GDB_PID=""

  gdb_rc="$(sed -n 's/^GDB_RC=//p' "$RUN_DIR/gdb.status")"
  if [[ "$gdb_rc" != "0" ]]; then
    echo "macvm: bootstrap GDB failed with exit code $gdb_rc" >&2
    echo "macvm: evidence retained at $RUN_DIR" >&2
    exit 70
  fi

  wait_for_log_pattern "$RUN_DIR/serial.log" "$STAGE2_PROMPT" "$STAGE2_PROMPT_TIMEOUT_SECONDS"

  timeout "$POST_GDB_TIMEOUT" "$GDB_BIN" -q -batch -x "$POST_TRACE_SCRIPT_RUN" \
    >"$RUN_DIR/post-gdb.log" 2>&1 &
  POST_GDB_PID=$!

  sleep "$POST_GDB_ATTACH_GRACE_SECONDS"

  if ! kill -0 "$POST_GDB_PID" >/dev/null 2>&1; then
    collect_status "POST_GDB_RC" "$POST_GDB_PID" "$RUN_DIR/post-gdb.status"
    echo "macvm: post-boot command GDB exited before restore helper started" >&2
    echo "macvm: evidence retained at $RUN_DIR" >&2
    exit 70
  fi

  "$PYTHON_BIN" "$SESSION_TOOL" \
    --socket "$USBRESTORE_SOCK" \
    --connect-timeout "$SESSION_CONNECT_TIMEOUT" \
    --recv-timeout "$SESSION_RECV_TIMEOUT" \
    --jsonl "$RUN_DIR/session.jsonl" \
    "${session_step_args[@]}" \
    >"$RUN_DIR/helper.stdout" 2>"$RUN_DIR/helper.stderr" &
  HELPER_PID=$!

  collect_status "HELPER_RC" "$HELPER_PID" "$RUN_DIR/helper.status"
  wait_for_post_gdb_milestone_if_needed
  stop_process "$POST_GDB_PID"
  collect_post_gdb_status_if_needed
  validate_restore_session_evidence
  finish_qemu_after_helper
else
  "$PYTHON_BIN" "$SESSION_TOOL" \
    --socket "$USBRESTORE_SOCK" \
    --connect-timeout "$SESSION_CONNECT_TIMEOUT" \
    --recv-timeout "$SESSION_RECV_TIMEOUT" \
    --jsonl "$RUN_DIR/session.jsonl" \
    "${session_step_args[@]}" \
    >"$RUN_DIR/helper.stdout" 2>"$RUN_DIR/helper.stderr" &
  HELPER_PID=$!

  timeout "$GDB_TIMEOUT" "$GDB_BIN" -q -batch -x "$TRACE_SCRIPT_RUN" \
    >"$RUN_DIR/gdb.log" 2>&1 &
  GDB_PID=$!

  collect_status "HELPER_RC" "$HELPER_PID" "$RUN_DIR/helper.status"
  sleep "$POST_HELPER_GRACE_SECONDS"
  stop_process "$GDB_PID"
  collect_status "GDB_RC" "$GDB_PID" "$RUN_DIR/gdb.status"
  GDB_PID=""
  validate_restore_session_evidence
  finish_qemu_after_helper
fi

helper_rc="$(sed -n 's/^HELPER_RC=//p' "$RUN_DIR/helper.status")"
if [[ "$helper_rc" != "0" ]]; then
  echo "macvm: restore socket helper failed with exit code $helper_rc" >&2
  echo "macvm: evidence retained at $RUN_DIR" >&2
  exit 70
fi

if ! grep -Fq '"event": "recv-match"' "$RUN_DIR/session.jsonl"; then
  echo "macvm: restore socket did not receive the expected 0402 response" >&2
  echo "macvm: evidence retained at $RUN_DIR" >&2
  exit 70
fi

if ! grep -Fq "$STAGE2_PROMPT" "$RUN_DIR/serial.log"; then
  echo "macvm: iBEC did not reach the Stage2 recovery prompt" >&2
  echo "macvm: evidence retained at $RUN_DIR" >&2
  exit 70
fi

if ! grep -Fq "bdif_usb_restore_packet action=chardev-in" "$RUN_DIR/trace.log" ||
   ! grep -Fq "bdif_usb_restore_packet action=chardev-out" "$RUN_DIR/trace.log"; then
  echo "macvm: QEMU did not trace both restore chardev directions" >&2
  echo "macvm: evidence retained at $RUN_DIR" >&2
  exit 70
fi

echo "macvm: iBEC USB restore smoke passed"
echo "macvm: evidence retained at $RUN_DIR"
