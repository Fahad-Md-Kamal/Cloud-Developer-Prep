# Rust Track: Plan and What Is Left

> **For whoever continues this (human or Claude Code, on any machine).**
> This file is **not** part of the site (it sits outside `docs/`). It records
> the plan, the finished work, the exact remaining pages, and the process that
> was used, so the work can continue on another PC without guessing.
> Read the root `CLAUDE.md` first. Its rules apply to every page.

**Goal.** A Rust learning track deep enough that a developer can follow it
from "never wrote Rust" to expert level. Stable version at the time of
writing: **Rust 1.99.1** (released 2026-10-15), **Cargo 0.100**, **edition
2024** (the latest edition; no newer one exists). Every page must be
**verified**: runnable code compiled and run on the current stable toolchain,
and real compiler error text, not remembered text.

---

## 1. Status

### Done (committed)

- New top-level nav domain **Rust**, folder `docs/rust/`, in `zensical.toml`
  (after Python) and in `docs/index.md` (section `### Rust`).
- `docs/rust/rust-learning-roadmap.md` — the old `docs/rust-learning-roadmap.md`
  **moved** here. It is still the **legacy text** (see task H below).
- **Foundations group, 11 pages** in `docs/rust/foundations/`:
  toolchain and cargo, ownership and borrowing, lifetimes, types/enums/patterns,
  error handling, collections and strings, traits and generics, iterators and
  closures, smart pointers, modules/crates/editions, testing and documentation.
- Runnable samples crate **`code_samples/rust/`** (package
  `rust-guru-samples`, edition 2024, `rust-version = "1.99"`):
    - `examples/*.rs` (run with `cargo run --example NAME`)
    - `compile_fail/*.rs` (files that must FAIL to compile; their error text is
      quoted in the pages)
    - `src/lib.rs` + `tests/integration.rs` (unit, integration, doc and
      property tests; `cargo test` passes: 8 + 2 + 3 tests)
- `scripts/generate_rust_nav.py` — regenerates the Rust nav in `zensical.toml`
  **and** the Rust section of `docs/index.md` from one page list. A page is
  listed only if its file exists.

### Written but **not yet used by a page** (samples exist, page missing)

These were compiled and run on 1.99.1 and are ready to be quoted:

| Sample | For page | Verified output (short) |
|---|---|---|
| `examples/memory_layout.rs` | memory layout & DSTs | default-repr struct 8 bytes vs `repr(C)` 12; `Option<Option<bool>>` = 1; `&[u8]`/`&str`/`&dyn` = 16; `Vec<()>` capacity is `usize::MAX`; `offset_of!` works |
| `examples/advanced_traits.rs` | advanced traits | typestate door, sealed trait, `Money<C>` is 8 bytes, GAT `LendingIterator` (`WindowsMut`), extension trait, `dyn Any` downcast |
| `compile_fail/invariant_mut_ref.rs` | variance & dropck | `E0597` because `&mut T` is invariant |
| `compile_fail/dropck_inspector.rs` | variance & dropck | `E0597` ... "borrow might be used here, when `world` is dropped and runs the destructor" |

### Known state of the site

- `zensical build --clean` currently reports **31 "page does not exist"
  warnings and nothing else**. They are **forward links** from the finished
  pages to pages that are not written yet. The build still exits with code 0, so
  GitHub Pages deploys. Each new page removes some warnings. **Target: zero.**
- `docs/rust/rust-learning-roadmap.md` is not yet the hub (task H).

---

## 2. Setup on a new machine

```bash
# 1. Rust (stable). Use rustup, not a distro package.
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup update stable          # must be >= 1.99
rustc --version               # expect 1.99.x or newer

# 2. Nightly + Miri (needed ONLY for the unsafe page)
rustup toolchain install nightly --profile minimal --component miri --component rust-src

# 3. Check the samples still pass
cd code_samples/rust
cargo test
cargo run --example ownership_moves

# 4. Site build (see CLAUDE.md §2)
pip install -r requirements.txt
python3 scripts/generate_nav_manifest.py
zensical build --clean        # if `zensical serve` is running, build in a copy
```

