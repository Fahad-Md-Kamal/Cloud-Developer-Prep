---
title: Rust Types, Enums & Patterns
---

# Rust Types, Enums & Patterns

Rust's type system is the main tool for writing programs that are
**correct by construction**. Two ideas carry most of the weight: **enums**
(a value that is *one of* several shapes, each carrying its own data) and
**pattern matching** (taking such a value apart, with the compiler
checking you handled every shape). Together they replace null pointers,
status codes, and a lot of defensive `if` chains. This page also covers
the number rules that surprise people coming from other languages.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Let chains need
    edition 2024 (stable since Rust 1.88). `if let` guards in `match` arms
    are stable since Rust 1.95. Everything was run on 1.99.1.

## 1. "How do numbers behave, and where is Rust strict on purpose?"

**Answer:**

- Integer types are named by size: `i8 i16 i32 i64 i128 isize` (signed),
  `u8 u16 u32 u64 u128 usize` (unsigned). `isize` and `usize` match the
  pointer size, and `usize` is the type of **lengths and indices**.
- Floats are `f32` and `f64`. The default for an unsuffixed integer is
  `i32`, and for a float, `f64`.
- **Overflow** is the first surprise. Plain `+` **panics** in a debug build
  and **wraps** in a release build. You choose the behaviour with
  explicit methods:

| Method | On overflow |
|---|---|
| `checked_add` | Returns `None` |
| `wrapping_add` | Wraps around |
| `saturating_add` | Stays at the maximum or minimum |
| `overflowing_add` | Returns `(wrapped, did_overflow)` |
| `strict_add` | **Always panics**, in every build (stable since Rust 1.91) |

- **No implicit conversions.** `let x: u64 = my_u32;` is an error. Convert
  on purpose:
    - `u64::from(my_u32)` — lossless, cannot fail (the `From` trait).
    - `u8::try_from(300_i32)` — may fail, returns a `Result` (`TryFrom`).
    - `x as u8` — a raw cast. It **silently truncates**: `300_i32 as u8` is
      `44`. A float cast **saturates**: `1e20_f64 as i32` is `i32::MAX`, and
      `f64::NAN as i32` is `0`.
- Prefer `From` and `TryFrom` over `as` for anything that could lose
  information. Use `as` only when you want exactly that bit-level
  behaviour.
- **Floats follow IEEE 754.** `NaN == NaN` is `false`, and `NaN < 1.0` is
  `false`. That is why `f64` is `PartialOrd` and **not** `Ord`: it has no
  total order, so you cannot `.sort()` a `Vec<f64>`. Use
  `sort_by(|a, b| a.total_cmp(b))`.
- `0.1 + 0.2` is `0.30000000000000004` in Rust, as in every language that
  uses binary floats. Use integers (cents) or a decimal crate for money.
- `char` is a 4-byte Unicode scalar value, **not** a byte. `'🦀' as u32` is
  `0x1f980`. A byte is `u8`.
- Run `numeric_semantics` to see every line of this section. Try it with
  and without `--release`.

## 2. "What are tuples, arrays, slices, and strings?"

**Answer:**

- A **tuple** `(i32, f64, &str)` groups values of different types. The
  empty tuple `()` is the **unit** type, the "no value" type that functions
  return when they return nothing.
- An **array** `[T; N]` has a size known at **compile time** (`[0u8; 16]`)
  and lives wherever you put it, often the stack.
- A **slice** `[T]` is a **view** of some elements stored elsewhere. You
  almost always meet it behind a pointer: `&[T]` (shared) or `&mut [T]`.
  A `&[T]` is a **fat pointer**: an address plus a length.
- `str` is a slice of UTF-8 bytes, and `&str` is a view into text. A
  `String` is the **owned**, growable version. See
  [Collections & Strings](rust-collections-and-strings.md).
- **Indexing is bounds-checked.** `v[10]` on a 3-element vector **panics**.
  Use `v.get(10)` to get an `Option`. The checks are cheap, and iterators
  usually remove them.
- **`!` (the never type)** is the type of expressions that never finish:
  `panic!()`, `return`, `loop {}`. It coerces to every type, which is why
  `let n: i32 = match x { Some(n) => n, None => return };` works.

## 3. "How do structs and methods work?"

