---
title: Rust Toolchain & Cargo
---

# Rust Toolchain & Cargo

Rust ships as a **toolchain**: a compiler (`rustc`), a build and package
tool (`cargo`), a documentation tool (`rustdoc`), a formatter
(`rustfmt`), and a linter (`clippy`), all installed and updated by one
manager called `rustup`. **Cargo is the tool you actually use all day.**
It reads one file, `Cargo.toml`, works out which crates (Rust packages)
to download, and calls `rustc` the right number of times with the right
flags. Know how Cargo decides what to build, and most "why is my build
slow, large, or different on another machine" questions answer
themselves.

!!! note "Version"
    Written for **Rust 1.99** (stable, October 2026) and the **2024
    edition**. Cargo's own version number is one major step behind:
    Cargo 0.100 ships with Rust 1.99.

## 1. "What is in the toolchain, and what are the release channels?"

**Answer:**

- The pieces:

| Tool | What it does |
|---|---|
| `rustup` | Installs and switches toolchains, targets, and components |
| `rustc` | The compiler: turns one crate into a library or a program |
| `cargo` | Build system and package manager: resolves, downloads, builds, tests, publishes |
| `rustdoc` | Builds HTML documentation, and runs the code examples in doc comments |
| `rustfmt` | Formats code in the standard style |
| `clippy` | A linter with hundreds of checks for correctness and style |
| `rust-analyzer` | The language server that powers your editor (not part of `rustc`) |

- Three **release channels**:
    - **stable** — a new version every **six weeks**. This is what you ship.
    - **beta** — the next stable, for testing.
    - **nightly** — built every night. It is the only channel that allows
      **unstable features** (`#![feature(...)]`) and tools such as Miri.
- Stability promise: code that compiles on one stable version keeps
  compiling on later stable versions, apart from a few documented
  exceptions such as fixes for soundness bugs. This is why upgrading
  Rust is routine, not an event.
- A **target** is the platform you build for, for example
  `x86_64-unknown-linux-gnu` or `wasm32-unknown-unknown`. Add one with
  `rustup target add <triple>`. Cross-compiling is a first-class feature.
- A **component** is an extra tool for a toolchain (`clippy`, `rustfmt`,
  `rust-src`, `miri`).
- Pin a project to a toolchain with a file named `rust-toolchain.toml`:

    ```toml
    [toolchain]
    channel = "1.99"
    components = ["clippy", "rustfmt"]
    targets = ["wasm32-unknown-unknown"]
    ```

  Everyone who enters the folder then uses the same compiler. This is
  the Rust version of `.python-version` or `.nvmrc`.

## 2. "What is an edition, and how is it different from a version?"

**Answer:**

- A **version** (1.99) is a compiler release. An **edition** (2015, 2018,
  2021, 2024) is a set of language rules a **crate** opts into with
  `edition = "2024"` in `Cargo.toml`.
- Editions exist so Rust can fix design mistakes, such as new keywords or
  changed rules, **without breaking old code**. Old crates stay on their
  old edition.
- Crates of **different editions work together** in one program. The
  edition is chosen **per crate**, and the compiler translates between
  them. A 2015-edition library can be used by a 2024 application.
- Moving a crate up is a tool-assisted step: `cargo fix --edition`
  rewrites most code, then you change the `edition` line.
- The 2024 edition is the latest. Its changes (return-position `impl
  Trait` capture rules, the scope of temporaries in `if let` and at the
  end of a block, `unsafe` extern blocks, `let` chains, the `gen`
  keyword reserved) are covered in
  [Modules, Crates & Editions](rust-modules-crates-and-editions.md) and
  [Modern Rust: 2024 to 1.99](../mastery/modern-rust-2024-to-1-99.md).
- `cargo new` always picks the newest edition. For a new project, use it.

## 3. "What does `cargo build` actually do?"

**Answer:**

- Cargo works in **five steps**:
    1. **Read** `Cargo.toml` (what you want) and `Cargo.lock` (the exact
       versions that were chosen last time).
    2. **Resolve** the dependency graph. If there is no lock file, or it
       is out of date, Cargo picks versions that satisfy every
       requirement and writes `Cargo.lock`.
    3. **Download** missing crates into a shared cache in your home
       folder.
    4. **Compile** each crate in dependency order by calling `rustc`, once
       per crate, in parallel where the graph allows. Build scripts and
       procedural macros are compiled first because they must **run**
       during the build.
    5. **Link** the final program.
