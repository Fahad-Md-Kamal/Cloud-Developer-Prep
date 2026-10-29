---
title: Rust Lifetimes
---

# Rust Lifetimes

A lifetime is a **name for the stretch of code during which a reference
is valid**. Lifetimes exist for one reason: so the compiler can prove that
no reference outlives the value it points to. They are checked at compile
time and **erased before the program runs**: they cost nothing, and they
never change how long a value really lives. They only **describe**
relationships between references so the compiler can verify them. Most
Rust code never writes a lifetime, because the compiler fills them in. This
page covers the cases where it cannot, and how to think about them.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Examples were
    compiled on 1.99.1. Prerequisite:
    [Ownership & Borrowing](rust-ownership-and-borrowing.md).

## 1. "What is a lifetime, really?"

```rust
let r;
{
    let x = 5;
    r = &x;       // r borrows x
}                 // x is dropped here
println!("{r}");  // r would point at freed memory
```

```text
error[E0597]: `x` does not live long enough
 --> compile_fail/does_not_live_long_enough.rs:5:13
  |
4 |         let x = 5;
  |             - binding `x` declared here
5 |         r = &x;
  |             ^^ borrowed value does not live long enough
6 |     }
  |     - `x` dropped here while still borrowed
7 |     println!("{r}");
  |                - borrow later used here
```

**Answer:**

- Every reference has a lifetime: the region from where the borrow is
  created to the **last place it is used**. The owner must live at least
  that long.
- A **lifetime parameter** such as `'a` is a **placeholder** for one of
  these regions. Writing `&'a str` says "a reference valid for region
  `'a`".
- Lifetime annotations **do not extend** a value's life. They tell the
  compiler how the lifetimes of inputs and outputs **relate**, so it can
  check callers.
- Only **references** (and types that contain them) have lifetimes. A
  `String` or `Vec<i32>` has no lifetime parameter, because it owns its
  data.
- Mental model: a lifetime is a **set of points in the program's control
  flow graph** where the borrow is live. The compiler solves "outlives"
  constraints between these sets. If a solution exists, the program is
  accepted.

## 2. "When do you have to write a lifetime?"

```rust
fn longest(a: &str, b: &str) -> &str {
    if a.len() > b.len() { a } else { b }
}
```

```text
error[E0106]: missing lifetime specifier
 --> compile_fail/missing_lifetime.rs:1:33
  |
1 | fn longest(a: &str, b: &str) -> &str {
  |               ----     ----     ^ expected named lifetime parameter
  |
  = help: this function's return type contains a borrowed value, but the signature does not say whether it is borrowed from `a` or `b`
help: consider introducing a named lifetime parameter
  |
1 | fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
  |           ++++     ++          ++          ++
```

**Answer:**

- When a function returns a reference, the compiler must know **which
  input it borrows from**. Here it could be `a` or `b`, so you must say.
- The fix `fn longest<'a>(a: &'a str, b: &'a str) -> &'a str` reads:
  "the result lives no longer than **both** inputs."
- The compiler checks the **body** against this signature and checks every
  **call** against it. Callers only need the signature, never the body.
  That is why lifetimes are part of the **contract** of a function.
- If the two inputs have **different** lifetimes, `'a` becomes the
  **shorter** of the two (the overlap). This is why `longest` cannot return
  a reference to something that has already died:

    ```rust
    let a = String::from("short");
    let result;
    {
        let b = String::from("longer one");
        result = longest(&a, &b).to_string(); // copy out before `b` dies
    }
    ```

- You can use **different** lifetimes when the output depends on only
  one input: `fn first<'a, 'b>(x: &'a str, _y: &'b str) -> &'a str`.

## 3. "What are the elision rules, and why can you usually skip lifetimes?"

**Answer:**

- **Elision** means the compiler fills in lifetimes by three fixed rules.
  They exist because most functions follow a few patterns.
    1. Each **input** reference without a name gets its **own** lifetime.
    2. If there is **exactly one** input lifetime, it is given to **all**
       output references. (`fn first_word(s: &str) -> &str`)
    3. If one input is `&self` or `&mut self`, **its** lifetime is given
       to all outputs. (`fn name(&self) -> &str`)
- If the rules do not decide, you get `E0106` and must write the lifetimes
  yourself, as with `longest`.
- Rule 3 is convenient and sometimes **wrong for you**. See the next
  section.
- `'_` is the **anonymous lifetime**: "a lifetime, infer it". It is useful
  in types such as `Ref<'_, T>` and `Cow<'_, str>` and in `impl` headers:
  `impl Parser<'_>`.
