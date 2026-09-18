// Part2.cpp
#include <iostream>
#include <thread>
#include <vector>
#include <atomic>
#include <chrono>
#include <random>

const long TOTAL_POINTS = 50000000;
const int NUM_THREADS = 4;
std::atomic<long> atomicHits(0);

void workerAtomic(long points) {
    thread_local std::mt19937 gen(std::random_device{}());
    thread_local std::uniform_real_distribution<double> dis(0.0, 1.0);

    for (long i = 0; i < points; ++i) {
        double x = dis(gen);
        double y = dis(gen);
        if (x * x + y * y <= 1.0) {
            atomicHits.fetch_add(1, std::memory_order_relaxed); // Атомарная операция
        }
    }
}

int main() {
    std::cout << "=== Part 2: The Synchronization Trap ===" << std::endl;

    // 1. Однопоточный запуск
    auto start = std::chrono::high_resolution_clock::now();
    long singleHits = 0;
    std::mt19937 gen(1337);
    std::uniform_real_distribution<double> dis(0.0, 1.0);
    for (long i = 0; i < TOTAL_POINTS; ++i) {
        double x = dis(gen);
        double y = dis(gen);
        if (x * x + y * y <= 1.0) singleHits++;
    }
    auto end = std::chrono::high_resolution_clock::now();
    long singleTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    std::cout << "Однопоточный: Pi = " << (4.0 * singleHits / TOTAL_POINTS) 
              << ", Время = " << singleTime << " ms" << std::endl;

    // 2. Многопоточный с std::atomic
    start = std::chrono::high_resolution_clock::now();
    long pointsPerThread = TOTAL_POINTS / NUM_THREADS;
    std::vector<std::thread> threads;

    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back(workerAtomic, pointsPerThread);
    }

    for (auto& t : threads) {
        t.join();
    }
    end = std::chrono::high_resolution_clock::now();
    long atomicTime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

    std::cout << "Atomic (" << NUM_THREADS << " потока): Pi = " 
              << (4.0 * atomicHits / TOTAL_POINTS) 
              << ", Время = " << atomicTime << " ms" << std::endl;

    return 0;
}