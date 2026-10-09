---
title: "Threading in Practice"
---

# Threading in Practice

Hands-on tasks to build real depth on Python threading, beyond
knowing the GIL exists. Builds on
[Concurrency & AsyncIO](concurrency-and-asyncio.md)'s decision
framework — this page is where you actually write the code. Do each
task yourself before reading the explanation.

## Task 1: Reproduce a race condition, then fix it

**The task:** run this, and predict the output before you look at it.

```python
import threading

counter = 0

def increment():
    global counter
    for _ in range(100_000):
        counter += 1

threads = [threading.Thread(target=increment) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(counter)  # you'd expect 400_000 — do you get it?
```

!!! warning "On modern CPython, you might actually get 400,000"
    On CPython 3.11+/3.12, this *exact* loop shape often prints the
    correct `400000` every single time, which looks like proof the
    race doesn't exist. It isn't proof of that — see
    ["Why this specific loop doesn't reliably show the race"](#why-this-specific-loop-doesnt-reliably-show-the-race)
    below before concluding the GIL made this safe.

**What's actually happening:**

- `counter += 1` looks like one operation but isn't — it's
  read-current-value, add-one, write-new-value as three separate
  steps at the bytecode level.
- The GIL guarantees only one thread executes Python bytecode at a
  time, but it can switch threads *between* those three steps, not
  just between statements.
- Thread A reads `counter` as 5, gets paused, Thread B reads it as 5
  too, both compute 6, both write 6 back — one increment is silently
  lost. Run it enough times with enough threads and the final count is
  reliably *less* than 400,000, by a different amount each run.

**The fix:**

```python
import threading

counter = 0
lock = threading.Lock()

def increment():
    global counter
    for _ in range(100_000):
        with lock:
            counter += 1

threads = [threading.Thread(target=increment) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(counter)  # now reliably 400_000
```

- `with lock:` ensures only one thread can execute the
  read-modify-write sequence at a time — the other threads block until
  it's released.
- **The interview-level insight**: the GIL prevents two threads from
  executing Python bytecode *simultaneously*, but it does **not**
  make multi-step operations atomic. "The GIL means I don't need
  locks" is a genuinely common, genuinely wrong belief — this exercise
  is the concrete counterexample.

### Why this specific loop doesn't reliably show the race

If you ran Task 1's first snippet and got exactly `400000` every time,
you haven't disproven the race — you've hit a CPython implementation
detail. `dis.dis` on the loop body shows why:

```
>>   24 FOR_ITER      11 (to 50)
     28 STORE_FAST     0 (_)
     30 LOAD_GLOBAL    2 (counter)
     40 LOAD_CONST     2 (1)
     42 BINARY_OP     13 (+=)
     46 STORE_GLOBAL   1 (counter)
     48 JUMP_BACKWARD 13 (to 24)
```

- CPython doesn't check whether it should switch threads at *every*
  bytecode instruction — only at specific checkpoints: loop backedges
  (`JUMP_BACKWARD`), function calls (`CALL`), and a few others.
- `counter`'s entire read-modify-write (`LOAD_GLOBAL` →
  `BINARY_OP` → `STORE_GLOBAL`) sits *between* two checkpoints
  (`FOR_ITER` and `JUMP_BACKWARD`) with no checkpoint inside it — so a
  thread that starts one increment is guaranteed to finish it before
  the GIL can be taken away. The read-modify-write ends up accidentally
  atomic for *this specific loop shape*, not because Python promises
  that anywhere.
- Proof the race is still real: insert a function call between the
  read and the write — a `CALL` *is* a checkpoint, so now a thread can
  be interrupted mid-increment:

```python
def identity(x):  # a plain call forces a bytecode CALL checkpoint
    return x

def increment():
    global counter
    for _ in range(100_000):
        counter = counter + identity(1)  # now races reliably
```

- Run that version across 4 threads and the final count comes in
  under 400,000, inconsistently, every run — the hazard was always
  there; this loop shape just happened not to expose it.
- **Don't rely on this.** Which instructions count as a "checkpoint"
  is a CPython implementation detail, not a language guarantee — it
  has changed across Python versions before and can again. The lock
  from the fix above is the only thing that's actually guaranteed.

### Seeing the race happen, not just the wrong number

A wrong final number proves *that* updates were lost, but not *how*.
Slowing the read-modify-write down with a deliberate delay — and
printing every step — makes the lost update itself visible:

```python
import threading
import time

def visual_race_demo():
    shared = 0
    print("--- Visual race condition demo (2 threads, 5 increments each) ---\n")

    def worker(name):
        nonlocal shared
        for _ in range(5):
            read_value = shared
            print(f"[{name}] READ  counter = {read_value}")
            time.sleep(0.05)  # widen the window so both threads read before either writes
            new_value = read_value + 1
            shared = new_value
            print(f"[{name}] WRITE counter = {new_value}")
            time.sleep(0.05)

    t1 = threading.Thread(target=worker, args=("Thread-A",))
    t2 = threading.Thread(target=worker, args=("Thread-B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"\nFinal counter = {shared}  (expected 10 if no updates were lost)")
```

