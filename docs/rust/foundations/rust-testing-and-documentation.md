---
title: Rust Testing & Documentation
---

# Rust Testing & Documentation

Testing is built into Rust's tooling, not added from outside: `cargo
test` finds and runs your tests with no framework to install. It runs
**three kinds** at once: **unit tests** next to the code, **integration
tests** that use only the public API, and **documentation tests** that
compile and run the code examples in your doc comments. That last one is
the quiet superpower: **your documentation cannot go out of date without
the build failing.** This page covers all three, property-based testing,
and how to organize tests so they stay fast and useful.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. The sample crate
    runs 8 unit tests, 2 integration tests, and 3 doc tests, plus 2
    property tests with `proptest` 1. All were run on 1.99.1.

## 1. "What kinds of tests does `cargo test` run?"

**Answer:**

| Kind | Where it lives | Can see | Use for |
|---|---|---|---|
| **Unit test** | A `#[cfg(test)] mod tests` at the bottom of the same file | **Private** items too | One function or module in detail |
| **Integration test** | A file in `tests/` | Only the **public API** (it is a separate crate) | How the crate behaves for a real user |
| **Doc test** | A code block inside a `///` or `//!` comment | The public API | Keeping examples correct |
| **Example** | A file in `examples/` | The public API | Runnable demos (built, not asserted, by `cargo test`) |

- A test is a function marked **`#[test]`**. It **passes** if it returns
  normally and **fails** if it panics. `assert!`, `assert_eq!`, and
  `assert_ne!` panic with a clear message that shows both values.
- `#[cfg(test)]` means the module is **compiled only when testing**, so it
  adds nothing to your release binary.
- `cargo test` runs tests **in parallel threads** by default. Tests must not
  depend on each other or on shared global state.
- Useful commands:

| Command | Does |
|---|---|
| `cargo test` | All kinds |
| `cargo test name` | Tests whose name contains `name` |
| `cargo test --lib` | Unit tests only |
| `cargo test --test integration` | One integration file |
| `cargo test --doc` | Doc tests only |
| `cargo test -- --nocapture` | Show `println!` output of passing tests |
| `cargo test -- --test-threads=1` | Run one at a time |
| `cargo test -- --ignored` | Run the `#[ignore]` tests |
| `cargo test --workspace` | Every crate in a workspace |

## 2. "How do you write good unit tests?"

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_each_unit() {
        assert_eq!(parse_duration("250ms").unwrap(), Duration::from_millis(250));
    }

    // A test may return Result, so `?` works inside it.
    #[test]
    fn parse_with_question_mark() -> Result<(), ParseDurationError> {
        let d = parse_duration("10s")?;
        assert_eq!(d.as_secs(), 10);
        Ok(())
    }

    #[test]
    #[should_panic(expected = "pop from empty stack")]
    fn empty_pop_panics() {
        Stack::<i32>::new().pop_or_panic();
    }

    #[test]
    #[ignore = "slow: run with `cargo test -- --ignored`"]
    fn slow_test() { /* ... */ }
}
```

**Answer:**

- **`use super::*;`** brings the parent module's items (including private
  ones) into the test module. This is the reason unit tests live **inside**
  the module they test.
- **One behaviour per test**, named as a sentence:
  `parse_errors_are_specific`, not `test1`.
- **`#[should_panic(expected = "text")]`** passes only if the code panics
  **with that text** in the message. Without `expected`, any panic passes,
  which can hide the wrong failure.
- **Return `Result` from a test** to use `?` instead of `unwrap()`. A
  returned `Err` fails the test and prints the error.
- **`#[ignore]`** skips slow or environment-specific tests unless you ask
  with `--ignored`.
- **Test the error paths**, not only the happy path. Matching on the error
  variant (`assert_eq!(parse("5x"), Err(BadUnit("x".into())))`) is the
  payoff of good error types. See
  [Error Handling](rust-error-handling.md).
- Use `assert!(matches!(value, Pattern))`, or `std::assert_matches!` (stable
  since Rust 1.96), which **prints the actual value** on failure.
- Compare floats with a tolerance, not `==`.
- **Table-driven tests** are a loop over `(input, expected)` pairs. Include
  the input in the assertion message so a failure says which case broke:
  `assert_eq!(f(x), want, "input was {x:?}")`.
- Tests can use `?` and `Box<dyn Error>`, but **keep assertions explicit**.
  A test that only calls `unwrap()` proves "does not crash", not "is
  correct".

## 3. "What are integration tests, and how do they differ?"

```rust
// tests/integration.rs
use guru_samples::{parse_duration, slugify, Stack};

#[test]
fn public_api_works_together() {
    assert_eq!(slugify("Rust: Ownership & Borrowing"), "rust-ownership-borrowing");
    assert_eq!(parse_duration("90s").unwrap().as_secs(), 90);
}
```

