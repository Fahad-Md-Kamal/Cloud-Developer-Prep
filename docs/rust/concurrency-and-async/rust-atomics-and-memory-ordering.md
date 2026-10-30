---
title: Atomics & Memory Ordering in Rust
---

# Atomics & Memory Ordering in Rust

An **atomic** is a value that the CPU (Central Processing Unit) can read or
change in **one indivisible step**, so no other thread ever sees it half
updated. Atomics are the lock-free building block under `Mutex`, channels,
and `Arc`. Their hard part is not the operation itself but the
**memory ordering**: a rule that says which **other** memory writes become
visible to other threads, and when. This page builds the idea from the
ground up, then implements a handoff and a spinlock, and checks them with
`loom`.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Every example ran on
    1.99.1. `loom` 0.7.2 was used for the model-checking examples.
    `update` and `try_update` on the atomic integer types are stable since
    **1.95**, and `AtomicU32::from_mut` and friends since **1.98**. The
    generic `Atomic<T>` type is **still unstable** (see §6).

## 1. "Why do atomics exist, when we have `Mutex`?"

**Answer:**

- A plain `counter += 1` is **three steps**: read, add, write. Two threads can
  both read 5 and both write 6, so one update is lost. In Rust, sharing a
  plain integer like that does not compile (see
  [Threads & Synchronization §2](rust-threads-and-synchronization.md#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race)).
- `AtomicUsize::fetch_add` does the whole read-add-write as **one step**.
  Four threads adding 100,000 times each gave exactly `400000` in the sample.
- Atomics are **cheaper** than a lock for one small value (no sleeping, no
  kernel call), and they can never be **poisoned** or **deadlock** by
  themselves.
- They are also **harder**: one atomic is easy, but correctness across
  **two or more** variables needs the ordering rules below.
- Use them for: counters and statistics, flags (`stop`, `ready`), reference
  counts, and building synchronization types. Use a `Mutex` for everything
  else (§8).

## 2. "What are `Relaxed`, `Acquire`, `Release`, `AcqRel`, and `SeqCst`?"

**Answer:**

- **Why ordering exists.** Both the **compiler** and the **CPU** may
  **reorder** memory operations for speed, and every core has its own caches.
  Within one thread, the result looks as if nothing was reordered. **Between
  threads**, another thread can observe the writes in a **different order**.
  The `Ordering` argument tells the compiler and the CPU how much to hold
  back.
- The key idea is **happens-before**: if event A *happens before* event B,
  then everything A did is visible to B. Atomics create that relation only
  where you ask for it.

| Ordering | Plain-language meaning | Typical use |
|---|---|---|
| `Relaxed` | The operation is atomic. **No ordering** with other memory | Counters, statistics |
| `Release` (stores) | Everything I wrote **before** this store is visible to whoever **reads** it with `Acquire` | Publish data, unlock |
| `Acquire` (loads) | After this load sees a `Release` store, I see everything written before that store | Consume data, lock |
| `AcqRel` | Both, for operations that read and write (`fetch_add`, CAS) | Reference counts, handoff |
| `SeqCst` | `AcqRel` plus **one single global order** of all `SeqCst` operations | When unsure; simple reasoning |

- A **Release store paired with an Acquire load of the same atomic** forms a
  **synchronizes-with** edge. That edge is the only thing that makes the
  earlier plain writes visible. Using `Relaxed` on either side removes it.
- `SeqCst` is **the safe default**. It costs a little on some CPUs (more on
  weakly ordered ones such as ARM than on x86). Start with it and weaken
  only with a reason and a test.
- Not every ordering is allowed everywhere: a **load** cannot be `Release`,
  and a **store** cannot be `Acquire`. This is checked at run time (a panic),
  not by the compiler.
- The model is the same as C++20's. The official reference is the
  documentation of `std::sync::atomic`. The free book *Rust Atomics and Locks*
  (Mara Bos) explains it in depth.

## 3. "How do you hand data from one thread to another with a flag?"

```rust
static DATA: AtomicU64 = AtomicU64::new(0);
static READY: AtomicBool = AtomicBool::new(false);

let reader = thread::spawn(|| {
    while !READY.load(Ordering::Acquire) {
        hint::spin_loop();
    }
    DATA.load(Ordering::Relaxed)             // guaranteed to see 42
});
DATA.store(42, Ordering::Relaxed);
READY.store(true, Ordering::Release);        // publishes the DATA write
```

Sample output: `reader saw data = 42`.

**Answer:**

- The writer stores the data, then **releases** the flag. The reader
  **acquires** the flag. Because the reader saw `READY == true` from a
  `Release` store, it also sees the `DATA` write that happened before it.
- `DATA` itself can be `Relaxed`. The flag does the ordering for it.
- `hint::spin_loop()` tells the CPU "I am busy waiting" (it lowers power and
  helps a hyper-thread sibling). A real program should usually **block**
  (channel, `Condvar`, or `thread::park`) instead of spinning.
- **What breaks with `Relaxed` on the flag?** The reader may see
  `READY == true` and still read the **old** `DATA` (0). On x86 this is hard
  to trigger because the hardware is strong, and on ARM it can really
  happen. Testing on one machine proves nothing. `loom` (§7) proves it.

## 4. "How does `compare_exchange` work, and what are `update` and `try_update`?"

```rust
// compare_exchange(expected, new, success_order, failure_order)
let c = AtomicUsize::new(1);
c.compare_exchange(1, 2, SeqCst, SeqCst);   // Ok(1)   value was 1, now 2
c.compare_exchange(1, 3, SeqCst, SeqCst);   // Err(2)  value was 2, nothing changed

// a hand-written CAS loop: set the value to a new maximum
let mut cur = max.load(Relaxed);
while cur < new {
    match max.compare_exchange_weak(cur, new, Relaxed, Relaxed) {
        Ok(_) => break,
        Err(actual) => cur = actual,       // someone else changed it: retry with the fresh value
    }
}

// Rust 1.95: the same pattern as one method
let prev = a.update(SeqCst, SeqCst, |x| x * 2);                      // always applies, returns previous
let r = a.try_update(SeqCst, SeqCst, |x| (x < 5).then_some(0));      // Err(10): closure said None
let r = a.try_update(SeqCst, SeqCst, |x| (x > 5).then_some(x + 1));  // Ok(10): applied, now 11
```

**Answer:**

- **Compare-and-swap (CAS)** says: "set the value to `new`, **only if** it
  still equals `expected`." The result is `Ok(previous)` on success and
  `Err(actual)` on failure. It is the basis of almost every lock-free
  algorithm: read, compute, try to publish, retry if someone beat you.
- It takes **two orderings**: one for the success case (a read-modify-write)
  and one for the failure case (just a load, so it cannot be `Release`).
- **`compare_exchange` vs `compare_exchange_weak`:**
    - The weak version may **fail spuriously** (return `Err` even though the
      value matched). It is cheaper on some CPUs (ARM).
    - Use **weak inside a loop** (you retry anyway) and **strong** when a
      single attempt must be reliable.
- **`update` and `try_update`** (stable 1.95 on the integer types, `AtomicBool`
  and `AtomicPtr`) wrap the retry loop:
    - `update` applies a function and **always** succeeds. It returns the
      **previous** value (`5` before doubling to `10`).
    - `try_update` lets the closure return `None` to **refuse**. It returns
      `Ok(previous)` or `Err(current)`.
- **`fetch_update` is deprecated.** On 1.99.1 the compiler says:
  "use of deprecated method ... renamed to `try_update` for consistency".
  Existing code and tutorials use the old name. Switch to `try_update`.
- **`fetch_max`, `fetch_min`, `fetch_and`, `fetch_or`, `swap`** cover the
  common cases without a loop. Use them first.

## 5. "How do you build a spinlock, and why is it usually a bad idea?"

```rust
struct SpinLock { locked: AtomicBool }

impl SpinLock {
    const fn new() -> Self { Self { locked: AtomicBool::new(false) } }
    fn lock(&self) {
        while self.locked
            .compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed)
            .is_err()
        {
            hint::spin_loop();
        }
    }
    fn unlock(&self) { self.locked.store(false, Ordering::Release); }
}
```

Sample: four threads each add 50,000 times to a plain `u64` under this lock
and get exactly `200000`.

**Answer:**

- **Acquire on lock, Release on unlock** is the whole trick. Everything one
  thread wrote **inside** the lock is visible to the next thread that takes
  the lock. This pair is exactly what `Mutex` uses.
- The sample needs `unsafe` for the plain write, because the type does not
  hand out a guard. A real design returns a guard that unlocks on `Drop`.
- **Why not use it in production:**
    - A waiting thread **burns a whole core**.
    - If the lock holder is **descheduled** by the operating system, everyone
      else spins for a full time slice.
    - It has no fairness and no poisoning.
- `std::sync::Mutex` spins briefly, then **sleeps** the thread (using the
  operating system's futex or equivalent). That is the right trade for
  almost every program.
- A spinlock is correct only for very short critical sections, or where you
  cannot sleep (interrupt handlers in `no_std` code, see
  [no_std & Embedded Rust](../performance-and-internals/rust-no-std-and-embedded.md)).

## 6. "What is the ABA problem, and what else is new in the atomics API?"

**Answer:**

- **ABA:** a CAS loop reads value **A**, gets interrupted, and meanwhile other
  threads change it to **B** and back to **A**. The CAS succeeds because the
  value **looks** unchanged, but the **world** changed. In a lock-free
  stack, A may be a pointer to a node that was freed and reused, so the
  structure gets corrupted.
- Fixes:
    - Add a **version counter** next to the value (a "tagged pointer"), so
      A-then-B-then-A becomes A1, B2, A3.
    - Use **safe memory reclamation** so a node is never freed while another
      thread may still look at it (epoch-based reclamation in
      `crossbeam-epoch`, or hazard pointers).
    - Avoid the problem: use a `Mutex` or a proven crate.
- `AtomicPtr` got more methods in **1.91**: `fetch_ptr_add`, `fetch_ptr_sub`,
  `fetch_byte_add`, `fetch_byte_sub`, `fetch_or`, `fetch_and`, `fetch_xor`.
  They are the building blocks for tagged pointers.
- **`from_mut`** (1.98 on the concrete types) views a plain `&mut u32` as an
  `&AtomicU32` when you hold exclusive access. The sample prints `6` after
  an atomic `fetch_add` through the view.
- **The generic `Atomic<T>` is not stable.** Trying `use
  std::sync::atomic::Atomic;` on 1.99.1 fails:

    ```text
    error[E0658]: use of unstable library feature `generic_atomic`
     --> compile_fail/generic_atomic_unstable.rs:1:25
      |
    1 | use std::sync::atomic::{Atomic, Ordering};
      |                         ^^^^^^
      |
      = note: see issue #130539 <https://github.com/rust-lang/rust/issues/130539> for more information
    ```

  Keep using `AtomicU32`, `AtomicU64`, and so on. (The release notes list
  `Atomic<T>::from_mut` because the documentation lives on the generic type.)
- `AtomicU64` is 8 bytes with 8-byte alignment (printed by the sample). On
  some 32-bit targets 64-bit atomics do not exist or need locks, so check
  `cfg(target_has_atomic = "64")` for portable code.

## 7. "How do you test lock-free code with `loom`?"

```rust
// src/lib.rs (excerpt): the type under test takes the orderings as parameters
#[cfg(loom)]
use loom::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
#[cfg(not(loom))]
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

// test: loom runs the closure under EVERY allowed interleaving and reordering
loom::model(move || {
    let h = Arc::new(Handoff::new());
    let h2 = Arc::clone(&h);
    let t = thread::spawn(move || h2.publish(42, publish));
    if let Some(v) = h.try_read(read) {
        assert_eq!(v, 42, "saw ready=true but stale data");
    }
    t.join().unwrap();
});
```

Run with `RUSTFLAGS="--cfg loom" cargo test --release --lib loom_tests`.
Real result:

| Orderings used | Result |
|---|---|
| `Release` store, `Acquire` load | all interleavings pass |
| `Relaxed`, `Relaxed` | loom **finds the bug**: `assertion left == right failed: saw ready=true but stale data`, `left: 0, right: 42` |

**Answer:**

- **`loom`** is a **model checker**. It replaces `std`'s atomics, `Mutex`,
  and threads with its own versions, then runs your test again and again,
  exploring the **possible** schedules and memory reorderings instead of
  hoping to hit one.
- That is the difference from a normal stress test: a stress test on an x86
  laptop may pass a million times with `Relaxed`, because the hardware is
  strong. Loom reports the bug in a single run.
- Practical rules:
    - Hide the `std` vs `loom` import behind `cfg(loom)`, as above.
    - Keep the **model small** (two or three threads, a few operations). The
      number of schedules grows very fast.
    - Run it in release mode and in CI as a separate job.
- Other tools: **Miri** (checks for undefined behaviour and, with its
  weak-memory emulation, some ordering bugs, see
  [Unsafe Rust & Miri](../advanced-language/rust-unsafe-and-miri.md)), and
  **ThreadSanitizer** (finds real data races at run time on nightly).

## 8. "When should you use atomics, and when a `Mutex`?"

**Answer:**

- **Default: use a `Mutex`** (or a channel). It is correct, readable, and
  fast enough in nearly every program.
- Reach for **atomics** when:
    - the shared state is **one word** (counter, flag, id generator),
    - you measured a lock as the bottleneck,
    - you are writing the **synchronization primitive** itself.
- A lock-free data structure is **not automatically faster**. Under heavy
  contention, CAS loops waste work and bounce cache lines between cores. A
  well-made `Mutex` can win.
- **Do not write your own lock-free queue for production.** Use
  `crossbeam` or the standard channels. Writing one is a great exercise: see
  the capstone list in [Capstone Projects](../mastery/rust-capstone-projects.md).
- Rules of thumb:
    - If you cannot say which `Release` pairs with which `Acquire`, use
      `SeqCst`.
    - If two atomics must change **together**, they need a lock (or be packed
      into one atomic).

## 9. "How do AI tools help or hurt with atomics?"

**Answer:**

- **Weak spot:** they write `Ordering::Relaxed` or `Ordering::SeqCst` by
  habit, and **cannot tell you whether it is correct**. Confident text about
  "happens-before" is often wrong in the details.
- **Good use:** ask for the **property** ("what must be visible to the
  reader after it sees the flag?"), then write a `loom` test yourself and run
  it. The test decides, not the explanation.
- Ask for the **weakest correct ordering** and a **justification per
  operation**. Reject answers without a "this Release pairs with that
  Acquire" statement.
- Never accept a hand-rolled lock-free structure from an AI tool without a
  model check and a review by a human who knows the memory model.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Concepts**

- "Why is `counter += 1` unsafe across threads but `fetch_add` is fine?" —
  expects three steps vs one indivisible step,
  [§1](#1-why-do-atomics-exist-when-we-have-mutex).
- "Explain `Acquire` and `Release` in plain words." — expects publish and
  consume with a synchronizes-with edge,
  [§2](#2-what-are-relaxed-acquire-release-acqrel-and-seqcst).
- "When is `Relaxed` enough?" — expects counters with no other data to
  publish, [§2](#2-what-are-relaxed-acquire-release-acqrel-and-seqcst).
- "Does `Relaxed` on a flag work on your x86 laptop?" — expects it may pass
  there and fail on ARM, [§3](#3-how-do-you-hand-data-from-one-thread-to-another-with-a-flag).

**Compare-and-swap**

- "What is a CAS loop?" — expects read, compute, try, retry,
  [§4](#4-how-does-compare_exchange-work-and-what-are-update-and-try_update).
- "`compare_exchange` vs `compare_exchange_weak`?" — expects spurious
  failure, use weak in loops,
  [§4](#4-how-does-compare_exchange-work-and-what-are-update-and-try_update).
- "What is the ABA problem and how do you fix it?" — expects version tag or
  safe reclamation,
  [§6](#6-what-is-the-aba-problem-and-what-else-is-new-in-the-atomics-api).

**Building and testing**

- "Write a spinlock. Which orderings and why?" — expects Acquire on lock,
  Release on unlock, [§5](#5-how-do-you-build-a-spinlock-and-why-is-it-usually-a-bad-idea).
- "How do you test a lock-free structure?" — expects `loom` model checking,
  [§7](#7-how-do-you-test-lock-free-code-with-loom).
- "Is lock-free always faster than a mutex?" — expects no, contention and
  complexity, [§8](#8-when-should-you-use-atomics-and-when-a-mutex).

---

## Code Samples

All files were run on Rust 1.99.1.

- `code_samples/rust/examples/atomics.rs` — relaxed counter, Release/Acquire
  handoff, spinlock, CAS-loop maximum, `update` and `try_update`,
  `compare_exchange` results, `AtomicPtr`, `from_mut`, sizes.
- `code_samples/rust/compile_fail/generic_atomic_unstable.rs` — the
  `generic_atomic` error quoted above.
- `code_samples/rust/async_demo/src/lib.rs` — the `Handoff` type with a
  normal test and two `loom` tests (correct and buggy).

```bash
cd code_samples/rust
cargo run --release --example atomics

cd async_demo
cargo test                                                   # normal test
RUSTFLAGS="--cfg loom" cargo test --release --lib loom_tests # loom model
```
