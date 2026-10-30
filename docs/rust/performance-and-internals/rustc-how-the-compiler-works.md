---
title: How rustc Works — Pipeline, MIR, the Borrow Checker, Monomorphization, and Compile Times
---

# How rustc Works

`rustc` turns your source into a program in a **chain of stages**. Each
stage works on a different **intermediate representation (IR)**, a form of
the program chosen for one job: parsing wants a tree of syntax, type
checking wants resolved names, the borrow checker wants a control-flow
graph, and the code generator wants something close to machine code. If you
know the stages, compiler errors, slow builds, and code-size surprises all
become easier to explain.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Output shown was
    produced by `rustc 1.99.1`; the nightly-only parts used `rustc
    1.101.0-nightly (2026-10-28)`. Status claims (what is or is not stable)
    were checked against the `rustc-dev-guide` and `RELEASES.md` on that
    date. Internal details change faster than the language: treat stage
    names as stable and exact flags as things to re-check.

## 1. "What are the stages from source to executable?"

**Answer:**

- The pipeline, in order:

| Stage | Input to output | What happens |
|---|---|---|
| Lex and parse | text to **AST** (Abstract Syntax Tree) | tokens, then a tree that mirrors the syntax |
| Expansion | AST to AST | `macro_rules!` and procedural macros run, `#[cfg]` is applied |
| Name resolution | AST | each name is tied to its definition (`use`, modules, scopes) |
| Lowering | AST to **HIR** (High-level IR) | sugar removed: `for`, `?`, `if let` become simpler forms |
| Type checking | HIR | types inferred, traits solved, methods chosen |
| Lowering | HIR to **THIR** (Typed HIR) | a fully typed tree used to build MIR and check patterns |
| MIR build | THIR to **MIR** (Mid-level IR) | a control-flow graph of simple steps |
| Borrow check and MIR passes | MIR | ownership and borrow errors; optimizations |
| Monomorphization | MIR to MIR copies | generics are copied per concrete type |
| Code generation | MIR to **LLVM IR** | handed to the LLVM backend |
| LLVM | LLVM IR to object files | optimization and machine code |
| Linking | objects to executable | the system linker joins everything |

- Two ideas to keep: **everything before MIR is about meaning** (names,
  types, traits), and **everything after is about code**.
