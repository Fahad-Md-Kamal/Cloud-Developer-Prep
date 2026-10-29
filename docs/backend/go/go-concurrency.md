---
title: "Concurrency in Go: Goroutines, Channels & the Scheduler"
---

# Concurrency in Go: Goroutines, Channels & the Scheduler

A **goroutine** is a function that runs concurrently with the rest of
the program — Go's own lightweight unit of concurrency, managed by
Go's own runtime scheduler rather than the operating system directly.
Concurrency is Go's signature strength, built into the language itself
(the `go` keyword, channels) rather than bolted on as a library the
way Python's `asyncio` or `threading` are — this page covers that
model in depth, with the Python comparisons woven in where they
sharpen the point.

## 1. Goroutines vs. OS Threads vs. Python's AsyncIO

```go
func fetchData(url string, ch chan<- map[string]interface{}) {
    ch <- data
}

func main() {
    ch := make(chan map[string]interface{})
    for _, url := range urls {
        go fetchData(url, ch) // launch a goroutine
    }
    for i := 0; i < len(urls); i++ {
        result := <-ch // receive from the channel
    }
}
```

- `go someFunc()` launches a goroutine — it returns immediately, and
  `someFunc` runs concurrently. A goroutine starts with a tiny stack
  (around 2KB, growing as needed) compared to an OS thread's typical
  1-8MB fixed stack, which is why a Go program can run hundreds of
  thousands of goroutines where it could only run a few thousand OS
  threads.
- **Go's scheduler runs goroutines M:N** — mapping many (M) goroutines
  onto a smaller number (N) of OS threads, itself scheduled across
  `GOMAXPROCS` CPU cores. This is genuine parallelism on multi-core
  hardware, not just concurrency on a single thread the way Python's
  `asyncio` event loop is — see
  [Threading & the GIL](../../python/concurrency/threading-and-the-gil.md) for
  exactly what Python's GIL restricts that Go's model doesn't have to
  work around at all.
- **Interview point:** "are goroutines green threads?" — close enough
  for an interview answer, with one real distinction: Go's scheduler
  can preempt a long-running goroutine at safe points (function calls,
  since Go 1.14 even tight loops), so one badly-behaved goroutine
  generally can't starve the others the way a naive cooperative
  scheduler could.

## 2. Channels — Go's Own Words for It

```go
ch := make(chan int)       // unbuffered — send blocks until received
ch := make(chan int, 100)  // buffered — up to 100 pending values

ch <- 42       // send
value := <-ch  // receive

select {
case msg := <-ch1:
    fmt.Println("Received from ch1:", msg)
case msg := <-ch2:
    fmt.Println("Received from ch2:", msg)
case <-time.After(1 * time.Second):
    fmt.Println("Timeout")
}
```

- A **channel** is a typed pipe goroutines use to send and receive
  values — Go's own framing is "don't communicate by sharing memory,
  share memory by communicating": instead of multiple goroutines
  reading/writing the same variable under a lock, pass the value
  through a channel and only one goroutine touches it at a time.
- An **unbuffered** channel's send blocks until a receiver is actually
  ready — this makes it a synchronization point, not just a queue.
  A **buffered** channel's send only blocks once the buffer is full.
- `select` waits on multiple channel operations at once, running
  whichever case becomes ready first — the direct Go analogue of
  Python's `asyncio.wait`, with `time.After` giving a clean,
  built-in timeout pattern.

## 3. Shared State Still Needs Synchronization

A real interview progression (word count, built up in three steps —
solve it, make it concurrent, make it thread-safe):

```go
// Step 1: sequential — the correctness baseline
func wordCount(docs []string) map[string]int {
    counts := make(map[string]int)
    for _, doc := range docs {
        for _, word := range strings.Fields(doc) {
            counts[word]++
        }
    }
    return counts
}

// Step 2: "make it concurrent" — the naive, BROKEN version most
// candidates write first: a plain map has no synchronization, so
// concurrent writes from multiple goroutines race exactly like
// Python's counter += 1 under threading — this panics
// ("concurrent map writes") or silently loses updates under -race.
func wordCountConcurrentBroken(docs []string) map[string]int {
    counts := make(map[string]int)
    var wg sync.WaitGroup
    for _, doc := range docs {
        wg.Add(1)
        go func(d string) {
            defer wg.Done()
            for _, word := range strings.Fields(d) {
                counts[word]++ // DATA RACE: unsynchronized map write
            }
        }(doc)
    }
    wg.Wait()
    return counts
}

// Step 3: "make it thread-safe" — a mutex around the shared map
func wordCountSafe(docs []string) map[string]int {
    counts := make(map[string]int)
    var mu sync.Mutex
    var wg sync.WaitGroup
    for _, doc := range docs {
        wg.Add(1)
        go func(d string) {
            defer wg.Done()
            local := make(map[string]int)
            for _, word := range strings.Fields(d) {
                local[word]++ // accumulate locally first — no lock needed yet
            }
            mu.Lock()
            for word, n := range local {
                counts[word] += n // merge into shared state under the lock
            }
            mu.Unlock()
        }(doc)
    }
    wg.Wait()
    return counts
}
```

