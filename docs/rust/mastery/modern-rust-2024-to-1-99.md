---
title: "Modern Rust: 2024 Edition to 1.99"
---

# Modern Rust: 2024 Edition to 1.99

Rust ships a new **stable version every six weeks**, and each one adds
small, backward-compatible improvements. This page covers the 15 releases
from **1.85** (the one that shipped the 2024 edition) to **1.99**, grouped
by **theme** instead of by date, so you can see which old habits have a
better replacement today. Every example here lives in one runnable file,
and every item was checked against the official release notes
(`RELEASES.md` in the Rust repository).

!!! note "Version"
    Written for **Rust 1.99.1** (released 2026-10-15) and the **2024
    edition**. Release dates come from `RELEASES.md`: 1.85 on 2025-02-20,
    1.99 on 2026-10-01. All examples compiled and ran on 1.99.1. If a newer
    stable exists when you read this, check its release notes first.

## 1. "How does Rust versioning work, and how do you keep up?"

**Answer:**

- **Core idea:** a new version never breaks working code. Breaking changes
  are held back for an **edition**, which you opt into per crate.
- A **version** (1.99) is the compiler and standard library. A new one comes
  every **6 weeks**.
- An **edition** (2015, 2018, 2021, 2024) is a language dialect chosen in
  `Cargo.toml`. Editions interoperate: a 2024 crate can depend on a 2015
  crate. See [Toolchain & Cargo §2](../foundations/rust-toolchain-and-cargo.md#2-what-is-an-edition-and-how-is-it-different-from-a-version).
- **MSRV** (Minimum Supported Rust Version) is the oldest compiler your crate
  promises to build with. Set it with `rust-version` in `Cargo.toml`. Cargo
  now resolves dependencies with it in mind (see
  [§9](#9-what-changed-in-cargo-and-the-toolchain)).
- To keep up, read the **release notes** each time (a 5-minute habit). Look at
  three headings: **Language**, **Stabilized APIs**, **Compatibility Notes**.
- `cargo fix --edition` does the mechanical work of moving to a new edition.
- Features land as **nightly-only** first, then stabilize. A `#![feature(...)]`
  gate means "unstable": do not use it in production.

## 2. "What new control-flow and pattern features exist?"

```rust
// let chains (1.88, 2024 edition): mix `let` and booleans with &&
if let Ok(n) = s.parse::<i32>()
    && n > 10
    && let Some(sq) = n.checked_mul(n)
{
    println!("{sq}");
}

// `if let` guard (1.95): bind and test inside a match arm
match msg {
    Msg::Num(n) if let Some(d) = n.checked_sub(5) && d > 0 => { /* ... */ }
    _ => {}
}

std::assert_matches!(result, Ok(n) if n > 3); // 1.96
```

**Answer:**

- **Let chains (1.88):** flatten "pyramid of `if let`" code into one condition.
  They work in **edition 2024 only**. In 2021 the compiler says:

```text
error: let chains are only allowed in Rust 2024 or later
 --> compile_fail/let_chain_2021.rs:5:8
```

- **`if let` guards (1.95):** a `match` arm guard can now contain `if let`, so
  you stop writing a nested `match` inside an arm just to test a second
  pattern. The old lint `irrefutable_let_patterns` stopped complaining about
  let chains in the same release.
- **`assert_matches!` (1.96):** an assertion for patterns. Use it as
  `std::assert_matches!` (the macro is not in the prelude). It prints the value
  on failure, which `assert!(matches!(...))` does not.
- **`cfg_select!` (1.95):** a `match` on configuration, replacing the
  `cfg-if` crate: `std::cfg_select! { unix => "unix", _ => "other" }`.
- **`#[cfg(true)]` and `#[cfg(false)]` (1.88):** boolean literals are valid
  `cfg` predicates.
- **Pattern-binding drop order (1.91):** bindings are now dropped in the order
  they are written. This was previously unspecified in edge cases.
- Background: [Types, Enums & Patterns §6](../foundations/rust-types-enums-and-patterns.md#6-what-are-let-chains-and-if-let-guards-and-what-do-they-replace).

## 3. "What changed for async, closures, and traits?"

```rust
async fn apply_async(f: impl AsyncFn(i32) -> i32, x: i32) -> i32 { f(x).await }
let offset = 10;
let r = block_on(apply_async(async |x| x + offset, 5)); // 15

let animal: Box<dyn Animal> = dog_box; // Box<dyn Dog> where Dog: Animal (1.86)
```

**Answer:**

- **Async closures (1.85):** `async |x| ...` is a closure that returns a
  future **and may borrow from its own captured state**. The old workaround,
  `|x| async move { ... }`, could not lend its captures to the future it
  returned. `AsyncFn`, `AsyncFnMut` and `AsyncFnOnce` are in the prelude in
  every edition.
- **Trait object upcasting (1.86):** a `Box<dyn Sub>` converts to
  `Box<dyn Super>` when `Sub: Super`. Before, you needed a helper method like
  `fn as_super(&self) -> &dyn Super`.
- **Precise capturing in traits (1.87):** `-> impl Iterator<Item = u32> + use<'a>`
  now works for methods inside traits. In the 2024 edition, return-position
  `impl Trait` captures **all** in-scope lifetimes by default, so `use<..>`
  is how you **opt out**. In the **trait declaration** you must list `Self`
  too (`use<'a, Self>`); the compiler rejects `use<'a>` there, and rejects
  `Self` inside the impl. The sample shows both compiling.
  See [Lifetimes §8](../foundations/rust-lifetimes.md#8-how-do-lifetimes-interact-with-impl-trait-and-what-changed-in-2024).
- **`Waker::noop` (1.85):** a waker that does nothing. It makes tiny test
  executors easy (see the sample's `block_on`).
- **`#[diagnostic::do_not_recommend]` (1.85):** library authors can stop the
  compiler from suggesting a confusing blanket impl in error messages.
- **Safe `#[target_feature]` functions (1.86):** a function can require a CPU
  feature without being `unsafe` to define.
- **Still true:** `async fn` in traits works, but a trait using it is **not
  dyn compatible**. Use generics, or `Box<dyn Future>` through a helper.
  Details in [Traits & Generics §3](../foundations/rust-traits-and-generics.md#3-what-does-it-mean-that-a-trait-is-dyn-compatible).

## 4. "What changed in unsafe and low-level Rust?"

**Answer:**

- **C-variadic functions (1.99):** you can now **define** a function with
  `...` in Rust, not just declare it. Read arguments with
  `VaList::next_arg::<T>()`:

```rust
unsafe extern "C" fn sum_ints(count: i32, mut args: ...) -> i32 {
    let mut total = 0;
    for _ in 0..count {
        total += unsafe { args.next_arg::<i32>() };
    }
    total
}
// sum_ints(3, 10, 20, 30) == 60
```

- **Naked functions (1.88):** `#[unsafe(naked)]` gives full control over the
  assembly, with no compiler prologue or epilogue. 1.99 also allows a naked
  function to define a C-variadic function.
- **Volatile access to non-Rust memory (1.90):** allowed, including address 0.
  This matters for embedded and memory-mapped hardware.
- **`UnsafeCell` guarantee (1.99):** its contents may be reached **without**
  calling `get`. The `invalid_reference_casting` lint was adjusted.
- **`MaybeUninit` is documented (1.92):** its representation and validity are
  now written down. 1.95 added many `From`/`AsRef` conversions for
  `MaybeUninit<[T; N]>`.
- **New pointer and layout APIs:** `Vec::into_parts` / `from_parts` (1.99),
  `Box::into_non_null` / `from_non_null` (1.99), `Box::new_zeroed` (1.92),
  `size_of_val_raw` / `align_of_val_raw` (1.99), `NonNull::with_exposed_provenance`
  (1.89), `Layout::repeat` (1.95).
- **Lints that now fail or warn:**

| Lint | Level | Since | Catches |
|---|---|---|---|
| `dangerous_implicit_autorefs` | deny | 1.89 | an implicit `&` created when you use `*raw_ptr` |
| `dangling_pointers_from_locals` | warn | 1.91 | returning a raw pointer to a local |
| `integer_to_ptr_transmutes` | warn | 1.91 | `transmute` from an integer to a pointer |
| `deref_nullptr` | deny | 1.93 | dereferencing a null pointer |
| `invalid_runtime_symbol_definitions` | deny | 1.98 | defining `memcmp`, `strlen`, ... yourself |

- Background: the Unsafe & Miri and FFI pages cover how to use these safely
  (see [Unsafe Rust & Miri](../advanced-language/rust-unsafe-and-miri.md) and
  [FFI & C Interop](../advanced-language/rust-ffi-and-c-interop.md)).

## 5. "Which new collection and slice APIs replace old workarounds?"

```rust
let mut v: Vec<i32> = (1..=8).collect();
let evens: Vec<i32> = v.extract_if(.., |x| *x % 2 == 0).collect(); // 1.87
if let Ok([a, b]) = v.get_disjoint_mut([0, 3]) { std::mem::swap(a, b); } // 1.86
*v.push_mut(2) += 40; // 1.95: push and get &mut to the new item
let diffs: Vec<i32> = [1, 2, 4].array_windows().map(|[a, b]| b - a).collect(); // 1.94
```

**Answer:**

| API | Since | Replaces |
|---|---|---|
| `Vec::extract_if`, `LinkedList::extract_if` | 1.87 | the old unstable `drain_filter`, or `retain` plus a second pass |
| `HashMap/HashSet::extract_if` | 1.88 | collect keys, then remove one by one |
| `BTreeMap/BTreeSet::extract_if` | 1.91 | the same |
| `get_disjoint_mut` (slices, `HashMap`) | 1.86 | `split_at_mut` gymnastics for two `&mut` items |
| `Vec::pop_if` | 1.86 | `if v.last().is_some_and(..) { v.pop() }` |
| `<[T]>::split_off_first` and friends | 1.87 | manual slicing |
| `as_chunks::<N>()` | 1.88 | `chunks_exact` with a length check |
| `array_windows::<N>()` | 1.94 | `windows(2)` plus indexing |
| `<[T]>::as_array::<N>()` | 1.93 | `try_into()` to an array reference |
| `Vec::push_mut`, `insert_mut`, `VecDeque::push_*_mut` | 1.95 | push, then `last_mut().unwrap()` |
| `VecDeque::pop_front_if`, `pop_back_if` | 1.93 | peek then pop |
| `VecDeque::retain_back(len)` | 1.99 | keeps the **last `len`** items (not a predicate) |
| `Vec::into_parts` / `from_parts` | 1.99 | `ManuallyDrop` plus `as_mut_ptr` plus `len` plus `capacity` |
| `IntoIterator for Box<[T; N]>` | 1.99 | `.into_iter()` on the array after unboxing |
| `iter::chain`, `array::repeat` | 1.91 | `a.into_iter().chain(b)`, `[x; N]` for non-`Copy` via closures |
| `Peekable::next_if_map` | 1.94 | manual `peek` and `next` |
| `btree_map::Entry::insert_entry` | 1.92 | insert then look up again |

- **Careful with `retain_back`:** the name suggests a predicate like
  `Vec::retain`, but the argument is a **length**. This is an easy mistake to
  make from memory (the docs say "keeping the last `len` elements").
- **Strings and paths:** `str::floor_char_boundary` (1.91),
  `str::substr_range` and `strip_circumfix` (1.98), `String::from_utf8_lossy_owned`
  (1.99), `PathBuf::add_extension` / `with_added_extension` (1.91),
  `Path::file_prefix` (1.91).
- **`Duration::from_mins` / `from_hours` (1.91)**, `Duration::from_nanos_u128` (1.93).
- Background: [Collections & Strings](../foundations/rust-collections-and-strings.md).

## 6. "What new number and option helpers should I use?"

**Answer:**

| API | Since | What it does |
|---|---|---|
| `midpoint` (ints, floats) | 1.85 | average without overflow |
| `is_multiple_of` | 1.87 | `n % k == 0` that does not panic when `k == 0` |
| `unbounded_shl` / `unbounded_shr` | 1.87 | shift by any amount; result is 0 past the width, no panic |
| `checked_sub_signed` and the `overflowing`/`saturating`/`wrapping` forms | 1.90 | unsigned minus signed |
| `strict_add`, `strict_sub`, `strict_mul`, ... | 1.91 | **always** panic on overflow, in release builds too |
| `highest_one`, `lowest_one`, `bit_width`, `isolate_highest_one`, `isolate_lowest_one` | 1.97 | bit-level helpers (1.97 also added them to `NonZero`) |
| `{float}::algebraic_add` and friends | 1.98 | allows the compiler to reorder float math (like fast-math, but scoped) |
| `bool::ok_or`, `bool::ok_or_else` | 1.98 | `true.ok_or(err)` is `Ok(())` |
| `Option/Result::map_or_default` | 1.98 | `map_or(Default::default(), f)` |
| `Result::flatten` | 1.89 | `Result<Result<T, E>, E>` to `Result<T, E>` |
| `bool: TryFrom<{integer}>` | 1.95 | only 0 and 1 succeed |

- **`strict_*` vs `wrapping_*` vs `checked_*`:** `strict` panics even with
  `overflow-checks = false`. Use it where a silent wrap would be a bug, such as
  index or size math. Rules for plain `+` are in
  [Types, Enums & Patterns §1](../foundations/rust-types-enums-and-patterns.md#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose).
- **`algebraic_*` changes results:** `0.1.algebraic_add(0.2)` may differ from
  `0.1 + 0.2` because the compiler may reorder operations. In the sample run
  on 1.99.1 it printed the same value. Do not rely on either result.
- 1.99 fully **deprecated the old integer modules**: `std::i32::MAX` now warns
  (and the sample file `compile_fail/std_i32_max.rs` denies it). Use `i32::MAX`:

```text
error: use of deprecated constant `std::i32::MAX`: replaced by the `MAX` associated constant on this type
 --> compile_fail/std_i32_max.rs:5:30
```

## 7. "What changed for threads, locks, atomics, and lazy values?"

**Answer:**

- **`RwLockWriteGuard::downgrade` (1.92):** turn a write guard into a read
  guard **without** letting another writer in between:

```rust
let mut w = lock.write().unwrap();
*w += 1;
let r = std::sync::RwLockWriteGuard::downgrade(w);
```

- **File locks (1.89):** `File::lock`, `lock_shared`, `try_lock`,
  `try_lock_shared`, `unlock`. The sample opens a **second handle** to the
  same file, and `try_lock` on it fails with "lock acquisition failed because
  the operation would block". Locks work **between handles/processes**; do not
  assume what happens when the same handle locks twice.
- **Atomics `update` / `try_update` (1.95):** a compare-exchange loop in one
  call, on `AtomicBool`, the integer atomics and `AtomicPtr`:
  `n.update(Ordering::SeqCst, Ordering::SeqCst, |x| x * 3)` returns the **old**
  value.
- **`Atomic<T>::from_mut` (1.98):** view a plain `&mut u32` as an atomic when
  you hold exclusive access (also `get_mut_slice`, `from_mut_slice`).
  `AtomicPtr` gained `fetch_ptr_add` and `fetch_or` in 1.91.
- **`LazyCell` and `LazyLock` (1.94):** `get`, `get_mut` and `force_mut`.
  `LazyLock::get(&lazy)` returns `None` until something forces it. 1.89 added
  `DerefMut`, and 1.96 added `From<T>`.
- **`Once::wait` and `OnceLock::wait` (1.86):** block until initialization.
- **`LocalKey<Cell<T>>::update` (1.99):** update a `thread_local!` cell
  directly.
- **`Cell::update` (1.88):** `c.update(|x| x * 2)`.
- Background: [Smart Pointers §5](../foundations/rust-smart-pointers.md#5-what-are-cow-oncelock-and-lazylock-for).
  Concurrency details are on the
  [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md) and
  [Atomics & Memory Ordering](../concurrency-and-async/rust-atomics-and-memory-ordering.md) pages.

## 8. "What are the new range types?"

**Answer:**

- **Core idea:** the old `std::ops::Range` is **itself an iterator**, so it
  cannot be `Copy` (copying an iterator would be a trap). 1.95 and 1.96 added
  new types in `core::range` (also `std::range`): `Range`, `RangeInclusive`,
  `RangeFrom`, `RangeToInclusive`.
- The new types are **`Copy`** and are **not** iterators themselves. Call
  `.into_iter()` (verified in the sample: `Range { start: 2, end: 5 }`, copied,
  then summed to 9).
- The `a..b` syntax **still makes the old type** in 1.99. Assigning `2..5` to a
  `std::range::Range<i32>` fails with `expected struct std::range::Range<i32>,
  found struct std::ops::Range<{integer}>`, and the compiler suggests
  `.into()`. Build the new types with a struct literal or with `.into()`.
- `std::range::legacy` (1.98) names the old types explicitly.
- 1.96: ranges of `NonZero` integers are iterable.

## 9. "What changed in Cargo and the toolchain?"

**Answer:**

| Change | Since | Why it matters |
|---|---|---|
| Resolver `"3"` (MSRV-aware) is the default for **edition 2024** | 2024 edition | picks dependency versions your `rust-version` can compile |
| Automatic garbage collection of the Cargo cache | 1.88 | old downloads and builds are cleaned up |
| Multi-package `cargo publish` | 1.90 | publish a workspace in dependency order |
| `lld` is the default linker on `x86_64-unknown-linux-gnu` | 1.90 | faster links, no setup |
| `build.build-dir` config | 1.91 | separate intermediate files from final outputs |
| `--target host-tuple` | 1.91 | name the host target without spelling it out |
| `include` key in Cargo config | 1.94 | share and layer config files |
| TOML 1.1 in manifests | 1.94 | newer syntax, but raises your development MSRV |
| `build.warnings` config (`"warn"`, `"allow"`, `"deny"`) | 1.97 | make warnings from your own packages errors in CI, replacing `-Dwarnings` |
| `resolver.lockfile-path` | 1.97 | read-only source trees |
| v0 symbol mangling is the default | 1.97 | older debuggers and profilers may fail to demangle |
| New `debug` profile | 1.99 | a step toward making `dev` faster and `debug` the debugging profile |
| Override inherited `default-features` for edition 2024 workspace members | 1.99 | `serde = { workspace = true, default-features = false }` works |
| Incremental compilation is off by default when `CI` is set | 1.99 | CI builds are clean and reproducible |
| LLVM 23 | 1.99 | code generation updates |

- `--remap-path-prefix` and `--emit` for rustdoc (1.97) and
  `--remap-path-scope` (1.95) help reproducible builds.
- Background: [Toolchain & Cargo](../foundations/rust-toolchain-and-cargo.md) and,
  for CI, the [CI/CD & Supply Chain](../production/rust-ci-cd-and-supply-chain.md) page.

## 10. "What are the 2024 edition changes I should know by heart?"

**Answer:**

- **Return-position `impl Trait` captures all in-scope lifetimes** (use `use<..>`
  to opt out). See [§3](#3-what-changed-for-async-closures-and-traits).
- **`if let` temporary scope:** temporaries in the scrutinee drop before the
  `else` block. This fixes a class of deadlocks with `Mutex` guards.
- **Tail-expression temporaries** drop before local variables.
- **Unsafe changes:** `unsafe extern` blocks, `#[unsafe(no_mangle)]`,
  `unsafe_op_in_unsafe_fn` warns, references to `static mut` are denied,
  `std::env::set_var` is `unsafe`.
- **`gen` is a reserved keyword** (for future generators; `gen` blocks are not
  stable).
- **`Box<[T]>` implements `IntoIterator` by value**, and the prelude gained
  `Future` and `IntoFuture`.
- **Let chains** and the **MSRV-aware resolver** need this edition.
- **Macro fragment specifiers:** `expr` now also matches `const {}` and `_`;
  use `expr_2021` for the old behavior.
- Full table with samples:
  [Modules, Crates & Editions §5](../foundations/rust-modules-crates-and-editions.md#5-what-changed-in-the-2024-edition).

## 11. "Which old habits should you stop?"

**Answer:**

| Old habit | Use now | Since |
|---|---|---|
| `lazy_static!` or `once_cell::Lazy` | `std::sync::LazyLock` / `OnceLock` | 1.80 / 1.70 |
| `\|x\| async move { .. }` returning a borrowing future | `async \|x\| ..` | 1.85 |
| `as_super()` helper methods for trait objects | trait object upcasting | 1.86 |
| `drain_filter` crates, or `retain` plus collecting | `extract_if` | 1.87 to 1.91 |
| Nested `if let` pyramids | let chains | 1.88 (2024 edition) |
| A nested `match` just to test a second pattern in an arm | `if let` guard | 1.95 |
| `assert!(matches!(..))` | `std::assert_matches!` | 1.96 |
| `cfg-if` crate | `std::cfg_select!` | 1.95 |
| `std::i32::MAX`, `std::u32::MAX` | `i32::MAX`, `u32::MAX` | deprecated 1.99 |
| `#[no_mangle]` | `#[unsafe(no_mangle)]` | 2024 edition |
| `extern "C" { .. }` | `unsafe extern "C" { .. }` | 2024 edition |
| `static mut` with references | `Mutex`, atomics, or `UnsafeCell` | denied in 2024 |
| `mem::transmute` between an integer and a pointer | `with_exposed_provenance` / `ptr::without_provenance` | lint 1.91 |
| `async-trait` crate for non-`dyn` use | native `async fn` in traits | 1.75 |
| `-Dwarnings` in `RUSTFLAGS` (changing flags invalidates the build cache) | `build.warnings = "deny"` config (only lints from local packages) | 1.97 |
| Manual `unsafe` CAS loop on an atomic | `Atomic*::update` | 1.95 |

- Not every old pattern is wrong. The crates above are fine in older
  codebases. Stop **starting** new code with them.

## 12. "What is still not stable?"

**Answer:**

- These do **not appear as stabilized in any release note from 1.85 to 1.99**
  (searched `RELEASES.md` for each): **Polonius** (the next borrow checker),
  the **next-generation trait solver**, **specialization**, **`gen` blocks**,
  **Cranelift** as a stable backend, and the **parallel front end**
  (`-Zthreads`, nightly flag).
- Release notes name specialization once, in a negative way: 1.93 **stopped
  using it** inside the standard library for `Copy` because it is unsound with
  lifetime-dependent impls.
- Treat these as "watch the tracking issues": if you read about them in a blog
  post, check the current release notes before using them.
- Nightly-only features need `#![feature(...)]` and a nightly toolchain. A
  `rust-toolchain.toml` can pin one per project, but production code should
  stay on stable.

## 13. "How do AI tools help or hurt with modern Rust?"

**Answer:**

- **Hurt:** models learned most Rust from older code. Expect suggestions with
  `lazy_static`, `once_cell`, `std::i32::MAX`, `#[no_mangle]`, `async-trait`
  and `extern "C" {}`. The compiler and `clippy` tell you what is outdated.
- **Hurt:** an assistant may invent an API name that sounds right (for
  example a predicate for `retain_back`). Always open the docs
  (`cargo doc --open`, or the std docs) before trusting a new method.
- **Help:** ask it to "modernize this crate to the 2024 edition", then
  run `cargo fix --edition` and review the diff yourself. Ask for
  explanations of each changed line.
- **Help:** paste the **release notes** for the versions you skipped and ask
  for a summary of what affects your code. You still verify.
- Pin the model's target: say "Rust 1.99, edition 2024" at the start of a
  prompt, and set `rust-version` in `Cargo.toml` so the compiler enforces it.
- More on interviews: [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 14. Interview Questions You're Likely to Get Asked

**Versions and editions**

- "What is the difference between a Rust version and an edition?" — expects:
  versions ship every 6 weeks and never break; editions are opt-in dialects per
  crate that interoperate, [§1](#1-how-does-rust-versioning-work-and-how-do-you-keep-up).
- "What is MSRV, and who enforces it?" — expects: the oldest supported
  compiler; `rust-version` in `Cargo.toml`; the MSRV-aware resolver,
  [§9](#9-what-changed-in-cargo-and-the-toolchain).

**Language features**

- "What are let chains, and which edition do they need?" — expects: `&&`
  chains of `let` and booleans, edition 2024 only,
  [§2](#2-what-new-control-flow-and-pattern-features-exist).
- "What does an `if let` guard let you do?" — expects: bind and test inside a
  match-arm guard, 1.95, [§2](#2-what-new-control-flow-and-pattern-features-exist).
- "Why are async closures better than closures that return `async move`
  blocks?" — expects: they can lend their captured state to the future,
  [§3](#3-what-changed-for-async-closures-and-traits).
- "What does `use<..>` do?" — expects: lists the generics a returned
  `impl Trait` captures; 2024 captures everything by default,
  [§3](#3-what-changed-for-async-closures-and-traits).
- "Can you convert `Box<dyn Sub>` to `Box<dyn Super>`?" — expects: yes since
  1.86 (upcasting), [§3](#3-what-changed-for-async-closures-and-traits).

**Standard library**

- "How do you remove matching items from a `Vec` and also keep them?" — expects:
  `extract_if`, [§5](#5-which-new-collection-and-slice-apis-replace-old-workarounds).
- "How do you get two `&mut` items from one slice?" — expects: `get_disjoint_mut`,
  returns an error on overlap, [§5](#5-which-new-collection-and-slice-apis-replace-old-workarounds).
- "Why are the new range types `Copy`, and how do you iterate them?" — expects:
  they are not iterators; call `.into_iter()`, [§8](#8-what-are-the-new-range-types).
- "How do you downgrade a write lock safely?" — expects:
  `RwLockWriteGuard::downgrade`, [§7](#7-what-changed-for-threads-locks-atomics-and-lazy-values).
- "How do you stop silent integer wrap?" — expects: `checked_*`, `strict_*`,
  or `overflow-checks`, [§6](#6-what-new-number-and-option-helpers-should-i-use).

**Safety and tooling**

- "Which `unsafe` things did the 2024 edition tighten?" — expects: `unsafe extern`,
  `unsafe(no_mangle)`, `static mut` references denied, `set_var` unsafe,
  [§10](#10-what-are-the-2024-edition-changes-i-should-know-by-heart).
- "How do you make CI fail on warnings today?" — expects: `build.warnings`
  config (1.97) instead of `-Dwarnings`, [§9](#9-what-changed-in-cargo-and-the-toolchain).
- "What is still unstable?" — expects: Polonius, next trait solver,
  specialization, `gen` blocks, `-Zthreads`, [§12](#12-what-is-still-not-stable).

---

## Code Samples

- `code_samples/rust/examples/modern_rust.rs`: one runnable example per
  item, grouped by release (1.85 to 1.99).
- `code_samples/rust/compile_fail/let_chain_2021.rs` (edition 2021 error) and
  `std_i32_max.rs` (deprecated constant error) quote real compiler output.

```bash
cd code_samples/rust
cargo run --example modern_rust
rustc --edition 2021 --emit=metadata -o /tmp/out compile_fail/let_chain_2021.rs   # fails on purpose
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/std_i32_max.rs     # fails on purpose
```
