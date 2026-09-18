import threading
import time

TOTAL_OPS = 2_000_000
NUM_THREADS = 4

class UnsafeCounter:
    def __init__(self): self.val = 0
    def inc(self): self.val += 1

class LockedCounter:
    def __init__(self):
        self.val = 0
        self.lock = threading.Lock()
    def inc(self):
        with self.lock:
            self.val += 1

class LocklessCounter:
    def __init__(self):
        self.buffers = [0] * NUM_THREADS

    def work(self, tid, ops_per_thread):
        acc = 0
        for _ in range(ops_per_thread):
            acc += 1
        self.buffers[tid] = acc

    def reduce(self):
        return sum(self.buffers)

def bench(counter_type):
    c = counter_type()
    ops_per_thread = TOTAL_OPS // NUM_THREADS
    def work():
        for _ in range(ops_per_thread):
            c.inc()
    threads = [threading.Thread(target=work) for _ in range(NUM_THREADS)]
    start = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join()
    return c.val, time.perf_counter() - start

def bench_lockless():
    c = LocklessCounter()
    ops_per_thread = TOTAL_OPS // NUM_THREADS
    threads = [threading.Thread(target=c.work, args=(i, ops_per_thread)) for i in range(NUM_THREADS)]
    start = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join()
    val = c.reduce()
    return val, time.perf_counter() - start

if __name__ == "__main__":
    val_unsafe, t_unsafe = bench(UnsafeCounter)
    val_locked, t_locked = bench(LockedCounter)
    val_lockless, t_lockless = bench_lockless()

    print(f"Unsafe: Value = {val_unsafe:,} / {TOTAL_OPS:,} | Time: {t_unsafe:.4f}s")
    print(f"Locked: Value = {val_locked:,} / {TOTAL_OPS:,} | Time: {t_locked:.4f}s")
    print(f"Lockless: Value = {val_lockless:,} / {TOTAL_OPS:,} | Time: {t_lockless:.4f}s")
    print(f"Contention Cost Multiplier: {t_locked / t_unsafe:.2f}x")
    print(f"Lockless Speedup over Locked: {t_locked / t_lockless:.2f}x")