Also needed later: a C compiler (`cc`) for the FFI page, Docker for the
database page (PostgreSQL), and `wasm32-unknown-unknown` target for the
WebAssembly page (`rustup target add wasm32-unknown-unknown`).

**If the newest stable is no longer 1.99:** re-run the version checks (section
6) and update the "Version" note on every page. The rule in `CLAUDE.md` is to
always target the latest stable version.

---

## 3. The process used for every page (follow it)

1. **Write the sample first** in `code_samples/rust/examples/NAME.rs`. Keep it
   one file, small, with a header comment (`//!`) that says how to run it.
2. **Compile and run it** on current stable. Fix until it works. Keep the real
   output; quote it in the page.
3. **For every claim about a compiler error**, put a failing file in
   `code_samples/rust/compile_fail/` and capture the real message with
   `rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/FILE.rs`.
   (Use `--edition 2021` where the page is about an edition difference.)
4. **Verify anything version-specific** against the sources in section 6, not
   memory. My knowledge ended mid-2026; features from 1.97 to 1.99 were checked
   in `RELEASES.md`.
5. **Write the page** in `docs/rust/<group>/<file>.md` using the page template
   (section 4).
6. **Register it:** `python3 scripts/generate_rust_nav.py` (it is already
   listed there; it just starts including the file),
   then `python3 scripts/generate_nav_manifest.py`.
7. **Build:** `zensical build --clean` and read the warnings. Fix anchors.
   Count of "page does not exist" must go **down**.
8. **Commit** locally in small commits. When the user says "commit and push",
   squash all unpushed commits into one and push (CLAUDE.md §3).

---

## 4. Page template (from CLAUDE.md, applied to Rust)

- Front matter `title:` (full descriptive title). Nav label is short and is set
  in `scripts/generate_rust_nav.py`.
- Intro of 1 short paragraph: what the thing **is**, in plain words, before any
  question. Then a `!!! note "Version"` box: "Written for **Rust 1.99** and the
  **2024 edition**", plus what was verified.
- Numbered Q&A sections: `## N. "Realistic interview-style question?"`, each
  with a bullet **Answer:**. Code block first for mechanical questions.
- **Fundamentals before comparisons.** Say what X and Y are before "X vs Y".
- Real compiler errors quoted from section 3 step 3. Tables for comparisons.
- **Spell out every abbreviation on first use** (RAII, SIMD, ABI, FFI, ...).
- **Plain vocabulary**, short bullets, one idea each, lead with the core idea.
- Cross-link instead of repeating: relative links such as
  `[Lifetimes §5](rust-lifetimes.md#5-what-does-static-mean-it-has-two-meanings)`.
  Anchors are the heading text, lowercased, punctuation removed, spaces to `-`.
  Check with the build.
- A section **"How do AI tools help or hurt here?"** with concrete, topic-specific
  advice (not generic). Link
  `[Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md)`.
- `## N. Interview Questions You're Likely to Get Asked`, grouped under bold
  mini-headers, each item: quoted question — expects [answer], [§ link].
- Last: `---` then **`## Code Samples`** listing the real files and the exact
  `cargo run --example ...` commands.
- Markdown bugs to avoid (CLAUDE.md §7): blank line before every table; escape
  `|` as `\|` inside table cells; no blank lines/`<style>`/comments inside raw
  HTML; use double-backtick spans when an inline code span contains backticks.

---

## 5. Remaining pages (25) and the roadmap hub

**File names, nav labels and descriptions are already fixed** in
`scripts/generate_rust_nav.py`. The finished pages **already link to these exact
file names** (that is why the build shows 31 dangling links), so **do not rename
them**. Each entry below: path under `docs/rust/`, then what it must cover, the
sample to write, and facts to verify.

### Group: Advanced Language (`advanced-language/`)