```rust
#[derive(Debug, Clone, PartialEq)]
struct User {
    name: String,
    age: u32,
}

impl User {
    fn new(name: &str, age: u32) -> Self {      // associated function
        User { name: name.to_string(), age }
    }
    fn is_adult(&self) -> bool {                 // method: takes &self
        self.age >= 18
    }
}

let a = User::new("Ann", 30);
let b = User { name: "Bob".into(), ..a.clone() }; // struct update syntax
```

**Answer:**

- Three struct forms: **named fields** (`User { name, age }`), **tuple
  structs** (`Meters(f64)`), and **unit structs** (`Marker`).
- Methods live in `impl` blocks. The first parameter says how the method
  uses the value: `self` (consumes it), `&self` (reads), `&mut self`
  (changes). A function without `self` is an **associated function**
  called as `Type::name()`.
- Fields are **private to the module** unless marked `pub`. Privacy is by
  module, not by type, which is the basis of the encapsulation tricks in
  [Project Architecture & API Guidelines](../production/rust-project-architecture-and-api-design.md).
- `#[derive(...)]` writes standard trait implementations for you:

| Derive | Gives you |
|---|---|
| `Debug` | `{:?}` formatting |
| `Clone`, `Copy` | Explicit and implicit duplication |
| `PartialEq`, `Eq` | `==` (and "equality is total", for `Eq`) |
| `PartialOrd`, `Ord` | `<`, sorting (field by field in order) |
| `Hash` | Use as a `HashMap` key |
| `Default` | `Type::default()` |

- Struct update syntax `..a.clone()` fills the remaining fields from
  another value. Note that it **moves** the fields it takes.
- A **newtype** is a tuple struct with one field: `struct Meters(f64);`.
  It is a **distinct type with zero run-time cost**. It stops you passing a
  `Meters` where `Seconds` is expected, and it is the way to implement
  foreign traits on foreign types (the orphan rule).

## 4. "What is an enum, and why is it better than null or status codes?"

```rust
enum Shape {
    Circle { r: f64 },
    Rect { w: f64, h: f64 },
    Triangle(f64, f64, f64),
}

fn area(s: &Shape) -> f64 {
    match s {
        Shape::Circle { r } => std::f64::consts::PI * r * r,
        Shape::Rect { w, h } => w * h,
        Shape::Triangle(a, b, c) => { /* Heron's formula */ 0.0 }
    }
}
```

**Answer:**

- An enum is a **sum type**: a value is **exactly one** of the listed
  **variants**, and each variant can carry **different data**. A struct is
  a **product type**: it has **all** its fields.
- In memory, an enum is a small **tag** (which variant) plus room for the
  **largest** variant's data. The compiler can sometimes hide the tag
  inside an unused bit pattern (a **niche**). `Option<&T>`, `Option<Box<T>>`
  and `Option<NonZeroU32>` are the **same size** as the plain pointer or
  integer, because `0` is free to mean `None`. `Option<u32>` is 8 bytes
  because every `u32` value is used. See
  [Memory Layout & DSTs](../advanced-language/rust-memory-layout-and-dsts.md).
- The two enums you use daily:
    - **`Option<T>`**: `Some(T)` or `None`. Rust has **no null**. Absence is
      a value you must handle.
    - **`Result<T, E>`**: `Ok(T)` or `Err(E)`. Errors are values. See
      [Error Handling](rust-error-handling.md).
- **`match` must be exhaustive.** Add a variant later, and every `match`
  without a catch-all becomes a **compile error**, pointing at each place
  to update. This is the main reason refactoring Rust is safe.
- Avoid `_ =>` for your own enums when you want that safety net.
- **`#[non_exhaustive]`** on a public enum tells **other crates** they must
  include a catch-all arm, so you can add variants without a breaking
  change.
- Compared with other approaches:

| Approach | Problem |
|---|---|
| `null` | Any reference may be null; nothing forces a check |
| Status codes (`-1`, `0`) | Easy to ignore; the value and the error share one type |
| Exceptions | Hidden control flow; the type does not show what can fail |
| **Enums** | The type says what can happen, and the compiler checks every case |

## 5. "What kinds of patterns exist?"

**Answer:**

