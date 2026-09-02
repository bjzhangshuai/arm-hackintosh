/*
 * Copyright (C) 2014 - Linaro
 * Author: Rob Herring <rob.herring@linaro.org>
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, see <http://www.gnu.org/licenses/>.
 */

#include "qemu/osdep.h"
#include "cpu.h"
#include "helper.h"
#include "kvm-consts.h"
#include "qemu/main-loop.h"
#include "system/runstate.h"
#include "internals.h"
#include "arm-powerctl.h"
#include "target/arm/multiprocessing.h"
#include "target/arm/trace.h"
#include "syndrome.h"

#define QEMU_APPLE_PAC_SET_INITIAL_STATE 0xc1000000ULL
#define QEMU_APPLE_PAC_GET_DEFAULT_KEYS 0xc1000001ULL
#define QEMU_APPLE_PAC_SET_A_KEYS 0xc1000002ULL
#define QEMU_APPLE_PAC_SET_B_KEYS 0xc1000003ULL
#define QEMU_APPLE_PAC_SET_EL0_DIVERSIFIER 0xc1000004ULL
#define QEMU_APPLE_PAC_SET_EL0_DIVERSIFIER_AT_EL1 0xc1000005ULL
#define QEMU_APPLE_PAC_SET_G_KEY 0xc1000006ULL
#define QEMU_APPLE_PAC_NOP 0xc10000f0ULL

#define QEMU_APPLE_OEM_UID 0x8300ff01ULL
#define QEMU_APPLE_OEM_REVISION 0x8300ff03ULL
#define QEMU_APPLE_OEM_FEATURES 0x8300feffULL

#define QEMU_APPLE_OEM_FEATURE_UNSUPPORTED 0xffffffffULL

#define QEMU_APPLE_PAC_DEFAULT_A_KEY 0x564d4150504c4541ULL
#define QEMU_APPLE_PAC_DEFAULT_B_KEY 0x564d4150504c4542ULL
#define QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER 0x564d4150504c454aULL
#define QEMU_APPLE_PAC_DEFAULT_G_KEY 0x564d4150504c4547ULL

#define QEMU_APPLE_PAC_DOMAIN_APIA 0x415049414b455930ULL
#define QEMU_APPLE_PAC_DOMAIN_APDA 0x415044414b455930ULL
#define QEMU_APPLE_PAC_DOMAIN_APIB 0x415049424b455930ULL
#define QEMU_APPLE_PAC_DOMAIN_APDB 0x415044424b455930ULL
#define QEMU_APPLE_PAC_DOMAIN_APGA 0x415047414b455930ULL

static bool arm_is_vmapple_pac_hvc_function(uint64_t function_id)
{
    return function_id >= QEMU_APPLE_PAC_SET_INITIAL_STATE &&
           function_id <= QEMU_APPLE_PAC_SET_G_KEY;
}

static bool arm_is_vmapple_hvc_function(uint64_t function_id)
{
    return arm_is_vmapple_pac_hvc_function(function_id) ||
           function_id == QEMU_APPLE_PAC_NOP ||
           function_id == QEMU_APPLE_OEM_UID ||
           function_id == QEMU_APPLE_OEM_REVISION ||
           function_id == QEMU_APPLE_OEM_FEATURES;
}

static uint64_t arm_vmapple_pac_mix64(uint64_t value)
{
    value ^= value >> 30;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27;
    value *= 0x94d049bb133111ebULL;
    value ^= value >> 31;
    return value;
}

static ARMPACKey arm_vmapple_pac_derive_key(uint64_t seed, uint64_t domain)
{
    ARMPACKey key = {
        .lo = arm_vmapple_pac_mix64(seed ^ domain),
        .hi = arm_vmapple_pac_mix64(seed + domain + 0x9e3779b97f4a7c15ULL),
    };

    return key;
}

static uint64_t arm_vmapple_pac_effective_seed(uint64_t base_seed,
                                                uint64_t diversifier)
{
    return arm_vmapple_pac_mix64(base_seed ^ diversifier);
}

