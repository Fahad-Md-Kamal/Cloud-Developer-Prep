---
title: Advanced Rust Traits and Type-Level Design
---

# Advanced Rust Traits and Type-Level Design

**Type-level design** means using Rust's type system to make wrong programs
**impossible to write**, instead of checking at run time. A door that cannot
be closed twice, a `Money<Usd>` that cannot be added to a `Money<Eur>`, a
trait that outsiders cannot implement: all of these are rules enforced by
the compiler, with **no run-time cost**. This page collects the advanced
trait features that make that possible, and says honestly which ones are
still unstable.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. All code was
    compiled and run on 1.99.1. Every "unstable" claim below was checked by
    compiling the feature on stable and quoting the real error.
    Prerequisites: [Traits & Generics](../foundations/rust-traits-and-generics.md)
    and [Lifetimes](../foundations/rust-lifetimes.md).

## 1. "What is the typestate pattern?"

```rust
struct Open;
struct Closed;

struct Door<State> {
    opened_times: u32,
    _state: PhantomData<State>,
}

impl Door<Closed> {
    fn new() -> Self { Door { opened_times: 0, _state: PhantomData } }
    fn open(self) -> Door<Open> { /* ... */ }
}
impl Door<Open> {
    fn close(self) -> Door<Closed> { /* ... */ }
}

let door = Door::new().open().close().open();   // compiles
// Door::new().close();   // error: no method `close` for `Door<Closed>`
```

```text
typestate door opened 2 times
```

**Answer:**

- **Typestate** puts an object's **state in its type**. Methods exist only in
  the states where they are legal, so calling them in the wrong order is a
  **compile error**, not a bug.
- Methods take `self` **by value** and return the next state. The old value
  is moved, so you cannot keep using a "closed" door after opening it. See
  [Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md).
