---
title: Concurrency & AsyncIO
---

# Concurrency & AsyncIO

The GIL, threading, AsyncIO, and multiprocessing — not four separate
topics, but one decision that keeps coming back in a senior Python
interview. This page covers them in one pass, grouped by primitive
rather than by question, so each concept builds on the one before it:
the GIL first (it explains *why* the other three exist), then
threading's own pitfalls, then AsyncIO as a different way to get
concurrency without threads at all.

## Choosing Between Threading, AsyncIO, and Multiprocessing

**The one-liner to lead with:** "threads for I/O-bound, processes for
CPU-bound, AsyncIO for *massively* concurrent I/O on one thread" —
then be ready to explain *why*, not just recite it. The sections below
are that explanation.

**The decision rule:**

- Mostly network-bound (lots of concurrent waits, a client library
  that supports it) → AsyncIO.
- Must call a blocking library with no async client → a thread pool
  around the blocking calls.
- CPU-dominated (parsing, number-crunching, ML inference) →
  multiprocessing, sized to core count.
- Never run CPU-bound work directly inside an async event loop — it
  blocks *every* other task on that loop, not just the one doing the
  work.

| | Strength | Trade-off |
|---|---|---|
| **AsyncIO** | Thousands of concurrent tasks on one thread, low memory overhead | One blocking or CPU-heavy call stalls the *entire* event loop |
| **Threading** | Works with existing blocking libraries with minimal code changes | No real CPU parallelism due to the GIL — bounded scalability (hundreds of threads, not thousands) |
| **Multiprocessing** | True parallel CPU execution, bypasses the GIL entirely | Higher memory/startup cost, and data must be pickled across process boundaries |

## 1. "Explain the GIL. Then explain why threads still help I/O-bound code despite it."

**Answer:**

- The GIL is a single mutex in CPython that prevents more than one
  thread from executing Python bytecode at a time.
- Threads still help I/O-bound work because a thread **releases** the
  GIL while blocked on I/O (network call, file read, DB query) —
  another thread runs during that wait. A regular (sequential) loop
  can't do this: if each iteration waits on something, the total time
  is the *sum* of every wait, one after another. A threaded loop lets
  multiple iterations be in flight at once, so the total time becomes
  closer to the *longest single wait*, not the sum of all of them.
- CPU-bound work gets no benefit from threads at all, since only one
  thread can be *executing* Python at any instant no matter how many
  exist — for that case, reach for `multiprocessing`/
  `ProcessPoolExecutor` instead, where each process gets its own GIL
  and actually runs on a separate core (see
  [Multiprocessing in Practice](multiprocessing-in-practice.md)).

**Concrete example — fetching 20 URLs:**

