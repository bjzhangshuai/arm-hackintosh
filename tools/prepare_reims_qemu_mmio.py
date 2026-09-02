#!/usr/bin/env python3
"""Prepare the pinned Reims ARM MMIO shim for a Linux/TCG host.

The upstream Reims shim deliberately limits two host callbacks to Darwin:
reading the publishing ARM vCPU registers and constructing a host view over
guest pages. QEMU exposes both operations portably for the subset needed on
Linux. In addition, the pinned shim starts its device poll timer only when an
optional native host window starts. A backend-vulkan, ``-display none`` build
has no such window, but still must poll the shared state and deliver ONLINE,
interrupt, and scanout actions.

The replacements are exact. A changed upstream source fails the build instead
of silently producing a partly adapted device.
"""

from __future__ import annotations

import argparse
from pathlib import Path


READ_XREG_START = "static int reims_vgpu_mmio_read_xreg("
READ_XREG_END = "\n/*\n * Contiguous host-VA view"
MAP_PAGES_START = "static int reims_vgpu_mmio_map_pages("
MAP_PAGES_END = "\n/*\n * Release a view map_pages handed out."


READ_XREG_REPLACEMENT = r'''static int reims_vgpu_mmio_read_xreg(void *ctx, uint32_t index,
                                        uint64_t *out)
{
    CPUState *cs = current_cpu;
    GByteArray *reg;
    int len;

    (void)ctx;
    if (!out || index >= 31 || !cs) {
        return -1;
    }

    /*
     * This callback runs synchronously in the publishing vCPU's IOSFC MMIO
     * write. The generic GDB register hook therefore reads that exact CPU and
     * avoids an ARM target header in a common system device.
     */
    cpu_synchronize_state(cs);
    reg = g_byte_array_sized_new(sizeof(*out));
    len = gdb_read_register(cs, reg, index);
    if (len != sizeof(*out) || reg->len != sizeof(*out)) {
        g_byte_array_unref(reg);
        return -1;
    }
    *out = ldq_le_p(reg->data);
    g_byte_array_unref(reg);
    return 0;
}
'''


MAP_PAGES_REPLACEMENT = r'''static int reims_vgpu_mmio_map_pages(void *ctx, const uint64_t *gpas,
                                      size_t count, void **out_ptr)
{
    const hwaddr page =
        (hwaddr)1 << REIMS_VGPU_GUEST_PAGE_SHIFT_ARM64E;
    uint8_t *base = NULL;
    MemoryRegion *base_mr = NULL;
    size_t i;

    (void)ctx;
    if (!gpas || count == 0 || !out_ptr || count > UINT64_MAX / page) {
        return -1;
    }

    /*
     * Linux QEMU keeps guest RAM in stable RAMBlock mappings. Accept a view
     * only when page i is exactly base + i * 16 KiB in the same RAM region.
     * This is the packed-view contract consumed by the Rust mapper; sparse or
     * cross-region lists fail closed and use its explicit copy fallback.
     */
    rcu_read_lock();
    if (gpas[0] <= UINT64_MAX - (count - 1) * page) {
        hwaddr total = count * page;
        bool sequential = true;

        for (i = 1; i < count; i++) {
            if (gpas[i] != gpas[0] + i * page) {
                sequential = false;
                break;
            }
        }
        if (sequential) {
            hwaddr xlat, plen = total;
            MemoryRegion *mr;
            uint8_t *hva;

            mr = address_space_translate(&address_space_memory, gpas[0],
                                         &xlat, &plen, true,
                                         MEMTXATTRS_UNSPECIFIED);
            if (mr && memory_region_is_ram(mr) && plen >= total) {
                hva = (uint8_t *)memory_region_get_ram_ptr(mr) + xlat;
                if (((uintptr_t)hva & (page - 1)) == 0) {
                    rcu_read_unlock();
                    *out_ptr = hva;
                    return 0;
                }
            }
        }
    }

    for (i = 0; i < count; i++) {
        hwaddr xlat, plen = page;
        MemoryRegion *mr;
        uint8_t *hva;

        mr = address_space_translate(&address_space_memory, gpas[i], &xlat,
                                     &plen, true, MEMTXATTRS_UNSPECIFIED);
        if (!mr || !memory_region_is_ram(mr) || plen < page) {
            goto fail;
        }
        hva = (uint8_t *)memory_region_get_ram_ptr(mr) + xlat;
        if (i == 0) {
            base = hva;
            base_mr = mr;
            if (((uintptr_t)base & (page - 1)) != 0) {
                goto fail;
            }
        } else if (mr != base_mr || hva != base + i * page) {
            goto fail;
        }
    }
    rcu_read_unlock();
    *out_ptr = base;
    return 0;

fail:
    rcu_read_unlock();
    return -1;
}
'''