**A1. `rust-memory-layout-and-dsts.md`** — sample done (`memory_layout.rs`).
Cover: stack/heap/static; size and alignment; padding and why the default
`repr(Rust)` **reorders fields** (8 vs 12 bytes); `repr(C)`, `repr(packed)`
(references to packed fields are a problem), `repr(align)`, `repr(u8)` enums,
`repr(transparent)`; enum layout (tag + payload); **niche optimization** with
the printed table; thin vs fat pointers (`&[T]`, `&str`, `&dyn`, `Box<dyn>`,
`Rc<str>`); `Sized` and `?Sized`; DSTs and `size_of_val`; ZSTs (`Vec<()>` never
allocates, capacity `usize::MAX`); `mem::offset_of!`; `Layout` and the
allocator API at a glance; layout is **not guaranteed** for `repr(Rust)`.
Verify: `core::mem::size_of_val_raw` and `align_of_val_raw` are stable in 1.99.

**A2. `rust-advanced-traits-and-type-level-design.md`** — sample done
(`advanced_traits.rs`). Cover: typestate builder; sealed traits; `PhantomData`
unit markers; GATs and the lending iterator (why `Iterator` cannot do
overlapping `&mut` windows); higher-ranked trait bounds with closures; extension
traits; `dyn Any` and downcasting; associated consts; marker traits; blanket-impl
coherence and the orphan rule revisited; trait objects with generics; what is
**still unstable** (specialization, trait aliases) with a stable alternative for
each. Verify: current GAT limits; `async fn` in traits and `dyn` (not dyn
compatible); return-position `impl Trait` in traits.

**A3. `rust-variance-dropck-and-phantomdata.md`** — compile_fail files done;
write a run sample `examples/variance_phantom.rs`. Cover: subtyping exists only
for lifetimes; **covariance** (`&'a T`, `Vec<&'a T>`), **invariance** (`&mut T`,
`Cell<&'a T>`, `*mut T`), **contravariance** (`fn(&'a T)`); the printed
`invariant_mut_ref` error; how variance is computed for a struct; the **drop
checker** with `dropck_inspector` and `#[may_dangle]` (unstable, used by std);
`PhantomData<T>` jobs (variance, drop-check ownership, auto traits);
`PhantomData<*const ()>` to opt out of `Send`/`Sync`; auto traits `Send`/`Sync`
rules and `unsafe impl`; negative reasoning. Source: the Nomicon chapters on
subtyping, drop check and PhantomData (raw GitHub `rust-lang/nomicon`, `master`,
`src/`).