- Every crate gets a **fingerprint** (its source, flags, features,
  dependency versions). If the fingerprint is unchanged, Cargo reuses the
  earlier result. That is why the **second** build is fast and why
  dependencies are built **once**.
- Output lives in `target/`: `target/debug/` for the default profile and
  `target/release/` for `--release`. Delete the folder to start fresh. Do
  not commit it.
- `cargo check` runs the **front half** of the compiler only (parsing, type
  checking, borrow checking) and skips code generation. It is
  **much faster** than `cargo build` and gives the same errors. Use it in
  your edit loop.
- Compile times matter because Rust does heavy work per crate. Later pages
  cover why. See
  [How rustc Works](../performance-and-internals/rustc-how-the-compiler-works.md).

## 4. "What are profiles, and what do dev and release really change?"

**Answer:**

- A **profile** is a named group of compiler settings. Cargo has these
  built-in ones: `dev`, `release`, `test`, `bench`, and (new in Rust 1.99)
  `debug`.

| Setting | `dev` (default) | `release` (`--release`) |
|---|---|---|
| `opt-level` | `0` (no optimization) | `3` (full) |
| `debug` | `true` (debug info) | `false` |
| `debug-assertions` | `true` | `false` |
| `overflow-checks` | `true` | `false` |
| `lto` | `false` | `false` |
| `panic` | `unwind` | `unwind` |
| `incremental` | `true` | `false` |
| `codegen-units` | `256` | `16` |

- `test` inherits `dev`. `bench` inherits `release`. The new `debug`
  profile inherits `dev`. The release notes describe it as preparation
  for making `dev` faster by default later, with `debug` kept for
  debugger use.
- **Same code, different behaviour.** In `dev`, integer overflow
  **panics** and `debug_assert!` runs. In `release`, overflow **wraps**
  and `debug_assert!` is removed. Test in both before you ship.
- **Debug builds are slow.** Programs are often 10 to 100 times slower
  at `opt-level = 0`. Never benchmark a dev build.
- Common release tuning:

    ```toml
    [profile.release]
    lto = "fat"         # optimize across crate boundaries (slower build, faster code)
    codegen-units = 1   # one unit = better optimization, no parallel codegen
    panic = "abort"     # smaller and faster, but a panic ends the process
    strip = "symbols"   # smaller binary
    ```

- `panic = "abort"` is a **semantic change**: no stack unwinding, no
  `catch_unwind`, and destructors do not run on panic. Use it on purpose.
- Dependencies can have their own settings:
  `[profile.dev.package."*"] opt-level = 2` makes slow dependencies fast
  in dev while your own code stays quick to compile.

## 5. "How do versions, Cargo.lock, and the resolver work?"

**Answer:**

- A requirement like `serde = "1.0.200"` means "any version that is
  **SemVer-compatible** with 1.0.200", which is `>=1.0.200, <2.0.0`.
  SemVer (Semantic Versioning) says a change in the first non-zero
  number is breaking: `0.3.x` and `0.4.x` are **not** compatible.
- `Cargo.lock` records the **exact** version of every crate in the graph.
    - **Binaries and applications:** commit it. Everyone builds the same
      thing.
    - **Libraries:** the lock file is not used by users of your library,
      so it matters less. Many teams still commit it for CI.
- `cargo update` moves the lock file forward within the allowed ranges.
  `cargo build --locked` fails if the lock file would change. Use
  `--locked` in CI.
- Two crates may need **different versions** of the same dependency.
  Cargo then builds **both** and links both, as long as the types do not
  cross between them. A common surprise is "expected `X` found `X`" where
  both are from different versions of one crate.
- **`rust-version`** (the MSRV, Minimum Supported Rust Version) in
  `Cargo.toml` says which compiler a crate needs. Resolver `"3"`, the
  default for edition 2024, prefers dependency versions that are
  compatible with your `rust-version` instead of the newest ones.
- **Yanked** versions are removed from new resolutions but still work for
  existing lock files.

## 6. "How do features work, and what goes wrong with them?"

```toml
[features]
default = ["json"]
json = ["dep:serde_json"]   # enables the optional dependency
fancy = []                  # a plain on/off switch
```

```rust
#[cfg(feature = "fancy")]
fn banner() { println!("fancy"); }
```

**Answer:**

