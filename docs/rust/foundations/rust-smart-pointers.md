---
title: Rust Smart Pointers & Interior Mutability
---

# Rust Smart Pointers & Interior Mutability

A plain reference (`&T`) only **borrows**. Sometimes you need more:
a value on the **heap** with one owner (`Box`), a value with **several
owners** (`Rc`, `Arc`), or the ability to **mutate through a shared
reference** (`Cell`, `RefCell`, `Mutex`). These are **smart pointers**:
types that act like pointers but add ownership rules or extra behaviour.
They are also where the borrow checker's rules move from **compile time to
run time**, so knowing exactly what each one costs and when it can panic is
essential.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. `LazyLock` and
    `OnceLock` (stable since 1.80 and 1.70) are used instead of
    `static mut`. Examples ran on 1.99.1.

## 1. "What makes a type a smart pointer?"

**Answer:**

- A smart pointer usually **owns** what it points to, and implements two
  traits:
    - **`Deref`** (and `DerefMut`): `*p` and method calls reach the inner
      value.
    - **`Drop`**: cleanup when the pointer goes away (free memory, decrement
      a counter, release a lock).
- **Deref coercion** is the compiler's automatic conversion chain. A
  `&MyBox<String>` is accepted where `&str` is expected, because it applies
  `Deref` repeatedly: `&MyBox<String>` to `&String` to `&str`. This is why
  you can pass `&string` to a function that takes `&str`.
- `String` and `Vec<T>` are smart pointers too: they own heap data and
  dereference to `str` and `[T]`.
- The ones to know:

| Type | Owners | Mutation | Thread-safe | Checked |
|---|---|---|---|---|
| `Box<T>` | one | via `&mut` | if `T` is | compile time |
| `Rc<T>` | many | none (read-only) | **no** | compile time |
| `Arc<T>` | many | none (read-only) | **yes** | compile time |
| `Cell<T>` | one | replace whole value | no | none needed |
| `RefCell<T>` | one | borrow rules | no | **run time** (panics) |
| `Mutex<T>` / `RwLock<T>` | one value, many handles | exclusive access | **yes** | run time (blocks) |
| `Cow<'a, T>` | borrowed or owned | clone on write | if `T` is | compile time |

## 2. "When do you use `Box<T>`?"

```rust
enum List {
    Cons(i32, Box<List>),
    Nil,
}
```

**Answer:**

- `Box<T>` puts a `T` on the **heap** and gives you **one owner**. The box
  itself is **one pointer** (8 bytes on 64-bit), and the `T` is freed when
  the box is dropped.
