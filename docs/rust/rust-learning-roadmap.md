# Rust Learning Roadmap: Beginner to Professional

Coming from Python/Go/Kotlin, the one new idea the whole language is
built around is **ownership** — everything else here either sets that
up or builds on it. This roadmap runs from "never written a line of
Rust" through to what a production Rust codebase actually looks like,
in four levels, each with a project to force the concepts to stick.

## Level 0: Before You Start

**Why Rust, concretely** — it gives you memory safety and
thread-safety *guarantees* without a garbage collector, enforced by
the compiler at build time instead of caught by tests or production
incidents. That's the actual trade Rust is making: a harder, slower
compile-time learning curve in exchange for removing an entire class
of bugs (use-after-free, data races, null pointer dereferences) that
Python/Go/Kotlin either don't have to think about (GC) or only catch
at runtime (Go's race detector).

- **Reach for Rust when**: raw performance matters (systems tools,
  game engines, high-throughput services), you need predictable
  low-latency behavior a GC's pause times can't give you, you're
  targeting WebAssembly, or you're writing something safety-critical
  (embedded, OS-level code).
- **Don't reach for Rust when**: you're prototyping fast, the team
  doesn't have time to absorb the learning curve, or the workload is
  I/O-bound and a GC's overhead was never the bottleneck anyway — this
  is most backend CRUD APIs, where Python/Go are a faster path to
  shipping.
- **Setup**: `rustup` (the toolchain installer/version manager — the
  `pyenv`/`nvm` equivalent), `cargo` (bundled — build tool, package
  manager, and test runner all in one, unlike Python's separate
  pip/venv/pytest). Editor: VS Code + `rust-analyzer` extension for
  real-time type/borrow-checker feedback as you type.
- Play with syntax with zero local setup first: the
  [Rust Playground](https://play.rust-lang.org/).

## Level 1: Beginner — The Core Language

### 1.1 Ownership, Borrowing & Lifetimes

- **Ownership**: every value has exactly one owner; the value is freed
  the instant that owner goes out of scope — no garbage collector, no
  manual `free()` either. Assigning or passing a non-`Copy` value
  *moves* it — the old variable becomes invalid, not a second
  reference to the same data the way Python assignment would be.
- **Borrowing** (`&T`, `&mut T`): lets code *use* a value without
  taking ownership. The compiler enforces, at compile time: any number
  of immutable borrows, *or* exactly one mutable borrow, never both at
  once — this single rule is what eliminates data races before the
  program ever runs.
- **The borrow checker** will reject code that looks obviously fine to
  someone coming from a GC'd language. Expect to lose a week fighting
  it — that's the normal learning curve, not a sign of doing something
  wrong. Read the compiler's error messages closely; they're
  unusually good at explaining exactly what rule was violated.
- **Lifetimes** (`'a`): explicit annotations for the cases where the
  compiler can't automatically prove a reference stays valid long
  enough on its own. Most code never needs them written out — the
  compiler infers them — but function signatures returning a
  reference, and structs holding one, often do.

### 1.2 Types, Structs, Enums & Pattern Matching

- Scalar types (`i32`, `u64`, `f64`, `bool`, `char`), tuples, arrays
  vs. the growable `Vec<T>`.
- `struct` for grouped data (closest to a Python `dataclass` or a Go
  struct).
- `enum` — genuinely more powerful than Python's `Enum` or Go's
  `iota`-based constants: each variant can carry its own differently-
  shaped data (`enum Shape { Circle(f64), Rectangle(f64, f64) }`),
  making it a real sum/algebraic type, not just a labeled constant.
- `match` — exhaustive pattern matching; the compiler forces every
  variant to be handled (or an explicit `_` catch-all), which is what
  makes `enum` + `match` together Rust's primary tool for modeling
  "one of several possible states" safely.

### 1.3 Error Handling: `Result` and `Option`

- No exceptions, no `null`. A function that can fail returns
  `Result<T, E>` (`Ok(value)` or `Err(error)`); a value that might be
  absent is `Option<T>` (`Some(value)` or `None`).
- The `?` operator propagates an `Err`/`None` up to the caller in one
  character, the idiomatic alternative to Go's `if err != nil {
  return err }` repeated after every call.
- The compiler forces you to handle (or deliberately ignore via
  `.unwrap()`/`.expect()`) every `Result`/`Option` — an error can't
  silently vanish the way an uncaught exception's stack trace can get
  swallowed elsewhere.

### 1.4 Collections & String Handling

- `Vec<T>` (growable array), `HashMap<K, V>`, `HashSet<T>` — the
  everyday collections, directly comparable to Python's list/dict/set.
- `String` (owned, heap-allocated, growable) vs. `&str` (a borrowed
  view into string data — could point into a `String`, a string
  literal, or part of either). This split is ownership applied
  directly to the most common type in the language, and the single
  most common beginner confusion.

**Project**: a command-line calculator or a simple word-frequency
counter reading a text file — enough to touch ownership, `Result`,
collections, and string handling together without anything else in
the way.

## Level 2: Intermediate — Writing Idiomatic Rust

### 2.1 Traits & Generics

- **Traits** are Rust's interfaces — a set of methods a type promises
  to implement. Closer to Go's implicit "has the right methods"
  satisfaction than Java/Kotlin's explicit `implements`, but Rust
  traits are declared explicitly (`impl TraitName for MyType`).
- **Generics** (`fn largest<T: PartialOrd>(list: &[T]) -> T`) write
  one function/struct that works across multiple types, with trait
  bounds constraining *which* types are actually allowed.
- `dyn Trait` vs. generics: generics are resolved at compile time
  (zero runtime cost, but one compiled copy per concrete type used —
  "monomorphization"); `dyn Trait` is resolved at runtime via a vtable
  (one shared compiled version, small runtime dispatch cost) — the
  real trade-off to know for an interview: compile-time speed/binary
  size vs. runtime flexibility.

### 2.2 Iterators & Closures

- Iterator chains (`.iter().map(...).filter(...).collect()`) —
  functional in style like a Python comprehension, but **lazy**: a
  `.map()` does nothing until something actually consumes the
  iterator (a `for` loop, `.collect()`, `.sum()`), closer to a Python
  generator than a list comprehension in that respect.
- Closures (`|x| x + 1`) capture their environment automatically; the
  compiler infers *how* (by reference, mutable reference, or by
  value/move) from how the closure's body actually uses each captured
  variable — explicit `move` forces capture by value when needed
  (commonly, handing a closure off to another thread).

### 2.3 Smart Pointers & Interior Mutability

- `Box<T>` — a value on the heap instead of the stack; needed for
  recursive types (a type that contains itself) and for storing a
  `dyn Trait` value, since its size isn't known at compile time.
- `Rc<T>` — reference-counted shared ownership, single-threaded only.
  `Arc<T>` — the thread-safe equivalent (atomic reference counting),
  used anywhere shared ownership crosses threads.
- `RefCell<T>` — interior mutability: lets you mutate data through a
  shared (`&`) reference by moving the borrow-checking from compile
  time to *runtime* (panics if the rules are violated at runtime
  instead of refusing to compile) — the escape hatch for the genuinely
  rare cases the compile-time borrow checker is too conservative for.

### 2.4 Modules, Crates & the Cargo Ecosystem

- A **crate** is a compilation unit (a library or binary) — Rust's
  equivalent of a Python package or Go module. `Cargo.toml` declares
  dependencies, pulled from [crates.io](https://crates.io) (the
  PyPI/npm equivalent).
- `mod` organizes code within one crate into a module tree;
  `pub`/private visibility is explicit and enforced per-item, stricter
  by default than Python's underscore convention.
- `cargo doc --open` generates and opens browsable API docs from
  doc-comments (`///`) — built into the toolchain, no separate Sphinx-
  style setup needed.

### 2.5 Testing

- `#[test]` functions plus `cargo test` — built directly into the
  toolchain and standard library, no separate pytest-equivalent
  dependency required.
- Unit tests commonly live in a `#[cfg(test)] mod tests` block at the
  bottom of the same file as the code under test; integration tests
  live in a separate top-level `tests/` directory, testing the crate's
  public API only, the same "test the contract, not the internals"
  split as a well-organized Python/Go test suite.
- Doc-comments with embedded code examples are run as tests too
  (`cargo test` executes them) — documentation that silently goes
  stale and stops matching the real API is structurally harder here.

**Project**: a CLI tool with real subcommands (`clap` for argument
parsing), its own unit + integration tests, published as a usable
binary via `cargo install --path .`.

## Level 3: Advanced — Concurrency & Systems-Level Rust

### 3.1 Fearless Concurrency: Threads, Channels, `Arc<Mutex<T>>`

- `std::thread::spawn` for OS threads; `mpsc` (multi-producer,
  single-consumer) channels to pass data between them, the same
  "share memory by communicating" instinct as Go's channels.
- The ownership/borrowing rules extend into concurrency: the compiler
  refuses to compile code that would let two threads mutate the same
  data unsynchronized — most data races are caught at compile time
  instead of needing a separate tool like Go's `-race` detector.
- `Arc<Mutex<T>>` is the standard shared-mutable-state pattern —
  directly comparable to Go's `sync.Mutex`, except the type system
  physically prevents touching the locked data without holding the
  lock first (there's no way to even *reach* the `T` inside without
  going through `.lock()`).

### 3.2 Async Rust: Tokio, Futures, `async`/`await`

- `async fn` returns a `Future` that does nothing until it's actually
  `.await`ed or handed to a runtime — conceptually close to Python's
  `asyncio` coroutines, but Rust has no built-in runtime; **Tokio** is
  the de facto standard one (comparable to picking an event loop
  implementation yourself).
- Needed for essentially any real web service or network-heavy tool —
  the ecosystem (Axum, most database drivers, `reqwest` for HTTP
  clients) assumes an async runtime is already running.
- Common early trap: mixing blocking, synchronous code (heavy CPU
  work, blocking file I/O) directly inside an `async` function stalls
  the whole runtime's thread — blocking work needs
  `tokio::task::spawn_blocking` to move it off the async executor.

### 3.3 Unsafe Rust & FFI

- `unsafe` unlocks a small set of operations the compiler can't verify
  are safe (raw pointer dereferencing, calling foreign/C functions,
  mutable access to statics) — it does **not** turn off the borrow
  checker everywhere, just inside that specific block, and the
  programmer is now personally responsible for upholding the
  invariants the compiler would otherwise enforce.
- FFI (calling C libraries, or being called from C/Python/Node via a
  native extension) is the most common real reason to reach for
  `unsafe` in application code — most other application-level Rust
  never needs it at all.

### 3.4 Macros: Declarative & Procedural

- **Declarative macros** (`macro_rules!`) — pattern-match on the
  tokens passed in and generate code, Rust's answer to avoiding
  repetitive boilerplate without a preprocessor.
- **Procedural macros** — run arbitrary code at compile time to
  generate code; `#[derive(Debug, Clone, Serialize)]` is the most
  common form every Rust developer uses constantly without writing one
  themselves. Writing a custom proc macro is a genuinely advanced,
  rarely-needed skill — know what they are and why `#[derive(...)]`
  works before attempting to write your own.

### 3.5 Performance: Profiling, Benchmarking, Release Builds

- `cargo build --release` (optimizations on, debug assertions off) vs.
  a plain `cargo build` (fast to compile, slow to run) — a debug build
  can be an order of magnitude slower; never benchmark or ship a
  debug build.
- `criterion` crate for real statistical benchmarking (handles warm-up,
  noise, outliers) instead of hand-rolled timing.
- `cargo flamegraph` for CPU profiling — the Rust-ecosystem equivalent
  of `py-spy`/`pprof`, pointing at exactly which function is actually
  consuming the time before optimizing blind.

**Project**: a concurrent tool that touches all three — a multi-
threaded or async web scraper/crawler with shared state (a visited-URL
set behind `Arc<Mutex<_>>`, or fully async with Tokio), profiled once
it's correct.

## Level 4: Professional — Production Rust

### 4.1 Web Services

- **Axum** or **Actix-web** — the Django/FastAPI-shaped layer:
  routing, extractors (pulling typed data out of a request, similar
  role to FastAPI's dependency injection), middleware, and JSON
  (de)serialization via **serde** (the universal serialization crate
  — `#[derive(Serialize, Deserialize)]` on a struct is most Rust
  developers' first real encounter with procedural macros in
  practice).

### 4.2 Database Layer

- **`sqlx`** — async, and *compile-time checks your SQL against the
  real database schema* if you opt into its macro mode, catching a
  typo'd column name at compile time instead of in production.
- **`diesel`** — a full, synchronous ORM with a stricter compile-time-
  checked query builder.
- **`sea-orm`** — async ORM, closer in spirit to Django's ORM for
  anyone who wants that level of abstraction over raw SQL.

### 4.3 Error Handling at Scale

- **`thiserror`** — a derive macro for defining your own clean, typed
  error enums with minimal boilerplate (library-facing: callers get a
  precise error type to match on).
- **`anyhow`** — a single flexible error type for application code
  that just needs to propagate "something went wrong" up to a top-
  level handler with context, without defining a type per failure
  mode (application-facing, not for a library's public API).
- Real services need an explicit **error boundary** — one place
  (commonly Axum/Actix middleware) that converts internal error types
  into the actual HTTP status codes and JSON error bodies clients see,
  the same centralizing instinct as a Django/DRF custom exception
  handler.

### 4.4 Observability

- **`tracing`** — structured, span-based logging built for async code
  specifically (a plain log line loses which concurrent request it
  belongs to; `tracing`'s spans don't). The de facto standard,
  displacing the older `log` crate for anything async.
- Metrics/export typically via `tracing` subscribers feeding
  Prometheus/OpenTelemetry — same end destination as any other
  language's observability stack, different wiring to get there.

### 4.5 Workspace Organization

- A **Cargo workspace** (one top-level `Cargo.toml` listing multiple
  member crates) splits a large project into separate compilation
  units — faster incremental builds (only the changed crate and its
  dependents recompile), and a real enforced boundary between, say, a
  shared domain-types crate and the web-service crate that depends on
  it.

### 4.6 Testing Strategy

- Unit + integration tests (Level 2) still apply at scale.
- **`proptest`** — property-based testing (state a property that must
  always hold, let the tool generate adversarial inputs trying to
  break it), the same idea as Python's Hypothesis, native to Rust.
- Doc-tests stay compiled and run as part of `cargo test` even in a
  large codebase — API documentation genuinely can't silently drift
  out of sync with the real function signature.

### 4.7 Tooling, CI/CD & Deployment

- **`clippy`** — the standard linter, catches a large set of common
  non-idiomatic patterns the compiler itself doesn't flag; run in CI
  as a hard gate, same role as `ruff`/`golangci-lint`.
- **`rustfmt`** — the standard formatter, one canonical style, no
  bikeshedding (same role as `black`/`gofmt`).
- **`cargo audit`** — checks dependencies against a known-
  vulnerability database, the Rust-ecosystem equivalent of
  `pip-audit`/`npm audit`.
- Deployment: Rust compiles to a single static(-ish) binary — a
  multi-stage Docker build (compile in a `rust:` builder image, copy
  just the final binary into a minimal runtime image like `distroless`
  or `alpine`) produces a genuinely tiny final image compared to
  shipping a full language runtime.
- Cross-compilation (`cargo build --target x86_64-unknown-linux-musl`,
  etc.) for building a Linux binary from a different host OS, or
  targeting a `musl` libc for a fully static binary with zero system
  dependencies at runtime.

### 4.8 Specialization Branches (pick based on actual goal)

- **WebAssembly** — `wasm-pack`, compiling Rust to run in a browser or
  any WASM host at near-native speed; a genuinely distinctive Rust
  strength few other languages compete with directly.
- **Embedded** — `no_std` (opting out of the standard library for
  environments with no OS underneath, like a microcontroller), the
  `embedded-hal` ecosystem.

**Project**: a production-shaped REST API — real database (`sqlx` +
Postgres), structured error handling, `tracing` instrumentation, a
test suite (unit + integration + at least one `proptest`), `clippy`/
`rustfmt` wired into CI, and a multi-stage Docker build that deploys
it as a minimal image.

## Ecosystem Cheat Sheet

| Need | Crate |
|---|---|
| Web framework | `axum`, `actix-web` |
| Async runtime | `tokio` |
| Serialization | `serde` (+ `serde_json`) |
| HTTP client | `reqwest` |
| Database (async, compile-checked SQL) | `sqlx` |
| Database (full ORM) | `diesel`, `sea-orm` |
| CLI argument parsing | `clap` |
| Error types (library) | `thiserror` |
| Error handling (application) | `anyhow` |
| Structured logging/tracing | `tracing` + `tracing-subscriber` |
| Benchmarking | `criterion` |
| Property-based testing | `proptest` |
| Parallel data processing | `rayon` |

## Resources by Level

- **Beginner**: *The Rust Programming Language* ("the Book," free,
  official) read alongside **Rustlings** (interactive, compiler-
  error-driven exercises) — the standard starting combination.
- **Intermediate**: *Rust by Example* for quick, runnable syntax
  reference; *Programming Rust* (O'Reilly) for a deeper systems-level
  treatment of ownership and types.
- **Advanced/Professional**: *Zero To Production In Rust* (web
  services specifically, Axum/sqlx/testing/deployment all covered
  together); the official `tokio` tutorial for async in depth; the
  `cargo` book for workspace/publishing/build-config details.

## Suggested Timeline

| Level | Time (part-time study) | Exit signal |
|---|---|---|
| 0 — Setup | 1-2 days | Toolchain installed, Playground explored |
| 1 — Beginner | 1-2 weeks | Can write ownership-correct code without fighting the compiler on every line |
| 2 — Intermediate | 2-3 weeks | Comfortable with traits, iterators, and a tested CLI tool shipped |
| 3 — Advanced | 2-3 weeks | A concurrent/async project working and profiled |
| 4 — Professional | 4-6+ weeks, ongoing | A deployed, tested, observable web service — and genuinely comfortable reading unfamiliar production Rust code |
