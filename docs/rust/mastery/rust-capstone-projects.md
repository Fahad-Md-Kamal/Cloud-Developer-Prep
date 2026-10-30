---
title: "Rust Capstone Projects: Ten Graded Builds"
---

# Rust Capstone Projects: Ten Graded Builds

Reading does not make a Rust developer; **building under compiler pressure**
does. This page gives you **ten projects, ordered from easy to hard**. Each
one names the concepts it forces you to use, links to the page that teaches
them, and has **acceptance tests** you can run. The code skeletons compile
today and every test starts out **ignored**; your job is to fill in the
`todo!()` bodies and un-ignore the tests.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. The skeleton package
    `code_samples/rust/capstones/` compiles on 1.99.1 with no warnings and
    uses only the standard library. The acceptance tests have **not** been run
    against reference solutions: if a test looks wrong to you, trust the
    project description and fix the test. Reference solutions are **not**
    provided on purpose.

## 1. "How do I use these projects?"

**Answer:**

- **Core idea:** a capstone is done when its acceptance tests pass **and**
  `cargo clippy -- -D warnings` is clean **and** you can explain every
  `unsafe` block, `clone`, and `Arc` in it.
- Workflow for each project:

```bash
cd code_samples/rust/capstones
cargo test c01 -- --ignored     # all red: your starting point
# implement src/c01_grep.rs, remove #[ignore] from tests as they pass
cargo test c01
cargo clippy --all-targets -- -D warnings
```

- Do them in order the first time. Later projects assume you finished the
  earlier ones; the "Needs" line says which pages to read first.
- Time guide (part-time, first attempt): projects 1 to 3 take a weekend each,
  4 to 7 a week each, 8 to 10 one to two weeks each.
- Write a short README per project: design choices, what you measured, what
  you would change. This is what interviewers ask about.
- Commit after every passing test. A history of small commits shows how you
  think.

| # | Project | Level | Core skill |
|---|---|---|---|
| 1 | CLI grep clone | Beginner | `&str`, iterators, `Result` |
| 2 | Markdown to HTML | Beginner | enums, parsing |
| 3 | Key-value store with a write-ahead log | Intermediate | files, error design |
| 4 | HTTP server from `std::net` | Intermediate | bytes, TCP, threads |
| 5 | Async chat server | Intermediate | Tokio, channels |
| 6 | Thread pool | Intermediate | `Arc`, `Mutex`, `Drop` |
| 7 | Interpreter | Advanced | recursive types, parsing |
| 8 | Arena allocator | Advanced | `unsafe`, `Layout` |
| 9 | Lock-free queue checked with `loom` | Expert | atomics, ordering |
| 10 | A tiny async runtime | Expert | `Future`, `Waker`, `Pin` |

## 2. "Project 1: how do I build a `grep` clone?"

**Answer:**

- **Goal:** a command `mygrep PATTERN FILE...` that prints matching lines with
  line numbers. Flags: `-i` (ignore case), `-v` (invert), `-c` (count).
- **Core idea:** keep the search logic in a **library function** over a
  `BufRead`, and the file and argument handling in `main`. Then the logic is
  testable without files.
- **Needs:** [Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md),
  [Collections & Strings](../foundations/rust-collections-and-strings.md),
  [Error Handling](../foundations/rust-error-handling.md),
  [Iterators & Closures](../foundations/rust-iterators-and-closures.md).
- **Skeleton and tests:** `src/c01_grep.rs`: `c01_finds_lines_with_numbers`,
  `c01_ignore_case_and_invert`.
- **Acceptance (beyond the tests):** reads standard input when no file is
  given; exits with code 1 when nothing matched and 2 on an I/O error; handles
  a file that is not valid UTF-8 without crashing.
- **Stretch:** regular expressions with the `regex` crate; `clap` for
  arguments ([CLI & Systems](../production/rust-cli-and-systems-programming.md));
  search directories in parallel with `rayon`; memory-map big files.

