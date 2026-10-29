---
title: Rust Traits & Generics
---

# Rust Traits & Generics

A **trait** is a named set of behaviour that types can promise to
provide. **Generics** let one piece of code work for many types, as long
as they keep a trait's promise. Together they are how Rust gets
polymorphism **without inheritance** and, in the common case, **without
any run-time cost**: the compiler writes a specialised copy of generic code
for each type it is used with. Understanding the one big choice here,
**static dispatch (generics) versus dynamic dispatch (`dyn Trait`)**, is
what separates someone who can write Rust from someone who can design with
it.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Trait upcasting
    (stable since Rust 1.86) and native `async fn` in traits are used. The
    compiler now says "dyn compatible" where older books say "object
    safe". Examples ran on 1.99.1.

## 1. "What is a trait, and how do you use one?"

```rust
trait Describe {
    fn name(&self) -> String;               // required
    fn describe(&self) -> String {          // default, can be overridden
        format!("I am {}", self.name())
    }
}

impl Describe for Dog { fn name(&self) -> String { "a dog".into() } }
```

**Answer:**

- A trait lists **method signatures** (and may give **default
  implementations**). A type opts in with `impl Trait for Type`.
- Traits are how Rust shares behaviour. There is **no class inheritance**:
  a type does not inherit fields or methods from a parent, it only
  implements traits.
- A trait can also have **associated types** (`type Item;`), **associated
  constants** (`const MAX: u32;`), and **supertraits** (`trait Pet: Animal`,
  meaning every `Pet` is also an `Animal`).
- The standard library is built on traits: `Display`, `Debug`, `Clone`,
  `Copy`, `PartialEq`, `Ord`, `Hash`, `Default`, `Iterator`, `From`,
  `Into`, `Drop`, `Deref`, `Add` (and the other operators), `Send`, `Sync`.
  **Operator overloading is just a trait**: `a + b` calls `Add::add(a, b)`.
