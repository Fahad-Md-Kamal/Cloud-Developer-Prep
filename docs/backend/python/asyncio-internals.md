---
title: "AsyncIO Internals"
---

# AsyncIO Internals

AsyncIO gets concurrency without threads at all — this page covers how,
from `asyncio.gather()` down to what `async`/`await` actually compiles
to and what the event loop's main loop is doing on every tick. See
[Choosing a Concurrency Model](choosing-a-concurrency-model.md) for when
AsyncIO is the right tool versus threading or multiprocessing.

## Cooperative Scheduling

**"AsyncIO runs on a single thread — how does it get concurrency out of
that, and what does using it actually look like?"**

**Answer — the mechanics:**

- Single-threaded concurrency here means **cooperative** scheduling,
  not parallelism — only one coroutine is ever actually executing
  Python bytecode at a time, same as
  [the GIL](threading-and-the-gil.md#the-gil) already implies for
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
  [Choosing a Concurrency Model](choosing-a-concurrency-model.md).

## The OS I/O Model Underneath AsyncIO

**"How does the OS actually handle input and output, and how does that
relate to AsyncIO?"**

**Answer:**

- At the OS level, I/O (reading a socket, a file, waiting on a
  network response) works through system calls — a process asks the
  kernel to perform the operation, and the kernel manages the actual
  hardware (network card, disk controller) and interrupts the process
  when data is ready. The two classic models:
    - **Blocking I/O** — the calling thread is suspended by the OS
      scheduler until the operation completes. This is what a plain
      `socket.recv()` does by default: the thread does nothing else
      until data arrives.
    - **Non-blocking I/O with readiness notification** — the process
      asks the kernel "tell me which of these N file descriptors are
      ready to read/write right now" via a system call
      (`select`/`poll` historically, `epoll` on Linux, `kqueue` on
      BSD/macOS), then only acts on the ones that are actually ready —
      no thread sits blocked waiting on any single one.
- **This second model is exactly what AsyncIO's event loop is built
  on.** `asyncio`'s default event loop uses `epoll` (Linux) under the
  hood: it registers every open socket a coroutine is waiting on, asks
  the kernel which ones are ready, and resumes only those coroutines —
  the same mechanism as
  [cooperative scheduling above](#cooperative-scheduling),
  just one level deeper: the event loop's own "which task is ready to
  run" decision is itself answered by a single OS readiness-notification
  call covering every waiting task at once, not N separate blocking
  calls.
- **Why this explains thousands of concurrent connections on one
  thread:** a thread-per-connection blocking model needs one OS thread
  per in-flight connection — real memory and scheduling overhead past
  a few thousand. `epoll` lets one thread ask about thousands of file
  descriptors in a single call, so AsyncIO's concurrency ceiling is
  governed by memory-per-coroutine (cheap) rather than
  memory-per-OS-thread (comparatively expensive).
- **Interview point:** "AsyncIO achieves concurrency through
  cooperative multitasking" is the *application-level* answer above;
  "AsyncIO's event loop is a thin wrapper around epoll/kqueue readiness
  notification" is the *systems-level* answer underneath it — being
  able to go one layer deeper than "it uses `await`" is what
  distinguishes a surface answer from a strong one here.

## Coroutines as Generators, and the Event Loop's Main Loop

**"What does `async`/`await` actually compile to, and what is the event
loop's main loop actually doing?"**

**Answer:**

- Calling an `async def` function doesn't run any of its code — it
  returns a **coroutine object**, the exact same thing a generator
  function does when called: nothing executes until something starts
  driving it forward.
- `await` is built on the **same suspension mechanism as `yield`** in a
  generator: it pauses execution at that exact point and hands control
  back to whatever is driving the coroutine, ready to resume from that
  same point — not restart — the next time it's driven forward again.
  `async`/`await` is syntax on top of the generator protocol, not a
  separate mechanism invented from scratch.
- The event loop is that driver. Mechanically, advancing a coroutine
  one step is calling `.send(None)` on it: that call runs the coroutine
  until its next `await`, and when the coroutine finally returns, that
  same `send()` call raises `StopIteration` carrying the return value —
  precisely how exhausting an ordinary generator already works.

<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of a coroutine suspending at await, the event loop registering interest with epoll, and resuming the coroutine via send() once epoll reports the socket ready" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="420" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<rect x="20" y="150" width="220" height="110" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<text x="130" y="190" font-size="15" font-weight="600" text-anchor="middle" fill="#1d4a78">Coroutine</text>
<text x="130" y="210" font-size="12" text-anchor="middle" fill="#3d699a">await socket.recv()</text>
<text x="130" y="230" font-size="12" text-anchor="middle" fill="#3d699a">suspends via yield</text>
<rect x="340" y="150" width="220" height="110" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="450" y="190" font-size="15" font-weight="600" text-anchor="middle" fill="#7a5c14">Event Loop</text>
<text x="450" y="210" font-size="12" text-anchor="middle" fill="#9a7420">registers the socket,</text>
<text x="450" y="228" font-size="12" text-anchor="middle" fill="#9a7420">moves on to other work</text>
<rect x="660" y="150" width="220" height="110" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="770" y="190" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">epoll (kernel)</text>
<text x="770" y="210" font-size="12" text-anchor="middle" fill="#5b6472">watching many sockets</text>
<text x="770" y="228" font-size="12" text-anchor="middle" fill="#5b6472">for all waiting coroutines</text>
<circle r="10" fill="#d9822b" cy="205"><animate attributeName="cx" values="130;340;770;340;130;130" keyTimes="0;0.18;0.4;0.62;0.8;1" dur="13s" repeatCount="indefinite"></animate></circle>
<rect x="340" y="150" width="220" height="110" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2" opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.68;0.95;0.98;1" dur="13s" repeatCount="indefinite"></animate></rect>
<text x="450" y="190" font-size="15" font-weight="600" text-anchor="middle" fill="#0f6b45" opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.68;0.95;0.98;1" dur="13s" repeatCount="indefinite"></animate>Event Loop</text>
<text x="450" y="210" font-size="12" text-anchor="middle" fill="#3d9a73" opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.68;0.95;0.98;1" dur="13s" repeatCount="indefinite"></animate>socket ready —</text>
<text x="450" y="228" font-size="12" text-anchor="middle" fill="#3d9a73" opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.68;0.95;0.98;1" dur="13s" repeatCount="indefinite"></animate>calls coro.send(None)</text>
<text x="450" y="330" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.37;0.4;1" dur="13s" repeatCount="indefinite"></animate>await suspends the coroutine — the loop registers interest with epoll and moves on.</text>
<text x="450" y="330" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.4;0.44;0.58;0.62;1" dur="13s" repeatCount="indefinite"></animate>epoll.poll() reports this socket is now readable.</text>
<text x="450" y="330" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.64;0.68;0.95;0.98;1" dur="13s" repeatCount="indefinite"></animate>The loop calls coro.send(None) — execution resumes right after the await.</text>
</svg>

### The Event Loop's Main Loop, Stripped to Its Core

`loop.run_forever()` is, underneath everything above it, one simple
loop that never stops until told to:

1. Work out how long it's safe to wait (based on the earliest scheduled
   timed callback — `asyncio.sleep()`'s deadline, say — or block
   indefinitely if nothing is scheduled).
2. Call `epoll.poll(timeout)` — this blocks only until either a
   registered socket becomes ready, or that timeout elapses, whichever
   comes first.
3. Run every callback that's now ready: each socket `epoll` just
   reported, plus anything already queued from earlier (a timer firing,
   another coroutine's `call_soon`) — "running a callback" for a
   suspended coroutine means exactly one `send(None)` call, advancing it
   to its next `await` or to completion.
4. Go back to step 1, forever.

Every `await` that resolves anywhere in an AsyncIO program is just
another callback landing in that same queue, picked up on the very next
tick of this one loop — there's no separate machinery per coroutine,
just this one loop multiplexing all of them through the same
epoll-plus-callback-queue mechanism.

---

## Code Samples

- `code_samples/chapter-1/asyncio/event_loop_optimization.py`
- `code_samples/chapter-1/asyncio/async_legal_crawler.py`

```bash
pip install aiohttp uvloop
python code_samples/chapter-1/asyncio/event_loop_optimization.py
```