WINDOW_TIMER_OLD = r'''    rc = reims_vgpu_qemu_window_start(s->rust_handle, REIMS_VGPU_MMIO_EFI_W,
                               REIMS_VGPU_MMIO_EFI_H);
    if (rc == REIMS_VGPU_QEMU_OK) {
        s->poll_timer = timer_new_ms(QEMU_CLOCK_HOST,
                                     reims_vgpu_mmio_poll_tick, s);
        timer_mod(s->poll_timer, qemu_clock_get_ms(QEMU_CLOCK_HOST));
#if defined(CONFIG_DARWIN)
        reims_vgpu_mmio_window_owner = s;
        qemu_main = reims_vgpu_mmio_window_main_loop;
#endif
    } else {
        qemu_log_mask(LOG_GUEST_ERROR,
                      "%s: host window unavailable rc=%d; using QEMU display\n",
                      TYPE_REIMS_VGPU_MMIO, rc);
    }
'''


WINDOW_TIMER_REPLACEMENT = r'''    rc = reims_vgpu_qemu_window_start(s->rust_handle, REIMS_VGPU_MMIO_EFI_W,
                               REIMS_VGPU_MMIO_EFI_H);
    if (rc == REIMS_VGPU_QEMU_OK) {
#if defined(CONFIG_DARWIN)
        reims_vgpu_mmio_window_owner = s;
        qemu_main = reims_vgpu_mmio_window_main_loop;
#endif
    } else {
        qemu_log_mask(LOG_GUEST_ERROR,
                      "%s: host window unavailable rc=%d; using QEMU display\n",
                      TYPE_REIMS_VGPU_MMIO, rc);
    }

    /*
     * The poll loop is a device requirement, not a native-window service.
     * Headless Linux/Vulkan builds still need it to observe the guest enable
     * mask and deliver ONLINE, IRQ, and scanout actions.
     */
    s->poll_timer = timer_new_ms(QEMU_CLOCK_HOST,
                                 reims_vgpu_mmio_poll_tick, s);
    timer_mod(s->poll_timer, qemu_clock_get_ms(QEMU_CLOCK_HOST));
'''


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise ValueError(f"missing start marker: {start}")
    end_at = text.find(end, start_at)
    if end_at < 0:
        raise ValueError(f"missing end marker after {start}: {end.strip()}")
    if text.find(start, start_at + 1) >= 0:
        raise ValueError(f"ambiguous start marker: {start}")
    return text[:start_at] + replacement.rstrip() + text[end_at:]


def replace_exact_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {name} block, found {count}")
    return text.replace(old, new, 1)


def prepare(source: str) -> str:
    include_anchor = '#include "hw/core/cpu.h"\n'
    include = '#include "exec/gdbstub.h"\n'
    if source.count(include_anchor) != 1:
        raise ValueError("expected exactly one CPU header include")
    if include in source:
        raise ValueError("GDB register header is already present")

    result = source.replace(include_anchor, include_anchor + include, 1)
    result = replace_section(
        result, READ_XREG_START, READ_XREG_END, READ_XREG_REPLACEMENT
    )
    result = replace_section(
        result, MAP_PAGES_START, MAP_PAGES_END, MAP_PAGES_REPLACEMENT
    )

    stable_anchor = ".map_pages_stable = 0,"
    if result.count(stable_anchor) != 1:
        raise ValueError("expected exactly one map_pages_stable assignment")
    result = result.replace(stable_anchor, ".map_pages_stable = 1,", 1)
    result = replace_exact_once(
        result,
        WINDOW_TIMER_OLD,
        WINDOW_TIMER_REPLACEMENT,
        "window-coupled poll timer",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.source.read_text(encoding="utf-8")
    output = prepare(source)
    args.output.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