**Answer:**

- Every file in `tests/` is compiled as a **separate crate** that depends on
  your library, so it can only use what is `pub`. It tests the crate **the
  way a user sees it**, and it fails if you accidentally hide something
  important.
- Shared helper code goes in `tests/common/mod.rs` (a folder, not a file in
  `tests/` directly, so Cargo does not treat it as a test crate).
- Integration tests need a **library crate**. A pure binary crate has
  nothing to import. The usual layout is a thin `main.rs` that calls into
  `lib.rs`, so the logic **is** testable.
- **Binaries**: Cargo sets `CARGO_BIN_EXE_<name>` so a test can run your
  compiled program and check its output and exit code. Since Rust 1.94 this
  variable is also available at **run time**, not only at compile time.
- **Slow tests** (database, network) are best put in integration tests, and
  marked `#[ignore]` or gated behind a feature or environment variable.
- When tests need a **service** (Postgres, Redis), run it in a container
  from the test (the `testcontainers` crate) or in CI, and reset state
  between tests.

## 4. "What are doc tests, and why do they matter?"

````rust
/// Turns a title into a URL-friendly slug.
///
/// # Examples
///
/// ```
/// use guru_samples::slugify;
/// assert_eq!(slugify("Hello, Rust World!"), "hello-rust-world");
/// ```
///
/// Lines that start with `# ` are compiled but hidden in the docs:
///
/// ```
/// # use guru_samples::slugify;
/// assert_eq!(slugify("  --A  b-- "), "a-b");
/// ```
pub fn slugify(input: &str) -> String { /* ... */ }
````

**Answer:**

- Every fenced code block in a doc comment is **compiled and run** by `cargo
  test` (as `cargo test --doc` does alone). Each is its own tiny program
  that uses your crate like a user. If an example stops compiling or an
  `assert!` fails, the **test fails**.
- That makes documentation **honest**. It also makes the examples the best
  possible **API test**: if the example is awkward to write, the API is
  awkward to use.
- Code block options:
    - `` ```no_run `` — compile but do not run (for code that needs a
      network).
    - `` ```ignore `` — skip entirely (avoid it).
    - `` ```should_panic `` — expect a panic.
    - `` ```compile_fail `` — **must fail to compile**, which documents
      what the type system forbids.
- A line starting with **`# `** is **hidden** from the rendered docs but
  still compiled. Use it for setup lines (imports, a `fn main`) that would
  distract.
- Examples can use `?` if the hidden `main` returns `Result`: end the block
  with `# Ok::<(), Box<dyn std::error::Error>>(())`.
- **Doc comment styles**: `///` documents the item **after** it, `//!`
  documents the item that **contains** it (a module or crate, at the top of
  a file). Write in Markdown.
- Conventional sections: `# Examples`, `# Panics` (when it can panic),
  `# Errors` (what `Err` means), and `# Safety` (**required** on every
  `unsafe fn`, explaining what the caller must guarantee).
- `cargo doc --open` builds the HTML. **Intra-doc links** such as
  ``[`Stack::push`]`` link to other items and are checked. Enable the
  lints `missing_docs` and `rustdoc::broken_intra_doc_links` in libraries.

## 5. "What is property-based testing?"

```rust
proptest! {
    // Property: slugify is idempotent (slugifying a slug changes nothing).
    #[test]
    fn slugify_is_idempotent(s in ".{0,40}") {
        let once = slugify(&s);
        prop_assert_eq!(slugify(&once), once);
    }

    // Property: a formatted `{n}s` always parses back to n seconds.
    #[test]
    fn seconds_round_trip(n in 0u64..1_000_000) {
        prop_assert_eq!(parse_duration(&format!("{n}s")).unwrap().as_secs(), n);
    }
}
```

**Answer:**

- An **example-based** test checks one input you thought of. A **property**
  test states a **rule that must hold for all inputs**, and the library
  generates **hundreds of random inputs** to try to break it.
- When it finds a failure, it **shrinks** the input to the **smallest**
  example that still fails, which makes the bug easy to see. Failing cases
  are saved so they run again next time.
- Good properties:
    - **Round trip**: `decode(encode(x)) == x`.
    - **Idempotence**: `f(f(x)) == f(x)` (normalization, sorting, slugs).
    - **Invariants**: a sorted vector is ordered and has the same length;
      a balanced tree stays balanced.
    - **Oracle**: a fast implementation matches a slow, obviously correct
      one.
    - **No panic**: parsing any bytes never panics.
- Crates: **`proptest`** (this page) and `quickcheck`. For **fuzzing**
  (coverage-guided random input, great for parsers and unsafe code),
  use `cargo fuzz` with libFuzzer, or AFL.
- Property tests find the bugs example tests miss, especially in **parsers,
  serializers, and data structures**.

## 6. "How do you organize tests and make code testable?"

