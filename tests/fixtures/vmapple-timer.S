.text
.global _start
_start:
    movz x10, #0x7000, lsl #16
    mrs x0, cntfrq_el0
    str x0, [x10]
    mrs x1, cntvct_el0
    str x1, [x10, #8]
    add x2, x1, x0
    msr cntv_cval_el0, x2
    mov x3, #3
    msr cntv_ctl_el0, x3
    isb
1:
    mrs x4, cntvct_el0
    str x4, [x10, #16]
    mrs x5, cntv_ctl_el0
    tbz x5, #2, 1b
    str x4, [x10, #24]
    mov x6, #1
    str x6, [x10, #32]
    msr cntv_ctl_el0, xzr
2:
    mrs x4, cntvct_el0
    str x4, [x10, #16]
    b 2b