Output — both threads consistently read the same stale value before
either writes back, so every single increment is lost, not just some:

```
[Thread-A] READ  counter = 4
[Thread-B] READ  counter = 4     <- both read the same stale value
[Thread-A] WRITE counter = 5
[Thread-B] WRITE counter = 5     <- Thread-A's increment is silently lost
...
Final counter = 5  (expected 10 if no updates were lost)
```

- The symmetric `time.sleep(0.05)` on both sides of the read-modify-write
  is what makes this 100% reproducible instead of relying on a race
  that may or may not happen to occur — both threads are pushed through
  the same read-then-sleep-then-write rhythm in lockstep, so they
  collide on every iteration rather than occasionally.
- The fix is the same as above: wrap the read-modify-write in
  `with lock:` and every increment lands correctly, because now only
  one thread can be between `READ` and `WRITE` at a time — try it and
  rerun to see the output change from losing updates to a clean count
  of `10`.

## Task 2: Build a bounded worker pool for I/O-bound work

**The task:** fetch 20 URLs concurrently, but never more than 5 at
once, and collect results as they finish (not necessarily in the
order you submitted them).

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch(url: str) -> str:
    # stand-in for a real request — replace with requests.get(url).text
    time.sleep(0.5)
    return f"content of {url}"

urls = [f"https://example.com/page/{i}" for i in range(20)]

with ThreadPoolExecutor(max_workers=5) as pool:
    futures = {pool.submit(fetch, url): url for url in urls}
    for future in as_completed(futures):
        url = futures[future]
        try:
            result = future.result()
            print(f"done: {url} -> {len(result)} chars")
        except Exception as exc:
            print(f"failed: {url} -> {exc}")
```

- `ThreadPoolExecutor` is the standard tool for this — don't hand-roll
  `Thread` objects and a semaphore unless you have a reason to.
- `max_workers=5` bounds concurrency deliberately. For I/O-bound work,
  this number is usually much higher than your CPU core count, since
  threads spend nearly all their time *waiting*, not computing — the
  real ceiling is usually the target server's rate limit or your own
  memory, not CPU.
- `as_completed` yields futures as they finish, not in submission
  order — the right choice when you want to process results as soon
  as they're ready rather than waiting for a specific one.
- Wrapping `future.result()` in `try/except` matters: an exception
  raised inside the worker function is stored on the future and only
  re-raised when you call `.result()` — a bare loop with no
  `try/except` will crash on the first failed request rather than
  reporting it and continuing.

**Extend it yourself:** replace `fetch` with a real `requests.get`
call, and change `max_workers` to 1, 5, and 50 — time each run. At
some point past the target server's actual capacity, more workers
stops helping and starts just producing more failed/rate-limited
requests. Finding that point by measurement, not guessing, is the
actual skill.

## Task 3: A producer/consumer pipeline with `queue.Queue`

**The task:** one producer thread generates work items; three
consumer threads process them; shut down cleanly when production is
done — no consumer left hanging forever waiting for work that will
never come.

```python
import queue
import threading

SENTINEL = object()  # a unique "no more work" marker

def producer(q: queue.Queue, n_items: int):
    for i in range(n_items):
        q.put(f"item-{i}")
    for _ in range(3):  # one sentinel per consumer
        q.put(SENTINEL)

def consumer(q: queue.Queue, worker_id: int):
    while True:
        item = q.get()
        if item is SENTINEL:
            break
        print(f"worker {worker_id} processing {item}")
        q.task_done()

q = queue.Queue(maxsize=10)  # bounded — see below
threads = [threading.Thread(target=consumer, args=(q, i)) for i in range(3)]
for t in threads:
    t.start()

producer(q, 25)

for t in threads:
    t.join()
```

- `queue.Queue` is already thread-safe internally — no manual lock
  needed around `put`/`get`, unlike the plain-list scenario in Task 1.
- The **sentinel pattern** (a unique marker meaning "stop") is the
  standard way to shut down a fixed pool of consumers cleanly — each
  consumer exits when it personally receives a sentinel, so you need
  exactly one sentinel per consumer, not one total.
- `maxsize=10` gives the queue **backpressure** — if consumers fall
  behind, `q.put()` blocks the producer instead of letting the queue
  grow unboundedly in memory. Try `maxsize=0` (unbounded, the default)
  vs a small bound with a slow consumer and watch the difference in
  memory behavior on a real workload.
- This exact shape — a queue, a fixed pool of workers pulling from it,
  a shutdown signal — is what
  [Building Worker Pools From Scratch](building-worker-pools.md)
  generalizes into a reusable class, and what Celery does at a
  distributed, multi-machine scale.

---

## Code Samples

No dedicated code samples yet for this section — the tasks above are
meant to be typed and run directly.
