---
title: Async Rust Internals - Futures, Wakers, Pin, and Writing an Executor
---

# Async Rust Internals - Futures, Wakers, Pin, and Writing an Executor

**Async** lets one thread run **many tasks** by switching between them
whenever one has to wait (for the network, a timer, a file). In Rust, an
`async fn` does not run when you call it. It returns a **future**: a plain
value that describes the work and can be asked "are you done yet?" by calling
`poll`. **Nothing in the language runs futures.** A library called a
**runtime** (Tokio, smol) does that. This page opens the box: what an
`async fn` turns into, how a **waker** tells the runtime to try again, why
**`Pin`** exists, and a complete executor in about 50 lines of standard
library code.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Every example ran on
    1.99.1 with the standard library only. `Waker::noop` and async closures
    (`async |x| ...`, `AsyncFn*` traits) are stable since **1.85**.
    `async fn` in traits is stable since 1.75. The official Async Book is
    being rewritten and is partly unfinished: use it with care and prefer the
    standard library documentation for `std::future`, `std::task`, and
    `std::pin`.

## 1. "What does an `async fn` compile to?"

```rust
async fn add_slowly(a: u32, b: u32) -> u32 {
    Timer::new(Duration::from_millis(30)).await;
    a + b
}
```

**Answer:**

- The compiler turns the body into a **state machine**: a hidden `enum`-like
  type that implements the **`Future`** trait. Each `.await` is a point where
  the machine can **pause** and later **resume**.
- The type stores **everything that is alive across an `.await`**: the
  arguments, local variables, and the future being awaited. Nothing else.
  That is why a future is an ordinary, movable-until-polled **value** that
  needs no heap allocation of its own.
- The size is real and measurable. From the sample (`size_of_val`):

| Future | Size in bytes | Why |
|---|---|---|
| `async {}` | 1 | only the state tag |
| `add_slowly(1, 2)` (not yet polled) | 32 | arguments plus the `Timer` it will create |
| `big_buffer()` with a `[u8; 1024]` alive across an `.await` | 1026 | the buffer lives **inside the future** |
| `Box::pin(big_buffer())` | 8 | just a pointer; the future is on the heap |

- Consequences:
    - A **large local across an `.await` makes the future large**. Futures are
      moved when spawned and when nested, so this costs copies. Box the big
      one (`Box::pin`) or shrink what lives across the await.
    - An `async` call **inside** another `async` fn is **inlined** into the
      parent's state machine. **Recursion** needs `Box::pin` because the type
      would otherwise contain itself.
    - The compiler writes the state machine, but the **rules are ordinary**
      ownership rules. See [Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md).

## 2. "What are `Future`, `Poll`, `Context`, and `Waker`?"

```rust
pub trait Future {
    type Output;
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>;
}
pub enum Poll<T> { Ready(T), Pending }
```

**Answer:**

- `poll` is called by the **executor**. It runs the future **as far as it can
  go** and returns either `Ready(value)` (finished) or `Pending` (blocked).
  `poll` must **never block** the thread.
- When a future returns `Pending`, it promises: "**I will call the waker when
  I can make progress.**" The waker is found in the `Context`
  (`cx.waker()`). Without that promise nobody would ever poll the future
  again, and the task would hang forever. A `Pending` that forgot to arrange
  a wake-up is the classic hand-written-future bug.
- `Waker::wake()` tells the executor "put this task back in the ready
  queue". A clone of the waker can go to **any thread**.
- **A hand-written future**, a countdown that wakes itself each time. Real
  output (`block_on` is in §3):

    ```text
    Countdown::poll, 3 left
    Countdown::poll, 2 left
    Countdown::poll, 1 left
    result = liftoff, polled 4 times
    ```

- **A timer future** that is woken from a helper thread:

    ```rust
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        let mut st = self.shared.lock().unwrap();
        if st.done {
            Poll::Ready(())
        } else {
            st.waker = Some(cx.waker().clone());   // always store the LATEST waker
            Poll::Pending
        }
    }
    ```

    The helper thread sleeps, sets `done = true`, and calls `waker.wake()`.
    The sample runs two chained `add_slowly` calls and reports `sum = 13,
    polls = 3`: **one poll to start, one per timer wake-up**, and no polls
    in between. That is the whole point: while the timer waits, the thread is
    free.
