/*
 * VMApple Backdoor Interface
 *
 * Copyright © 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * This work is licensed under the terms of the GNU GPL, version 2 or later.
 * See the COPYING file in the top-level directory.
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include "qemu/osdep.h"
#include "qemu/units.h"
#include "qemu/log.h"
#include "qemu/module.h"
#include "trace.h"
#include "hw/core/cpu.h"
#include "hw/core/qdev-properties.h"
#include "hw/core/qdev-properties-system.h"
#include "hw/vmapple/vmapple.h"
#include "hw/core/sysbus.h"
#include "hw/block/block.h"
#include "qapi/error.h"
#include "system/block-backend.h"
#include "system/dma.h"
#include "chardev/char-fe.h"

OBJECT_DECLARE_SIMPLE_TYPE(VMAppleBdifState, VMAPPLE_BDIF)

struct VMAppleBdifState {
    SysBusDevice parent_obj;

    BlockBackend *aux;
    BlockBackend *root;
    BlockBackend *usb;
    bool usb_restore_pending;
    bool usb_restore_first_packet_used;
    uint32_t usb_restore_selected_queue;
    uint64_t usb_restore_pending_addr;
    uint32_t usb_restore_pending_len;
    uint32_t usb_restore_pending_flags;
    GByteArray *usb_restore_rx;
    MemoryRegion mmio;
    char *usb_restore_first_packet;
    CharFrontend usb_restore_chr;
    bool block_writes;
    uint32_t root_queue_notify;
    uint32_t aux_queue_notify;
    uint32_t usb_queue_notify;
};

#define VMAPPLE_BDIF_SIZE   0x00200000

#define REG_DEVID_MASK      0xffff0000
#define DEVID_ROOT          0x00000000
#define DEVID_AUX           0x00010000
#define DEVID_USB           0x00100000

#define REG_STATUS          0x0
#define REG_STATUS_ACTIVE     BIT(0)
#define REG_CFG             0x4
#define REG_CFG_ACTIVE        BIT(1)
#define REG_CFG_USB_RESTORE   0x1a01
#define REG_UNK1            0x8
#define REG_BUSY            0x10
#define REG_BUSY_READY        BIT(0)
#define REG_UNK2            0x400
#define REG_QUEUE_NOTIFY    0x404
#define REG_CMD             0x408
#define REG_QUEUE_SELECT    0x410
#define REG_NEXT_DEVICE     0x420
#define REG_UNK3            0x434

typedef struct VblkSector {
    uint32_t pad;
    uint32_t pad2;
    uint32_t sector;
    uint32_t pad3;
} VblkSector;

typedef struct VblkReqCmd {
    uint64_t addr;
    uint32_t len;
    uint32_t flags;
} VblkReqCmd;

typedef struct VblkReq {
    VblkReqCmd sector;
    VblkReqCmd data;
    VblkReqCmd retval;
} VblkReq;

#define VBLK_DATA_FLAGS_READ  0x00030001
#define VBLK_DATA_FLAGS_WRITE 0x00010001

#define VBLK_RET_SUCCESS  0
#define VBLK_RET_FAILED   1

#define VBLK_USB_RESTORE_FLAGS 0x00020001
#define VBLK_USB_RESTORE_HEADER_LEN 6
#define VBLK_USB_RESTORE_MAX_PACKET (16 * MiB)
#define VBLK_USB_RESTORE_OUT_FLAGS 0x00000001

static bool bdif_is_usb_restore_transfer(uint64_t devid, const VblkReq *req)
{
    if (devid != DEVID_USB) {
        return false;
    }

    return req->sector.addr &&
           req->sector.len > sizeof(VblkSector) &&
           req->sector.flags == VBLK_USB_RESTORE_FLAGS &&
           req->data.addr == 0 && req->data.len == 0 &&
           req->data.flags == 0 &&
           req->retval.addr == 0 && req->retval.len == 0 &&
           req->retval.flags == 0;
}

static bool bdif_is_usb_restore_out_packet(uint64_t devid, const VblkReq *req)
{
    if (devid != DEVID_USB) {
        return false;
    }

    return req->sector.addr &&
           req->sector.len &&
           req->sector.flags == VBLK_USB_RESTORE_OUT_FLAGS &&
           req->data.addr == 0 && req->data.len == 0 &&
           req->data.flags == 0 &&
           req->retval.addr == 0 && req->retval.len == 0 &&
           req->retval.flags == 0;
}

static int bdif_hex_value(char ch)
{
    if (ch >= '0' && ch <= '9') {
        return ch - '0';
    }
    if (ch >= 'a' && ch <= 'f') {
        return ch - 'a' + 10;
    }
    if (ch >= 'A' && ch <= 'F') {
        return ch - 'A' + 10;
    }
    return -1;
}

static bool bdif_hex_separator(char ch)
{
    return ch == ':' || ch == ',' || ch == '-' || ch == '_' ||
           ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r';
}

static int bdif_decode_hex_packet(const char *hex, uint8_t *buf,
                                  size_t buf_len, size_t *packet_len)
{
    const char *p = hex;
    size_t len = 0;

    while (*p) {
        int hi;
        int lo;

        while (bdif_hex_separator(*p)) {
            p++;
        }
        if (!*p) {
            break;
        }

        hi = bdif_hex_value(*p++);
        if (hi < 0) {
            return -1;
        }

        lo = bdif_hex_value(*p++);
        if (lo < 0) {
            return -1;
        }

        if (len == buf_len) {
            return -1;
        }
        buf[len++] = (hi << 4) | lo;
    }

    if (!len) {
        return -1;
    }

    *packet_len = len;
    return 0;
}

static bool bdif_usb_restore_deliver_first_packet(VMAppleBdifState *s,
                                                  const VblkReq *req,
                                                  uint64_t gp_addr,
                                                  uint64_t guest_pc)
{
    g_autofree uint8_t *packet = NULL;
    size_t packet_len = 0;
    uint64_t header = 0;
    MemTxResult dma_result;

    if (!s->usb_restore_first_packet || s->usb_restore_first_packet_used) {
        return false;
    }

    s->usb_restore_first_packet_used = true;
    if (req->sector.len > VBLK_USB_RESTORE_MAX_PACKET) {
        trace_bdif_vblk_error("usb", "usb-restore-capacity", gp_addr,
                              req->sector.len, VBLK_USB_RESTORE_MAX_PACKET,
                              guest_pc);
        return false;
    }

    packet = g_malloc0(req->sector.len);
    if (bdif_decode_hex_packet(s->usb_restore_first_packet, packet,
                               req->sector.len, &packet_len) < 0) {
        trace_bdif_vblk_error("usb", "usb-restore-hex", gp_addr,
                              req->sector.len, 0, guest_pc);
        return false;
    }

    dma_result = dma_memory_write(&address_space_memory, req->sector.addr,
                                  packet, packet_len,
                                  MEMTXATTRS_UNSPECIFIED);
    if (dma_result != MEMTX_OK) {
        trace_bdif_vblk_error("usb", "usb-restore-dma", gp_addr,
                              req->sector.addr, dma_result, guest_pc);
        return false;
    }

    memcpy(&header, packet, MIN(packet_len, sizeof(header)));
    s->usb_restore_pending = false;
    trace_bdif_usb_restore_packet("inject-first", req->sector.addr,
                                  req->sector.len, packet_len, header,
                                  guest_pc);
    return true;
}

static void bdif_usb_restore_handle_out_packet(VMAppleBdifState *s,
                                               const VblkReq *req,
                                               uint64_t gp_addr,
                                               uint64_t guest_pc)
{
    g_autofree uint8_t *packet = NULL;
    uint64_t header = 0;
    MemTxResult dma_result;

    if (req->sector.len > VBLK_USB_RESTORE_MAX_PACKET) {
        trace_bdif_vblk_error("usb", "usb-restore-out-capacity", gp_addr,
                              req->sector.len, VBLK_USB_RESTORE_MAX_PACKET,
                              guest_pc);
        return;
    }

    packet = g_malloc0(req->sector.len);
    dma_result = dma_memory_read(&address_space_memory, req->sector.addr,
                                 packet, req->sector.len,
                                 MEMTXATTRS_UNSPECIFIED);
    if (dma_result != MEMTX_OK) {
        trace_bdif_vblk_error("usb", "usb-restore-out-dma", gp_addr,
                              req->sector.addr, dma_result, guest_pc);
        return;
    }

    memcpy(&header, packet, MIN((size_t)req->sector.len, sizeof(header)));
    trace_bdif_usb_restore_packet("guest-out", req->sector.addr,
                                  req->sector.len, req->sector.len, header,
                                  guest_pc);

    if (qemu_chr_fe_backend_connected(&s->usb_restore_chr)) {
        int packet_len = (int)req->sector.len;
        int written = qemu_chr_fe_write(&s->usb_restore_chr, packet,
                                        packet_len);

        if (written == packet_len) {
            trace_bdif_usb_restore_packet("chardev-out", req->sector.addr,
                                          req->sector.len, req->sector.len,
                                          header, guest_pc);
        } else {
            trace_bdif_vblk_error("usb", "usb-restore-chardev-write",
                                  gp_addr, (uint64_t)(int64_t)written,
                                  req->sector.len, guest_pc);
        }
        qemu_chr_fe_accept_input(&s->usb_restore_chr);
    }
}

static BlockBackend *bdif_backend_for_devid(VMAppleBdifState *s,
                                            uint64_t devid)
{
    switch (devid) {
    case DEVID_ROOT:
        return s->root;
    case DEVID_AUX:
        return s->aux;
    case DEVID_USB:
        return s->usb;
    default:
        return NULL;
    }
}

static uint64_t bdif_cfg_for_devid(VMAppleBdifState *s, uint64_t devid)
{
    if (!bdif_backend_for_devid(s, devid)) {
        return 0;
    }

    switch (devid) {
    case DEVID_USB:
        return REG_CFG_USB_RESTORE;
    default:
        return REG_CFG_ACTIVE;
    }
}

static const char *bdif_devid_name(uint64_t devid)
{
    switch (devid) {
    case DEVID_ROOT:
        return "root";
    case DEVID_AUX:
        return "aux";
    case DEVID_USB:
        return "usb";
    default:
        return "unknown";
    }
}

static const char *bdif_reg_name(hwaddr offset)
{
    switch (offset & ~REG_DEVID_MASK) {
    case REG_STATUS:
        return "status";
    case REG_CFG:
        return "cfg";
    case REG_UNK1:
        return "unk1";
    case REG_BUSY:
        return "busy";
    case REG_UNK2:
        return "unk2";
    case REG_QUEUE_NOTIFY:
        return "queue-notify";
    case REG_CMD:
        return "cmd";
    case REG_QUEUE_SELECT:
        return "queue-select";
    case REG_NEXT_DEVICE:
        return "next-device";
    case REG_UNK3:
        return "unk3";
    default:
        return "unknown";
    }
}

static uint32_t *bdif_queue_notify_for_devid(VMAppleBdifState *s,
                                             uint64_t devid)
{
    switch (devid) {
    case DEVID_ROOT:
        return &s->root_queue_notify;
    case DEVID_AUX:
        return &s->aux_queue_notify;
    case DEVID_USB:
        return &s->usb_queue_notify;
    default:
        return NULL;
    }
}

static uint64_t bdif_guest_pc(void)
{
    return current_cpu ? current_cpu->cc->get_pc(current_cpu) : 0;
}

static void bdif_trace_access(const char *op, uint64_t devid, hwaddr offset,
                              unsigned size, uint64_t value)
{
    trace_bdif_access(op, bdif_devid_name(devid), bdif_reg_name(offset),
                      offset, size, value, bdif_guest_pc());
}

static bool bdif_usb_restore_try_deliver_rx(VMAppleBdifState *s,
                                            uint64_t guest_pc)
{
    uint32_t payload_len;
    size_t packet_len;
    uint64_t header = 0;
    MemTxResult dma_result;

    if (!s->usb_restore_pending || !s->usb_restore_rx ||
        s->usb_restore_rx->len < VBLK_USB_RESTORE_HEADER_LEN) {
        return false;
    }

    payload_len = ldl_le_p(s->usb_restore_rx->data);
    if (payload_len > VBLK_USB_RESTORE_MAX_PACKET -
                      VBLK_USB_RESTORE_HEADER_LEN) {
        trace_bdif_vblk_error("usb", "usb-restore-chardev-len",
                              s->usb_restore_pending_addr, payload_len,
                              VBLK_USB_RESTORE_MAX_PACKET, guest_pc);
        g_byte_array_set_size(s->usb_restore_rx, 0);
        return false;
    }

    packet_len = payload_len + VBLK_USB_RESTORE_HEADER_LEN;
    if (s->usb_restore_rx->len < packet_len) {
        return false;
    }

    if (packet_len > s->usb_restore_pending_len) {
        trace_bdif_vblk_error("usb", "usb-restore-chardev-capacity",
                              s->usb_restore_pending_addr, packet_len,
                              s->usb_restore_pending_len, guest_pc);
        g_byte_array_remove_range(s->usb_restore_rx, 0, packet_len);
        return false;
    }

    dma_result = dma_memory_write(&address_space_memory,
                                  s->usb_restore_pending_addr,
                                  s->usb_restore_rx->data, packet_len,
                                  MEMTXATTRS_UNSPECIFIED);
    if (dma_result != MEMTX_OK) {
        trace_bdif_vblk_error("usb", "usb-restore-chardev-dma",
                              s->usb_restore_pending_addr,
                              s->usb_restore_pending_addr, dma_result,
                              guest_pc);
        g_byte_array_remove_range(s->usb_restore_rx, 0, packet_len);
        return false;
    }

    memcpy(&header, s->usb_restore_rx->data,
           MIN(packet_len, sizeof(header)));
    trace_bdif_usb_restore_packet("chardev-in", s->usb_restore_pending_addr,
                                  s->usb_restore_pending_len, packet_len,
                                  header, guest_pc);
    g_byte_array_remove_range(s->usb_restore_rx, 0, packet_len);
    s->usb_restore_pending = false;
    return true;
}

static int bdif_usb_restore_chr_can_read(void *opaque)
{
    (void)opaque;
    return VBLK_USB_RESTORE_MAX_PACKET;
}

static void bdif_usb_restore_chr_read(void *opaque, const uint8_t *buf,
                                      int size)
{
    VMAppleBdifState *s = opaque;
    uint64_t guest_pc = bdif_guest_pc();
    uint64_t header = 0;

    if (size <= 0) {
        return;
    }

    if (!s->usb_restore_rx) {
        s->usb_restore_rx = g_byte_array_new();
    }

    if (s->usb_restore_rx->len + size > VBLK_USB_RESTORE_MAX_PACKET) {
        trace_bdif_vblk_error("usb", "usb-restore-chardev-overflow",
                              s->usb_restore_pending_addr,
                              s->usb_restore_rx->len + size,
                              VBLK_USB_RESTORE_MAX_PACKET, guest_pc);
        g_byte_array_set_size(s->usb_restore_rx, 0);
        qemu_chr_fe_accept_input(&s->usb_restore_chr);
        return;
    }

    g_byte_array_append(s->usb_restore_rx, buf, size);
    memcpy(&header, buf, MIN((size_t)size, sizeof(header)));
    trace_bdif_usb_restore_packet("chardev-buffered", 0,
                                  VBLK_USB_RESTORE_MAX_PACKET,
                                  (uint32_t)size, header, guest_pc);
    bdif_usb_restore_try_deliver_rx(s, guest_pc);
    qemu_chr_fe_accept_input(&s->usb_restore_chr);
}

static uint64_t bdif_read(void *opaque, hwaddr offset, unsigned size)
{
    VMAppleBdifState *s = opaque;
    uint64_t ret = -1;
    uint64_t devid = offset & REG_DEVID_MASK;
    bool present = bdif_backend_for_devid(s, devid) != NULL;

    switch (offset & ~REG_DEVID_MASK) {
    case REG_STATUS:
        ret = present ? REG_STATUS_ACTIVE : 0;
        break;
    case REG_CFG:
        ret = bdif_cfg_for_devid(s, devid);
        break;
    case REG_UNK1:
        ret = present ? 0x420 : 0;
        break;
    case REG_BUSY:
        if (devid == DEVID_USB) {
            bdif_usb_restore_try_deliver_rx(s, bdif_guest_pc());
        }
        if (devid == DEVID_USB &&
            s->usb_restore_pending &&
            s->usb_restore_selected_queue == 0) {
            ret = 0;
        } else {
            ret = present ? REG_BUSY_READY : 0;
        }
        break;
    case REG_UNK2:
        ret = present ? 0x1 : 0;
        break;
    case REG_QUEUE_NOTIFY:
        {
            uint32_t *queue_notify = bdif_queue_notify_for_devid(s, devid);

            ret = present && queue_notify ? *queue_notify : 0;
        }
        break;
    case REG_UNK3:
        ret = present ? 0x0 : -1;
        break;
    case REG_NEXT_DEVICE:
        switch (devid) {
        case DEVID_ROOT:
            ret = 0x8000000;
            break;
        case DEVID_AUX:
            ret = 0x10000;
            break;
        case DEVID_USB:
            ret = 0x100000;
            break;
        }
        break;
    }

    bdif_trace_access("read", devid, offset, size, ret);
    trace_bdif_read(offset, size, ret);
    return ret;
}

static void le2cpu_sector(VblkSector *sector)
{
    sector->sector = le32_to_cpu(sector->sector);
}

static void le2cpu_reqcmd(VblkReqCmd *cmd)
{
    cmd->addr = le64_to_cpu(cmd->addr);
    cmd->len = le32_to_cpu(cmd->len);
    cmd->flags = le32_to_cpu(cmd->flags);
}

static void le2cpu_req(VblkReq *req)
{
    le2cpu_reqcmd(&req->sector);
    le2cpu_reqcmd(&req->data);
    le2cpu_reqcmd(&req->retval);
}

static void vblk_cmd(VMAppleBdifState *s, uint64_t devid, BlockBackend *blk,
                     uint64_t gp_addr, uint64_t static_off)
{
    VblkReq req;
    VblkSector sector;
    uint64_t off = 0;
    g_autofree char *buf = NULL;
    uint8_t ret = VBLK_RET_FAILED;
    int r;
    MemTxResult dma_result;
    uint64_t guest_pc = bdif_guest_pc();
    uint64_t header = 0;

    dma_result = dma_memory_read(&address_space_memory, gp_addr,
                                 &req, sizeof(req), MEMTXATTRS_UNSPECIFIED);
    if (dma_result != MEMTX_OK) {
        trace_bdif_vblk_error(bdif_devid_name(devid), "req-dma", gp_addr,
                              dma_result, 0, guest_pc);
        return;
    }

    le2cpu_req(&req);
    trace_bdif_vblk_cmd(bdif_devid_name(devid), gp_addr, guest_pc);
    trace_bdif_vblk_desc(bdif_devid_name(devid), "sector",
                         req.sector.addr, req.sector.len, req.sector.flags,
                         guest_pc);
    trace_bdif_vblk_desc(bdif_devid_name(devid), "data", req.data.addr,
                         req.data.len, req.data.flags, guest_pc);
    trace_bdif_vblk_desc(bdif_devid_name(devid), "retval", req.retval.addr,
                         req.retval.len, req.retval.flags, guest_pc);

    if (bdif_is_usb_restore_transfer(devid, &req)) {
        s->usb_restore_pending = true;
        s->usb_restore_pending_addr = req.sector.addr;
        s->usb_restore_pending_len = req.sector.len;
        s->usb_restore_pending_flags = req.sector.flags;

        trace_bdif_usb_restore_packet("pending", req.sector.addr,
                                      req.sector.len, 0, 0, guest_pc);
        if (bdif_usb_restore_deliver_first_packet(s, &req, gp_addr,
                                                  guest_pc) ||
            bdif_usb_restore_try_deliver_rx(s, guest_pc)) {
            return;
        }

        trace_bdif_vblk_error(bdif_devid_name(devid), "usb-restore-pending",
                              gp_addr, req.sector.len, req.sector.flags,
                              guest_pc);
        s->usb_restore_pending = true;
        return;
    }

    if (bdif_is_usb_restore_out_packet(devid, &req)) {
        bdif_usb_restore_handle_out_packet(s, &req, gp_addr, guest_pc);
        return;
    }

    if (req.sector.len != sizeof(sector)) {
        trace_bdif_vblk_error(bdif_devid_name(devid), "sector-len", gp_addr,
                              req.sector.len, sizeof(sector), guest_pc);
        goto out;
    }

    /* Read the vblk command */
    dma_result = dma_memory_read(&address_space_memory, req.sector.addr,
                                 &sector, sizeof(sector),
                                 MEMTXATTRS_UNSPECIFIED);
    if (dma_result != MEMTX_OK) {
        trace_bdif_vblk_error(bdif_devid_name(devid), "sector-dma", gp_addr,
                              req.sector.addr, dma_result, guest_pc);
        goto out;
    }
    le2cpu_sector(&sector);

    off = sector.sector * 512ULL + static_off;
    trace_bdif_vblk_sector(bdif_devid_name(devid), sector.sector, off,
                           req.data.len, req.data.flags, guest_pc);

    /* Sanity check that we're not allocating bogus sizes */
    if (req.data.len > 128 * MiB) {
        trace_bdif_vblk_error(bdif_devid_name(devid), "data-len", gp_addr,
                              req.data.len, 128 * MiB, guest_pc);
        goto out;
    }

    buf = g_malloc0(req.data.len);
    switch (req.data.flags) {
    case VBLK_DATA_FLAGS_READ:
        r = blk_pread(blk, off, req.data.len, buf, 0);
        header = req.data.len >= sizeof(header) ? ldq_le_p(buf) : 0;
        trace_bdif_vblk_read(bdif_devid_name(devid),
                             req.data.addr, off, req.data.len, r,
                             guest_pc, header);
        if (r < 0) {
            trace_bdif_vblk_error(bdif_devid_name(devid), "read-failed",
                                  gp_addr, off, (uint64_t)r, guest_pc);
            goto out;
        }
        dma_result = dma_memory_write(&address_space_memory, req.data.addr, buf,
                                      req.data.len, MEMTXATTRS_UNSPECIFIED);
        if (dma_result == MEMTX_OK) {
            ret = VBLK_RET_SUCCESS;
        } else {
            trace_bdif_vblk_error(bdif_devid_name(devid), "data-dma",
                                  gp_addr, req.data.addr, dma_result,
                                  guest_pc);
        }
        break;
    case VBLK_DATA_FLAGS_WRITE:
        if (!s->block_writes) {
            trace_bdif_vblk_error(bdif_devid_name(devid), "write-disabled",
                                  gp_addr, off, req.data.len, guest_pc);
            break;
        }
        dma_result = dma_memory_read(&address_space_memory, req.data.addr, buf,
                                     req.data.len, MEMTXATTRS_UNSPECIFIED);
        if (dma_result != MEMTX_OK) {
            trace_bdif_vblk_error(bdif_devid_name(devid), "write-data-dma",
                                  gp_addr, req.data.addr, dma_result,
                                  guest_pc);
            goto out;
        }
        header = req.data.len >= sizeof(header) ? ldq_le_p(buf) : 0;
        r = blk_pwrite(blk, off, req.data.len, buf, 0);
        trace_bdif_vblk_write(bdif_devid_name(devid),
                              req.data.addr, off, req.data.len, r,
                              guest_pc, header);
        if (r < 0) {
            trace_bdif_vblk_error(bdif_devid_name(devid), "write-failed",
                                  gp_addr, off, (uint64_t)r, guest_pc);
            goto out;
        }
        ret = VBLK_RET_SUCCESS;
        break;
    default:
        trace_bdif_vblk_error(bdif_devid_name(devid), "data-flags", gp_addr,
                              req.data.flags, req.data.len, guest_pc);
        break;
    }

    if (devid == DEVID_USB) {
        s->usb_restore_pending = false;
    }