**Answer:**

- **Make logic pure and push I/O to the edges.** A function that takes data
  and returns data is trivial to test. Wrap file, network, and clock access
  in a small layer.
- **Use traits as test seams.** Take `&impl Clock` or `&dyn Store` instead
  of calling the real thing, and give tests a fake. Rust has **no runtime
  mocking by magic**, so design for it. `mockall` can generate mocks from
  traits when handwritten fakes get tedious.
- **Inject time and randomness.** Pass a clock and a seeded random generator.
- **Prefer real dependencies in integration tests** (a real database in a
  container) over heavy mocks. Mocks test your assumptions, not reality.
- **Snapshot testing** (`insta`) records an output once and flags any change.
  It suits CLI output, serialized data, and error messages.
- **Run tests faster**: `cargo nextest` runs each test in its own process,
  in parallel, with better output and retries.
- **Benchmarks** are not tests. See
  [Performance Engineering](../performance-and-internals/rust-performance-engineering.md).
- **Use Miri** for unsafe code: `cargo +nightly miri test` finds undefined
  behaviour. See [Unsafe Rust & Miri](../advanced-language/rust-unsafe-and-miri.md).
- **Coverage**: `cargo llvm-cov` reports which lines tests execute.
  Coverage shows what is **not** tested. It does not prove the tests are
  good.
- **Lint and format in CI** with `cargo clippy -- -D warnings` and `cargo fmt
  --check`. See
  [CI/CD & Supply Chain](../production/rust-ci-cd-and-supply-chain.md).
- **Test async code** with the runtime's test macro (`#[tokio::test]`). See
  [Tokio & Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md).
- The **compiler is also your first test suite**. Types and exhaustive
  `match` rule out whole classes of tests that other languages need. Spend
  test effort on **logic and boundaries**, not on "did I pass the right
  type".

## 7. "How do AI tools help or hurt with tests?"

**Answer:**

- Good for: generating a first set of unit tests, listing edge cases, writing
  `proptest` strategies, and drafting doc examples.
- They often write tests that **assert the current behaviour**, including
  bugs, and tests that call `unwrap()` and prove nothing. They love
  `#[should_panic]` **without `expected`**.
- Ask: "which of these tests would fail if I broke the function in this
  specific way?" That is a **mutation** check. The tool `cargo mutants`
  automates it by changing your code and seeing whether tests notice.
- Always run the generated tests and **read** them. Delete any you cannot
  explain.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 8. Interview Questions You're Likely to Get Asked

**Basics**

- "What kinds of tests does `cargo test` run?" — expects unit,
  integration, doc (and examples compiled),
  [§1](#1-what-kinds-of-tests-does-cargo-test-run).
- "Why do unit tests live in the same file?" — expects they can see
  private items through `use super::*`, and `#[cfg(test)]` removes them from
  the release build,
  [§2](#2-how-do-you-write-good-unit-tests).
- "Can an integration test call a private function?" — expects no: it is a
  separate crate using the public API,
  [§3](#3-what-are-integration-tests-and-how-do-they-differ).

**Details**

- "What does `#[should_panic(expected = ...)]` add?" — expects it checks
  the panic message, so the right panic is what made the test pass,
  [§2](#2-how-do-you-write-good-unit-tests).
- "What is a doc test and what does `# ` do in one?" — expects compiled and
  run examples, with hidden setup lines,
  [§4](#4-what-are-doc-tests-and-why-do-they-matter).
- "What does `compile_fail` in a doc block document?" — expects what the
  type system forbids,
  [§4](#4-what-are-doc-tests-and-why-do-they-matter).
- "What is a `# Safety` section for?" — expects the contract of an
  `unsafe fn`,
  [§4](#4-what-are-doc-tests-and-why-do-they-matter).

**Practice**

- "What is property-based testing, and give a property for a `sort`
  function." — expects random inputs, shrinking, and: output is ordered,
  same length, same elements,
  [§5](#5-what-is-property-based-testing).
- "How do you test code that uses the system clock or a database?" —
  expects traits as seams and fakes, or a real service in integration
  tests,
  [§6](#6-how-do-you-organize-tests-and-make-code-testable).
- "Why are Rust projects usually a thin `main.rs` plus a library?" —
  expects testability of the logic,
  [§3](#3-what-are-integration-tests-and-how-do-they-differ).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `src/lib.rs` — `slugify`, `parse_duration`, and a `Stack`, with doc
  tests and a unit-test module (`should_panic`, `ignore`, `Result`-returning
  tests, and two `proptest` properties).
- `tests/integration.rs` — two integration tests that use only the public
  API.

```bash
cd code_samples/rust
cargo test                     # unit + integration + doc tests
cargo test -- --ignored        # also run the slow test
cargo test --doc               # doc tests only
cargo doc --open               # build the HTML documentation
```
