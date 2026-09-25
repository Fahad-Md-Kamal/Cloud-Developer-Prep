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