- **The interview-level insight:** a plain Go `map` is exactly as
  unsynchronized as a Python `dict` — "goroutines are lightweight"
  says nothing about whether shared state they touch is safe, the same
  lesson as
  [Threading & the GIL's threading pitfalls](../../python/concurrency/threading-and-the-gil.md#threading-problems-and-how-to-fix-them)
  applied to a different language.
- `sync.Mutex` is Go's direct equivalent of Python's `threading.Lock`
  — `mu.Lock()`/`mu.Unlock()` (usually paired with `defer mu.Unlock()`
  in real code) bracket the critical section the same way Python's
  `with lock:` does. `sync.RWMutex` adds a reader/writer split — many
  concurrent readers, one exclusive writer — for the common case where
  reads vastly outnumber writes. `sync.Once` runs initialization code
  exactly once no matter how many goroutines call it concurrently.
- Accumulating into a **local** map per goroutine and only locking to
  merge it into the shared map at the end (Step 3) minimizes time
  spent holding the lock — the same contention-reduction instinct as
  batching writes, rather than taking the lock on every single
  increment.
- `go vet` and running tests with `go test -race` catch exactly this
  class of bug — the race detector would flag Step 2's `counts[word]++`
  immediately, the equivalent rigor to actually running Python's
  threading race demo enough times to see it fail.

## 4. Common Concurrency Patterns

```go
// Worker pool — a fixed number of goroutines pulling from a shared job channel
func workerPool(jobs <-chan int, results chan<- int, numWorkers int) {
    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs { // reads until the channel is closed
                results <- process(job)
            }
        }()
    }
    wg.Wait()
    close(results)
}
```

- **Worker pool** — a fixed number of goroutines consuming from a
  shared channel, bounding concurrency instead of launching one
  goroutine per item unboundedly — the same reasoning as a thread pool
  in any language, see
  [Worker Pools & Backpressure](../../python/concurrency/worker-pools-and-backpressure.md)
  for the general concept this instantiates in Go specifically.
- **Fan-out/fan-in** — fan-out distributes work across multiple
  goroutines reading the same input channel; fan-in merges multiple
  output channels back into one, usually with its own `sync.WaitGroup`
  to know when every producer has finished before closing the merged
  channel.
- **Pipeline** — chaining stages together, each stage its own
  goroutine reading from an input channel and writing to an output
  channel, so each stage runs concurrently with the ones before and
  after it rather than the whole pipeline processing one item fully
  before starting the next.
- `range` over a channel reads values until the channel is `close`d —
  the idiomatic way a consumer knows a producer is done, instead of a
  sentinel value or explicit "done" flag.

## 5. Context: Cancellation, Timeouts & Request-Scoped Values

```go
func fetchUserWithTimeout(ctx context.Context, userID string) (*User, error) {
    ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
    defer cancel()
    return userService.Get(ctx, userID)
}
```

- `context.Context` carries cancellation signals, deadlines, and
  request-scoped values through a call chain — critical in a
  distributed system, where one slow downstream call shouldn't hang a
  request indefinitely.
- `context.WithTimeout`/`WithCancel` return a derived context and a
  `cancel` function; calling `cancel()` (always via `defer`, so it
  runs even on an early return) signals every goroutine holding that
  context to stop — a function that respects context should check
  `ctx.Done()` in any loop or blocking operation, not just pass the
  context along unused.
- **Interview point:** the convention is that `context.Context` is
  always the *first* parameter of any function that does I/O or could
  block, and it's never stored in a struct — this keeps cancellation
  scoped to exactly the call chain it belongs to, not leaked into
  longer-lived state.

## 6. Interview Questions You're Likely to Get Asked

**Goroutines & scheduling**

- "How do goroutines differ from OS threads, and why does that matter
  at scale?" — expects the stack-size and M:N scheduling difference,
  [§1](#1-goroutines-vs-os-threads-vs-pythons-asyncio).
- "Is Go concurrency the same as Python's asyncio?" — expects the
  real-parallelism-vs-single-thread-event-loop distinction,
  [§1](#1-goroutines-vs-os-threads-vs-pythons-asyncio).

**Channels & synchronization**

- "What's the difference between a buffered and unbuffered channel's
  blocking behavior?" — expects the synchronization-point vs. queue
  distinction, [§2](#2-channels-gos-own-words-for-it).
- "Two goroutines write to the same map concurrently with no lock —
  what happens?" — expects naming the data race and `sync.Mutex` as
  the fix, [§3](#3-shared-state-still-needs-synchronization).

**Patterns & context**

- "How do you bound the number of concurrent goroutines processing a
  large job list?" — expects a worker pool,
  [§4](#4-common-concurrency-patterns).
- "Where does `context.Context` belong in a function signature, and
  why shouldn't it live in a struct?" — expects first-parameter
  convention and call-chain scoping, [§5](#5-context-cancellation-timeouts-request-scoped-values).

---

## Code Samples

No dedicated code samples for this page — every snippet above is a
complete, runnable pattern with `go run` (the worker pool and pipeline
examples need a `process`/stage function supplied).
