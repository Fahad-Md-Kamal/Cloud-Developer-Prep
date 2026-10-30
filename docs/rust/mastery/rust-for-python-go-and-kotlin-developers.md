---
title: Rust for Python, Go & Kotlin Developers
---

# Rust for Python, Go & Kotlin Developers

You already know how to program. What slows you down in Rust is not syntax: it
is a handful of **habits that stop working**. In Python, Go, and Kotlin the
runtime (a garbage collector, a reference-counting interpreter) quietly decides
when memory is freed and who may touch it. In Rust **you and the compiler
decide**, and the compiler checks your decisions before the program runs. This
page translates each language's idioms into Rust, then lists the traps for
each background.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Every Rust idiom
    below is in one runnable file and every quoted compiler error is a real
    one from 1.99.1. Python, Go and Kotlin statements are about their
    standard behavior; check your own version for details.

## 1. "What is the one idea I must change first, whatever my background?"

**Answer:**

- **Core idea:** every value has **one owner**, and the value is freed when the
  owner goes out of scope. Assigning or passing a value **moves** it.
- Python's `b = a` makes two names for one object. Rust's `let b = a` makes
  `a` **unusable**:

```text
error[E0382]: borrow of moved value: `a`
 --> compile_fail/python_alias_moved.rs:6:22
  |
3 |     let a = vec![1, 2, 3];
  |         - move occurs because `a` has type `Vec<i32>`, which does not implement the `Copy` trait
4 |     let b = a;
  |             - value moved here
```

- The fix is a choice you now make on purpose: **borrow** (`&a`), **clone**
  (`a.clone()`), or **move and stop using the old name**.
- Full model: [Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md).

## 2. "When should I choose Rust, and when should I not?"

**Answer:**

- **Core idea:** choose Rust when you need **speed, memory control, or
  compile-time guarantees** and can pay with a steeper learning curve.
- Choose Rust when:
    - latency must be predictable (a garbage-collector pause is not allowed),
    - you ship a **single static binary** or a library other languages call
      (see [FFI & C Interop](../advanced-language/rust-ffi-and-c-interop.md)),
    - you target **WebAssembly** or embedded devices
      ([WebAssembly](../performance-and-internals/rust-webassembly.md),
      [no_std & Embedded](../performance-and-internals/rust-no-std-and-embedded.md)),
    - you want the compiler to catch data races and null/use-after-free bugs.
- Do **not** choose Rust when you are prototyping, the work is mostly waiting
  on a database or network, the team has no time to learn it, or a library
  you need only exists in your current language (machine-learning stacks are
  the common case).

| You use today | Rust is a good addition when | Stay with your language when |
|---|---|---|
| **Python** | a hot loop or parser is the bottleneck; you want a fast native extension (PyO3) | scripts, data analysis, glue code, ML research |
| **Go** | you need no GC pauses, tighter memory, richer types (enums), or safer sharing across threads | simple network services where Go's speed of delivery matters more |
| **Kotlin / JVM** | you need small memory and fast start (no JVM warm-up), native binaries, or an Android native library | large JVM ecosystems, Spring services, Android UI |

- A realistic migration is **not** "rewrite everything": it is one hot path
  or one new service in Rust, called from the old stack.

## 3. "How do the basic idioms translate from Python?"

**Answer:**

| Python | Rust | Note |
|---|---|---|
| `[u.name.upper() for u in users if u.age >= 18]` | `users.iter().filter(\|u\| u.age >= 18).map(\|u\| u.name.to_uppercase()).collect::<Vec<_>>()` | iterators are **lazy**; `collect` runs them |
| `{u.name: u.age for u in users}` | `.map(\|u\| (u.name.as_str(), u.age)).collect::<HashMap<_, _>>()` | the target type decides what `collect` builds |
| `Counter(s)` / `defaultdict(int)` | `*map.entry(c).or_insert(0) += 1` | the `entry` API |
| `d.get("k")` returns `None` | `d.get("k")` returns `Option<&V>` | missing is a **type**, not a surprise |
| `d["k"]` raises `KeyError` | `d["k"]` **panics** | prefer `get` |
| `a, b = b, a` | `std::mem::swap(&mut a, &mut b)` | or `(a, b) = (b, a)` for `Copy` values |
| `for i, (x, y) in enumerate(zip(a, b))` | `for (i, (x, y)) in a.iter().zip(b).enumerate()` | same shape |
| `@dataclass class User` | `#[derive(Debug, Clone, PartialEq)] struct User { .. }` | derive gives you `repr`, `==`, `copy` |
| `None` | `Option<T>` (`None` / `Some(x)`) | the compiler forces you to handle it |
| `try: ... except ValueError` | `Result<T, E>` and `match` or `?` | errors are **return values** |
| `with open(f) as fh:` | a value that closes itself on scope exit (`Drop`) | no `with`, it is automatic |
| `class Base` / inheritance | `trait` plus `impl Trait for Type` | **no inheritance of data**, compose instead |
| `isinstance(x, Dog)` | `match` on an `enum`, or `dyn Any` downcast | prefer an enum |
| `list` of mixed types | `Vec<Box<dyn Trait>>` or an `enum` | one type per `Vec` |
| `typing.Protocol` | `trait` | checked at compile time |
| `lambda x: x + 1` | `\|x\| x + 1` | closures capture by reference unless `move` |
| `pip`, `venv`, `pytest`, `black`, `ruff` | `cargo`, built-in, `cargo test`, `cargo fmt`, `cargo clippy` | one tool |

