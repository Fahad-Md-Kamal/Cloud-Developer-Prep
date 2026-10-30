---
title: Rust Variance, Drop Check and PhantomData
---

# Rust Variance, Drop Check and PhantomData

Three ideas decide whether the borrow checker accepts code that is
written with **generics, lifetimes and raw pointers**: **variance** (when may a
type with a long lifetime be used where a shorter one is needed), the
**drop checker** (may a destructor still read data that is already gone), and
**`PhantomData`** (how a type tells the compiler about things it holds only
"in spirit"). Normal code never touches them. Library authors and anyone writing
`unsafe` data structures must get them right, because a mistake turns into
undefined behaviour. This page explains each rule with the real compiler error.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Code and errors are
    from Rust 1.99.1. Facts about `may_dangle` and variance are checked against
    the Rustonomicon (`subtyping.md`, `dropck.md`, `phantom-data.md`,
    `send-and-sync.md`, branch `master`). Prerequisites:
    [Lifetimes](../foundations/rust-lifetimes.md) and
    [Smart Pointers](../foundations/rust-smart-pointers.md).

## 1. "Does Rust have subtyping?"

**Answer:**

- **Yes, but only for lifetimes.** A reference that lives longer is a
  **subtype** of one that lives shorter: `&'long T` can be used wherever
  `&'short T` is expected, because the longer one is valid for **at least** as
  long. We write `'long: 'short`.
- There is **no** subtyping between structs, traits, or generics such as
  `Dog` and `Animal`. Inheritance does not exist. (Trait objects use
  coercion, not subtyping.)
- **`'static` is the longest lifetime**, so a `&'static str` fits anywhere a
  `&'a str` is needed.
- **Variance** answers the next question: if `'long: 'short`, how are
  `Box<&'long T>`, `Cell<&'long T>` or `fn(&'long T)` related to the
  `'short` versions? It depends on **how the type uses the parameter**.

## 2. "What are covariance, invariance and contravariance?"

```rust
fn shorten<'long: 'short, 'short>(x: &'long str) -> &'short str { x }

let v: Vec<&'static str> = vec!["a", "b"];
let local = String::from("c");
let mut shorter: Vec<&str> = v;      // Vec<&'static str> shrinks: covariant
shorter.push(&local);
```

```text
covariant: &'static str used as a shorter &str -> static text
covariant: Vec<&'static str> coerced, then pushed a local: ["a", "b", "c"]
contravariant: fn(&str) used as fn(&'static str) -> 5
```

**Answer:**

- **Covariant**: the subtype relation **goes the same way**. A `&'long T`
  works as `&'short T`. This is the **default** and the common case.
- **Invariant**: **no** relation. You must use **exactly** the lifetime
  asked for. Required whenever a value can be **written through**.
- **Contravariant**: the relation goes the **opposite way**. Only function
  arguments are contravariant: a function that accepts **any** lifetime can
  stand in for one that accepts only `'static`.

| Type | Variance in `'a` | Variance in `T` |
|---|---|---|
| `&'a T` | covariant | covariant |
| `&'a mut T` | covariant | **invariant** |
| `Box<T>`, `Vec<T>`, `Option<T>` | n/a | covariant |
| `Cell<T>`, `RefCell<T>`, `UnsafeCell<T>` | n/a | **invariant** |
| `*const T` | n/a | covariant |
| `*mut T` | n/a | **invariant** |
| `fn(T) -> U` | n/a | **contravariant** in `T`, covariant in `U` |
| `PhantomData<T>` | n/a | covariant |

- This table extends the one in the Nomicon (`Option` and `PhantomData`
  added). A struct is **variant
  only if all uses are**: one invariant field makes the whole parameter
  invariant. Rust computes it for you from the fields.