static void arm_vmapple_pac_program_a_pair(ARMPACKey *apia,
                                            ARMPACKey *apda,
                                            uint64_t base_seed,
                                            uint64_t diversifier)
{
    uint64_t seed = arm_vmapple_pac_effective_seed(base_seed, diversifier);

    *apia = arm_vmapple_pac_derive_key(seed, QEMU_APPLE_PAC_DOMAIN_APIA);
    *apda = arm_vmapple_pac_derive_key(seed, QEMU_APPLE_PAC_DOMAIN_APDA);
}

static void arm_vmapple_pac_program_b_pair(ARMPACKey *apib,
                                            ARMPACKey *apdb,
                                            uint64_t base_seed,
                                            uint64_t diversifier)
{
    uint64_t seed = arm_vmapple_pac_effective_seed(base_seed, diversifier);

    *apib = arm_vmapple_pac_derive_key(seed, QEMU_APPLE_PAC_DOMAIN_APIB);
    *apdb = arm_vmapple_pac_derive_key(seed, QEMU_APPLE_PAC_DOMAIN_APDB);
}

static void arm_vmapple_pac_program_a_keys(CPUARMState *env, uint64_t seed)
{
    env->vmapple_pac.a_seed = seed;
    env->keys.apia = arm_vmapple_pac_derive_key(
        seed, QEMU_APPLE_PAC_DOMAIN_APIA);
    env->keys.apda = arm_vmapple_pac_derive_key(
        seed, QEMU_APPLE_PAC_DOMAIN_APDA);
    arm_vmapple_pac_program_a_pair(
        &env->vmapple_pac.el0_apia, &env->vmapple_pac.el0_apda,
        seed, env->vmapple_pac.el0_diversifier);
    arm_vmapple_pac_program_a_pair(
        &env->vmapple_pac.el1_user_apia,
        &env->vmapple_pac.el1_user_apda,
        seed, env->vmapple_pac.el1_user_diversifier);
}

static void arm_vmapple_pac_program_b_keys(CPUARMState *env, uint64_t seed)
{
    env->vmapple_pac.b_seed = seed;
    env->keys.apib = arm_vmapple_pac_derive_key(
        seed, QEMU_APPLE_PAC_DOMAIN_APIB);
    env->keys.apdb = arm_vmapple_pac_derive_key(
        seed, QEMU_APPLE_PAC_DOMAIN_APDB);
    arm_vmapple_pac_program_b_pair(
        &env->vmapple_pac.el0_apib, &env->vmapple_pac.el0_apdb,
        seed, env->vmapple_pac.el0_diversifier);
    arm_vmapple_pac_program_b_pair(
        &env->vmapple_pac.el1_user_apib,
        &env->vmapple_pac.el1_user_apdb,
        seed, env->vmapple_pac.el1_user_diversifier);
}

static void arm_vmapple_pac_program_el0_diversifier(CPUARMState *env,
                                                     uint64_t diversifier)
{
    env->vmapple_pac.el0_diversifier = diversifier;
    arm_vmapple_pac_program_a_pair(
        &env->vmapple_pac.el0_apia, &env->vmapple_pac.el0_apda,
        env->vmapple_pac.a_seed, diversifier);
    arm_vmapple_pac_program_b_pair(
        &env->vmapple_pac.el0_apib, &env->vmapple_pac.el0_apdb,
        env->vmapple_pac.b_seed, diversifier);
}

static void arm_vmapple_pac_program_el1_user_diversifier(
    CPUARMState *env, uint64_t diversifier)
{
    env->vmapple_pac.el1_user_diversifier = diversifier;
    arm_vmapple_pac_program_a_pair(
        &env->vmapple_pac.el1_user_apia,
        &env->vmapple_pac.el1_user_apda,
        env->vmapple_pac.a_seed, diversifier);
    arm_vmapple_pac_program_b_pair(
        &env->vmapple_pac.el1_user_apib,
        &env->vmapple_pac.el1_user_apdb,
        env->vmapple_pac.b_seed, diversifier);
}