## 3. "Project 2: how do I convert Markdown to HTML?"

**Answer:**

- **Goal:** `to_html(&str) -> String` for headings, paragraphs, emphasis,
  inline code, and bullet lists, with HTML escaping.
- **Core idea:** two passes. First split the text into **blocks** (an `enum
  Block`), then parse **inline** markup inside each block. Escaping happens
  once, at the end.
- **Needs:** [Types, Enums & Patterns](../foundations/rust-types-enums-and-patterns.md),
  [Collections & Strings](../foundations/rust-collections-and-strings.md) (UTF-8
  and `char_indices`), [Iterators & Closures](../foundations/rust-iterators-and-closures.md).
- **Skeleton and tests:** `src/c02_markdown.rs`: heading, inline plus escape, list.
- **Acceptance:** `<script>` in the input never produces a real tag; unbalanced
  `**` does not panic; a 1 MB input finishes in under a second in a release
  build.
- **Stretch:** links and images; code fences; nested lists; property tests
  ([Testing & Docs §5](../foundations/rust-testing-and-documentation.md#5-what-is-property-based-testing))
  that assert "output never contains an unescaped `<` from the text".

## 4. "Project 3: how do I build a key-value store with a write-ahead log?"

**Answer:**

- **Goal:** `KvStore` with `set`, `get`, `delete`, and `compact`. Data survives
  a restart.
- **Core idea:** a **write-ahead log** records every change **before** it is
  applied in memory. On startup you **replay** the log. This is how real
  databases survive crashes.
- **Needs:** [Error Handling](../foundations/rust-error-handling.md) (your own
  `KvError`), [Collections & Strings](../foundations/rust-collections-and-strings.md),
  [Smart Pointers](../foundations/rust-smart-pointers.md) (`Drop`), and the
  [CLI & Systems](../production/rust-cli-and-systems-programming.md) page for
  files and `BufWriter`.
- **Skeleton and tests:** `src/c03_kv_store.rs`: `c03_survives_restart`,
  `c03_compaction_keeps_data`.
- **Acceptance:** a half-written last log line is detected (`KvError::Corrupt`)
  or safely ignored, never silently misread; values may contain spaces and
  newlines (design an escape or use length prefixes).
- **Stretch:** compact atomically (write a new file, `rename` over the old);
  checksums per record; a file lock so two processes cannot open the same
  store ([Modern Rust §7](modern-rust-2024-to-1-99.md#7-what-changed-for-threads-locks-atomics-and-lazy-values));
  an in-memory index over a log of **offsets** so values need not all fit in
  RAM; benchmark with the [Performance](../performance-and-internals/rust-performance-engineering.md) page.

## 5. "Project 4: how do I build an HTTP server with only the standard library?"

**Answer:**

- **Goal:** serve `GET` requests over TCP with correct status lines, headers,
  and `Content-Length`. A simple router (`/`, `/hello/NAME`, a 404).
- **Core idea:** HTTP/1.1 is **text over a byte stream**. A request ends at a
  blank line (`\r\n\r\n`); a read may return half a request, so you must
  buffer.
- **Needs:** [Error Handling](../foundations/rust-error-handling.md),
  [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md),
  [Collections & Strings](../foundations/rust-collections-and-strings.md).
- **Skeleton and tests:** `src/c04_http_server.rs`: `parse_request`
  (complete and incomplete input) and `response`.
- **Acceptance:** `curl -i http://127.0.0.1:PORT/hello/ana` shows a valid
  response; a request split across two TCP reads still works; a request
  larger than your header limit gets `431` instead of growing memory.
- **Stretch:** reuse your project 6 thread pool; keep-alive connections;
  chunked bodies; read timeouts; compare with
  [Web Services with Axum](../production/rust-web-services-with-axum.md) and
  note what Axum and `hyper` handle for you.

## 6. "Project 5: how do I build an async chat server?"

**Answer:**

- **Goal:** clients connect with TCP (or `telnet`), choose a name, and every
  line they type is sent to everyone. `/who` lists users. Quit with Ctrl-C and
  the server shuts down cleanly.
- **Core idea:** separate the **pure state** (`Room`: names and routing) from
  the **I/O** (one Tokio task per client). Pure state is easy to test; the
  async part is a thin wrapper.
- **Needs:** [Async Internals](../concurrency-and-async/rust-async-internals.md),
  [Tokio & Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md),
  [Smart Pointers](../foundations/rust-smart-pointers.md) (`Arc`, `Mutex`).
- **Skeleton and tests:** `src/c05_chat_room.rs`: `c05_join_say_leave`,
  `c05_duplicate_name_rejected`. Add `tokio` yourself for the server binary.
- **Acceptance:** a slow client cannot make the others lag (use bounded
  channels and **drop or disconnect** the slow one); disconnecting removes the
  user and tells the others; no `std::sync::MutexGuard` is held across an
  `.await`.
- **Stretch:** graceful shutdown with a `CancellationToken`; rooms; message
  history with a ring buffer; metrics and tracing
  ([Observability](../production/rust-observability.md)).

## 7. "Project 6: how do I build a thread pool?"

**Answer:**

- **Goal:** `ThreadPool::new(n)` and `execute(job)`. Dropping the pool waits
  for every queued job and joins every worker.
- **Core idea:** workers share the **receiving end** of one channel
  (`Arc<Mutex<Receiver<Job>>>`). A job is a `Box<dyn FnOnce() + Send>`. Dropping
  the **sender** is the shutdown signal.
- **Needs:** [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md),
  [Traits & Generics](../foundations/rust-traits-and-generics.md) (`dyn`, `Send`),
  [Smart Pointers](../foundations/rust-smart-pointers.md).
- **Skeleton and tests:** `src/c06_thread_pool.rs`:
  `c06_runs_all_jobs_before_drop_returns`, `c06_zero_workers_panics`.
- **Acceptance:** 100 jobs on 4 workers all run exactly once; a panicking job
  does not kill the pool (or is reported); no worker spins at 100% CPU while
  idle.
- **Stretch:** return a handle with the job's result; a bounded queue with
  backpressure; work stealing (study `crossbeam-deque` and `rayon`); a
  `scope`-style API that accepts non-`'static` closures.

## 8. "Project 7: how do I build an interpreter?"

**Answer:**

- **Goal:** evaluate arithmetic with variables: `1 + 2 * 3`, `-x + 10`,
  parentheses. Then add `let` bindings, functions, and `if`.
- **Core idea:** three steps: **tokenize** (text to tokens), **parse**
  (tokens to a tree, `enum Expr` with `Box` children), **evaluate** (walk the
  tree). Errors are values, not panics.
- **Needs:** [Types, Enums & Patterns](../foundations/rust-types-enums-and-patterns.md),
  [Smart Pointers §2](../foundations/rust-smart-pointers.md#2-when-do-you-use-boxt) (`Box` for
  recursive types), [Error Handling](../foundations/rust-error-handling.md).
- **Skeleton and tests:** `src/c07_interpreter.rs`: `c07_precedence_and_parens`,
  `c07_errors_are_values`.
- **Acceptance:** error messages include the position (line and column);
  deeply nested input (10,000 parentheses) returns an error instead of a stack
  overflow.
- **Stretch:** a bytecode compiler and a stack VM, then compare speed; a
  string type with `Rc<str>`; closures that capture their environment
  ([Iterators & Closures](../foundations/rust-iterators-and-closures.md)); a
  macro-free parser built with `chumsky`/`winnow` for comparison.

## 9. "Project 8: how do I build an arena allocator?"

**Answer:**

- **Goal:** `Arena::alloc<T>(&self, value) -> Option<&mut T>` hands out many
  values from one block of memory, correctly aligned. Everything is freed at
  once when the arena drops.
- **Core idea:** a **bump allocator** keeps an offset; each allocation rounds
  the offset up to `align_of::<T>()`, checks space, writes the value, and
  moves the offset. The tricky part is returning `&mut T` from `&self`, which
  needs interior mutability and a safety argument.
- **Needs:** [Memory Layout & DSTs](../advanced-language/rust-memory-layout-and-dsts.md),
  [Unsafe & Miri](../advanced-language/rust-unsafe-and-miri.md),
  [Variance & Drop Check](../advanced-language/rust-variance-dropck-and-phantomdata.md).
- **Skeleton and tests:** `src/c08_arena.rs`: `c08_allocates_distinct_aligned_values`,
  `c08_full_arena_returns_none`.
- **Acceptance:** `cargo +nightly miri test c08` is clean (no out-of-bounds, no
  misalignment, no aliasing violation); every `unsafe` block has a `// SAFETY:`
  comment that names the invariant.
- **Stretch:** run destructors of arena values on drop (keep a list of drop
  glue); grow by chaining chunks; a typed arena (`TypedArena<T>`); compare
  with the `bumpalo` crate; zero-sized types.

## 10. "Project 9: how do I build a lock-free queue and prove it with `loom`?"

**Answer:**

- **Goal:** a bounded single-producer, single-consumer (SPSC) ring buffer
  with `push` and `pop` that never takes a lock.
- **Core idea:** two atomic counters, `head` (consumer) and `tail` (producer).
  The producer writes a slot, then publishes with a **`Release`** store of
  `tail`. The consumer reads `tail` with **`Acquire`**, then the slot. That
  pairing is the whole correctness argument.
- **Needs:** [Atomics & Memory Ordering](../concurrency-and-async/rust-atomics-and-memory-ordering.md),
  [Unsafe & Miri](../advanced-language/rust-unsafe-and-miri.md),
  [Variance & Drop Check](../advanced-language/rust-variance-dropck-and-phantomdata.md)
  (`PhantomData`, `Send`/`Sync`).
- **Skeleton and tests:** `src/c09_queue.rs`: `c09_fifo_order_single_thread`,
  `c09_two_threads_see_every_item_once_in_order`.
- **Acceptance:** a `loom` model with one producer and one consumer explores
  every thread interleaving and passes; run the stress test 100 times;
  `Drop` frees items still in the queue (no leak under Miri).
- **Stretch:** weaken orderings from `SeqCst` to the minimum and let `loom`
  find your mistakes; cache-line padding to avoid **false sharing**
  (measure it); a multi-producer version; compare with `crossbeam` and
  `std::sync::mpsc`.

## 11. "Project 10: how do I build a tiny async runtime?"

**Answer:**

- **Goal:** `block_on`, a single-threaded `Executor` with `spawn` and `run`,
  and a `sleep` future driven by a timer.
- **Core idea:** a future is just a state machine with a `poll` method. A
  **waker** is how a future tells the executor "poll me again". The executor
  keeps a queue of ready tasks and **parks the thread** when it is empty.
- **Needs:** [Async Internals](../concurrency-and-async/rust-async-internals.md),
  [Smart Pointers §7](../foundations/rust-smart-pointers.md#7-what-is-pin-in-one-paragraph) (`Pin`),
  [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md)
  (`park`/`unpark`).
- **Skeleton and tests:** `src/c10_runtime.rs`: `c10_block_on_returns_value`,
  `c10_runs_every_task`, `c10_sleep_waits`. The skeleton's `sleep` is a
  placeholder (`std::future::ready`) so it compiles; the `c10_sleep_waits`
  test is the one that proves your real timer.
- **Acceptance:** the thread uses no CPU while all tasks wait; a task that
  wakes itself many times does not starve others; dropping a task cancels it.
- **Stretch:** a multi-threaded executor with a shared queue; a `JoinHandle`
  that returns the task's output; a timer wheel; compare behavior with Tokio
  on the same workload ([Tokio & Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md)).

## 12. "Which projects fit which goal?"

**Answer:**

| Your goal | Do these | Then read |
|---|---|---|
| Backend services | 1, 3, 4, 5, 6 | [Web Services with Axum](../production/rust-web-services-with-axum.md), [Databases](../production/rust-databases.md) |
| Systems / infrastructure | 3, 4, 6, 8, 9 | [Performance Engineering](../performance-and-internals/rust-performance-engineering.md) |
| Compilers / languages | 2, 7, 10 | [How rustc Works](../performance-and-internals/rustc-how-the-compiler-works.md) |
| Embedded / WASM | 2, 7, 8 | [no_std & Embedded](../performance-and-internals/rust-no-std-and-embedded.md), [WebAssembly](../performance-and-internals/rust-webassembly.md) |
| Interview "depth" stories | 6, 9, 10 | [Guru Question Bank](rust-guru-question-bank.md) |

## 13. "How do AI tools help or hurt when I build these?"

**Answer:**

- **Hurt:** if an assistant writes the project, you skip the learning that
  was the point. For capstones, **write the first version yourself** and use
  the assistant as a reviewer.
- **Help:** after your tests pass, ask: "review this for ownership problems,
  needless clones, and missing error cases" and compare with your own list.
- **Help:** ask it to **generate adversarial test inputs** (malformed
  requests, huge inputs, partial reads) and add the good ones to your suite.
- **Hurt:** lock-free and `unsafe` code. Assistants write code that looks
  right and is not. Treat a suggestion as unverified until **Miri** and
  **`loom`** pass.
- **Help:** explain a failing `loom` trace or Miri message in plain words,
  then **you** fix the cause.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md)
  for how interviewers now ask about your tool use.

## 14. Interview Questions You're Likely to Get Asked

**About your projects**

- "Walk me through the hardest bug in your thread pool." — expects: a concrete
  story (a deadlock from holding the receiver lock while running a job, or a
  missing `drop` of the sender), [§7](#7-project-6-how-do-i-build-a-thread-pool).
- "How did you prove your queue correct?" — expects: `Release`/`Acquire`
  pairing, `loom` interleavings, Miri, a stress test,
  [§10](#10-project-9-how-do-i-build-a-lock-free-queue-and-prove-it-with-loom).
- "Why did your arena need `unsafe`, and how did you contain it?" — expects: a
  small safe API, `// SAFETY:` comments, Miri,
  [§9](#9-project-8-how-do-i-build-an-arena-allocator).
- "How does your executor know when to poll a task again?" — expects: the
  waker, a ready queue, parking,
  [§11](#11-project-10-how-do-i-build-a-tiny-async-runtime).

**Design**

- "How would you make your key-value store crash safe?" — expects: log before
  apply, flush or `fsync`, checksums, atomic rename for compaction,
  [§4](#4-project-3-how-do-i-build-a-key-value-store-with-a-write-ahead-log).
- "How do you stop a slow chat client from hurting everyone?" — expects:
  bounded channel, drop or disconnect, backpressure,
  [§6](#6-project-5-how-do-i-build-an-async-chat-server).
- "Why separate pure logic from I/O in a server?" — expects: tests without
  sockets, [§6](#6-project-5-how-do-i-build-an-async-chat-server).

---

## Code Samples

- `code_samples/rust/capstones/`: a separate Cargo package (`rust-capstones`)
  with one file per project (`src/c01_grep.rs` to `src/c10_runtime.rs`),
  `todo!()` bodies, and ignored acceptance tests. It uses only `std`.
- `code_samples/rust/capstones/README.md`: the workflow.

```bash
cd code_samples/rust/capstones
cargo build                     # skeletons compile
cargo test -- --ignored         # every unfinished project (all red at the start)
cargo test c06                  # after you implement project 6 and remove #[ignore]
cargo +nightly miri test c08    # project 8 under Miri (needs the nightly toolchain)
```