- A **feature** is a named compile-time switch. It can turn code on with
  `#[cfg(feature = "name")]` and pull in **optional dependencies**.
- The rule that matters: features must be **additive**. Turning a feature
  on may add things, never remove or change existing behaviour.
- Why additive: Cargo **unifies** features across the whole graph. If
  crate A needs `tokio/full` and crate B needs `tokio/rt`, **one**
  `tokio` is built with the **union**. If your feature changes behaviour
  rather than adding it, another crate can break you by turning it on.
- `default` features are on unless a dependent writes
  `default-features = false`. Libraries should keep defaults small.
- `dep:name` in a feature turns on an optional dependency **without**
  creating an implicit feature of the same name.
- Resolver `"2"` and later keep features of **build dependencies and dev
  dependencies** separate from your normal dependencies, so a test-only
  feature does not leak into your release build.
- Check all combinations of a library's features in CI (for example with
  `cargo hack --feature-powerset`), because a mistake in one combination
  can ship unnoticed.
- Try it yourself: `cargo run --example features_demo` and the same with
  `--features fancy`.

## 7. "How do workspaces organize a larger project?"

```toml
# Cargo.toml at the repository root
[workspace]
members = ["crates/*"]
resolver = "3"

[workspace.package]
edition = "2024"
version = "0.1.0"

[workspace.dependencies]
serde = { version = "1", features = ["derive"] }
```

```toml
# crates/api/Cargo.toml
[package]
name = "api"
edition.workspace = true
version.workspace = true

[dependencies]
serde.workspace = true
```

**Answer:**

- A **workspace** is a set of crates that share **one** `Cargo.lock`, one
  `target/` folder, and one resolver result.
- Benefits:
    - **One version** of each dependency across all crates.
    - **Shared build cache**, so a shared dependency compiles once.
    - **Central settings**: `[workspace.package]`, `[workspace.dependencies]`,
      and `[workspace.lints]` avoid repeating the same lines.
- A **virtual workspace** has a root `Cargo.toml` with no `[package]` of
  its own. It only lists members.
- Splitting code into several crates also **speeds up incremental
  builds**, because `rustc` works one crate at a time. A change in a
  small crate does not rebuild a large one that does not depend on it.
- Since Rust 1.99, a member on edition 2024 or later can **override**
  `default-features` of an inherited workspace dependency.
- See [Project Architecture & API Guidelines](../production/rust-project-architecture-and-api-design.md)
  for how to cut crates.

## 8. "What are build scripts, and when do you need one?"

**Answer:**

- A **build script** is a file named `build.rs` at the crate root. Cargo
  compiles it first and **runs it before** building the crate.
