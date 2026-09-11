import time
import math
from concurrent.futures import ProcessPoolExecutor

def is_prime(n):
    if n < 2: 
        return False
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0: 
            return False
    return True

def work(args):
    start, end = args
    return sum(1 for i in range(start, end) if is_prime(i))

def run_bench(threads, target=5000000):
    chunk = target // threads
    ranges = [(i * chunk, target if i == threads - 1 else (i + 1) * chunk) for i in range(threads)]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=threads) as executor:
        list(executor.map(work, ranges))
    return time.perf_counter() - t0

if __name__ == "__main__":
    thread_list = [1, 2, 4, 8, 16, 32]
    t1_avg = 0.0
    print("Threads | Run 1 (s) | Run 2 (s) | Run 3 (s) | Avg T_N (s) | Speedup S_N | Efficiency E_N")
    for n in thread_list:
        runs = [run_bench(n) for _ in range(3)]
        avg = sum(runs) / 3.0
        if n == 1:
            t1_avg = avg
        speedup = t1_avg / avg
        eff = (speedup / n) * 100
        print(f"N={n:<2}    | {runs[0]:.3f}     | {runs[1]:.3f}     | {runs[2]:.3f}     | {avg:.3f}       | {speedup:.2f}x       | {eff:.1f}%")