- **Store the newest waker on every `Pending`.** The task may have moved to
  a different executor thread between polls, and an old waker would wake the
  wrong place.
- `poll` is a **hint**, not a guarantee: an executor may poll a future again
  without a wake-up, so `poll` must be safe to call at any time (**spurious
  polls**).
- `Poll`'s two variants are the whole model. There are no callbacks and no
  hidden threads.

## 3. "How do you write an executor?"

```rust
/// Run one future to completion on the current thread.
fn block_on<F: Future>(fut: F) -> (F::Output, usize) {
    let mut fut = std::pin::pin!(fut);
    let flag = Arc::new(Flag { woken: Mutex::new(false), cv: Default::default(), wakes: AtomicUsize::new(0) });
    let waker = Waker::from(Arc::clone(&flag));       // Flag implements std::task::Wake
    let mut cx = Context::from_waker(&waker);
    let mut polls = 0;
    loop {
        polls += 1;
        if let Poll::Ready(v) = fut.as_mut().poll(&mut cx) {
            return (v, polls);
        }
        let mut woken = flag.woken.lock().unwrap();   // sleep until somebody calls wake()
        while !*woken { woken = flag.cv.wait(woken).unwrap(); }
        *woken = false;
    }
}
```

**Answer:**

- An executor needs only three things: **a place to store tasks**, a
  **waker** that marks one ready, and a **loop** that polls ready tasks. The
  code above is a real executor for a single future: it polls, and if the
  result is `Pending` it **sleeps on a condition variable** until a waker
  fires. (See [Threads & Synchronization §5](rust-threads-and-synchronization.md#5-when-do-you-use-rwlock-condvar-barrier-and-oncelock)
  for `Condvar`.)
- `std::task::Wake` is the easy way to build a `Waker`: implement `wake` on a
  type inside an `Arc`, then `Waker::from(arc)`. Before it existed, you had
  to fill in a raw vtable (`RawWaker`) by hand, with `unsafe`.
- **Many tasks:** keep a queue of boxed futures
  (`Pin<Box<dyn Future<Output = ()>>>`), poll the front one, push it back if
  `Pending`. The sample's `Executor` does this with `Waker::noop()` (a waker
  that does nothing, so it just **busy-polls**) and two workers that
  `YieldNow().await` between steps:

    ```text
    order: ["a1", "b1", "a2", "b2", "a3", "b3"]
    ```

    The tasks **interleave** on one thread. That is concurrency without
    threads.
