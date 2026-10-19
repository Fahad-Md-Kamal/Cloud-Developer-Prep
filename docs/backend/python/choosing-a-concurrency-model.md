---
title: "Choosing a Concurrency Model"
---

# Choosing a Concurrency Model

The GIL, threading, AsyncIO, and multiprocessing — not four separate
topics, but one decision that keeps coming back in a senior Python
interview. This page is the decision framework; see
[Threading & the GIL](threading-and-the-gil.md) and
[AsyncIO Internals](asyncio-internals.md) for the mechanics each option
is actually built on.

## Concurrency vs. Parallelism

- **Concurrency** is the general concept: multiple tasks make progress
  over overlapping time periods, without necessarily running at the
  exact same instant. Threading, AsyncIO, *and* multiprocessing are
  all mechanisms for achieving concurrency — AsyncIO isn't a competing
  concept to concurrency, it's one specific way to get it.
- **Parallelism** is the stricter case: tasks genuinely executing at
  the same instant, which requires multiple CPU cores actually running
  Python bytecode simultaneously. In CPython, only multiprocessing
  achieves real parallelism — threading and AsyncIO both give
  concurrency *without* parallelism, since the GIL (for threads) and
  the single event-loop thread (for AsyncIO) each still run exactly
  one line of Python at a time.
- So "AsyncIO vs. concurrency" is really "one specific concurrency
  mechanism vs. the general category it belongs to" — the more useful
  question is the one this page answers: *which* concurrency mechanism
  fits a given workload.

## The Decision Rule

**The one-liner to lead with:** "threads for I/O-bound, processes for
CPU-bound, AsyncIO for *massively* concurrent I/O on one thread" —
then be ready to explain *why*, not just recite it.

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

For the full worked example of why threading specifically helps
I/O-bound work despite the GIL, see
[Threading & the GIL](threading-and-the-gil.md#the-gil). For AsyncIO's
own version of the same trade-off, see
[AsyncIO Internals](asyncio-internals.md).