- A **pattern** is a shape that a value is matched against, and it can
  **bind** parts of the value to names. Patterns appear in `match`,
  `let`, `if let`, `while let`, function parameters, and `for` loops.
- The forms:

| Pattern | Example | Matches |
|---|---|---|
| Literal | `0`, `'a'`, `"yes"` | That exact value |
| Range | `1..=9`, `'a'..='z'` | Any value in the range |
| Binding | `x`, `mut x` | Anything, and names it |
| Wildcard | `_` | Anything, ignored |
| Or | `1 \| 3 \| 5` | Any alternative |
| Tuple / struct | `(a, b)`, `Point { x, y: 0 }` | Destructures fields |
| Enum variant | `Some(n)`, `Shape::Rect { w, .. }` | One variant, with its data |
| Slice | `[first, .., last]`, `[x]`, `[]` | Arrays and slices by length |
| Reference | `&x`, `&mut x` | Through a reference |
| `@` binding | `n @ 10..=20` | Name the value **and** test it |
| Rest | `..` | "Ignore the other fields or elements" |

- A **guard** adds a condition: `x if x % 2 == 0 => ...`.
- **Irrefutable** patterns always match (`let (a, b) = pair;`). **Refutable**
  ones may fail (`Some(x)`) and need `if let`, `let else`, or `match`.
- **Binding modes ("match ergonomics")**: matching a **reference**
  against a non-reference pattern automatically binds **by reference**.
  `match &opt { Some(s) => ... }` gives `s: &String`, with no `&` or `ref`
  needed. Edition 2024 **reserves** writing explicit `ref`, `mut`, or `&`
  inside such a pattern, to leave room for improving this feature.
- **`let else`** binds or leaves:

    ```rust
    let Some((k, v)) = line.split_once('=') else {
        return None;
    };
    ```

  It keeps the happy path at the left margin instead of nesting.
- **Slice patterns** let you write recursion and "first and rest" code
  without index arithmetic.
- `matches!(value, pattern)` returns a `bool`. `assert_matches!` (stable
  since Rust 1.96) asserts a pattern and **prints the actual value** when
  it fails.

## 6. "What are let chains and `if let` guards, and what do they replace?"

```rust
// Let chains: edition 2024, stable since Rust 1.88
if let Some(s) = name
    && let Ok(n) = s.parse::<i32>()
    && let Some(max) = limit
    && n < max
{
    println!("{n} is under {max}");
}

// `if let` guard in a match arm: stable since Rust 1.95
let text = match input {
    Some(s) if let Ok(n) = s.parse::<i32>() => format!("number {n}"),
    Some(s) => format!("not a number: {s}"),
    None => "nothing".to_string(),
};
```

**Answer:**

- **Let chains** join `if let` tests and plain boolean conditions with
  `&&`. Every binding is visible to the conditions **after** it and to the
  body. Before 2024 you needed nested `if let` blocks or `and_then` chains.
- **`if let` guards** let a `match` arm test a second **pattern** on top of
  the first match. They replace the awkward "match, then match again"
  nesting.
- Let chains are **edition 2024 only**. If you write them in a 2021 crate
  you get an error that suggests changing the edition.
- Evaluation is **left to right and short-circuits**, like `&&`.
- Edition 2024 also changed **temporary scope** in `if let`: temporaries
  created in the scrutinee are dropped **before** the `else` branch runs.
  This removes a source of deadlocks with locks held across an `else`.
- Keep chains short. More than three or four conditions are usually a
  signal to extract a function.

## 7. "How do you design types so wrong states cannot exist?"

**Answer:**

- **Use enums instead of a flag plus optional fields.** Not:

    ```rust
    struct Job { done: bool, error: Option<String>, result: Option<Data> }
    ```

  but:

    ```rust
    enum Job { Pending, Running { started: Instant }, Done(Data), Failed(String) }
    ```

  Now "done with an error" cannot be represented.
- **Newtypes with checked constructors.** `struct Email(String);` with
  `Email::parse(&str) -> Result<Email, ParseError>` and a private field
  means every `Email` in the program is **already valid**. Validation
  happens once, at the edge.
- **`NonZero*` and `Option<NonZero*>`** express "an id that is never 0".
- **State machines as types ("typestate")**: `Door<Open>` and
  `Door<Closed>` are different types, and `open()` exists only on
  `Door<Closed>`. See
  [Advanced Traits & Type-Level Design](../advanced-language/rust-advanced-traits-and-type-level-design.md).
