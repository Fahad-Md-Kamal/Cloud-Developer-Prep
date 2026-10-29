---
title: Rust Iterators & Closures
---

# Rust Iterators & Closures

An **iterator** produces a sequence of values one at a time. A
**closure** is a small function you can write inline that can use the
variables around it. Together they replace most hand-written loops with
short, readable chains such as `items.iter().filter(...).map(...).sum()`.
The remarkable part is the cost: the compiler turns these chains into the
same machine code as a hand-written loop. This is **zero-cost abstraction**:
you do not pay for the convenience.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Async closures
    (stable since 1.85) and `core::iter::chain` (stable since 1.91) are
    mentioned. Examples ran on 1.99.1.

## 1. "What is an iterator, and why is it lazy?"

```rust
trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
    // ... about 70 provided methods built on `next`
}
```

**Answer:**

- The whole `Iterator` trait is **one required method**, `next`. It returns
  `Some(item)` until the sequence ends, then `None`. Everything else
  (`map`, `filter`, `sum`, `collect`, `zip`, ...) is a **provided method**
  built on it.
- Iterators are **lazy**: `iter.map(f)` does **no work**. It returns a new
  iterator that **would** apply `f`. Work happens only when something
  **consumes** the iterator (`collect`, `sum`, `for`, `count`, `last`).
  The sample proves it: the iterator is built, nothing prints, and then
  `take(2).collect()` maps exactly **two** items.
- Two kinds of method:

| Kind | Examples | Result |
|---|---|---|
| **Adapters** (lazy) | `map`, `filter`, `take`, `skip`, `zip`, `enumerate`, `rev`, `chain`, `flat_map`, `peekable`, `step_by`, `scan` | Another iterator |
| **Consumers** (run the chain) | `collect`, `sum`, `product`, `fold`, `count`, `min`, `max`, `any`, `all`, `find`, `position`, `for_each` | A final value |

- A `for x in thing` loop calls `IntoIterator::into_iter(thing)` and then
  `next()` until `None`. A `for` loop **is** an iterator consumer.
- Because chains are lazy and fused, there is **no intermediate `Vec`**
  between `filter` and `map`. Each element flows through the whole chain
  before the next one starts.
- **Short-circuiting** consumers (`any`, `all`, `find`, `take_while`) stop
  early, even on an **infinite** iterator: `(1u64..).map(|x| x * x)
  .find(|sq| *sq > 200)` finishes with `Some(225)`.

## 2. "How do you get an iterator from a collection?"

**Answer:**

- Three methods, matching the ownership rules in
  [Ownership & Borrowing](rust-ownership-and-borrowing.md):

| Call | Item type | Collection afterwards |
|---|---|---|
| `.iter()` | `&T` | untouched |
| `.iter_mut()` | `&mut T` | untouched, items may change |
| `.into_iter()` | `T` | consumed |

- `for x in &v` uses `iter()`, `for x in &mut v` uses `iter_mut()`, and
  `for x in v` uses `into_iter()`.
- **Ranges** (`0..10`, `1..=5`) are iterators. **Strings** give `chars()`,
  `bytes()`, `lines()`, `split_whitespace()`, `char_indices()`. **Slices**
  give `windows(n)`, `chunks(n)`, and `chunks_exact(n)`.
- Rust 1.96 and 1.95 stabilized new range types in `core::range`
  (`Range`, `RangeInclusive`, `RangeFrom`, ...), which, unlike the older
  ones, are `Copy` and are **not themselves iterators** (call
  `.into_iter()`). The older `std::ops::Range` types you use today still
  work.

## 3. "How do you build a collection from an iterator?"

**Answer:**

- **`collect()`** turns an iterator into a collection, and **the type you
  ask for decides what you get**:

    ```rust
    let v: Vec<i32> = it.collect();
    let s: String = chars.collect();
    let m: HashMap<_, _> = pairs.collect();
    let r: Result<Vec<i32>, _> = strings.iter().map(|s| s.parse()).collect();
    ```

- Use the **turbofish** when there is no variable to annotate:
  `.collect::<Vec<_>>()`. The `_` lets the compiler infer the item type.
