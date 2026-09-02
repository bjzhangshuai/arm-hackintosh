from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run-ibec-usb-restore-smoke.sh"
RESTORE_STEPS = ROOT / "configs" / "macos-26.6-restore.steps"


class IBecUsbRestoreSmokeRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_runner_is_guarded_and_guest_only(self) -> None:
        self.assertIn('source "$SCRIPT_DIR/lib/require-debug-env.sh"', self.text)
        self.assertIn("macvm_require_debug_env", self.text)
        self.assertNotIn("sudo", self.text)
        self.assertNotIn("systemctl", self.text)
        self.assertNotIn("apt ", self.text)
        self.assertNotIn("ninja install", self.text)

    def test_qemu_crash_timeout_and_missing_status_cannot_be_reported_as_pass(self) -> None:
        match = re.search(r"^validate_qemu_exit_status\(\) \{\n.*?^\}", self.text, re.M | re.S)
        self.assertIsNotNone(match)
        function = match.group(0)
        with tempfile.TemporaryDirectory() as directory:
            status = Path(directory) / "qemu.status"
            for keep in ("YES", "NO"):
                for rc in ("0", "1", "124", "125", "126", "127", "134", "137", "139", "143", "", "garbage", "0\nQEMU_RC=139"):
                    with self.subTest(keep=keep, rc=rc):
                        status.write_text(f"QEMU_RC={rc}\n")
                        result = subprocess.run(
                            ["bash", "-c", function + '\nRUN_DIR="$1"\nKEEP_QEMU_RUNNING_AFTER_HELPER="$2"\nvalidate_qemu_exit_status', "probe", directory, keep],
                            capture_output=True, text=True, check=False,
                        )
                        expected = 0 if rc == "0" or (keep == "NO" and rc == "143") else 70
                        self.assertEqual(result.returncode, expected, result.stderr)
                        if expected:
                            self.assertIn("does not imply boot success", result.stderr)
            status.unlink()
            result = subprocess.run(
                ["bash", "-c", function + '\nRUN_DIR="$1"\nKEEP_QEMU_RUNNING_AFTER_HELPER=YES\nvalidate_qemu_exit_status', "probe", directory],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 70)

    def test_runner_uses_new_run_directory_without_deleting_existing_state(self) -> None:
        self.assertIn('RUN_ROOT="${MACVM_RUN_ROOT:-/home/macvm/runs/aux-26.6}"', self.text)
        self.assertIn('RUN_NAME="${MACVM_RUN_NAME:-ibec-usb-restore-smoke-$(date +%Y%m%d-%H%M%S)}"', self.text)
        self.assertIn('if [[ -e "$RUN_DIR" ]]; then', self.text)
        self.assertIn('truncate -s 64M "$RUN_DIR/aux.img"', self.text)
        self.assertIn('truncate -s 64M "$RUN_DIR/root.img"', self.text)
        self.assertIn('truncate -s 64M "$RUN_DIR/usb.img"', self.text)
        self.assertIn('USBRESTORE_SOCK="$RUN_DIR/usbrestore.sock"', self.text)
        self.assertIn('SOCKET_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/macvm-usbrestore.XXXXXX")"', self.text)
        self.assertIn('printf \'%s\\n\' "$USBRESTORE_SOCK" >"$RUN_DIR/usbrestore-socket.path"', self.text)
        self.assertIn('QMP_SOCK="$RUN_DIR/qmp.sock"', self.text)
        self.assertIn('QMP_SOCKET_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/macvm-qmp.XXXXXX")"', self.text)
        self.assertIn('printf \'%s\\n\' "$QMP_SOCK" >"$RUN_DIR/qmp-socket.path"', self.text)
        self.assertNotIn("rm -rf", self.text)
        self.assertNotIn("--delete", self.text)

    def test_runner_enforces_validation_vm_resource_caps(self) -> None:
        self.assertIn('VCPUS="${MACVM_SMOKE_VCPUS:-4}"', self.text)
        self.assertIn('MEMORY_GIB="${MACVM_SMOKE_MEMORY_GIB:-4}"', self.text)
        self.assertIn('require_uint_range "MACVM_SMOKE_VCPUS" "$VCPUS" 1 16', self.text)
        self.assertIn('require_uint_range "MACVM_SMOKE_MEMORY_GIB" "$MEMORY_GIB" 1 36', self.text)
        self.assertIn('-smp "$VCPUS"', self.text)
        self.assertIn('-m "${MEMORY_GIB}G"', self.text)

    def test_runner_sets_ecid_to_match_personalized_restore_assets(self) -> None:
        self.assertIn('ECID="${MACVM_SMOKE_ECID:-0x1122334455667788}"', self.text)
        self.assertIn('require_u64_literal "MACVM_SMOKE_ECID" "$ECID"', self.text)
        self.assertIn("require_u64_literal() {", self.text)
        self.assertIn("0xFFFFFFFFFFFFFFFF", self.text)
        self.assertIn("vmapple,uuid=$ECID,rnd=0x713471fb", self.text)

    def test_runner_can_override_vmapple_cfg_identity_without_open_qemu_args(self) -> None:
        for variable in (
            "MACVM_VMAPPLE_CFG_SERIAL",
            "MACVM_VMAPPLE_CFG_MODEL",
            "MACVM_VMAPPLE_CFG_SOC_NAME",
        ):
            with self.subTest(variable=variable):
                self.assertIn(variable, self.text)
        self.assertIn(
            'require_vmapple_cfg_string "MACVM_VMAPPLE_CFG_SERIAL" "$VMAPPLE_CFG_SERIAL"',
            self.text,
        )
        self.assertIn(
            'require_vmapple_cfg_string "MACVM_VMAPPLE_CFG_MODEL" "$VMAPPLE_CFG_MODEL"',
            self.text,
        )
        self.assertIn(
            'require_vmapple_cfg_string "MACVM_VMAPPLE_CFG_SOC_NAME" "$VMAPPLE_CFG_SOC_NAME"',
            self.text,
        )
        self.assertIn("must fit in the vmapple-cfg 31-byte string field", self.text)
        self.assertIn("must be a single-line vmapple-cfg string", self.text)
        self.assertIn('>"$RUN_DIR/vmapple-cfg-overrides.env"', self.text)
        self.assertIn('-global "vmapple-cfg.serial=$VMAPPLE_CFG_SERIAL"', self.text)
        self.assertIn('-global "vmapple-cfg.model=$VMAPPLE_CFG_MODEL"', self.text)
        self.assertIn('-global "vmapple-cfg.soc_name=$VMAPPLE_CFG_SOC_NAME"', self.text)
        self.assertNotIn("MACVM_QEMU_EXTRA_ARGS", self.text)
        self.assertLess(
            self.text.index('require_vmapple_cfg_string "MACVM_VMAPPLE_CFG_MODEL"'),
            self.text.index('timeout "$QEMU_TIMEOUT" "$QEMU_BIN"'),
        )
        self.assertLess(
            self.text.index('>"$RUN_DIR/vmapple-cfg-overrides.env"'),
            self.text.index('printf \'%q \' "$QEMU_BIN"'),
        )

    def test_runner_timeouts_cover_the_gdb_driven_restore_chain(self) -> None:
        self.assertIn('QEMU_TIMEOUT="${MACVM_QEMU_TIMEOUT:-210s}"', self.text)
        self.assertIn('GDB_TIMEOUT="${MACVM_GDB_TIMEOUT:-180s}"', self.text)
        self.assertIn(
            'STAGE2_PROMPT_TIMEOUT_SECONDS="${MACVM_STAGE2_PROMPT_TIMEOUT_SECONDS:-45}"',
            self.text,
        )
        self.assertIn(
            'POST_GDB_MILESTONE_TIMEOUT_SECONDS="${MACVM_POST_GDB_MILESTONE_TIMEOUT_SECONDS:-600}"',
            self.text,
        )
        self.assertIn(
            'require_uint_range "MACVM_STAGE2_PROMPT_TIMEOUT_SECONDS" "$STAGE2_PROMPT_TIMEOUT_SECONDS" 1 300',
            self.text,
        )
        self.assertIn(
            'require_uint_range "MACVM_POST_GDB_MILESTONE_TIMEOUT_SECONDS" "$POST_GDB_MILESTONE_TIMEOUT_SECONDS" 1 3600',
            self.text,
        )
        self.assertIn('SESSION_RECV_TIMEOUT="${MACVM_SESSION_RECV_TIMEOUT:-90}"', self.text)

    def test_runner_rewrites_gdb_trace_scripts_to_the_selected_port(self) -> None:
        self.assertIn('GDB_PORT="${MACVM_GDB_PORT:-12345}"', self.text)
        self.assertIn("prepare_gdb_trace_script() {", self.text)
        self.assertIn(
            'TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script "$TRACE_SCRIPT" "gdb-trace.gdb")"',
            self.text,
        )
        self.assertIn(
            'POST_TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script "$POST_TRACE_SCRIPT" "post-gdb-trace.gdb")"',
            self.text,
        )
        self.assertIn(
            'FINAL_TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script "$FINAL_TRACE_SCRIPT" "final-gdb-trace.gdb")"',
            self.text,
        )
        self.assertIn(r"target remote 127[.]0[.]0[.]1:[0-9]+", self.text)
        self.assertIn('f"target remote 127.0.0.1:{port}"', self.text)
        self.assertIn("import hashlib", self.text)
        self.assertIn('source_re = re.compile(r"^(?P<indent>\\s*)source\\s+(?P<path>\\S+)(?P<tail>.*)$")', self.text)
        self.assertIn("def copy_gdb_source(path: Path, out: Path) -> None:", self.text)
        self.assertIn("if not nested.is_absolute():", self.text)
        self.assertIn("nested = path.parent / nested", self.text)
        self.assertIn("copy_gdb_source(nested, nested_out)", self.text)
        self.assertIn('line = f"{match.group(\'indent\')}source {nested_out}{match.group(\'tail\')}"', self.text)
        self.assertIn('out.with_suffix(out.suffix + ".source")', self.text)
        self.assertIn('-x "$TRACE_SCRIPT_RUN"', self.text)
        self.assertIn('-x "$POST_TRACE_SCRIPT_RUN"', self.text)
        self.assertIn('-x "$FINAL_TRACE_SCRIPT_RUN"', self.text)
        self.assertLess(
            self.text.index('mkdir -p "$RUN_DIR"'),
            self.text.index('TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script'),
        )
        self.assertLess(
            self.text.index('TRACE_SCRIPT_RUN="$(prepare_gdb_trace_script'),
            self.text.index('timeout "$QEMU_TIMEOUT" "$QEMU_BIN"'),
        )

    def test_runner_uses_restore_chardev_and_known_good_handshake(self) -> None:
        self.assertIn("-chardev", self.text)
        self.assertIn("usbrestore.sock", self.text)
        self.assertIn("path=$USBRESTORE_SOCK", self.text)
        self.assertIn('wait_for_socket "$USBRESTORE_SOCK"', self.text)
        self.assertIn('--socket "$USBRESTORE_SOCK"', self.text)
        self.assertIn("-global", self.text)
        self.assertIn("vmapple-bdif.usb-restore-chardev=usbrestore", self.text)
        self.assertIn("vmapple-bdif.block-writes=on", self.text)
        self.assertIn("--step send:0202", self.text)
        self.assertIn("--step expect:0402", self.text)
        self.assertIn("${session_step_args[@]}", self.text)
        self.assertIn("bdif_usb_restore_packet", self.text)

    def test_runner_allows_newline_ordered_session_steps_for_experiments(self) -> None:
        self.assertIn('if [[ -n "${MACVM_SESSION_STEPS:-}" ]]; then', self.text)
        self.assertIn('done <<< "$MACVM_SESSION_STEPS"', self.text)
        self.assertIn('session_step_args+=(--step "$step")', self.text)
        self.assertIn("session_step_args=(", self.text)

    def test_runner_supports_a_file_for_the_complete_restore_sequence(self) -> None:
        self.assertIn('SESSION_STEPS_FILE="${MACVM_SESSION_STEPS_FILE:-}"', self.text)
        self.assertIn(
            "MACVM_SESSION_STEPS and MACVM_SESSION_STEPS_FILE are mutually exclusive",
            self.text,
        )
        self.assertIn('if [[ "$SESSION_STEPS_FILE" != /* ]]; then', self.text)
        self.assertIn("MACVM_SESSION_STEPS_FILE is not readable", self.text)
        self.assertIn('done < "$SESSION_STEPS_FILE"', self.text)
        self.assertIn('>"$RUN_DIR/session-steps.path"', self.text)
        self.assertIn('cp -- "$SESSION_STEPS_FILE" "$RUN_DIR/session-steps.input"', self.text)

    def test_macos_26_restore_steps_are_complete_and_ordered(self) -> None:
        steps = [
            line
            for line in RESTORE_STEPS.read_text(encoding="utf-8").splitlines()
            if line and not line.lstrip().startswith("#")
        ]
        self.assertEqual(
            steps,
            [
                "send:0202",
                "expect:0402",
                "recovery-open",
                "upload-file:/home/macvm/macos-restore/26.6/restore-chain/RestoreTrustCache.094-96989-085.localpolicy-ticket.img4",
                "command:firmware",
                "expect:0100",
                "upload-file:/home/macvm/macos-restore/26.6/restore-chain/RestoreRamDisk.094-96989-085.localpolicy-ticket.img4",
                "command:ramdisk",
                "expect:0100",
                "upload-file:/home/macvm/macos-restore/26.6/restore-chain/RestoreDeviceTree.vma2macosap.localpolicy-ticket.img4",
                "command:devicetree",
                "expect:0100",
                "upload-file:/home/macvm/macos-restore/26.6/restore-chain/RestoreKernelCache.release.vma2.localpolicy-ticket.img4",
                "command:bootx",
                "expect:0100",
            ],
        )

    def test_runner_preserves_evidence_for_root_cause_analysis(self) -> None:
        for name in (
            "qemu.command",
            "qemu.stdout",
            "qemu.stderr",
            "gdb.log",
            "post-gdb.log",
            "serial.log",
            "trace.log",
            "session.jsonl",
            "helper.status",
            "gdb.status",
            "post-gdb.status",
            "final-gdb.log",
            "final-gdb.status",
            "qemu.status",
            "usbrestore-socket.path",
            "reims-vgpu-fail.log",
            "reims-vgpu-fail.path",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.text)

    def test_runner_supports_opt_in_post_boot_command_gdb_trace(self) -> None:
        self.assertIn('POST_TRACE_SCRIPT="${MACVM_GDB_POST_TRACE_SCRIPT:-}"', self.text)
        self.assertIn(
            'BASESYSTEM_TRACE_SCRIPT="$REPO_ROOT/tools/inject_basesystem_auth_and_boot_args_trace_mount.gdb"',
            self.text,
        )
        self.assertIn(
            'SYMLINK_ONLY_TRACE_SCRIPT="$REPO_ROOT/tools/trace_basesystem_symlink_preflight_live.gdb"',
            self.text,
        )
        self.assertIn('if [[ -n "${MACVM_GDB_TRACE_SCRIPT:-}" ]]; then', self.text)
        self.assertIn('TRACE_SCRIPT="$MACVM_GDB_TRACE_SCRIPT"', self.text)
        self.assertIn('elif [[ -n "$POST_TRACE_SCRIPT" ]]; then', self.text)
        self.assertIn(
            'TRACE_SCRIPT="$REPO_ROOT/tools/trace_ibec_usb_restore_bootstrap_detach.gdb"',
            self.text,
        )
        self.assertIn(
            'TRACE_SCRIPT="$REPO_ROOT/tools/trace_ibec_usb_restore_light.gdb"',
            self.text,
        )
        self.assertIn("would deadlock the runner", self.text)
        self.assertIn('if [[ -n "$POST_TRACE_SCRIPT" ]]; then', self.text)
        self.assertIn('require_file "$POST_TRACE_SCRIPT"', self.text)
        self.assertIn('POST_GDB_TIMEOUT="${MACVM_POST_GDB_TIMEOUT:-$GDB_TIMEOUT}"', self.text)
        self.assertIn(
            'POST_GDB_ATTACH_GRACE_SECONDS="${MACVM_POST_GDB_ATTACH_GRACE_SECONDS:-1}"',
            self.text,
        )
        self.assertIn('-x "$TRACE_SCRIPT_RUN"', self.text)
        self.assertIn('-x "$POST_TRACE_SCRIPT_RUN"', self.text)
        self.assertIn('>"$RUN_DIR/post-gdb.log" 2>&1 &', self.text)
        self.assertIn('collect_status "POST_GDB_RC" "$POST_GDB_PID" "$RUN_DIR/post-gdb.status"', self.text)
        self.assertIn("post-boot command GDB exited before restore helper started", self.text)
        self.assertIn('wait_for_log_pattern "$RUN_DIR/serial.log" "$STAGE2_PROMPT"', self.text)
        self.assertIn('STAGE2_PROMPT="Entering iBootStage2 recovery mode, starting command prompt"', self.text)
        self.assertLess(self.text.index('collect_status "GDB_RC"'), self.text.index('>"$RUN_DIR/post-gdb.log"'))
        self.assertLess(self.text.index('>"$RUN_DIR/post-gdb.log"'), self.text.index('>"$RUN_DIR/helper.stdout"'))

    def test_runner_rejects_basesystem_overrides_without_injecting_trace(self) -> None:
        self.assertIn("validate_basesystem_post_trace_coupling() {", self.text)
        self.assertIn('requires_basesystem_injection="YES"', self.text)
        self.assertIn('BaseSystem RAMDisk/TrustCache overrides require an injecting post-GDB trace', self.text)
        self.assertIn('BaseSystem RAMDisk/TrustCache overrides cannot use the symlink-only post-GDB trace', self.text)
        self.assertIn(
            "symlink-only tracing does not inject rd=md0, BaseSystem auth, or TrustCache handoff state",
            self.text,
        )
        self.assertIn('set MACVM_GDB_POST_TRACE_SCRIPT=$BASESYSTEM_TRACE_SCRIPT', self.text)
        self.assertIn('MACVM_BASESYSTEM_AUTH_BLOB is required by the BaseSystem injecting post-GDB trace', self.text)
        self.assertLess(
            self.text.index("validate_basesystem_post_trace_coupling"),
            self.text.index('if [[ -z "$QEMU_DISPLAY"'),
        )

    def test_runner_supports_read_only_final_natural_run_snapshot(self) -> None:
        self.assertIn('FINAL_TRACE_SCRIPT="${MACVM_GDB_FINAL_TRACE_SCRIPT:-}"', self.text)
        self.assertIn('FINAL_GDB_TIMEOUT="${MACVM_FINAL_GDB_TIMEOUT:-30s}"', self.text)
        self.assertIn('if [[ -n "$FINAL_TRACE_SCRIPT" ]]; then', self.text)
        self.assertIn('require_file "$FINAL_TRACE_SCRIPT"', self.text)
        self.assertIn("run_final_gdb_trace() {", self.text)
        self.assertIn('-x "$FINAL_TRACE_SCRIPT_RUN"', self.text)
        self.assertIn('>"$RUN_DIR/final-gdb.log" 2>&1', self.text)
        self.assertIn("FINAL_GDB_RC=%s", self.text)
        self.assertIn("finish_qemu_after_helper() {", self.text)
        self.assertIn('run_final_gdb_trace\n  stop_process "$QEMU_PID"', self.text)

    def test_runner_can_keep_qemu_running_after_successful_restore_helper(self) -> None:
        self.assertIn(
            'KEEP_QEMU_RUNNING_AFTER_HELPER="${MACVM_KEEP_QEMU_RUNNING_AFTER_HELPER:-NO}"',
            self.text,
        )
        self.assertIn(
            'MACVM_KEEP_QEMU_RUNNING_AFTER_HELPER must be YES or NO',
            self.text,
        )
        self.assertIn("validate_restore_session_evidence() {", self.text)
        self.assertIn('helper_rc="$(sed -n \'s/^HELPER_RC=//p\' "$RUN_DIR/helper.status")"', self.text)
        self.assertIn("restore socket did not receive the expected 0402 response", self.text)
        self.assertIn("QEMU did not trace both restore chardev directions", self.text)
        self.assertIn("required_post_gdb_milestone() {", self.text)
        self.assertIn("wait_for_post_gdb_milestone_if_needed() {", self.text)
        self.assertIn("MACVM_IMGSRC_STATE_APPLIED", self.text)
        self.assertIn("MACVM_SYMLINK_DETACH_AFTER_PACKAGESLINK", self.text)
        self.assertIn("Cannot execute this command while the target is running", self.text)
        self.assertIn("post-GDB hit a fatal BaseSystem trace failure", self.text)
        self.assertIn("post-GDB exited before required milestone", self.text)
        self.assertIn("timed out waiting for required post-GDB milestone", self.text)
        self.assertIn("collect_post_gdb_status_if_needed() {", self.text)
        self.assertIn("resume_qemu_if_debug_paused() {", self.text)
        self.assertIn('>"$RUN_DIR/qmp-resume.log" 2>&1', self.text)
        self.assertIn('"execute": "query-status"', self.text)
        self.assertIn('"execute": "cont"', self.text)
        self.assertIn("QEMU remained paused after QMP cont", self.text)
        self.assertIn("finish_qemu_after_helper() {", self.text)
        self.assertIn('if [[ "$KEEP_QEMU_RUNNING_AFTER_HELPER" == "YES" ]]; then', self.text)
        self.assertIn("resume_qemu_if_debug_paused", self.text)
        self.assertIn(
            "keeping QEMU running after restore helper until it exits or MACVM_QEMU_TIMEOUT expires",
            self.text,
        )
        self.assertIn('collect_status "QEMU_RC" "$QEMU_PID" "$RUN_DIR/qemu.status"', self.text)
        self.assertLess(
            self.text.index("validate_restore_session_evidence"),
            self.text.index("finish_qemu_after_helper"),
        )
        self.assertIn(
            'wait_for_post_gdb_milestone_if_needed\n'
            '  stop_process "$POST_GDB_PID"\n'
            "  collect_post_gdb_status_if_needed\n"
            "  validate_restore_session_evidence",
            self.text,
        )
        self.assertEqual(
            self.text.count("validate_restore_session_evidence\n  finish_qemu_after_helper"),
            2,
        )

    def test_runner_waits_for_log_pattern_without_touching_host_state(self) -> None:
        self.assertIn("wait_for_log_pattern() {", self.text)
        self.assertIn('grep -Fq "$pattern" "$log_path"', self.text)
        self.assertIn("sleep 0.25", self.text)
        self.assertIn("timed out waiting for log pattern", self.text)

    def test_runner_fails_when_restore_helper_fails(self) -> None:
        self.assertIn('helper_rc="$(sed -n \'s/^HELPER_RC=//p\' "$RUN_DIR/helper.status")"', self.text)
        self.assertIn('if [[ "$helper_rc" != "0" ]]; then', self.text)
        self.assertIn("restore socket helper failed with exit code", self.text)

    def test_runner_stops_timeout_process_groups_without_broad_process_matching(self) -> None:
        self.assertIn('if kill -0 -- "-$pid"', self.text)
        self.assertIn('kill -TERM -- "-$pid"', self.text)
        self.assertIn('elif kill -0 "$pid"', self.text)
        self.assertIn('kill -TERM "$pid"', self.text)
        self.assertNotIn("pkill", self.text)
        self.assertNotIn("killall", self.text)

    def test_runner_defaults_to_minimal_trace_to_avoid_tcg_slowdown(self) -> None:
        self.assertIn('TRACE_VERBOSE="${MACVM_SMOKE_TRACE_VERBOSE:-NO}"', self.text)
        self.assertIn('if [[ -n "${MACVM_TRACE_EVENTS:-}" ]]; then', self.text)
        self.assertIn('printf \'%s\\n\' "$MACVM_TRACE_EVENTS" >"$TRACE_EVENTS"', self.text)
        self.assertIn('if [[ "$TRACE_VERBOSE" == "YES" ]]; then', self.text)
        self.assertIn("TRACE_EVENTS_VERBOSE_EOF", self.text)
        self.assertIn("TRACE_EVENTS_MINIMAL_EOF", self.text)
        match = re.search(
            r"<<'TRACE_EVENTS_MINIMAL_EOF'\n(?P<body>.*?)\nTRACE_EVENTS_MINIMAL_EOF",
            self.text,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        assert match is not None
        minimal_section = match.group("body")
        self.assertIn("bdif_vblk_error", minimal_section)
        self.assertIn("bdif_usb_restore_packet", minimal_section)
        self.assertNotIn("bdif_read", minimal_section)
        self.assertNotIn("bdif_vblk_read", minimal_section)

    def test_runner_can_pause_before_guest_reboot_without_changing_default(self) -> None:
        self.assertIn('PAUSE_ON_REBOOT="${MACVM_PAUSE_ON_REBOOT:-NO}"', self.text)
        self.assertIn('if [[ "$PAUSE_ON_REBOOT" != "YES" && "$PAUSE_ON_REBOOT" != "NO" ]]', self.text)
        self.assertIn('if [[ "$PAUSE_ON_REBOOT" == "YES" ]]; then', self.text)
        self.assertIn('-action "reboot=shutdown,shutdown=pause"', self.text)
        self.assertIn("the default remains a real reset", self.text)

    def test_runner_supports_bounded_opt_in_qemu_debug_logging(self) -> None:
        self.assertIn('QEMU_LOG_ITEMS="${MACVM_QEMU_LOG_ITEMS:-}"', self.text)
        self.assertIn(
            '[[ -n "$QEMU_LOG_ITEMS" && ! "$QEMU_LOG_ITEMS" =~ ^[a-z0-9_,]+$ ]]',
            self.text,
        )
        self.assertIn('if [[ -n "$QEMU_LOG_ITEMS" ]]; then', self.text)
        self.assertIn('-d "$QEMU_LOG_ITEMS"', self.text)
        self.assertIn('-D "$RUN_DIR/qemu-debug.log"', self.text)
        self.assertNotIn('-D /tmp/', self.text)

    def test_runner_supports_configurable_qemu_display_without_changing_default(self) -> None:
        self.assertIn('QEMU_DISPLAY="${MACVM_QEMU_DISPLAY:-none}"', self.text)
        self.assertIn("MACVM_QEMU_DISPLAY must be a single QEMU display backend token", self.text)
        self.assertIn('-display "$QEMU_DISPLAY"', self.text)
        self.assertNotIn("-display none", self.text)
        self.assertLess(
            self.text.index('QEMU_DISPLAY="${MACVM_QEMU_DISPLAY:-none}"'),
            self.text.index('-display "$QEMU_DISPLAY"'),
        )

    def test_runner_uses_run_scoped_reims_fail_log_by_default(self) -> None:
        self.assertIn('if [[ -z "${REIMS_VGPU_FAIL_LOG:-}" ]]; then', self.text)
        self.assertIn('export REIMS_VGPU_FAIL_LOG="$RUN_DIR/reims-vgpu-fail.log"', self.text)
        self.assertIn('printf \'%s\\n\' "$REIMS_VGPU_FAIL_LOG" >"$RUN_DIR/reims-vgpu-fail.path"', self.text)
        self.assertLess(
            self.text.index('mkdir -p "$RUN_DIR"'),
            self.text.index('export REIMS_VGPU_FAIL_LOG="$RUN_DIR/reims-vgpu-fail.log"'),
        )
        self.assertLess(
            self.text.index('export REIMS_VGPU_FAIL_LOG="$RUN_DIR/reims-vgpu-fail.log"'),
            self.text.index('timeout "$QEMU_TIMEOUT" "$QEMU_BIN"'),
        )

    def test_runner_exposes_run_scoped_qmp_for_evidence_capture(self) -> None:
        self.assertIn('-qmp "unix:$QMP_SOCK,server=on,wait=off"', self.text)
        self.assertIn('rm -f "$QMP_SOCK"', self.text)
        self.assertIn('rmdir "$QMP_SOCKET_TMP_DIR"', self.text)

    def test_runner_can_expose_a_read_only_external_root_to_xnu(self) -> None:
        self.assertIn('ROOT_IMAGE="${MACVM_ROOT_IMAGE:-}"', self.text)
        self.assertIn('EXPOSE_ROOT_VIRTIO="${MACVM_EXPOSE_ROOT_VIRTIO:-NO}"', self.text)
        self.assertIn('if [[ "$ROOT_IMAGE" != /* ]]; then', self.text)
        self.assertIn('require_file "$ROOT_IMAGE"', self.text)
        self.assertIn('printf \'%s\\n\' "$ROOT_DRIVE" >"$RUN_DIR/root-image.path"', self.text)
        self.assertIn(
            '-drive "if=pflash,index=1,format=raw,file=$RUN_DIR/root.img"', self.text
        )
        self.assertIn('if [[ "$EXPOSE_ROOT_VIRTIO" == "YES" ]]; then', self.text)
        self.assertIn(
            '-drive "if=none,id=macvm-root-virtio,format=raw,file=$ROOT_DRIVE,readonly=on"',
            self.text,
        )
        self.assertIn(
            '-device "vmapple-virtio-blk-pci,variant=root,drive=macvm-root-virtio"',
            self.text,
        )
        self.assertIn(
            "MACVM_EXPOSE_ROOT_VIRTIO=YES requires MACVM_ROOT_IMAGE",
            self.text,
        )

    def test_runner_exposes_a_validated_run_scoped_xart_isc_copy(self) -> None:
        self.assertIn('ISC_IMAGE="${MACVM_ISC_IMAGE:-}"', self.text)
        self.assertIn(
            'EXPOSE_ISC_VIRTIO="${MACVM_EXPOSE_ISC_VIRTIO:-${LEGACY_EXPOSE_AUX_VIRTIO:-NO}}"',
            self.text,
        )
        self.assertIn(
            'ISC_VALIDATOR="${MACVM_ISC_VALIDATOR:-$REPO_ROOT/tools/build_vmapple_isc.py}"',
            self.text,
        )
        self.assertIn('if [[ "$ISC_IMAGE" != /* ]]; then', self.text)
        self.assertIn('"$PYTHON_BIN" "$ISC_VALIDATOR" inspect "$ISC_IMAGE"', self.text)
        self.assertIn(
            "MACVM_EXPOSE_ISC_VIRTIO=YES requires MACVM_ISC_IMAGE", self.text
        )
        self.assertIn('ISC_DRIVE="$RUN_DIR/aux.img"', self.text)
        self.assertIn(
            'cp --reflink=auto --sparse=always -- "$ISC_IMAGE" "$ISC_DRIVE"',
            self.text,
        )
        self.assertIn(
            'printf \'%s\\n\' "$ISC_IMAGE" >"$RUN_DIR/isc-template.path"', self.text
        )
        self.assertIn(
            'printf \'%s\\n\' "$ISC_DRIVE" >"$RUN_DIR/isc-image.path"', self.text
        )
        self.assertIn('if [[ "$EXPOSE_ISC_VIRTIO" == "YES" ]]; then', self.text)
        self.assertIn(
            '-drive "if=none,id=macvm-isc-virtio,format=raw,file=$ISC_DRIVE,file.locking=off"',
            self.text,
        )
        self.assertIn(
            '-device "vmapple-virtio-blk-pci,variant=root,drive=macvm-isc-virtio,share-rw=on"',
            self.text,
        )
        self.assertNotIn(
            'vmapple-virtio-blk-pci,variant=aux,drive=macvm-isc-virtio',
            self.text,
        )
        self.assertNotIn("file=$ISC_IMAGE", self.text)
        self.assertNotIn('$RUN_DIR/isc.img', self.text)
        self.assertIn(
            'AUX_PFLASH_DRIVE="if=pflash,index=0,format=raw,file=$RUN_DIR/aux.img"',
            self.text,
        )
        self.assertIn('AUX_PFLASH_DRIVE+=",file.locking=off"', self.text)
        self.assertIn('-drive "$AUX_PFLASH_DRIVE"', self.text)

    def test_aux_sharing_is_limited_to_the_run_scoped_copy(self) -> None:
        self.assertIn('file=$ISC_DRIVE,file.locking=off', self.text)
        self.assertIn('share-rw=on', self.text)
        self.assertNotIn('file=$ISC_IMAGE,file.locking=off', self.text)
        self.assertLess(
            self.text.index('ISC_DRIVE="$RUN_DIR/aux.img"'),
            self.text.index('file=$ISC_DRIVE,file.locking=off'),
        )

    def test_aux_utility_is_a_separate_opt_in_frontend(self) -> None:
        self.assertIn('EXPOSE_UTIL_VIRTIO="${MACVM_EXPOSE_UTIL_VIRTIO:-NO}"', self.text)
        self.assertIn('MACVM_EXPOSE_UTIL_VIRTIO must be YES or NO', self.text)
        self.assertIn('AUX utility frontend currently requires the validated iSC topology', self.text)
        self.assertIn('validate_isc_report(inspect_isc_image(Path(sys.argv[1])))', self.text)
        self.assertEqual(self.text.count('-device "vmapple-virtio-blk-pci,variant=aux,drive=macvm-util-virtio,share-rw=on"'), 1)
        self.assertIn('-drive "if=none,id=macvm-util-virtio,format=raw,file=$RUN_DIR/aux.img,file.locking=off"', self.text)
        self.assertNotIn('drive=macvm-util-virtio,readonly=on', self.text)
        self.assertIn('-device "vmapple-virtio-blk-pci,variant=root,drive=macvm-isc-virtio,share-rw=on"', self.text)

    def test_isc_uses_disk_role_and_preserves_legacy_flag_compatibility(self) -> None:
        self.assertIn(
            'LEGACY_EXPOSE_AUX_VIRTIO="${MACVM_EXPOSE_AUX_VIRTIO:-}"', self.text
        )
        self.assertIn(
            "MACVM_EXPOSE_ISC_VIRTIO conflicts with legacy MACVM_EXPOSE_AUX_VIRTIO",
            self.text,
        )
        self.assertIn("role 1 (root) to AppleVirtIODiskStorageDevice", self.text)
        self.assertIn("role 2 (aux) to", self.text)
        self.assertIn("AppleVirtIOUtilStorageDevice", self.text)
        self.assertIn("apfs_boot_util requires an AppleAPFSVolume", self.text)
        self.assertEqual(
            self.text.count(
                '-device "vmapple-virtio-blk-pci,variant=root,drive=macvm-isc-virtio,share-rw=on"'
            ),
            1,
        )

    def test_runner_exposes_a_validated_run_scoped_recovery_overlay(self) -> None:
        self.assertIn('RECOVERY_IMAGE="${MACVM_RECOVERY_IMAGE:-}"', self.text)
        self.assertIn('QEMU_IMG_BIN="${MACVM_QEMU_IMG_BIN:-qemu-img}"', self.text)
        self.assertIn(
            'RECOVERY_VOLUME_UUID="${MACVM_RECOVERY_VOLUME_UUID:-}"', self.text
        )
        self.assertIn(
            'EXPOSE_RECOVERY_VIRTIO="${MACVM_EXPOSE_RECOVERY_VIRTIO:-NO}"',
            self.text,
        )
        self.assertIn(
            'RECOVERY_VALIDATOR="${MACVM_RECOVERY_VALIDATOR:-$REPO_ROOT/tools/build_vmapple_recovery.py}"',
            self.text,
        )
        self.assertIn(
            'MACVM_EXPOSE_RECOVERY_VIRTIO must be YES or NO', self.text
        )
        self.assertIn(
            'MACVM_EXPOSE_RECOVERY_VIRTIO=YES requires MACVM_RECOVERY_IMAGE and MACVM_RECOVERY_VOLUME_UUID',
            self.text,
        )
        self.assertIn('if [[ "$RECOVERY_IMAGE" != /* ]]; then', self.text)
        self.assertIn('require_file "$RECOVERY_IMAGE"', self.text)
        self.assertIn('require_file "$RECOVERY_VALIDATOR"', self.text)
        self.assertIn(
            '"$PYTHON_BIN" "$RECOVERY_VALIDATOR" inspect "$RECOVERY_IMAGE"',
            self.text,
        )
        self.assertIn(
            '--expected-volume-uuid "$RECOVERY_VOLUME_UUID"', self.text
        )
        self.assertIn(
            'export MACVM_RECOVERY_VOLUME_UUID="$RECOVERY_VOLUME_UUID"', self.text
        )
        self.assertIn(
            'require_executable "$QEMU_IMG_BIN"', self.text
        )
        self.assertIn(
            'RECOVERY_DRIVE="$RUN_DIR/recovery-overlay.qcow2"', self.text
        )
        self.assertIn(
            '"$QEMU_IMG_BIN" create -q -f qcow2 -F raw', self.text
        )
        self.assertIn(
            '-b "$RECOVERY_IMAGE" "$RECOVERY_DRIVE"', self.text
        )
        self.assertIn(
            'chmod u+rw "$RECOVERY_DRIVE"', self.text
        )
        self.assertIn(
            '"$QEMU_IMG_BIN" info --output=json "$RECOVERY_DRIVE"', self.text
        )
        self.assertIn(
            'printf \'%s\\n\' "$RECOVERY_IMAGE" >"$RUN_DIR/recovery-template.path"',
            self.text,
        )
        self.assertIn(
            'printf \'%s\\n\' "$RECOVERY_DRIVE" >"$RUN_DIR/recovery-image.path"',
            self.text,
        )
        self.assertIn(
            'printf \'%s\\n\' "$RECOVERY_VOLUME_UUID" >"$RUN_DIR/recovery-volume-uuid"',
            self.text,
        )
        self.assertIn(
            '-drive "if=none,id=macvm-recovery-virtio,format=qcow2,file=$RECOVERY_DRIVE"',
            self.text,
        )
        self.assertIn(
            '-device "vmapple-virtio-blk-pci,variant=root,drive=macvm-recovery-virtio"',
            self.text,
        )
        self.assertNotIn(
            'vmapple-virtio-blk-pci,variant=aux,drive=macvm-recovery-virtio',
            self.text,
        )
        self.assertIn("AppleAPFSVolume with role Recovery (0x4)", self.text)
        self.assertIn("52637672-7900-11AA-AA11-00306543ECAC", self.text)
        self.assertIn("prebootensurer then mounts it read-write", self.text)
        self.assertNotIn(
            'id=macvm-recovery-virtio,format=raw,file=$RECOVERY_IMAGE,readonly=on',
            self.text,
        )
        self.assertNotIn(
            'id=macvm-recovery-virtio,format=qcow2,file=$RECOVERY_DRIVE,readonly=on',
            self.text,
        )
        self.assertNotIn("share-rw=on,drive=macvm-recovery-virtio", self.text)

    def test_runner_can_load_a_validated_ramdisk_override_into_guest_ram(self) -> None:
        self.assertIn(
            'RAMDISK_OVERRIDE_IMAGE="${MACVM_RAMDISK_OVERRIDE_IMAGE:-}"', self.text
        )
        self.assertIn(
            'RAMDISK_OVERRIDE_ADDRESS="${MACVM_RAMDISK_OVERRIDE_ADDRESS:-}"',
            self.text,
        )
        self.assertIn(
            "RAMDisk override image and address must be provided together", self.text
        )
        self.assertIn('--allowed-root "$RESTORE_DIR"', self.text)
        self.assertIn('--memory-gib "$MEMORY_GIB"', self.text)
        self.assertIn(
            '-device "loader,file=$RAMDISK_OVERRIDE_IMAGE,addr=$RAMDISK_OVERRIDE_ADDRESS,force-raw=on"',
            self.text,
        )
        self.assertIn("ramdisk-override.path", self.text)
        self.assertIn("ramdisk-override.address", self.text)

    def test_runner_builds_a_run_scoped_two_module_trustcache_for_handoff(self) -> None:
        for variable in (
            "MACVM_RESTORE_TRUSTCACHE_IMAGE",
            "MACVM_BASESYSTEM_TRUSTCACHE_IMAGE",
            "MACVM_TRUSTCACHE_OVERRIDE_ADDRESS",
            "MACVM_TRUSTCACHE_REGION_TOOL",
        ):
            with self.subTest(variable=variable):
                self.assertIn(variable, self.text)
        self.assertIn(
            "Restore, BaseSystem, and address TrustCache overrides must be provided together",
            self.text,
        )
        self.assertIn('"$PYTHON_BIN" "$TRUSTCACHE_REGION_TOOL" build', self.text)
        self.assertIn('--allowed-root "$RESTORE_DIR"', self.text)
        self.assertIn('--memory-gib "$MEMORY_GIB"', self.text)
        self.assertIn('TRUSTCACHE_REGION_IMAGE="$RUN_DIR/trustcache-region.raw"', self.text)
        self.assertIn('export MACVM_TRUSTCACHE_OVERRIDE_IMAGE="$TRUSTCACHE_REGION_IMAGE"', self.text)
        self.assertIn(
            'export MACVM_TRUSTCACHE_OVERRIDE_ADDRESS="$TRUSTCACHE_OVERRIDE_ADDRESS"',
            self.text,
        )
        self.assertNotIn("loader,file=$TRUSTCACHE_REGION_IMAGE", self.text)
        self.assertNotIn("MACVM_TRUSTCACHE_PHYSICAL_DUMP", self.text)
        for evidence in (
            "trustcache-region.build",
            "restore-trustcache.path",
            "basesystem-trustcache.path",
            "trustcache-override.address",
        ):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, self.text)

    def test_runner_verifies_stage2_prompt_and_bidirectional_trace(self) -> None:
        self.assertIn("Entering iBootStage2 recovery mode, starting command prompt", self.text)
        self.assertIn("bdif_usb_restore_packet action=chardev-in", self.text)
        self.assertIn("bdif_usb_restore_packet action=chardev-out", self.text)


if __name__ == "__main__":
    unittest.main()
