---
title: Tokio & Async Patterns in Rust
---

# Tokio & Async Patterns in Rust

**Tokio** is the most used **async runtime** for Rust. It provides what the
language does not: an **executor** that runs tasks on a pool of threads, a
**timer**, an **I/O driver** for sockets and files, and async versions of
channels and locks. This page is the practical side of
[Async Internals](rust-async-internals.md): how to start tasks, wait for
several things at once, stop work safely, limit load, shut down cleanly, and
avoid the mistakes that make async programs hang or stall.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**, with **Tokio 1.54.1**,
    `tokio-util` 0.7.20, and `tokio-stream` 0.1.19 (current when this was
    written, added with `cargo add`). Every example ran. Tokio is a normal
    crate, so check `cargo add tokio` for the version on your day.

## 1. "What does `#[tokio::main]` do, and which runtime flavor do you pick?"

```rust
#[tokio::main]                              // multi-thread flavor (default)
async fn main() { /* ... */ }

#[tokio::main(flavor = "current_thread")]   // one thread only
async fn main() { /* ... */ }
```

**Answer:**

- `#[tokio::main]` is a **macro** that builds a runtime and calls
  `block_on` on your `async fn main`. It is shorthand for creating the runtime
  by hand.
- Two **flavors**:

| Flavor | Threads | Tasks must be `Send`? | Use it for |
|---|---|---|---|
| `multi_thread` (default) | one worker per CPU core, **work stealing** | **yes** | servers, anything parallel |
| `current_thread` | the calling thread only | no (with `LocalSet`) | tests, CLIs, simple tools, `!Send` data |

- **Concurrency is not parallelism.** On `current_thread`, many tasks still
  make progress at once by interleaving at `.await`, but never run at the
  same instant.
- A task runs **until its next `.await`** and then yields. A task that
  never awaits **monopolizes** its thread (see §7).
- Add features deliberately: `tokio = { version = "...", features = ["full"] }`
  is convenient for learning. In a library or a small binary, list only what
  you need (`rt`, `macros`, `net`, `time`, `sync`) to cut compile time.

## 2. "How do you run things concurrently: `spawn`, `JoinHandle`, and `JoinSet`?"

```rust
let ok  = tokio::spawn(async { 1 + 1 });
let bad = tokio::spawn(async { if true { panic!("task blew up"); } 0 });
println!("{:?}", ok.await);                    // Ok(2)
println!("{}", bad.await.unwrap_err().is_panic());   // true

let mut set = JoinSet::new();
for i in 1..=3u64 {
    set.spawn(async move { sleep(Duration::from_millis(30 * (4 - i))).await; i });
}
while let Some(r) = set.join_next().await { /* 3, then 2, then 1 */ }
```

**Answer:**

- `tokio::spawn` starts a **task** (a future the runtime owns and drives) and
  returns a `JoinHandle<T>`. The task **starts right away**, even if you
  never await the handle.
- The future must be **`Send + 'static`**: it may move between threads, and it
  cannot borrow local variables. The `'static` error has the same cause as for
  `thread::spawn`; the real message is in §7.
- **A panic inside a task does not crash the program.** The runtime catches
  it and `.await` on the handle returns `Err(JoinError)`. `is_panic()` tells
  you why; the sample prints `true`. Always handle the `Result`, or panics
  vanish silently.
- **`JoinSet`** is the tool for "start N tasks and collect the results":
    - `join_next().await` returns results **in finish order** (the sample
      printed `[3, 2, 1]`, the reverse of the start order).
    - **Dropping a `JoinSet` aborts all its tasks.** That is **structured
      concurrency**: tasks cannot outlive the scope that owns the set. Raw
      `spawn` tasks are detached and can leak.
- `tokio::join!(a, b)` runs futures **concurrently on the same task** and
  waits for **all**. `tokio::try_join!` stops at the first error. Use
  `spawn` when you need real parallelism or independent lifetimes.
- A `JoinHandle` can `abort()` its task. The task is cancelled at its next
  `.await`, see §3.

## 3. "What is cancellation safety, and how do `select!` and timeouts work?"

```rust
// timeout: drop the inner future if the deadline passes
let r = timeout(Duration::from_millis(20), sleep(Duration::from_secs(5))).await;
assert!(r.is_err());

// select!: wait for the FIRST of several futures; the others are dropped
tokio::select! {
    _ = sleep(Duration::from_millis(10)) => println!("timer won"),
    _ = sleep(Duration::from_secs(5))   => println!("slow won"),
}
```

**Answer:**

