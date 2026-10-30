---
title: Project Architecture and API Design
---

# Project Architecture and API Design

Two questions decide whether a Rust codebase stays pleasant at 10,000
lines and at 200,000. **Architecture**: where do the boundaries go (crates,
modules, which code may know about which)? **API design**: what does the
public surface look like, so users can use it correctly, and **you** can
change it later without breaking them? Rust gives unusually strong tools
for both: privacy, the type system, `#[non_exhaustive]`, sealed traits, and
tools that check semantic versioning (SemVer) for you.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. The workspace
    sample was built and tested on 1.99.1. SemVer rules are from the Cargo
    reference's "SemVer Compatibility" chapter and the Rust API
    Guidelines checklist (both read for this page). `cargo-semver-checks`
    0.51.0 was run on a real before/after pair of crates.

## 1. "How do I lay out a Rust project?"

```text
arch_demo/
├── Cargo.toml                  # [workspace] and shared versions
└── crates/
    ├── shop-domain/            # rules + ports (traits); depends only on thiserror
    ├── shop-adapters/          # implements the ports (database, files, HTTP clients)
    └── shop-app/               # the binary: wires adapters into the domain
```

```toml
# Cargo.toml (workspace root)
[workspace]
resolver = "3"
members = ["crates/*"]

[workspace.package]
edition = "2024"
rust-version = "1.99"
publish = false

[workspace.dependencies]
thiserror = "2"
shop-domain = { path = "crates/shop-domain" }
shop-adapters = { path = "crates/shop-adapters" }
```

**Answer:**