**A4. `rust-unsafe-and-miri.md`** — needs samples and nightly Miri
(section 2). Cover: the five unsafe powers (deref raw pointer, call unsafe fn,
access `static mut`, implement unsafe trait, access union fields); `unsafe`
**blocks vs `unsafe fn` vs `unsafe trait`**; the contract idea and `# Safety`
docs; **undefined behaviour** list (dangling, aliasing violations, invalid
values such as `bool = 3`, data races, uninit reads); safe abstractions around
unsafe (re-implement `split_at_mut` with `slice::from_raw_parts_mut`,
a small `Vec`-like type with `NonNull` + `Layout`); `MaybeUninit` (1.92 documented
its representation and validity), `ManuallyDrop`, `mem::transmute` dangers;
**provenance** and `with_exposed_provenance`/`NonNull` APIs stabilized in 1.89
to 1.91; aliasing models (**Stacked Borrows vs Tree Borrows**; check which is
Miri's current default); `&raw const`/`&raw mut`; edition 2024 changes
(`unsafe_op_in_unsafe_fn` warn, `unsafe extern`, `#[unsafe(no_mangle)]`, `static mut`
references denied, `env::set_var` unsafe). **Run real UB under Miri**
(`cargo +nightly miri run --example ...`) and quote the Miri message for: out-of-bounds
read, use after free through a raw pointer, invalid `bool`, aliasing violation.
Also `cargo miri test`, sanitizers, `cargo-careful`, `loom` pointer.

**A5. `rust-ffi-and-c-interop.md`** — needs a small package
`code_samples/rust/ffi_demo/` (own `Cargo.toml`, `crate-type = ["cdylib",
"staticlib"]`) plus `demo.c` and `build.sh` that compiles the C file against the
library and runs it. Cover: `unsafe extern "C" { safe fn ...; fn ...; }` blocks
(2024 syntax); calling libc (`strlen`, `qsort` with a callback); `#[repr(C)]`
structs; `CString`/`CStr`; `#[unsafe(no_mangle)] pub extern "C" fn`; **ownership
across the boundary** (who frees what; `Box::into_raw`/`from_raw`; opaque handles);
**panics must not unwind into C** (`extern "C"` aborts; `extern "C-unwind"`);
error codes and out-parameters; `bindgen` and `cbindgen`; **PyO3 and maturin**
(Python), `napi-rs` (Node), `uniffi` (Kotlin/Swift); C-variadic functions
(definitions stabilized in 1.99); linking (`build.rs`, `cargo::rustc-link-lib`).
Verify the 2024 `unsafe extern` syntax by compiling.

**A6. `rust-macros.md`** — needs two small crates under
`code_samples/rust/macros_demo/` (a proc-macro crate with `syn`, `quote`,
`proc-macro2`, and a binary using it; add with `cargo add` to get current
versions). Cover: `macro_rules!` (fragment specifiers, repetition `$(...),*`,
recursion, **tt-muncher**, internal rules, `$crate`, **hygiene**); the 2024
`expr` fragment change and `expr_2021`; derive macros (write `#[derive(Describe)]`
that lists field names); attribute macros (`#[timed]` wrapping a function);
function-like proc macros; token streams; error reporting with `compile_error!`
and spans; `cargo expand`; proc-macro crates must be their own crate
(`proc-macro = true`) and **compile first**, with the build-time cost;
`#[my_macro] mod foo;` stabilized in 1.99; when **not** to use a macro.

### Group: Concurrency & Async (`concurrency-and-async/`)

**C1. `rust-threads-and-synchronization.md`.** Sample: `threads_sync.rs`.
Cover: `thread::spawn` and `JoinHandle`; **scoped threads** (`thread::scope`) and
the `E0373` error already shown on the lifetimes page; `Send` and `Sync` as auto
traits, why `Rc` and `RefCell` are not; `Arc<Mutex<T>>`, **lock poisoning**,
`RwLock` (and `RwLockWriteGuard::downgrade`, stable in 1.92), `Condvar`, `Barrier`,
`OnceLock`; channels (`mpsc`, `sync_channel`; note `crossbeam-channel`); deadlock
examples and lock ordering; edition 2024 `if let` temporary scope fixing a deadlock;
data parallelism with **rayon** (`par_iter`); thread-local storage;
`std::sync::Exclusive`-like patterns only if stable; `File::lock` (1.89); false sharing.
Show a real data race attempt failing to compile.

**C2. `rust-atomics-and-memory-ordering.md`.** Sample: `atomics.rs` (counter,
spinlock, a flag handoff with `Release`/`Acquire`, a CAS loop, `fetch_update`,
and the new `update`/`try_update` methods stabilized in 1.95). Cover: why atomics
exist; `Relaxed`, `Acquire`, `Release`, `AcqRel`, `SeqCst` with plain-language
**happens-before**; the compiler and CPU reordering model; `compare_exchange`
vs `_weak`; the ABA problem; `AtomicPtr` new methods (1.91); `Atomic<T>` generic
type and `from_mut` (1.98: verify what is stable); `std::hint::spin_loop`; why
`Mutex` is usually better; testing with **loom**. Source: std docs for
`std::sync::atomic` and the book *Rust Atomics and Locks* (free online).

**C3. `rust-async-internals.md`.** Sample: `async_executor.rs` — a tiny
single-threaded executor with a custom `Waker`, built with std only, plus a manual
`Future` (a timer or a countdown). Cover: what `async fn` compiles to (a state
machine, a type that implements `Future`); `Poll`, `Context`, `Waker`; **why
`Pin` exists** (self-referential state), `Unpin`; `async` blocks and `.await`;
futures are **lazy** and **cancelled by dropping**; `async fn` in traits and the
`dyn` limit; **async closures** (`AsyncFn*`, stable 1.85); cost: future size
(`size_of_val` a future), `Box::pin`; runtimes are libraries (Tokio, async-std
status, smol); `Send` futures and the "future cannot be sent between threads"
error (capture an `Rc` across `.await` to reproduce it). Verify the current
state of the official async book (raw GitHub `rust-lang/async-book`, `master`).

**C4. `rust-tokio-and-async-patterns.md`.** Sample: `tokio_patterns.rs` (add
`tokio` with `cargo add`). Cover: `#[tokio::main]` and runtime flavors
(multi-thread vs current-thread); `spawn`, `JoinSet`, `JoinHandle` and `JoinError`;
`select!` and **cancellation safety**; `timeout`; channels (`mpsc`, `oneshot`,
`broadcast`, `watch`); **backpressure** with bounded channels and `Semaphore`;
**graceful shutdown** with `CancellationToken` or a watch channel; blocking work
(`spawn_blocking`) and **never block the executor**; shared state
(`Arc<Mutex<_>>` vs actor with a channel); async `Mutex` vs std `Mutex`; streams
(`futures`/`tokio-stream`); structured concurrency; common deadlocks (holding a
std `MutexGuard` across `.await`, and the compiler error for it); testing with
`#[tokio::test]` and paused time.

### Group: Performance & Internals (`performance-and-internals/`)

**P1. `rust-performance-engineering.md`.** Samples with real measurements on the
author's machine (say so): `bench_demo.rs` or a `criterion`/`divan` bench.
Cover: **measure first** (release builds only; `black_box`); benchmarking with
`criterion` or `divan`; profiling (`perf`, `cargo flamegraph`, `samply`, Instruments
on macOS); allocation cost and `dhat`; `with_capacity`; `Vec` vs `HashMap` for small
data; cache locality, struct-of-arrays; iterator vs loop (zero-cost claim measured);
`#[inline]`, `#[cold]`, `core::hint::cold_path` (stable 1.95), `select_unpredictable`
(1.88); bounds-check removal; SIMD (auto-vectorization, `std::arch`, `portable_simd`
status); release tuning (`lto`, `codegen-units`, `opt-level`, `panic=abort`, PGO,
`-C target-cpu`); linker speed (lld default on x86_64 Linux since 1.90); compile
time (see P2). Include a worked "make this slower program 10x faster" example with
before and after numbers.

**P2. `rustc-how-the-compiler-works.md`.** Cover the pipeline: parsing → AST →
macro expansion → name resolution → **HIR** → type checking and trait solving →
**THIR** → **MIR** (borrow checking runs on MIR; **NLL**; **Polonius** and the
**next-gen trait solver** are not stable: verify current status) → monomorphization →
LLVM IR → machine code → linking; incremental compilation and the query system;
how generics blow up code size (`cargo llvm-lines`, `cargo bloat`); why compile times
are long and the fixes (fewer generics, `cargo check`, workspaces, `lld`, `mold`,
Cranelift on nightly, `sccache`, `-Zthreads` is nightly, `cargo build --timings`);
`--emit=mir,asm,llvm-ir` and Compiler Explorer; const evaluation and `const fn`
(1.93 made const-eval copy pointers byte by byte); lints and `clippy`; what an
`rlib` is; `-C` and `-Z` flags. Source: the rustc-dev-guide (raw GitHub
`rust-lang/rustc-dev-guide`).

**P3. `rust-no-std-and-embedded.md`.** Cover: `core` vs `alloc` vs `std`;
`#![no_std]`, `#![no_main]`; panic handlers; global allocators; `heapless`;
interrupts and volatile access (`read_volatile`; volatile to non-Rust memory is
allowed since 1.90); the embedded HAL ecosystem (`embedded-hal`, `embassy`,
`probe-rs`); targets (`thumbv7em-none-eabihf`); `cargo build --target`; testing
without hardware. Sample: a `#![no_std]` library crate that compiles for a bare
target (`rustup target add thumbv7em-none-eabihf`; `cargo build --target ...`).

**P4. `rust-webassembly.md`.** Cover: targets (`wasm32-unknown-unknown`,
`wasm32-wasip1`/WASI; verify current target names); `wasm-bindgen`, `wasm-pack`,
`trunk`; size tuning (`opt-level = "z"`, `lto`, `wasm-opt`); calling JS and being
called; `extern "C"` ABI on `wasm32-unknown-unknown` is now standards compliant
(1.89); Rust as a WASM component (`wit-bindgen`, component model) at a high level;
limits (threads, I/O). Sample: a function compiled to wasm and run from a tiny JS
or Node script.

### Group: Production Rust (`production/`)

For all production pages: use `cargo add` to get **current** crate versions, state
those versions on the page, and run every sample. Use Docker for PostgreSQL.

**R1. `rust-web-services-with-axum.md`.** Cover: Tokio + hyper + **tower**;
Axum routing, extractors, `State`, `Json`, error type implementing `IntoResponse`,
middleware via `tower` layers, graceful shutdown, timeouts, tracing layer, testing
with `tower::ServiceExt::oneshot`. Compare with Actix-web and Rocket briefly.
Sample: a small CRUD API with tests.

**R2. `rust-databases.md`.** Cover: `sqlx` (compile-time checked queries, pools,
transactions, migrations), Diesel, SeaORM; connection pool sizing; repository
pattern; N+1; running Postgres in Docker; migrations. Sample against Dockerized
Postgres.

**R3. `rust-serde-and-serialization.md`.** Cover: the data model (Serializer /
Deserializer, visitors); derive and its attributes (`rename_all`, `default`,
`flatten`, `tag`, `untagged`, `skip_serializing_if`); zero-copy borrowing
(`#[serde(borrow)]`, `for<'de>`, `DeserializeOwned`); custom `Serialize`/`Deserialize`;
formats (JSON, TOML, YAML, bincode, postcard, MessagePack); performance and
untrusted input limits. Sample: round trips and a custom deserializer.

**R4. `rust-observability.md`.** Cover: `tracing` (spans, events, fields),
`tracing-subscriber`, JSON logs, `#[instrument]`, OpenTelemetry export, metrics
(`metrics` crate or OTel), async spans, panics and backtraces.

**R5. `rust-project-architecture-and-api-design.md`.** Cover: workspace layout and
crate boundaries; hexagonal/ports-and-adapters in Rust; the **Rust API Guidelines**
checklist (naming, `From`/`AsRef`, `#[non_exhaustive]`, sealed traits); SemVer rules
and `cargo semver-checks`; error boundaries; builders; feature flags; MSRV policy;
documentation standards; deprecation.

**R6. `rust-cli-and-systems-programming.md`.** Cover: `clap` (derive), exit codes,
`std::process::Command`, `std::fs` and `std::io` (`BufRead`, `Read`/`Write`), file
locking (`File::lock`, 1.89), signals (`ctrlc`/`signal-hook`), memory-mapped files,
environment, terminal UI (`ratatui`) pointer, `anyhow`. Sample: a small `grep`-like
tool.

**R7. `rust-ci-cd-and-supply-chain.md`.** Cover: CI pipeline (fmt, clippy `-D
warnings`, test, doc, `--locked`); caching (`Swatinem/rust-cache`, `sccache`);
`cargo deny`, `cargo audit`, `cargo vet`; reproducible builds and
`--remap-path-scope` (1.95); cross-compilation (`cross`, `cargo zigbuild`); minimal
containers (distroless, `scratch` with musl; `FROM rust` multi-stage; `cargo
chef`); release automation (`cargo release`, `cargo dist`); publishing and
**yanking**; build-script risk; `cargo publish` multi-package (1.90). Sample:
`.github/workflows` example under `code_samples/rust/` (do not activate it) and a
multi-stage Dockerfile that builds and runs.

### Group: Mastery (`mastery/`)

**M1. `modern-rust-2024-to-1-99.md`.** Release-by-release notes from 1.85 to
1.99 from `RELEASES.md`, grouped by theme, each item with a one-line example.
Use the digest in section 7. Add "what to stop doing" (old idioms replaced).

**M2. `rust-for-python-go-and-kotlin-developers.md`.** Translation tables
(idiom → Rust), the traps for each background (Python: no GIL but ownership;
Go: no goroutine-style implicit sharing, `Result` vs `err`; Kotlin: nullability
vs `Option`, coroutines vs async), and when to **choose** Rust vs each. Reuse the
useful material from the legacy roadmap (section H).

**M3. `rust-capstone-projects.md`.** Ten graded projects (CLI grep clone, markdown
to HTML, KV store with WAL, HTTP server from `std::net`, async chat server,
thread pool, interpreter, arena allocator, lock-free queue verified with loom, a
tiny async runtime). For each: goal, concepts exercised (with links to pages),
acceptance tests, stretch goals, and the page it depends on. Put reference
solutions (or at least skeletons that compile) under `code_samples/rust/capstones/`.

**M4. `rust-guru-question-bank.md`.** 80 to 120 hard questions with strong
answers, grouped by topic and linked to the sections that teach them. Include
"predict the output / predict the compile error" items and design questions.

### H. The hub: `rust/rust-learning-roadmap.md`

The file is currently the **legacy roadmap** (Levels 0 to 4, ecosystem cheat
sheet, resources, timeline). Rewrite it as the **hub**:

- Keep the good parts: why Rust and when not; the ecosystem cheat sheet; the
  resources list; the timeline.
- Replace the level bullets with **links to the pages in this track**, in
  learning order, with a time estimate per group and a checkpoint project per
  group (point to the capstones).
- Add: how to practice (Rustlings, Exercism, Advent of Code, reading the std
  source), the official books to read alongside (The Book, Rust by Example, the
  Reference, the Rustonomicon, the Async Book, the Cargo Book, *Rust for
  Rustaceans*, *Programming Rust*, *Rust Atomics and Locks*, the Edition Guide),
  and a "guru checklist" of skills to be able to demonstrate.
- Follow the page template (section 4). Today it is paragraph-heavy and does
  not follow the bullet style.

---

## 6. Sources and how to read them (they work without a browser)

| Need | Where |
|---|---|
| Release notes (verified through 1.99.1) | `https://raw.githubusercontent.com/rust-lang/rust/master/RELEASES.md` |
| Latest stable version | `https://static.rust-lang.org/dist/channel-rust-stable.toml` (see `date` and `[pkg.cargo]`) |
| The Book | `https://raw.githubusercontent.com/rust-lang/book/main/src/` |
| The Reference | `https://raw.githubusercontent.com/rust-lang/reference/master/src/` |
| Nomicon (unsafe, variance, dropck) | `https://raw.githubusercontent.com/rust-lang/nomicon/master/src/` |
| Async Book | `https://raw.githubusercontent.com/rust-lang/async-book/master/src/` |
| Edition Guide | `https://raw.githubusercontent.com/rust-lang/edition-guide/master/src/` |
| rustc dev guide | `https://raw.githubusercontent.com/rust-lang/rustc-dev-guide/master/src/` |
| Cargo book | `https://doc.rust-lang.org/cargo/` (the raw GitHub path moved, so use the rendered pages) |
| Standard library docs | `https://doc.rust-lang.org/std/` (rendered pages fetch fine) |

`doc.rust-lang.org` pages are HTML: fetch and strip tags (a 15-line Python
helper using `urllib` and `re` was enough), then `grep`.
GitHub's API is rate limited without a token; prefer `raw.githubusercontent.com`.

---

## 7. Digest of Rust 1.85 → 1.99 (for page M1 and for fact checks)

Verified from `RELEASES.md`. **Language**:

- **1.85**: the **2024 edition** stable; **async closures** (`AsyncFn*`);
  `#[diagnostic::do_not_recommend]`.
- **1.86**: **trait object upcasting**; safe functions may use `#[target_feature]`;
  `missing_abi` lint warns.
- **1.87**: `asm_goto`; **precise capturing (`use<..>`) in traits**.
- **1.88**: **let chains** (edition 2024); **naked functions**; `cfg` boolean
  literals; `#[bench]` fully de-stabilized.
- **1.89**: explicitly inferred const args (`_`); `mismatched_lifetime_syntaxes`
  lint (warn); `dangerous_implicit_autorefs` deny; `repr(u128/i128)`; avx512
  target features; temporary lifetime extension through tuple-struct constructors.
- **1.90**: **`lld` is the default linker** on `x86_64-unknown-linux-gnu`; volatile
  access to non-Rust memory allowed.
- **1.91**: pattern-binding drop order defined; C-variadic declarations for more
  ABIs; `dangling_pointers_from_locals` and `integer_to_ptr_transmutes` lints.
- **1.92**: `MaybeUninit` representation documented; never-type fallback lints
  deny by default; `#[track_caller]` with `#[no_mangle]`.
- **1.93**: const-eval can copy pointers byte by byte; `const_item_interior_mutations`
  and `function_casts_as_integer` lints.
- **1.94**: Unicode 17; `unused_visibilities` lint.
- **1.95**: **`if let` guards** in `match`; `irrefutable_let_patterns` ignores
  let chains; `cfg_select!`; `--remap-path-scope`.
- **1.96**: `expr` metavariable allowed in `cfg`; never types coerce in tuples.
- **1.97**: `Result<T, Uninhabited>` counts as `T` for `must_use`;
  `dead_code_pub_in_binary` lint.
- **1.98**: shorten `&mut` lifetime during unsizing even when invariant;
  `invalid_runtime_symbol_definitions` (deny).
- **1.99**: **C-variadic function definitions** stable; `#[my_macro] mod foo;`;
  `UnsafeCell` contents reachable without `get` is guaranteed; new built-in Cargo
  profile `debug`.

**Notable library APIs**: `LazyCell/LazyLock::{get,get_mut,force_mut}` (1.94),
`core::range::{Range, RangeInclusive, RangeFrom, ...}` (1.95/1.96; **Copy**, not
iterators themselves; verified `std::range::Range` is `Copy` and `.into_iter()`
works), `assert_matches!` / `debug_assert_matches!` (1.96, used as
`std::assert_matches!`), `fmt::from_fn` (1.95), `Vec::push_mut`/`insert_mut`
(1.95), `core::hint::cold_path` (1.95), atomics `update`/`try_update` (1.95),
`Vec::extract_if` (1.87), `HashMap::extract_if` (1.88), `BTreeMap::extract_if`
(1.91), `Cell::update` (1.88), `Result::flatten` (1.89), `File::lock` family
(1.89), `{integer}::strict_*` (1.91), `RwLockWriteGuard::downgrade` (1.92),
`Box::new_zeroed` (1.92), `bool::ok_or` and `Option/Result::map_or_default` (1.98),
`VecDeque::retain_back`, `Vec::into_parts` (1.99).

**Cargo**: resolver `"3"` (MSRV-aware) default for edition 2024; multi-package
`cargo publish` (1.90); `build.build-dir` (1.91); config `include` (1.94);
auto garbage collection (1.88); `[profile.debug]` (1.99); workspace members on
2024+ can override inherited `default-features` (1.99).

**Not stable as of 1.99 (verify before writing)**: Polonius, the next-gen trait
solver, specialization, `gen` blocks, parallel front end (`-Zthreads`),
Cranelift as a stable backend.

---

## 8. Other tasks

1. **Hygiene of the finished samples.** Run `cargo clippy --all-targets -- -D
   warnings` and `cargo fmt` in `code_samples/rust/`. Known warnings:
   `dead_code` in `examples/ownership_patterns.rs` (fields never read). Fix by using
   the fields in a `println!`.
2. Add `code_samples/rust/README.md` (how to run examples, what each is for).
3. **Docs updates once the track is complete:**
    - `CLAUDE.md` §1: "Current top-level domains" list **already needs Rust added**
      (done in this commit: check it still reads correctly).
    - `docs/index.md`: the intro bullets and "What this covers" should mention
      Rust; `zensical.toml` `site_description` too.
    - `docs/README.md`: the domain list.
    - Add a Rust section link from `interview-prep` if useful.
4. Regenerate the PDF manifest after every nav change:
   `python3 scripts/generate_nav_manifest.py`.
5. **Done =** `zensical build --clean` prints **"No issues found"**; every
   `cargo run --example` works on current stable; `cargo test` and clippy are
   clean; every compile error quoted on a page has a file in `compile_fail/`;
   every page follows the template; version notes match the stable version.

## 9. Git

- Commit locally as you go. When the owner says **"commit and push"**, squash
  all unpushed commits into one, then push (CLAUDE.md §3).
- No `Co-Authored-By` or other AI-attribution trailer.
- Temporary Rust installs used while writing lived outside the repo. Nothing
  under `code_samples/rust/target/` is committed (it is git-ignored).