- **Take the narrowest type** in parameters (`&[T]` not `&Vec<T>`,
  `&str` not `&String`) and **return the most useful one**.
- Parse, don't validate: turn raw input into a rich type **once**, near
  the input, and pass the rich type everywhere else.

## 8. "How do constants, statics, blocks, and shadowing work?"

**Answer:**

- `const MAX: u32 = 100;` is **inlined** at each use. It has no address.
  `const fn` functions can run at compile time.
- `static NAME: T = ...;` is **one location in memory** for the whole
  program. A `static mut` is **unsafe** to touch, and in edition 2024
  **taking a reference to a `static mut` is an error**. Use atomics,
  `OnceLock`, or `LazyLock` instead. See
  [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md).
- **Everything is an expression.** A block evaluates to its last expression
  (no semicolon). `if`, `match`, and `loop { break value; }` all produce
  values.
- **Shadowing** (`let x = x.trim();`) creates a **new** variable with the
  same name, which can even change the type. It is not mutation, and it is
  idiomatic for step-by-step conversion.
- **Labels** (`'outer: for ... { break 'outer; }`) exit nested loops.

## 9. "How do AI tools help, and where do they mislead?"

**Answer:**

- Good for: writing `match` arms for a large enum, generating `derive`
  lists, and suggesting an enum redesign.
- They often write **older style**: nested `if let`, `.unwrap()` chains,
  or `as` casts for conversions. Ask for edition 2024 style, `let else`,
  let chains, `From` and `TryFrom`.
- They may add `_ =>` arms that **hide** missing variants. For your own
  enums, prefer listing every variant.
- Ask for the **invalid states** your types still allow, and for a design
  that removes them.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Numbers**

- "What happens on integer overflow in Rust?" — expects: panic in debug,
  wrap in release, and the explicit `checked`, `wrapping`, `saturating`,
  `overflowing`, and `strict` methods,
  [§1](#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose).
- "Why can't you sort a `Vec<f64>` with `.sort()`?" — expects floats are
  only `PartialOrd` because of NaN; use `total_cmp`,
  [§1](#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose).
- "`as` vs `From` vs `TryFrom`?" — expects `as` truncates silently,
  `From` is lossless, `TryFrom` can fail,
  [§1](#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose).

**Enums and patterns**

- "Why does Rust have no null, and what replaces it?" — expects `Option`,
  with the check enforced by the type,
  [§4](#4-what-is-an-enum-and-why-is-it-better-than-null-or-status-codes).
- "Why is `Option<&T>` the same size as `&T`?" — expects niche
  optimization,
  [§4](#4-what-is-an-enum-and-why-is-it-better-than-null-or-status-codes).
- "What does exhaustive matching buy you when the code changes?" —
  expects compile errors at every `match` after a new variant,
  [§4](#4-what-is-an-enum-and-why-is-it-better-than-null-or-status-codes).
- "What is `let else` for?" — expects early exit with a flat happy path,
  [§5](#5-what-kinds-of-patterns-exist).
- "What do let chains and `if let` guards add?" — expects flattening
  nested `if let`, and the edition 2024 and 1.95 facts,
  [§6](#6-what-are-let-chains-and-if-let-guards-and-what-do-they-replace).

**Design**

- "Model a job that can be pending, running, done, or failed." — expects
  one enum with data per variant, not a bool and two `Option`s,
  [§7](#7-how-do-you-design-types-so-wrong-states-cannot-exist).
- "What is a newtype and why use one?" — expects distinct type, zero cost,
  validated construction,
  [§3](#3-how-do-structs-and-methods-work).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/types_and_patterns.rs` — enums with data, ranges and guards,
  `let else`, slice patterns, `@` bindings, let chains, `if let` guards,
  and `matches!`.
- `examples/numeric_semantics.rs` — the overflow methods, `as` casts,
  float traps, `NonZero` niches, and `assert_matches!`.

```bash
cd code_samples/rust
cargo run --example types_and_patterns
cargo run --example numeric_semantics
cargo run --release --example numeric_semantics   # overflow behaves differently
```
