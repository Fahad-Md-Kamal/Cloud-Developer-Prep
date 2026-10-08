---
title: Concurrency & AsyncIO
---

# Concurrency & AsyncIO

The GIL and the AsyncIO/threading/multiprocessing decision — the two
questions that come up together in almost every senior Python
interview, since one explains the other.

## 1. "Explain the GIL. Then explain why threads still help I/O-bound code despite it."

**Answer:**

- The GIL is a single mutex in CPython that prevents more than one
  thread from executing Python bytecode at a time.
- Threads still help I/O-bound work because a thread **releases** the
  GIL while blocked on I/O (network call, file read, DB query) —
  another thread runs during that wait.
- CPU-bound work gets no benefit from threads at all, since only one
  thread can be *executing* Python at any instant no matter how many
  exist.

**If asked to demonstrate it live:**

- Run the same CPU-bound loop three ways — sequential, threaded,
  multiprocessed.
- Threaded comes out roughly equal to sequential (no real parallelism
  gained); multiprocessed actually scales, because separate processes
  each get their own GIL.

**The one-liner to lead with:** "threads for I/O-bound, processes for
CPU-bound" — then be ready to explain *why*, not just recite it.

| Pros of the GIL's existence | Cons / Trade-offs |
|---|---|
| Simplifies CPython's internals — no fine-grained locking on every object | Wastes multi-core hardware for CPU-bound pure-Python code |
| Makes single-threaded code fast — no lock overhead per operation | Real parallelism needs multiprocessing or a native extension that releases it |
| C extensions can release it during I/O/blocking calls for real concurrency | A frequent source of confusion — many candidates think threads never help at all |

## 2. "A Django view calling three third-party APIs is slow. Walk me through fixing it."

```python
import asyncio

async def fetch_async(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    tasks = [fetch_async(session, url) for url in urls]
    results = await asyncio.gather(*tasks)  # all concurrent, one thread
```

**Answer:**

- If the calls are sequential — awaiting each one in turn — they're
  slow because the total time is the *sum* of three round trips
  instead of the *max*.
- `asyncio.gather` (or a thread pool, in sync Django) runs them
  concurrently instead.

**Likely follow-up — "when would you reach for threading or multiprocessing instead of asyncio here?"**

- Decision rule: mostly network-bound → AsyncIO.
- Must call a blocking library with no async client → thread pool
  around the blocking calls.
- CPU-dominated (parsing, number-crunching, ML inference) →
  multiprocessing, sized to core count.
- Never run CPU work directly inside an async event loop — it blocks
  *every* other task on that loop, not just the one doing the work.

| Pros | Cons / Trade-offs |
|---|---|
| AsyncIO: thousands of concurrent tasks on one thread, low memory overhead | AsyncIO: one blocking or CPU-heavy call stalls the entire event loop |
| Threading: works with existing blocking libraries with minimal code changes | Threading: no real CPU parallelism due to the GIL — bounded scalability (hundreds, not thousands) |
| Multiprocessing: true parallel CPU execution, bypasses the GIL entirely | Multiprocessing: higher memory/startup cost, and data must be pickled across process boundaries |

## 3. "How do you prevent deadlocks? And if you don't know how long a task will take or when another thread releases a lock you need, how do you stop two threads from locking each other out?"

**Answer:**

- A deadlock needs two things at once: more than one lock, and
  threads acquiring them in *different orders* — thread 1 holds lock
  A and waits for lock B, while thread 2 holds lock B and waits for
  lock A. Neither ever releases.
- **Consistent lock ordering** is the real fix: if every thread in the
  codebase always acquires lock A before lock B, the circular-wait
  condition above can't happen — one of them will always get both
  locks free and proceed.
- **Timeouts** (`lock.acquire(timeout=5)`) turn an infinite wait into
  a failure the code can actually handle — give up, log it, retry —
  instead of hanging forever. This directly answers "I don't know how
  long a task will take": don't wait unboundedly on a lock whose
  hold time you can't predict.
- **Avoid nested locks entirely where possible** — the queue-based
  handoff from
  [Building Worker Pools](building-worker-pools.md#task-1-a-minimal-worker-pool-class)
  sidesteps the whole problem: a single worker owns a piece of state
  and everyone else communicates with it by putting work on a queue,
  so no two threads ever need to hold each other's locks at all.
- Always use `with lock:` rather than manual `lock.acquire()`/
  `lock.release()` pairs — a `with` block releases the lock even if an
  exception is raised inside it; a manual pair that forgets the
  `finally` leaves the lock held forever on the exception path, which
  is its own, very common way to manufacture a deadlock.

## 4. "AsyncIO runs on a single thread — how does `asyncio.gather()` get concurrency out of that?"

**Answer:**

- Single-threaded concurrency here means **cooperative** scheduling,
  not parallelism — only one coroutine is ever actually executing
  Python bytecode at a time, same as the GIL already implies.
- `asyncio.gather(*tasks)` schedules every task on the one event loop.
  Each task runs until it hits its own `await` (an I/O wait), at
  which point it voluntarily yields control back to the loop — the
  loop then resumes whichever other task is ready to make progress.
- The speedup comes entirely from *overlapping waits*: three HTTP
  calls that each take 1 second run as roughly 1 second total under
  `gather()`, not 3, because all three are "waiting" at the same time
  instead of one after another — see the worked example in
  [§2 above](#2-a-django-view-calling-three-third-party-apis-is-slow-walk-me-through-fixing-it).
- This is exactly why a CPU-bound or blocking (non-async) call inside
  one of the gathered coroutines is so damaging — it never hits an
  `await` to yield control, so it blocks the single thread running the
  entire event loop, stalling every other task in the `gather()` too,
  not just the one doing the work.

---

## Code Samples

- `code_samples/chapter-1/asyncio/event_loop_optimization.py`
- `code_samples/chapter-1/asyncio/concurrency_benchmark.py`
- `code_samples/chapter-1/asyncio/async_legal_crawler.py`

```bash
pip install aiohttp uvloop
python code_samples/chapter-1/asyncio/event_loop_optimization.py
```