static void arm_vmapple_pac_program_g_key(CPUARMState *env, uint64_t seed)
{
    env->keys.apga = arm_vmapple_pac_derive_key(seed,
                                                QEMU_APPLE_PAC_DOMAIN_APGA);
}

static void arm_vmapple_pac_set_initial_state(CPUARMState *env)
{
    env->vmapple_pac.el0_diversifier =
        QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER;
    env->vmapple_pac.el1_user_diversifier =
        QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER;
    arm_vmapple_pac_program_a_keys(env, QEMU_APPLE_PAC_DEFAULT_A_KEY);
    arm_vmapple_pac_program_b_keys(env, QEMU_APPLE_PAC_DEFAULT_B_KEY);
    arm_vmapple_pac_program_el0_diversifier(
        env, QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER);
    arm_vmapple_pac_program_el1_user_diversifier(
        env, QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER);
    arm_vmapple_pac_program_g_key(env, QEMU_APPLE_PAC_DEFAULT_G_KEY);
    env->vmapple_pac.use_el0_keys_at_el1 = false;
    env->vmapple_pac.active = true;
}

static bool arm_handle_vmapple_pac_hvc_call(CPUARMState *env,
                                            uint64_t function_id)
{
    switch (function_id) {
    case QEMU_APPLE_PAC_SET_INITIAL_STATE:
        arm_vmapple_pac_set_initial_state(env);
        break;
    case QEMU_APPLE_PAC_GET_DEFAULT_KEYS:
        env->xregs[1] = QEMU_APPLE_PAC_DEFAULT_A_KEY;
        env->xregs[2] = QEMU_APPLE_PAC_DEFAULT_B_KEY;
        env->xregs[3] = QEMU_APPLE_PAC_DEFAULT_EL0_DIVERSIFIER;
        env->xregs[4] = QEMU_APPLE_PAC_DEFAULT_G_KEY;
        break;
    case QEMU_APPLE_PAC_SET_A_KEYS:
        arm_vmapple_pac_program_a_keys(env, env->xregs[1]);
        break;
    case QEMU_APPLE_PAC_SET_B_KEYS:
        arm_vmapple_pac_program_b_keys(env, env->xregs[1]);
        break;
    case QEMU_APPLE_PAC_SET_EL0_DIVERSIFIER:
        arm_vmapple_pac_program_el0_diversifier(env, env->xregs[1]);
        break;
    case QEMU_APPLE_PAC_SET_EL0_DIVERSIFIER_AT_EL1:
        if (env->xregs[1] > 1) {
            env->xregs[0] = QEMU_PSCI_RET_INVALID_PARAMS;
            return true;
        }
        if (env->xregs[1] != 0) {
            arm_vmapple_pac_program_el1_user_diversifier(
                env, env->xregs[2]);
            env->vmapple_pac.use_el0_keys_at_el1 = true;
        } else {
            env->vmapple_pac.use_el0_keys_at_el1 = false;
        }
        break;
    case QEMU_APPLE_PAC_SET_G_KEY:
        arm_vmapple_pac_program_g_key(env, env->xregs[1]);
        break;
    default:
        return false;
    }

    env->xregs[0] = QEMU_PSCI_RET_SUCCESS;
    return true;
}

static bool arm_handle_vmapple_hvc_call(CPUARMState *env,
                                        uint64_t function_id)
{
    if (arm_is_vmapple_pac_hvc_function(function_id)) {
        return arm_handle_vmapple_pac_hvc_call(env, function_id);
    }

    switch (function_id) {
    case QEMU_APPLE_PAC_NOP:
        env->xregs[0] = QEMU_PSCI_RET_SUCCESS;
        return true;
    case QEMU_APPLE_OEM_UID:
        /* 3B878185-AA62-4E1F-9DC9-D6799CBB6EBB, per XNU hv_hvc.h. */
        env->xregs[0] = 0x9cbb6ebbULL;
        env->xregs[1] = 0x9dc9d679ULL;
        env->xregs[2] = 0xaa624e1fULL;
        env->xregs[3] = 0x3b878185ULL;
        return true;
    case QEMU_APPLE_OEM_REVISION:
        env->xregs[0] = 1;
        env->xregs[1] = 0;
        return true;
    case QEMU_APPLE_OEM_FEATURES:
        /* Do not advertise WFK/KICK before QEMU implements their semantics. */
        env->xregs[0] = QEMU_APPLE_OEM_FEATURE_UNSUPPORTED;
        return true;
    default:
        return false;
    }
}