- For `PhantomData<fn(T)>` the variance flips to contravariant, and
  `PhantomData<fn() -> T>` is covariant (see
  [§6](#6-what-does-phantomdata-do-and-how-do-i-choose-its-type)).

## 3. "Why is `&mut T` invariant? Show me the bug it prevents."

```rust
fn assign<'a>(target: &mut &'a str, value: &'a str) {
    *target = value;
}

let mut hello: &'static str = "hello";
{
    let world = String::from("world");
    assign(&mut hello, &world);
}
println!("{hello}");   // would print freed memory
```

```text
error[E0597]: `world` does not live long enough
  --> compile_fail/invariant_mut_ref.rs:10:28
   |
 7 |     let mut hello: &'static str = "hello";
   |                    ------------ type annotation requires that `world` is borrowed for `'static`
 8 |     {
 9 |         let world = String::from("world");
   |             ----- binding `world` declared here
10 |         assign(&mut hello, &world);
   |                            ^^^^^^ borrowed value does not live long enough
11 |     }
   |     - `world` dropped here while still borrowed
```

**Answer:**

- If `&mut &'static str` could shrink to `&mut &'short str`, then `assign`
  could write a **short-lived** reference into a variable that promises
  `'static`. After the block ends, `hello` dangles.
- Reading is safe to shrink. **Writing is not.** So anything you can write
  through is invariant: `&mut T`, `Cell<T>`, `RefCell<T>`, `*mut T`.
- Interior mutability has the same hole, shown with `Cell`:

```text
error[E0597]: `local` does not live long enough
  --> compile_fail/invariant_cell.rs:8:15
   |
 5 |     let long: Cell<&'static str> = Cell::new("long");
   |               ------------------ type annotation requires that `local` is borrowed for `'static`
 6 |     let short: &Cell<&str> = &long;
 7 |     let local = String::from("short");
   |         ----- binding `local` declared here
 8 |     short.set(&local);
   |               ^^^^^^ borrowed value does not live long enough
```

- **The error looks odd.** The message says "borrowed for `'static`" even though
  you never wrote it. The cause is invariance: the lifetime of `hello` or `long`
  **cannot shrink**, so the borrow is forced to be that long. When you see
  this shape, look for an invariant type (`&mut`, `Cell`, `*mut`) in the
  signature.
- One more effect: a **struct is invariant if any field is**. An
  `InvStruct<'static>` holding a `Cell<&'a str>` cannot be passed where
  `InvStruct<'short>` is needed:

```text
error[E0597]: `local` does not live long enough
  --> compile_fail/invariant_struct.rs:13:14
   |
11 |     let s: InvStruct<'static> = InvStruct(Cell::new("static"));
   |            ------------------ type annotation requires that `local` is borrowed for `'static`
```

- The `&mut T` rule is only about `T`. The **outer** reference lifetime of
  `&'a mut T` is covariant, so a `&'long mut Vec<i32>` still shrinks.
- Since **1.98** the compiler also shortens the `&mut` lifetime itself during
  an unsizing coercion even when the pointee is invariant (release notes).
  It does not change the rule above.

## 4. "What is the drop checker, and what is it protecting?"

```rust
struct Inspector<'a>(&'a u8);

impl<'a> Drop for Inspector<'a> {
    fn drop(&mut self) {
        println!("I was only {} days from retirement!", self.0);
    }
}

struct World<'a> {
    inspector: Option<Inspector<'a>>,
    days: Box<u8>,
}

let mut world = World { inspector: None, days: Box::new(1) };
world.inspector = Some(Inspector(&world.days));
```

```text
error[E0597]: `world.days` does not live long enough
  --> compile_fail/dropck_inspector.rs:18:38
   |
17 |     let mut world = World { inspector: None, days: Box::new(1) };
   |         --------- binding `world` declared here
18 |     world.inspector = Some(Inspector(&world.days));
   |                                      ^^^^^^^^^^^ borrowed value does not live long enough
19 | }
   | -
   | |
   | `world.days` dropped here while still borrowed
   | borrow might be used here, when `world` is dropped and runs the destructor for type `World<'_>`