- A **crate** is the unit of compilation: one `rustc` run per crate,
  producing an `rlib` (a Rust library file with metadata and MIR for
  generics), a `dylib`, a `cdylib`, a `staticlib`, or an executable.
  See
  [Modules, Crates & Editions §1](../foundations/rust-modules-crates-and-editions.md#1-what-are-packages-crates-and-modules).

## 2. "What happens in the front end: parse, expand, resolve?"

**Answer:**

- **Parsing** builds the AST. A syntax error stops here.
- **Macro expansion** runs *before* type checking. A macro sees **tokens**,
  not types, which is why a macro cannot ask "what is the type of this
  expression?" Expansion repeats until no macro calls are left.
- **Name resolution** decides which item each path means, including
  glob imports and the prelude of your edition.
- You can see the result of expansion on nightly. For this source:

```rust
macro_rules! twice { ($e:expr) => { $e + $e }; }
pub fn m(x: i32) -> i32 { twice!(x * 2) }
```

  `rustc +nightly -Zunpretty=expanded` prints:

```rust
pub fn m(x: i32) -> i32 { x * 2 + x * 2 }
```

- Procedural macros are **compiled first and run inside the compiler**,
  which is one reason crates that use them add build time. See
  [Macros](../advanced-language/rust-macros.md).
- The **2024 edition** changes some parts of this stage (for example, the
  `expr` macro fragment also matches `const {}` and `_`). See
  [Modules, Crates & Editions §5](../foundations/rust-modules-crates-and-editions.md#5-what-changed-in-the-2024-edition).

## 3. "What are HIR and THIR, and what does type checking do?"

**Answer:**

- **HIR** is the AST with the shortcuts removed. Nightly can print it
  (`-Zunpretty=hir`). `v[i]`, `?`, `for` loops and `async` all look simpler
  here than in your source.
- **Type checking** works on HIR and does three things at once:
    - **Inference**: fills in types you left out (Hindley-Milner style
      unification, extended with traits and coercions).
    - **Trait solving**: for every call like `x.clone()` or `a + b`, finds
      which `impl` applies, or reports that none does.
    - **Method lookup**: tries the receiver type, then `&T`, `&mut T`, then
      follows `Deref`, until a method fits.
- **THIR** is the typed form that is lowered into MIR. Pattern matching
  is checked here: **exhaustiveness** (all cases covered) and
  **reachability** (no useless arm) errors come from this stage.
- **Trait solver status.** The trait solver in use today is the
  original one. A rewrite, the **next-generation trait solver**, exists
  behind `-Znext-solver` (nightly). The compiler team's own CI document
  says they want to **stabilize it, together with Polonius alpha, in
  2026**. It was **not stable** on 1.99, so this page describes the
  current behaviour.
- Generics are **checked once, against their bounds**, not per use. That is
  why a missing bound is an error at the generic function, even if every
  real call would work. See
  [Traits & Generics §4](../foundations/rust-traits-and-generics.md#4-how-do-you-write-generic-code-and-what-are-bounds).

## 4. "What is MIR, and why does the borrow checker run on it?"

**Answer:**

- **MIR** is a **control-flow graph** (CFG): numbered **basic blocks**,
  each a straight list of simple statements ending in a jump. There are no
  loops or `match` expressions, only `goto` and `switchInt`.
- Here is the real **unoptimized MIR** (`-C opt-level=0`, shortened) of
  `fn pick(v: &Vec<i32>, i: usize) -> i32 { if i < v.len() { v[i] + 1 } else { -1 } }`:

```text
bb0: { _4 = Vec::<i32>::len(copy _1) -> [return: bb1, unwind continue]; }
bb1: { _3 = Lt(copy _2, move _4);
       switchInt(move _3) -> [0: bb5, otherwise: bb2]; }
bb2: { _6 = <Vec<i32> as Index<usize>>::index(copy _1, copy _2) -> [return: bb3, ...]; }
bb3: { _5 = copy (*_6);
       _7 = AddWithOverflow(copy _5, const 1_i32);
       assert(!move (_7.1: bool), "attempt to compute `{} + {}`, which would overflow", ...) -> [success: bb4, ...]; }
bb4: { _0 = move (_7.0: i32); goto -> bb6; }
bb5: { _0 = const -1_i32; goto -> bb6; }
bb6: { return; }
```

- Read it: `_1`, `_2` are the arguments, `_0` is the return value. The
  `index` call is `v[i]`. **The overflow check is explicit**: in debug
  builds, `+` becomes `AddWithOverflow` and an `assert`. In release builds
  the check is off by default (see
  [Types, Enums & Patterns](../foundations/rust-types-enums-and-patterns.md)).
- **Why the borrow checker uses MIR:** with a graph, "is this borrow still
  **live** at this point?" is a question about paths through the graph.
  That is **NLL** (Non-Lexical Lifetimes): a borrow lasts from where it is
  created to its **last use**, not to the end of the `{}` block. It is why
  `let r = &mut x; use(r); x += 1;` compiles.
- The borrow checker also uses MIR to track **moves and initialization**
  (use after move), and the **drop checker** decides where destructors run
  (see [Variance, Drop Check & PhantomData](../advanced-language/rust-variance-dropck-and-phantomdata.md)).
- **MIR optimizations** (inlining, constant propagation, dead code removal)
  run after borrow checking. They are why `-O` code is smaller than the
  MIR above.
- **Where NLL says no.** NLL is not complete. This famous case is rejected
  although it is safe (the shape is "return a reference on one path,
  mutate on the other"):

```rust
fn get_or_insert(map: &mut HashMap<u32, String>, k: u32) -> &String {
    if let Some(v) = map.get(&k) {
        return v;
    }
    map.insert(k, String::from("new"));
    &map[&k]
}
```

```text
error[E0502]: cannot borrow `*map` as mutable because it is also borrowed as immutable
 --> nll_conditional_return.rs:8:5
  |
4 | fn get_or_insert(map: &mut HashMap<u32, String>, k: u32) -> &String {
  |                       - let's call the lifetime of this reference `'1`
5 |     if let Some(v) = map.get(&k) {
  |                      --- immutable borrow occurs here
6 |         return v;
  |                - returning this value requires that `*map` is borrowed for `'1`
7 |     }
8 |     map.insert(k, String::from("new"));
  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ mutable borrow occurs here
```

- **Polonius** is the next borrow-checking algorithm. It tracks *which loans
  can reach each point* instead of lifetimes as regions. On nightly
  1.101, `rustc +nightly -Zpolonius=next` **accepted this exact file** and
  the program printed `new`. It is **not stable on 1.99**.
    - The stable fix today: use the `entry` API, or look up twice
      (`if map.contains_key(&k) { return &map[&k]; }`).
- Lifetimes are the user-facing side of this stage: see
  [Lifetimes](../foundations/rust-lifetimes.md).

## 5. "What is monomorphization, and what does it cost?"

**Answer:**

- **Monomorphization** means the compiler **makes a separate copy of a
  generic function for each concrete type it is used with**. `largest::<i32>`,
  `largest::<f64>` and `largest::<char>` are three different functions.
- Proof: one generic function, called with three types, compiled with
  `-C codegen-units=1`, and its symbols listed with `nm`:

```rust
#[inline(never)]
pub fn largest<T: PartialOrd + Copy>(xs: &[T]) -> T { /* ... */ }
// main calls it with &[i32], &[f64], &[char]
```

```text
... t __RINvCs8zzNNHmMyYC_13pipeline_demo7largestcEB2_
... t __RINvCs8zzNNHmMyYC_13pipeline_demo7largestdEB2_
... t __RINvCs8zzNNHmMyYC_13pipeline_demo7largestlEB2_
```

  The final letter before `EB2_` is the type (`c` is `char`, `d` is `f64`,
  `l` is `i32`): **three symbols from one function**.
- **Benefit:** each copy is optimized for its type, with no run-time lookup:
  this is **static dispatch**, the zero-cost side of generics.
- **Cost:** more code to compile and more machine code, so **longer
  builds and bigger binaries**.
- `dyn Trait` is the other choice: one copy, an indirect call through a
  vtable. See
  [Traits & Generics §2](../foundations/rust-traits-and-generics.md#2-what-is-the-difference-between-generics-and-dyn-trait).
- **Generics are only compiled when used.** A generic function in a library
  has no machine code until something instantiates it. That is why an
  `rlib` carries the **MIR** of generic functions: a downstream crate
  needs it to make its own copy.
- **Reduce the cost** with the "thin generic wrapper" pattern: a small
  generic function converts its arguments and calls one **non-generic**
  inner function that holds the real work. `std` does this for `fs::read`
  (`AsRef<Path>`).

## 6. "What do LLVM and the linker do?"

**Answer:**

- After monomorphization, `rustc` translates MIR to **LLVM IR** and gives it
  to **LLVM**, a separate compiler back end (also used by Clang and Swift).
  LLVM does most of the optimization you see at `-O` and emits machine code
  for the target CPU.
- Every crate gets split into **codegen units** (CGUs) so LLVM can work in
  parallel. More units mean a faster build and slightly less inlining; that
  is the `codegen-units` setting in
  [Performance Engineering §10](rust-performance-engineering.md#10-which-release-profile-settings-change-performance).
- The **linker** joins object files and libraries into one executable and
  removes unused code. On Linux x86-64 the default linker has been `lld`
  since **1.90**.
- Other back ends exist. **Cranelift** (a faster compiler with less
  optimization, good for debug builds) is a **nightly-only** `rustup`
  component (`rustc-codegen-cranelift`), not stable. A GCC back end is also
  in development.

## 7. "What are queries and incremental compilation?"

**Answer:**

- `rustc` is built as a set of **queries**: functions like "type of this
  item" or "MIR of this function" whose results are **cached and computed
  on demand**. A query calls other queries; the compiler records those
  dependencies as a graph.
- **Incremental compilation** saves that graph on disk (in `target/`). On
  the next build, `rustc` checks which inputs changed, reuses every cached
  result that does not depend on them, and **recomputes only the rest**.
  It is on by default for `dev` builds and off for `release`.
- That is why changing a function body rebuilds quickly, and why changing
  a widely used type or a public signature is slow: many queries depend on
  it.
- It is also why Rust, unlike C, has **no header files** and no fixed
  order of source files: the query system computes what it needs.

## 8. "Why are Rust builds slow, and how do you speed them up?"

**Answer:**

- **Why:** a lot of work per line (type inference, trait solving,
  borrow checking, monomorphization), LLVM optimization, and the fact that
  a **crate is one compilation unit**: a big crate cannot be split across
  machines.
- Find the cause **before** trying fixes:
    - **`cargo build --timings`** writes an HTML chart of every crate's build
      time and parallelism. It shows the **critical path**.
    - **`cargo llvm-lines`** (install with `cargo install cargo-llvm-lines`)
      counts lines of LLVM IR per function and **how many copies** (the
      monomorphization cost). Real output for the samples' timing example:

```text
  Lines               Copies             Function name
  -----               ------             -------------
  9684                312                (TOTAL)
   309 (3.2%,  3.2%)    1 (0.3%,  0.3%)  bench_demo::main
   267 (2.8%,  5.9%)    1 (0.3%,  0.6%)  <hashbrown::raw::RawTableInner>::resize_inner::<Global>
   235 (2.4%,  8.4%)    1 (0.3%,  1.0%)  <core::hash::sip::Sip13Rounds as ...>::d_rounds
```

    - **`cargo bloat`** does the same for the final binary's size.
- Fixes, from cheapest:

| Fix | Why it helps |
|---|---|
| `cargo check` while editing | stops before code generation; far faster than `build` |
| Split a large crate into a **workspace** | smaller units compile in parallel and cache separately |
| Fewer, smaller generic functions; the thin-wrapper pattern (§5) | fewer copies to compile |
| Fewer dependencies and fewer **features** | less code to build |
| Faster linker (`lld` is default on Linux x86-64; `mold` is an option) | linking is often the slowest step on a small change |
| `sccache` or `Swatinem/rust-cache` in CI | reuse compiled crates between runs |
| Lower `opt-level` or `debug = "line-tables-only"` for dev | less to optimize and write |
| Cranelift back end, `-Zthreads=N` | **nightly only**: stable rejects `-Z` flags |

- On stable, a `-Z` flag fails immediately:

```text
error: the option `Z` is only accepted on the nightly compiler

help: consider switching to a nightly toolchain: `rustup default nightly`
```

- The **parallel front end** (`-Zthreads`) and Cranelift are therefore
  not part of a production build today.
- Procedural macros and build scripts compile **before** the crates that
  use them, so they sit on the critical path. A slow `build.rs` slows
  every clean build. See
  [Toolchain & Cargo §8](../foundations/rust-toolchain-and-cargo.md#8-what-are-build-scripts-and-when-do-you-need-one).

## 9. "How do you look at what the compiler produced?"

**Answer:**

- `rustc` can **emit** each stage. The flag `--emit=` takes a comma list:

```bash
rustc --edition 2024 -O --crate-type=lib --emit=mir,llvm-ir,asm --out-dir out pipeline_demo.rs
```

| Flag | Output | Stable? |
|---|---|---|
| `--emit=mir` | `.mir` text | yes |
| `--emit=llvm-ir` | `.ll` text | yes |
| `--emit=asm` | `.s` assembly | yes |
| `--emit=metadata` | type-check only (what `cargo check` does) | yes |
| `-Zunpretty=expanded` | source after macro expansion | nightly |
| `-Zunpretty=hir` | HIR as source-like text | nightly |

- **`cargo expand`** (a third-party tool built on `-Zunpretty=expanded`) shows
  macro output for a whole crate.
- **Compiler Explorer** (godbolt.org) shows assembly next to your Rust
  source with colours. Use `-O` or the code is not what you will ship.
- When reading assembly, the questions are: **was this call inlined?**,
  **is there a bounds-check branch?**, and **is this loop vectorized?**
- `cargo rustc -- --emit=asm` forwards flags to the final crate only.

## 10. "How do `const fn` and compile-time evaluation work?"

**Answer:**

- A **`const fn`** can be called at **compile time** (to fill a `const`,
  `static`, array length, or `const` generic) and also at run time.
- The compiler runs a **MIR interpreter** (called **Miri's engine**,
  shared with the Miri tool) to evaluate it. Mistakes such as overflow,
  out-of-bounds, or an infinite loop become **compile errors**.
- The sample builds a table at compile time:

```rust
pub const fn square(x: u32) -> u32 { x * x }
const TABLE: [u32; 4] = [square(1), square(2), square(3), square(4)];
// printed: [1, 4, 9, 16]
```

- In the MIR dump, `TABLE` is its own item, evaluated once; no code runs for
  it at run time.
- Release **1.93** let const evaluation **copy pointers byte by byte**, so
  more code is allowed in `const` (for example parts of `memcpy`-like
  logic).
- Limits: no heap allocation in the result, no trait methods through
  `dyn`, and some traits are not yet usable in `const`. Check the Reference
  when a `const` fails.

## 11. "What are lints, Clippy, and the `-C` and `-Z` flags?"

**Answer:**

- **Lints** are checks that run on the compiler's IRs and report warnings,
  not errors, by default (`unused_variables`, `dead_code`). Each lint has a
  level: `allow`, `warn`, `deny`, `forbid`. Set per item with
  `#[allow(...)]` or per crate in `Cargo.toml` under `[lints.rust]`.
- Release notes keep adding lints, and some become **deny by default**:
  1.89 added `dangerous_implicit_autorefs` as deny, and 1.96 made
  `uninhabited_static` deny by default. Upgrading can therefore break a
  build that compiled before.
- **Clippy** is a separate linter that runs the compiler up to type
  checking and then applies hundreds of extra lints, sorted into groups
  (`correctness`, `style`, `perf`, `pedantic`). Run it with
  `cargo clippy --all-targets -- -D warnings`.
- **`-C`** options are **stable** code-generation flags (`-C opt-level=3`,
  `-C target-cpu=native`, `-C panic=abort`). **`-Z`** options are
  **unstable** and only work on nightly (§8). Cargo profiles map to `-C`
  flags.

## 12. "How do AI tools help or hurt here?"

**Answer:**

- **Help:**
    - Paste `--emit=mir` or `--emit=asm` output and ask "which block is the
      bounds check?" It reads these dumps faster than you.
    - Paste the output of `cargo build --timings` or `cargo llvm-lines` and
      ask for the **three biggest** changes.
    - Ask for the **stage** where an error comes from ("is E0502 from the
      borrow checker or type checking?") to learn where to look.
- **Hurt:**
    - Internals change every release. An AI often describes an **older
      pipeline** (for example calling NLL or Polonius "stable soon" with an
      old date, or naming flags that were renamed). Check against the
      `rustc-dev-guide` and the release notes.
    - It may say "Rust compiles slowly because of the borrow checker."
      Usually the **borrow checker is cheap**; monomorphization and LLVM are
      the costs. Measure with `--timings`.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 13. Interview Questions You're Likely to Get Asked

**Pipeline**

- "Walk me through what `cargo build` does to a `.rs` file." — expects:
  parse, expand, resolve, HIR, type check, MIR, borrow check, monomorphize,
  LLVM, link, [§1](#1-what-are-the-stages-from-source-to-executable).
- "Why can't a macro know a variable's type?" — expects: macros expand
  before type checking and work on tokens, [§2](#2-what-happens-in-the-front-end-parse-expand-resolve).

**MIR and borrow checking**

- "What is MIR and why does it matter?" — expects: a control-flow graph; the
  borrow checker and many optimizations run on it, [§4](#4-what-is-mir-and-why-does-the-borrow-checker-run-on-it).
- "What is NLL?" — expects: a borrow lasts until its last use, not the end
  of the block, [§4](#4-what-is-mir-and-why-does-the-borrow-checker-run-on-it).
- "Give an example the borrow checker rejects but is safe." — expects: the
  conditional-return case; mention Polonius is not yet stable,
  [§4](#4-what-is-mir-and-why-does-the-borrow-checker-run-on-it).

**Code size and speed**

- "What is monomorphization?" — expects: one copy per concrete type; faster
  code, bigger binary, [§5](#5-what-is-monomorphization-and-what-does-it-cost).
- "Static vs dynamic dispatch?" — expects: generics vs `dyn`, one copy and a
  vtable, [§5](#5-what-is-monomorphization-and-what-does-it-cost).
- "A clean build takes 20 minutes. What do you do?" — expects: `--timings`,
  `cargo llvm-lines`, split into a workspace, fewer generics and features,
  faster linker, CI cache, [§8](#8-why-are-rust-builds-slow-and-how-do-you-speed-them-up).

**Tooling**

- "How do you see the assembly for a function?" — expects: `--emit=asm`
  with `-O`, or Compiler Explorer, [§9](#9-how-do-you-look-at-what-the-compiler-produced).
- "What is the difference between `-C` and `-Z` flags?" — expects: stable
  codegen flags vs nightly-only, [§11](#11-what-are-lints-clippy-and-the-c-and-z-flags).

---

## Code Samples

All files are in `code_samples/rust/internals/` (plain `rustc` files, no
Cargo needed) and were run on Rust 1.99.1 unless marked nightly.

- `pipeline_demo.rs` — a generic `largest<T>` used with three types, and a
  `const fn` table. Used for the symbol list (§5), `--emit` (§9), and
  const evaluation (§10).
- `mir_small.rs` — the small function whose MIR is shown in §4, and the
  macro whose expansion is shown in §2 (nightly `-Zunpretty`).
- `nll_conditional_return.rs` — must fail on stable (`E0502`); accepted by
  `-Zpolonius=next` on nightly.

```bash
cd code_samples/rust/internals
rustc --edition 2024 -O -C codegen-units=1 pipeline_demo.rs && ./pipeline_demo && nm pipeline_demo | grep largest
rustc --edition 2024 --crate-type=lib --emit=mir -C opt-level=0 -o - mir_small.rs
rustc --edition 2024 nll_conditional_return.rs                  # fails with E0502
rustc +nightly -Zpolonius=next --edition 2024 nll_conditional_return.rs && ./nll_conditional_return
rustc +nightly -Zunpretty=expanded --edition 2024 --crate-type=lib mir_small.rs
cargo install cargo-llvm-lines   # then: cargo llvm-lines --release
```
