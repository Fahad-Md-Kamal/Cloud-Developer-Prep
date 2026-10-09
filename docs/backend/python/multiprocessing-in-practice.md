---
title: "Multiprocessing in Practice"
---

# Multiprocessing in Practice

Hands-on tasks for CPU-bound parallelism — where threading can't
help, because the GIL means only one thread executes Python bytecode
at a time regardless of thread count. Builds on
[Threading in Practice](threading-in-practice.md); do these after that
page, since several concepts (worker pools, queues) carry over with
process-specific differences.

## Task 1: Parallelize a CPU-bound task with `multiprocessing.Pool`

**The task:** count primes up to N, sequentially and then in
parallel, and notice where parallelism actually pays off.

```python
import time
from multiprocessing import Pool

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

numbers = list(range(2, 200_000))

# Sequential
start = time.perf_counter()
sequential_result = [n for n in numbers if is_prime(n)]
print(f"sequential: {time.perf_counter() - start:.2f}s")

# Parallel — actually uses multiple CPU cores
start = time.perf_counter()
with Pool(processes=4) as pool:
    flags = pool.map(is_prime, numbers)
parallel_result = [n for n, flag in zip(numbers, flags) if flag]
print(f"parallel: {time.perf_counter() - start:.2f}s")

assert sequential_result == parallel_result
```

- Unlike `ThreadPoolExecutor`, this genuinely runs on multiple CPU
  cores simultaneously — each process has its own Python interpreter
  and its own GIL, so they don't contend with each other the way
  threads do.
- **Process creation has real overhead** — each worker process starts
  a fresh Python interpreter and re-imports your module. For a task
  this cheap per-item, most of the wall-clock time can be
  pool-startup cost, not actual work. Try it with `numbers = list(range(2, 2_000_000))`
  instead and the parallel version's advantage becomes obvious — the
  per-item work has to be substantial enough to amortize the fixed
  overhead.
- `pool.map` blocks until *all* results are ready, in input order —
  fine here since we need the whole list; use `imap` or
  `imap_unordered` instead when you want to start processing results
  as they arrive rather than waiting for the entire batch.
- **`chunksize`** (an optional `pool.map` argument) controls how many
  items get sent to each worker per round-trip — the default
  auto-chunks reasonably, but for a very large number of very cheap
  items, an explicit larger chunksize reduces IPC overhead
  meaningfully. Worth knowing it exists even if you don't tune it
  every time.

## Task 2: Share state between processes correctly

**The task:** a counter incremented by multiple processes — the same
shape as Threading in Practice's Task 1, but processes don't share
memory by default, so the naive version fails differently.

```python
from multiprocessing import Process, Value, Lock

def increment(counter, lock, n: int):
    for _ in range(n):
        with lock:
            counter.value += 1

counter = Value("i", 0)  # a shared integer, backed by shared memory
lock = Lock()            # multiprocessing.Lock, not threading.Lock

processes = [Process(target=increment, args=(counter, lock, 100_000)) for _ in range(4)]
for p in processes:
    p.start()
for p in processes:
    p.join()

print(counter.value)  # 400_000
```

- A plain Python integer (or any normal object) **cannot** be shared
  between processes the way a global variable is shared between
  threads — each process gets its own independent copy of everything
  at fork time. Try passing a plain `int` instead of a `Value` and
  watch each process silently increment its own separate copy,
  printing `0` at the end since the parent's original `counter`
  variable was never touched at all.
- `Value("i", 0)` allocates an integer in memory genuinely shared
  across processes (backed by the OS, not Python's normal heap) — the
  `"i"` is a C-type code (signed int), the same typecodes as the
  `array` module.
- The lock still matters, for the exact same read-modify-write reason
  as Task 1 in threading — but it must be a `multiprocessing.Lock`,
  not a `threading.Lock`, since it needs to coordinate across process
  boundaries, not just threads within one process.
- For anything more complex than a single number (a shared dict, a
  shared list), reach for `multiprocessing.Manager()` instead —
  it runs a separate server process holding the real object, and
  every worker talks to it via a proxy. Simpler to use than raw shared
  memory, at the cost of extra IPC overhead per access.

## Task 3: A process pool with real error handling

**The task:** some tasks fail — make sure a single failure doesn't
crash the whole pool, and that you can tell which task failed and why.

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def risky_task(n: int) -> int:
    if n == 7:
        raise ValueError(f"deliberately broken on {n}")
    return n * n

with ProcessPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(risky_task, i): i for i in range(10)}
    for future in as_completed(futures):
        n = futures[future]
        try:
            print(f"{n} -> {future.result()}")
        except ValueError as exc:
            print(f"{n} failed: {exc}")
```

- An exception raised inside a worker process is pickled, sent back
  to the parent, and re-raised when `.result()` is called on that
  specific future — the other 9 tasks are entirely unaffected.
- This is the same `try/except`-around-`.result()` pattern as
  [Threading in Practice's Task 2](threading-in-practice.md#task-2-build-a-bounded-worker-pool-for-io-bound-work)
  — `ProcessPoolExecutor` and `ThreadPoolExecutor` share the same
  `concurrent.futures` interface deliberately, so code written against
  one mostly transfers to the other once the actual task is CPU-bound
  vs. I/O-bound.
- **What doesn't transfer**: anything you pass to a process pool
  (arguments, and the function itself if it's not a top-level, easily
  importable function) must be picklable — a lambda, a bound method
  on a non-picklable object, or an open file handle will fail with a
  pickling error specific to multiprocessing, a class of bug threading
  never has since threads share memory directly.

---

## Code Samples

No dedicated code samples yet for this section — the tasks above are
meant to be typed and run directly.