- A **workspace** is several crates built together, sharing one
  `Cargo.lock` and one `target/` folder. (Basics:
  [Toolchain & Cargo §7](../foundations/rust-toolchain-and-cargo.md#7-how-do-workspaces-organize-a-larger-project).)
- **`[workspace.package]` and `[workspace.dependencies]`** put the edition,
  `rust-version` and dependency versions in **one place**. Members write
  `edition.workspace = true` and `thiserror.workspace = true`. Upgrading a
  dependency becomes a one-line change.
- **The dependency direction is the architecture.** Verified with
  `cargo tree -p shop-domain --depth 1`: the domain crate depends on
  **only** `thiserror`. The compiler enforces that the domain cannot call
  the database, because the crate is not in its dependency list. A plain
  module boundary can be bypassed with one `use`; a crate boundary cannot.
- Start with **one crate and modules**. Split into a workspace when you
  have a real reason (see §2). Splitting early adds ceremony and no
  value.
- Typical shape for a service: a `domain` (or `core`) library, one or more
  adapter libraries, and thin `bin` crates (server, CLI, worker) that only
  assemble things.

## 2. "When should I split code into another crate?"

**Answer:**

- **Good reasons:**
    - **Enforce a boundary** (the domain must not see the database).
    - **Share code** between several binaries (a server and a CLI).
    - **Compile time:** the crate is the unit of compilation, and Cargo
      rebuilds only crates that changed (and their dependents). A big crate
      that changes constantly belongs near the **top** of the dependency
      graph, with stable code below it. (See
      [How the Compiler Works](../performance-and-internals/rustc-how-the-compiler-works.md).)
    - **Different release or license:** a crate you will publish.
    - **Procedural macros** must be their own crate (see
      [Macros](../advanced-language/rust-macros.md)).
- **Bad reasons:** "it looks tidier," or "microservices in one repo." Each
  crate adds a `Cargo.toml`, a public API to keep stable, and friction
  when a change spans two crates.
- **The orphan rule** limits where trait impls can live: you can implement
  a trait for a type only if your crate owns the trait or the type. Splitting
  a type from its trait impls into different crates can make that
  impossible. Keep a type and its core trait impls together.
- Rule of thumb: **modules for organization, crates for boundaries.**
  (Modules: [Modules, Crates & Editions §6](../foundations/rust-modules-crates-and-editions.md#6-how-do-you-structure-a-real-crates-modules).)

## 3. "How do I keep the core free of databases and frameworks?"

```rust
// shop-domain: the core defines what it NEEDS (ports) as traits...
pub trait Inventory {
    fn reserve(&mut self, sku: &str, qty: Quantity) -> Result<(), OrderError>;
}
pub trait OrderLog {
    fn record(&mut self, order: &Order) -> Result<(), OrderError>;
}

// ...and the use case is generic over them.
pub fn place_order<I: Inventory, L: OrderLog>(
    inv: &mut I, log: &mut L, sku: &str, qty: u32,
) -> Result<Order, OrderError> {
    let qty = Quantity::new(qty)?;   // validated type: an invalid quantity cannot exist
    inv.reserve(sku, qty)?;
    let order = Order { sku: sku.to_owned(), qty };
    log.record(&order)?;
    Ok(order)
}
```

```rust
// shop-app (composition root): the only place that picks real adapters.
let mut inv = MemoryInventory::with_stock(&[("pen", 5)]);
let mut log = StdoutLog;
place_order(&mut inv, &mut log, "pen", 3)
```

Real output of `cargo run -p shop-app` (three orders: 3 pens, 3 more, and
quantity 0):

```text
recorded: pen x3
ok: Order { sku: "pen", qty: Quantity(3) }
sorry, pen is out of stock
error: quantity 0 is not between 1 and 100
```

**Answer:**

- This is **hexagonal architecture**, also called ports and adapters.
  The **core** holds the rules. It declares **ports**: traits describing
  what it needs from the outside world. **Adapters** implement the ports
  with real technology. The core never imports an adapter.
- **Why it works well in Rust:**
    - A trait is the port. A generic function (`I: Inventory`) is
      resolved at **compile time**, so there is no runtime cost (see
      [Traits & Generics §2](../foundations/rust-traits-and-generics.md#2-what-is-the-difference-between-generics-and-dyn-trait)).
      Use `dyn Trait` instead when you need to pick the adapter at
      runtime or want less code size.
    - Tests pass in-memory fakes (the domain crate's test does exactly
      this and runs with no database; it passes).
    - The database crate can change (or be swapped for another) without
      touching the rules.
- **Parse, don't validate.** `Quantity::new` is the only way to build a
  `Quantity`, because its field is private. Every function that takes a
  `Quantity` can trust it. Trying to bypass it from another crate fails:

```text
error[E0423]: cannot initialize a tuple struct which contains private fields
 --> crates/shop-app/src/main.rs:5:14
  |
5 |     let _q = Quantity(0);
  |              ^^^^^^^^
note: constructor is not visible here due to private fields
```

- **Do not over-do it.** A trait for every struct, "just in case," is noise.
  Add a port only where you really have (or will test with) two
  implementations: databases, clocks, HTTP clients, queues, the file system.
- Keep **async** out of the core when you can; make the core pure logic
  and let the edges do I/O (the domain above is plain synchronous code).
- The database side of this idea is in [Databases §8](rust-databases.md#8-how-should-i-structure-database-code).

## 4. "What are the main rules of good API design in Rust?"

**Answer:**

- The **Rust API Guidelines** are an official checklist from the library
  team (repository `rust-lang/api-guidelines`). The groups and the rules
  that matter most:

| Group | Rule (checklist id) | In practice |
|---|---|---|
| Naming | Conversions use `as_`, `to_`, `into_` (C-CONV) | `as_` is a cheap borrow, `to_` is an expensive copy, `into_` takes ownership |
| Naming | Getters do not use `get_` (C-GETTER) | `fn name(&self)` not `fn get_name(&self)` |
| Interop | Types eagerly implement common traits (C-COMMON-TRAITS) | `Debug`, `Clone`, `PartialEq`, `Eq`, `Hash`, `Default`, `Display` where they make sense |
| Interop | Conversions use `From`, `AsRef`, `AsMut` (C-CONV-TRAITS) | Implement `From<A> for B`, not a custom `from_a` function |
| Interop | Types are `Send` and `Sync` where possible (C-SEND-SYNC) | Users move your types between threads |
| Interop | Error types are meaningful (C-GOOD-ERR) | See [Error Handling §4](../foundations/rust-error-handling.md#4-what-is-the-error-trait-and-what-should-an-error-type-look-like) |
| Predictability | Constructors are static inherent methods (C-CTOR) | `Type::new(..)` |
| Flexibility | Minimize assumptions about parameters with generics (C-GENERIC) | Take `impl AsRef<str>` or `&str`, not `&String` |
| Flexibility | Caller decides where to copy (C-CALLER-CONTROL) | Take `&[T]` or `impl IntoIterator`, not `Vec<T>`, unless you need ownership |
| Type safety | Newtypes provide static distinctions (C-NEWTYPE) | `UserId(u64)` and `OrderId(u64)` cannot be mixed up |
| Type safety | Arguments convey meaning through types, not `bool` (C-CUSTOM-TYPE) | `Mode::Fast`, not `run(true)` |
| Type safety | Builders construct complex values (C-BUILDER) | See the typestate builder in [Advanced Traits](../advanced-language/rust-advanced-traits-and-type-level-design.md) |
| Dependability | Functions validate their arguments (C-VALIDATE) | Return a `Result` or use a validated type |
| Debuggability | All public types implement `Debug` (C-DEBUG) | Add `#[derive(Debug)]` |
| Future proofing | Sealed traits (C-SEALED); structs have private fields (C-STRUCT-PRIVATE) | Next section |

- A good **public function** is hard to misuse: the types make invalid
  calls impossible or obvious, and the docs have `# Errors`, `# Panics` and
  `# Safety` sections where they apply (C-FAILURE).
- Write the **usage code first**. If the example you wish a user could
  write is awkward, the API is wrong.

## 5. "What changes break my users? How do I keep SemVer?"

**Answer:**

- **SemVer** (Semantic Versioning): `MAJOR.MINOR.PATCH`. Breaking changes
  need a new MAJOR (for `0.y.z`, a new `y`). Cargo trusts it: `serde = "1"`
  means "any 1.x, I promise it compiles."
- In Rust, what counts as breaking is **wider than most people expect**.
  From the Cargo reference:

| Change | Category |
|---|---|
| Rename, move or remove a public item | **Major** |
| Add a new public item | Minor |
| Add a public field to a struct that has no private field | **Major** (existing struct literals stop compiling) |
| Add a private field when all fields are public | **Major** |
| Add a private field when one already exists | Minor |
| Add a variant to an enum **without** `#[non_exhaustive]` | **Major** (users' `match` becomes non-exhaustive) |
| Add `#[non_exhaustive]` to an existing enum or struct | **Major** |
| Add a non-default trait item, or change a trait item's signature | **Major** |
| Add a trait item **with** a default | Possibly breaking (name clashes) |
| Tighten generic bounds | **Major** |
| Loosen generic bounds | Minor |
| Add or remove a function parameter | **Major** |
| Make an `unsafe` function safe | Minor |
| Raise the minimum Rust version (`rust-version`) | Possibly breaking (the reference recommends treating it as minor) |
| Add a Cargo feature | Minor |
| Remove a Cargo feature | **Major** |

- **Design to leave room.** Three tools, all enforced by the compiler:
    - **Private fields.** Users can only use constructors and methods, so
      you can add fields freely. The sample's `Quantity` has one.
    - **`#[non_exhaustive]`** on public enums and structs. You can add
      variants later. Users must write a `_` arm. The sample's
      `OrderError` uses it, and without the wildcard a user crate fails:

```text
error[E0004]: non-exhaustive patterns: `_` not covered
 --> crates/shop-app/src/main.rs:7:11
  |
7 |     match e {
  |           ^ pattern `_` not covered
  = note: `OrderError` is marked as non-exhaustive, so a wildcard `_` is necessary to match exhaustively
```

      (Inside the crate that defines the enum, the attribute has no effect
      on `match`: only other crates must write the wildcard.)
    - **Sealed traits**, so only your crate can implement a public trait
      and you can add methods safely. The pattern is in
      [Advanced Traits](../advanced-language/rust-advanced-traits-and-type-level-design.md).
- **Let a tool check.** `cargo semver-checks` compares your crate with the
  last release (or any baseline) and lists breaking changes. A real run
  on a `v1` and a `v2` of a small crate, where `v2` added a field to a
  public struct, added a parameter to a function, and removed a function:

```text
--- failure constructible_struct_adds_field: struct exhaustively constructible through public API adds field ---
  field Config.retries ... lib.rs:1
--- failure function_missing: pub fn removed or renamed ---
  function demo_lib::old_helper, previously in file ... lib.rs:3
--- failure function_parameter_count_changed: pub fn parameter count changed ---
  demo_lib::connect now takes 2 parameters instead of 1 ... lib.rs:2
     Summary semver requires new major version: 3 major and 0 minor checks failed
```

  It reported 202 checks, 3 failed. Run it in CI before every release
  (see [CI/CD & Supply Chain](rust-ci-cd-and-supply-chain.md)). It does not
  catch **everything** (behavior changes, performance, and some type-level
  changes are not detected), so it supports review, not replaces it.
- **Re-exports are public API.** If your signature exposes a type from
  another crate (`pub fn f() -> serde_json::Value`), that crate's major
  version is now part of **your** API. Prefer your own types at the
  boundary, or re-export the dependency (`pub use serde_json;`) so users
  get the same version.

## 6. "Where do error boundaries go?"

**Answer:**

- A **boundary** is where one layer hands control to another: the web
  layer, the domain, the database adapter. At each boundary, **convert**
  errors to the receiving layer's own type.
- A common layout:
    - **Domain:** a typed enum (`OrderError`) with meaning in business
      terms (`OutOfStock`, `BadQuantity`). Built with `thiserror`.
    - **Adapters:** map technology errors in (a unique-violation to
      `AlreadyExists`, a lost connection to `Storage(msg)`), so the domain
      never mentions `sqlx` or PostgreSQL.
    - **Edge (HTTP, CLI):** map domain errors out (to status codes or exit
      codes) and log the details (see
      [Web Services with Axum §4](rust-web-services-with-axum.md#4-how-do-i-return-errors-cleanly)).
- **Libraries** return typed errors, so callers can match. **Applications**
  may use `anyhow` at the very top for "log it and exit." (Detail:
  [Error Handling §5](../foundations/rust-error-handling.md#5-when-do-you-use-thiserror-and-when-anyhow).)
- Do not put a dependency's error type in your public enum as a public
  field; that makes the dependency part of your API (§5). Store a message
  or a boxed `dyn Error` source instead.

## 7. "How should I use feature flags?"

**Answer:**

- A **feature** is a named, optional part of a crate (extra
  dependencies, extra code). Users turn features on in their
  `Cargo.toml`. (How they work:
  [Toolchain & Cargo §6](../foundations/rust-toolchain-and-cargo.md#6-how-do-features-work-and-what-goes-wrong-with-them).)
- **Features must be additive.** Cargo **unifies** features: if two
  crates in a build depend on yours with different features, your crate is
  built **once** with the union. A feature that removes or changes
  behavior will break someone you never see. Never write a `no-x`
  feature or a feature that picks one of two mutually exclusive
  behaviors.
- Per the SemVer table (§5): adding a feature is minor; **removing one is
  major**, so every public feature name is a promise.
- Name features after what they add (`serde`, `tokio`, `tls`), not
  placeholder words (guideline C-FEATURE).
- Keep `default` small. A user can opt out of defaults with
  `default-features = false`, but then they must list what they need.
- **Test combinations.** CI should at least build with `--no-default-features`
  and `--all-features`. Use `cargo hack --feature-powerset` for a stricter
  check on small crates (the number of combinations grows quickly).

## 8. "What is an MSRV policy, and what should mine be?"

**Answer:**

- **MSRV** is the **M**inimum **S**upported **R**ust **V**ersion: the oldest
  compiler your crate promises to build with. You declare it in
  `Cargo.toml`: `rust-version = "1.99"` (the sample workspace does).
- Since the Cargo resolver version `"3"` (default in the 2024 edition),
  Cargo prefers dependency versions whose own `rust-version` fits yours.
  That is what makes a conservative MSRV workable.
- **Choose a written policy** and put it in the README. Common ones:
    - **Latest stable only:** simplest, fine for applications you deploy
      yourself. This site's samples do this.
    - **Latest stable minus N releases** (for example the last 4, about 6
      months): common for libraries, as the Cargo reference notes.
    - **A fixed old version** (for systems that update slowly): costs you
      new language and library features.
- **Test your MSRV in CI** with a job that installs exactly that
  toolchain and runs `cargo check` (the example workflow in
  [CI/CD & Supply Chain](rust-ci-cd-and-supply-chain.md) does).
- The Cargo reference treats raising the MSRV as a possibly-breaking
  change and recommends handling it as a **minor** bump, not major. State
  your policy so users know what to expect.

## 9. "How do I document and deprecate?"

```rust
#[deprecated(since = "1.2.0", note = "use `Client::connect_with` instead")]
pub fn connect(&self) {}
```

A caller then sees (real compiler output):

```text
warning: use of deprecated method `Client::connect`: use `Client::connect_with` instead
 --> /tmp/dep.rs:7:20
  |
7 | fn main() { Client.connect(); }
  |                    ^^^^^^^
  = note: `#[warn(deprecated)]` on by default
```

**Answer:**

- **Deprecate, wait one or more minor releases, then remove in the next
  major.** The attribute gives users a compiler warning with your message
  and does not break their build.
- Documentation checklist (from the API Guidelines): crate-level docs
  with an example (C-CRATE-DOC), an example on public items (C-EXAMPLE)
  that uses `?` and not `unwrap` (C-QUESTION-MARK), `# Errors` and
  `# Panics` sections (C-FAILURE), full `Cargo.toml` metadata
  (C-METADATA), and release notes for every significant change
  (C-RELNOTES). Examples are doc tests, so they stay correct (see
  [Testing & Documentation §4](../foundations/rust-testing-and-documentation.md#4-what-are-doc-tests-and-why-do-they-matter)).
- Keep a `CHANGELOG.md`. Write it for **users** ("`connect` is deprecated,
  use `connect_with`"), not as a commit list.
- Use `#[doc(hidden)]` only for items that must be public (macros need
  them) but are not API; and remember hidden items can still be depended
  on by someone.

## 10. "How do AI tools help or hurt with architecture and API design?"

**Answer:**

- Good for: drafting trait definitions, writing the fake adapters for
  tests, producing a first `CHANGELOG`, and explaining a `semver-checks`
  failure.
- They add a trait (and a `Box<dyn Trait>`) for every struct, and split
  into many crates, because "clean architecture" is in their training
  data. Ask: "which of these abstractions has a second implementation?"
- They make fields `pub` for convenience, and forget `#[non_exhaustive]`,
  so your first release locks in a fragile API. Review every `pub`.
- They return `anyhow::Result` from library functions. See §6.
- They do not know your SemVer promises. After an AI-assisted refactor,
  run `cargo semver-checks` and read its output yourself.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Architecture**

- "How do you structure a Rust service?" — expects a core crate with
  ports, adapter crates, thin binaries, the dependency direction,
  [§1](#1-how-do-i-lay-out-a-rust-project),
  [§3](#3-how-do-i-keep-the-core-free-of-databases-and-frameworks).
- "When do you split into crates?" — expects boundary, sharing, compile
  time, publishing, macros; not tidiness,
  [§2](#2-when-should-i-split-code-into-another-crate).
- "How do you make the database replaceable?" — expects a trait defined by
  the core, generics or `dyn`, in-memory fakes,
  [§3](#3-how-do-i-keep-the-core-free-of-databases-and-frameworks).

**API design**

- "Name some API guidelines." — expects `as_/to_/into_`, no `get_`,
  `From` over custom converters, newtypes, builders, eager derives,
  [§4](#4-what-are-the-main-rules-of-good-api-design-in-rust).
- "What is `#[non_exhaustive]` for?" — expects adding variants or fields
  without a breaking change; users need a wildcard arm,
  [§5](#5-what-changes-break-my-users-how-do-i-keep-semver).
- "Is adding a variant to a public enum breaking?" — expects yes unless
  `#[non_exhaustive]`,
  [§5](#5-what-changes-break-my-users-how-do-i-keep-semver).
- "What is a sealed trait?" — expects a public trait that outsiders cannot
  implement, so adding methods is safe,
  [§5](#5-what-changes-break-my-users-how-do-i-keep-semver).

**Releases**

- "What does `cargo semver-checks` do, and what can it not do?" —
  expects API diff against a baseline, not behavior,
  [§5](#5-what-changes-break-my-users-how-do-i-keep-semver).
- "Why must features be additive?" — expects feature unification,
  [§7](#7-how-should-i-use-feature-flags).
- "What is your MSRV policy?" — expects a stated policy, a CI job, the
  resolver `"3"` behavior,
  [§8](#8-what-is-an-msrv-policy-and-what-should-mine-be).

---

## Code Samples

Under `code_samples/rust/` (Rust 1.99.1).

- `arch_demo/` — a Cargo workspace with three crates: `shop-domain`
  (rules, ports, `Quantity`, `#[non_exhaustive] OrderError`, a unit test),
  `shop-adapters`, and `shop-app`.
- `arch_demo/compile_fail/non_exhaustive_match.rs` and
  `arch_demo/compile_fail/private_field.rs` — the two failing files whose
  error text is quoted above. To check one, copy it over
  `crates/shop-app/src/main.rs`, run `cargo build -p shop-app`, then
  restore the original.
- `semver_demo/v1` and `semver_demo/v2` — two versions of a small crate for
  `cargo semver-checks`.

```bash
cd code_samples/rust/arch_demo
cargo test                       # the domain test uses in-memory fakes
cargo run -p shop-app
cargo tree -p shop-domain --depth 1      # only thiserror

cargo install cargo-semver-checks --locked
cd ../semver_demo/v2
cargo semver-checks --baseline-root ../v1
```