```

**Answer:**

- When a value is dropped, its `Drop::drop` runs **with access to its
  fields**. If a field is a reference, `drop` may **read through it**. The
  **drop checker** makes sure that everything a destructor might read is
  **still alive** at that moment.
- Here `World` has a self-reference: `inspector` points into `days`. Fields
  drop in **declaration order**: `inspector` first, then `days`. Looks fine,
  but the drop checker does not reason about field order here. It sees
  `World<'a>` where `'a` must be **strictly longer** than the `World`
  itself, and `&world.days` is a borrow of the `World`'s own field.
- The rule: **if a type has a destructor (`Drop` impl) that may touch a
  borrowed value, that value must strictly outlive the type.** A type
  **without** a destructor has no such requirement, because nothing runs at
  drop time. (`Vec<&T>` has a destructor, but opts out with `#[may_dangle]`,
  see the next section.)
- A simpler version, with plain locals:

```text
error[E0597]: `text` does not live long enough
  --> compile_fail/dropck_wrong_order.rs:12:15
   |
11 |     let text = String::from("short-lived");
   |         ---- binding `text` declared here
12 |     n = Noisy(&text);
   |               ^^^^^ borrowed value does not live long enough
13 |     let _ = &n;
14 | }
   | -
   | |
   | `text` dropped here while still borrowed
   | borrow might be used here, when `n` is dropped and runs the `Drop` code for type `Noisy`
   |
   = note: values in a scope are dropped in the opposite order they are defined
```

- **Locals drop in reverse order of declaration.** Declare the data
  **first**, the borrower after it. In the runnable sample the order is right,
  so it prints `dropping Noisy(kept alive)` after `end of main`.
- Fixes: restructure so there is no self-reference; **split** the struct; hold
  the data in an `Rc` or in a `Vec` and use indices; or declare the owner before
  the borrower.

## 5. "What is `#[may_dangle]`, and why does `Vec<&T>` work?"

**Answer:**

- A `Vec<T>` **has** a destructor (it frees memory). A naive drop check would
  require every `&T` inside it to strictly outlive the `Vec`. That would reject
  ordinary code like putting a reference to a later local into a `Vec`.
- The standard library uses an **unstable** attribute,
  `unsafe impl<#[may_dangle] T> Drop for Vec<T>`. It promises: "my destructor
  **drops** the `T`s but never **reads** through a reference inside them". So
  `T` is allowed to be a dangling reference at drop time.
- `#[may_dangle]` needs the nightly feature `dropck_eyepatch`; on stable,
  `#![feature(...)]` fails with `E0554`. Std-only privilege, an `unsafe` promise.
- The precise rule from the Nomicon: if a type with `may_dangle` owns `T`
  values, it must **tell the compiler it owns them** with
  `PhantomData<T>`, because dropping a `T` may run `T`'s own destructor, and
  **that** destructor may read through references. That is what
  drop-check-ownership means (next section).
- On stable you have two choices: write the unsafe type so the compiler assumes
  the **safe** worst case (a stricter drop check), or use a safe standard
  container (`Vec`, `Box`) and avoid a custom `Drop` that borrows.

## 6. "What does `PhantomData` do, and how do I choose its type?"

```rust
struct MyIter<'a, T> {
    ptr: *const T,
    left: usize,
    _marker: PhantomData<&'a T>,   // "I hold a &'a T"
}
```

```text
MyIter sum = 60
Id<User> copied: 7 7
```

**Answer:**

- `PhantomData<T>` is a **zero-sized marker** that tells the compiler: "act as
  if this type contained a `T`". It has three effects:
    - **Uses the parameter.** A struct may not have a parameter it never
      uses (`E0392`). `PhantomData` is the way to "use" it.
    - **Variance.** It copies the variance of `T`.
    - **Ownership and auto traits.** It affects drop check (does the type
      own `T`?) and `Send` / `Sync`.
- Choose the type to match what the struct **really** does:

| What your struct does | Write | Effect |
|---|---|---|
| Borrows `T` for `'a` (raw-pointer iterator) | `PhantomData<&'a T>` | covariant in `'a` and `T`, no ownership |
| Borrows mutably | `PhantomData<&'a mut T>` | covariant in `'a`, invariant in `T` |
| Owns `T` through a raw pointer (like `Vec`) | `PhantomData<T>` | covariant, owns `T` for drop check, `Send` if `T: Send` |
| Is only **tagged** by `T`, owns none (typed ID) | `PhantomData<fn() -> T>` | covariant, no ownership, **always** `Send` and `Sync` |
| Is a consumer of `T` | `PhantomData<fn(T)>` | contravariant |
| Must be invariant in `T` | `PhantomData<fn(T) -> T>` or `PhantomData<*mut T>` | invariant |
| Must **not** be `Send` or `Sync` | `PhantomData<*const ()>` | opts out of both |

- The typed ID pattern is worth remembering. `Id<T>` below is `Copy` for
  **every** `T`, and `Id<Rc<u8>>` is still `Send`, because `fn() -> T` has no
  `T` inside it:

```rust
struct Id<T> { raw: u64, _t: PhantomData<fn() -> T> }
```

- A bare `PhantomData<T>` there would claim ownership of a `T`. That adds
  an unnecessary drop-check obligation and ties `Send`/`Sync` to `T`.
