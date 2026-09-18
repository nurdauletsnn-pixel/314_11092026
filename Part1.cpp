// Part1.cpp
#include <iostream>
#include <thread>
#include <vector>
#include <random>

long totalHits = 0; // Общая переменная с гонкой данных
const long TOTAL_POINTS = 50000000;
const int NUM_THREADS = 4;

void worker(long points) {
    // Генератор случайных чисел для каждого потока свой
    thread_local std::mt19937 gen(std::random_device{}());
    thread_local std::uniform_real_distribution<double> dis(0.0, 1.0);

    for (long i = 0; i < points; ++i) {
        double x = dis(gen);
        double y = dis(gen);
        if (x * x + y * y <= 1.0) {
            totalHits++; // Data Race!
        }
    }
}

int main() {
    std::cout << "=== Part 1: Phantom Bug ===" << std::endl;
    for (int run = 1; run <= 5; ++run) {
        totalHits = 0;
        long pointsPerThread = TOTAL_POINTS / NUM_THREADS;
        std::vector<std::thread> threads;

        for (int i = 0; i < NUM_THREADS; ++i) {
            threads.emplace_back(worker, pointsPerThread);
        }

        for (auto& t : threads) {
            t.join();
        }

        double pi = 4.0 * totalHits / TOTAL_POINTS;
        std::cout << "Запуск " << run << ": Pi = " << pi << " (Hits: " << totalHits << ")" << std::endl;
    }
    return 0;
}