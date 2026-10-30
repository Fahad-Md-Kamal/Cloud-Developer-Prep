---
title: Threads & Synchronization in Rust
---

# Threads & Synchronization in Rust

A **thread** is an independent line of execution that the operating system
schedules on a CPU (Central Processing Unit) core. Threads share the same
memory, so two threads can touch the same value at the same time. That is a
**data race**, and in most languages it is a bug you find at run time.
**Rust turns it into a compile error**: the ownership rules from
[Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md) apply
across threads, and two marker traits (`Send` and `Sync`) say which types may
cross a thread boundary. This page covers the standard library tools:
threads, locks, channels, and `rayon` for data parallelism.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Every example ran on
    1.99.1. `rayon` 1.12.0 was used for the data-parallel examples.
    `RwLockWriteGuard::downgrade` (1.92) and `File::lock` (1.89) are newer
    additions. Timings are from the author's 10-core Apple-silicon laptop.

## 1. "How do you start a thread, and what is a scoped thread?"

```rust
use std::thread;

let h = thread::spawn(|| (1..=10).sum::<u32>());
println!("{}", h.join().unwrap());            // 55

let mut data = vec![1, 2, 3, 4, 5, 6];
let (left, right) = data.split_at_mut(3);
thread::scope(|s| {
    s.spawn(|| left.iter_mut().for_each(|x| *x *= 10));
    s.spawn(|| right.iter_mut().for_each(|x| *x *= 100));
});
println!("{data:?}");                         // [10, 20, 30, 400, 500, 600]
```

**Answer:**

- `thread::spawn` takes a closure and returns a `JoinHandle<T>`.
    - `join()` waits for the thread and returns `Result<T, _>`. The `Err`
      case means the thread **panicked**.
    - The closure must be **`'static`**: the compiler cannot know how long
      the thread lives, so it cannot borrow local variables. Use `move` to
      give it ownership.
- **Scoped threads** (`thread::scope`) lift that limit.
    - The scope guarantees every thread inside it **finishes before the
      scope returns**, so the threads may **borrow** local data.
    - In the example the two threads each borrow a **different half** of the
      vector. That is allowed because `split_at_mut` proves the halves do not
      overlap.