- To call a trait's method, the **trait must be in scope** (`use
  some::Trait;`). A method that seems missing is often a missing `use`.
- **Orphan rule**: you may implement a trait for a type only if **your crate
  owns the trait or the type**. You cannot implement `Display` for
  `Vec<i32>`:

    ```text
    error[E0117]: only traits defined in the current crate can be implemented for types defined outside of the crate
      |
    3 | impl fmt::Display for Vec<i32> {
      |                       -------- `Vec` is not defined in the current crate
      = note: define and implement a trait or new type instead
    ```

  The reason is **coherence**: two crates must never provide conflicting
  implementations. The fix is a **newtype**: `struct Items(Vec<i32>);`.

## 2. "What is the difference between generics and `dyn Trait`?"

```rust
fn intro_static<T: Describe>(x: &T) -> String { x.describe() }   // generics
fn intro_dyn(x: &dyn Describe) -> String { x.describe() }         // trait object
```

**Answer:**

- **Static dispatch (generics, `impl Trait`)**: the compiler generates **one
  copy of the function for each concrete type** it is called with. This is
  called **monomorphization**. The call target is known at compile time,
  so it can be **inlined** and optimized. The cost is **bigger binaries**
  and **longer compile times**.
- **Dynamic dispatch (`dyn Trait`)**: **one** copy of the code. The value is
  accessed through a **fat pointer** of two words: a pointer to the data
  and a pointer to a **vtable** (a table of function pointers). Each call is
  an indirect call. The cost is a **small run-time overhead** and no
  inlining.
- The sample prints the pointer sizes: `&Dog` is 8 bytes, `&dyn Describe`
  is **16 bytes**.

| | Generics (`T: Trait`) | `dyn Trait` |
|---|---|---|
| Dispatch | Static, at compile time | Dynamic, through a vtable |
| Code size | One copy per type | One copy |
| Speed | Fastest (can inline) | Small indirect-call cost |
| Mixed types in one `Vec` | **No**, one `T` | **Yes**, `Vec<Box<dyn Trait>>` |
| Types known at compile time | Required | Not required (plugins, runtime choice) |
| Error messages | Can be long | Simple |

- **Use generics** by default: inside libraries, in hot code, and wherever
  the type is known. **Use `dyn Trait`** when you need a **heterogeneous
  collection**, **runtime selection** (a plugin, a strategy chosen by
  config), or you want to **reduce compile time and binary size**.
- Forms you will see:
    - `fn f(x: &impl Trait)` — sugar for a generic, in argument position.
    - `fn f() -> impl Trait` — "some type that implements `Trait`", chosen
      by the function body. One concrete type, still static.
    - `Box<dyn Trait>` — an owned trait object on the heap.
    - `&dyn Trait` and `&mut dyn Trait` — borrowed trait objects.
    - `Arc<dyn Trait + Send + Sync>` — shared across threads.
- `Box<dyn Trait>` means `Box<dyn Trait + 'static>`. See
  [Lifetimes §5](rust-lifetimes.md#5-what-does-static-mean-it-has-two-meanings).

## 3. "What does it mean that a trait is dyn compatible?"

```text
error[E0038]: the trait `Cloner` is not dyn compatible
 | fn dup(&self) -> Self;
 |                  ^^^^ ...because method `dup` references the `Self` type in its return type
 | fn map<F: Fn(i32) -> i32>(&self, f: F) -> i32;
 |    ^^^ ...because method `map` has generic type parameters
```

**Answer:**

- To build a **vtable**, the compiler needs one fixed function pointer per
  method. Some methods cannot have one, so a trait with them cannot be used
  as `dyn Trait`. A trait is **dyn compatible** when:
    - No method returns `Self` or takes `Self` by value in a way the vtable
      cannot express.
    - No method has **generic type parameters** (a vtable cannot hold
      "one function per type").
    - It has no associated constants, and does not require `Self: Sized`.
- Opt a method out with **`where Self: Sized`**. The trait stays dyn
  compatible, and the method is simply not callable on a `dyn Trait`. The
  sample's `Visitor::map_all` does this.
- **Supertrait casts (trait upcasting)**, stable since Rust 1.86: a
  `&dyn Pet` can be used where `&dyn Animal` is expected when
  `Pet: Animal`. Before 1.86 you needed a helper method.
- Since a trait object forgets the concrete type, you cannot clone one with
  `Clone`. The usual workaround is a `clone_box(&self) -> Box<dyn Trait>`
  method.

## 4. "How do you write generic code, and what are bounds?"

**Answer:**

- A **generic function** declares type parameters in angle brackets and
  **bounds** them with traits:

    ```rust
    fn largest<T: PartialOrd + Copy>(items: &[T]) -> T { /* ... */ }
    ```

  Without the bound, the compiler refuses to compile the body, because it
  cannot know `T` supports `>`:

    ```text
    error[E0369]: binary operation `>` cannot be applied to type `&T`
    help: consider restricting type parameter `T` with trait `PartialOrd`
    ```

  This is a big difference from C++ templates: Rust checks the generic
  **definition** once, against its bounds, not each use. Errors appear at
  the definition and are usually clear.
- Bound syntax:
    - `T: A + B` — inline.
    - `where T: A + B, U: C` — clearer when long.
    - `impl<T: Display> Trait for Wrapper<T>` — a **conditional impl**:
      `Wrapper<T>` implements the trait **only when** `T: Display`.
- **Blanket impls** implement a trait for **every** type meeting a bound:
  `impl<T: Display> Shout for T`. This is how `ToString` is available on
  everything that is `Display`, and how `Into` comes from `From`.
- **Associated types vs generic parameters.** If each implementor has
  exactly **one** natural output type, use an associated type
  (`Iterator::Item`). If a type may implement the trait **many times** for
  different `T`, use a parameter (`From<T>`: a type can be built `From` many
  sources).
- **Const generics** put a **value** in the type: `Matrix<const R: usize,
  const C: usize>`. `[T; N]` is the standard example. The sample's
  `transpose` returns a `Matrix<C, R>`, so a wrong shape is a compile error.
- **Default type parameters** keep common cases short:
  `trait Add<Rhs = Self>`.
- **Generic structs** can have methods only for some `T`, using separate
  `impl` blocks with different bounds.
- Since Rust 1.89, **explicitly inferred const arguments** are stable: you
  can write `_` in place of a const generic argument, such as
  `Matrix::<_, 3>`, and let the compiler infer it.

## 5. "What are the traits you must know by heart?"

**Answer:**

| Trait | Purpose | Notes |
|---|---|---|
| `Clone` / `Copy` | Duplicate a value | `Copy` is implicit and bitwise; see [Ownership §3](rust-ownership-and-borrowing.md#3-what-is-the-difference-between-copy-and-clone) |
| `Drop` | Cleanup when a value goes away | A type with `Drop` cannot be `Copy` |
| `PartialEq` / `Eq` | `==` | `Eq` promises equality is total (no NaN-like values) |
| `PartialOrd` / `Ord` | `<` and sorting | Derived order is field by field |
| `Hash` | Hash for map keys | Must agree with `Eq` |
| `Default` | A default value | |
| `Debug` / `Display` | Developer and user text | `Display` also gives `.to_string()` |
| `From` / `Into` | Infallible conversion | Implement `From`; `Into` comes free |
| `TryFrom` / `TryInto` | Fallible conversion | Returns `Result` |
| `AsRef` / `Borrow` | Cheap reference conversion | `AsRef` for APIs, `Borrow` for map lookups |
| `Deref` / `DerefMut` | Smart-pointer behaviour | Enables deref coercion; see [Smart Pointers](rust-smart-pointers.md) |
| `Iterator` / `IntoIterator` | Looping | See [Iterators & Closures](rust-iterators-and-closures.md) |
| `Fn`, `FnMut`, `FnOnce` | Callable values | Closures implement them |
| `Send` / `Sync` | Thread-safety markers | Automatic; see [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md) |
| `Sized` | Size known at compile time | `?Sized` relaxes it |
| `Error` | Error types | See [Error Handling](rust-error-handling.md) |

- **`Send` and `Sync`** are **auto traits**: the compiler implements them for
  a type if all its parts have them. They carry no methods. They are how the
  compiler rejects data races. This is the heart of "fearless concurrency".
- **Marker traits** such as `Copy`, `Send`, `Sync`, and `Eq` have no methods.
  They only record a **fact** about a type.
- Prefer implementing **`From`** rather than `Into`, and **`Display`**
  rather than writing `to_string` by hand.

## 6. "How do traits interact with async and closures?"

**Answer:**

- **`async fn` in traits** works directly (stable since Rust 1.75), so the
  `async-trait` crate is no longer needed in most code. The method returns
  an anonymous future. One limit: a trait with `async fn` is **not dyn
  compatible**, because every implementor's future is a different size. Use
  generics, or a boxed-future workaround, when you need `dyn`. See
  [Async Internals](../concurrency-and-async/rust-async-internals.md).
- **Async closures** (`async |x| { ... }`) are stable since Rust 1.85, with
  the traits `AsyncFn`, `AsyncFnMut`, and `AsyncFnOnce`. They solve the
  old problem of an async block that borrows from its captured
  environment.
- Closures implement `Fn`, `FnMut`, or `FnOnce` depending on **how they use
  what they capture**. A function that takes `impl Fn(i32) -> i32` is
  generic over the closure type. See
  [Iterators & Closures](rust-iterators-and-closures.md).

## 7. "What are the common trait and generic mistakes?"

**Answer:**

- **`Box<dyn Trait>` everywhere** because it is familiar from Java. Prefer a
  generic or an enum when the set of types is **known and closed**. An
  enum is faster and is checked for exhaustiveness.
- **Too many generic parameters**, which makes signatures unreadable and
  compile times long. Use `dyn Trait` or an enum at **boundaries**.
- **Over-bounded generics**. Ask only for the traits you use. `T: Clone`
  when you never clone limits callers for no reason.
- **Forgetting that a generic function is compiled per type.** A large
  generic function used with 20 types makes 20 copies. A common trick: keep
  the generic wrapper tiny and call a **non-generic inner function**.
- **Implementing a foreign trait for a foreign type.** Use a newtype.
- **Returning `impl Trait` when you need to name the type** (in a struct
  field, for example). Then use a generic parameter or a boxed trait
  object.
- **Reaching for specialization.** It is **not stable**. A stable
  alternative is a helper trait, or separate types.
- A **`dyn Trait` method call is not free**, but it is cheap. Do not
  contort designs to avoid it unless a profile says so.

## 8. "How do AI tools help or hurt with traits and generics?"

**Answer:**

- Good at **writing impls**, **blanket impls**, and explaining a long
  trait-bound error line by line.
- They often use **`Box<dyn Trait>` by default**, add **unneeded bounds**
  (`Clone + Send + Sync + 'static` "to be safe"), or use the old
  `async-trait` crate and `Pin<Box<dyn Future>>` where native `async fn` in
  traits works now.
- Ask: "which of these bounds does the body actually need?" and "does a
  closed set of types suggest an enum here?"
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Core ideas**

- "How does Rust do polymorphism without inheritance?" — expects traits
  plus generics, and composition,
  [§1](#1-what-is-a-trait-and-how-do-you-use-one).
- "What is the orphan rule and why does it exist?" — expects coherence, and
  the newtype workaround,
  [§1](#1-what-is-a-trait-and-how-do-you-use-one).
- "Explain monomorphization and its trade-offs." — expects a copy per type,
  speed and inlining vs code size and compile time,
  [§2](#2-what-is-the-difference-between-generics-and-dyn-trait).

**Dispatch**

- "Generics or `dyn Trait`? When each?" — expects the comparison table,
  [§2](#2-what-is-the-difference-between-generics-and-dyn-trait).
- "What is a fat pointer, and what is in a vtable?" — expects data pointer
  plus vtable pointer, and function pointers (plus size and drop),
  [§2](#2-what-is-the-difference-between-generics-and-dyn-trait).
- "Why can't you make this trait into `dyn Trait`?" — expects generic
  methods or `Self` in the return type, and `where Self: Sized`,
  [§3](#3-what-does-it-mean-that-a-trait-is-dyn-compatible).
- "What changed in Rust 1.86 about trait objects?" — expects trait
  upcasting,
  [§3](#3-what-does-it-mean-that-a-trait-is-dyn-compatible).

**Design**

- "Associated type or generic parameter?" — expects one output per type vs
  many implementations,
  [§4](#4-how-do-you-write-generic-code-and-what-are-bounds).
- "What is a blanket impl? Give an example from std." — expects `ToString`
  for `Display`, and `Into` from `From`,
  [§4](#4-how-do-you-write-generic-code-and-what-are-bounds).
- "Why can't a trait with `async fn` be a trait object, and what do you do?"
  — expects unknown future sizes; use generics or boxing,
  [§6](#6-how-do-traits-interact-with-async-and-closures).
- "When would you choose an enum over `Box<dyn Trait>`?" — expects a closed
  set of types known at compile time,
  [§7](#7-what-are-the-common-trait-and-generic-mistakes).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/traits_generics.rs` — default methods, static vs dynamic
  dispatch (with pointer sizes), associated types, a blanket impl,
  operator overloading, const generics, trait upcasting, and
  `where Self: Sized`.
- `compile_fail/orphan_rule.rs`, `not_dyn_compatible.rs`,
  `missing_trait_bound.rs` — the three errors shown on this page.

```bash
cd code_samples/rust
cargo run --example traits_generics
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/not_dyn_compatible.rs
```
