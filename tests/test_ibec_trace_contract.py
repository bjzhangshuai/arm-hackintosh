from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class IBECTraceContractTests(unittest.TestCase):
    def test_relocated_halt_probe_enables_root_cause_trace_markers(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_relocated_halt.gdb").read_text(encoding="utf-8")

        self.assertIn("set $relocate_ibec_for_final_callback = 1", text)
        self.assertIn("set $trace_relocated_ibec_halt = 1", text)
        self.assertIn("set $trace_relocated_ibec_exceptions = 1", text)
        self.assertIn("set $trace_relocated_ibec_init_failure = 1", text)
        self.assertIn("set $trace_relocated_ibec_context_return = 1", text)

    def test_synthetic_root_descriptor_probe_is_opt_in_only(self) -> None:
        main_trace = (ROOT / "tools" / "trace_ibss_lpol_then_ibec_inject.gdb").read_text(
            encoding="utf-8"
        )
        inject_trace = (ROOT / "tools" / "trace_ibec_root_descriptor_inject.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("init-if-undefined $inject_synthetic_root_descriptor = 0", main_trace)
        self.assertIn("POST_IBEC_SYNTHETIC_ROOT_DESCRIPTOR_INJECTED", main_trace)
        self.assertIn("set $inject_synthetic_root_descriptor = 1", inject_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", inject_trace)

    def test_descriptor_table_probe_is_observe_only(self) -> None:
        main_trace = (ROOT / "tools" / "trace_ibss_lpol_then_ibec_inject.gdb").read_text(
            encoding="utf-8"
        )
        table_trace = (ROOT / "tools" / "trace_ibec_descriptor_table.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("init-if-undefined $trace_relocated_ibec_descriptor_table = 0", main_trace)
        self.assertIn("POST_IBEC_STATIC_DESCRIPTOR_ENTRY24", main_trace)
        self.assertIn("POST_IBEC_DESCRIPTOR_TABLE_READY", main_trace)
        self.assertIn("POST_IBEC_DESCRIPTOR_TABLE_SCAN", main_trace)
        self.assertIn("POST_IBEC_DESCRIPTOR_TABLE_FOUND", main_trace)
        self.assertIn("POST_IBEC_DESCRIPTOR_TABLE_NOT_FOUND", main_trace)
        self.assertIn("init-if-undefined $restore_relocated_ibec_descriptor_table = 0", main_trace)
        self.assertIn("set $trace_relocated_ibec_descriptor_table = 1", table_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", table_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", table_trace)

    def test_descriptor_table_restore_probe_is_opt_in_and_diagnostic(self) -> None:
        main_trace = (ROOT / "tools" / "trace_ibss_lpol_then_ibec_inject.gdb").read_text(
            encoding="utf-8"
        )
        restore_trace = (ROOT / "tools" / "trace_ibec_descriptor_table_restore.gdb").read_text(
            encoding="utf-8"
        )
        static_tail_trace = (ROOT / "tools" / "trace_ibec_static_tail_restore.gdb").read_text(
            encoding="utf-8"
        )
        low_scratch_trace = (ROOT / "tools" / "trace_ibec_static_tail_low_scratch.gdb").read_text(
            encoding="utf-8"
        )
        boot_progress_trace = (
            ROOT / "tools" / "trace_ibec_low_scratch_boot_progress.gdb"
        ).read_text(encoding="utf-8")
        bdif_enum_trace = (
            ROOT / "tools" / "trace_ibec_bdif_enum_low_scratch.gdb"
        ).read_text(encoding="utf-8")
        usb_restore_light_trace = (
            ROOT / "tools" / "trace_ibec_usb_restore_light.gdb"
        ).read_text(encoding="utf-8")
        usb_restore_bootstrap_detach_trace = (
            ROOT / "tools" / "trace_ibec_usb_restore_bootstrap_detach.gdb"
        ).read_text(encoding="utf-8")
        usb_packets_trace = (
            ROOT / "tools" / "trace_ibec_usb_packets_light.gdb"
        ).read_text(encoding="utf-8")
        img4_validation_trace = (
            ROOT / "tools" / "trace_ibec_img4_validation_light.gdb"
        ).read_text(encoding="utf-8")
        img4_command_trace = (
            ROOT / "tools" / "trace_ibec_img4_command_phase.gdb"
        ).read_text(encoding="utf-8")
        allocator_step_trace = (ROOT / "tools" / "trace_ibec_stage_allocator_step.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("POST_IBEC_DESCRIPTOR_TABLE_BEFORE_OPTIONAL_RESTORE", main_trace)
        self.assertIn("POST_IBEC_DESCRIPTOR_TABLE_RESTORED", main_trace)
        self.assertIn("init-if-undefined $restore_relocated_ibec_static_tail = 0", main_trace)
        self.assertIn("POST_IBEC_STATIC_TAIL_RESTORED", main_trace)
        self.assertIn("firebloom_meta0", main_trace)
        self.assertIn("iBEC.descriptor-table.bin", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_CALL", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_RETURN", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_CALLEE_RETURN", main_trace)
        self.assertIn("POST_IBEC_SERVICE_CALL_BOOTSTRAP_SVC", main_trace)
        self.assertIn("IBEC_STAGE_CONFIG_HELPER_ENTER", main_trace)
        self.assertIn("IBEC_STAGE_CONFIG_HELPER_FLAG_CHECK", main_trace)
        self.assertIn("IBEC_STAGE_CONFIG_HELPER_AFTER_CONTEXT_BUILD", main_trace)
        self.assertIn("IBEC_STAGE_CONFIG_HELPER_RETURN", main_trace)
        self.assertIn("IBEC_STAGE_CONTEXT_BUILD_ENTER", main_trace)
        self.assertIn("IBEC_STAGE_CONTEXT_BUILD_RETURN", main_trace)
        self.assertIn("IBEC_RESTORE_GLOBALS_PRE", main_trace)
        self.assertIn("IBEC_RESTORE_GLOBALS_ENTER", main_trace)
        self.assertIn("IBEC_RESTORE_GLOBALS_POST", main_trace)
        self.assertIn("IBEC_STAGE_CONTEXT_APPEND_RETURN", main_trace)
        self.assertIn("IBEC_STAGE_CONTEXT_APPEND_RETAB", main_trace)
        self.assertIn("IBEC_STAGE_CONTEXT_APPEND_LIMIT_FAIL", main_trace)
        self.assertIn("IBEC_STAGE_CONTEXT_APPEND_BOUNDS_FAIL", main_trace)
        self.assertIn("IBEC_STAGE_CONFIG_HELPER_RETURNED_TO_CALLER", main_trace)
        self.assertIn("IBEC_ALLOC_HELPER_RETURN_PRE x19=0x%lx qword_30=0x%lx", main_trace)
        self.assertIn("IBEC_ALLOC_HELPER_RETAB", main_trace)
        self.assertIn("IBEC_ALLOC_HELPER_AFTER_RET", main_trace)
        self.assertIn("init-if-undefined $step_stage_allocator_return = 0", main_trace)
        self.assertIn("set $ibec_manifest_ok_seen = 0", main_trace)
        self.assertIn("set $ibec_manifest_ok_seen = 1", main_trace)
        self.assertIn("set $in_relocated_ibec = 0", main_trace)
        self.assertIn("set $in_relocated_ibec = 1", main_trace)
        self.assertIn("set $ibec_root_build_return_seen = 0", main_trace)
        self.assertIn("set $ibec_root_build_return_seen = 1", main_trace)
        self.assertIn("init-if-undefined $detach_after_ibec_aux_bdif_ready = 0", main_trace)
        self.assertIn("POST_IBEC_AUX_BDIF_READY_DETACH", main_trace)
        self.assertIn("expected_cfg=0x%x", main_trace)
        self.assertIn("detach_after_ibec_aux_bdif_ready && $w23 == 0x2 && $w21 == 0x0", main_trace)
        self.assertIn("set $detach_after_ibec_aux_bdif_ready = 1", usb_restore_bootstrap_detach_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", usb_restore_bootstrap_detach_trace)
        self.assertIn("init-if-undefined $trace_relocated_ibec_descriptor_presence = 1", main_trace)
        self.assertIn("init-if-undefined $trace_relocated_ibec_map_checks = 1", main_trace)
        self.assertIn("init-if-undefined $trace_relocated_ibec_bdif_enum = 0", main_trace)
        self.assertIn("init-if-undefined $trace_relocated_ibec_usb_packets = 0", main_trace)
        self.assertIn("init-if-undefined $trace_ibec_allocator = 1", main_trace)
        self.assertIn("if $trace_relocated_ibec_bdif_enum", main_trace)
        self.assertIn("if $trace_relocated_ibec_usb_packets", main_trace)
        self.assertIn("0xfffffc0000000000", main_trace)
        self.assertIn("0xfffffd0000000000", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_SLOT_REGISTER", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_SLOT_REGISTER", main_trace)
        self.assertIn("POST_IBEC_USB_KIND1_CALLBACK", main_trace)
        self.assertIn("POST_IBEC_USB_KIND1_QUEUE_CHECK", main_trace)
        self.assertIn("POST_IBEC_USB_KIND1_EMPTY_QUEUE_CREDIT", main_trace)
        self.assertIn("POST_IBEC_USB_KIND1_ACK_PATH", main_trace)
        self.assertIn("POST_IBEC_USB_KIND2_CALLBACK", main_trace)
        self.assertIn("POST_IBEC_USB_KIND3_PENDING_CHECK", main_trace)
        self.assertIn("POST_IBEC_USB_KIND3_CLEAR_PENDING", main_trace)
        self.assertIn("POST_IBEC_USB_KIND3_QUEUE_HEAD", main_trace)
        self.assertIn("POST_IBEC_USB_KIND3_EMPTY_OR_INVALID", main_trace)
        self.assertIn("POST_IBEC_USB_KIND3_EMPTY_OR_INVALID_SLOT", main_trace)
        self.assertIn("POST_IBEC_USB_STATUS_REPLY_BUILD", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_QUEUE_OR_SEND", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_QUEUE_PENDING_CHECK", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_QUEUE_ENQUEUE", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_QUEUE_SEND_IMMEDIATE", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_ENTRY", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND2_DISPATCH", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_PAYLOAD_ENTRY", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_SLOT_STATE", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_LENGTH_CLASSIFY", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_SETUP_SPLIT", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_SETUP_BYTES", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_QUEUE_PAYLOAD", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_QUEUE_PAYLOAD_BYTES", main_trace)
        self.assertIn("POST_IBEC_USB_CALLBACK_KIND1_QUEUE_DONE", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_ENGINE_SIGNAL", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_ENGINE_ENTRY", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_ENGINE_WAIT", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_ENGINE_WAIT_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_ENGINE_SLOT", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_ENGINE_COPY_HOST_PAYLOAD", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_ENGINE_SEND_GUEST_PACKET", main_trace)
        self.assertIn("POST_IBEC_USB_INPUT_QUEUE_ENQUEUE", main_trace)
        self.assertIn("POST_IBEC_USB_INPUT_QUEUE_ENQUEUE_FRAME", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_BUILD_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_BUILD_CALL_WAIT", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_BUILD_WAIT_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_EVENT_PAYLOAD_BRANCH", main_trace)
        self.assertIn("POST_IBEC_USB_EVENT_REPLY_BUILD", main_trace)
        self.assertIn("POST_IBEC_USB_EVENT_LARGE_BUFFER_PATH", main_trace)
        self.assertIn("POST_IBEC_USB_EVENT_COMMIT", main_trace)
        self.assertIn("POST_IBEC_USB_REQUEST_ENGINE_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_STATE_ADVANCE", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_STATE1_BRANCH", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_STATE1_CALLBACK", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_STATE2_BRANCH", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_STATE2_CALLBACK", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_STATE3_BRANCH", main_trace)
        self.assertIn("POST_IBEC_USB_ENDPOINT_STATE3_DESC_READY", main_trace)
        self.assertIn("POST_IBEC_USB_TASKS_INIT_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_RPC_TASK_CREATE", main_trace)
        self.assertIn("POST_IBEC_USB_CMD_TASK_CREATE", main_trace)
        self.assertIn("POST_IBEC_USB_RPC_TASK_ENTRY", main_trace)
        self.assertIn("POST_IBEC_USB_CMD_TASK_ENTRY", main_trace)
        self.assertIn("POST_IBEC_USB_CMD_TASK_STATUS_CALL", main_trace)
        self.assertIn("POST_IBEC_USB_CMD_TASK_DISPATCH_PACKET", main_trace)
        self.assertIn("POST_IBEC_USB_CMD_TASK_DISPATCH_BYTES", main_trace)
        self.assertIn("POST_IBEC_USB_CMD_TASK_SVC81", main_trace)
        self.assertIn("POST_IBEC_USB_CMD_TASK_SVC81_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_STATUS_WAIT_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_STATUS_WAIT_SVC82", main_trace)
        self.assertIn("POST_IBEC_USB_STATUS_WAIT_SVC82_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_STATUS_WAIT_READY", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_TASK_INIT_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_TASK_CREATE", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_TASK_ENTRY", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_TASK_POLL_BYTE", main_trace)
        self.assertIn("POST_IBEC_USB_REQ_TASK_CONSUME_BYTE", main_trace)
        self.assertIn("POST_IBEC_USB_VBUS_POLL_TASK_CREATE", main_trace)
        self.assertIn("POST_IBEC_USB_VBUS_TASK_CREATE", main_trace)
        self.assertIn("POST_IBEC_USB_VBUS_TASK_ENTRY", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_DISPATCH_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_DISPATCH_BYTES", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_DISPATCH_TYPE0", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_DISPATCH_TYPE1", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_DISPATCH_CALL_ENDPOINT", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_DISPATCH_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_TYPE0_HANDLER_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_TYPE0_ARMED", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_ENQUEUE_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_ENQUEUE_SPAN0", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_ENQUEUE_SPAN1", main_trace)
        self.assertIn("POST_IBEC_USB_PACKET_ENQUEUE_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_REQUEST_WAIT_ENTER", main_trace)
        self.assertIn("POST_IBEC_USB_REQUEST_SVC81", main_trace)
        self.assertIn("POST_IBEC_USB_REQUEST_STATUS_RETURN", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_ENTER", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_STATUS_RETURN", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_UNK2_RETURN", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_CFG_RETURN", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_CFG_ACCEPTED", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_LOAD_MMIO_BASE", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_MMIO_BASE_LOADED", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_UNK1_CAP_LOADED", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_CFG_MISMATCH", main_trace)
        self.assertIn("POST_IBEC_BDIF_ENUM_SUCCESS_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_ENUM_RETURN", main_trace)
        self.assertIn("POST_IBEC_USB_ENUM_ACCEPTED", main_trace)
        self.assertIn(
            "condition $bpnum $phase == 1 && $ibec_manifest_ok_seen && ($x2 - $x1) == 0x80000",
            main_trace,
        )
        self.assertIn("set $synthetic_return_addr = 0x73fff000", main_trace)
        self.assertIn("break *0x73fff000", main_trace)
        self.assertIn("set $x30 = $synthetic_return_addr", main_trace)
        self.assertNotIn("set $x30 = 0x700c56c8", main_trace)
        self.assertNotIn("break *0x700c56c8", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7DD0", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7DDC", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7DE8", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7DF4", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E00", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E0C", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E18", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E24", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E30", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E3C", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E48", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E4C", main_trace)
        self.assertIn("POST_IBEC_ROOT_BUILD_FAIL_7E58", main_trace)
        self.assertIn("POST_IBEC_FATAL_ABORT_HELPER_ENTRY", main_trace)
        self.assertIn("if $trace_relocated_ibec_descriptor_presence", main_trace)
        self.assertIn("if $trace_relocated_ibec_map_checks", main_trace)
        self.assertIn("POST_IBEC_EXCEPTION_VECTOR_INIT_ENTER", main_trace)
        self.assertIn("POST_IBEC_EXCEPTION_VECTOR_INIT_STORE_PAIR", main_trace)
        self.assertIn("POST_IBEC_EXCEPTION_VECTOR_INIT_STORE_LIMIT", main_trace)
        self.assertIn("POST_IBEC_EXCEPTION_VECTOR_APPEND_LOAD", main_trace)
        self.assertIn("POST_IBEC_EXCEPTION_VECTOR_APPEND_STORE", main_trace)
        self.assertIn("POST_IBEC_EXCEPTION_VECTOR_APPEND_BOUNDS_FAIL", main_trace)
        self.assertIn("0x70121ea0", main_trace)
        self.assertIn("condition $bpnum $in_relocated_ibec && !$ibec_root_build_return_seen", main_trace)
        self.assertIn("POST_IBEC_FIREBLOOM_SLICE_VALIDATE_ENTER", main_trace)
        self.assertIn("POST_IBEC_FIREBLOOM_SLICE_VALIDATE_TUPLE", main_trace)
        self.assertIn("POST_IBEC_FIREBLOOM_SLICE_VALIDATE_FAIL", main_trace)
        self.assertIn("POST_IBEC_FIREBLOOM_UNALIGNED_PTR_PANIC", main_trace)
        self.assertIn("IBEC_IMG4_VALIDATE_ENTER", img4_validation_trace)
        self.assertIn("IBEC_IMG4_PARSE_RETURN", img4_validation_trace)
        self.assertIn("IBEC_IMG4_DEEP_RETURN", img4_validation_trace)
        self.assertIn("IBEC_IMG4_FAILURE_PATH", img4_validation_trace)
        self.assertIn("IBEC_IMG4_VALIDATE_RETURN", img4_validation_trace)
        self.assertIn("set $phase = 0", img4_validation_trace)
        self.assertIn("set $in_relocated_ibec = 0", img4_validation_trace)
        self.assertIn("condition $bpnum $phase == 1", img4_validation_trace)
        self.assertIn("set $trace_ibec_allocator = 0", img4_validation_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", img4_validation_trace)
        self.assertIn("target remote 127.0.0.1:12345", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_VALIDATE_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PARSE_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_FAILURE_PATH", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_VALIDATE_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_TYPE_CHECK", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_PAYLOAD_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_PAYLOAD_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_STATUS_MAP_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_STATUS_MAP_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_FINAL_BRANCH", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_TYPE_REJECT", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_DEEP_BOUNDS_REJECT", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_VALIDATE_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_COMPONENT_POLICY_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_COMPONENT_POLICY_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_COMPONENT_POLICY_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_COMPONENT_TYPE_CHECK", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_COMPONENT_ZMEM_PRECHECK_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_COMPONENT_ZMEM_LENGTH_CHECK", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_COMPONENT_FAIL_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_ERROR_HELPER_A", img4_command_trace)
        self.assertIn("IBEC_CMD_ERROR_HELPER_B", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_AFTER_COMPONENT_OK", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_TRUST_EVAL_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_POLICY_MAIN_OK", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_COPY_DONE", img4_command_trace)
        self.assertIn("IBEC_CMD_IMG4_PAYLOAD_SUCCESS_EXIT_PRE", img4_command_trace)
        self.assertIn("IBEC_CMD_COMPARE_WRAPPER_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_COMPARE_BYTES", img4_command_trace)
        self.assertIn("IBEC_CMD_COMPARE_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_KERNELCACHE_STAGE_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_KERNELCACHE_LOAD_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_KERNELCACHE_LOAD_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_OPEN_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_VALIDATE_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_VALIDATE_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_IMAGE_INVALID", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_SUCCESS", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_PRIMARY_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_OPEN_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_ALT_VALIDATE_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_ALT_VALIDATE_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_IMAGE_INVALID", img4_command_trace)
        self.assertIn("IBEC_CMD_LOAD_KERNELCACHE_SUCCESS", img4_command_trace)
        self.assertIn("IBEC_CMD_POST_BOOT_ALIGN_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_POST_BOOT_ALIGN_FLAG", img4_command_trace)
        self.assertIn("IBEC_CMD_POST_BOOT_ALIGN_REGISTER", img4_command_trace)
        self.assertIn("IBEC_CMD_POST_BOOT_ALIGN_REMAINDER_PRE", img4_command_trace)
        self.assertIn("IBEC_CMD_POST_BOOT_ALIGN_REJECT", img4_command_trace)
        self.assertIn("IBEC_CMD_POST_BOOT_ALIGN_CALLER_RETURN_PRE", img4_command_trace)
        self.assertIn("IBEC_CMD_POST_BOOT_ALIGN_CALLER_RETAB", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_POST_ALIGN_OK", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_MAIN_HANDOFF_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_MAIN_HANDOFF_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_BOOT_ARGS_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_BOOT_ARGS_SUCCESS_BRANCH", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_PREPARE_IBOOT_HANDOFF_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_PREPARE_IBOOT_HANDOFF_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_ENTER", img4_command_trace)
        self.assertIn("set $bootx_final_switch_seen = 0", img4_command_trace)
        self.assertIn("set $bootx_final_switch_seen = 1", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_SVC6", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_AFTER_SVC6", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_POST_SVC_HELPER_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_ERROR_HELPER_B_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_KIND_NOTIFY_A", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_KIND_NOTIFY_B", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_FLUSH_A_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_FLUSH_B_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_PANIC_OR_LOG_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_FINAL_SWITCH_LOG_CALL", img4_command_trace)
        self.assertIn("set $bootx_notify_b_seen = 0", img4_command_trace)
        self.assertIn("set $bootx_notify_b_seen = 1", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_AFTER_SET_KIND_FLAG", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_HELPER_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_WAIT_FLAG1", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_FLAG1", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_WAIT_FLAG2", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_FLAG2", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_SVC_C5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_AFTER_SVC_C5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_POST_BRANCH", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_FINAL_SVC_C5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_FINAL_AFTER_SVC_C5", img4_command_trace)
        self.assertIn("set $bootx_notify_b_callback = 0", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_SLOT", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_LOADED", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_BRAAZ", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_CALLBACK_MISSING", img4_command_trace)
        self.assertIn("set $bootx_notify_b_callback_seen = 0", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET0_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET0_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET80_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_RESET80_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_PENDING_RELEASE_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_SLOT_LOOP_START", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_SLOT ", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_SLOT_RELEASE_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_LOOP_DONE", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAILCALL_C5B0", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_RELEASE_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_RELEASE_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_FLAG_LOADED", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_PATH", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_AFTER_BOUND", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_RELEASE_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_OPTIONAL_RELEASE_RETURN", img4_command_trace)
        self.assertIn("set $bootx_tail_release_seen = 0", img4_command_trace)
        self.assertIn("set $bootx_tail_release_status_cleared_hits = 0", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_WAIT_SETUP", img4_command_trace)
        self.assertIn("$bootx_tail_release_status_cleared_hits < 12", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_STATUS_CLEARED", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_STATUS_READ_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_STATUS_READ_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_WAIT_DONE", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_RETURN_VALUE", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_TAIL_RELEASE_RETAB", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_BUFFER_RELEASE_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_BOUNDS_FAIL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CALLBACK_TAIL_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_OUTER_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_FALLBACK_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_RETURN_PREP", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_RETURN_BRANCH", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_A_RETAB_SHIM", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_CLEANUP_A", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_B_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_B_SVC_C5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_CLEANUP_B_AFTER_SVC_C5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_CLEANUP_B", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_SVC_C5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_AFTER_SVC_C5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_DRAIN_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_SVC5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_AFTER_SVC5", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_STATE_MMIO_WRITE", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_STATE_HELPER_RETURNED", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_NOTIFY_B_RETURN", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_KIND_CHECK", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_NON_STAGE2_FLAG_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_SET_BOOT_FLAG", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_BOOT_FLAG_WRITE", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_ARGS_PREP", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_WRAPPER_CALL", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_WRAPPER_ENTER", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_SVC7", img4_command_trace)
        self.assertIn("IBEC_CMD_BOOTX_HANDOFF_SVC7_RETURNED", img4_command_trace)
        self.assertIn("IBEC_CMD_EXCEPTION_ESR_FAR", img4_command_trace)
        self.assertIn("x/24i $post_ibec_elr", img4_command_trace)
        self.assertIn("IBEC_CMD_EXCEPTION_ELR_CLEANUP", img4_command_trace)
        self.assertIn("IBEC_CMD_HALT_LOOP", img4_command_trace)
        self.assertIn("IBEC_CMD_PANIC_LOG_ENTRY", img4_command_trace)
        self.assertIn("break *0x7008af74", img4_command_trace)
        self.assertIn("break *0x7008afec", img4_command_trace)
        self.assertIn("break *0x7008b060", img4_command_trace)
        self.assertIn("break *0x7008b090", img4_command_trace)
        self.assertIn("break *0x7008b098", img4_command_trace)
        self.assertIn("break *0x7008a7ec", img4_command_trace)
        self.assertIn("break *0x7008a7f0", img4_command_trace)
        self.assertIn("break *0x7008a670", img4_command_trace)
        self.assertIn("break *0x70071c50", img4_command_trace)
        self.assertIn("break *0x700726e0", img4_command_trace)
        self.assertIn("break *0x70072818", img4_command_trace)
        self.assertIn("break *0x700e5fa8", img4_command_trace)
        self.assertIn("break *0x70071fd0", img4_command_trace)
        self.assertIn("break *0x7007242c", img4_command_trace)
        self.assertIn("break *0x700b53dc", img4_command_trace)
        self.assertIn("break *0x700b5430", img4_command_trace)
        self.assertIn("break *0x700720a4", img4_command_trace)
        self.assertIn("break *0x70070ef4", img4_command_trace)
        self.assertIn("break *0x70076e14", img4_command_trace)
        self.assertIn("break *0x70076f60", img4_command_trace)
        self.assertIn("break *0x70076f64", img4_command_trace)
        self.assertIn("break *0x700c33c4", img4_command_trace)
        self.assertIn("break *0x700cc818", img4_command_trace)
        self.assertIn("break *0x700770e4", img4_command_trace)
        self.assertIn("break *0x70077234", img4_command_trace)
        self.assertIn("break *0x700772cc", img4_command_trace)
        self.assertIn("POST_IBEC_FIREBLOOM_UNALIGNED_PTR_METADATA", main_trace)
        self.assertIn("POST_IBEC_PANIC_REPORT_ENTRY", main_trace)
        self.assertIn("POST_IBEC_PANIC_REPORT_STRING_X0", main_trace)
        self.assertIn("POST_IBEC_PANIC_REPORT_STRING_X1", main_trace)
        self.assertIn("POST_IBEC_PANIC_REPORT_FINAL_FORMAT_CALL", main_trace)
        self.assertIn("POST_IBEC_PANIC_REPORT_RESET_CALL", main_trace)
        self.assertIn("POST_IBEC_PANIC_REPORT_FINAL_TEXT", main_trace)
        self.assertIn("POST_IBEC_FATAL_RESET_ENTRY", main_trace)
        self.assertIn("POST_IBEC_FATAL_RESET_SYSTEM_RESET_CALL", main_trace)
        self.assertIn("POST_IBEC_FATAL_RESET_STRING_X20", main_trace)
        self.assertIn("POST_IBEC_SERVICE_CALL_8_WRAPPER", main_trace)
        self.assertIn("set $restore_relocated_ibec_descriptor_table = 1", restore_trace)
        self.assertIn("set $trace_relocated_ibec_descriptor_table = 1", restore_trace)
        self.assertIn("set $trace_relocated_ibec_root_build = 1", restore_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", restore_trace)
        self.assertIn("set $restore_relocated_ibec_static_tail = 1", static_tail_trace)
        self.assertIn("set $restore_relocated_ibec_descriptor_table = 1", static_tail_trace)
        self.assertIn("set $trace_relocated_ibec_root_build = 1", static_tail_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", static_tail_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", static_tail_trace)
        self.assertIn("set $restore_relocated_ibec_static_tail = 1", low_scratch_trace)
        self.assertIn("set $restore_relocated_ibec_descriptor_table = 1", low_scratch_trace)
        self.assertIn("set $trace_relocated_ibec_descriptor_table = 0", low_scratch_trace)
        self.assertIn("set $trace_relocated_ibec_root_build = 1", low_scratch_trace)
        self.assertIn("set $trace_relocated_ibec_context_return = 0", low_scratch_trace)
        self.assertIn("set $trace_relocated_ibec_descriptor_presence = 0", low_scratch_trace)
        self.assertIn("set $trace_relocated_ibec_map_checks = 0", low_scratch_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", low_scratch_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", low_scratch_trace)
        self.assertIn("set $restore_relocated_ibec_static_tail = 1", boot_progress_trace)
        self.assertIn("set $restore_relocated_ibec_descriptor_table = 1", boot_progress_trace)
        self.assertIn("set $trace_relocated_ibec_root_build = 0", boot_progress_trace)
        self.assertIn("set $trace_relocated_ibec_context_return = 0", boot_progress_trace)
        self.assertIn("set $trace_relocated_ibec_descriptor_presence = 0", boot_progress_trace)
        self.assertIn("set $trace_relocated_ibec_map_checks = 0", boot_progress_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", boot_progress_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", boot_progress_trace)
        self.assertIn("set $restore_relocated_ibec_static_tail = 1", bdif_enum_trace)
        self.assertIn("set $restore_relocated_ibec_descriptor_table = 1", bdif_enum_trace)
        self.assertIn("set $trace_relocated_ibec_bdif_enum = 1", bdif_enum_trace)
        self.assertIn("set $trace_relocated_ibec_descriptor_presence = 0", bdif_enum_trace)
        self.assertIn("set $trace_relocated_ibec_map_checks = 0", bdif_enum_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", bdif_enum_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", bdif_enum_trace)
        self.assertIn("set $restore_relocated_ibec_static_tail = 1", usb_restore_light_trace)
        self.assertIn("set $restore_relocated_ibec_descriptor_table = 1", usb_restore_light_trace)
        self.assertIn("set $trace_relocated_ibec_bdif_enum = 1", usb_restore_light_trace)
        self.assertIn("set $trace_ibec_allocator = 0", usb_restore_light_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", usb_restore_light_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", usb_restore_light_trace)
        self.assertIn("set $restore_relocated_ibec_static_tail = 1", usb_packets_trace)
        self.assertIn("set $restore_relocated_ibec_descriptor_table = 1", usb_packets_trace)
        self.assertIn("set $trace_relocated_ibec_usb_packets = 1", usb_packets_trace)
        self.assertIn("set $trace_ibec_allocator = 0", usb_packets_trace)
        self.assertNotIn("set $inject_synthetic_root_descriptor = 1", usb_packets_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", usb_packets_trace)
        self.assertIn("set $step_stage_allocator_return = 1", allocator_step_trace)
        self.assertIn("source /home/macvm/src/macvm/tools/trace_ibss_lpol_then_ibec_inject.gdb", allocator_step_trace)

    def test_main_ibec_trace_has_descriptor_exception_and_halt_evidence(self) -> None:
        text = (ROOT / "tools" / "trace_ibss_lpol_then_ibec_inject.gdb").read_text(
            encoding="utf-8"
        )

        required_markers = (
            "POST_IBEC_ENTRY",
            "POST_IBEC_ROOT_LOOKUP_REQUEST",
            "POST_IBEC_ROOT_DESCRIPTOR_CHECK_CALL",
            "POST_IBEC_DESCRIPTOR_PRESENT_ENTER",
            "POST_IBEC_DESCRIPTOR_PRESENT_BASIC_CHECK",
            "POST_IBEC_DESCRIPTOR_PRESENT_FAIL",
            "POST_IBEC_CONTEXT_RETURNED_TO_PANIC",
            "POST_IBEC_EXCEPTION_ESR_FAR",
            "POST_IBEC_PANIC_LOG_ENTRY",
            "POST_IBEC_HALT_LOOP",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_exception_trace_uses_general_register_snapshots_not_direct_sysregs(self) -> None:
        text = (ROOT / "tools" / "trace_ibss_lpol_then_ibec_inject.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("saved_esr", text)
        self.assertIn("saved_far", text)
        self.assertIn("saved_elr", text)
        self.assertNotIn("$esr_el1", text)
        self.assertNotIn("$far_el1", text)
        self.assertNotIn("$elr_el1", text)

    def test_bootx_live_dump_trace_uses_readable_ibec_text_window(self) -> None:
        text = (ROOT / "tools" / "dump_ibec_bootx_live.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("IBEC_BOOTX_MMIO_PROBE_30240040", text)
        self.assertIn("IBEC_BOOTX_MMIO_PROBE_30260000_BLOCK", text)
        self.assertIn("IBEC_BOOTX_EXCEPTION_ESR_FAR", text)
        self.assertIn("dump binary memory /tmp/macvm-ibec-bootx-live.bin 0x7006c000 0x70130000", text)
        self.assertIn("base=0x7006c000 end=0x70130000", text)
        self.assertNotIn("dump binary memory /tmp/macvm-ibec-bootx-live.bin 0x70000000 0x70130000", text)

    def test_bootx_handoff_trace_marks_final_svc7_path(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_handoff.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_HANDOFF_WRAPPER_ENTER",
            "IBEC_BOOTX_HANDOFF_SVC7",
            "IBEC_BOOTX_HANDOFF_SVC7_RETURNED",
            "IBEC_BOOTX_SVC7_HANDLER_ENTER",
            "IBEC_BOOTX_STAGE_SWITCH_ENTER",
            "IBEC_BOOTX_STAGE_SWITCH_FAIL_NO_READY_FRAME",
            "IBEC_BOOTX_STAGE_SWITCH_FAIL_NO_CALLBACK",
            "IBEC_BOOTX_HANDOFF_EXCEPTION_ESR_FAR",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("break *0x70087da8", text)
        self.assertIn("break *0x70087db8", text)
        self.assertIn("break *0x70087dbc", text)
        self.assertIn("break *0x700be548", text)
        self.assertIn("break *0x700c035c", text)
        self.assertIn("set $bootx_handoff_seen = 0", text)
        self.assertIn("set $bootx_handoff_seen = 1", text)
        self.assertIn("condition $bpnum $bootx_handoff_seen", text)
        self.assertNotIn("set $x", text)

    def test_boot_args_override_is_layout_guarded_and_handoff_scoped(self) -> None:
        text = (ROOT / "tools" / "override_ibec_boot_args_verbose.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("break *0x70087c8c", text)
        self.assertIn("set $macvm_boot_args = $x1", text)
        self.assertIn("$macvm_boot_args_revision != 3", text)
        self.assertIn("$macvm_boot_args_version != 2", text)
        self.assertIn("0x6d3d6472", text)
        self.assertIn("0x3064", text)
        self.assertIn("MACVM_BOOT_ARGS_REFUSED unexpected-layout", text)
        self.assertIn("MACVM_BOOT_ARGS_REFUSED unexpected-command-line", text)
        self.assertIn(
            'b"rd=md0 serial=3 -v -noprogress debug=0x144 keepsyms=1 wdt=-1\\0"',
            text,
        )
        self.assertNotIn("set $x1", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)

    def test_basesystem_boot_args_override_targets_apple_root_virtio(self) -> None:
        text = (ROOT / "tools" / "override_ibec_boot_args_basesystem.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("break *0x70087c8c", text)
        self.assertIn("set $macvm_boot_args = $x1", text)
        self.assertIn("$macvm_boot_args_revision != 3", text)
        self.assertIn("$macvm_boot_args_version != 2", text)
        self.assertIn("0x6d3d6472", text)
        self.assertIn("0x3064", text)
        self.assertIn("MACVM_BASESYSTEM_BOOT_ARGS_REFUSED unexpected-layout", text)
        self.assertIn(
            "MACVM_BASESYSTEM_BOOT_ARGS_REFUSED unexpected-command-line", text
        )
        self.assertIn(
            'b"rd=disk0s1 serial=3 -v -noprogress debug=0x144 keepsyms=1 wdt=-1\\0"',
            text,
        )
        self.assertNotIn("set $x1", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)

    def test_basesystem_auth_injection_is_capacity_and_type_guarded(self) -> None:
        text = (ROOT / "tools" / "inject_basesystem_auth_and_boot_args.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("break *0x70087c8c", text)
        self.assertIn("set $macvm_boot_args = $x1", text)
        self.assertIn("$macvm_boot_args_revision != 3", text)
        self.assertIn("$macvm_boot_args_version != 2", text)
        self.assertIn("0x6d3d6472", text)
        self.assertIn("0x3064", text)
        self.assertIn('struct.unpack("<QI", dt_fields)', text)
        self.assertIn('struct.unpack("<QQQ", memory_fields)', text)
        self.assertIn("device_tree_virtual - virt_base + phys_base", text)
        self.assertIn("device_tree_physical < phys_base + memory_size", text)
        self.assertIn("parse_device_tree(flattened, allow_zero_padding=True)", text)
        self.assertIn('memory_map_region(logical_tree, "DeviceTree")', text)
        self.assertIn("mapped_base != device_tree_physical", text)
        self.assertIn("capacity < device_tree_length", text)
        self.assertIn("MACVM_BASESYSTEM_AUTH_BLOB", text)
        self.assertIn(
            "from basesystem_auth import BaseSystemAuthError, extract_csys_auth_payload",
            text,
        )
        self.assertIn("auth_payload = extract_csys_auth_payload(auth_container)", text)
        self.assertIn("replace_properties_exact_span", text)
        self.assertIn('node_path="/device-tree/chosen/secure-boot-hashes"', text)
        self.assertIn('replaced_hash_names = ("rtsc", "rdsk", "rdtr", "rkrn")', text)
        self.assertIn('(\"base-system-volume-auth-blob\", auth_payload, False)', text)
        self.assertNotIn('(\"base-system-volume-auth-blob\", auth_container, False)', text)
        self.assertIn(
            "auth_padding_length = len(auth_container) - len(auth_payload) + 32",
            text,
        )
        self.assertIn("unsafe BaseSystem auth padding length", text)
        self.assertIn(
            '(\"macvm-auth-padding\", b\"\\0\" * auth_padding_length, False)', text
        )
        self.assertIn('old_names=("apfs-preboot-uuid",)', text)
        self.assertIn('(\"boot-objects-path\", b\"/\\0\" + b\"\\0\" * 36, False)', text)
        self.assertIn('parse_device_tree(updated), "/device-tree/chosen"', text)
        self.assertIn('property("boot-objects-path")', text)
        self.assertIn('boot_objects_path.value[:2] != b"/\\0"', text)
        self.assertIn("injected.secure or injected.length != len(auth_payload)", text)
        self.assertIn("exactly 0x80000000 bytes out of bounds", text)
        self.assertIn("item.length != 48", text)
        self.assertIn("exact-span replacement changed the DeviceTree length", text)
        self.assertIn('updated.ljust(device_tree_length, b"\\0")', text)
        self.assertIn("MACVM_RAMDISK_OVERRIDE_IMAGE", text)
        self.assertIn("MACVM_RAMDISK_OVERRIDE_ADDRESS", text)
        self.assertIn("MACVM_TRUSTCACHE_OVERRIDE_IMAGE", text)
        self.assertIn("MACVM_TRUSTCACHE_OVERRIDE_ADDRESS", text)
        self.assertIn("from trustcache_region import (", text)
        self.assertIn("load_region_image", text)
        self.assertIn("parse_trustcache_address", text)
        self.assertIn("validate_trustcache_physical_region", text)
        self.assertIn("regions_overlap", text)
        self.assertIn('allowed_root="/home/macvm/runs/aux-26.6"', text)
        self.assertIn('memory_map_region(logical_tree, "TrustCache")', text)
        self.assertIn("PAGE_SIZE as TRUSTCACHE_PAGE_SIZE", text)
        self.assertIn('memory_map_region(logical_tree, "DeviceTree")', text)
        self.assertIn("bootkc_layout_base - len(trustcache_bytes)", text)
        self.assertIn("trustcache_address - device_tree_length", text)
        self.assertIn("device_tree_physical - relocated_device_tree_physical", text)
        self.assertIn("relocation_distance % TRUSTCACHE_PAGE_SIZE", text)
        self.assertIn(
            'ignored_regions = {"DeviceTree", "TrustCache", "MemoryMapReserved-0"}',
            text,
        )
        self.assertIn(
            "relocated DeviceTree/TrustCache overlaps the BaseSystem RAMDisk", text
        )
        self.assertIn('name="DeviceTree"', text)
        self.assertIn('name="TrustCache"', text)
        self.assertIn("relocated DeviceTree mapping did not persist", text)
        self.assertIn("TrustCache DeviceTree mapping did not persist", text)
        self.assertIn("relocated DeviceTree bytes did not persist", text)
        self.assertIn("TrustCache handoff bytes did not persist", text)
        self.assertIn('boot_args + 0x60, struct.pack("<Q", relocated_device_tree_virtual)', text)
        self.assertIn("relocated BootArgs DeviceTree pointer did not persist", text)
        self.assertIn("trustcache_entries=", text)
        self.assertIn('memory_map_region(logical_tree, "RAMDisk")', text)
        self.assertIn('memory_map_region(logical_tree, "MemoryMapReserved-0")', text)
        self.assertIn("replace_property_value_in_place", text)
        self.assertIn('name="RAMDisk"', text)
        self.assertIn('name="MemoryMapReserved-0"', text)
        self.assertIn('memory_map_region(logical_tree, "BootKC-ro")', text)
        self.assertIn('(\"volume-group-capability\", 0x318442C, bytes.fromhex(\"48200036\")', text)
        self.assertIn('(\"volume-group-validity\", 0x3184434, bytes.fromhex(\"0820c036\")', text)
        self.assertIn('(\"recovery-mount\", 0x318449C, bytes.fromhex(\"b9bef397\")', text)
        self.assertIn('(\"skip-hfs-probe\", 0x329B81C, bytes.fromhex(\"4b99ef97\")', text)
        self.assertIn('bytes.fromhex("c0028052")', text)
        self.assertIn('bytes.fromhex("1f2003d5")', text)
        self.assertIn('bytes.fromhex("b9bef397")', text)
        self.assertIn('bytes.fromhex("00008052")', text)
        self.assertIn("BootKC-ro does not begin with a Mach-O header", text)
        self.assertIn("BootKC patch did not persist", text)
        self.assertIn('b"-bsdmgroot -bsdmgroot-ramdisk\\0"', text)
        self.assertIn("MACVM_TRUSTCACHE_OVERRIDE_IMAGE", text)
        self.assertIn('name="TrustCache"', text)
        self.assertIn("di_root_image_ext reused md0", text)
        self.assertIn("independent RAM block device", text)
        self.assertNotIn("bsdmgpath=/BaseSystem.dmg", text)
        self.assertIn("MACVM_BASESYSTEM_AUTH_INJECTED", text)
        self.assertIn("MACVM_BASESYSTEM_HANDOFF_REFUSED", text)
        self.assertIn("detach", text)

    def test_basesystem_pivot_guard_is_bounded_and_exact(self) -> None:
        text = (
            ROOT / "tools" / "inject_basesystem_auth_and_boot_args_trace_mount.gdb"
        ).read_text(encoding="utf-8")

        # The trace is a copy of the validated Boot22 handoff and must preserve
        # its exact signed-media guards and reviewed BootKC patches.
        self.assertIn("MACVM_BASESYSTEM_AUTH_INJECTED", text)
        self.assertIn('(\"base-system-volume-auth-blob\", auth_payload, False)', text)
        self.assertNotIn('(\"base-system-volume-auth-blob\", auth_container, False)', text)
        self.assertIn('memory_map_region(logical_tree, "BootKC-ro")', text)
        self.assertIn(
            '("skip-hfs-probe", 0x329B81C, bytes.fromhex("4b99ef97")', text
        )
        self.assertIn("MACVM_ALLOW_BASESYSTEM_RW_ROOT", text)
        self.assertIn("allow_basesystem_rw_root", text)
        self.assertIn('"basesystem-rw-mount-flags"', text)
        self.assertIn("0x329B86C", text)
        self.assertIn('bytes.fromhex("27108052")', text)
        self.assertIn('bytes.fromhex("07108052")', text)
        self.assertIn("basesystem_rw_root={int(allow_basesystem_rw_root)}", text)
        self.assertIn("MNT_RDONLY | MNT_DONTBROWSE", text)
        self.assertIn('b"-bsdmgroot -bsdmgroot-ramdisk\\0"', text)
        self.assertIn("MACVM_TRUSTCACHE_OVERRIDE_IMAGE", text)
        self.assertIn("MACVM_TRUSTCACHE_OVERRIDE_ADDRESS", text)
        self.assertIn("load_region_image", text)
        self.assertIn("PAGE_SIZE as TRUSTCACHE_PAGE_SIZE", text)
        self.assertIn("bootkc_layout_base - len(trustcache_bytes)", text)
        self.assertIn("trustcache_address - device_tree_length", text)
        self.assertIn('name="DeviceTree"', text)
        self.assertIn('name="TrustCache"', text)
        self.assertIn("relocated DeviceTree mapping did not persist", text)
        self.assertIn("TrustCache DeviceTree mapping did not persist", text)
        self.assertIn("relocated DeviceTree bytes did not persist", text)
        self.assertIn("TrustCache handoff bytes did not persist", text)
        self.assertIn("relocated BootArgs DeviceTree pointer did not persist", text)
        self.assertIn('MACVM_RECOVERY_VOLUME_UUID', text)
        self.assertIn('str(uuid.UUID(recovery_uuid_literal)).upper()', text)
        self.assertIn('replace_zero_filled_property_with_prefix', text)
        self.assertIn('old_name="host-os-information"', text)
        self.assertIn('new_name="boot-uuid"', text)
        self.assertIn('prefix=recovery_uuid.encode("ascii")', text)
        self.assertIn('boot_uuid_property.value[:36]', text)
        self.assertIn('or any(boot_uuid_property.value[36:])', text)
        self.assertIn('recovery_uuid={recovery_uuid}', text)
        self.assertIn('prebootensurer 753.100.4', text)
        self.assertIn('role Recovery (0x4)', text)

        expected_breakpoints = (
            "hbreak *$macvm_imageboot_apfs_mount_call",
            "hbreak *$macvm_rooted_ramdisk_return",
            "hbreak *$macvm_imageboot_old_root_mount_ready",
            "hbreak *$macvm_imageboot_pivot_return",
        )
        for breakpoint in expected_breakpoints:
            with self.subTest(breakpoint=breakpoint):
                self.assertIn(breakpoint, text)

        for marker in (
            "XNU_BASESYSTEM_APFS_MOUNT_ENTER",
            "XNU_ROOTED_RAMDISK_DECISION",
            "MACVM_PIVOT_GUARD_APPLIED",
            "MACVM_PIVOT_GUARD_REFUSED",
            "MACVM_IMGSRC_STATE_PREPARED",
            "MACVM_IMGSRC_STATE_APPLIED",
            "MACVM_IMGSRC_STATE_REFUSED",
            "MACVM_IMGSRC_STATE_ROLLED_BACK",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("set $macvm_symlink_embedded_trace = 1", text)
        self.assertIn(
            "source /home/macvm/src/macvm/tools/trace_basesystem_symlink_preflight_live.gdb",
            text,
        )
        self.assertIn("set $macvm_symlink_embedded_trace = 0", text)
        self.assertIn("set $macvm_rooted_ramdisk_calls = 0", text)
        self.assertIn("set $macvm_basesystem_pivot_active = 0", text)
        self.assertIn("set $macvm_basesystem_pivot_guard_applied = 0", text)
        self.assertIn(
            "set $macvm_imageboot_apfs_mount_static = 0xfffffe000a29f870", text
        )
        self.assertIn(
            "set $macvm_imageboot_apfs_mount_call = $macvm_imageboot_apfs_mount_static + $macvm_kernelcache_slide",
            text,
        )
        self.assertIn(
            "set $macvm_apfs_static_rooted_ramdisk_return = 0xfffffe00098beed8",
            text,
        )
        self.assertIn("set $macvm_kernelcache_slide = 0x19344000", text)
        self.assertIn(
            "set $macvm_rooted_ramdisk_return = $macvm_apfs_static_rooted_ramdisk_return + $macvm_kernelcache_slide",
            text,
        )
        self.assertEqual(
            0xFFFFFE00098BEED8 + 0x19344000,
            0xFFFFFE0022C02ED8,
        )
        self.assertEqual(
            0xFFFFFE000A29F870 + 0x19344000,
            0xFFFFFE00235E3870,
        )
        self.assertNotIn("0xfffffe0024c02ed8", text)
        self.assertNotIn("hbreak *0xfffffe00235db6a4", text)
        self.assertIn("$macvm_basesystem_pivot_active == 1", text)
        self.assertIn("duplicate-basesystem-apfs-mount", text)
        self.assertIn("basesystem-rooted-ramdisk-was-not-active", text)
        self.assertIn("use-explicit-disk-image=1", text)
        expected_imgsrc_static_addresses = {
            "macvm_imageboot_old_root_mount_ready_static": 0xFFFFFE000A29F91C,
            "macvm_imageboot_pivot_return_static": 0xFFFFFE000A29F940,
            "macvm_rootvnode_static": 0xFFFFFE000A992D78,
            "macvm_imgsrc_rootvnodes_static": 0xFFFFFE000A9881D0,
            "macvm_mountlist_tail_static": 0xFFFFFE000A9881B8,
            "macvm_nummounts_static": 0xFFFFFE000A9BEAB0,
        }
        for name, address in expected_imgsrc_static_addresses.items():
            with self.subTest(name=name):
                self.assertIn(f"set ${name} = 0x{address:016x}", text)
                self.assertIn(
                    f"set ${name.removesuffix('_static')} = ${name} + $macvm_kernelcache_slide",
                    text,
                )
        self.assertIn("from xnu_imgsrc_state import retain_outgoing_root", text)
        self.assertIn(
            "from xnu_imgsrc_state import commit_imgsrc_transfer, rollback_retained_root",
            text,
        )
        self.assertIn("x17 field", text)
        self.assertIn("authenticated by autda into x16", text)
        self.assertIn("def u64_eval(expression):", text)
        self.assertIn("& 0xFFFFFFFFFFFFFFFF", text)
        self.assertIn('x16 = u64_eval("$x16")', text)
        self.assertIn('rootvnode_address = u64_eval("$macvm_rootvnode")', text)
        self.assertIn("outgoing_mount = x16", text)
        self.assertIn('pc = u64_eval("$pc")', text)
        self.assertIn('root_mount_field_address = old_root_vnode + 0xD8', text)
        self.assertIn("root_mnt_value=0x", text)
        self.assertIn('imgsrc_rootvnode=u64_eval("$macvm_imgsrc_rootvnodes")', text)
        self.assertIn('mount_count=u64_eval("$macvm_nummounts")', text)
        self.assertIn('pivot_result = int(gdb.parse_and_eval("$w0"))', text)
        self.assertIn("if pivot_result != 0:", text)
        self.assertIn("if retained is not None and not memory.writes_started:", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        # The APFS guard changes only w0.  The later XNU transaction must flow
        # through the validated helper rather than a raw GDB pointer shortcut.
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set $x19", text)
        self.assertNotIn("set *(unsigned", text)
        self.assertNotIn("set $w27", text)
        self.assertNotIn("set *(unsigned long *)$macvm_imgsrc_rootvnodes", text)
        self.assertIn("set $w0 = 0", text)

    def test_basesystem_symlink_live_trace_is_late_attach_observe_only(self) -> None:
        text = (ROOT / "tools" / "trace_basesystem_symlink_live.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("target remote 127.0.0.1:12345", text)
        self.assertIn("post-GDB handoff script detaches", text)
        self.assertIn("set $macvm_kernelcache_slide = 0x19344000", text)
        self.assertIn("set $macvm_symlink_trace_limit = 8", text)
        self.assertIn("MACVM_SYMLINK_LIVE_TRACE_ARMED", text)
        self.assertIn("def _macvm_emit_symlink_trace(marker):", text)
        self.assertIn("name_pointer = _macvm_read_u64(cnp + 0x28)", text)
        self.assertIn("name_length = min(_macvm_read_u32(cnp + 0x30), 256)", text)
        self.assertIn("target_pointer = _macvm_read_u64(args + 0x28)", text)
        self.assertNotIn("finish", text)

        expected_breakpoints = (
            "hbreak *$macvm_vnop_symlink_primary",
            "hbreak *$macvm_vnop_symlink_secondary",
            "hbreak *$macvm_apfs_vnop_symlink",
            "hbreak *$macvm_apfs_vnop_symlink_return_fast",
            "hbreak *$macvm_apfs_vnop_symlink_return_slow",
        )
        for breakpoint in expected_breakpoints:
            with self.subTest(breakpoint=breakpoint):
                self.assertIn(breakpoint, text)

        expected_symlink_static_addresses = {
            "macvm_vnop_symlink_primary_static": 0xFFFFFE000884E174,
            "macvm_vnop_symlink_secondary_static": 0xFFFFFE0008869948,
            "macvm_apfs_vnop_symlink_static": 0xFFFFFE00098EEC34,
            "macvm_apfs_vnop_symlink_return_fast_static": 0xFFFFFE00098EED1C,
            "macvm_apfs_vnop_symlink_return_slow_static": 0xFFFFFE00098EF3E4,
        }
        for name, address in expected_symlink_static_addresses.items():
            with self.subTest(name=name):
                self.assertIn(f"set ${name} = 0x{address:016x}", text)
                self.assertIn(
                    f"set ${name.removesuffix('_static')} = ${name} + $macvm_kernelcache_slide",
                    text,
                )

        for marker in (
            "MACVM_SYMLINK_VNOP_PRIMARY_ENTER",
            "MACVM_SYMLINK_VNOP_SECONDARY_ENTER",
            "MACVM_SYMLINK_APFS_ENTER",
            "MACVM_SYMLINK_APFS_RETURN",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_basesystem_symlink_preflight_trace_classifies_pre_vnop_eperm(self) -> None:
        text = (
            ROOT / "tools" / "trace_basesystem_symlink_preflight_live.gdb"
        ).read_text(encoding="utf-8")

        self.assertIn("target remote 127.0.0.1:12345", text)
        self.assertIn("after MACVM_IMGSRC_STATE_APPLIED", text)
        self.assertIn("macvm_symlink_embedded_trace", text)
        self.assertIn("if $macvm_symlink_embedded_trace == 0", text)
        self.assertIn(
            'gdb.set_convenience_variable("macvm_symlink_embedded_trace", 0)',
            text,
        )
        self.assertIn("set $macvm_kernelcache_slide = 0x19344000", text)
        self.assertIn("set $macvm_symlink_trace_limit = 8192", text)
        self.assertIn("MACVM_SYMLINK_PREFLIGHT_TRACE_ARMED", text)
        self.assertIn("def _macvm_begin_symlink_syscall(kind):", text)
        self.assertIn("def _macvm_read_proc_identity(proc):", text)
        self.assertIn("def _macvm_read_u8(address):", text)
        self.assertIn("def _macvm_try_read_u8(address):", text)
        self.assertIn("def _macvm_is_target_symlink_process(process_name):", text)
        self.assertIn("def _macvm_trace_mac_create_entry():", text)
        self.assertIn("def _macvm_trace_mac_create_hook():", text)
        self.assertIn("def _macvm_set_focus_breakpoints(enabled):", text)
        self.assertIn("def _macvm_start_focus(origin, active_index, name, cred=0, dvp=0, cnp=0):", text)
        self.assertIn("def _macvm_clear_focus(reason):", text)
        self.assertIn("def _macvm_request_detach_after_packageslink(reason):", text)
        self.assertIn("def _macvm_focus_cred_matches(cred):", text)
        self.assertIn("def _macvm_trace_symlinkat_checkpoint(marker, *", text)
        self.assertIn("def _macvm_trace_sandbox_eval_enter():", text)
        self.assertIn("def _macvm_trace_sandbox_rootless_enter():", text)
        self.assertIn("def _macvm_trace_sandbox_rootless_return():", text)
        self.assertIn("def _macvm_trace_sandbox_eval_result():", text)
        self.assertIn("def _macvm_trace_mac_create_policy_step_return(stage):", text)
        self.assertIn("def _macvm_trace_mac_create_final_return():", text)
        self.assertIn("def _macvm_mark_packageslink_context_confirmed(reason):", text)
        self.assertIn("def _macvm_policy_summary(mpc):", text)
        self.assertIn("def _macvm_mac_create_step_is_packageslink():", text)
        self.assertIn("def _macvm_filter_context_summary(context):", text)
        self.assertIn("set $macvm_symlink_focus_thread = 0", text)
        self.assertIn("set $macvm_symlink_focus_cred = 0", text)
        self.assertIn("set $macvm_symlink_packageslink_context_confirmed = 0", text)
        self.assertIn("set $macvm_symlink_apfs_rofs_mount = 0", text)
        self.assertIn("set $macvm_symlink_apfs_rofs_tx_obj = 0", text)
        self.assertIn("set $macvm_allow_packageslink_symlink = 0", text)
        self.assertIn("set $macvm_allow_packageslink_rofs_bypass = 0", text)
        self.assertIn("set $macvm_allow_packageslink_apfs_rofs_bypass = 0", text)
        self.assertIn("set $macvm_symlink_detach_after_packageslink = 0", text)
        self.assertIn("set $macvm_symlink_detach_requested = 0", text)
        self.assertIn("MACVM_ALLOW_PACKAGESLINK_SYMLINK", text)
        self.assertIn("MACVM_ALLOW_PACKAGESLINK_ROFS_BYPASS", text)
        self.assertIn("MACVM_ALLOW_PACKAGESLINK_APFS_ROFS_BYPASS", text)
        self.assertIn("MACVM_DETACH_AFTER_PACKAGESLINK", text)
        self.assertIn("def _macvm_current_thread_global_num():", text)
        self.assertIn("def _macvm_focus_thread_matches():", text)
        self.assertIn("hbreak *$macvm_mac_create", text)
        self.assertIn("def _macvm_trace_static_return(marker, *, result_is_errno=True", text)
        self.assertIn("def _macvm_kauth_vnode_action_names(action):", text)
        self.assertIn("def _macvm_vnode_summary(vp):", text)
        self.assertIn("def _macvm_packageslink_allow_enabled():", text)
        self.assertIn(
            "def _macvm_sandbox_context_is_packageslink_symlink_create(context):",
            text,
        )
        self.assertIn("macvm_bp_mac_create", text)
        self.assertIn("macvm_bp_mac_create_policy_return", text)
        self.assertIn("macvm_bp_mac_create_cond_policy_return", text)
        self.assertIn("macvm_bp_mac_create_final_return", text)
        self.assertIn("macvm_bp_sandbox_evaluate_internal", text)
        self.assertIn("macvm_bp_sandbox_apply_rootless_modifier", text)
        self.assertIn("macvm_bp_sandbox_apply_rootless_return", text)
        self.assertIn("macvm_bp_sandbox_hook_create_eval_return", text)
        self.assertIn("macvm_bp_symlinkat_mac_create_return", text)
        self.assertIn("macvm_bp_symlinkat_vnode_authorize_return", text)
        self.assertIn("macvm_bp_symlinkat_vnop_symlink_return", text)
        self.assertIn("macvm_bp_symlinkat_common_result", text)
        self.assertIn("macvm_bp_vnode_authorize_rofs_branch", text)
        self.assertIn("hbreak *$macvm_vnode_authorize_rofs_branch", text)
        self.assertIn("macvm_bp_apfs_vnop_symlink_rofs_branch", text)
        self.assertIn("hbreak *$macvm_apfs_vnop_symlink_rofs_branch", text)
        self.assertIn("python _macvm_toggle_breakpoints(_macvm_optional_breakpoint_names(), False)", text)
        self.assertIn("_macvm_toggle_breakpoints(_macvm_optional_breakpoint_names(), enabled)", text)
        self.assertIn(
            '_macvm_set_conv("macvm_symlink_focus_thread", _macvm_current_thread_global_num())',
            text,
        )
        self.assertIn('_macvm_set_conv("macvm_symlink_focus_cred", cred)', text)
        self.assertIn("if not _macvm_focus_thread_matches():", text)
        self.assertIn("_macvm_focus_cred_matches", text)
        self.assertIn("python _macvm_set_focus_breakpoints(False)", text)
        self.assertIn("set $macvm_proc_p_comm_offset = 0x5cc", text)
        self.assertIn("set $macvm_proc_p_name_offset = 0x5dd", text)
        self.assertIn("set $macvm_symlink_mac_create_hook_trace_limit = 64", text)
        self.assertIn('"PackagesLink" in link', text)
        self.assertIn('"Image Volume/Packages" in target', text)
        self.assertIn('"PackagesLink" in name', text)
        self.assertIn('"mountrecursive"', text)
        self.assertIn("should_log = focus or index <= _macvm_conv_int", text)
        self.assertIn("process_focus = _macvm_is_target_symlink_process(process_name)", text)
        self.assertIn("focus_was_active = _macvm_conv_int(\"macvm_symlink_focus\") != 0", text)
        self.assertIn("if not focus_was_active:", text)
        self.assertIn("path_probe = process_focus or index <= _macvm_conv_int", text)
        self.assertIn('target = _macvm_try_read_c_string(fields["target_ptr"]) if path_probe else "<skipped>"', text)
        self.assertIn('link = _macvm_try_read_c_string(fields["link_ptr"]) if path_probe else "<skipped>"', text)

        expected_static_addresses = {
            "macvm_syscall_symlink_static": 0xFFFFFE0009E90FC8,
            "macvm_syscall_symlinkat_static": 0xFFFFFE0009E9147C,
            "macvm_mac_create_static": 0xFFFFFE000A508E08,
            "macvm_hook_vnode_check_create_static": 0xFFFFFE00096E2034,
            "macvm_vnode_authorize_static": 0xFFFFFE0009E80594,
            "macvm_vnode_authattr_new_static": 0xFFFFFE0009E8158C,
            "macvm_proc_use_alternative_symlink_ea_static": 0xFFFFFE000A1E3D7C,
            "macvm_vnop_symlink_primary_static": 0xFFFFFE000884E174,
            "macvm_vnop_symlink_secondary_static": 0xFFFFFE0008869948,
            "macvm_apfs_vnop_symlink_static": 0xFFFFFE00098EEC34,
            "macvm_apfs_vnop_symlink_rofs_branch_static": 0xFFFFFE00098EECF8,
            "macvm_apfs_vnop_symlink_rofs_fallthrough_static": 0xFFFFFE00098EED20,
            "macvm_apfs_vnop_symlink_return_fast_static": 0xFFFFFE00098EED1C,
            "macvm_apfs_vnop_symlink_return_slow_static": 0xFFFFFE00098EF3E4,
            "macvm_mac_create_policy_return_static": 0xFFFFFE000A508EE0,
            "macvm_mac_create_cond_policy_return_static": 0xFFFFFE000A5090D8,
            "macvm_mac_create_final_return_static": 0xFFFFFE000A509038,
            "macvm_altlink_return_static": 0xFFFFFE00098EE184,
            "macvm_vnode_authorize_rofs_branch_static": 0xFFFFFE0009E7EB4C,
            "macvm_vnode_authorize_rofs_fallthrough_static": 0xFFFFFE0009E7E98C,
            "macvm_vnode_authorize_write_extattr_return_static": 0xFFFFFE0009718F34,
            "macvm_symlinkat_mac_create_return_static": 0xFFFFFE0009E911D4,
            "macvm_symlinkat_vnode_authorize_return_static": 0xFFFFFE0009E911F8,
            "macvm_symlinkat_vnop_symlink_return_static": 0xFFFFFE0009E9126C,
            "macvm_symlinkat_common_result_static": 0xFFFFFE0009E913E0,
            "macvm_sandbox_evaluate_internal_static": 0xFFFFFE00096F2A80,
            "macvm_sandbox_apply_rootless_modifier_static": 0xFFFFFE00097188E8,
            "macvm_sandbox_apply_rootless_return_static": 0xFFFFFE00096F2BEC,
            "macvm_sandbox_hook_create_eval_return_static": 0xFFFFFE00096E2200,
        }
        for name, address in expected_static_addresses.items():
            with self.subTest(name=name):
                self.assertIn(f"set ${name} = 0x{address:016x}", text)
                self.assertIn(
                    f"set ${name.removesuffix('_static')} = ${name} + $macvm_kernelcache_slide",
                    text,
                )

        for marker in (
            "MACVM_SYMLINK_SYSCALL_ENTER",
            "MACVM_SYMLINK_FOCUS_START",
            "MACVM_SYMLINK_FOCUS_CLEAR",
            "MACVM_SYMLINK_FOCUS_IGNORED",
            "MACVM_SYMLINK_FOCUS_BREAKPOINTS",
            "MACVM_SYMLINK_PACKAGESLINK_CONTEXT_CONFIRMED",
            "MACVM_SYMLINK_MAC_CREATE_ENTER",
            "MACVM_SYMLINK_MAC_CREATE_HOOK_ENTER",
            "MACVM_SYMLINK_MAC_CREATE_POLICY_RETURN",
            "MACVM_SYMLINK_MAC_CREATE_POLICY_ALLOW_APPLIED",
            "MACVM_SYMLINK_MAC_CREATE_FINAL_RETURN",
            "MACVM_SYMLINK_MAC_CREATE_FINAL_ALLOW_APPLIED",
            "MACVM_SYMLINK_SANDBOX_EVAL_ENTER",
            "MACVM_SYMLINK_SANDBOX_EVAL_RETURN",
            "MACVM_SYMLINK_PACKAGESLINK_ALLOW_APPLIED",
            "MACVM_SYMLINK_ROOTLESS_MODIFIER_ENTER",
            "MACVM_SYMLINK_ROOTLESS_MODIFIER_RETURN",
            "MACVM_SYMLINK_SYMLINKAT_MAC_CREATE_RETURN",
            "MACVM_SYMLINK_SYMLINKAT_VNODE_AUTHORIZE_RETURN",
            "MACVM_SYMLINK_SYMLINKAT_VNOP_SYMLINK_RETURN",
            "MACVM_SYMLINK_SYMLINKAT_COMMON_RESULT",
            "MACVM_SYMLINK_VNODE_AUTHORIZE_ENTER",
            "MACVM_SYMLINK_VNODE_AUTHORIZE_ROFS_BRANCH",
            "MACVM_SYMLINK_VNODE_AUTHORIZE_WRITE_EXTATTR_RETURN",
            "MACVM_SYMLINK_VNODE_AUTHATTR_ENTER",
            "MACVM_SYMLINK_ALTLINK_ENTER",
            "MACVM_SYMLINK_ALTLINK_RETURN",
            "MACVM_SYMLINK_VNOP_PRIMARY_ENTER",
            "MACVM_SYMLINK_VNOP_PRIMARY_RETURN",
            "MACVM_SYMLINK_VNOP_SECONDARY_ENTER",
            "MACVM_SYMLINK_VNOP_SECONDARY_RETURN",
            "MACVM_SYMLINK_APFS_ENTER",
            "MACVM_SYMLINK_APFS_RETURN",
            "MACVM_SYMLINK_APFS_ROFS_BRANCH",
            "MACVM_SYMLINK_DETACH_AFTER_PACKAGESLINK",
            "MACVM_SYMLINK_APFS_RETURN_FAST",
            "MACVM_SYMLINK_APFS_RETURN_SLOW",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("target={target!r}", text)
        self.assertIn("link={link!r}", text)
        self.assertIn("p_comm={p_comm!r}", text)
        self.assertIn("p_name={p_name!r}", text)
        self.assertIn("process = f\" p_comm={p_comm!r} p_name={p_name!r}\"", text)
        self.assertIn('"WRITE_EXTATTRIBUTES"', text)
        self.assertIn("action={_macvm_kauth_vnode_action_names(action)}", text)
        self.assertIn("result_is_errno=False", text)
        self.assertIn("name={name!r}", text)
        self.assertIn("lr=0x{_macvm_u64('$x30'):x}", text)
        self.assertIn("kind != 1", text)
        self.assertIn("va_type != 5", text)
        self.assertIn('name != "PackagesLink"', text)
        self.assertIn('"PackagesLink" not in _macvm_symlink_focus_name', text)
        self.assertIn('gdb.execute("set $x0 = 0", to_string=True)', text)
        self.assertIn('gdb.execute("set $x23 = 0", to_string=True)', text)
        self.assertIn("allow_enabled={1 if allow_enabled else 0}", text)
        self.assertIn("allow_applied={allow_applied}", text)
        self.assertIn("original_x0=0x{original_x0:x}", text)
        self.assertIn("aggregate_before={aggregate_before}", text)
        self.assertIn("policy_name={name!r}", text)
        self.assertIn("policy_fullname={fullname!r}", text)
        self.assertIn("policy_ops=0x{ops:x}", text)
        self.assertIn("hook=0x{hook:x}", text)
        self.assertIn("stage={stage}", text)
        self.assertIn("context_reason={context_reason!r}", text)
        self.assertIn(
            '_macvm_log_ignored_focus("MACVM_SYMLINK_SANDBOX_EVAL_RETURN", "no-pending-sandbox-eval")',
            text,
        )
        self.assertIn("vp + 0x71", text)
        self.assertIn("vp + 0xB8", text)
        self.assertIn("vp + 0xD8", text)
        self.assertIn("mount + 0x70", text)
        self.assertIn("mount + 0x74", text)
        self.assertIn("mnt_rdonly={1 if (mnt_flag is not None and (mnt_flag & 1)) else 0}", text)
        self.assertIn("authenticated_mount=0x{mount:x}", text)
        self.assertIn("resume_pc=0x{resume_pc:x}", text)
        self.assertIn("new_mnt_flag=0x{new_mnt_flag if new_mnt_flag is not None else 0:x}", text)
        self.assertIn("allow_enabled={1 if allow_enabled else 0}", text)
        self.assertIn("allow_reason={allow_reason!r}", text)
        self.assertIn('"PackagesLink" not in _macvm_symlink_focus_name', text)
        self.assertIn('macvm_symlink_packageslink_context_confirmed") == 0', text)
        self.assertIn("(action & 0x4) == 0", text)
        self.assertIn("v_type != 2", text)
        self.assertNotIn('v_name != "Installation"', text)
        self.assertIn("packageslink-context-not-confirmed", text)
        self.assertIn("mnt-rdonly-absent", text)
        self.assertIn("packageslink-focused-mnt-rdonly", text)
        self.assertIn("context_confirmed={_macvm_conv_int('macvm_symlink_packageslink_context_confirmed')}", text)
        self.assertIn("focus_name={_macvm_symlink_focus_name!r}", text)
        self.assertIn("_macvm_memory().write_memory(mount + 0x70", text)
        self.assertIn("set $pc = 0x{_macvm_conv_int('macvm_vnode_authorize_rofs_fallthrough'):x}", text)
        self.assertIn("def _macvm_decode_vnop_symlink_args(args):", text)
        self.assertIn("def _macvm_trace_apfs_rofs_branch():", text)
        self.assertIn("args = _macvm_u64(\"$x19\")", text)
        self.assertIn("apfs_mount = _macvm_u64(\"$x20\")", text)
        self.assertIn("apfs_node = _macvm_u64(\"$x21\")", text)
        self.assertIn("apfs_mount + 0x35c", text)
        self.assertIn("apfs_mount + 0xD0", text)
        self.assertIn("tx_obj + 0x15B", text)
        self.assertIn("apfs_node + 0x9d", text)
        self.assertIn("decoded[\"name\"] != \"PackagesLink\"", text)
        self.assertIn('"Image Volume/Packages" not in decoded["target"]', text)
        self.assertIn("apfs-rofs-condition-absent", text)
        self.assertIn("packageslink-apfs-rofs-state-cleared", text)
        self.assertIn("_macvm_memory().write_memory(\n                    apfs_mount + 0x35c", text)
        self.assertIn("_macvm_memory().write_memory(\n                    tx_obj + 0x15B", text)
        self.assertIn("_macvm_memory().write_memory(\n                    apfs_node + 0x9d", text)
        self.assertIn('_macvm_set_conv("macvm_symlink_apfs_rofs_mount", apfs_mount)', text)
        self.assertIn('_macvm_set_conv("macvm_symlink_apfs_rofs_tx_obj", tx_obj or 0)', text)
        self.assertIn('_macvm_request_detach_after_packageslink(f"{marker}:result={result}")', text)
        self.assertIn('MACVM_SYMLINK_PACKAGESLINK_FINAL success=', text)
        self.assertIn('MACVM_DETACH_AFTER_PACKAGESLINK_RESULT', text)
        self.assertIn('if clear_always or (clear_on_error and result != 0 and not _macvm_wait_for_packageslink_final_result()):', text)
        self.assertIn('"MACVM_SYMLINK_SYMLINKAT_VNOP_SYMLINK_RETURN"', text)
        self.assertIn('"MACVM_SYMLINK_SYMLINKAT_COMMON_RESULT"', text)
        self.assertIn("new_apfs_mount_ro=0x{new_apfs_mount_ro if new_apfs_mount_ro is not None else 0:x}", text)
        self.assertIn("tx_ro_byte=0x{tx_ro_byte if tx_ro_byte is not None else 0:x}", text)
        self.assertIn("new_tx_ro_byte=0x{new_tx_ro_byte if new_tx_ro_byte is not None else 0:x}", text)
        self.assertIn("new_apfs_node_flags=0x{new_apfs_node_flags if new_apfs_node_flags is not None else 0:x}", text)
        self.assertIn("set $pc = 0x{_macvm_conv_int('macvm_apfs_vnop_symlink_rofs_fallthrough'):x}", text)
        self.assertIn("if $macvm_symlink_detach_requested != 0", text)
        self.assertIn("apfs_rofs_branch=%#lx", text)
        self.assertIn("apfs_rofs_fallthrough=%#lx", text)
        self.assertIn('"MACVM_SYMLINK_VNODE_AUTHORIZE_ENTER",', text)
        self.assertIn('"MACVM_SYMLINK_VNODE_AUTHATTR_ENTER",', text)
        self.assertIn("if not _macvm_focus_thread_matches():", text)
        self.assertIn("mac_create=%#lx", text)
        self.assertIn("sandbox_eval=%#lx", text)
        self.assertIn("rootless_modifier=%#lx", text)
        self.assertIn("hook_eval_return=%#lx", text)
        self.assertIn("symlinkat_mac_return=%#lx", text)
        self.assertIn("symlinkat_common=%#lx", text)
        self.assertNotIn("or process_focus", text)
        self.assertNotIn("_macvm_finish_symlink_syscall", text)
        self.assertNotIn("gdb.FinishBreakpoint", text)
        self.assertNotIn("type=gdb.BP_HARDWARE_BREAKPOINT", text)
        self.assertNotIn("class _MacvmReturnPcProbe", text)
        self.assertNotIn("_macvm_install_return_pc_probe", text)
        self.assertNotIn("MACVM_SYMLINK_RETURN_PROBE_FAILED", text)
        self.assertNotIn("macvm_syscall_symlink_return", text)
        self.assertNotIn("macvm_syscall_symlinkat_return", text)
        self.assertNotRegex(text, r"(?m)^\s*finish\s*$")
        self.assertNotIn("set $w0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_proc_name_offset_probe_is_read_only_and_self_detaching(self) -> None:
        text = (
            ROOT / "tools" / "probe_proc_name_offsets_live.gdb"
        ).read_text(encoding="utf-8")

        self.assertIn("target remote 127.0.0.1:12345", text)
        self.assertIn("MACVM_PROC_NAME_PROBE_BEGIN", text)
        self.assertIn("MACVM_PROC_NAME_CANDIDATE", text)
        self.assertIn("MACVM_PROC_NAME_PROBE_END", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("write_memory", text)
        self.assertNotIn("set $w0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_allproc_name_probe_is_read_only_and_self_detaching(self) -> None:
        text = (
            ROOT / "tools" / "probe_allproc_names_live.gdb"
        ).read_text(encoding="utf-8")

        self.assertIn('os.environ.get("MACVM_GDB_PORT", "12345")', text)
        self.assertIn('target remote 127.0.0.1:{port}', text)
        self.assertIn("KERNPROC_STATIC = 0xFFFFFE0007916C28", text)
        self.assertIn("PROC_P_COMM_OFFSET = 0x5CC", text)
        self.assertIn("PROC_P_NAME_OFFSET = 0x5DD", text)
        self.assertIn("MACVM_ALLPROC_PROBE_BEGIN", text)
        self.assertIn("MACVM_ALLPROC_ENTRY", text)
        self.assertIn("MACVM_ALLPROC_PROBE_END", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("proc_find(", text)
        self.assertNotIn("write_memory", text)
        self.assertNotIn("set $w0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_svc7_step_trace_is_bounded_and_self_detaching(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_svc7_step.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("set $svc7_step_limit = 96", text)
        self.assertIn("break *0x70087db8", text)
        self.assertIn("IBEC_BOOTX_SVC7_STEP_ENTER", text)
        self.assertIn("IBEC_BOOTX_SVC7_STEP index=%u", text)
        self.assertIn("while $svc7_step_count < $svc7_step_limit", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)

    def test_bootx_svc7_switch_trace_captures_callback_selection(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_svc7_switch.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_SVC7_SWITCH_SVC7",
            "IBEC_BOOTX_SVC7_SWITCH_CASE7_DISPATCH",
            "IBEC_BOOTX_SVC7_SWITCH_CASE7_ENTER",
            "IBEC_BOOTX_SVC7_SWITCH_KIND_COMPARE",
            "IBEC_BOOTX_SVC7_SWITCH_ACCEPTED",
            "IBEC_BOOTX_SVC7_SWITCH_STAGE_SWITCH_CALL",
            "IBEC_BOOTX_SVC7_SWITCH_STAGE_SWITCH_ENTER",
            "IBEC_BOOTX_SVC7_SWITCH_READY_CHECK_RETURN",
            "IBEC_BOOTX_SVC7_SWITCH_CALLBACK_CALL",
            "IBEC_BOOTX_SVC7_SWITCH_CALLBACK_RETURNED",
            "IBEC_BOOTX_SVC7_SWITCH_EXCEPTION",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("set $svc7_stage_callback = $x24", text)
        self.assertIn("break *0x700d4484", text)
        self.assertIn("break *0x700d6298", text)
        self.assertIn("break *0x700d6674", text)
        self.assertIn("break *0x70087c8c", text)

    def test_bootx_callback_step_trace_is_bounded_and_diagnostic_only(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_callback_step.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("set $callback_step_limit = 160", text)
        self.assertIn("break *0x70087c8c", text)
        self.assertIn("IBEC_BOOTX_CALLBACK_STEP_CALL", text)
        self.assertIn("IBEC_BOOTX_CALLBACK_STEP index=%u", text)
        self.assertIn("while $callback_step_count < $callback_step_limit", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_callback_disasm_trace_dumps_trampoline_without_stepping(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_callback_disasm.gdb").read_text(
            encoding="utf-8"
        )

        self.assertIn("break *0x70087c8c", text)
        self.assertIn("IBEC_BOOTX_CALLBACK_DISASM_CALL", text)
        self.assertIn("x/192i $callback_disasm_target", text)
        self.assertIn("set $callback_disasm_literal_base = $callback_disasm_target + 0x240", text)
        self.assertIn("x/32gx $callback_disasm_literal_base", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("\nsi\n", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_entry_trace_follows_trampoline_ret_only(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_kernel_entry.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_KERNEL_ENTRY_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_ENTRY_ADVANCE_TO_TRAMPOLINE_RET",
            "IBEC_BOOTX_KERNEL_ENTRY_TRAMPOLINE_RET",
            "IBEC_BOOTX_KERNEL_ENTRY_AFTER_RET",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("break *0x70087c8c", text)
        self.assertIn("set $kernel_entry_trace_entry = $x0", text)
        self.assertIn("set $kernel_entry_trace_boot_args = $x1", text)
        self.assertIn("set $kernel_entry_trace_ret = $kernel_entry_trace_trampoline + 0x2b8", text)
        self.assertIn("advance *$kernel_entry_trace_ret", text)
        self.assertEqual(text.count("\n    si\n"), 1)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_early_step_trace_is_bounded(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_kernel_early_step.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_KERNEL_EARLY_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_EARLY_TRAMPOLINE_RET",
            "IBEC_BOOTX_KERNEL_EARLY_ENTRY",
            "IBEC_BOOTX_KERNEL_EARLY_BRANCH_TARGET",
            "IBEC_BOOTX_KERNEL_EARLY_STEP",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("set $kernel_early_step_limit = 512", text)
        self.assertIn("advance *$kernel_early_ret", text)
        self.assertGreaterEqual(text.count("\n    si\n"), 2)
        self.assertIn("while $kernel_early_step_count < $kernel_early_step_limit", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_landmarks_trace_skips_known_long_loops(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_kernel_landmarks.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_KERNEL_LANDMARKS_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_LANDMARKS_TRAMPOLINE_RET",
            "IBEC_BOOTX_KERNEL_LANDMARKS_ENTRY",
            "IBEC_BOOTX_KERNEL_LANDMARKS_BRANCH_TARGET",
            "IBEC_BOOTX_KERNEL_LANDMARKS_ZERO_TABLE_DONE",
            "IBEC_BOOTX_KERNEL_LANDMARKS_ASLR_DONE",
            "IBEC_BOOTX_KERNEL_LANDMARKS_MAP1_DONE",
            "IBEC_BOOTX_KERNEL_LANDMARKS_STATIC_REGION_SPIN",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("advance *0x76f5c104", text)
        self.assertIn("while $pc != 0x76f5c13c && $kernel_landmarks_guard < 48", text)
        self.assertIn("if $pc == 0x76f5c11c", text)
        self.assertIn("advance *0x76f5c1f4", text)
        self.assertIn("x/384i $pc", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_hvc_trace_captures_first_hypervisor_call(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_kernel_hvc.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_KERNEL_HVC_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_HVC_BRANCH_TARGET",
            "IBEC_BOOTX_KERNEL_HVC_ZERO_TABLE_DONE",
            "IBEC_BOOTX_KERNEL_HVC_ASLR_DONE",
            "IBEC_BOOTX_KERNEL_HVC_MAP1_DONE",
            "IBEC_BOOTX_KERNEL_HVC_BEFORE",
            "IBEC_BOOTX_KERNEL_HVC_AFTER",
            "IBEC_BOOTX_KERNEL_HVC_AFTER_CBNZ",
            "IBEC_BOOTX_KERNEL_HVC_NONZERO_RETURN_SPIN",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("advance *0x76f5c104", text)
        self.assertIn("advance *0x76f5c13c", text)
        self.assertIn("advance *0x76f5c1f4", text)
        self.assertIn("advance *0x76f5c33c", text)
        self.assertIn("if $pc == 0x76f5c340", text)
        self.assertGreaterEqual(
            sum(1 for line in text.splitlines() if line.strip() == "si"),
            4,
        )
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_mmu_ret_trace_follows_hvc_and_boot_stub_return(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_kernel_mmu_ret.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_KERNEL_MMU_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_MMU_BRANCH_TARGET",
            "IBEC_BOOTX_KERNEL_MMU_HVC_BEFORE",
            "IBEC_BOOTX_KERNEL_MMU_HVC_AFTER",
            "IBEC_BOOTX_KERNEL_MMU_AFTER_CBNZ",
            "IBEC_BOOTX_KERNEL_MMU_BOOT_STUB_RET",
            "IBEC_BOOTX_KERNEL_MMU_AFTER_BOOT_STUB_RET",
            "IBEC_BOOTX_KERNEL_MMU_STEP",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("set $kernel_mmu_step_limit = 96", text)
        self.assertIn("advance *0x76f5c104", text)
        self.assertIn("advance *0x76f5c13c", text)
        self.assertIn("advance *0x76f5c1f4", text)
        self.assertIn("advance *0x76f5c33c", text)
        self.assertIn("advance *0x76f5c384", text)
        self.assertIn("while $kernel_mmu_step_count < $kernel_mmu_step_limit", text)
        self.assertGreaterEqual(
            sum(1 for line in text.splitlines() if line.strip() == "si"),
            5,
        )
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_high_disasm_trace_dumps_mmu_enabled_xnu_code(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_kernel_high_disasm.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_KERNEL_HIGH_DISASM_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_HIGH_DISASM_BOOT_STUB_RET",
            "IBEC_BOOTX_KERNEL_HIGH_DISASM_AFTER_BOOT_STUB_RET",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("set $kernel_high_slide = $x22 - $x23", text)
        self.assertIn("set $kernel_high_low_pc = $pc - $kernel_high_slide", text)
        self.assertIn("x/256i $pc", text)
        self.assertIn("advance *0x76f5c384", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_pac_hvc_trace_captures_high_vmapple_pac_calls(self) -> None:
        text = (ROOT / "tools" / "trace_ibec_bootx_kernel_pac_hvc.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "IBEC_BOOTX_KERNEL_PAC_HVC_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_PAC_HVC_BOOTSTRAP_BEFORE",
            "IBEC_BOOTX_KERNEL_PAC_HVC_BOOTSTRAP_AFTER",
            "IBEC_BOOTX_KERNEL_PAC_HVC_BOOTSTRAP_AFTER_CBNZ",
            "IBEC_BOOTX_KERNEL_PAC_HVC_HIGH_ENTRY",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_BEFORE",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_AFTER",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_AFTER_CBNZ",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_1_NONZERO_RETURN_SPIN",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_BEFORE",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_AFTER",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_AFTER_CBNZ",
            "IBEC_BOOTX_KERNEL_PAC_HVC_GET_DEFAULT_2_NONZERO_RETURN_SPIN",
            "IBEC_BOOTX_KERNEL_PAC_HVC_AFTER_WINDOW",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("set $kernel_pac_hvc_get_default_1 = $kernel_pac_slide + 0x778884c0", text)
        self.assertIn("set $kernel_pac_hvc_get_default_2 = $kernel_pac_slide + 0x77888504", text)
        self.assertIn("set $kernel_pac_after_hvc_window = $kernel_pac_slide + 0x77888514", text)
        self.assertIn("advance *$kernel_pac_hvc_get_default_1", text)
        self.assertIn("advance *$kernel_pac_hvc_get_default_2", text)
        self.assertIn("advance *$kernel_pac_after_hvc_window", text)
        self.assertIn("x4=0x%lx", text)
        self.assertGreaterEqual(
            sum(1 for line in text.splitlines() if line.strip() == "si"),
            8,
        )
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_high_milestones_trace_locates_pre_pac_control_flow(self) -> None:
        text = (
            ROOT / "tools" / "trace_ibec_bootx_kernel_high_milestones.gdb"
        ).read_text(encoding="utf-8")

        for marker in (
            "IBEC_BOOTX_KERNEL_HIGH_MS_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_HIGH_MS_BOOTSTRAP_HVC_BEFORE",
            "IBEC_BOOTX_KERNEL_HIGH_MS_BOOTSTRAP_HVC_AFTER",
            "IBEC_BOOTX_KERNEL_HIGH_MS_ENTRY",
            "IBEC_BOOTX_KERNEL_HIGH_MS_REBASE_BRANCH",
            "IBEC_BOOTX_KERNEL_HIGH_MS_REBASE_DONE",
            "IBEC_BOOTX_KERNEL_HIGH_MS_STATIC_BRANCH",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PLATFORM_RANGE_DONE",
            "IBEC_BOOTX_KERNEL_HIGH_MS_INITCALL_LOOP",
            "IBEC_BOOTX_KERNEL_HIGH_MS_INITCALL_DONE",
            "IBEC_BOOTX_KERNEL_HIGH_MS_BOOTARGS_COPY_DONE",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PRE_PAC_DEFAULTS",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_1_BEFORE",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_1_AFTER",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_1_AFTER_CBNZ",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_2_BEFORE",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_2_AFTER",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_GET_DEFAULT_2_AFTER_CBNZ",
            "IBEC_BOOTX_KERNEL_HIGH_MS_PAC_DEFAULTS_DONE",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        for address in (
            "0xfffffe00238881f4",
            "0xfffffe00238882ec",
            "0xfffffe0023888304",
            "0xfffffe00238883b8",
            "0xfffffe002388842c",
            "0xfffffe0023888444",
            "0xfffffe0023888468",
            "0xfffffe0023888490",
            "0xfffffe00238884c0",
            "0xfffffe0023888504",
            "0xfffffe0023888514",
        ):
            with self.subTest(address=address):
                self.assertIn(f"break *{address}", text)

        self.assertIn("advance *0x76f5c384", text)
        self.assertIn("set $kernel_high_ms_slide = $x22 - $x23", text)
        self.assertGreaterEqual(
            sum(1 for line in text.splitlines() if line.strip() == "si"),
            7,
        )
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_high_step_window_trace_follows_dynamic_control_flow(self) -> None:
        text = (
            ROOT / "tools" / "trace_ibec_bootx_kernel_high_step_window.gdb"
        ).read_text(encoding="utf-8")

        for marker in (
            "IBEC_BOOTX_KERNEL_HIGH_STEP_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_BOOTSTRAP_HVC_BEFORE",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_BOOTSTRAP_HVC_AFTER",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_ENTRY",
            "IBEC_BOOTX_KERNEL_HIGH_STEP index=%u",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_1_BEFORE",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_1_AFTER",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_2_BEFORE",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_PAC_GET_DEFAULT_2_AFTER",
            "IBEC_BOOTX_KERNEL_HIGH_STEP_LIMIT_REACHED",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("set $kernel_high_step_limit = 1024", text)
        self.assertIn("set $kernel_high_step_low_pc = $pc - $kernel_high_step_slide", text)
        self.assertIn("$kernel_high_step_count % 32 == 0", text)
        self.assertIn("$pc == 0xfffffe00238884c0", text)
        self.assertIn("$pc == 0xfffffe0023888504", text)
        self.assertIn("advance *0x76f5c384", text)
        self.assertGreaterEqual(
            sum(1 for line in text.splitlines() if line.strip() == "si"),
            6,
        )
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_bootx_kernel_macho_loop_trace_dumps_parser_inputs_and_code(self) -> None:
        text = (
            ROOT / "tools" / "trace_ibec_bootx_kernel_macho_loop.gdb"
        ).read_text(encoding="utf-8")

        for marker in (
            "IBEC_BOOTX_KERNEL_MACHO_CALLBACK_CALL",
            "IBEC_BOOTX_KERNEL_MACHO_BOOTSTRAP_HVC_BEFORE",
            "IBEC_BOOTX_KERNEL_MACHO_BOOTSTRAP_HVC_AFTER",
            "IBEC_BOOTX_KERNEL_MACHO_HIGH_ENTRY",
            "IBEC_BOOTX_KERNEL_MACHO_BRANCH",
            "IBEC_BOOTX_KERNEL_MACHO_HEADER_64",
            "IBEC_BOOTX_KERNEL_MACHO_HEADER_32",
            "IBEC_BOOTX_KERNEL_MACHO_LOOP_ENTRY",
            "IBEC_BOOTX_KERNEL_MACHO_LOOP_DISASM",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("advance *0xfffffe0023888364", text)
        self.assertIn("x/16gx $x21", text)
        self.assertIn("x/32wx $x21", text)
        self.assertIn("x/512i 0xfffffe0023888a80", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_xnu_natural_run_snapshot_is_read_only_and_self_detaching(self) -> None:
        text = (ROOT / "tools" / "snapshot_xnu_natural_run.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "XNU_NATURAL_SNAPSHOT_SELECTED",
            "XNU_NATURAL_SNAPSHOT_THREADS",
            "XNU_NATURAL_SNAPSHOT_DISASM",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("thread apply all p/x $pc", text)
        self.assertIn("x/96i $pc", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_xnu_early_panic_snapshot_captures_argument_and_frame_chain(self) -> None:
        text = (ROOT / "tools" / "snapshot_xnu_early_panic.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "XNU_EARLY_PANIC_SELECTED",
            "XNU_EARLY_PANIC_ARGUMENT_X2",
            "XNU_EARLY_PANIC_SPIN_DISASM",
            "XNU_EARLY_PANIC_CALLER_DISASM",
            "XNU_EARLY_PANIC_BACKTRACE",
            "XNU_EARLY_PANIC_STACK",
            "XNU_EARLY_PANIC_FRAME_POINTERS",
            "XNU_EARLY_PANIC_FRAME index=%u",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("x/s $x2", text)
        self.assertIn("$panic_frame_index < 8", text)
        self.assertIn("0xffff000000000000 |", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_xnu_psci_reset_trace_stops_before_machine_reset(self) -> None:
        text = (ROOT / "tools" / "trace_xnu_psci_reset_panic.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "XNU_PSCI_SYSTEM_RESET_CALLBACK",
            "XNU_PSCI_SYSTEM_RESET_HIGH_ENTRY",
            "XNU_PSCI_SYSTEM_RESET_ARMED",
            "XNU_PSCI_SYSTEM_RESET_BEFORE",
            "XNU_PSCI_SYSTEM_RESET_THREADS",
            "XNU_PSCI_SYSTEM_RESET_DISASM",
            "XNU_PSCI_SYSTEM_RESET_BACKTRACE",
            "XNU_PSCI_SYSTEM_RESET_STACK_WORDS",
            "XNU_PSCI_SYSTEM_RESET_STACK_CHARS",
            "XNU_PSCI_SYSTEM_RESET_FRAME_POINTERS",
            "XNU_PSCI_SYSTEM_RESET_FRAME index=%u",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("hbreak *0xfffffe0021bef310", text)
        self.assertIn("condition $xnu_reset_bp $x0 == 0x84000009", text)
        self.assertIn("disable $xnu_reset_bp", text)
        self.assertIn("enable $xnu_reset_bp", text)
        self.assertIn("$xnu_reset_frame_index < 12", text)
        self.assertIn("thread apply all p/x $pc", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)

    def test_xnu_paused_reboot_snapshot_covers_every_vcpu_read_only(self) -> None:
        text = (ROOT / "tools" / "snapshot_xnu_paused_reboot.gdb").read_text(
            encoding="utf-8"
        )

        for marker in (
            "XNU_PAUSED_REBOOT_SELECTED",
            "XNU_PAUSED_REBOOT_THREADS",
            "XNU_PAUSED_REBOOT_REGISTERS",
            "XNU_PAUSED_REBOOT_REQUESTER",
            "XNU_PAUSED_REBOOT_REQUESTER_REGISTERS",
            "XNU_PAUSED_REBOOT_EXCEPTION_REGISTERS",
            "XNU_PAUSED_REBOOT_FAULT_INSTRUCTION",
            "XNU_PAUSED_REBOOT_FAULT_DISASM",
            "XNU_PAUSED_REBOOT_CALLER_DISASM",
            "XNU_PAUSED_REBOOT_FRAME1_DISASM",
            "XNU_PAUSED_REBOOT_BACKTRACES",
            "XNU_PAUSED_REBOOT_STACK_WORDS",
            "XNU_PAUSED_REBOOT_STACK_CHARS",
            "XNU_PAUSED_REBOOT_SAVED_STATE_X22_WORDS",
            "XNU_PAUSED_REBOOT_SAVED_STATE_X22_DWORDS",
            "XNU_PAUSED_REBOOT_DEBUGGER_STATE",
            "XNU_PAUSED_REBOOT_DEBUGGER_FIELDS",
            "XNU_PAUSED_REBOOT_DEBUGGER_ARGS",
            "XNU_PAUSED_REBOOT_ORIGINAL_UNDEFINED",
            "XNU_PAUSED_REBOOT_ORIGINAL_UNDEFINED_DISASM",
            "XNU_PAUSED_REBOOT_ORIGINAL_UNDEFINED_FILE",
            "XNU_PAUSED_REBOOT_IMPL_ERROR",
            "XNU_PAUSED_REBOOT_IMPL_ERROR_STATUS",
            "XNU_PAUSED_REBOOT_IMPL_ERROR_GPRS",
            "XNU_PAUSED_REBOOT_IMPL_ERROR_FRAME",
            "XNU_PAUSED_REBOOT_IMPL_ERROR_GVA_TO_GPA",
            "XNU_PAUSED_REBOOT_IMPL_ERROR_PC_DISASM",
            "XNU_PAUSED_REBOOT_IMPL_ERROR_STATE_WORDS",
            "XNU_PAUSED_REBOOT_FRAME_POINTERS",
            "XNU_PAUSED_REBOOT_FRAME index=%d",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertIn("thread apply all info registers", text)
        self.assertIn("xnu_function_id == 0x84000009", text)
        self.assertIn("$ESR_EL1", text)
        self.assertIn("$ELR_EL1", text)
        self.assertIn("$FAR_EL1", text)
        self.assertIn("x/wx $ELR_EL1", text)
        self.assertIn("x/96i $ELR_EL1-0x80", text)
        self.assertIn("x/64gx $sp", text)
        self.assertIn("x/512cb $sp", text)
        self.assertIn("x/96gx $x22", text)
        self.assertIn("x/192wx $x22", text)
        self.assertIn("& 0xFFFFFFFFFFFFFFFF", text)
        self.assertIn('int(gdb.parse_and_eval("$x27"))', text)
        self.assertIn('struct.unpack("<9Q"', text)
        self.assertIn('("PANIC_STRING", xnu_panic_str_ptr)', text)
        self.assertIn('gdb.execute("x/24gx 0x%x"', text)
        self.assertIn("xnu_panic_args_ptr + 24", text)
        self.assertIn('struct.unpack("<4Q"', text)
        self.assertIn("xnu_original_pc - 0x100", text)
        self.assertIn('xnu_panic_format.startswith("Undefined kernel instruction:")', text)
        self.assertIn('"implementation specific error" in xnu_panic_format', text)
        self.assertIn('struct.unpack("<9Q", xnu_impl_arg_raw)', text)
        self.assertIn('struct.unpack_from("<29Q", xnu_saved_state_raw, 8)', text)
        self.assertIn('struct.unpack_from("<4Q", xnu_saved_state_raw, 240)', text)
        self.assertIn('xnu_state_far, xnu_state_esr = struct.unpack_from(', text)
        self.assertIn('"<2Q", xnu_saved_state_raw, 280', text)
        self.assertIn("xnu_state_pc - 0x100", text)
        self.assertIn('gdb.execute("monitor gva2gpa 0x%x" % xnu_state_far)', text)
        self.assertIn("xnu_saved_lr & 0x0000FFFFFFFFFFFF", text)
        self.assertIn("bt", text)
        self.assertIn("detach", text)
        self.assertIn("quit", text)
        self.assertNotIn("set $x0", text)
        self.assertNotIn("set *(unsigned", text)


if __name__ == "__main__":
    unittest.main()