- Sequential: 20 requests × 0.5s each ≈ 10 seconds total.
- Threaded (`ThreadPoolExecutor(max_workers=5)`, as in
  [Threading in Practice's Task 2](threading-in-practice.md#task-2-build-a-bounded-worker-pool-for-io-bound-work)):
  5 requests waiting concurrently at a time ≈ 20/5 × 0.5s = 2 seconds
  total.
- The same 20 URLs doing CPU-bound work (not I/O) instead would take
  roughly the same wall-clock time threaded as sequential — sometimes
  worse, from thread-switching overhead — since there's no wait for a
  second thread to fill.

**If asked to demonstrate it live:**

- Run the same CPU-bound loop three ways — sequential, threaded,
  multiprocessed.
- Threaded comes out roughly equal to sequential (no real parallelism
  gained); multiprocessed actually scales, because separate processes
  each get their own GIL.

| Pros of the GIL's existence | Cons / Trade-offs |
|---|---|
| Simplifies CPython's internals — no fine-grained locking on every object | Wastes multi-core hardware for CPU-bound pure-Python code |
| Makes single-threaded code fast — no lock overhead per operation | Real parallelism needs multiprocessing or a native extension that releases it |
| C extensions can release it during I/O/blocking calls for real concurrency | A frequent source of confusion — many candidates think threads never help at all |

## 2. "What kinds of problems do threaded programs face, and how do you overcome them?"

**Answer:**

- **Race conditions** — two threads read-modify-write shared state at
  the same time and one update gets silently lost (the `counter += 1`
  demo in
  [Threading in Practice's Task 1](threading-in-practice.md#task-1-reproduce-a-race-condition-then-fix-it)).
    - **Overcome:** a `threading.Lock()` around the critical section
      (`with lock:`), so only one thread can be mid-update at a time.
- **Deadlocks** — two threads each hold a lock the other needs, and
  both wait forever. A deadlock needs two things at once: more than
  one lock, and threads acquiring them in *different orders* — thread
  1 holds lock A and waits for lock B, while thread 2 holds lock B and
  waits for lock A. Neither ever releases.
    - **Overcome — consistent lock ordering:** if every thread in the
      codebase always acquires lock A before lock B, the circular-wait
      condition above can't happen — one of them will always get both
      locks free and proceed.
    - **Overcome — timeouts:** `lock.acquire(timeout=5)` turns an
      infinite wait into a failure the code can actually handle — give
      up, log it, retry — instead of hanging forever. This is the
      direct answer to "I don't know how long a task will take": don't
      wait unboundedly on a lock whose hold time you can't predict.
    - **Overcome — avoid nested locks entirely where possible:** the
      queue-based handoff from
      [Building Worker Pools](building-worker-pools.md#task-1-a-minimal-worker-pool-class)
      sidesteps the whole problem — a single worker owns a piece of
      state and everyone else communicates with it by putting work on
      a queue, so no two threads ever need to hold each other's locks
      at all.
    - **A related trap:** always use `with lock:` rather than manual
      `lock.acquire()`/`lock.release()` pairs — a `with` block releases
      the lock even if an exception is raised inside it; a manual pair
      that forgets the `finally` leaves the lock held forever on the
      exception path, which is its own, very common way to manufacture
      a deadlock.
- **No real CPU parallelism (the GIL)** — only one thread executes
  Python bytecode at a time, so adding threads never speeds up
  CPU-bound work, no matter how many cores the machine has.
    - **Overcome:** this isn't fixable with more threads — switch to
      `multiprocessing`/`ProcessPoolExecutor` instead, where each
      process gets its own GIL and runs on a separate core.
- **Unbounded resource growth** — a fast producer thread and a slow
  consumer thread, with no limit on how much queued work piles up in
  memory.
    - **Overcome:** backpressure — a bounded `queue.Queue(maxsize=N)`
      so the producer blocks once it's full, or a
      `ThreadPoolExecutor(max_workers=N)` that caps concurrency
      outright. See
      [Building Worker Pools' backpressure task](building-worker-pools.md#task-2-add-backpressure-with-a-bounded-queue).
- **Silent failures** — an exception raised inside a bare `Thread`'s
  target function kills that thread silently; nothing propagates to
  the rest of the program.
    - **Overcome:** `ThreadPoolExecutor` instead of raw `Thread`
      objects — exceptions are captured on the `Future` and re-raised
      when `.result()` is called, instead of silently disappearing.
- **Non-deterministic shutdown** — consumer threads looping forever on
  a queue with no way to know when to stop.
    - **Overcome:** the sentinel pattern — a unique "stop" marker put
      on the queue once per consumer, so each one exits cleanly when
      it personally receives a sentinel. See
      [Threading in Practice's Task 3](threading-in-practice.md#task-3-a-producerconsumer-pipeline-with-queuequeue).

**The underlying pattern:** almost every one of these is solved by
*reducing shared mutable state* — a lock protects it, a queue hands
work off instead of sharing it, a pool bounds it. The less two threads
directly touch the same memory, the fewer of these problems show up in
the first place.

## 3. "AsyncIO runs on a single thread — how does it get concurrency out of that, and what does using it actually look like?"

**Answer — the mechanics:**

- Single-threaded concurrency here means **cooperative** scheduling,
  not parallelism — only one coroutine is ever actually executing
  Python bytecode at a time, same as the GIL already implies for
  threads.
- `asyncio.gather(*tasks)` schedules every task on the one event loop.
  Each task runs until it hits its own `await` (an I/O wait), at
  which point it voluntarily yields control back to the loop — the
  loop then resumes whichever other task is ready to make progress.
- This is exactly why a CPU-bound or blocking (non-async) call inside
  one of the gathered coroutines is so damaging — it never hits an
  `await` to yield control, so it blocks the single thread running the
  entire event loop, stalling every other task in the `gather()` too,
  not just the one doing the work.

**Worked example — "three third-party API calls are slow, sequentially":**

```python
import asyncio

async def fetch_async(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    tasks = [fetch_async(session, url) for url in urls]
    results = await asyncio.gather(*tasks)  # all concurrent, one thread
```

- If the calls are sequential — awaiting each one in turn — they're
  slow because the total time is the *sum* of three round trips
  instead of the *max*.
- `asyncio.gather` (or a thread pool, in synchronous code) runs them
  concurrently instead — the speedup comes entirely from *overlapping
  waits*: three HTTP calls that each take 1 second run as roughly 1
  second total under `gather()`, not 3, because all three are
  "waiting" at the same time instead of one after another.
- For the full decision rule on when to reach for threading or
  multiprocessing instead of AsyncIO here, see
  [Choosing Between Threading, AsyncIO, and Multiprocessing](#choosing-between-threading-asyncio-and-multiprocessing)
  above.

---

## Code Samples

- `code_samples/chapter-1/asyncio/event_loop_optimization.py`
- `code_samples/chapter-1/asyncio/concurrency_benchmark.py`
- `code_samples/chapter-1/asyncio/async_legal_crawler.py`

```bash
pip install aiohttp uvloop
python code_samples/chapter-1/asyncio/event_loop_optimization.py
```
