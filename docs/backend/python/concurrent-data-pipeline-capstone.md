---
title: "Capstone: A Concurrent Data Pipeline"
---

# Capstone: A Concurrent Data Pipeline

An advanced project tying together
[Threading in Practice](threading-in-practice.md),
[Multiprocessing in Practice](multiprocessing-in-practice.md), and
[Building Worker Pools From Scratch](building-worker-pools.md) into
one realistic system — the kind of architecture question a senior
interview asks after confirming you know the individual primitives.

## The problem

Build a pipeline that fetches data from multiple sources, transforms
it, and writes the results — using the right concurrency primitive for
each stage, not one tool for everything.

- **Fetch stage (I/O-bound)** — download N URLs (or hit N API
  endpoints, or read N files) concurrently.
- **Transform stage (CPU-bound)** — parse/process each fetched payload
  in a way that's deliberately expensive (e.g. a regex-heavy parse, a
  hash computation, a synthetic CPU-bound loop) — genuinely benefits
  from multiple cores, not just multiple threads.
- **Write stage (contention-prone)** — write every result to a single
  output file or a single SQLite database — a stage where naive
  concurrent access would corrupt output, so it needs to be
  deliberately serialized.
- **Coordination** — the three stages run concurrently with each
  other (fetching item 5 while transforming item 3 while writing item
  1), not as three sequential batch passes.

## Why one tool doesn't fit all three stages

- The fetch stage is I/O-bound — [Threading in Practice](threading-in-practice.md)
  applies: a `ThreadPoolExecutor` handles many concurrent waits
  cheaply.
- The transform stage is CPU-bound — threading buys nothing here
  because of the GIL; [Multiprocessing in Practice](multiprocessing-in-practice.md)
  applies: a `ProcessPoolExecutor` actually uses multiple cores.
- The write stage has to be serialized regardless of how the other two
  stages are parallelized — multiple processes or threads writing to
  the same file/connection concurrently is a correctness bug, not a
  performance question. One dedicated writer, fed by a queue, is the
  standard fix — the same queue-plus-worker shape as
  [Building Worker Pools From Scratch](building-worker-pools.md),
  just with exactly one worker by design.

## Suggested architecture

```
[fetch threads] --> fetch_queue --> [transform processes] --> write_queue --> [single writer thread] --> output
```

- A `ThreadPoolExecutor` (or the manual pool from the worker-pools
  page) fetches sources concurrently and pushes raw payloads onto
  `fetch_queue`.
- A `ProcessPoolExecutor` consumes from `fetch_queue`, transforms each
  payload, and pushes results onto `write_queue`. (In practice, feeding
  a `ProcessPoolExecutor` from a live queue takes a bit of extra
  wiring compared to `pool.map` on a fixed list — submitting each item
  as it arrives via `pool.submit()` and collecting futures is the
  more realistic approach than trying to share a `multiprocessing.Queue`
  directly with a `ProcessPoolExecutor`.)
- A single writer thread (never more than one) drains `write_queue`
  and writes each result — no lock needed here specifically *because*
  there's deliberately only one writer.

## Milestones — build it in this order

1. **Sequential baseline first.** Fetch, transform, and write
   everything one item at a time, no concurrency at all. Time it. This
   is your correctness reference and your speedup baseline — you
   can't credibly claim a speedup without one.
2. **Thread-pool the fetch stage only**, still processing/writing
   sequentially after all fetches complete. Confirm output is
   identical to the baseline.
3. **Process-pool the transform stage**, reading from the now-fetched
   results. Confirm output is still identical.
4. **Wire the stages together concurrently** via queues, so fetching,
   transforming, and writing genuinely overlap in time rather than
   running as three sequential passes. This is the step that actually
   requires the queue architecture above, not just parallel batches.
5. **Add graceful shutdown and error handling** — a failed fetch or a
   failed transform for one item should not crash the pipeline or
   silently drop the item; log it and continue. Handle Ctrl-C
   (`KeyboardInterrupt`) by draining in-flight work cleanly rather than
   leaving corrupted partial output.
6. **Add progress reporting** — a running count of
   fetched/transformed/written items, updated safely from multiple
   threads/processes (this itself is a small return to Task 1 of
   Threading in Practice: a shared counter needs a lock).

## What a strong solution demonstrates

- The sequential baseline actually exists and was actually measured —
  not just asserted.
- Each stage uses the concurrency primitive that matches its actual
  bottleneck (I/O vs. CPU vs. serialized-by-necessity), not a single
  tool applied uniformly out of convenience.
- The pipeline survives a single item failing at any stage without
  crashing or silently corrupting output — proven with a deliberately
  broken input, not just assumed.
- Shutdown is actually graceful — no orphaned worker threads/processes
  left running, no half-written output file, when the pipeline is
  interrupted mid-run.
- The performance claim ("this is now N times faster") is backed by
  the same baseline-vs-final measurement from the milestones above,
  on the same input.

## Likely follow-up questions an interviewer asks about this kind of project

- "Why not just use one big `ProcessPoolExecutor` for everything,
  fetch included?" — tests whether you understand that processes are
  expensive for I/O-bound work that's mostly waiting, not computing —
  you'd pay process overhead for stages that don't need multiple
  cores at all.
- "What happens if the transform stage is much slower than fetch?" —
  tests whether you understand backpressure: an unbounded
  `fetch_queue` would grow without limit; a bounded one makes the
  fetch stage block once it's full, the same concept as
  [Building Worker Pools' Task 2](building-worker-pools.md#task-2-add-backpressure-with-a-bounded-queue).
- "How would you scale the transform stage across multiple machines,
  not just multiple cores on one?" — tests whether you can name the
  actual next step: this is exactly the local-worker-pool-to-Celery
  jump covered in
  [Building Worker Pools' Task 3](building-worker-pools.md#task-3-from-your-own-worker-pool-to-celery-whats-actually-different) —
  a real broker instead of an in-process queue, workers on separate
  machines instead of local threads/processes.
- "Your writer thread is now the bottleneck — what do you do?" — tests
  whether "just add more writer threads" is recognized as usually the
  wrong answer (it reintroduces the exact write-contention problem a
  single writer existed to avoid) versus the right answer: batch
  writes, use a faster sink, or partition output so multiple writers
  can safely own disjoint pieces of it.

---

## Code Samples

No dedicated code samples yet for this section — this capstone is
meant to be built from the milestones above, not copied from a
reference solution.
