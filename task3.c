#include <stdio.h>
#include <pthread.h>
#include <sys/time.h>

#define NUM_THREADS 10
#define INCREMENTS 1000000

long long shared_counter = 0;
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

void* count_unsynced(void* arg) {
    for (int i = 0; i < INCREMENTS; i++) {
        shared_counter++;
    }
    return NULL;
}

void* count_synced(void* arg) {
    for (int i = 0; i < INCREMENTS; i++) {
        pthread_mutex_lock(&lock);
        shared_counter++;
        pthread_mutex_unlock(&lock);
    }
    return NULL;
}

double get_time_ms() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (tv.tv_sec * 1000.0) + (tv.tv_usec / 1000.0);
}

int main() {
    for (int run = 1; run <= 10; run++) {
        shared_counter = 0;
        pthread_t threads[NUM_THREADS];
        for (int i = 0; i < NUM_THREADS; i++) pthread_create(&threads[i], NULL, count_unsynced, NULL);
        for (int i = 0; i < NUM_THREADS; i++) pthread_join(threads[i], NULL);
        long long act = shared_counter;
        printf("Run #%d: Measured = %lld | Error = %lld\n", run, act, 10000000LL - act);
    }

    double t0 = get_time_ms();
    shared_counter = 0;
    pthread_t threads[NUM_THREADS];
    for (int i = 0; i < NUM_THREADS; i++) pthread_create(&threads[i], NULL, count_unsynced, NULL);
    for (int i = 0; i < NUM_THREADS; i++) pthread_join(threads[i], NULL);
    double t_unlocked = get_time_ms() - t0;

    t0 = get_time_ms();
    shared_counter = 0;
    for (int i = 0; i < NUM_THREADS; i++) pthread_create(&threads[i], NULL, count_synced, NULL);
    for (int i = 0; i < NUM_THREADS; i++) pthread_join(threads[i], NULL);
    double t_locked = get_time_ms() - t0;

    printf("\nUnlocked = %.2f ms vs. Locked = %.2f ms\n", t_unlocked, t_locked);
    return 0;
}
