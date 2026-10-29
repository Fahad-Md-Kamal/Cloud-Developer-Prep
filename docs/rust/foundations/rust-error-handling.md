---
title: Rust Error Handling
---

# Rust Error Handling

Rust has **no exceptions**. A function that can fail says so in its
**return type**, and the caller must deal with it. Failures that you can
reasonably recover from are values: `Result<T, E>`. Failures that mean "the
program has a bug" are **panics**. This design makes every failure path
**visible in the types** and checked by the compiler. The skill is
choosing good error types: enough detail for the caller to act, without
drowning them or leaking your dependencies.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Examples were run
    on 1.99.1 with `thiserror` 2 and `anyhow` 1.

## 1. "What is the difference between `Result` and a panic?"

**Answer:**

- **`Result<T, E>`** (from [Types, Enums & Patterns](rust-types-enums-and-patterns.md#4-what-is-an-enum-and-why-is-it-better-than-null-or-status-codes))
  is for failures that are **expected** and can be handled: a file is
  missing, the input is invalid, the network is down.
- **`panic!`** is for **bugs**: a broken invariant, an index out of range,
  a value that "cannot happen." A panic **unwinds** the stack (running
  `Drop` code) and ends the thread, usually the program.
- Rule of thumb: if a **caller** could do something sensible about it,
  return `Result`. If the only sensible response is "fix the code," panic.
- `Result` is marked `#[must_use]`: ignoring a returned `Result` is a
  **compiler warning**. The failure cannot be silently dropped.
- Compared with other approaches:

| Language | Mechanism | Weakness Rust avoids |
|---|---|---|
| Java, Python, Kotlin | Exceptions | Failures are invisible in signatures; any call may throw |
| Go | `(value, error)` returns | `if err != nil` is easy to forget or ignore |
| C | Error codes, `errno` | Same, plus the value and the error share a type |
| **Rust** | `Result<T, E>` | The type names the failure; ignoring it warns; `?` removes the noise |

## 2. "How does the `?` operator work?"

```rust
fn read_port(cfg: &[(&str, &str)]) -> Result<u16, ConfigError> {
    let raw = cfg.iter().find(|(k, _)| *k == "port")
        .map(|(_, v)| *v)
        .ok_or(ConfigError::Missing("port"))?;   // returns early on Err
    raw.parse::<u16>().map_err(|source| ConfigError::BadNumber { key: "port", source })
}
```

**Answer:**

- `expr?` means: "if `expr` is `Ok(v)`, give me `v`. If it is `Err(e)`,
  **return** `Err(From::from(e))` from the current function."
- The `From::from` call is what makes `?` convenient: if your function's
  error type implements `From<TheirError>`, the conversion is **automatic**.
- `?` also works on **`Option`** in a function that returns `Option`, and
  on any type that implements the `Try` machinery (for example
  `ControlFlow`).
- `?` is **not** magic control flow. It is a **visible early return**, one
  character at each place that can fail. Reading a function, you can see
  every exit.
- A function that returns `Result` can only use `?` on a compatible error
  type. If you need to convert, write `.map_err(...)` or implement `From`.
- `fn main() -> Result<(), E>` is allowed: an `Err` prints its `Debug`
  form and exits with status 1. For control over the exit status, return
  `std::process::ExitCode`.

## 3. "Which methods on `Result` and `Option` should you know?"

**Answer:**

| Need | Method |
|---|---|
| Transform the success value | `map` |
| Transform the error | `map_err` |
| Chain another fallible step | `and_then` |
| Turn `Option` into `Result` | `ok_or`, `ok_or_else` |
| Turn `Result` into `Option` | `.ok()` |
| Default on failure | `unwrap_or`, `unwrap_or_else`, `unwrap_or_default` |
| Flip `Option<Result<T,E>>` into `Result<Option<T>,E>` | `transpose` |
| Remove one level of nesting | `Result::flatten` (stable since 1.89) |
| Test without consuming | `is_ok`, `is_err`, `is_some_and`, `is_ok_and` |
| `bool` into `Result` | `bool::ok_or`, `ok_or_else` (stable since 1.98) |

- **`unwrap()`** panics on `None` or `Err`. **`expect("why this cannot fail")`**
  does the same with a message. Both are fine in **tests, examples, and
  after a check that makes failure impossible**. Elsewhere, prefer `?` or a
  default. Many teams enable the Clippy lints `unwrap_used` and
  `expect_used` for library code.
- Prefer **`ok_or_else`** (a closure) when building the error is costly,
  because `ok_or(expr)` always evaluates `expr`.
- **Collecting** results: an iterator of `Result<T, E>` collects into
  `Result<Vec<T>, E>` and **stops at the first error**. `try_fold` is the
  same idea for folding. Run `error_patterns` to see both, plus
  `transpose`.

## 4. "What is the `Error` trait, and what should an error type look like?"

**Answer:**

- `std::error::Error` is a trait with two pieces that matter:
    - It requires `Debug` and `Display`. `Display` is the **message for a
      human**, `Debug` is for developers.
    - `source()` returns the **underlying cause**, forming a **chain**.
- Good error type properties:
    1. **Matchable**: callers can `match` on the **kind** of failure.
    2. **Informative**: the message says **what** failed, not only that
       something failed.
    3. **Chained**: the cause is kept (`source`), not flattened into a
       string.
    4. **Small enough**: see the size note below.
- A hand-written enum shows what is needed:

    ```rust
    #[derive(Debug)]
    enum ConfigError {
        Missing(&'static str),
        BadNumber { key: &'static str, source: ParseIntError },
    }
    // + impl Display, + impl Error { fn source(...) }
    ```

- **`Box<dyn Error + Send + Sync>`** is the "any error" type for quick
  code and `main`. `Send + Sync` lets it cross threads. `?` converts any
  error into it. It is **not matchable** (callers can only `downcast_ref`).
- **Error size matters.** A `Result<T, E>` is as large as the larger of `T`
  and `E`, plus a tag. A 256-byte error makes every `Result` 257 bytes, even
  when it is `Ok`. Box the large error: `Result<(), Box<BigError>>` is 8
  bytes. (Clippy warns with `result_large_err`.)

## 5. "When do you use `thiserror` and when `anyhow`?"

**Answer:**

- **`thiserror`**: a derive macro that writes `Display`, `Error`, `source`,
  and `From` for your **own error enum**. It is for **libraries** and for
  any module where callers should **match** on the failure.

    ```rust
    #[derive(Debug, thiserror::Error)]
    enum AppError {
        #[error("config problem: {0}")]
        Config(#[from] ConfigError),          // also writes From<ConfigError>
        #[error("value {0} is out of range")]
        OutOfRange(u16),
    }
    ```

- **`anyhow`**: one opaque error type, `anyhow::Error`, that wraps any error
  and lets you add **context**. It is for **applications** (binaries),
  where the only thing to do with an error is to report it.

    ```rust
    use anyhow::Context;
    fn run() -> anyhow::Result<()> {
        let p = checked_port(&cfg).context("while starting the server")?;
        Ok(())
    }
    ```

  Iterating `e.chain()` prints each cause, outermost first. The sample
  prints: `while starting the server`, then `value 80 is out of range`.
- The simple split: **libraries return typed errors (`thiserror`),
  applications use `anyhow` at the top.** A library that returns
  `anyhow::Error` forces its users to give up matching.
- Others worth knowing: `eyre` and `color-eyre` (richer reports), `miette`
  (pretty diagnostics for tools that show source code), `snafu` (a
  context-selector style).
- **Do not expose a dependency's error type** in your public API unless you
  mean to. If your error holds a `reqwest::Error` in a public variant, your
  version of `reqwest` becomes part of your API. Wrap it, or hold it in a
  private field behind your own variant.
- Add **`#[non_exhaustive]`** to public error enums, so adding a variant
  later is not a breaking change.

## 6. "When is a panic right, and what happens when one occurs?"

**Answer:**

- **Right**: a violated **invariant** (internal logic error), a failed
  `assert!`, an **impossible** `match` arm (`unreachable!()`), `unwrap` on
  a value you just checked, and **tests**.
- **Wrong**: bad **user input**, I/O failures, parse failures,
  anything the outside world can cause. Return `Result`.
- By default a panic **unwinds**: it walks up the stack running `Drop`
  code and then ends the **thread**. In the main thread, that ends the
  program with status 101.
- With `panic = "abort"` in the profile, the process **stops at once**
  without unwinding. Binaries are smaller, but `Drop` code does not run
  and `catch_unwind` does not work.
- **`std::panic::catch_unwind`** catches a panic. It is **not** an
  exception system: use it only at **boundaries** (a thread pool that must
  survive a bad job, a plugin host, an FFI edge, where unwinding through C
  is undefined behaviour). See
  [FFI & C Interop](../advanced-language/rust-ffi-and-c-interop.md).
- A panic in another **thread** is caught by the runtime: `join()` returns
  `Err(payload)`. A panic while a `Mutex` guard is held **poisons** the
  mutex. See [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md).
- A panic inside `Drop` **while already panicking** aborts the process.
  Never let `Drop` fail.
- **`#[track_caller]`** makes a function report the **caller's** location
  in panic messages. The sample prints `error_patterns.rs:51:41`, the call
  site, not the line with `panic!`. The standard library uses this for
  `unwrap`, `expect`, and indexing.
- **Set a panic hook** (`std::panic::set_hook`) in services to log
  structured details, then let the process exit and be restarted by its
  supervisor.

## 7. "What patterns keep error handling clean?"

**Answer:**

- **One error enum per layer.** A parsing module has `ParseError`, a storage
  module has `StoreError`, the application has `AppError` with
  `#[from]` for each. Each layer converts at its boundary.
- **Add context where information exists**, not at the top. The place that
  knows "which file" or "which user" should add it:
  `.with_context(|| format!("reading {}", path.display()))`.
- **Do not log and return** an error at every level. That prints the same
  failure five times. Handle it **or** pass it up, and log **once**, at
  the place that decides what to do.
- **Do not turn errors into strings** early. Strings cannot be matched and
  lose the chain.
- **Use `Result<Vec<_>, E>` from iterators** to fail fast, or **partition**
  successes and failures when you want all of them:

    ```rust
    let (oks, errs): (Vec<_>, Vec<_>) = items.iter().map(parse).partition(Result::is_ok);
    ```

- **Retry only retryable errors.** Give your error type a method such as
  `is_retryable()` and use it in the retry loop.
- **Make illegal states unrepresentable** so some errors cannot happen. See
  [Types, Enums & Patterns §7](rust-types-enums-and-patterns.md#7-how-do-you-design-types-so-wrong-states-cannot-exist).

## 8. "How do you get a backtrace, and what does async change?"

**Answer:**

- Set `RUST_BACKTRACE=1` to print a backtrace on panic, and
  `RUST_BACKTRACE=full` for more detail. `anyhow` captures a backtrace
  when this variable is on.
- `std::backtrace::Backtrace::capture()` records one on demand. It is
  **cheap when disabled** and slow when enabled, so avoid it on hot error
  paths.
- Backtraces need **debug symbols**. Release builds with `strip` show
  little. Keep `debug = "line-tables-only"` if you want readable
  backtraces in production at a small size cost.
- In **async** code, `?` works the same. A backtrace shows the executor's
  frames, not a logical "call stack" of awaits. For async diagnostics, use
  **tracing spans**. See [Observability](../production/rust-observability.md).
- Errors that cross a **task** boundary (`tokio::spawn`) come back as
  `JoinError` from the handle: the task's own `Result` is nested inside.
  See [Tokio & Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md).

## 9. "Where do AI tools help or hurt here?"

**Answer:**

- Good for: writing `thiserror` enums, `From` impls, and converting
  `unwrap()` calls into `?` with context.
- They overuse `unwrap()` and `expect()` in generated code, and love
  `Box<dyn Error>` everywhere. Ask for a **typed** error in libraries.
- They often return `anyhow::Result` from a library function. Check that
  against [§5](#5-when-do-you-use-thiserror-and-when-anyhow).
- A review prompt that works well: "Find every place this code can panic,
  and tell me which should be `Result`."
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Basics**

- "How does Rust handle errors without exceptions?" — expects `Result`
  in the signature, `#[must_use]`, and `?`,
  [§1](#1-what-is-the-difference-between-result-and-a-panic).
- "What does `?` expand to?" — expects early return of
  `Err(From::from(e))`,
  [§2](#2-how-does-the-operator-work).
- "`unwrap` vs `expect` vs `?`?" — expects panic vs panic with message vs
  propagate, and where each is acceptable,
  [§3](#3-which-methods-on-result-and-option-should-you-know).

**Design**

- "`thiserror` or `anyhow`?" — expects typed errors in libraries,
  `anyhow` in applications,
  [§5](#5-when-do-you-use-thiserror-and-when-anyhow).
- "Why might a `Result` be unexpectedly large?" — expects the error's size
  is part of every `Result`; box large errors,
  [§4](#4-what-is-the-error-trait-and-what-should-an-error-type-look-like).
- "Why shouldn't a public error enum contain a dependency's error
  directly?" — expects it leaks the dependency into your semver,
  [§5](#5-when-do-you-use-thiserror-and-when-anyhow).
- "How do you collect many fallible results?" — expects
  `collect::<Result<Vec<_>, _>>()` and `partition`,
  [§3](#3-which-methods-on-result-and-option-should-you-know) and
  [§7](#7-what-patterns-keep-error-handling-clean).

**Panics**

- "When is a panic acceptable?" — expects invariants and bugs, not
  input,
  [§6](#6-when-is-a-panic-right-and-what-happens-when-one-occurs).
- "What does `panic = "abort"` change?" — expects no unwinding, no
  `Drop`, no `catch_unwind`,
  [§6](#6-when-is-a-panic-right-and-what-happens-when-one-occurs).
- "What does `#[track_caller]` do?" — expects panics report the caller's
  location,
  [§6](#6-when-is-a-panic-right-and-what-happens-when-one-occurs).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/error_handling.rs` — a hand-written error, `thiserror`,
  `anyhow` with context and `chain()`, `Option::ok_or`,
  `Result::flatten`, and `catch_unwind`.
- `examples/error_patterns.rs` — `collect` into `Result`, `try_fold`,
  `transpose`, error sizes, `#[track_caller]`, and `ExitCode`.

```bash
cd code_samples/rust
cargo run --example error_handling
cargo run --example error_patterns
```