out:
    dma_memory_write(&address_space_memory, req.retval.addr, &ret, 1,
                     MEMTXATTRS_UNSPECIFIED);
}

static void bdif_write(void *opaque, hwaddr offset,
                       uint64_t value, unsigned size)
{
    VMAppleBdifState *s = opaque;
    uint64_t devid = offset & REG_DEVID_MASK;
    BlockBackend *blk = bdif_backend_for_devid(s, devid);

    bdif_trace_access("write", devid, offset, size, value);
    trace_bdif_write(offset, size, value);

    switch (offset & ~REG_DEVID_MASK) {
    case REG_CMD:
        if (blk) {
            vblk_cmd(s, devid, blk, value, 0x0);
        }
        break;
    case REG_QUEUE_NOTIFY:
        {
            uint32_t *queue_notify = bdif_queue_notify_for_devid(s, devid);

            if (blk && queue_notify) {
                *queue_notify = (uint32_t)value;
            }
        }
        break;
    case REG_QUEUE_SELECT:
        s->usb_restore_selected_queue = devid == DEVID_USB ? value : 0;
        break;
    }
}

static const MemoryRegionOps bdif_ops = {
    .read = bdif_read,
    .write = bdif_write,
    .endianness = DEVICE_NATIVE_ENDIAN,
    .valid = {
        .min_access_size = 1,
        .max_access_size = 8,
    },
    .impl = {
        .min_access_size = 1,
        .max_access_size = 8,
    },
};