- Size is **zero**:
  [Memory Layout §9](rust-memory-layout-and-dsts.md#9-what-is-a-zero-sized-type-and-why-is-it-useful).
  Uses for the marker in API design:
  [Advanced Traits §3](rust-advanced-traits-and-type-level-design.md#3-how-do-unit-markers-with-phantomdata-prevent-unit-mix-ups).

## 7. "What are `Send` and `Sync`, and how are they computed?"

```rust
struct NotSend(PhantomData<*const ()>);          // opts out
struct RawHolder(*mut u8);
unsafe impl Send for RawHolder {}                // YOU promise it is safe
```

```text
error[E0277]: `*const ()` cannot be sent between threads safely
  --> compile_fail/phantom_not_send.rs:8:24
   |
 8 |       std::thread::spawn(move || {
   |       ------------------ ^------
   ...
   = help: within `{closure@compile_fail/phantom_not_send.rs:8:24: 8:31}`, the trait `Send` is not implemented for `*const ()`
note: required because it appears within the type `PhantomData<*const ()>`
note: required because it appears within the type `NotSend`
```

**Answer:**

- **`Send`**: a value of this type can be **moved to another thread**.
  **`Sync`**: `&T` can be **shared** between threads. Equivalently,
  `T: Sync` exactly when `&T: Send`.
- They are **auto traits**: the compiler implements them for a struct **if
  every field has them**. Raw pointers are **neither** `Send` nor `Sync`, so any
  struct holding one loses both automatically.
- That is why `Rc` is not `Send` (its counter is not atomic) and
  `Cell`/`RefCell` are not `Sync` (unsynchronized interior mutability).
  See [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md).
- `unsafe impl Send for X {}` is a **promise to the compiler** that you have
  checked it. A wrong promise is a **data race**, which is undefined
  behaviour. Do this only for a type like a wrapper around a C handle that you
  know is thread-safe, and put the reasoning in a `// SAFETY:` comment.
- You can **opt out** of an auto trait by adding a field that lacks it, as
  `NotSend` does. Negative impls (`impl !Send for X`) are **unstable**.
- Auto traits can be **seen through** generics: `Id<Rc<u8>>` is `Send` in the
  sample, because the marker is `fn() -> Rc<u8>`, which contains no `Rc`.

## 8. "What goes wrong when I write unsafe code and get these wrong?"

**Answer:**

- **Wrong variance**: a raw-pointer container using `*mut T` is **invariant**
  by default. That is **safe but annoying**: `MyVec<&'static str>` cannot
  become `MyVec<&'a str>`. Use `NonNull<T>` (covariant) plus `PhantomData<T>`,
  as `Vec` does.
- **Too much variance** is **unsound**. If you store a `&mut`-like handle in
  a field typed as covariant, safe code can write a short-lived reference
  into a long-lived slot (the §3 bug). When in doubt, **be invariant**.
- **Missing drop-check ownership**: a container that owns `T`s through raw
  pointers but has no `PhantomData<T>` lets the compiler believe it does not
  own them, so safe code may drop the `T`'s referents too early. Add
  `PhantomData<T>`.
- **A wrong `unsafe impl Send/Sync`**: undefined behaviour, found only by
  [Miri](rust-unsafe-and-miri.md) or the thread sanitizer if at all.
- Checklist for a new raw-pointer type:
    1. Pick the pointer: `NonNull<T>` if covariant is right, `*mut T` if not.
    2. Add `PhantomData<T>` if you own `T` values.
    3. Decide `Send`/`Sync` from the **meaning** of the type, not from what
       compiles.
    4. Test the variance with a `compile_fail` test.

## 9. "How do AI tools help or hurt here?"

**Answer:**

- They explain **why** a lifetime error says "borrowed for `'static`" when you
  never wrote it, if you give them the signature and the error. Ask: "is there
  an invariant type here?".
- They often **write `PhantomData<T>` for everything**. Ask which of the
  rows in the §6 table applies. A typed ID with `PhantomData<T>` makes the ID
  `!Send` for no reason.
- They happily generate `unsafe impl Send` to "fix" a compile error. That
  hides a bug. Require a `SAFETY` argument and a Miri or loom test.
- **Never** accept advice to add `#![feature(dropck_eyepatch)]` to a stable
  project.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Basics**

- "Does Rust have subtyping?" — expects only for lifetimes, `'long: 'short`,
  [§1](#1-does-rust-have-subtyping).
- "Covariant, invariant, contravariant: one example each." — expects `&T`,
  `&mut T` / `Cell<T>`, `fn(T)`,
  [§2](#2-what-are-covariance-invariance-and-contravariance).
- "What does `PhantomData<T>` do?" — expects it uses the parameter, sets
  variance, and affects drop check and auto traits,
  [§6](#6-what-does-phantomdata-do-and-how-do-i-choose-its-type).

**Depth**

- "Why is `&mut T` invariant in `T`?" — expects the write-a-short-borrow bug,
  [§3](#3-why-is-mut-t-invariant-show-me-the-bug-it-prevents).
- "What does the drop checker prevent?" — expects a destructor reading
  already-freed data, and the strictly-outlive rule,
  [§4](#4-what-is-the-drop-checker-and-what-is-it-protecting).
- "Why does `Vec<&T>` pass drop check?" — expects `#[may_dangle]` and that it
  is unstable, std-only,
  [§5](#5-what-is-may_dangle-and-why-does-vect-work).
- "What are `Send` and `Sync`, and who implements them?" — expects auto traits
  computed from fields, raw pointers opt out, `unsafe impl` is a promise,
  [§7](#7-what-are-send-and-sync-and-how-are-they-computed).

**Design**

- "Design a typed ID `Id<T>` that is `Copy` and `Send` for any `T`." — expects
  `PhantomData<fn() -> T>`,
  [§6](#6-what-does-phantomdata-do-and-how-do-i-choose-its-type).
- "You write a raw-pointer `Vec`. What fields do you add besides the
  pointer?" — expects `PhantomData<T>`, length, capacity, and the
  variance/`Send` decisions,
  [§8](#8-what-goes-wrong-when-i-write-unsafe-code-and-get-these-wrong).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/variance_phantom.rs` — covariance, contravariance, struct
  variance, a raw-pointer iterator with `PhantomData<&'a T>`, the typed ID,
  auto-trait assertions, drop order.
- `compile_fail/invariant_mut_ref.rs`, `invariant_cell.rs`,
  `invariant_struct.rs`, `dropck_inspector.rs`, `dropck_wrong_order.rs`,
  `phantom_not_send.rs` — one file per error quoted above.

```bash
cd code_samples/rust
cargo run --example variance_phantom
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/invariant_mut_ref.rs
```