- The `'static` error is `E0373`, shown with its real text in
  [Lifetimes §5](../foundations/rust-lifetimes.md#5-what-does-static-mean-it-has-two-meanings).
- A dropped `JoinHandle` **detaches** the thread: it keeps running, and
  nobody sees its result or its panic. When `main` returns, the process ends
  and detached threads are killed.
- Prefer scoped threads when the work is a bounded fork-and-join. Use
  `spawn` for long-lived background threads.

## 2. "What are `Send` and `Sync`, and how does Rust prevent a data race?"

**Answer:**

- Two **auto traits** (the compiler implements them for you when all fields
  qualify) describe thread safety:

| Trait | Meaning | Example that is **not** it |
|---|---|---|
| `Send` | Ownership of a `T` may **move** to another thread | `Rc<T>`, `MutexGuard<T>` |
| `Sync` | A `&T` may be **shared** between threads (`T: Sync` means `&T: Send`) | `Cell<T>`, `RefCell<T>` |

- `thread::spawn` requires the closure to be `Send`, so you cannot move an
  `Rc` into a thread. Real compiler output:

    ```text
    error[E0277]: `Rc<i32>` cannot be sent between threads safely
     --> thread_rc_not_send.rs:7:27
      |
    7 |     let h = thread::spawn(move || println!("{s2}"));
      |             ------------- -------^^^^^^^^^^^^^^^^^
      |             |             |
      |             |             `Rc<i32>` cannot be sent between threads safely
      |             |             within this `{closure@thread_rc_not_send.rs:7:27: 7:34}`
      |             required by a bound introduced by this call
      |
      = help: within `{closure@thread_rc_not_send.rs:7:27: 7:34}`, the trait `Send` is not implemented for `Rc<i32>`
    ```

    `Rc` uses a plain (non-atomic) counter. Two threads changing it at once
    would corrupt it, so the type is not `Send`. `Arc` uses an atomic counter
    and is.
- A `RefCell` shared by reference fails the `Sync` check:

    ```text
    error[E0277]: `RefCell<i32>` cannot be shared between threads safely
     --> refcell_not_sync.rs:7:17
      |
    7 |         s.spawn(|| *cell.borrow_mut() += 1);
      |           ----- ^^^^^^^^^^^^^^^^^^^^^^^^^^ `RefCell<i32>` cannot be shared between threads safely
      |
      = help: the trait `Sync` is not implemented for `RefCell<i32>`
      = note: if you want to do aliasing and mutation between multiple threads, use `std::sync::RwLock` instead
    ```

- The classic data race (two threads incrementing a shared counter) does not
  compile either. The borrow checker sees **two mutable borrows**:

    ```text
    error[E0499]: cannot borrow `counter` as mutable more than once at a time
     --> scoped_two_mut.rs:7:17
      |
    5 |     thread::scope(|s| {
      |                    - has type `&'1 Scope<'1, '_>`
    6 |         s.spawn(|| counter += 1);
      |         ------------------------
      |         |       |  |
      |         |       |  first borrow occurs due to use of `counter` in closure
      |         |       first mutable borrow occurs here
      |         argument requires that `counter` is borrowed for `'1`
    7 |         s.spawn(|| counter += 1);
      |                 ^^ ------- second borrow occurs due to use of `counter` in closure
    ```

- Why this prevents data races: a data race needs **shared and mutable** at
  the same time. Rust's rule is "shared XOR mutable" for references. The
  **safe** ways to get both go through a type that adds synchronization
  (`Mutex`, `RwLock`, atomics), and those are the only types that are
  `Sync` while allowing mutation.
- `unsafe impl Send for T {}` is a **promise** you make to the compiler. If it
  is wrong, you get undefined behaviour. See
  [Variance, Drop Check & PhantomData](../advanced-language/rust-variance-dropck-and-phantomdata.md)
  for the auto-trait rules and how `PhantomData` opts a type out.
- **Rust prevents data races, not race conditions.** Two threads can still
  do things in a bad order (check-then-act) with perfectly safe code.

## 3. "How do you share mutable state: `Arc<Mutex<T>>`?"

```rust
use std::sync::{Arc, Mutex};

let total = Arc::new(Mutex::new(0u64));
let handles: Vec<_> = (0..8).map(|_| {
    let total = Arc::clone(&total);
    thread::spawn(move || {
        for _ in 0..1000 {
            *total.lock().unwrap() += 1;
        }
    })
}).collect();
for h in handles { h.join().unwrap(); }
println!("{}", *total.lock().unwrap());       // 8000
```

**Answer:**

- `Arc<T>` gives **many owners** across threads (atomic reference count, see
  [Smart Pointers §3](../foundations/rust-smart-pointers.md#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for)).
  `Mutex<T>` gives **one-at-a-time access** to the `T` inside.
- The `Mutex` **owns the data**. You cannot reach the `u64` without calling
  `lock()`, so you cannot forget to lock. This differs from C++ and Java,
  where the lock and the data are separate things.
- `lock()` returns a **guard** (`MutexGuard`). The lock is released when the
  guard is **dropped** (RAII, "Resource Acquisition Is Initialization").
  There is no `unlock()` to forget.
- **Keep the guard short.** `*total.lock().unwrap() += 1;` drops the guard at
  the end of the statement. A guard stored in a `let` lives until the end of
  the block. Use an inner `{ ... }` block or `drop(guard)` to release early.
- `lock()` returns `Result` because of **poisoning** (next question).
- Prefer **message passing** or **no sharing** (give each thread its own
  chunk) when you can. A lock is a point where threads wait for each other.

## 4. "What is lock poisoning?"

```rust
let m = Arc::new(Mutex::new(5));
let m2 = Arc::clone(&m);
let r = thread::spawn(move || {
    let _g = m2.lock().unwrap();
    panic!("boom while holding the lock");
}).join();
// r.is_err() == true, m.is_poisoned() == true
let v = m.lock().unwrap_or_else(|e| e.into_inner());   // recover anyway
```

Output from the sample: `thread panicked: true, poisoned: true`, then
`recovered value: 5`.

**Answer:**

- If a thread **panics while holding a guard**, the data may be half
  updated. The `Mutex` is marked **poisoned**, and later `lock()` calls
  return `Err(PoisonError)`.
- The error still contains the guard. `into_inner()` gives it to you when
  you decide the data is still usable (or can be repaired).
- `.lock().unwrap()` is the usual choice: a poisoned lock means a bug
  elsewhere, so propagating the panic is reasonable.
- `parking_lot::Mutex` (a popular crate) has **no poisoning**. The standard
  library keeps it so a broken invariant is never silently reused.

## 5. "When do you use `RwLock`, `Condvar`, `Barrier`, and `OnceLock`?"

**Answer:**

| Type | Use it for | Notes |
|---|---|---|
| `RwLock<T>` | **Many readers or one writer** | Worth it only if reads dominate and last a while. Otherwise `Mutex` is faster |
| `Condvar` | **Wait until a condition becomes true** | Always used with a `Mutex` and a loop (`wait_while`) |
| `Barrier` | **Wait until N threads arrive** | `wait()` tells exactly one thread it is the "leader" |
| `OnceLock<T>` | **Set once, read many times** | Global config; `get_or_init` is race-free |

```rust
// RwLockWriteGuard::downgrade (stable 1.92): write, then keep reading
let rw = RwLock::new(String::from("v1"));
let mut w = rw.write().unwrap();
w.push_str("-edited");
let r = RwLockWriteGuard::downgrade(w);   // no gap where another writer sneaks in
println!("{}", *r);                        // v1-edited

// Condvar: wait for a flag set by another thread
let pair = Arc::new((Mutex::new(false), Condvar::new()));
let pair2 = Arc::clone(&pair);
thread::spawn(move || {
    *pair2.0.lock().unwrap() = true;
    pair2.1.notify_one();
});
let (lock, cv) = &*pair;
let ready = cv.wait_while(lock.lock().unwrap(), |ready| !*ready).unwrap();
```

- A `Condvar` can wake up **spuriously** (without a notify), and a notify
  sent before the waiter starts waiting is lost. That is why you check the
  **condition under the lock** in a loop. `wait_while` does exactly this.
- `RwLock` can **starve** writers or readers, depending on the operating
  system's implementation. Do not assume a fairness policy.
- `OnceLock` replaces `static mut` for global state. See
  [Smart Pointers §5](../foundations/rust-smart-pointers.md#5-what-are-cow-oncelock-and-lazylock-for).

## 6. "How do channels work, and when do you prefer them?"

```rust
use std::sync::mpsc;

let (tx, rx) = mpsc::channel();
for id in 0..3 {
    let tx = tx.clone();
    thread::spawn(move || tx.send(id * id).unwrap());
}
drop(tx);                                   // the original sender must go too
let mut got: Vec<i32> = rx.iter().collect();
got.sort();                                 // [0, 1, 4]
```

**Answer:**

- `mpsc` means **multiple producer, single consumer**. Clone the `Sender`
  for more producers. There is exactly one `Receiver`.
- The receiver loop ends when **every sender is dropped**. A forgotten
  original `tx` makes `rx.iter()` wait forever. This is the most common
  channel bug.
- `channel()` is **unbounded**: a fast producer can fill memory.
  `sync_channel(n)` is **bounded**: `send` **blocks** when `n` items are
  waiting. This is **backpressure**. The sample shows a producer of four
  items with `sync_channel(1)` being slowed down by the receiver.
- Sending **moves** the value, so the sender can no longer touch it. The
  ownership system gives you "share memory by communicating" for free.
- `std::sync::mpsc` has one consumer and a limited feature set. The
  **`crossbeam-channel`** crate adds multiple consumers and `select!`.
  For async code use Tokio's channels, see
  [Tokio & Async Patterns §4](rust-tokio-and-async-patterns.md#4-which-channel-do-you-use-and-how-do-you-get-backpressure).
- Choose by shape: **channels** for pipelines and work queues, **a mutex**
  for a small shared structure many threads read and update.

## 7. "How do deadlocks happen, and how do you avoid them?"

**Answer:**

- A **deadlock** is a cycle of waiting. Thread 1 holds lock A and waits for B.
  Thread 2 holds B and waits for A. Rust **does not prevent** it, because the
  program is memory safe, just stuck.
- Typical causes:
    - **Inconsistent lock order**. Fix: define one global order (always A
      before B), or merge both values under **one** lock.
    - **Locking twice** on one thread. `Mutex` is **not reentrant**: the second
      `lock()` on the same thread deadlocks or panics (unspecified).
    - **Calling unknown code while holding a lock** (a callback that locks
      again).
    - **Holding a guard across a blocking call** (a channel `recv`, I/O).
- Tools: keep critical sections tiny, never hold two locks if you can avoid
  it, use `try_lock` where a failure is acceptable.
- **Edition 2024 fixed one accidental deadlock.** In older editions, the
  temporary guard in an `if let` scrutinee **lived through the `else` block**.
  The same source, run in both editions:

    ```rust
    let m = Mutex::new(Some(1));
    if let None = *m.lock().unwrap() {
        println!("unreachable");
    } else {
        println!("try_lock ok = {}", m.try_lock().is_ok());
    }
    ```

    | Edition | Output | Meaning |
    |---|---|---|
    | 2021 | `try_lock ok = false` | the guard is still alive in `else`; a real `lock()` would **deadlock** |
    | 2024 | `try_lock ok = true` | the guard is dropped before `else` |

    The wider rule about when temporaries are dropped is in
    [Ownership §4](../foundations/rust-ownership-and-borrowing.md#4-when-exactly-are-values-dropped-and-in-what-order).

## 8. "How do you use all CPU cores for a data-parallel task?"

```rust
use rayon::prelude::*;

let n = 3_000_000u32;
let seq = (0..n).filter(|&x| is_prime(x)).count();
let par = (0..n).into_par_iter().filter(|&x| is_prime(x)).count();
```

Measured (release build, 10 threads): **sequential 219 ms, parallel 41 ms**
for 216,816 primes below 3 million. Same answer, about 5x faster.

**Answer:**

- **`rayon`** is a thread-pool library. Change `.iter()` to `.par_iter()` (or
  `.into_iter()` to `.into_par_iter()`) and the iterator chain from
  [Iterators & Closures](../foundations/rust-iterators-and-closures.md) runs
  on all cores.
- It uses **work stealing**: idle threads take work from busy ones, so uneven
  chunks still balance out.
- The compiler **checks** the closure: it must be `Send + Sync`, so a shared
  `Cell` or an unprotected `&mut` counter does not compile.
- `collect()` **keeps the order** of the input. `sum`, `reduce`, `fold`,
  and `rayon::join` (run two closures in parallel) are the other building
  blocks.
- When **not** to use it: small inputs (splitting costs more than the work),
  tiny closures, or work that is I/O bound (use async, see
  [Tokio & Async Patterns](rust-tokio-and-async-patterns.md)).
- Always **measure in release mode**. A debug build can make parallel code
  look slower.

## 9. "What else should you know: thread-locals, file locks, false sharing?"

**Answer:**

- **Thread-local storage:** `thread_local!` gives each thread its own copy.
  In the sample the main thread's counter is 1 and a new thread sees 0.
  Use `with_borrow` / `with_borrow_mut` on a `RefCell` inside.
- **File locks** (stable 1.89): `File::lock`, `try_lock`, `lock_shared`, and
  `unlock` lock a file for the **whole machine** (between processes). In the
  sample `try_lock` on an already locked file returned false.
- **False sharing** (a performance trap, not a correctness bug): two threads
  update **different** variables that sit in the **same CPU cache line**
  (usually 64 bytes). The cores keep invalidating each other's cache. The fix
  is padding or aligning (`#[repr(align(64))]`), see
  [Memory Layout & DSTs](../advanced-language/rust-memory-layout-and-dsts.md).
- **Atomics** are the lock-free building block under `Mutex` and channels:
  [Atomics & Memory Ordering](rust-atomics-and-memory-ordering.md).
- **Thread count:** a thread costs a stack (2 MiB virtual by default on
  most platforms) and scheduler work. Do not spawn one per request. Use a
  pool (`rayon`, a runtime) or async.

## 10. "How do AI tools help or hurt with concurrent code?"

**Answer:**

- **Good at:** explaining `Send`/`Sync` errors, turning a loop into a
  `par_iter`, and writing the boilerplate `Arc::clone` + `move` pattern.
- **Weak at:** judging **lock granularity** and **ordering**. A generated
  solution often wraps everything in one `Arc<Mutex<_>>`, which compiles and
  may serialize the whole program.
- A common bad suggestion for a `Send` error is `unsafe impl Send`. Treat it
  as a red flag. First ask why the type is not `Send`.
- Ask the tool to **explain the lock order** and what happens on panic
  (poisoning). If it cannot, you cannot trust the code.
- Tests do not prove concurrent code correct. Ask for a `loom` test or a
  stress test, see
  [Atomics & Memory Ordering §7](rust-atomics-and-memory-ordering.md#7-how-do-you-test-lock-free-code-with-loom).
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Basics**

- "What does `thread::spawn` require of its closure, and why?" — expects
  `Send + 'static`, the thread may outlive the caller,
  [§1](#1-how-do-you-start-a-thread-and-what-is-a-scoped-thread).
- "What is a scoped thread and when would you use it?" — expects borrowing
  local data safely, guaranteed join,
  [§1](#1-how-do-you-start-a-thread-and-what-is-a-scoped-thread).
- "What happens to a thread whose `JoinHandle` is dropped?" — expects
  detached, killed at process exit,
  [§1](#1-how-do-you-start-a-thread-and-what-is-a-scoped-thread).

**Send and Sync**

- "Explain `Send` and `Sync`. Give a type that is neither." — expects the
  table, `Rc` / `RefCell`,
  [§2](#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race).
- "Is `&T` `Send`?" — expects only if `T: Sync`,
  [§2](#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race).
- "Does Rust prevent race conditions?" — expects no, only data races,
  [§2](#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race).

**Locks and channels**

- "Why does `lock()` return a `Result`?" — expects poisoning,
  [§4](#4-what-is-lock-poisoning).
- "Why does the `Mutex` own its data?" — expects you cannot forget to lock,
  [§3](#3-how-do-you-share-mutable-state-arcmutext).
- "My `for x in rx` loop never ends. Why?" — expects a live `Sender`,
  [§6](#6-how-do-channels-work-and-when-do-you-prefer-them).
- "Bounded vs unbounded channels?" — expects backpressure,
  [§6](#6-how-do-channels-work-and-when-do-you-prefer-them).
- "Why do you need a loop around `Condvar::wait`?" — expects spurious
  wakeups, [§5](#5-when-do-you-use-rwlock-condvar-barrier-and-oncelock).

**Design**

- "How would you find and fix a deadlock?" — expects lock order, one lock,
  short sections, [§7](#7-how-do-deadlocks-happen-and-how-do-you-avoid-them).
- "How do you parallelize a CPU-heavy iterator chain?" — expects `rayon`,
  and when it does not help,
  [§8](#8-how-do-you-use-all-cpu-cores-for-a-data-parallel-task).
- "Why is `unsafe impl Send` dangerous?" — expects an unchecked promise,
  [§2](#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/threads_sync.rs` — spawn and join, scoped threads, `Arc<Mutex>`,
  poisoning and recovery, `RwLock::downgrade`, `Condvar`, `Barrier`,
  `mpsc` and `sync_channel`, `OnceLock`, `thread_local!`, `try_lock`, and
  `File::lock`.
- `examples/if_let_lock_scope.rs` — the same source compiled in edition 2021
  and 2024 (command in the file header).
- `async_demo/examples/rayon_demo.rs` — sequential vs `rayon` primes,
  ordered `collect`, `rayon::join`.
- `compile_fail/thread_rc_not_send.rs`, `refcell_not_sync.rs`,
  `data_race_counter.rs`, `scoped_two_mut.rs` — real errors quoted above.

```bash
cd code_samples/rust
cargo run --example threads_sync
cargo run --example if_let_lock_scope            # edition 2024 result
rustc --edition 2021 examples/if_let_lock_scope.rs -o /tmp/x && /tmp/x

cd async_demo
cargo run --release --example rayon_demo

cd ..
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/thread_rc_not_send.rs   # must fail
```