- Collecting `Result<T, E>` or `Option<T>` items into `Result<Vec<T>, E>`
  **stops at the first failure**. See
  [Error Handling §3](rust-error-handling.md#3-which-methods-on-result-and-option-should-you-know).
- Other ways to finish: `partition` (split into two collections),
  `unzip`, `sum::<T>()`, `product`, `fold(init, f)`, `reduce(f)`, and
  `collect_into`-style `extend`.
- `fold` is the general tool. `sum` and `count` are `fold` with fixed
  behaviour. `scan` is `fold` that **emits every intermediate state**
  (running totals).
- **Peekable** adds one-item lookahead (`peek`, `next_if`), which is how
  hand-written **parsers** read tokens.
- **Generators of your own**: `std::iter::from_fn(|| ...)` builds an
  iterator from a closure, `std::iter::successors(first, |x| next)` from a
  rule, and `repeat`, `repeat_n`, `once`, `empty` for simple cases.

## 4. "How do you write your own iterator?"

```rust
struct Countdown(u32);

impl Iterator for Countdown {
    type Item = u32;
    fn next(&mut self) -> Option<u32> {
        if self.0 == 0 { None } else { self.0 -= 1; Some(self.0 + 1) }
    }
}
```

**Answer:**

- Implement **one method**, `next`, and you **inherit every adapter**:
  `Countdown(4).zip(...)`, `.filter(...)`, `.sum::<u32>()` all work.
- To make your **collection** usable in a `for` loop, implement
  `IntoIterator`. Do it **three times** for the usual ergonomics: for
  `MyColl` (by value), `&MyColl` (items are `&T`), and `&mut MyColl`
  (items are `&mut T`). The sample implements the `&` form with
  `type IntoIter = std::slice::Iter<'a, String>`.
- A function can **return** an iterator without naming its type:

    ```rust
    fn evens_squared(v: &[i32]) -> impl Iterator<Item = i32> + '_ {
        v.iter().filter(|x| **x % 2 == 0).map(|x| x * x)
    }
    ```

  The return type is a **specific**, unnameable type (a `Map<Filter<...>>`).
  Edition 2024 captures lifetimes automatically here. See
  [Lifetimes §8](rust-lifetimes.md#8-how-do-lifetimes-interact-with-impl-trait-and-what-changed-in-2024).
- To store **different** iterators in one variable, use
  `Box<dyn Iterator<Item = T>>`. It costs one allocation and a virtual
  call per item.
- **Marker traits** make iterators smarter: `ExactSizeIterator` (knows its
  length), `DoubleEndedIterator` (supports `rev`), `FusedIterator`
  (stays `None` after the first `None`). Implement them when true.
- `size_hint()` lets `collect` preallocate. A good `size_hint` is a free
  performance win for custom iterators.

## 5. "Why is this zero-cost, and when is it not?"

**Answer:**

- Each adapter is a **struct** with a generic parameter for the inner
  iterator and the closure. `v.iter().filter(f).map(g)` has the type
  `Map<Filter<slice::Iter<i32>, F>, G>`. Since the closure types are
  **known at compile time**, the compiler **inlines** everything, removes
  the `Option` wrapping of `next`, and usually **vectorizes** the loop with
  SIMD (Single Instruction, Multiple Data) instructions.
- The result is the same as, or often **better than**, a hand-written loop,
  because iterators skip **bounds checks** that indexing would do (the
  iterator already knows it is in range).
- Not free when:
    - You **box** the iterator (`Box<dyn Iterator>`).
    - You **collect** into a `Vec` in the middle of a chain without a reason.
      One `collect` at the end is the usual shape.
    - A closure does **real work** (allocates, locks). The abstraction is
      free, the work is not.
- **Debug builds** are slow with iterator chains, because inlining is off at
  `opt-level = 0`. Measure with `--release`. See
  [Toolchain & Cargo §4](rust-toolchain-and-cargo.md#4-what-are-profiles-and-what-do-dev-and-release-really-change).
- Rule: **write the clear iterator chain first**. Rewrite as a loop only if a
  profile shows a problem, and only for that spot.

## 6. "What is a closure, and how does it capture variables?"

```rust
let mut count = 0;
let mut bump = || count += 1;   // borrows `count` mutably
bump();
bump();
println!("{count}");            // 2
```

**Answer:**

- A closure is an **anonymous function** that can **capture** variables from
  its surroundings: `|x| x + n`. Each closure has its **own unique
  compiler-generated type**, which is why you cannot write that type by
  hand.
- A closure captures each variable in the **least powerful way** it needs:

| It only... | Captures by | Implements |
|---|---|---|
| reads the variable | shared reference `&` | `Fn` |
| changes the variable | mutable reference `&mut` | `FnMut` (and `FnOnce`) |
| moves the variable out (consumes it) | value (move) | `FnOnce` only |

- The three traits form a hierarchy: every `Fn` is also `FnMut`, and every
  `FnMut` is also `FnOnce`. A function that takes `impl FnOnce` accepts
  **any** closure. One that takes `impl Fn` is the **most demanding**
  (the closure must be callable many times without changing anything).
- A `move` keyword **forces capture by value**, even when a reference would
  do. You need it when a closure must **outlive** the current function
  (thread spawn, returning a closure):

    ```rust
    fn make_adder(n: i32) -> impl Fn(i32) -> i32 { move |x| x + n }
    ```

- **Disjoint capture** (edition 2021 and later): a closure captures only the
  **fields** it uses, not the whole struct. In the sample, `read_a`
  borrows only `s.a`, so `s.b.push('!')` is allowed while it is alive.
- `Copy` data is copied into a `move` closure. A `String` is **moved** and
  is no longer usable outside.
- **Non-capturing closures** coerce to plain function pointers (`fn(i32) ->
  i32`). Function names also work wherever a closure is expected:
  `.map(String::from)`, `.filter(Option::is_some)`.

## 7. "How do you pass and return closures?"

**Answer:**

| Need | Write |
|---|---|
| Accept a closure (the common case) | `fn run<F: Fn(i32) -> i32>(f: F)` or `fn run(f: impl Fn(i32) -> i32)` |
| Call it once, may consume captures | `F: FnOnce() -> T` |
| Call it many times, may mutate | `F: FnMut(...)` |
| Return one closure | `fn make() -> impl Fn(i32) -> i32` |
| Return **one of several** closures | `fn make(kind: &str) -> Box<dyn Fn(i32) -> i32>` |
| Store several different closures | `Vec<Box<dyn Fn(i32) -> i32>>` |
| Store one closure in a struct | a generic parameter: `struct Button<F: Fn()> { on_click: F }` |
| Share across threads | `Arc<dyn Fn(i32) -> i32 + Send + Sync>` |

- **Static (generic) beats `Box<dyn Fn>`** when you can: it inlines. Use the
  box when you need **different closures in one place**, as in the sample's
  operations list.
- **Async closures** (`async |x| ...`, stable since Rust 1.85) return a
  future that **can borrow from the closure's own captures**, which a plain
  `|x| async move { ... }` cannot do. They use `AsyncFn`, `AsyncFnMut`, and
  `AsyncFnOnce`. See
  [Async Internals](../concurrency-and-async/rust-async-internals.md).
- **Recursion** with closures is awkward (a closure cannot name itself). Use
  a nested `fn`, or pass the closure itself as an argument.

## 8. "What are common mistakes with iterators and closures?"

**Answer:**

- **Collecting just to loop again**: `let v: Vec<_> = it.collect(); for x in v`.
  Loop over the iterator directly.
- **Using `.iter().map(...)` and never consuming it**. The compiler warns:
  "iterators are lazy and do nothing unless consumed".
- **`for_each` with side effects** instead of a `for` loop. A `for` loop is
  clearer, and you can `break`, `continue`, and `return` from it. `for_each`
  cannot.
- **`.clone()` inside `map`** to avoid a borrow problem. Check whether
  `.cloned()` or `.copied()` on the iterator is what you meant.
- **Index loops** (`for i in 0..v.len()`) when iterating by reference
  works. They add bounds checks and invite off-by-one errors.
- **Holding a `RefCell` borrow or a lock guard** inside a closure that runs
  lazily, then being surprised by when it runs. Lazy means "later".
- **Boxing too early**: `Box<dyn Fn>` where a generic would do.
- **Capturing too much**: a `move` closure that moves a large value when a
  reference would do. Clone just what you need first (`let name =
  name.clone(); move || ...`).

## 9. "How do AI tools help or hurt here?"

**Answer:**

- Good for: turning loops into chains, picking the right adapter, and
  explaining a long iterator type in an error.
- They often write **unreadable mega-chains**, collect too early, or use
  `fold` where `sum` or `max_by_key` exists. Ask for the **simplest** form
  that reads like the requirement.
- They may use `.unwrap()` inside closures. Ask for `?`-friendly code with
  `try_fold` or `collect::<Result<...>>`.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Iterators**

- "What is the `Iterator` trait, and which method must you implement?" —
  expects `next`, with everything else provided,
  [§1](#1-what-is-an-iterator-and-why-is-it-lazy).
- "Why do iterators do nothing until consumed? Give an example." —
  expects laziness and adapters vs consumers,
  [§1](#1-what-is-an-iterator-and-why-is-it-lazy).
- "`iter`, `iter_mut`, `into_iter`: what are the item types?" — expects
  `&T`, `&mut T`, `T`,
  [§2](#2-how-do-you-get-an-iterator-from-a-collection).
- "How does `collect` know what to build?" — expects the target type
  annotation or turbofish, including `Result<Vec<_>, _>`,
  [§3](#3-how-do-you-build-a-collection-from-an-iterator).
- "Why are iterator chains as fast as loops?" — expects monomorphization,
  inlining, and removed bounds checks,
  [§5](#5-why-is-this-zero-cost-and-when-is-it-not).
- "How do you return an iterator from a function?" — expects `impl
  Iterator`, or `Box<dyn Iterator>` for several types,
  [§4](#4-how-do-you-write-your-own-iterator).

**Closures**

- "`Fn` vs `FnMut` vs `FnOnce`?" — expects the capture table and the
  hierarchy,
  [§6](#6-what-is-a-closure-and-how-does-it-capture-variables).
- "When do you need `move`?" — expects a closure that outlives its scope,
  such as a thread or a returned closure,
  [§6](#6-what-is-a-closure-and-how-does-it-capture-variables).
- "How do you store closures of different types in a `Vec`?" — expects
  `Vec<Box<dyn Fn(...)>>`,
  [§7](#7-how-do-you-pass-and-return-closures).
- "What is new with async closures?" — expects `AsyncFn*` and borrowing
  from captures,
  [§7](#7-how-do-you-pass-and-return-closures).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/iterators_closures.rs` — laziness (with printed proof), common
  adapters and consumers, `collect` targets, `peekable`, `from_fn`,
  `successors`, a custom iterator, `IntoIterator for &T`, `Fn`/`FnMut`/
  `FnOnce`, returning closures, `Box<dyn Fn>`, and disjoint capture.

```bash
cd code_samples/rust
cargo run --example iterators_closures
```