static void bdif_init(Object *obj)
{
    VMAppleBdifState *s = VMAPPLE_BDIF(obj);

    s->usb_restore_rx = g_byte_array_new();
    memory_region_init_io(&s->mmio, obj, &bdif_ops, obj,
                         "VMApple Backdoor Interface", VMAPPLE_BDIF_SIZE);
    sysbus_init_mmio(SYS_BUS_DEVICE(obj), &s->mmio);
}

static const Property bdif_properties[] = {
    DEFINE_PROP_DRIVE("aux", VMAppleBdifState, aux),
    DEFINE_PROP_DRIVE("root", VMAppleBdifState, root),
    DEFINE_PROP_DRIVE("usb", VMAppleBdifState, usb),
    DEFINE_PROP_STRING("usb-restore-first-packet", VMAppleBdifState, usb_restore_first_packet),
    DEFINE_PROP_CHR("usb-restore-chardev", VMAppleBdifState, usb_restore_chr),
    DEFINE_PROP_BOOL("block-writes", VMAppleBdifState, block_writes, false),
};

static bool bdif_set_block_write_perm(BlockBackend *blk, const char *name,
                                      Error **errp)
{
    int r;

    if (!blk) {
        return true;
    }

    r = blk_set_perm(blk, BLK_PERM_CONSISTENT_READ | BLK_PERM_WRITE,
                     BLK_PERM_ALL, errp);
    if (r < 0) {
        error_prepend(errp, "vmapple-bdif %s backing: ", name);
        return false;
    }

    return true;
}

