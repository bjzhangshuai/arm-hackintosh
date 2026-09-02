#define _GNU_SOURCE
#include <errno.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static volatile uint64_t sink;

static double now_seconds(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0) {
        perror("clock_gettime");
        exit(2);
    }
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1000000000.0;
}

static uint64_t rotl64(uint64_t x, unsigned n) {
    return (x << n) | (x >> (64U - n));
}

static void emit(const char *name, double seconds, uint64_t work, uint64_t checksum) {
    printf("{\"case\":\"%s\",\"seconds\":%.9f,\"work\":%llu,\"checksum\":\"%016llx\"}\n",
           name, seconds, (unsigned long long)work, (unsigned long long)checksum);
}

__attribute__((noinline)) static void bench_integer(void) {
    const uint64_t iterations = 50000000ULL;
    uint64_t a = 0x243f6a8885a308d3ULL;
    uint64_t b = 0x13198a2e03707344ULL;
    double start = now_seconds();
    for (uint64_t i = 0; i < iterations; ++i) {
        a += (b ^ i) * 0x9e3779b185ebca87ULL;
        b = rotl64(b ^ a, 17) + 0xc2b2ae3d27d4eb4fULL;
        a ^= a >> 29;
    }
    double elapsed = now_seconds() - start;
    sink = a ^ b;
    emit("integer", elapsed, iterations, sink);
}

__attribute__((noinline)) static void bench_branch(void) {
    const size_t bytes = 1U << 20;
    const uint64_t passes = 32;
    uint8_t *data = malloc(bytes);
    if (!data) {
        perror("malloc branch");
        exit(2);
    }
    uint32_t state = 0x12345678U;
    for (size_t i = 0; i < bytes; ++i) {
        state = state * 1664525U + 1013904223U;
        data[i] = (uint8_t)(state >> 24);
    }
    volatile const uint8_t *vdata = data;
    uint64_t sum = 0;
    double start = now_seconds();
    for (uint64_t pass = 0; pass < passes; ++pass) {
        for (size_t i = 0; i < bytes; ++i) {
            if (vdata[i] & 1U) {
                sum += (uint64_t)vdata[i] + pass;
            } else {
                sum ^= ((uint64_t)vdata[i] << (pass & 7U));
            }
        }
    }
    double elapsed = now_seconds() - start;
    free(data);
    sink = sum;
    emit("branch", elapsed, bytes * passes, sink);
}

__attribute__((noinline)) static void bench_sequential_memory(void) {
    const size_t words = 8U * 1024U * 1024U;
    const uint64_t passes = 4;
    uint64_t *data = aligned_alloc(64, words * sizeof(*data));
    if (!data) {
        perror("aligned_alloc memory");
        exit(2);
    }
    for (size_t i = 0; i < words; ++i) {
        data[i] = (uint64_t)i * 0x9e3779b185ebca87ULL;
    }
    volatile const uint64_t *vdata = data;
    uint64_t sum = 0;
    double start = now_seconds();
    for (uint64_t pass = 0; pass < passes; ++pass) {
        for (size_t i = 0; i < words; ++i) {
            sum += vdata[i] ^ pass;
        }
    }
    double elapsed = now_seconds() - start;
    free(data);
    sink = sum;
    emit("memory_seq", elapsed, words * passes, sink);
}

__attribute__((noinline)) static void bench_pointer_chase(void) {
    const uint32_t count = 1U << 20;
    const uint64_t steps = 8ULL * count;
    uint32_t *next = aligned_alloc(64, (size_t)count * sizeof(*next));
    uint32_t *order = malloc((size_t)count * sizeof(*order));
    if (!next || !order) {
        perror("malloc pointer");
        exit(2);
    }
    for (uint32_t i = 0; i < count; ++i) order[i] = i;
    uint32_t state = 0x6d2b79f5U;
    for (uint32_t i = count - 1; i > 0; --i) {
        state = state * 1664525U + 1013904223U;
        uint32_t j = state % (i + 1U);
        uint32_t tmp = order[i]; order[i] = order[j]; order[j] = tmp;
    }
    for (uint32_t i = 0; i < count; ++i) next[order[i]] = order[(i + 1U) & (count - 1U)];
    uint32_t at = order[0];
    volatile const uint32_t *vnext = next;
    double start = now_seconds();
    for (uint64_t i = 0; i < steps; ++i) at = vnext[at];
    double elapsed = now_seconds() - start;
    free(order);
    free(next);
    sink = at;
    emit("pointer_chase", elapsed, steps, sink);
}

__attribute__((noinline)) static void bench_syscall(void) {
    const uint64_t iterations = 200000ULL;
    uint64_t completed = 0;
    double start = now_seconds();
    for (uint64_t i = 0; i < iterations; ++i) {
        long result = syscall(SYS_getpid);
        completed += result > 0;
    }
    double elapsed = now_seconds() - start;
    sink = completed;
    emit("syscall", elapsed, iterations, sink);
}

__attribute__((noinline)) static void bench_atomic(void) {
    const uint64_t iterations = 20000000ULL;
    _Atomic uint64_t counter = 0;
    double start = now_seconds();
    for (uint64_t i = 0; i < iterations; ++i) {
        atomic_fetch_add_explicit(&counter, 1, memory_order_relaxed);
    }
    double elapsed = now_seconds() - start;
    sink = atomic_load_explicit(&counter, memory_order_relaxed);
    emit("atomic", elapsed, iterations, sink);
}

int main(void) {
    bench_integer();
    bench_branch();
    bench_sequential_memory();
    bench_pointer_chase();
    bench_syscall();
    bench_atomic();
    return sink == UINT64_MAX;
}