- `select!` polls several futures and runs the branch of the **first** that
  finishes. **All the others are dropped.** Dropping a future cancels it, as
  explained in
  [Async Internals §4](rust-async-internals.md#4-are-futures-lazy-what-does-cancellation-mean).
  `timeout` is the same idea with a timer.
- A future is **cancellation safe** if dropping it at an `.await` loses
  nothing: you can start it again and no data is gone. It is **not** safe if
  it has already **consumed** something it now holds only in its own state.
- Real demonstration (`cancel_safety` sample). The function reads two items,
  and the timer fires between them:

    ```rust
    async fn recv_pair(rx: &mut mpsc::Receiver<u32>) -> Option<(u32, u32)> {
        let first = rx.recv().await?;
        let second = rx.recv().await?;   // <- dropped here: `first` is gone
        Some((first, second))
    }
    ```

    ```text
    timeout, recv_pair future dropped
    items still in the channel: [2, 3]  (the 1 is gone: it was held inside the dropped future)
    ```

  The `1` was taken out of the channel and lived only inside the dropped
  future.
- **The fix is to keep partial state outside the future** that can be
  dropped (a variable in the enclosing loop):

    ```text
    timeout tick, partial state kept: Some(1)
    fixed pair: (1, 2)
    ```

- Rules of thumb:
    - `mpsc::Receiver::recv`, `Semaphore::acquire`, `Mutex::lock`, and
      `sleep` are documented as **cancellation safe**.
    - Methods that **read part of a message and keep it internally**, such
      as `AsyncReadExt::read_exact` and a hand-written multi-step `async fn`,
      are **not**. Check the "Cancel safety" section in each method's docs.
    - In a `select!` **loop**, create the long-lived futures **outside** the
      loop and pass `&mut fut`, or use a `watch`/`mpsc` channel.
- `tokio::select!` also supports `biased;` (poll in written order, not
  random) and `else` (when all branches are disabled).

## 4. "Which channel do you use, and how do you get backpressure?"

```rust
let (tx, mut rx) = mpsc::channel::<u32>(2);       // capacity 2
let producer = tokio::spawn(async move {
    for i in 0..5 {
        tx.send(i).await.unwrap();                // waits while 2 items are queued
    }
});
```

**Answer:**

| Channel | Producers : consumers | Message kept | Use it for |
|---|---|---|---|
| `mpsc` | many : one | queued in order | work queues, event streams |
| `oneshot` | one : one | exactly one value | a reply to a request |
| `broadcast` | many : many | every receiver gets every message | notifications, fan-out |
| `watch` | one : many | **only the latest** value | configuration, shutdown flag, state |

- Sample results: `oneshot: reply`; `broadcast: hello all / hello all` (two
  receivers each got it); `watch keeps only the latest: 2` (the value `1` was
  overwritten before anyone looked).
- **Backpressure** means a fast producer is **slowed down** by a slow
  consumer instead of filling memory. A **bounded** `mpsc::channel(n)` does
  it: `send().await` **waits** while `n` items are queued. The sample used a
  slow consumer and reported the producer was held back.
- **Avoid `mpsc::unbounded_channel`** unless the producer is naturally limited.
  It never pushes back, so a traffic burst turns into memory growth.
- A **`Semaphore`** limits how many things run at once (database
  connections, outgoing requests). Six tasks with `Semaphore::new(2)` reached
  a peak concurrency of exactly **2**. The permit is released on drop.
- A task that **never stops accepting** work is the usual cause of
  out-of-memory in async services. Bound **every** queue, and decide what
  happens when it is full: wait, drop, or reject with an error.
- For thread-based code, see
  [Threads & Synchronization §6](rust-threads-and-synchronization.md#6-how-do-channels-work-and-when-do-you-prefer-them).

## 5. "How do you shut down gracefully?"

```rust
let token = CancellationToken::new();
let worker_token = token.clone();
let worker = tokio::spawn(async move {
    let mut ticks = 0;
    loop {
        tokio::select! {
            _ = worker_token.cancelled() => return ticks,    // finish, flush, leave
            _ = sleep(Duration::from_millis(10)) => ticks += 1,
        }
    }
});
sleep(Duration::from_millis(55)).await;
token.cancel();
let ticks = worker.await.unwrap();      // the task ended by itself, cleanly
```

The sample printed `worker stopped cleanly after 4 ticks` (the number varies
slightly with timing).

**Answer:**

- **Graceful shutdown** has three parts: **detect** the signal, **tell every
  task**, and **wait** for them to finish.
- **Detect:** `tokio::signal::ctrl_c().await` (and on Unix
  `signal(SignalKind::terminate())`, which is what containers send).
- **Tell:** a **`CancellationToken`** (from `tokio-util`) is cloned into every
  task. `cancel()` wakes all of them. A `watch` channel carrying a `bool`
  works the same way without an extra crate.
- **Wait:** keep the `JoinHandle`s or a `JoinSet` and `.await` them, often
  with an **overall timeout** so a stuck task cannot block the exit forever.
- **Do not just drop the runtime.** Tasks are killed at their next await,
  with no chance to flush buffers or close connections.
- In a web server, the framework takes the shutdown future. See
  [Web Services with Axum](../production/rust-web-services-with-axum.md).
- Order matters: **stop accepting** new work first, **drain** in-flight work,
  then close shared resources (database pool, files).

## 6. "How do you share state between tasks: a mutex or an actor?"

```rust
enum Msg { Add(u64), Get(oneshot::Sender<u64>) }

fn spawn_counter_actor() -> mpsc::Sender<Msg> {
    let (tx, mut rx) = mpsc::channel(16);
    tokio::spawn(async move {
        let mut total = 0;                       // owned by ONE task: no lock needed
        while let Some(m) = rx.recv().await {
            match m {
                Msg::Add(n) => total += n,
                Msg::Get(reply) => { let _ = reply.send(total); }
            }
        }
    });
    tx
}
```

The sample added 1 through 4 and read back `actor total: 10`.

**Answer:**

- **Option 1: `Arc<Mutex<T>>`.** Simple, good for a small structure with short
  critical sections. Which `Mutex`?
    - **`std::sync::Mutex`** (the default recommendation): fast, and fine as
      long as you **never hold the guard across an `.await`**. Lock, change,
      unlock, in one synchronous block.
    - **`tokio::sync::Mutex`**: its guard **can** be held across an `.await`
      (the sample did this), at the cost of being slower. Use it only when
      you must `.await` while holding the lock (for example, to write to a
      connection that only one task may use at a time).
- **Option 2: an actor.** One task **owns** the state and receives
  **messages** over a channel. Other tasks hold a `Sender` (the "handle").
    - No locks, no poisoning, no guard-across-await mistakes.
    - Requests that need an answer include a **`oneshot::Sender`** for the
      reply, as `Msg::Get` does.
    - It serializes access (one message at a time) and a bounded channel gives
      **backpressure** for free.
- Choose the **mutex** for simple shared data, and the **actor** when the
  state has real logic, does I/O, or needs ordering. Background on the
  non-async types: [Smart Pointers §3](../foundations/rust-smart-pointers.md#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for).

## 7. "What are the classic async mistakes?"

**Answer:**

**Mistake 1: blocking the executor.** A task that calls a blocking function
(`std::thread::sleep`, a heavy loop, a synchronous file or database call)
**holds its worker thread**, and every other task on that thread waits. Real
measurement on a **single-threaded** runtime: a 50 ms timer task is waiting
while a neighbour task blocks for 300 ms:

| What the neighbour task does | When the 50 ms timer fired |
|---|---|
| `std::thread::sleep(300ms)` | after **300 ms** |
| `spawn_blocking` around the same sleep | after **50 ms** |

- `tokio::task::spawn_blocking` moves the work to a **separate pool of
  threads** meant for blocking calls. Use it for CPU-heavy functions
  (the sample summed a million numbers there), synchronous libraries, and
  file-system APIs without async support.
- For a long CPU job inside an async fn, call `tokio::task::yield_now().await`
  periodically, or use `rayon` on a blocking thread
  ([Threads & Synchronization §8](rust-threads-and-synchronization.md#8-how-do-you-use-all-cpu-cores-for-a-data-parallel-task)).
- **A rule of thumb:** if a call can take longer than about 10 to 100
  microseconds without an `.await`, it can starve other tasks.

**Mistake 2: holding a `std::sync::MutexGuard` across an `.await`.** The guard
is not `Send`, so the task cannot be spawned. Real error from the sample:

```text
error: future cannot be sent between threads safely
   --> examples/zz_std_guard_across_await.rs:8:18
    |
  8 |       let handle = tokio::spawn(async move {
    |  __________________^
  9 | |         let mut guard = d.lock().unwrap();
 10 | |         *guard += 1;
 11 | |         tokio::time::sleep(Duration::from_millis(1)).await;
 12 | |     });
    | |______^ future created by async block is not `Send`
    |
    = help: within `{async block@...}`, the trait `Send` is not implemented for `std::sync::MutexGuard<'_, i32>`
note: future is not `Send` as this value is used across an await
    |
  9 |         let mut guard = d.lock().unwrap();
    |             --------- has type `std::sync::MutexGuard<'_, i32>` which is not `Send`
 11 |         tokio::time::sleep(Duration::from_millis(1)).await;
    |                                                      ^^^^^ await occurs here, with `mut guard` maybe used later
```

- Fix: end the guard's scope **before** the `.await` (copy out what you
  need), or use `tokio::sync::Mutex`, or switch to an actor (§6).
- On a **single-threaded** runtime the code would compile but could
  **deadlock**: the task holding the lock sleeps, another task blocks on
  `lock()`, and the only thread is stuck. That is why the `Send` error is
  a gift.

**Mistake 3: spawning a task that borrows a local variable.** Real error:

```text
error[E0373]: async block may outlive the current function, but it borrows `name`, which is owned by the current function
 --> examples/zz_spawn_borrows_local.rs:4:26
  |
4 |     let h = tokio::spawn(async {
  |                          ^^^^^ may outlive borrowed value `name`
  |
  = note: async blocks are not executed immediately and must either take a reference or ownership of outside variables they use
help: to force the async block to take ownership of `name` (and any other referenced variables), use the `move` keyword
```

- Fix: `async move` and clone what several tasks need (`Arc::clone`). It is
  the same root cause as in
  [Lifetimes §5](../foundations/rust-lifetimes.md#5-what-does-static-mean-it-has-two-meanings).

**Mistake 4: unbounded queues and unbounded spawning.** See §4: bound
channels, and limit concurrency with a `Semaphore`.

**Mistake 5: forgetting that a dropped `JoinHandle` detaches the task.**
Errors and panics inside it are never seen. Collect handles in a `JoinSet`.

## 8. "How do you work with streams?"

```rust
let (tx, rx) = mpsc::channel(4);
tokio::spawn(async move { for i in 0..5 { tx.send(i).await.unwrap(); } });
let evens: Vec<_> = ReceiverStream::new(rx)
    .filter(|n| n % 2 == 0)
    .map(|n| n * 10)
    .collect()
    .await;                                      // [0, 20, 40]
```

**Answer:**

- A **stream** is the async version of an iterator: **many values over
  time**, each obtained with an `.await`. The trait is `Stream` (from the
  `futures` crate, re-exported by `tokio-stream`), with `next().await`
  instead of `next()`.
- `StreamExt` gives the adapters you know from
  [Iterators & Closures](../foundations/rust-iterators-and-closures.md):
  `map`, `filter`, `take`, `chain`, `collect`, plus time-aware ones such as
  `timeout` and `throttle`.
- Wrappers such as `ReceiverStream` turn a channel into a stream.
- `buffer_unordered(n)` (in `futures::StreamExt`) is the common way to
  run **up to `n` async operations at once** over a list of inputs. It is
  often simpler than a `JoinSet` plus a `Semaphore`.
- The standard library does **not** have a stable `Stream` trait yet, so the
  ecosystem trait is what you use.

## 9. "How do you test async code, and the time-dependent parts?"

```rust
#[tokio::test(start_paused = true)]
async fn hour_long_sleep_is_instant() {
    let real = std::time::Instant::now();
    let start = tokio::time::Instant::now();
    sleep(Duration::from_secs(3600)).await;
    assert!(start.elapsed() >= Duration::from_secs(3600));
    assert!(real.elapsed() < Duration::from_secs(1));
}
```

Both tests in `tests/paused_time.rs` pass, and the one-hour sleep takes
microseconds of real time.

**Answer:**

- `#[tokio::test]` builds a **current-thread** runtime for each test and runs
  the `async fn` in it. See
  [Testing & Documentation](../foundations/rust-testing-and-documentation.md)
  for the general testing tools.
- With `start_paused = true` (needs the `test-util` feature) the **clock is
  virtual**: whenever every task is idle, time **jumps** to the next timer.
  Timeouts, retries, and heartbeats test **instantly and deterministically**.
- Never use real `sleep` to "wait for the other task" in tests. Use channels,
  `oneshot`, or paused time. Real sleeps make tests slow and flaky.
- For `select!` and cancellation, test the **cancel path** on purpose: drop
  the future in the middle and check no data was lost (the `recv_pair` test
  above).
- Race conditions between tasks are still possible. `loom` (see
  [Atomics §7](rust-atomics-and-memory-ordering.md#7-how-do-you-test-lock-free-code-with-loom))
  does not cover Tokio's runtime, so rely on careful design and
  stress tests.

## 10. "How do AI tools help or hurt with Tokio code?"

**Answer:**

- **Good at:** boilerplate (`main`, `spawn`, channels), converting blocking code
  to `spawn_blocking`, and explaining the "future cannot be sent" error.
- **Weak at:** **cancellation safety** and **blocking**. Generated code often
  puts a non-cancel-safe call in a `select!` and calls a blocking library
  inside an `async fn`. Both compile and fail only under load.
- It often reaches for `unbounded_channel` and `tokio::spawn` in a loop. Ask
  "what bounds this?" every time.
- It may use an **old API or an old crate version**. Check `Cargo.toml`
  against `cargo add` and read the compiler warnings.
- Ask for a **shutdown story** and a **test with paused time**. If the
  answer has neither, the code is not production ready.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Runtime and tasks**

- "Multi-thread vs current-thread runtime?" — expects work stealing and
  `Send` requirement vs one thread,
  [§1](#1-what-does-tokiomain-do-and-which-runtime-flavor-do-you-pick).
- "What happens when a spawned task panics?" — expects `JoinError`, the
  program continues, [§2](#2-how-do-you-run-things-concurrently-spawn-joinhandle-and-joinset).
- "`join!` vs `spawn`?" — expects same task vs separate task,
  [§2](#2-how-do-you-run-things-concurrently-spawn-joinhandle-and-joinset).
- "What does dropping a `JoinSet` do?" — expects aborts the tasks,
  [§2](#2-how-do-you-run-things-concurrently-spawn-joinhandle-and-joinset).

**Cancellation and channels**

- "What is cancellation safety? Give an unsafe example." — expects data held
  inside a dropped future, `recv_pair`,
  [§3](#3-what-is-cancellation-safety-and-how-do-select-and-timeouts-work).
- "What does `select!` do with the losing branches?" — expects they are
  dropped, [§3](#3-what-is-cancellation-safety-and-how-do-select-and-timeouts-work).
- "How do you add backpressure?" — expects bounded channel, `Semaphore`,
  [§4](#4-which-channel-do-you-use-and-how-do-you-get-backpressure).
- "When would you use `watch` over `broadcast`?" — expects latest value only,
  [§4](#4-which-channel-do-you-use-and-how-do-you-get-backpressure).
- "How do you shut a service down gracefully?" — expects signal, token,
  join with timeout, [§5](#5-how-do-you-shut-down-gracefully).

**Pitfalls and design**

- "Why must you not call `std::thread::sleep` in an async fn?" — expects
  blocks the worker, starves tasks, the 300 ms number,
  [§7](#7-what-are-the-classic-async-mistakes).
- "Why does holding a `std` mutex guard across an await fail to compile?" —
  expects guard is not `Send`, [§7](#7-what-are-the-classic-async-mistakes).
- "`std::sync::Mutex` or `tokio::sync::Mutex`?" — expects std unless you
  must hold across await, [§6](#6-how-do-you-share-state-between-tasks-a-mutex-or-an-actor).
- "What is the actor pattern in Tokio?" — expects one owner task plus
  messages, [§6](#6-how-do-you-share-state-between-tasks-a-mutex-or-an-actor).
- "How do you test a 30-second timeout quickly?" — expects `start_paused`,
  [§9](#9-how-do-you-test-async-code-and-the-time-dependent-parts).

---

## Code Samples

All files are in `code_samples/rust/async_demo/` (its own package, so the main
samples crate stays free of these dependencies) and were run on Rust 1.99.1
with Tokio 1.54.1.

- `examples/tokio_patterns.rs` — spawn and `JoinError`, `JoinSet`, `timeout`
  and `select!`, `oneshot`, `broadcast`, `watch`, backpressure,
  `Semaphore`, `CancellationToken` shutdown, `spawn_blocking`, an actor,
  async `Mutex`, and streams.
- `examples/cancel_safety.rs` — the unsafe `recv_pair` and its fix.
- `examples/blocking_the_executor.rs` — the 300 ms vs 50 ms measurement.
- `tests/paused_time.rs` — `start_paused` tests.
- `compile_fail/std_guard_across_await.rs`, `spawn_borrows_local.rs` and
  `run_compile_fail.sh` — the real errors quoted above.

```bash
cd code_samples/rust/async_demo
cargo run --example tokio_patterns
cargo run --example cancel_safety
cargo run --example blocking_the_executor
cargo test
./run_compile_fail.sh        # prints the real compiler errors; both must fail
```