- The state types are **zero-sized**, and `PhantomData<State>` carries them
  at no cost. See
  [Memory Layout §9](rust-memory-layout-and-dsts.md#9-what-is-a-zero-sized-type-and-why-is-it-useful).
- Real uses: a builder that cannot call `build()` before the required
  fields are set; a connection that is `Disconnected`, `Connected`,
  `Authenticated`; a file handle that is `Open` or `Closed`.
- **Cost**: more types and more generic code. Use it when a wrong order is
  a **real** risk (protocols, security), not for every builder.

## 2. "How do I stop other code from implementing my trait?"

```rust
mod sealed {
    pub trait Sealed {}
}
pub trait Currency: sealed::Sealed {
    const CODE: &'static str;
}
```

Another crate that tries it:

```text
error[E0277]: the trait bound `Other: Sealed` is not satisfied
  --> compile_fail/sealed_trait_outside.rs:13:22
   |
13 | impl api::Closed for Other {}
   |                      ^^^^^ unsatisfied trait bound
   ...
   = note: `Closed` is a "sealed trait", because to implement it you also need to implement `api::private::Sealed`, which is not accessible; this is usually done to force you to use one of the provided types that already implement it
```

**Answer:**

- A **sealed trait** is public (anyone can **use** it as a bound) but has a
  **private supertrait**, so nobody outside the crate can **implement** it.
- Why seal? So you can **add methods later without breaking users**. If
  anyone could implement the trait, adding a required method would break
  their code. Sealing makes that change **SemVer-safe** (Semantic
  Versioning).
- Seal a trait when the set of implementors is **closed by design**
  (`Currency`, a protocol version, the standard library's `Pattern`-like
  helpers). Do not seal one meant as an extension point.
- The compiler even **explains** the trick in the error above.
- Alternative: `#[non_exhaustive]` stops outsiders from building a struct or
  matching an enum exhaustively. It is the sibling tool for types. See
  [Project Architecture & API Design](../production/rust-project-architecture-and-api-design.md).

## 3. "How do unit markers with `PhantomData` prevent unit mix-ups?"

```rust
struct Money<C: Currency> { cents: i64, _c: PhantomData<C> }

let a: Money<Usd> = Money::new(1050);
let b: Money<Usd> = Money::new(295);
a.add(&b);                 // fine
// a.add(&Money::<Eur>::new(100));   // type mismatch: expected Money<Usd>
```

```text
13.45 USD
1.00 EUR (a Money<Usd> cannot be added to this)
size_of Money<Usd> = 8 (same as i64)
```

**Answer:**

- A **phantom type parameter** appears in the type but not in the data.
  `PhantomData<C>` is a zero-sized field that "uses" `C`, so the compiler
  accepts the parameter.
- `Money<Usd>` and `Money<Eur>` are **different types**. Mixing them is a
  compile error. The size stays 8 bytes, the same as a bare `i64`.
- Real uses: units of measure (`Meters` vs `Feet`), IDs that must not be
  confused (`UserId` vs `OrderId`), and validated vs unvalidated data
  (`Email<Raw>` vs `Email<Verified>`).
- The associated const `C::CODE` shows one more trick: the **type** picks the
  constant at compile time.
- `PhantomData` also controls variance and drop-check behaviour. See
  [Variance, Drop Check & PhantomData](rust-variance-dropck-and-phantomdata.md).

## 4. "What are generic associated types (GATs), and why can't `Iterator` do this?"

```rust
trait LendingIterator {
    type Item<'a> where Self: 'a;
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}

struct WindowsMut<'t, T> { slice: &'t mut [T], start: usize, size: usize }

impl<'t, T> LendingIterator for WindowsMut<'t, T> {
    type Item<'a> = &'a mut [T] where Self: 'a;
    fn next<'a>(&'a mut self) -> Option<&'a mut [T]> {
        let window = self.slice[self.start..].get_mut(..self.size)?;
        self.start += 1;
        Some(window)
    }
}
```

```text
lending iterator result = [6, 9, 12, 4, 5]
```

**Answer:**

- A normal associated type, like `Iterator::Item`, is **one fixed type**.
  `next(&mut self)` returns `Option<Self::Item>`, and that type cannot
  mention the borrow of `self`.
- So an `Iterator` cannot hand out a `&mut` slice that **borrows from the
  iterator**: two items would overlap, and the items outlive the call.
  `slice::windows_mut` does not exist for this reason.
- A **GAT** is an associated type with its **own parameters**, here a
  lifetime: `Item<'a>`. Each call to `next` picks a fresh `'a`, tied to the
  `&'a mut self` borrow. The result borrows from the iterator.
- The price: you cannot use `for` loops (they need `Iterator`). You write
  `while let Some(w) = it.next()`. The windows overlap, and each is
  mutable, which `Iterator` could never allow.
- The `where Self: 'a` clause is **required**. Leave it out and you get:

```text
error: missing required bound on `Item`
 --> compile_fail/gat_missing_where.rs:3:5
  |
3 |     type Item<'a>;
  |     ^^^^^^^^^^^^^-
  |                  |
  |                  help: add the required where clause: `where Self: 'a`
  |
  = note: this bound is currently required to ensure that impls have maximum flexibility
```

- GATs are stable and used for lending iterators, **collection traits**
  (`type Iter<'a>`) and async-style traits. Their limits: a trait with a GAT is
  **not dyn compatible** (`E0038`, "because it contains generic associated
  type `Item`"), and some higher-ranked uses need workarounds. Read the standard `LendingIterator` crates (`lending-iterator`,
  `streaming-iterator`) if you need ready-made ones.

## 5. "What do `for<'a>` bounds mean on a closure or a trait?"

```rust
fn run_on_two<P>(p: &P) -> (String, String)
where
    P: for<'a> Fn(&'a str) -> &'a str,
{
    let a = String::from("alpha beta");
    let r1 = p(&a).to_string();
    let b = String::from("gamma delta");
    let r2 = p(&b).to_string();
    (r1, r2)
}
```

```text
HRTB closure: ("alpha", "gamma")
```

**Answer:**

- `for<'a>` is a **higher-ranked trait bound** (HRTB). It says "this holds for
  **every** lifetime `'a`", not for one lifetime chosen by the caller.
- Here `p` is called with **two different** borrows (`&a` and `&b`). If the
  bound named one lifetime, it could only be called with one.
- You rarely write it by hand. The compiler inserts it for `Fn(&str) -> &str`
  (elision), which is why this usually "just works". See
  [Lifetimes §7](../foundations/rust-lifetimes.md#7-what-is-a-higher-ranked-bound-fora).
- You meet it explicitly in `DeserializeOwned` (`for<'de> Deserialize<'de>`)
  and in trait methods that take generic borrowed input.

## 6. "What are `impl Trait` in a trait and `async fn` in a trait?"

```rust
trait Source {
    fn items(&self) -> impl Iterator<Item = u32>;   // return-position impl Trait in trait
}
trait Fetch {
    async fn fetch(&self, id: u32) -> String;       // async fn in trait
}
```

```text
RPITIT: evens 20 listed 6
async fn in trait: ("item-1", "item-2")
```

**Answer:**

- Both are **stable**. A trait method may return `impl Trait`. Each
  implementation returns its **own concrete type** (`Evens` returns a
  `Filter`, `Listed` returns a `Copied`). `async fn` in a trait is sugar
  for the same: it returns an anonymous `impl Future`.
- **No boxing, no allocation.** The caller sees a generic return type and
  the compiler monomorphizes. This replaced the old `async-trait` crate for
  most code.
- **Limit 1: not dyn compatible.** You cannot make `Box<dyn Fetch>`:

```text
error[E0038]: the trait `Fetch` is not dyn compatible
  --> compile_fail/async_trait_dyn.rs:14:21
   |
14 |     let _x: Box<dyn Fetch> = Box::new(A);
   |                     ^^^^^ `Fetch` is not dyn compatible
   ...
 3 |     async fn fetch(&self) -> u32;
   |              ^^^^^ ...because method `fetch` is `async`
```

- Why: each implementation returns a **different** future type of a different
  size, so there is no single vtable entry. See
  [Memory Layout §8](rust-memory-layout-and-dsts.md#8-what-does-sized-mean-and-what-is-sized).
  The workaround is the **dyn-safe wrapper**: a second trait that returns
  `Pin<Box<dyn Future>>`, with a blanket impl (see
  [§10](#10-how-do-i-use-a-trait-as-dyn-when-it-is-not-dyn-compatible)).
- **Limit 2: `Send` is not known.** In generic code the compiler cannot
  assume the future is `Send`, so spawning it on a multi-threaded runtime
  fails:

```text
error[E0277]: `impl Future<Output = u32>` cannot be sent between threads safely
...
help: `Send` can be made part of the associated future's guarantees for all implementations of `Fetch::fetch`
  |
1 + trait Fetch { fn fetch(&self) -> impl std::future::Future<Output = u32> + Send; }
```

- The fix the compiler suggests is to **write the trait as
  `fn fetch(&self) -> impl Future<Output = u32> + Send`** (you can still
  implement it with `async fn`). See
  [Async Rust Internals](../concurrency-and-async/rust-async-internals.md).

## 7. "What are const generics and associated consts?"

```rust
struct Matrix<const R: usize, const C: usize>([[i32; C]; R]);

impl<const R: usize, const C: usize> Matrix<R, C> {
    fn transpose(&self) -> Matrix<C, R> { /* ... */ }
}

trait Shape { const SIDES: u32; }
```

```text
transpose of 2x3 = Matrix([[1, 4], [2, 5], [3, 6]])
consts: triangle has 3 sides, square has 4
```

**Answer:**

- A **const generic** is a **value** (an integer, `bool`, or `char`) used as
  a type parameter. `Matrix<2, 3>` and `Matrix<3, 2>` are different types, so
  the compiler checks that a transpose really has swapped dimensions.
- It replaces "array of any length" tricks: `fn f<const N: usize>(a: [u8; N])`
  works for every `N`, and `N` is known inside the function.
- An **associated const** (`const SIDES: u32` in a trait) is a constant each
  implementor sets. Use it for per-type facts (`Currency::CODE`, `Shape::SIDES`)
  with no method call and no run-time cost.
- **Limits:** generic expressions like `[u8; N + 1]` and arbitrary types as
  const parameters are **not stable** (`generic_const_exprs`, `adt_const_params`).
  Work around by passing both numbers, or using a trait with an associated
  const.
- Since 1.89 you may write `_` to **infer** a const argument:
  `let a: [u8; _] = [1, 2, 3];`.

## 8. "What are supertraits, blanket impls and marker traits?"

```rust
trait Named { fn name(&self) -> String; }
trait Greeter: Named {                       // supertrait: Greeter requires Named
    fn greet(&self) -> String { format!("Hello, {}!", self.name()) }
}
impl<T: Display> Named for T { /* ... */ }   // blanket impl: for every Display type
impl<T: Display> Greeter for T {}

trait Plain: Copy + 'static {}               // marker trait: no methods
```

```text
Hello, 42! Hello, Ferris!
marker: u8 1 bytes, f32 4 bytes
```

**Answer:**

- A **supertrait** (`trait B: A`) means "to implement `B` you must also
  implement `A`". Inside `B` you can call `A`'s methods.
- A **blanket impl** (`impl<T: Bound> Trait for T`) implements a trait for
  **every** type that meets the bound. The standard library does this
  everywhere: every `Display` type gets `ToString`; every `I: Iterator` gets
  all the adapter methods.
- A **marker trait** has no methods. It only **states a fact** the compiler or a
  generic function can rely on: `Copy`, `Send`, `Sync`, `Sized`, `Eq`. Your
  own (`Plain`, `Validated`) work as documentation the compiler enforces.
- **Coherence** (the "one impl per type" rule) limits blanket impls. This
  does **not** compile:

```text
error[E0119]: conflicting implementations of trait `Describe` for type `i32`
  --> compile_fail/conflicting_blanket_impl.rs:14:1
   |
 8 | impl<T: Display> Describe for T {
   | ------------------------------- first implementation here
...
14 | impl Describe for i32 {
   | ^^^^^^^^^^^^^^^^^^^^^ conflicting implementation for `i32`
```

- `i32` is `Display`, so both impls apply and Rust has no way to pick the more
  specific one. That would be **specialization**, which is unstable (see
  [§9](#9-what-is-still-unstable-and-what-do-i-do-instead)).
- The **orphan rule** (you may implement a trait only if the trait or the
  type is yours) is covered in
  [Traits & Generics](../foundations/rust-traits-and-generics.md). Blanket
  impls make it stricter: adding one is a **breaking change** for a public
  trait, because downstream implementations may now conflict.

## 9. "What is still unstable, and what do I do instead?"

**Answer:**

| Feature | Status on 1.99 | Stable alternative |
|---|---|---|
| Specialization (`default fn`) | Unstable | Separate traits, an enum, or one trait method that every type implements |
| Trait aliases (`trait A = B + C;`) | Unstable | A trait with a **blanket impl** (below) |
| `generic_const_exprs` (`[T; N + 1]`) | Unstable | Pass both sizes as parameters |
| Allocator-parameterized collections | Unstable | A global allocator or an arena crate |
| `Send` bound on `async fn` in a trait via `T::fetch(..): Send` (return type notation) | Not stable | Write `-> impl Future + Send` in the trait |

Specialization and trait aliases, as the compiler reports them:

```text
error[E0658]: specialization is experimental
 --> compile_fail/specialization_unstable.rs:7:5
  = note: see issue #31844 <https://github.com/rust-lang/rust/issues/31844> for more information

error[E0658]: trait aliases are experimental
 --> compile_fail/trait_alias_unstable.rs:2:1
  = note: see issue #41517 <https://github.com/rust-lang/rust/issues/41517> for more information
```

The blanket-impl workaround for a trait alias:

```rust
trait Both: Clone + Debug {}
impl<T: Clone + Debug> Both for T {}
```

- Do **not** switch a project to nightly to get one of these. Use the stable
  alternative and revisit when the feature ships.
- Check the current state in the release notes before you write "unstable"
  in a design document: features do stabilize (GATs, `async fn` in traits,
  trait upcasting, and let chains all did in recent years).

## 10. "How do I use a trait as `dyn` when it is not dyn compatible?"

```rust
trait Plugin {
    fn run(&self, input: &str) -> String;
}
trait DynPlugin {
    fn run_dyn(&self, input: &str) -> String;
}
impl<T: Plugin> DynPlugin for T {
    fn run_dyn(&self, input: &str) -> String { self.run(input) }
}

let plugins: Vec<Box<dyn DynPlugin>> = vec![Box::new(Upper)];
```

```text
dyn wrapper: ABC
```

**Answer:**

- Make a **second, dyn-compatible trait** with the methods you need to call
  dynamically, and add a **blanket impl** from the first trait to the second.
  Any type that implements `Plugin` is now also a `dyn DynPlugin`.
- For `async fn`, the dyn trait's method returns
  `Pin<Box<dyn Future<Output = T> + Send + '_>>`. That is exactly what the
  `async-trait` and `dynosaur` crates generate for you.
- Use generics (static dispatch) by default and add the `dyn` wrapper **only
  where you need a heterogeneous collection or a plugin boundary**. See
  [Traits & Generics §2](../foundations/rust-traits-and-generics.md#2-what-is-the-difference-between-generics-and-dyn-trait).
- Related: since **1.86** you can **upcast** a trait object to its supertrait
  object, `Box<dyn Animal>` to `Box<dyn Debug>`, when `Animal: Debug`:

```text
upcast: Dog, noise woof
```

## 11. "What is `dyn Any`, and when is downcasting right?"

```rust
fn describe(v: &dyn Any) -> String {
    if let Some(i) = v.downcast_ref::<i32>() { format!("i32 {i}") }
    else if let Some(s) = v.downcast_ref::<String>() { format!("String {s:?}") }
    else { "something else".to_string() }
}
```

```text
i32 5
String "hi"
something else
```

**Answer:**

- `dyn Any` is the **one** place where Rust lets you ask a value "what type
  are you really?" at run time. It uses a `TypeId` stored in the vtable. It
  works only for `'static` types.
- Use it for **heterogeneous containers** where the set of types is open:
  plugin registries, ECS (Entity Component System) game engines, request
  extensions (`http::Extensions`), and `Box<dyn Error>` downcasting.
- **Prefer an enum** when you know all the cases: the compiler then checks
  that you handled each one. Downcasting moves that check to run time.
- It is a **smell** if you downcast often inside your own logic. That usually
  means a trait method is missing.

## 12. "What is an extension trait?"

```rust
trait StrExt {
    fn is_palindrome(&self) -> bool;
}
impl StrExt for str { /* ... */ }

"A man, a plan, a canal: Panama".is_palindrome()   // true
```

```text
true false
```

**Answer:**

- The orphan rule forbids adding **inherent** methods to a type you do not
  own. An **extension trait** is the workaround: define a trait in your crate
  and implement it for the foreign type. Importing the trait enables the
  method.
- Real examples: `Itertools` (more iterator methods), `StreamExt`,
  `FutureExt`, `tower::ServiceExt`, `Read`/`Write` helpers.
- Name it `FooExt`, keep it small, and make sure the **trait must be in
  scope** (`use my_crate::StrExt;`). Forgetting the import is the usual
  "method not found" error.
- Risk: if the standard library later adds an **inherent** method with the
  same name, that method wins and silently changes which code runs. Give
  extension methods distinctive names.

## 13. "How do AI tools help or hurt here?"

**Answer:**

- They are **good at** drafting a typestate builder or a sealed trait from a
  description, and at explaining a coherence error.
- They are **weak at** knowing what is **stable today**. Generated code that
  uses specialization, trait aliases, or `generic_const_exprs` needs
  `#![feature(...)]` and will not build on stable. **Always compile**.
- They tend to produce `#[async_trait]` where native `async fn` in traits is
  enough now. Ask for the native version, and for the `+ Send` form if the
  future must be spawned.
- They over-engineer: a typestate or GAT where a plain enum or a `Vec`
  would do. Ask "what bug does this type prevent?" and drop it if the
  answer is "none".
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 14. Interview Questions You're Likely to Get Asked

**Patterns**

- "What is typestate, and what does it cost?" — expects state encoded as a
  type, methods only in valid states, more generic code,
  [§1](#1-what-is-the-typestate-pattern).
- "How do you make a trait impossible to implement outside your crate?" —
  expects a private supertrait (sealed), and why (SemVer),
  [§2](#2-how-do-i-stop-other-code-from-implementing-my-trait).
- "What does `PhantomData` do in `Money<C>`?" — expects a zero-sized marker
  that uses the parameter,
  [§3](#3-how-do-unit-markers-with-phantomdata-prevent-unit-mix-ups).

**Features**

- "Why can't `Iterator` return overlapping `&mut` windows, and what can?" —
  expects item type cannot borrow from `self`; a GAT lending iterator,
  [§4](#4-what-are-generic-associated-types-gats-and-why-cant-iterator-do-this).
- "What is a higher-ranked trait bound?" — expects `for<'a>`: valid for every
  lifetime,
  [§5](#5-what-do-fora-bounds-mean-on-a-closure-or-a-trait).
- "Can you use `async fn` in a trait? Can you make it `dyn`?" — expects
  stable, not dyn compatible, `Send` caveat, dyn-safe wrapper,
  [§6](#6-what-are-impl-trait-in-a-trait-and-async-fn-in-a-trait).
- "What is a const generic?" — expects a value as a type parameter and the
  stable limits,
  [§7](#7-what-are-const-generics-and-associated-consts).

**Design**

- "Why can't I write both a blanket impl and a specific impl?" — expects
  coherence and the missing specialization,
  [§8](#8-what-are-supertraits-blanket-impls-and-marker-traits).
- "What would you do without trait aliases?" — expects a trait with a
  blanket impl,
  [§9](#9-what-is-still-unstable-and-what-do-i-do-instead).
- "`dyn Any` or an enum?" — expects the enum when cases are closed,
  [§11](#11-what-is-dyn-any-and-when-is-downcasting-right).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/advanced_traits.rs` — typestate, sealed trait, `Money<C>`,
  lending iterator, extension trait, `dyn Any`, a higher-ranked closure.
- `examples/advanced_traits_more.rs` — return-position `impl Trait` and
  `async fn` in traits, const generics, associated consts, marker trait,
  supertrait and blanket impl, upcasting, the dyn-safe wrapper, a
  higher-ranked closure.
- `compile_fail/sealed_trait_outside.rs`, `gat_missing_where.rs`,
  `async_trait_dyn.rs`, `async_trait_send.rs`,
  `conflicting_blanket_impl.rs`, `specialization_unstable.rs`,
  `trait_alias_unstable.rs` — one file per error quoted above.

```bash
cd code_samples/rust
cargo run --example advanced_traits
cargo run --example advanced_traits_more
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/async_trait_dyn.rs
```
