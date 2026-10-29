---
title: Rust Modules, Crates & Editions
---

# Rust Modules, Crates & Editions

Rust organizes code in **three nested layers**: a **crate** (one unit of
compilation: a library or a program), **modules** inside it (namespaces
that also control **privacy**), and **packages** (what Cargo builds and
publishes). Privacy is the core idea: **everything is private by default**,
and you choose what to expose. That default is what lets you change the
inside of a crate without breaking anyone. This page also explains
**editions** properly, because they decide which language rules a crate
uses.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**, the latest edition.
    The edition errors shown here were produced by compiling the same
    files with `--edition 2021` and `--edition 2024` on 1.99.1.

## 1. "What are packages, crates, and modules?"

**Answer:**

- A **crate** is the unit the compiler (`rustc`) builds in one run. It is
  either a **binary crate** (has `main`, produces a program) or a
  **library crate** (no `main`, produces code for others to use).
- A **package** is what Cargo manages: one `Cargo.toml`, with **one library
  crate** (`src/lib.rs`) and/or **any number of binary crates**
  (`src/main.rs`, and each file in `src/bin/`).
- A **module** (`mod`) is a **namespace inside a crate**. Modules form a
  tree rooted at the crate root (`lib.rs` or `main.rs`).
- A **workspace** groups several packages. See
  [Toolchain & Cargo §7](rust-toolchain-and-cargo.md#7-how-do-workspaces-organize-a-larger-project).
- Typical package layout:

    ```text
    my_app/
    ├── Cargo.toml
    ├── src/
    │   ├── main.rs          # binary crate root
    │   ├── lib.rs           # library crate root (optional)
    │   ├── config.rs        # `mod config;` in the crate root
    │   ├── db/
    │   │   ├── mod.rs       # or db.rs next to the db/ folder
    │   │   └── pool.rs      # `mod pool;` inside db
    │   └── bin/tool.rs      # another binary
    ├── tests/               # integration tests
    ├── examples/            # runnable examples
    └── benches/             # benchmarks
    ```

- **Files are modules.** Writing `mod config;` in the crate root tells the
  compiler to load `config.rs` (or `config/mod.rs`). Nothing is included
  unless a `mod` line says so. This is different from languages where every
  file in a folder is picked up automatically.
- Use the **modern layout** `db.rs` plus a `db/` folder for submodules,
  rather than the older `db/mod.rs` style. Both work.

## 2. "How does privacy work?"

```rust
mod bank {
    pub struct Account {
        pub owner: String,   // public
        balance: i64,        // private to `bank`
    }
    pub(crate) fn audit(a: &Account) -> String { /* ... */ }
    mod internal {
        pub(super) fn fee() -> i64 { 2 }   // visible to the parent only
    }
}
```

```text
error[E0616]: field `balance` of struct `Account` is private
  --> compile_fail/private_field.rs:14:7
   |
14 |     a.balance = 100;
   |       ^^^^^^^ private field
```

**Answer:**

- **Default is private.** An item is visible **inside the module where it is
  defined and in that module's children**, and nowhere else.
- The visibility levels:

| Keyword | Visible to |
|---|---|
| (nothing) | The current module and its descendants |
| `pub(self)` | Same as nothing |
| `pub(super)` | The parent module (and everything inside it) |
| `pub(in path)` | A named ancestor module |
| `pub(crate)` | The whole crate, not other crates |
| `pub` | Everyone who can reach the module (other crates too, if every module on the path is `pub`) |

- **Privacy is per module, not per type.** Code in the **same module** can
  touch private fields of a struct defined there. This differs from Java or
  C++, where the class is the boundary. The consequence: to hide fields, put
  the type in **its own module**.
- A struct with a **private field** cannot be built with a struct literal
  outside its module. This is the standard way to force callers through a
  **constructor that checks invariants** (the "validated newtype" idea in
  [Types, Enums & Patterns §7](rust-types-enums-and-patterns.md#7-how-do-you-design-types-so-wrong-states-cannot-exist)).
- **Enum variants** and **trait methods** are public if the enum or trait is.
- **Be stingy with `pub`.** Every `pub` item is a promise. A smaller public
  API means fewer breaking changes.

## 3. "How do `use`, paths, and re-exports work?"

**Answer:**

- A **path** names an item: `crate::bank::Account` (absolute, from the crate
  root), `self::rates::FEE` (relative, current module), `super::fee()`
  (parent module).
- **`use`** brings a name into scope so you do not type the full path:
  `use bank::Account;`. It is **a convenience, not an import of code**. The
  code is already in the crate.
- Forms:
    - `use std::collections::{HashMap, HashSet};` — several names.
    - `use std::fmt::Result as FmtResult;` — rename on import.
    - `use std::io::{self, Write};` — the module itself and one item.
    - `use crate::models::*;` — everything public. Use sparingly. It makes
      it unclear where names come from. Common in `prelude` modules and
      tests.
- **Re-exporting** with `pub use` lets you **decouple your public paths from
  your file layout**:

    ```rust
    pub use self::rates::FEE as DEFAULT_FEE;
    ```

  Callers write `bank::DEFAULT_FEE` and never learn that `rates` exists. You
  can then move code around internally without a breaking change. Most
  large libraries build a **flat public API** with `pub use`.
- Convention for imports:
    - Import **types and traits** by name (`use std::collections::HashMap`).
    - Import **functions** through their module (`use std::fs; fs::read(...)`),
      so a call shows where it comes from.
- **External crates** are referenced by name straight away: `use serde::Serialize;`.
  They are declared in `Cargo.toml`, not in code. Since the 2018 edition
  there is no `extern crate` line.
- The **prelude**: names the compiler imports into every module
  (`Option`, `Vec`, `String`, `Clone`, ...). Edition 2024 added `Future`
  and `IntoFuture` to the prelude.

## 4. "What exactly is an edition?"

**Answer:**

- A Rust **edition** is a **named set of language rules** a crate opts into
  with `edition = "2024"` in `Cargo.toml`. The four editions are 2015, 2018,
  2021, and 2024. **2024 is the latest.** There is no newer edition.
- Editions exist to make **changes that would break old code** (new
  keywords, changed rules) **without breaking it**. Old crates stay on their
  edition and **keep compiling forever**.
- Key points:
    - The edition is **per crate**. A 2015 library and a 2024 app work
      together in one program.
    - Editions differ only on the **surface** (syntax, name resolution, some
      lints and rules). They share the **same compiler back end and the same
      standard library**.
    - They arrive about **every three years**, on a Rust release (2024 came
      with Rust 1.85, in February 2025).
    - Most new features are **available in every edition**. Only changes that
      could break old code are gated.
- **Migration** is automated: `cargo fix --edition` rewrites most code, then
  you set the new `edition`. Do it one crate at a time. Run the tests
  between steps.

| Edition | Main changes (short) |
|---|---|
| 2018 | New module paths (`crate::`), `async` and `dyn` keywords, NLL borrow checker |
| 2021 | Disjoint closure captures, `IntoIterator` for arrays, new prelude traits, panic macro consistency, resolver 2 |
| 2024 | See next section |

## 5. "What changed in the 2024 edition?"

**Answer:**

- **`let` chains** in `if` and `while` (`if let Some(x) = a && x > 3`). The
  same code in a 2021 crate fails:

    ```text
    error: let chains are only allowed in Rust 2024 or later
     --> compile_fail/let_chain_edition_2021.rs:4:8
      |
    4 |     if let Some(x) = a && x > 3 {
      |        ^^^^^^^^^^^^^^^
    ```

- **Return-position `impl Trait` captures all in-scope lifetimes** by
  default, with `use<..>` to opt out. See
  [Lifetimes §8](rust-lifetimes.md#8-how-do-lifetimes-interact-with-impl-trait-and-what-changed-in-2024).
- **Temporary scope changes**:
    - Temporaries in a block's **tail expression** are dropped **before** the
      block's locals. This fixes the `RefCell::borrow()` end-of-function
      error. See
      [Ownership §4](rust-ownership-and-borrowing.md#4-when-exactly-are-values-dropped-and-in-what-order).
    - Temporaries in an **`if let`** condition are dropped **before** the
      `else` branch. This removes a source of deadlocks.
- **`unsafe` tightening**:
    - `extern` blocks must be written **`unsafe extern "C" { ... }`**, and
      items inside can be marked `safe`.
    - Attributes such as `#[no_mangle]` become **`#[unsafe(no_mangle)]`**.
    - `unsafe_op_in_unsafe_fn` **warns**: inside an `unsafe fn`, each unsafe
      operation needs its own `unsafe { }` block.
    - **References to `static mut` are denied** (error), as shown here:

        ```text
        error: creating a mutable reference to mutable static
         --> compile_fail/static_mut_ref_edition_2024.rs:5:17
          |
        5 |         let r = &mut COUNTER;
          |                 ^^^^^^^^^^^^ mutable reference to mutable static
        help: use `&raw mut` instead to create a raw pointer
        ```

- **Never type fallback** now falls back to `!` instead of `()`, which makes
  some hidden bugs visible.
- **`gen` is a reserved keyword** (for future generator blocks). Using it as
  a name needs `r#gen`:

    ```text
    error: expected identifier, found reserved keyword `gen`
    help: escape `gen` to use it as an identifier
    3 |     let r#gen = 5;
    ```

- **Match ergonomics reservations**: writing `ref`, `mut`, or `&` inside a
  pattern that already uses default binding modes is an error, to leave
  room for changing the rules.
- **Macro fragment specifier** `expr` also matches `const { }` and `_`
  expressions (`expr_2021` keeps the old behaviour).
- **Standard library**: `Box<[T]>` iterates by value, `Future` and
  `IntoFuture` join the prelude, and some functions (`std::env::set_var`)
  become `unsafe`.
- **Cargo**: resolver `"3"` (MSRV-aware) is the default, and
  `rust-version` becomes meaningful to dependency resolution.
- Read the full list in the
  [Edition Guide](https://doc.rust-lang.org/edition-guide/rust-2024/index.html).
  The next page of this track that builds on it is
  [Modern Rust: 2024 to 1.99](../mastery/modern-rust-2024-to-1-99.md).

## 6. "How do you structure a real crate's modules?"

**Answer:**

- **Group by feature or layer**, not by kind. `users/`, `orders/`, `billing/`
  usually age better than `models/`, `controllers/`, `utils/`.
- **Keep the crate root small.** `lib.rs` should declare modules, re-export
  the public API with `pub use`, and carry crate-level documentation.
- **Make the public API flat and intentional.** Hide the layout with `pub
  use`. Mark internals `pub(crate)`.
- **Split into several crates** (a workspace) when a part has a different
  rate of change, different dependencies, or needs a separate boundary.
  `rustc` compiles a crate as a unit, so a small crate rebuilds faster than
  a large one. See
  [Project Architecture & API Guidelines](../production/rust-project-architecture-and-api-design.md).
- **Avoid a `utils` or `common` junk drawer.** Name modules by what they
  do.
- **A `prelude` module** (`pub mod prelude { pub use ...; }`) lets users
  import your main traits and types with one `use my_crate::prelude::*;`.
- **Modules may depend on each other in a cycle** inside one crate, but
  **crates may not**. Keep module dependencies tidy anyway.
- **Conditional compilation**: `#[cfg(feature = "x")]`,
  `#[cfg(target_os = "linux")]`, `#[cfg(test)]`, and `cfg!(...)` in
  expressions. Since Rust 1.95 there is also the `cfg_select!` macro, a
  `match`-like way to pick code by `cfg`.

## 7. "How do AI tools help or hurt here?"

**Answer:**

- Good for: proposing a module layout, writing `pub use` facades, and
  running a mechanical edition migration (with `cargo fix` doing the
  safe part).
- They often make **everything `pub`**, generate a `utils.rs` drawer, use
  `extern crate`, or write **2018-era paths**. Tell them the edition.
- They may also write `unsafe extern` incorrectly or miss the 2024 `unsafe`
  attribute syntax. Check with the compiler and the Edition Guide.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 8. Interview Questions You're Likely to Get Asked

**Structure**

- "What is the difference between a package, a crate, and a module?" —
  expects Cargo unit, compilation unit, namespace,
  [§1](#1-what-are-packages-crates-and-modules).
- "Does a new `.rs` file become part of the crate automatically?" —
  expects no: a `mod` line is needed,
  [§1](#1-what-are-packages-crates-and-modules).

**Privacy**

- "What is the default visibility, and what is `pub(crate)`?" — expects
  private by default; whole-crate visibility,
  [§2](#2-how-does-privacy-work).
- "Is Rust privacy per type or per module? What follows from that?" —
  expects per module, so put a type in its own module to hide its fields,
  [§2](#2-how-does-privacy-work).
- "Why re-export with `pub use`?" — expects decoupling public paths from
  file layout, to keep the API stable,
  [§3](#3-how-do-use-paths-and-re-exports-work).

**Editions**

- "What is an edition? Can crates of different editions be linked?" —
  expects per-crate rules, with full interoperability,
  [§4](#4-what-exactly-is-an-edition).
- "Name three changes in the 2024 edition." — expects let chains, RPIT
  lifetime capture, tail-expression temporaries, `unsafe extern`, `static
  mut` references denied, `gen` reserved,
  [§5](#5-what-changed-in-the-2024-edition).
- "How do you migrate a crate to a new edition?" — expects `cargo fix
  --edition`, then change the key, crate by crate,
  [§4](#4-what-exactly-is-an-edition).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/modules_visibility.rs` — nested modules, `pub`, `pub(crate)`,
  `pub(super)`, a private field, and a `pub use` re-export.
- `compile_fail/private_field.rs` — the privacy error shown above.
- `compile_fail/let_chain_edition_2021.rs` — compile with `--edition 2021`
  to see the let chain error.
- `compile_fail/gen_keyword_edition_2024.rs`,
  `compile_fail/static_mut_ref_edition_2024.rs` — two 2024 errors.

```bash
cd code_samples/rust
cargo run --example modules_visibility
rustc --edition 2021 --emit=metadata -o /tmp/out compile_fail/let_chain_edition_2021.rs
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/static_mut_ref_edition_2024.rs
```