- It talks to Cargo by printing lines that start with `cargo::`, for
  example `cargo::rerun-if-changed=path` ("rebuild only if this file
  changed") and `cargo::rustc-link-lib=name` ("link this C library").
- Typical uses: compile C code, find a system library, generate Rust
  source from a schema, and set `cfg` flags based on the environment. It
  writes generated files into the folder named by the `OUT_DIR`
  environment variable.
- Costs: it slows builds, runs arbitrary code on every machine that
  builds your crate, and is a supply chain risk. Use it only when
  needed. See
  [CI/CD & Supply Chain](../production/rust-ci-cd-and-supply-chain.md).
- **Procedural macros** are the other build-time code. See
  [Macros](../advanced-language/rust-macros.md).

## 9. "How do you configure Cargo and the toolchain per project and per machine?"

**Answer:**

- `Cargo.toml` — what the **crate** is. Committed.
- `rust-toolchain.toml` — which **compiler**. Committed.
- `.cargo/config.toml` — how **Cargo** behaves: alias commands, linker
  settings, target defaults, extra flags. It is read from the current
  folder upward and from your home folder.

    ```toml
    [alias]
    lint = "clippy --all-targets -- -D warnings"

    [target.x86_64-unknown-linux-gnu]
    rustflags = ["-C", "target-cpu=native"]
    ```

- Environment variables such as `CARGO_BUILD_JOBS`, `RUSTFLAGS`, and
  `CARGO_TARGET_DIR` override files.
- A config file can pull in other config files with the `include` key,
  which is useful to share settings across repositories.
- `RUSTFLAGS` set in the environment **replaces** flags from config, and
  changing it rebuilds everything. Put shared flags in
  `.cargo/config.toml` instead.

## 10. "Which commands do you use every day?"

**Answer:**

| Command | Use |
|---|---|
| `cargo new` / `cargo init` | Start a crate |
| `cargo add serde` / `cargo remove serde` | Edit dependencies |
| `cargo check` | Fast type check, no binary |
| `cargo build` / `cargo run` | Build, build and run |
| `cargo test` | Unit, integration, and doc tests |
| `cargo clippy` | Lints |
| `cargo fmt` | Format |
| `cargo doc --open` | Build and open docs, including your dependencies' |
| `cargo tree` | Show the dependency graph (`-d` shows duplicates, `-i name` shows who needs a crate) |
| `cargo update` | Update `Cargo.lock` |
| `cargo fix` | Apply compiler suggestions, and migrate editions |
| `cargo install --locked name` | Install a tool, using its lock file |
| `cargo clean` | Remove build output (`--workspace` limits it to your crates) |
| `cargo publish` | Release to crates.io (multi-package publish is stable since 1.90) |

- `cargo doc --open` is the **best habit** for learning a crate. The
  documentation is generated from the exact version you use.
- Tools such as `cargo expand` (show macro output), `cargo audit`,
  `cargo deny`, `cargo nextest`, and `cargo hack` are separate installs
  that are worth knowing.

## 11. "How do you make builds reproducible?"

**Answer:**

- Commit `Cargo.lock` and `rust-toolchain.toml`.
- In CI, build with `cargo build --locked` so a drifting lock file fails
  the job.
- **Vendor** dependencies (`cargo vendor`) when you must build offline or
  want to audit all source.
- Pin build-time tools (`cargo install --locked --version X`).
- Record what built a binary. A binary can embed the git hash and
  compiler version through a build script.
- Reproducible output across machines also depends on file paths. The
  `--remap-path-prefix` and `--remap-path-scope` options control the paths
  that end up inside the binary.

## 12. "How do AI tools fit into the Rust workflow?"

**Answer:**

- The **compiler is the best teacher** in the loop. Paste the full error
  from `cargo check`, not a summary. Rust errors are precise, and AI
  explanations work best with the exact text.
- AI assistants often invent **crate versions, feature names, and APIs**.
  Use `cargo add` (it picks a real version) and `cargo doc --open` to
  confirm an API exists before you trust it.
- Training data lags: models may write 2018-era or 2021-era code (older
  idioms, missing `let` chains, `async-trait` where native async
  functions in traits now work). Tell the tool your edition and Rust
  version.
- Run `cargo clippy` on generated code. It catches many non-idiomatic
  patterns.
- Never accept code you cannot explain. See
  [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 13. Interview Questions You're Likely to Get Asked

**Basics**

- "What is the difference between a Rust version and an edition?" —
  expects: a compiler release vs a per-crate opt-in set of language
  rules, and that editions interoperate,
  [§2](#2-what-is-an-edition-and-how-is-it-different-from-a-version).
- "Why is `cargo check` faster than `cargo build`?" — expects: it skips
  code generation and linking,
  [§3](#3-what-does-cargo-build-actually-do).

**Cargo**

- "What is in `Cargo.lock` and should you commit it?" — expects exact
  versions, and yes for applications,
  [§5](#5-how-do-versions-cargolock-and-the-resolver-work).
- "Why must features be additive?" — expects feature unification across
  the graph, [§6](#6-how-do-features-work-and-what-goes-wrong-with-them).
- "Why can one crate appear twice in the build?" — expects
  SemVer-incompatible requirements building two versions,
  [§5](#5-how-do-versions-cargolock-and-the-resolver-work).

**Production**

- "What differs between a dev and a release build besides speed?" —
  expects overflow checks and `debug_assert!`, plus possible behaviour
  differences, [§4](#4-what-are-profiles-and-what-do-dev-and-release-really-change).
- "How would you shrink and speed up a release binary?" — expects `lto`,
  `codegen-units = 1`, `panic = "abort"`, `strip`, and the trade-offs,
  [§4](#4-what-are-profiles-and-what-do-dev-and-release-really-change).

---

## Code Samples

Runnable files live in `code_samples/rust/` (a Cargo package with
edition 2024). Install Rust with `rustup`, then from that folder:

- `examples/features_demo.rs` — a feature switch and the dev vs release
  difference.

    ```bash
    cd code_samples/rust
    cargo run --example features_demo
    cargo run --release --example features_demo --features fancy
    ```
