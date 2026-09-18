// Part3_std.cpp
#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <random>
#include <iomanip>

const long TOTAL_POINTS = 100000000;
const int THREAD_COUNTS[] = {1, 2, 4, 8, 16, 32};

void workerReduction(long points, long& localResult) {
    thread_local std::mt19937 gen(std::random_device{}());
    thread_local std::uniform_real_distribution<double> dis(0.0, 1.0);

    long hits = 0;
    for (long i = 0; i < points; ++i) {
        double x = dis(gen);
        double y = dis(gen);
        if (x * x + y * y <= 1.0) {
            hits++;
        }
    }
    localResult = hits; // Запись только 1 раз в конце
}

int main() {
    std::cout << "=== Part 3: OpenMP-Style Reduction ===" << std::endl;
    std::cout << std::left << std::setw(12) << "Threads(T)" 
              << " | " << std::setw(12) << "Runtime(ms)" 
              << " | " << std::setw(18) << "Speedup (T1/TT)" 
              << " | " << std::setw(12) << "Efficiency" << std::endl;
    std::cout << std::string(60, '-') << std::endl;

    double baselineTime = 0.0;

    for (int tCount : THREAD_COUNTS) {
        long pointsPerThread = TOTAL_POINTS / tCount;
        std::vector<std::thread> threads;
        std::vector<long> localHits(tCount, 0);

        auto start = std::chrono::high_resolution_clock::now();

        for (int i = 0; i < tCount; ++i) {
            threads.emplace_back(workerReduction, pointsPerThread, std::ref(localHits[i]));
        }

        long totalHits = 0;
        for (int i = 0; i < tCount; ++i) {
            threads[i].join();
            totalHits += localHits[i];
        }

        auto end = std::chrono::high_resolution_clock::now();
        double runtime = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

        if (tCount == 1) {
            baselineTime = runtime;
        }

        double speedup = baselineTime / runtime;
        double efficiency = (speedup / tCount) * 100.0;

        std::cout << std::left << std::setw(12) << tCount 
                  << " | " << std::setw(12) << runtime 
                  << " | " << std::setw(16) << std::fixed << std::setprecision(2) << speedup << "x"
                  << " | " << std::setw(11) << std::setprecision(1) << efficiency << "%" << std::endl;
    }
    return 0;
}