static bool arm_is_implemented_psci_function(uint64_t function_id)
{
    switch (function_id) {
    case QEMU_PSCI_0_2_FN_PSCI_VERSION:
    case QEMU_PSCI_0_2_FN_MIGRATE_INFO_TYPE:
    case QEMU_PSCI_0_2_FN_AFFINITY_INFO:
    case QEMU_PSCI_0_2_FN64_AFFINITY_INFO:
    case QEMU_PSCI_0_2_FN_SYSTEM_RESET:
    case QEMU_PSCI_0_2_FN_SYSTEM_OFF:
    case QEMU_PSCI_0_1_FN_CPU_ON:
    case QEMU_PSCI_0_2_FN_CPU_ON:
    case QEMU_PSCI_0_2_FN64_CPU_ON:
    case QEMU_PSCI_0_1_FN_CPU_OFF:
    case QEMU_PSCI_0_2_FN_CPU_OFF:
    case QEMU_PSCI_0_1_FN_CPU_SUSPEND:
    case QEMU_PSCI_0_2_FN_CPU_SUSPEND:
    case QEMU_PSCI_0_2_FN64_CPU_SUSPEND:
    case QEMU_PSCI_1_0_FN_PSCI_FEATURES:
    case QEMU_PSCI_0_1_FN_MIGRATE:
    case QEMU_PSCI_0_2_FN_MIGRATE:
        return true;
    default:
        return false;
    }
}

static bool arm_is_iboot_svc_a0_psci_call(ARMCPU *cpu)
{
    CPUARMState *env = &cpu->env;

    return is_a64(env) &&
           syn_get_ec(env->exception.syndrome) == EC_AA64_SVC &&
           FIELD_EX32(env->exception.syndrome, ISS_IMM16, IMM16) == 0xa0 &&
           arm_is_implemented_psci_function(env->xregs[0]);
}

static bool arm_is_vmapple_svc_a0_hvc_call(ARMCPU *cpu)
{
    CPUARMState *env = &cpu->env;

    return is_a64(env) &&
           (arm_is_implemented_psci_function(env->xregs[0]) ||
            arm_is_vmapple_hvc_function(env->xregs[0]));
}

bool arm_is_psci_call(ARMCPU *cpu, int excp_type)
{
    /*
     * Return true if the exception type matches the configured PSCI conduit.
     * This is called before the SMC/HVC instruction is executed, to decide
     * whether we should treat it as a PSCI call or with the architecturally
     * defined behaviour for an SMC or HVC (which might be UNDEF or trap
     * to EL2 or to EL3).
     */

    switch (excp_type) {
    case EXCP_HVC:
        if (cpu->psci_conduit == QEMU_PSCI_CONDUIT_SVC_A0) {
            return arm_is_vmapple_svc_a0_hvc_call(cpu);
        } else if (cpu->psci_conduit != QEMU_PSCI_CONDUIT_HVC) {
            return false;
        }
        break;
    case EXCP_SMC:
        if (cpu->psci_conduit != QEMU_PSCI_CONDUIT_SMC) {
            return false;
        }
        break;
    case EXCP_SWI:
        if (cpu->psci_conduit == QEMU_PSCI_CONDUIT_SVC_A0) {
            return arm_is_iboot_svc_a0_psci_call(cpu);
        }
        return false;
    default:
        return false;
    }

    return true;
}