- A lint, `mismatched_lifetime_syntaxes` (warn by default since Rust 1.89),
  asks you to be consistent about hidden lifetimes in signatures, for
  example writing `-> Iter<'_, u8>` instead of a bare `-> Iter<u8>`.

## 4. "How do structs hold references, and what is the `&mut self` trap?"

```rust
struct Parser<'src> {
    rest: &'src str,
}

impl<'src> Parser<'src> {
    fn next_token(&mut self) -> Option<&'src str> { /* ... */ }
}
```

**Answer:**

- A struct that **stores a reference** must declare the lifetime of what
  it borrows: `Parser<'src>`. The struct then **cannot outlive** the text it
  points into.
- The trap: if you write `fn next_token(&mut self) -> Option<&str>`,
  elision rule 3 ties the result to the **`&mut self` borrow**. Then the
  second call is rejected:

    ```text
    error[E0499]: cannot borrow `p` as mutable more than once at a time
      --> compile_fail/self_tied_borrow.rs:22:14
       |
    21 |     let t1 = p.next_token();
       |              - first mutable borrow occurs here
    22 |     let t2 = p.next_token();
       |              ^ second mutable borrow occurs here
    23 |     println!("{t1:?} {t2:?}");
       |                -- first borrow later used here
    ```

- The fix is to return `Option<&'src str>`: the token borrows from the
  **original source text**, not from the parser. Both tokens can then live
  at the same time. This is the single most useful lifetime idea for
  writing **zero-copy parsers**.
- Ask for each returned reference: "**what does this really borrow from?**"
  Then write that in the signature.
- A struct that stores a reference **to its own data** (a self-referential
  struct) **cannot be written in safe Rust**. Alternatives: store an index
  or range instead of a reference, split the owner and the borrower into
  two structs, or use `Pin` with a vetted crate. See
  [Smart Pointers](rust-smart-pointers.md) and
  [Async Internals](../concurrency-and-async/rust-async-internals.md), where
  futures face exactly this problem.

## 5. "What does `'static` mean? It has two meanings."

**Answer:**

- **`&'static T`**: a reference that is valid for the **entire program**.
  String literals have this type (`&'static str`), because their text is
  stored in the program binary. `Box::leak` also produces one by leaking
  memory on purpose.
- **`T: 'static` as a bound**: "`T` **contains no references that can
  expire**." An owned `String` satisfies `'static`. A `&'a str` with a short
  `'a` does not. It does **not** mean "lives forever": a `String`
  satisfies `'static` and is dropped normally.
- This is why `thread::spawn` requires `'static`: the new thread might
  outlive the function, so the closure may not **borrow** local data:

    ```text
    error[E0373]: closure may outlive the current function, but it borrows `data`, which is owned by the current function
     --> compile_fail/spawn_borrows_local.rs:5:32
      |
    5 |     let handle = thread::spawn(|| {
      |                                ^^ may outlive borrowed value `data`
      ...
    help: to force the closure to take ownership of `data` (and any other referenced variables), use the `move` keyword
    ```

  The fix is `move` (give the thread the data), or **scoped threads**
  (`thread::scope`), which are allowed to borrow because they are joined
  before the function returns. See
  [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md).
- `Box<dyn Trait>` means `Box<dyn Trait + 'static>` by default. If the
  trait object holds a borrow, you must write `Box<dyn Trait + 'a>`.
- **Common mistake**: adding `'static` to make an error go away. It
  usually forces you to **own** more than you wanted, or leak memory. Ask
  first why the compiler wants it.

## 6. "What are lifetime bounds and subtyping?"

**Answer:**

- **`'a: 'b`** reads "`'a` **outlives** `'b`": `'a` lasts at least as long
  as `'b`. **`T: 'a`** means "everything inside `T` outlives `'a`".
- A **longer lifetime can be used where a shorter one is expected**. This
  is **subtyping** for lifetimes: `&'long T` is a subtype of `&'short T`.
  That is why you can pass a reference to a long-lived value into a
  function that expects a short-lived one.
- Whether this works for **wrapper types** depends on **variance**: `&'a T`
  and `Vec<&'a T>` are **covariant** (shrinking is fine), while
  `&mut T` and `Cell<&'a T>` are **invariant** in the borrowed type. That
  difference explains many confusing errors with `&mut` and generics. See
  [Variance, Drop Check & PhantomData](../advanced-language/rust-variance-dropck-and-phantomdata.md).