**Python traps:**

- **"No GIL" does not mean "easy threads."** Rust threads run in parallel, so
  the compiler demands that shared data is `Sync` and mutations go through a
  lock or atomic. See [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md).
- **Strings are UTF-8 bytes.** `s[0]` does not compile; use `.chars()`,
  `.bytes()` or slice by byte range. See
  [Collections & Strings §3](../foundations/rust-collections-and-strings.md#3-how-do-strings-work-why-cant-you-index-them).
- **Integers do not grow.** `i32` overflows (panics in debug builds, wraps in
  release unless you use `checked_*`/`strict_*`). Python's big ints are `i128`
  or a crate here.
- **Default arguments, keyword arguments, and overloading do not exist.** Use a
  struct, a builder, or `Option` parameters.
- **A Python extension** is where you meet Rust first:
  [PyO3 and maturin](../advanced-language/rust-ffi-and-c-interop.md) let you
  write the hot function in Rust and import it from Python.

## 4. "How do the basic idioms translate from Go?"

**Answer:**

| Go | Rust | Note |
|---|---|---|
| `func parse(s string) (int, error)` | `fn parse(s: &str) -> Result<i32, ParseErr>` | one value, not a pair |
| `if err != nil { return 0, err }` | `?` | converts the error with `From` on the way out |
| `errors.Is(err, ErrEmpty)` | `matches!(e, ParseErr::Empty)` | errors are an `enum` you can match |
| `errors.New("x")` / `fmt.Errorf("%w", err)` | `thiserror` (libraries) / `anyhow::Context` (apps) | see [Error Handling §5](../foundations/rust-error-handling.md#5-when-do-you-use-thiserror-and-when-anyhow) |
| `defer f.Close()` | a guard type with `Drop`; runs at scope end, in reverse order | no `defer` keyword needed |
| `interface{ Read() }` (implicit) | `trait Read` (explicit `impl Read for T`) | you must write the `impl` |
| `[]T`, `append` | `Vec<T>`, `push` | a slice is `&[T]` |
| `map[string]int` | `HashMap<String, i32>` | iteration order is **random** |
| `struct` embedding | composition and traits | no embedding |
| `go func() { ch <- f() }()` | `thread::spawn(move \|\| tx.send(f()))` or `tokio::spawn` | see below |
| `sync.WaitGroup` | `JoinHandle::join`, `thread::scope`, `JoinSet` | |
| `select { case <-a: .. }` | `tokio::select!` | cancellation rules differ |
| `context.Context` | a `CancellationToken` or passing a deadline | no built-in standard type |
| `go test`, `go vet`, `gofmt` | `cargo test`, `cargo clippy`, `cargo fmt` | |
| `nil` | `Option<T>` | there is no zero value for most types |

```go
// Go
v, err := parse(s)
if err != nil { return 0, err }
```

```rust
// Rust: the `?` is the whole `if err != nil` block
let v = parse(s)?;
```

**Go traps:**

- **A dropped error is a compile warning in Rust.** In Go `parse("1")` as a
  statement is legal. In Rust it triggers `unused_must_use` (shown here with
  `#![deny(unused_must_use)]`):

```text
error: unused `Result` that must be used
 --> compile_fail/go_unused_result.rs:7:5
  |
7 |     parse("1");
  |     ^^^^^^^^^^
  = note: this `Result` may be an `Err` variant, which should be handled
```

- **No implicit sharing.** In Go two goroutines can read and write the same
  variable, and the race detector may or may not catch it. In Rust the
  compiler refuses; you wrap the data in `Arc<Mutex<T>>` (the data lives
  **inside** the mutex, so you cannot touch it without the lock).
- **Closing a channel is dropping the sender.** In the sample, forgetting
  `drop(tx)` makes the receiving `for` loop wait forever, because one sender
  is still alive.
- **Goroutines vs `async` tasks.** Rust has no built-in runtime. A goroutine
  is closest to a **Tokio task** (`tokio::spawn`), and blocking inside one
  stalls a worker thread. See [Tokio & Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md).
- **No GC means lifetimes.** A function that returns a reference must say
  which input it borrows from. See [Lifetimes](../foundations/rust-lifetimes.md).
- **Generics are real.** Go's generics are limited; Rust's traits and generics
  go much further. See [Traits & Generics](../foundations/rust-traits-and-generics.md).

## 5. "How do the basic idioms translate from Kotlin?"

**Answer:**

| Kotlin | Rust | Note |
|---|---|---|
| `String?` | `Option<String>` | |
| `p.nickname?.length ?: 0` | `p.nickname.as_deref().map_or(0, str::len)` | `as_deref` turns `Option<String>` into `Option<&str>` |
| `nickname!!` | `.unwrap()` or `.expect("msg")` | panics instead of throwing |
| `if (x != null) { x.foo() }` | `if let Some(x) = x { x.foo() }` | |
| `data class User(val name: String)` | `#[derive(Debug, Clone, PartialEq)] struct User` | |
| `user.copy(age = 32)` | `User { age: 32, ..user.clone() }` | struct update syntax |
| `sealed class Shape` + `when` | `enum Shape` + `match` | the compiler checks every case |
| `fun String.shout()` (extension) | a trait implemented for `str` | you must import the trait |
| `interface Foo` with default methods | `trait Foo` with default methods | |
| `object Config` | `static` / `LazyLock` | |
| `val` / `var` | `let` / `let mut` | immutable by default, like `val` |
| `List<T>` (read-only view) | `&[T]` or `Vec<T>` | ownership is explicit |
| `try { } catch (e: Exception)` | `Result` and `?`, or `catch_unwind` (rare) | exceptions are not control flow |
| `suspend fun` / coroutines | `async fn` plus an executor | **lazy** until awaited |
| `Flow<T>` | `Stream<T>` (crate `futures` or `tokio-stream`) | |
| `let`, `also`, `apply`, `run` | `Option::map`, a block, a builder | no scope-function sugar |
| Gradle | Cargo | |
| `@JvmStatic`, annotations | attributes `#[..]` and derive macros | |

```text
error[E0369]: cannot add `{integer}` to `Option<i32>`
 --> compile_fail/kotlin_option_not_null.rs:5:24
  |
5 |     let total: i32 = n + 1;
  |                      - ^ - {integer}
```

**Kotlin traps:**

- **Nullability is stricter, not looser.** `Option<T>` must be unwrapped with
  `match`, `if let`, `?`, `map`, or `unwrap_or`. There is no smart cast after
  a null check, so you rebind: `if let Some(x) = x`.
- **No exceptions, no `finally`.** Use `Result`, and `Drop` for cleanup.
- **Coroutines vs `async`.** Kotlin coroutines are started by a builder
  (`launch`) and have structured scopes built in. A Rust `async fn` does
  **nothing** until polled; you pick the runtime (Tokio) yourself, and a
  future can be **cancelled just by dropping it**. See
  [Async Internals](../concurrency-and-async/rust-async-internals.md).
- **Everything is a value.** There are no object references to share freely.
  A class with a `List<Child>` and back-pointers needs `Rc<RefCell<..>>`,
  indices, or an arena. See [Smart Pointers](../foundations/rust-smart-pointers.md).
- **No inheritance.** `open class` hierarchies become traits and composition.
- **Generics are monomorphized,** not erased: each concrete type gets its own
  compiled copy, so there is no runtime type information like `reified`.
- **Android:** Rust is used for native libraries called through JNI, often
  generated by `uniffi`. See [FFI & C Interop](../advanced-language/rust-ffi-and-c-interop.md).

## 6. "Which concepts have no equivalent in my language?"

**Answer:**

| Concept | What it means | Where to learn it |
|---|---|---|
| **Ownership and moves** | one owner, freed at scope end | [Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md) |
| **Borrow rules** | many readers **or** one writer | [Ownership & Borrowing §5](../foundations/rust-ownership-and-borrowing.md#5-what-are-the-rules-of-borrowing-and-why-do-they-exist) |
| **Lifetimes** | how long a reference is valid | [Lifetimes](../foundations/rust-lifetimes.md) |
| **Traits, not classes** | behavior without inheritance | [Traits & Generics](../foundations/rust-traits-and-generics.md) |
| **Enums with data** | one value, several shapes | [Types, Enums & Patterns §4](../foundations/rust-types-enums-and-patterns.md#4-what-is-an-enum-and-why-is-it-better-than-null-or-status-codes) |
| **`Send` and `Sync`** | which types may cross threads | [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md) |
| **`unsafe`** | where *you* guarantee safety | [Unsafe & Miri](../advanced-language/rust-unsafe-and-miri.md) |
| **Macros** | code that writes code | [Macros](../advanced-language/rust-macros.md) |
| **Editions** | opt-in language dialects | [Modules, Crates & Editions](../foundations/rust-modules-crates-and-editions.md) |

## 7. "What mistakes does each background make in the first month?"

**Answer:**

- **Everyone:** cloning to silence the borrow checker. It works but hides a
  design question. Ask "who should own this?" first.
- **Everyone:** fighting with `String` vs `&str`. Rule: **take `&str`, return
  `String`** until you know why. See
  [Collections & Strings](../foundations/rust-collections-and-strings.md).
- **Python:** reaching for `Rc<RefCell<T>>` to rebuild an object graph. Try
  `Vec` plus indices, or an `enum` tree, first.
- **Python:** `unwrap()` everywhere, like skipping `try/except`. Fine in a
  script, wrong in a service. See [Error Handling](../foundations/rust-error-handling.md).
- **Go:** `Box<dyn Error>` everywhere instead of an error `enum`. Fine in
  `main`; in a library, use `thiserror`.
- **Go:** spawning an OS thread per task. Use a pool (`rayon`) or `async`.
- **Kotlin:** a deep trait hierarchy copied from a class hierarchy. Prefer
  small traits and generics.
- **Kotlin:** thinking `async` runs in the background like `launch`. It does
  not start until polled.
- **All:** writing a lifetime annotation to "fix" an error without
  understanding it. Read the message first; often the answer is to own the
  data instead.

## 8. "How do AI tools help or hurt when I translate from another language?"

**Answer:**

- **Help:** ask "translate this Python function to idiomatic Rust and explain
  each ownership decision". The explanation is the lesson.
- **Hurt:** line-by-line translations. They use `clone()` and `unwrap()`
  everywhere and copy the other language's structure (inheritance, shared
  mutable objects). The result compiles and is not idiomatic.
- **Hurt:** assistants often "fix" a borrow error by adding `.clone()` or
  `Rc<RefCell<..>>`. Ask instead: "what is the ownership design here, and is
  there a version without cloning?"
- **Help:** ask for the **compiler error** to be explained in terms of your
  home language ("explain E0382 like I know Python references").
- **Check:** run `cargo clippy`. It flags the usual translated-code smells
  (needless clones, `return` at the end of a function, manual loops that an
  iterator replaces).
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Moving from another language**

- "You come from Python. What is the biggest conceptual change in Rust?" —
  expects: ownership and moves instead of shared references and a GC,
  [§1](#1-what-is-the-one-idea-i-must-change-first-whatever-my-background).
- "When would you pick Rust over Go?" — expects: no GC pauses, richer types,
  compile-time data-race safety, FFI/WASM; and when not,
  [§2](#2-when-should-i-choose-rust-and-when-should-i-not).
- "How does `?` compare to Go's `if err != nil`?" — expects: it returns early
  and converts the error type with `From`,
  [§4](#4-how-do-the-basic-idioms-translate-from-go).
- "How does Rust's `Option` compare to Kotlin's nullable types?" — expects:
  a real type you must unwrap, no smart cast,
  [§5](#5-how-do-the-basic-idioms-translate-from-kotlin).
- "How do `async` functions in Rust differ from Kotlin coroutines or Python
  `asyncio`?" — expects: futures are lazy, no built-in runtime, cancel by
  drop, [§5](#5-how-do-the-basic-idioms-translate-from-kotlin).

**Design**

- "How would you share a counter between threads?" — expects: `Arc<Mutex<T>>`
  or an atomic; the data lives inside the lock,
  [§4](#4-how-do-the-basic-idioms-translate-from-go).
- "How do you model a Kotlin sealed class?" — expects: an `enum` with data and
  an exhaustive `match`, [§5](#5-how-do-the-basic-idioms-translate-from-kotlin).
- "You need to speed up one Python function. What are your options?" —
  expects: profile first, then PyO3 or a native crate; compare with
  `numpy`/`cython`, [§2](#2-when-should-i-choose-rust-and-when-should-i-not).
- "A teammate clones everything to fix borrow errors. What do you say?" —
  expects: ask who should own the data; borrow or restructure,
  [§7](#7-what-mistakes-does-each-background-make-in-the-first-month).

---

## Code Samples

- `code_samples/rust/examples/translation_idioms.rs`: the Rust side of the
  Python, Go and Kotlin idioms above (comprehensions, `Counter`, `Result` and
  `?`, `Drop` as `defer`, channels, `Arc<Mutex<T>>`, `Option`, `enum` as
  sealed class, extension traits).
- `code_samples/rust/compile_fail/python_alias_moved.rs`,
  `kotlin_option_not_null.rs`, `go_unused_result.rs`: real error text quoted
  above.

```bash
cd code_samples/rust
cargo run --example translation_idioms
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/python_alias_moved.rs      # fails on purpose
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/kotlin_option_not_null.rs  # fails on purpose
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/go_unused_result.rs        # fails on purpose
```