void arm_handle_psci_call(ARMCPU *cpu)
{
    /*
     * This function partially implements the logic for dispatching Power State
     * Coordination Interface (PSCI) calls (as described in ARM DEN 0022D.b),
     * to the extent required for bringing up and taking down secondary cores,
     * and for handling reset and poweroff requests.
     * Additional information about the calling convention used is available in
     * the document 'SMC Calling Convention' (ARM DEN 0028)
     */
    CPUARMState *env = &cpu->env;
    uint64_t param[4];
    uint64_t context_id, mpidr;
    uint64_t entry;
    int32_t ret = 0;
    int i;

    for (i = 0; i < 4; i++) {
        /*
         * All PSCI functions take explicit 32-bit or native int sized
         * arguments so we can simply zero-extend all arguments regardless
         * of which exact function we are about to call.
         */
        param[i] = is_a64(env) ? env->xregs[i] : env->regs[i];
    }
    trace_arm_psci_call(param[0], param[1], param[2], param[3],
                        arm_cpu_mp_affinity(cpu), env->pc);

    if (is_a64(env) &&
        syn_get_ec(env->exception.syndrome) == EC_AA64_HVC &&
        FIELD_EX32(env->exception.syndrome, ISS_IMM16, IMM16) == 0 &&
        arm_is_vmapple_hvc_function(param[0])) {
        /*
         * macOS 26 XNU issues vmapple PAC HVCs and then probes the bounded
         * OEM discovery ABI before and after
         * enabling SCTLR_EL1.  On Apple hardware/hypervisor-backed vmapple
         * these initialize, return, and program implementation-defined
         * ARMv8.3-PAuth keys and report optional hypervisor features.  Under
         * Linux TCG there is no EL2 handler, so model only the explicitly
         * implemented calls and let XNU use its fallback when an optional
         * OEM feature is not advertised.  Unknown HVC calls remain
         * architecturally handled instead of being swallowed.
         */
        if (arm_handle_vmapple_hvc_call(env, param[0])) {
            return;
        }
    }

    if ((param[0] & QEMU_PSCI_0_2_64BIT) && !is_a64(env)) {
        ret = QEMU_PSCI_RET_NOT_SUPPORTED;
        goto err;
    }

    switch (param[0]) {
        CPUState *target_cpu_state;
        ARMCPU *target_cpu;

    case QEMU_PSCI_0_2_FN_PSCI_VERSION:
        ret = QEMU_PSCI_VERSION_1_1;
        break;
    case QEMU_PSCI_0_2_FN_MIGRATE_INFO_TYPE:
        ret = QEMU_PSCI_0_2_RET_TOS_MIGRATION_NOT_REQUIRED; /* No trusted OS */
        break;
    case QEMU_PSCI_0_2_FN_AFFINITY_INFO:
    case QEMU_PSCI_0_2_FN64_AFFINITY_INFO:
        mpidr = param[1];

        switch (param[2]) {
        case 0:
            target_cpu_state = arm_get_cpu_by_id(mpidr);
            if (!target_cpu_state) {
                ret = QEMU_PSCI_RET_INVALID_PARAMS;
                break;
            }
            target_cpu = ARM_CPU(target_cpu_state);

            g_assert(bql_locked());
            ret = target_cpu->power_state;
            break;
        default:
            /* Everything above affinity level 0 is always on. */
            ret = 0;
        }
        break;
    case QEMU_PSCI_0_2_FN_SYSTEM_RESET:
        qemu_system_reset_request(SHUTDOWN_CAUSE_GUEST_RESET);
        /* QEMU reset and shutdown are async requests, but PSCI
         * mandates that we never return from the reset/shutdown
         * call, so power the CPU off now so it doesn't execute
         * anything further.
         */
        goto cpu_off;
    case QEMU_PSCI_0_2_FN_SYSTEM_OFF:
        qemu_system_shutdown_request(SHUTDOWN_CAUSE_GUEST_SHUTDOWN);
        goto cpu_off;
    case QEMU_PSCI_0_1_FN_CPU_ON:
    case QEMU_PSCI_0_2_FN_CPU_ON:
    case QEMU_PSCI_0_2_FN64_CPU_ON:
    {
        /* The PSCI spec mandates that newly brought up CPUs start
         * in the highest exception level which exists and is enabled
         * on the calling CPU. Since the QEMU PSCI implementation is
         * acting as a "fake EL3" or "fake EL2" firmware, this for us
         * means that we want to start at the highest NS exception level
         * that we are providing to the guest.
         * The execution mode should be that which is currently in use
         * by the same exception level on the calling CPU.
         * The CPU should be started with the context_id value
         * in x0 (if AArch64) or r0 (if AArch32).
         */
        int target_el = arm_feature(env, ARM_FEATURE_EL2) ? 2 : 1;
        bool target_aarch64 = arm_el_is_aa64(env, target_el);

        mpidr = param[1];
        entry = param[2];
        context_id = param[3];
        ret = arm_set_cpu_on(mpidr, entry, context_id,
                             target_el, target_aarch64);
        break;
    }
    case QEMU_PSCI_0_1_FN_CPU_OFF:
    case QEMU_PSCI_0_2_FN_CPU_OFF:
        goto cpu_off;
    case QEMU_PSCI_0_1_FN_CPU_SUSPEND:
    case QEMU_PSCI_0_2_FN_CPU_SUSPEND:
    case QEMU_PSCI_0_2_FN64_CPU_SUSPEND:
        /* Affinity levels are not supported in QEMU */
        if (param[1] & 0xfffe0000) {
            ret = QEMU_PSCI_RET_INVALID_PARAMS;
            break;
        }
        /* Powerdown is not supported, we always go into WFI */
        if (is_a64(env)) {
            env->xregs[0] = 0;
        } else {
            env->regs[0] = 0;
        }
        helper_wfi(env, 4);
        break;
    case QEMU_PSCI_1_0_FN_PSCI_FEATURES:
        switch (param[1]) {
        case QEMU_PSCI_0_2_FN_PSCI_VERSION:
        case QEMU_PSCI_0_2_FN_MIGRATE_INFO_TYPE:
        case QEMU_PSCI_0_2_FN_AFFINITY_INFO:
        case QEMU_PSCI_0_2_FN64_AFFINITY_INFO:
        case QEMU_PSCI_0_2_FN_SYSTEM_RESET:
        case QEMU_PSCI_0_2_FN_SYSTEM_OFF:
        case QEMU_PSCI_0_1_FN_CPU_ON:
        case QEMU_PSCI_0_2_FN_CPU_ON:
        case QEMU_PSCI_0_2_FN64_CPU_ON:
        case QEMU_PSCI_0_1_FN_CPU_OFF:
        case QEMU_PSCI_0_2_FN_CPU_OFF:
        case QEMU_PSCI_0_1_FN_CPU_SUSPEND:
        case QEMU_PSCI_0_2_FN_CPU_SUSPEND:
        case QEMU_PSCI_0_2_FN64_CPU_SUSPEND:
        case QEMU_PSCI_1_0_FN_PSCI_FEATURES:
            if (!(param[1] & QEMU_PSCI_0_2_64BIT) || is_a64(env)) {
                ret = 0;
                break;
            }
            /* fallthrough */
        case QEMU_PSCI_0_1_FN_MIGRATE:
        case QEMU_PSCI_0_2_FN_MIGRATE:
        default:
            ret = QEMU_PSCI_RET_NOT_SUPPORTED;
            break;
        }
        break;
    case QEMU_PSCI_0_1_FN_MIGRATE:
    case QEMU_PSCI_0_2_FN_MIGRATE:
    default:
        ret = QEMU_PSCI_RET_NOT_SUPPORTED;
        break;
    }

err:
    if (is_a64(env)) {
        env->xregs[0] = ret;
    } else {
        env->regs[0] = ret;
    }
    return;

cpu_off:
    ret = arm_set_cpu_off(arm_cpu_mp_affinity(cpu));
    /* notreached */
    /* sanity check in case something failed */
    assert(ret == QEMU_ARM_POWERCTL_RET_SUCCESS);
}