- Bounds appear in generics: `struct Ref<'a, T: 'a>` used to be required.
  Today the compiler **infers** `T: 'a` for struct definitions, so you
  rarely write it.
- Recent releases keep refining these rules. For example, Rust 1.98 allows
  shortening the lifetime of a `&mut` during unsizing coercion even in an
  invariant position, such as coercing a `Cell<&'long mut i32>` to a
  `Cell<&'short mut dyn Send>`.

## 7. "What is a higher-ranked bound (`for<'a>`)?"

```rust
fn apply_to_local<F>(f: F) -> usize
where
    F: for<'x> Fn(&'x str) -> &'x str,
{
    let local = String::from("local value");
    f(&local).len()
}
```

**Answer:**

- `for<'x> Fn(&'x str) -> &'x str` means "this function works for **any**
  lifetime `'x`, chosen by the **caller of `f`**", not one lifetime fixed
  in advance.
- Here, `f` is called with a reference to a **local** whose lifetime does
  not even exist when `apply_to_local` is written. A plain `<'a>` would
  fix `'a` before the call and could not accept that.
- You rarely **write** `for<'x>`. The compiler adds it for you in
  `Fn(&str) -> &str` (an elided closure signature). You see it in error
  messages and in advanced trait bounds.
- It is the tool behind patterns such as "visit every element with a
  borrowed view" and trait bounds on `Deserialize` (`for<'de> Deserialize<'de>`
  is `DeserializeOwned`).

## 8. "How do lifetimes interact with `impl Trait`, and what changed in 2024?"

```rust
fn evens(v: &[i32]) -> impl Iterator<Item = &i32> {
    v.iter().filter(|x| **x % 2 == 0)
}

fn count_up(_label: &str, n: u32) -> impl Iterator<Item = u32> + use<> {
    0..n
}
```

**Answer:**

- A return type `impl Trait` hides the real type. The question is: **which
  lifetimes may that hidden type borrow?**
- **Before edition 2024**: it captured only the lifetimes you wrote in the
  bounds, which forced awkward tricks (`+ '_`, `Captures` helper traits).
- **Edition 2024**: return-position `impl Trait` **captures all in-scope
  lifetimes by default**. The first function above just works.
- The price: sometimes you capture **more than you want**. With edition
  2024, this fails, and the compiler tells you the fix:

    ```text
    error[E0597]: `tmp` does not live long enough
    note: this call may capture more lifetimes than intended, because Rust 2024 has adjusted the `impl Trait` lifetime capture rules
    help: use the precise capturing `use<...>` syntax to make the captures explicit
      | fn count_up(_label: &str, n: u32) -> impl Iterator<Item = u32> + use<> {
    ```

- **`use<>`** is **precise capturing**: it lists exactly the generic
  parameters and lifetimes the result may use. `use<>` means "captures
  nothing". `use<'a, T>` captures just those.
- Precise capturing also works in **traits** since Rust 1.87.
- Related: **`async fn`** in traits and impls returns an `impl Future`, so
  the same capture rules decide whether the future borrows the arguments.
  See [Async Internals](../concurrency-and-async/rust-async-internals.md).

## 9. "What are the common lifetime errors and the standard fixes?"

**Answer:**

| Error | Meaning | Usual fix |
|---|---|---|
| `E0106` missing lifetime specifier | Output reference with no clear source | Add a named lifetime, or return an owned value |
| `E0597` does not live long enough | The owner dies before the borrow ends | Move the owner outward, or own the data |
| `E0515` cannot return reference to local | You returned `&local` | Return the value itself (`String`, not `&String`) |
| `E0499` second mutable borrow, via a method | The method ties the result to `&mut self` | Return data tied to the original lifetime, or clone small data |
| `E0373` closure may outlive the function | `spawn` needs `'static` | Add `move`, or use `thread::scope` |
| `E0521` borrowed data escapes the function | A reference is stored where a longer life is needed | Own it (`to_owned`), or change the signature |
| "lifetime may not live long enough" | Output tied to a shorter lifetime than promised | Relate the lifetimes with a bound (`'a: 'b`) or simplify |

- Habit: when stuck, **write the lifetimes out in full** and read the
  signature as a sentence. If the sentence is not what you mean, change
  the signature, not the body.
- When the signature is **hard to write**, that is a design signal: maybe
  the function should return an owned value, or the data should be owned
  by a different layer.

## 10. "When should you avoid lifetime parameters entirely?"