static void bdif_realize(DeviceState *dev, Error **errp)
{
    VMAppleBdifState *s = VMAPPLE_BDIF(dev);

    if (s->block_writes &&
        (!bdif_set_block_write_perm(s->aux, "aux", errp) ||
         !bdif_set_block_write_perm(s->root, "root", errp))) {
        return;
    }

    if (qemu_chr_fe_backend_connected(&s->usb_restore_chr)) {
        qemu_chr_fe_set_handlers(&s->usb_restore_chr,
                                 bdif_usb_restore_chr_can_read,
                                 bdif_usb_restore_chr_read, NULL, NULL,
                                 s, NULL, true);
        qemu_chr_fe_accept_input(&s->usb_restore_chr);
    }
}

static void bdif_unrealize(DeviceState *dev)
{
    VMAppleBdifState *s = VMAPPLE_BDIF(dev);

    if (qemu_chr_fe_backend_connected(&s->usb_restore_chr)) {
        qemu_chr_fe_set_handlers(&s->usb_restore_chr, NULL, NULL, NULL,
                                 NULL, s, NULL, true);
        qemu_chr_fe_deinit(&s->usb_restore_chr, false);
    }

    if (s->usb_restore_rx) {
        g_byte_array_unref(s->usb_restore_rx);
        s->usb_restore_rx = NULL;
    }
}

static void bdif_class_init(ObjectClass *klass, const void *data)
{
    DeviceClass *dc = DEVICE_CLASS(klass);

    dc->desc = "VMApple Backdoor Interface";
    device_class_set_props(dc, bdif_properties);
    dc->realize = bdif_realize;
    dc->unrealize = bdif_unrealize;
}

static const TypeInfo bdif_info = {
    .name          = TYPE_VMAPPLE_BDIF,
    .parent        = TYPE_SYS_BUS_DEVICE,
    .instance_size = sizeof(VMAppleBdifState),
    .instance_init = bdif_init,
    .class_init    = bdif_class_init,
};

static void bdif_register_types(void)
{
    type_register_static(&bdif_info);
}

type_init(bdif_register_types)
