---
title: "Building Worker Pools From Scratch"
---

# Building Worker Pools From Scratch

Implementing a worker pool yourself — before you reach for
`ThreadPoolExecutor` or Celery — so the abstraction stops being a
black box. Builds directly on the producer/consumer pattern in
[Threading in Practice's Task 3](threading-in-practice.md#task-3-a-producerconsumer-pipeline-with-queuequeue).

## Task 1: A minimal worker pool class

**The task:** wrap the queue-plus-workers shape from Threading in
Practice into a reusable class with `submit()` and `shutdown()`
methods — the shape `ThreadPoolExecutor` hides behind a nicer API.

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

## Task 2: Add backpressure with a bounded queue

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

## Task 3: From your own worker pool to Celery — what's actually different

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