**Answer:**

- **Own the data** in structs that live a long time: `String`, `Vec<T>`,
  `Arc<T>`. A long-lived service with `struct App<'a>` is a warning sign.
- **Borrow in function parameters**, **own in stored fields**. This one
  rule removes most lifetime annotations from application code.
- **Zero-copy borrowing** (structs with lifetimes) is worth it when:
    - You parse large inputs and want to avoid allocating every token.
    - The borrowed struct has a **short, local life** (parse, use, drop).
    - You measured, and allocation was the cost.
- **Arenas and indices**: when objects point to each other, store them in
  a `Vec` and refer to them by index or ID. No lifetimes, no cycles, and
  good cache behaviour.
- **Shared ownership** (`Rc`, `Arc`) replaces lifetimes when "who owns
  this?" has no single answer. Use it **deliberately**.
- `Cow<'a, str>` gives you **both**: a borrowed result when possible, an
  owned one when needed.
- `serde` supports **borrowing deserialization** (`&'de str` fields),
  which is where `for<'de> Deserialize<'de>` comes from. See
  [Serde & Serialization](../production/rust-serde-and-serialization.md).

## 11. "How do AI tools handle lifetimes?"

**Answer:**

- They are **good at explaining** an error and at suggesting a signature,
  and **bad at judging the design**. A frequent suggestion is
  `'static` everywhere, or adding `.clone()` until it compiles.
- Give the tool the **function signature and the error**. Ask: "what does
  the result borrow from, and could the function return an owned value?"
- Be skeptical of a suggestion that adds lifetime parameters to a
  **struct** that did not have one. Ask whether owning the data is
  simpler.
- Verify any `unsafe` suggestion with extreme care. A lifetime error is
  almost never solved by `unsafe` or `transmute`.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 12. Interview Questions You're Likely to Get Asked

**Basics**

- "What is a lifetime? Does it change how long a value lives?" — expects:
  a name for a valid region of references, checked at compile time,
  purely descriptive,
  [§1](#1-what-is-a-lifetime-really).
- "Why does `fn longest(a: &str, b: &str) -> &str` not compile?" — expects
  the compiler cannot tell which input the output borrows from,
  [§2](#2-when-do-you-have-to-write-a-lifetime).
- "State the three elision rules." — expects the one-input rule and the
  `&self` rule,
  [§3](#3-what-are-the-elision-rules-and-why-can-you-usually-skip-lifetimes).

**Depth**

- "What are the two meanings of `'static`?" — expects `&'static T` vs
  `T: 'static`, and that an owned `String` is `'static`,
  [§5](#5-what-does-static-mean-it-has-two-meanings).
- "Why does `thread::spawn` need `'static`, and what are the ways out?" —
  expects `move` or `thread::scope`,
  [§5](#5-what-does-static-mean-it-has-two-meanings).
- "A parser's `next()` returns `&str` and the second call fails to compile.
  Why?" — expects the elided lifetime ties the result to `&mut self`;
  return `&'src str`,
  [§4](#4-how-do-structs-hold-references-and-what-is-the-mut-self-trap).
- "What is `for<'a>` for?" — expects higher-ranked bounds, a function that
  must work for any lifetime,
  [§7](#7-what-is-a-higher-ranked-bound-fora).
- "What did edition 2024 change for `impl Trait` in return position?" —
  expects capture of all in-scope lifetimes and `use<>`,
  [§8](#8-how-do-lifetimes-interact-with-impl-trait-and-what-changed-in-2024).

**Design**

- "When would you avoid a struct with a lifetime parameter?" — expects
  long-lived or shared data: own it, use indices, or `Arc`,
  [§10](#10-when-should-you-avoid-lifetime-parameters-entirely).
- "Can you write a self-referential struct in safe Rust?" — expects no,
  and the alternatives,
  [§4](#4-how-do-structs-hold-references-and-what-is-the-mut-self-trap).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/lifetimes.rs` — `longest`, elision, a zero-copy `Parser<'src>`,
  edition 2024 `impl Trait` capture, `use<>`, `'static`, and a
  higher-ranked bound.
- `compile_fail/missing_lifetime.rs`, `does_not_live_long_enough.rs`,
  `dangling_reference.rs`, `self_tied_borrow.rs`,
  `spawn_borrows_local.rs`, `rpit_captures_lifetime.rs` — one file per
  error shown on this page.

```bash
cd code_samples/rust
cargo run --example lifetimes
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/self_tied_borrow.rs
```
