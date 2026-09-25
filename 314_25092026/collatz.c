#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <omp.h>

#define MOD_VAL 1000000007ULL

static inline uint32_t collatz_steps(uint64_t n) {
    uint32_t steps = 0;
    while (n > 1) {
        if ((n & 1) == 0) {
            n >>= 1;
        } else {
            n = 3 * n + 1;
        }
        steps++;
    }
    return steps;
}

void run_sequential(uint64_t N, uint32_t *out_max_steps, uint64_t *out_checksum) {
    uint32_t max_steps = 0;
    uint64_t checksum = 0;

    for (uint64_t i = 1; i <= N; i++) {
        uint32_t steps = collatz_steps(i);
        if (steps > max_steps) {
            max_steps = steps;
        }
        checksum = (checksum + steps) % MOD_VAL;
    }

    *out_max_steps = max_steps;
    *out_checksum = checksum;
}

void run_parallel(uint64_t N, int threads, uint32_t *out_max_steps, uint64_t *out_checksum) {
    uint32_t max_steps = 0;
    uint64_t checksum_sum = 0;

    omp_set_num_threads(threads);

    #pragma omp parallel for reduction(max:max_steps) reduction(+:checksum_sum) schedule(static)
    for (uint64_t i = 1; i <= N; i++) {
        uint32_t steps = collatz_steps(i);
        if (steps > max_steps) {
            max_steps = steps;
        }
        checksum_sum += steps;
    }

    *out_max_steps = max_steps;
    *out_checksum = checksum_sum % MOD_VAL;
}

uint64_t run_false_sharing_naive(uint64_t N, int threads) {
    int hit_count[128] = {0};
    omp_set_num_threads(threads);

    #pragma omp parallel for schedule(static)
    for (uint64_t i = 1; i <= N; i++) {
        if (collatz_steps(i) > 100) {
            hit_count[omp_get_thread_num()]++;
        }
    }

    uint64_t total = 0;
    for (int i = 0; i < threads; i++) {
        total += hit_count[i];
    }
    return total;
}

uint64_t run_false_sharing_reduction(uint64_t N, int threads) {
    uint64_t total_hits = 0;
    omp_set_num_threads(threads);

    #pragma omp parallel for reduction(+:total_hits) schedule(static)
    for (uint64_t i = 1; i <= N; i++) {
        if (collatz_steps(i) > 100) {
            total_hits++;
        }
    }
    return total_hits;
}

void run_scheduled(uint64_t N, int threads, int sched_type) {
    omp_set_num_threads(threads);
    uint32_t max_steps = 0;

    if (sched_type == 0) {
        #pragma omp parallel for reduction(max:max_steps) schedule(static)
        for (uint64_t i = 1; i <= N; i++) {
            uint32_t s = collatz_steps(i);
            if (s > max_steps) max_steps = s;
        }
    } else if (sched_type == 1) {
        #pragma omp parallel for reduction(max:max_steps) schedule(static, 1000)
        for (uint64_t i = 1; i <= N; i++) {
            uint32_t s = collatz_steps(i);
            if (s > max_steps) max_steps = s;
        }
    } else if (sched_type == 2) {
        #pragma omp parallel for reduction(max:max_steps) schedule(dynamic, 100)
        for (uint64_t i = 1; i <= N; i++) {
            uint32_t s = collatz_steps(i);
            if (s > max_steps) max_steps = s;
        }
    } else if (sched_type == 3) {
        #pragma omp parallel for reduction(max:max_steps) schedule(dynamic, 10000)
        for (uint64_t i = 1; i <= N; i++) {
            uint32_t s = collatz_steps(i);
            if (s > max_steps) max_steps = s;
        }
    } else if (sched_type == 4) {
        #pragma omp parallel for reduction(max:max_steps) schedule(guided)
        for (uint64_t i = 1; i <= N; i++) {
            uint32_t s = collatz_steps(i);
            if (s > max_steps) max_steps = s;
        }
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;

    uint64_t N = atoll(argv[1]);
    int mode = (argc >= 3) ? atoi(argv[2]) : 0;
    int threads = (argc >= 4) ? atoi(argv[3]) : 1;
    int sched_type = (argc >= 5) ? atoi(argv[4]) : 0;

    uint32_t max_s = 0;
    uint64_t chk = 0;

    if (mode == 0) {
        run_sequential(N, &max_s, &chk);
        printf("SEQ,%llu,%u,%llu\n", N, max_s, chk);
    } else if (mode == 1) {
        run_parallel(N, threads, &max_s, &chk);
        printf("PAR,%d,%llu,%u,%llu\n", threads, N, max_s, chk);
    } else if (mode == 2) {
        uint64_t hits = run_false_sharing_naive(N, threads);
        printf("FS_NAIVE,%d,%llu\n", threads, hits);
    } else if (mode == 3) {
        uint64_t hits = run_false_sharing_reduction(N, threads);
        printf("FS_MITIGATED,%d,%llu\n", threads, hits);
    } else if (mode == 4) {
        run_scheduled(N, threads, sched_type);
        printf("SCHED,%d,%d\n", threads, sched_type);
    }

    return 0;
}
