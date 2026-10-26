---
title: "Worker Pools & Backpressure"
---

# Worker Pools & Backpressure

Hands-on tasks building up from a raw `queue.Queue` to a reusable worker
pool class, then comparing that against the two tools you'd actually
reach for in practice: `ThreadPoolExecutor` and Celery. Builds on
[Threading & the GIL](threading-and-the-gil.md) — do each task yourself
before reading the explanation.

## Task: A Producer/Consumer Pipeline with `queue.Queue`

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
  needed around `put`/`get`, unlike the plain-counter scenario in
  [Threading & the GIL's race condition task](threading-and-the-gil.md#task-reproduce-a-race-condition-then-fix-it).
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
  a shutdown signal — is what the next task generalizes into a
  reusable class, and what Celery does at a distributed, multi-machine
  scale.

## Task: A Minimal Worker Pool Class

**The task:** wrap the queue-plus-workers shape above into a reusable
class with `submit()` and `shutdown()` methods — the shape
`ThreadPoolExecutor` hides behind a nicer API.

```python
import queue
import threading
from dataclasses import dataclass, field

SENTINEL = object()

@dataclass
class WorkerPool:
    num_workers: int
    _queue: queue.Queue = field(default_factory=queue.Queue)
    _threads: list = field(default_factory=list)

    def __post_init__(self):
        for i in range(self.num_workers):
            t = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            t.start()
            self._threads.append(t)

    def _worker_loop(self, worker_id: int):
        while True:
            task = self._queue.get()
            if task is SENTINEL:
                self._queue.task_done()
                break
            func, args, kwargs = task
            try:
                func(*args, **kwargs)
            except Exception as exc:
                print(f"worker {worker_id} task failed: {exc}")
            finally:
                self._queue.task_done()

    def submit(self, func, *args, **kwargs):
        self._queue.put((func, args, kwargs))

    def shutdown(self, wait: bool = True):
        for _ in range(self.num_workers):
            self._queue.put(SENTINEL)
        if wait:
            for t in self._threads:
                t.join()


# Usage
def process_item(item):
    print(f"processing {item}")

pool = WorkerPool(num_workers=3)
for i in range(10):
    pool.submit(process_item, f"item-{i}")
pool.shutdown()
```

**What this exercise actually teaches:**

- `ThreadPoolExecutor.submit()` and `.shutdown()` are doing exactly
  this under the hood — a queue, a fixed set of long-lived worker
  threads pulling from it in a loop, and a shutdown signal. Building
  it once means the standard library version stops being magic.
- `daemon=True` on the worker threads means they won't prevent the
  program from exiting if something goes wrong and `shutdown()` is
  never called — a safety net, not a substitute for calling it
  properly.
- Catching exceptions *inside* the worker loop (rather than letting
  them escape) is a deliberate choice here — an uncaught exception in
  a plain `Thread`'s target function just kills that thread silently
  and the pool is now short one worker forever, with no error
  propagated anywhere. `ThreadPoolExecutor` avoids this by capturing
  the exception on the `Future` instead — a real difference between
  building it yourself and using the standard tool.

## Task: Add Backpressure with a Bounded Queue

**The task:** modify the pool above so a slow set of workers can't let
memory grow without bound if `submit()` is called faster than tasks
complete.

```python
_queue: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=50))
```

- With an unbounded queue (the default), a producer that outpaces the
  workers just keeps piling up tasks in memory — on a real workload
  with a slow downstream dependency, this is exactly how a service
  runs out of memory hours into a deploy, not immediately.
- `maxsize=50` makes `submit()` (via the queue's `put()`) block once
  50 tasks are pending — the producer is now forced to slow down to
  match the workers' actual throughput, trading unbounded memory
  growth for the caller waiting.
- This is the same backpressure concept as a bounded channel in Go, or
  a bounded connection pool in a database client — a recurring pattern
  anywhere producers and consumers can run at different speeds.

## Task: A Bounded Worker Pool Using `ThreadPoolExecutor`

**The task:** fetch 20 URLs concurrently, but never more than 5 at
once, and collect results as they finish (not necessarily in the
order you submitted them) — this time using the standard library tool
instead of the hand-rolled class above.

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
  `Thread` objects and a semaphore unless you have a reason to, and
  having just built the class above, you now know exactly what it's
  doing underneath.
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

## From Your Own Worker Pool to Celery

**Answer, no new code — this is the conceptual bridge:**

- The shape is identical: a queue holding pending work, a fixed set of
  workers pulling from it, a way to submit new work, a way to shut
  down cleanly. Everything built above is that shape, in-process, on
  one machine.
- Celery's actual additions:
    - **The queue is a real broker** (Redis, RabbitMQ) instead of an
      in-process `queue.Queue` — durable, and reachable from other
      machines, not just other threads in the same process.
    - **Workers can run anywhere** — on a different machine entirely
      from whatever calls `.delay()` — because the broker is the
      shared point of contact, not shared memory.
    - **Retries, routing, and scheduling** are built in — a failed
      task can be automatically retried with backoff, different task
      types can be routed to different worker pools, and a task can be
      scheduled for later (Celery Beat) — all things the from-scratch
      version above would need to be built by hand.
    - **Durability across a crash** — if a worker process dies
      mid-task with a real broker, the task can be redelivered to
      another worker; the in-process version above loses all pending
      queued tasks if the process itself crashes, since the queue only
      ever lived in that process's memory.
- The trade-off for all of that: real infrastructure (a broker to run
  and monitor) and real operational complexity, instead of a
  self-contained class. See
  [Practical Patterns §3](practical-patterns.md#3-when-do-you-reach-for-celery-instead-of-just-handling-something-in-the-request)
  for when that trade-off is actually worth making.

| From-scratch worker pool | Celery |
|---|---|
| Zero infrastructure — just Python, runs in one process | Needs a broker (Redis/RabbitMQ) running and monitored |
| Tasks lost if the process crashes — nothing durable | Broker persists tasks; a crashed worker's task can be redelivered |
| Workers must live in the same process as the queue | Workers can run on entirely separate machines |
| No built-in retry/scheduling — you'd write it yourself | Retries, routing, and scheduled tasks (Celery Beat) built in |

---

## Code Samples

No dedicated code samples yet for this section — the tasks above are
meant to be typed and run directly.