- A **real** runtime adds: a ready queue that wakers push into (so it does not
  busy-poll), an **I/O driver** (epoll, kqueue, or IOCP: the operating
  system's "tell me when this socket is readable" calls) that calls wakers
  when I/O is ready, a **timer wheel**, and for multi-thread runtimes
  **work stealing** across worker threads.
- **A good exercise:** extend the sample so the `Executor` stores a waker per
  task and sleeps when the queue is empty. That is the "tiny async runtime"
  capstone in [Capstone Projects](../mastery/rust-capstone-projects.md).

## 4. "Are futures lazy? What does cancellation mean?"

**Answer:**

- **Futures are lazy.** Creating one runs **nothing**. The sample proves it:

    ```text
    created the future, nothing printed yet
    (body running)
    after block_on: 1
    ```

  This differs from JavaScript promises, which start immediately. In Rust a
  forgotten future (never `.await`ed, never spawned) silently does nothing.
  The compiler warns: futures are `#[must_use]`.
- **Cancelling a future = dropping it.** No special mechanism. The state
  machine is just a value, so dropping it runs the destructors of everything
  alive at the **current `.await`**:

    ```text
    Noisy dropped (future cancelled mid-way)
    ```

  The code after the `.await` simply never runs.
- This is **powerful** (a timeout is "drop the future") and **dangerous**:
  a future may be dropped **between any two `.await`s**, leaving shared state
  half updated, or losing data it held. That is **cancellation safety**, see
  [Tokio & Async Patterns §3](rust-tokio-and-async-patterns.md#3-what-is-cancellation-safety-and-how-do-select-and-timeouts-work).
- Destructors cannot `.await` (there is no async `Drop` in stable Rust).
  Clean up with an explicit async `shutdown()` call, not in `drop`.

## 5. "Why does `Pin` exist?"

**Answer:**

- **The problem:** a state machine can hold a **reference to its own
  fields**. Inside an `async fn`, `let r = &buffer; other().await; use(r);`
  stores both `buffer` and a pointer to it in the same future. If the future
  is **moved** (copied to a new address), the pointer still points at the
  **old** address, which is now garbage. This is a **self-referential
  struct**, and plain Rust references cannot express it.
- **The solution:** `Pin<P>` wraps a pointer and **promises the target will
  not move** until it is dropped. `poll` takes `self: Pin<&mut Self>`, so the
  future can rely on a stable address once polling starts.
- **`Unpin`** is an auto trait that means "moving me is harmless". Almost all
  types are `Unpin`, so `Pin` costs nothing for them. A compiler-generated
  future is **not** `Unpin` (it may be self-referential). `PhantomPinned`
  opts a type out. Real error when you try to get a plain `&mut` view of a
  type that is not `Unpin`:

    ```text
    error[E0277]: `PhantomPinned` cannot be unpinned
      --> pin_unpin_move.rs:11:31
       |
    11 |     let mut pinned = Pin::new(&mut a);
       |                      -------- ^^^^^^ within `SelfRef`, the trait `Unpin` is not implemented for `PhantomPinned`
       |
       = note: consider using the `pin!` macro
               consider using `Box::pin` if you need to access the pinned value outside of the current scope
    ```

- **How you pin in practice:**

| Need | Tool | Where the future lives |
|---|---|---|
| Poll a future right here | `std::pin::pin!(fut)` | the stack |
| Store or return it, or make a `dyn Future` | `Box::pin(fut)` | the heap |
| Await it | `.await` | pinned for you |

- You rarely write `Pin` yourself. You meet it when you **write a manual
  `Future`**, build an executor, or store futures in a collection. A short
  summary of the idea is in
  [Smart Pointers §7](../foundations/rust-smart-pointers.md#7-what-is-pin-in-one-paragraph).

## 6. "What does `async fn` in a trait do, and why can't it be `dyn`?"

```rust
trait Fetch { async fn fetch(&self) -> u32; }      // fine with generics

fn generic<T: Fetch + Sync>(t: &T) { needs_send(t.fetch()); }   // error
```

**Answer:**

- `async fn` in traits is stable (since 1.75). It works with **generics**:
  `async fn use_generic<T: Fetch>(t: &T)` compiled and ran in the sample.
- **Problem 1: `Send`.** The trait does not say whether the returned future is
  `Send`, so generic code that needs it (for example to hand it to a
  multi-threaded runtime) fails. Real error:

    ```text
    error[E0277]: `impl Future<Output = u32>` cannot be sent between threads safely
      --> async_trait_unknown_send.rs:10:16
       |
    10 |     needs_send(t.fetch());
       |     ---------- ^^^^^^^^^ `impl Future<Output = u32>` cannot be sent between threads safely
       |
    help: `Send` can be made part of the associated future's guarantees for all implementations of `Fetch::fetch`
       |
     4 -     async fn fetch(&self) -> u32;
     4 +     fn fetch(&self) -> impl std::future::Future<Output = u32> + Send;
    ```

  The compiler's own fix is the answer: declare the method as
  `fn fetch(&self) -> impl Future<Output = u32> + Send`. Implementations may
  **still be written as `async fn`**. The sample's `SendFetch` shows it.
- **Problem 2: `dyn`.** A trait with an `async fn` is **not dyn compatible**,
  because each implementation returns a **different future type** with a
  different size, and a vtable needs one fixed signature:

    ```text
    error[E0038]: the trait `Fetch` is not dyn compatible
      |
    2 |     async fn fetch(&self) -> u32;
      |              ^^^^^ ...because method `fetch` is `async`
    ```

- **Workaround for `dyn`:** return a boxed future by hand,
  `fn fetch(&self) -> Pin<Box<dyn Future<Output = u32> + '_>>`. This costs one
  allocation per call. The sample shows it working (`dyn via boxed future:
  3`). The `async-trait` crate generates exactly this code for you.
- Background on dyn compatibility:
  [Traits & Generics §3](../foundations/rust-traits-and-generics.md#3-what-does-it-mean-that-a-trait-is-dyn-compatible).

## 7. "What are async closures and the `AsyncFn` traits?"

```rust
async fn apply<F>(f: F, x: &str) -> usize
where
    F: AsyncFn(&str) -> usize,
{
    f(x).await
}

let n = apply(async |s| s.len(), "hello").await;   // 5
```

**Answer:**

- An **async closure** (`async |x| ...`, stable in **1.85**) is a closure whose
  call returns a future, and that future may **borrow from the closure and
  from its arguments**.
- Before, the usual attempt `|x| async move { ... }` was a normal closure that
  **returns** a future. That could not express "the returned future borrows
  my argument", so higher-order helpers with borrowed arguments were
  impossible without boxing.
- The traits are **`AsyncFn`, `AsyncFnMut`, `AsyncFnOnce`**, parallel to
  `Fn`, `FnMut`, `FnOnce` (see
  [Iterators & Closures](../foundations/rust-iterators-and-closures.md)).
  Use them as bounds, as above.
- The sample's `blocking_the_executor` example passes
  `impl AsyncFnOnce()` the same way.

## 8. "Why does the compiler say 'future cannot be sent between threads safely'?"

```rust
async fn uses_rc() {
    let local = Rc::new(1);
    yield_now().await;           // `local` is alive across this await
    println!("{local}");
}
```

**Answer:**

- A multi-thread runtime (Tokio's default) may **resume a task on a different
  thread** after an `.await`. So the future must be **`Send`**. A future is
  `Send` only if **everything alive across an `.await`** is `Send`.
- Real error:

    ```text
    error: future cannot be sent between threads safely
      --> future_not_send_rc.rs:15:18
       |
    15 |     require_send(uses_rc());
       |                  ^^^^^^^^^ future returned by `uses_rc` is not `Send`
       |
       = help: within `impl Future<Output = ()>`, the trait `Send` is not implemented for `Rc<i32>`
    note: future is not `Send` as this value is used across an await
       |
     7 |     let local = Rc::new(1);
       |         ----- has type `Rc<i32>` which is not `Send`
     8 |     yield_now().await;
       |                 ^^^^^ await occurs here, with `local` maybe used later
    ```

  Note how the message names the **value** and the **await** point. That is
  the best clue you get.
- The **same error with a `std::sync::MutexGuard`** (the guard is not `Send`,
  and holding a lock across an `.await` is also a deadlock risk) is shown
  with real output in
  [Tokio & Async Patterns §7](rust-tokio-and-async-patterns.md#7-what-are-the-classic-async-mistakes).
- Fixes: **drop** the value before the `.await` (a smaller scope), use a
  `Send` replacement (`Arc` for `Rc`, an async `Mutex`), or run on a
  **single-threaded** runtime where `Send` is not required
  (`tokio::task::LocalSet`, current-thread runtime).

## 9. "Which runtime do you pick, and what does a runtime add?"

**Answer:**

- The standard library gives **only** `Future`, `Poll`, `Context`, `Waker`,
  and `async`/`await`. **A runtime is a library**: executor, timers, an I/O
  driver, and async versions of sockets, files, and channels.
- Choices today:
    - **Tokio**: the default in production (multi-thread, big ecosystem:
      `hyper`, `axum`, `tonic`, `sqlx`). Covered in
      [Tokio & Async Patterns](rust-tokio-and-async-patterns.md).
    - **smol**: small, simple, and the recommended replacement for
      `async-std`.
    - **`async-std` is discontinued.** Its own README says so and tells
      users to switch to `smol`.
    - **Embassy**: async for microcontrollers, with no heap
      ([no_std & Embedded Rust](../performance-and-internals/rust-no-std-and-embedded.md)).
- **Portability trap:** I/O types are **tied to their runtime**. A Tokio
  `TcpStream` does not work in a smol executor without an adapter. Libraries
  that must work everywhere take generic `AsyncRead`/`AsyncWrite` or accept a
  feature flag.
- **Async is not always the answer.** It pays off for **many concurrent,
  mostly waiting** tasks (servers, proxies). For CPU-bound work or a handful
  of connections, plain threads are simpler and just as fast
  ([Threads & Synchronization](rust-threads-and-synchronization.md)).

## 10. "How do AI tools help or hurt with async Rust?"

**Answer:**

- **Good at:** explaining the "cannot be sent between threads" error (ask it
  to name the value and the await), and generating a first `block_on`.
- **Weak at:** `Pin` and wakers. Generated hand-written futures often
  return `Pending` **without registering a waker**. The program compiles,
  then hangs. Always ask: "where is the waker stored, and who calls it?"
- Models trained on older code produce **old idioms**: the `async-std` crate,
  `futures::executor::block_on` where Tokio is already in use, `RawWaker`
  vtables instead of `Wake`, `|x| async move` instead of async closures.
- Verify the **runtime mix**. Generated code often mixes Tokio and
  `async-std` types, which fail at run time, not compile time.
- Ask the tool to **explain a state machine for your function** (what is
  stored across each `.await`). If it cannot, you cannot trust the rest.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Core model**

- "What does an `async fn` return, and what does it compile to?" — expects
  an anonymous `impl Future`, a state machine that stores locals across
  awaits, [§1](#1-what-does-an-async-fn-compile-to).
- "Who runs a future?" — expects an executor from a runtime library; the
  language has none, [§2](#2-what-are-future-poll-context-and-waker).
- "What is a `Waker` and what happens if you forget to call it?" — expects
  the task is never polled again and hangs,
  [§2](#2-what-are-future-poll-context-and-waker).
- "Are futures lazy?" — expects yes, nothing runs until polled,
  [§4](#4-are-futures-lazy-what-does-cancellation-mean).

**Pin and cancellation**

- "Why does `Pin` exist?" — expects self-referential state machines,
  [§5](#5-why-does-pin-exist).
- "What is `Unpin`?" — expects "moving is harmless", most types,
  [§5](#5-why-does-pin-exist).
- "How do you cancel a future?" — expects drop it, and the safety caveat,
  [§4](#4-are-futures-lazy-what-does-cancellation-mean).

**Traits and Send**

- "Why can't you make a `dyn` trait object from a trait with `async fn`?" —
  expects each impl returns a different future type,
  [§6](#6-what-does-async-fn-in-a-trait-do-and-why-cant-it-be-dyn).
- "What is an async closure and how does it differ from `|x| async move {}`?"
  — expects borrowing from arguments, `AsyncFn` traits,
  [§7](#7-what-are-async-closures-and-the-asyncfn-traits).
- "Why must futures be `Send` for `tokio::spawn`?" — expects tasks may move
  between threads at an await,
  [§8](#8-why-does-the-compiler-say-future-cannot-be-sent-between-threads-safely).

**Design**

- "How would you implement `block_on`?" — expects pin, a waker that unparks
  or notifies, a poll loop, [§3](#3-how-do-you-write-an-executor).
- "When would you choose threads over async?" — expects CPU-bound work or
  few tasks, [§9](#9-which-runtime-do-you-pick-and-what-does-a-runtime-add).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/async_executor.rs` — `Countdown` and `Timer` futures, a
  `Wake`-based `block_on`, a round-robin `Executor`, laziness, future sizes,
  cancellation by drop, and an async closure.
- `examples/async_traits.rs` — `async fn` in a trait, the `Send`-bounded
  form, the boxed-future `dyn` workaround, and an `AsyncFn` bound.
- `compile_fail/future_not_send_rc.rs`, `async_trait_unknown_send.rs`,
  `async_fn_in_dyn_trait.rs`, `pin_unpin_move.rs` — the real errors quoted
  above.

```bash
cd code_samples/rust
cargo run --example async_executor
cargo run --example async_traits
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/future_not_send_rc.rs   # must fail
```