- Three real uses:
    1. **Recursive types.** A `List` that contains a `List` would have
       **infinite size**. A `Box<List>` has a **fixed size** (one pointer),
       so the compiler can lay it out. This is also how trees are built.
    2. **Trait objects**: `Box<dyn Trait>`. See
       [Traits & Generics §2](rust-traits-and-generics.md#2-what-is-the-difference-between-generics-and-dyn-trait).
    3. **Moving large values cheaply.** Moving a `Box` copies 8 bytes, not
       the whole value. Also useful to keep a rarely used large enum
       variant from making every value big.
- Do **not** box just to "avoid copies" of small values, or to feel
  safe. A plain value on the stack is faster, and the compiler already
  moves instead of copying.
- **`Box::leak`** gives you a `&'static mut T` by never freeing the memory.
  It is valid for data that lives for the whole program, such as a
  configuration loaded at startup.
- `Option<Box<T>>` is the **same size** as `Box<T>` (the null pointer is
  the `None`): the niche optimization. The sample prints `size_of
  Box<List> = 8`.

## 3. "When do you use `Rc` and `Arc`, and what are `Weak` pointers for?"

**Answer:**

- **`Rc<T>`** (reference counted) lets **several owners** share one value.
  `Rc::clone(&a)` does **not** copy the data. It increments a **counter**.
  When the last `Rc` is dropped, the count reaches zero and the value is
  freed. The count is not atomic, so `Rc` is **not `Send`**: the compiler
  forbids moving it to another thread.
- **`Arc<T>`** (atomically reference counted) is the same, but the counter
  uses **atomic** instructions, so it is safe to share across threads. The
  cost is a little more per clone and drop. Use `Rc` in single-threaded
  code and `Arc` as soon as threads or async tasks are involved.
- Both give **shared, read-only** access. To **change** shared data you
  combine them with interior mutability: `Rc<RefCell<T>>` on one thread,
  `Arc<Mutex<T>>` or `Arc<RwLock<T>>` across threads.
- **Reference cycles leak.** If `A` holds an `Rc` to `B` and `B` holds an
  `Rc` back to `A`, neither count reaches zero. This is safe (no crash) but
  the memory is never freed.
- **`Weak<T>`** is a **non-owning** pointer to an `Rc` or `Arc` value. It
  does not keep the value alive. `weak.upgrade()` returns `Some(Rc<T>)` if
  the value still exists, and `None` if it is gone. Use it for **back
  references** (a child pointing to its parent).
- The sample builds a tree: `branch` owns `leaf` through `Rc`, and `leaf`
  points back with `Weak`. The output shows counts (`branch strong=1
  weak=1`, `leaf strong=2 weak=0`), and after `branch` is dropped, the
  `upgrade()` returns `None`.
- Useful associated functions:
    - `Rc::strong_count(&a)` and `Rc::weak_count(&a)` for debugging.
    - `Rc::ptr_eq(&a, &b)` — are these the same allocation?
    - `Rc::try_unwrap(rc)` — get the value back **if you are the only
      owner**.
    - **`Rc::make_mut(&mut rc)`** — **copy on write**. If shared, it
      clones the inner value first, then gives you `&mut`. The sample shows
      `a` and `b` separating after the push.
- Prefer a design **without shared ownership** when you can. Pass
  references, move the value, or store items in a `Vec` and use indices.

## 4. "What is interior mutability?"

**Answer:**

- The borrow rule says you cannot mutate through a **shared** `&T`.
  **Interior mutability** is a controlled exception: a type that lets you
  mutate through `&self`, while keeping the program safe by other means.
- The safe versions:

| Type | How it stays safe | Cost | Use |
|---|---|---|---|
| `Cell<T>` | You can only **copy in/out or replace** the whole value, never borrow into it | Free | Counters, flags, small `Copy` values |
| `RefCell<T>` | **Counts borrows at run time** and panics on a violation | A counter check per borrow | Single-threaded graphs, caches, observers |
| `Mutex<T>` | One thread at a time, others **wait** | A lock operation | Shared mutable state across threads |
| `RwLock<T>` | Many readers **or** one writer | A lock operation | Read-mostly shared state |
| `OnceCell` / `OnceLock` | Written **once**, then read-only | Cheap reads | Lazy initialization |
| Atomics (`AtomicUsize`, ...) | Hardware atomic instructions | Cheap | Counters and flags across threads |

- All of them are built on **`UnsafeCell<T>`**, the only primitive in Rust
  that allows mutation through a shared reference. Since Rust 1.99 the
  contents of an `UnsafeCell` are guaranteed to be reachable without going
  through `get`.
- **`RefCell` panics instead of failing to compile.** Two overlapping
  `borrow_mut()` calls cause a panic at run time (`RefCell already
  borrowed`). The sample catches one. `try_borrow` and `try_borrow_mut`
  return a `Result` instead.
- A `RefCell` is `!Sync`: it cannot be shared between threads. Use `Mutex`
  or `RwLock` there.
- **Keep borrows short.** Never hold a `Ref` or `RefMut` across a call that
  might borrow the same cell again.
- **The `Rc<RefCell<T>>` pattern** gives shared, mutable data in
  single-threaded code. It works, but it moves checking to run time, and
  mistakes become panics. Treat it as a **last resort**, as explained in
  [Ownership & Borrowing §7](rust-ownership-and-borrowing.md#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it).

## 5. "What are `Cow`, `OnceLock`, and `LazyLock` for?"

**Answer:**

- **`Cow<'a, T>`** ("clone on write") is an enum: `Borrowed(&'a T)` or
  `Owned(T::Owned)`. A function can return a borrowed value when nothing
  changed and allocate only when it must. The sample's `normalize` borrows
  when the input has no spaces. `to_mut()` clones **on the first write**.
  It appears all over the standard library, for example
  `String::from_utf8_lossy`.
- **`OnceLock<T>`** is a cell you can set **once** (from any thread) and
  read afterwards. **`LazyLock<T>`** runs an initialization closure the
  **first time** it is used. Both replace most uses of `static mut` and the
  old `lazy_static` and `once_cell` crates for new code. The single-thread
  versions are `OnceCell` and `LazyCell`. Recent releases added `get`,
  `get_mut`, and `force_mut` to the lazy types.

    ```rust
    static TABLE: LazyLock<Vec<u32>> = LazyLock::new(|| (1..=5).map(|x| x * x).collect());
    ```

  The sample prints `(computing TABLE once)` exactly once, however many
  times `TABLE` is read.
- Edition 2024 **denies references to `static mut`**, so these types are
  how you hold global state safely.
- **Global state is still global state.** Prefer passing a context
  explicitly. It makes testing easier.

## 6. "How does `Deref` work, and how do you write a smart pointer?"

```rust
struct MyBox<T>(T);
impl<T> Deref for MyBox<T> {
    type Target = T;
    fn deref(&self) -> &T { &self.0 }
}
impl<T: Debug> Drop for MyBox<T> { fn drop(&mut self) { /* cleanup */ } }
```

**Answer:**

- `*b` is shorthand for `*Deref::deref(&b)`. A method call `b.len()` is
  looked up on `MyBox`, then on `Target`, then on `Target`'s `Target`,
  and so on. That chain is **auto-deref**.
- **Deref coercion** applies the same chain to **function arguments**: when
  a function expects `&str` and you pass `&MyBox<String>`, the compiler
  inserts the derefs for you.
- Implement `Deref` **only for real smart pointers**. Using it to fake
  inheritance ("make `Dog` deref to `Animal`") is a well-known **anti-pattern**
  because it makes method lookup confusing.
- `Drop` runs when the value goes out of scope. You cannot call
  `drop(&mut self)` directly. Call the free function `drop(value)`.
- In `unsafe` code, `ManuallyDrop` and `MaybeUninit` take control of drop.
  See [Unsafe Rust & Miri](../advanced-language/rust-unsafe-and-miri.md).

## 7. "What is `Pin`, in one paragraph?"

**Answer:**

- A value normally can be **moved** in memory at any time. Some values must
  **not move** after a certain point, because they contain pointers **to
  themselves**. The main example is the state machine the compiler builds
  for an `async` function.
- `Pin<P>` wraps a pointer and promises the value behind it **will not be
  moved** until it is dropped (unless the type is `Unpin`, which says "moving
  me is harmless"). Most types are `Unpin` automatically.
- You mostly meet `Pin` as `Pin<Box<dyn Future>>` or in the signature of
  `Future::poll`. The full explanation is in
  [Async Internals](../concurrency-and-async/rust-async-internals.md).

## 8. "How do you choose between them?"

**Answer:**

- Ask these questions in order:
    1. Do I need a pointer at all? A plain value or a `&T` is usually
       enough.
    2. One owner, but heap, recursion, or `dyn`? **`Box<T>`**.
    3. Several owners, one thread? **`Rc<T>`**. Several threads? **`Arc<T>`**.
    4. Need to change shared data? Add **`RefCell`** (one thread) or
       **`Mutex` / `RwLock`** (threads). A simple counter? **`Cell`** or an
       **atomic**.
    5. A back pointer without ownership? **`Weak<T>`**.
    6. Maybe borrow, maybe own? **`Cow`**.
    7. Initialize once, globally? **`OnceLock` / `LazyLock`**.
- Costs to remember: a `Box` is one allocation. An `Rc` clone is a counter
  increment. An `Arc` clone is an **atomic** increment. A `RefCell` borrow is
  a counter check. A `Mutex` lock may block.
- Warning signs in a design review: `Rc<RefCell<...>>` nested three deep,
  `Arc<Mutex<...>>` around **everything**, or `clone()` of an `Arc` in a hot
  loop. Each suggests a data-ownership redesign.

## 9. "How do AI tools help or hurt here?"

**Answer:**

- They suggest `Rc<RefCell<T>>` or `Arc<Mutex<T>>` **immediately** for any
  borrow-checker error. That compiles, and hides a design problem, and adds
  run-time panics or contention.
- Ask: "can this be done with plain ownership, indices into a `Vec`, or
  message passing?"
- They may use `Rc` in code that later crosses threads (a compile error
  they then "fix" by switching to `Arc` everywhere). Decide thread use
  first.
- They sometimes still reach for `lazy_static!` or `static mut`. Ask for
  `LazyLock` and `OnceLock`.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Basics**

- "What is a smart pointer? Which traits make one?" — expects owning
  pointer behaviour via `Deref` and `Drop`,
  [§1](#1-what-makes-a-type-a-smart-pointer).
- "What is deref coercion?" — expects the automatic reference conversion
  chain, such as `&String` to `&str`,
  [§1](#1-what-makes-a-type-a-smart-pointer).
- "Why can't you define a recursive enum without `Box`?" — expects
  infinite size; a box has a fixed size,
  [§2](#2-when-do-you-use-boxt).

**Sharing**

- "`Rc` vs `Arc`?" — expects atomic vs non-atomic count, and `Send`,
  [§3](#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for).
- "How can `Rc` leak memory and how do you prevent it?" — expects cycles
  and `Weak`,
  [§3](#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for).
- "What does `Rc::make_mut` do?" — expects copy on write,
  [§3](#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for).

**Interior mutability**

- "What is interior mutability and why is it needed?" — expects mutation
  through `&self` as a controlled exception,
  [§4](#4-what-is-interior-mutability).
- "`Cell` vs `RefCell` vs `Mutex`?" — expects the table, and run-time vs
  compile-time checking,
  [§4](#4-what-is-interior-mutability).
- "What happens if you call `borrow_mut` twice?" — expects a panic, and
  `try_borrow_mut` as the alternative,
  [§4](#4-what-is-interior-mutability).
- "What is the primitive underneath all of these?" — expects
  `UnsafeCell`,
  [§4](#4-what-is-interior-mutability).

**Design**

- "How would you hold a global config safely?" — expects `OnceLock` or
  `LazyLock`, not `static mut`,
  [§5](#5-what-are-cow-oncelock-and-lazylock-for).
- "What is `Cow` for?" — expects borrow or own, clone on write,
  [§5](#5-what-are-cow-oncelock-and-lazylock-for).
- "Why is implementing `Deref` for inheritance an anti-pattern?" —
  expects confusing method resolution,
  [§6](#6-how-does-deref-work-and-how-do-you-write-a-smart-pointer).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/smart_pointers.rs` — `Box` and a recursive list, a custom
  `Deref` and `Drop`, an `Rc`/`Weak` tree with printed counts, `RefCell`
  borrow checking at run time (including the panic), `Cell`, `Rc::make_mut`,
  `Arc` across threads, `Cow`, `OnceLock` and `LazyLock`, and `Box::leak`.

```bash
cd code_samples/rust
cargo run --example smart_pointers
```
