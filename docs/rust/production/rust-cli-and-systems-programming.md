---
title: CLI Tools and Systems Programming
---

# CLI Tools and Systems Programming

A **command-line tool** is a program whose whole interface is: arguments in,
text and files in, text and files out, and an **exit code** that says
whether it worked. Rust is a very good fit for them: one static binary
with no runtime to install, fast start-up, and a type system that makes the
argument parsing and error handling hard to get wrong. This page builds a
small `grep` and then covers the system pieces every tool eventually needs:
files and streams, child processes, file locks, memory-mapped files,
signals and the environment.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Samples run on
    1.99.1 on macOS with `clap` 4.6.7, `anyhow` 1.0.104, `memmap2` 0.9.12
    and `ctrlc` 3.5.2. All outputs below are real. **Not run:** Windows
    behavior, and the `ratatui` terminal UI (mentioned only as a
    pointer).

## 1. "How do I parse arguments and print help?"

```rust
#[derive(Parser, Debug)]
#[command(version, about = "Print lines that contain PATTERN")]
struct Args {
    /// Text to look for
    pattern: String,
    /// Files to search; standard input when empty
    files: Vec<std::path::PathBuf>,
    /// Ignore upper/lower case
    #[arg(short, long)]
    ignore_case: bool,
    /// Print only the number of matching lines per input
    #[arg(short, long)]
    count: bool,
}
```

Real help output (`cli_grep --help`), generated from the struct and its doc
comments:

```text
Print lines that contain PATTERN

Usage: cli_grep [OPTIONS] <PATTERN> [FILES]...

Arguments:
  <PATTERN>   Text to look for
  [FILES]...  Files to search; standard input when empty

Options:
  -i, --ignore-case  Ignore upper/lower case
  -c, --count        Print only the number of matching lines per input
  -h, --help         Print help
  -V, --version      Print version
```

**Answer:**

- **`clap`** (Command Line Argument Parser) with the **derive** API: you
  write a struct, and `Args::parse()` builds it from the real arguments. A
  `bool` field is a flag, `Vec<PathBuf>` is "zero or more", `Option<T>` is
  optional, a `String` without `#[arg]` is a required positional.
- Doc comments (`///`) become the help text. `#[command(version)]` adds
  `--version` from `Cargo.toml`.
- **Errors are handled for you.** Missing the required pattern gives a usage
  message and **exit code 2**. Real output:

```text
error: the following required arguments were not provided:
  <PATTERN>

Usage: cli_grep <PATTERN> [FILES]...

For more information, try '--help'.
```

- Use `PathBuf`, not `String`, for file arguments: paths on Unix are bytes,
  not always valid UTF-8, and `PathBuf` keeps them intact. (Strings:
  [Collections & Strings §3](../foundations/rust-collections-and-strings.md#3-how-do-strings-work-why-cant-you-index-them).)
- Subcommands (`git commit`, `git push`) are an `enum` with
  `#[derive(Subcommand)]`. Also add shell completions with `clap_complete`
  and a man page with `clap_mangen` if you ship the tool (neither run
  here).
- Alternatives exist for tiny tools (`std::env::args()` plus manual
  parsing, or lighter crates such as `lexopt` and `pico-args`). Derive with
  `clap` is the default for anything users will see.

## 2. "What should my tool return? How do exit codes work?"

```rust
fn main() -> ExitCode {
    match run(&Args::parse()) {
        Ok(true) => ExitCode::SUCCESS,
        Ok(false) => ExitCode::from(1),
        Err(e) => {
            eprintln!("error: {e:#}");
            ExitCode::from(2)
        }
    }
}
```

Real runs (`-i alpha` on a file with `Alpha`, `beta`, `alphabet`):

```text
$ cli_grep -i alpha /tmp/g1.txt        -> two lines printed, exit=0
$ cli_grep zzz /tmp/g1.txt             -> nothing printed,   exit=1
$ cli_grep x /nope.txt                 -> exit=2
error: cannot open /nope.txt: No such file or directory (os error 2)
```

**Answer:**

- The **exit code** is how scripts and CI know what happened. By
  convention `0` is success and anything else is failure. Follow the
  convention of the tool you imitate: `grep` uses `0` found, `1` not found,
  `2` error. Document your codes.
- `fn main() -> ExitCode` is the clean way. `ExitCode::SUCCESS`,
  `ExitCode::FAILURE`, `ExitCode::from(n)`.
- `fn main() -> Result<(), E>` also works: on `Err` it prints the `Debug`
  form of the error and exits with code **1**. That is fine for a quick
  script, but the `Debug` text is ugly; format the message yourself for
  users.
- **`std::process::exit(n)` ends the process immediately and skips
  destructors** (buffers not flushed, locks not released). Prefer
  returning from `main`.
- **Messages and data go to different streams.** Normal output to
  standard output (`println!`), errors and progress to standard error
  (`eprintln!`), so `tool > out.txt` keeps errors on screen and pipes see
  clean data.
- Use **`anyhow`** with `.with_context(..)` for application errors. The
  `{e:#}` format prints the whole chain on one line, as in the real
  output above:
  `error: /tmp/g2.txt: line 1 is not valid UTF-8 ...: stream did not contain valid UTF-8`
  ([Error Handling §5](../foundations/rust-error-handling.md#5-when-do-you-use-thiserror-and-when-anyhow)).

## 3. "How do I read and write files and streams efficiently?"

```rust
fn search(args: &Args, name: &str, input: impl BufRead, out: &mut impl Write) -> anyhow::Result<usize> {
    for (i, line) in input.lines().enumerate() {
        let line = line.with_context(|| format!("{name}: line {} ...", i + 1))?;
        // ...
        writeln!(out, "{name}:{}:{line}", i + 1)?;
    }
    // ...
}
```

**Answer:**

- **The traits are the design.** `Read` and `Write` are byte streams;
  `BufRead` adds `lines()` and `read_line()`. Files, standard input,
  network sockets, `&[u8]` and `Vec<u8>` all implement them. The function
  above takes `impl BufRead` and `impl Write`, so the **same code** works
  on a file, on stdin and in a unit test that passes `"abc\nxyz".as_bytes()`
  (the sample has 2 such tests; they pass).
- **Wrap in a buffer.** An unbuffered `File` makes one system call per
  read or write. Use `BufReader::new(file)` and `BufWriter::new(stdout)`
  for line-by-line work. `std::io::stdout()` is line-buffered already, but
  `BufWriter` is much faster for many small writes.
- **Flush `BufWriter` explicitly** (`out.flush()?`). If you let it drop,
  the final flush happens in `Drop`, and any error there is **ignored**.
- **`read_to_string` loads the whole file.** Fine for small config files;
  for large input stream it line by line (as above) or in chunks. A
  `lines()` loop uses memory proportional to the longest line, not the file.
- `fs::read_to_string`, `fs::write`, `fs::read_dir`, `fs::create_dir_all`
  and `fs::rename` cover the whole-file cases.
- **Invalid UTF-8.** `lines()` returns an `Err` for a line that is not
  valid UTF-8. Real behavior: a file with the bytes `ff fe` gave exit 2 and
  the message above. If your tool must handle arbitrary bytes, use
  `read_until(b'\n', ..)` on `&[u8]` or the `bstr` crate.
- **Writing safely:** to replace a file without leaving a half-written
  one, write to a temporary file in the same directory and then
  `fs::rename` it over the target (rename is atomic on the same
  file system on common platforms).

## 4. "What happens when the reader closes the pipe? (`| head`)"

```text
$ seq 1 2000000 | cli_grep 1 | head -1
-:1:1
(exit codes: seq 141, cli_grep 0, head 0)
```

**Answer:**

- Rust programs **ignore the SIGPIPE signal** at start-up (the usual
  C-program behavior would be to die silently). So when `head` exits and
  the pipe closes, the next `write` simply **returns an error**
  (`ErrorKind::BrokenPipe`).
- Without handling, the sample printed a noisy `error: Broken pipe (os
  error 32)` (observed in an earlier version). The fix is in `main`: treat
  `BrokenPipe` as a normal reason to stop and return quietly.
- Note that `println!` **panics** on a broken pipe, because it expects
  stdout to work. For tools meant to sit in pipelines, write with
  `writeln!(out, ..)` and handle the `Result`, as the sample does.
- The 141 in the real output belongs to `seq` (128 + 13, SIGPIPE), not to
  your program.

## 5. "How do I run other programs?"

```rust
// 1. Capture output. No shell is involved: arguments are not re-parsed.
let out = Command::new("echo").args(["hello", "$HOME", "a b"]).output()?;
// -> "hello $HOME a b\n"   (the $HOME was NOT expanded)

// 2. A pipeline by hand: child1 | child2
let mut c1 = Command::new("printf").arg("b\\na\\nc\\n").stdout(Stdio::piped()).spawn()?;
let sorted = Command::new("sort").stdin(c1.stdout.take().unwrap()).output()?;
c1.wait()?;
// -> "a\nb\nc\n"
```

Real output from `examples/sys_tour.rs`:

```text
echo -> "hello $HOME a b\n" status=exit status: 0
sorted -> "a\nb\nc\n"
false -> success=false code=Some(1)
missing -> No such file or directory (os error 2)
```

**Answer:**

- `Command::new("program").arg(..).args([..])` starts a program
  **directly**, with no shell. That is the safe default: user input in an
  argument cannot inject extra commands (`$HOME` stayed literal above).
  Never build `sh -c "..."` strings from untrusted input.
- Three ways to run: `.status()` (wait, inherit the terminal), `.output()`
  (wait, capture standard output and error), `.spawn()` (start and keep a
  `Child` handle).
- **A non-zero exit is not an `Err`.** `status()` returns `Ok` with an
  `ExitStatus` you inspect (`success()`, `code()`). `Err` means the program
  could not be **started** (`No such file or directory`, above).
- **Pipe deadlock:** if you capture two pipes with `.spawn()` and read them
  one after the other, a child that fills the second pipe while you wait on
  the first blocks forever. Use `.output()` (it reads both) or read in
  threads.
- `.env("K", "V")`, `.env_clear()`, `.current_dir(..)` configure the child.
  Children inherit your environment unless you clear it.
- Always `wait()` on spawned children; an unwaited child becomes a
  **zombie** until your program exits.

## 6. "How do I lock a file so two processes don't corrupt it?"

```rust
let mut a = OpenOptions::new().create(true).write(true).truncate(true).open(&path)?;
a.lock()?;                       // blocks until acquired (std, stable since 1.89)
writeln!(a, "line one\nline two\nneedle here")?;
let b = File::open(&path)?;
match b.try_lock() {
    Err(TryLockError::WouldBlock) => println!("second handle: WouldBlock"),
    other => println!("unexpected: {other:?}"),
}
a.unlock()?;
```

Real output:

```text
second handle: WouldBlock
after unlock, try_lock ok: true
```

**Answer:**

- `File::lock` (exclusive), `lock_shared`, `try_lock`, `try_lock_shared`
  and `unlock` are in the standard library since **Rust 1.89**. Before
  that you needed the `fs2` or `fd-lock` crates.
- **Exclusive** lock: one holder, for writers. **Shared** lock: many
  holders, for readers, but no writer.
- The lock is released when the file is **closed** (dropped) or by
  `unlock`. If your process crashes, the operating system releases it.
- **Advisory, not mandatory:** the lock only works if **every** process
  that touches the file asks for it. Another program that ignores locks can
  still write. Use a lock file or a database for real coordination.
- Behavior differs by platform and file system (network file systems are the
  usual problem). Read the "Platform-specific behavior" section of the
  `File::lock` documentation before relying on it. The output above is from
  macOS only.
- Typical uses: a single-instance guard (`try_lock` on a PID file), and
  serializing writes to a shared state file.

## 7. "What is a memory-mapped file, and when should I use one?"

```rust
// `unsafe` because another process could truncate or change the file while we read it.
let map = unsafe { memmap2::Mmap::map(&File::open(&path)?)? };
let pos = map.windows(6).position(|w| w == b"needle");
// -> mmap: 30 bytes, 'needle' at byte Some(18)
```

**Answer:**

- **Memory mapping** asks the operating system to make a file look like a
  region of memory. You index it like a `&[u8]`; the OS loads pages from
  disk on demand and shares them between processes. There is no `read`
  call and no copy into your buffer.
- Good for: **large read-mostly files** (search tools, indexes, databases)
  and random access without reading everything.
- Not good for: small files (setup cost), files on slow network disks, and
  anything another process may modify.
- **Why it is `unsafe`:** the compiler guarantees a `&[u8]` never changes.
  If the file is truncated while mapped, reading the missing pages crashes
  the process (a bus error), and if it is modified, your `&[u8]` changes
  under you. Rust cannot prevent that; **you** promise nobody does. See
  [Unsafe & Miri](../advanced-language/rust-unsafe-and-miri.md).
- The standard library has no memory-mapping API; the common crate is
  `memmap2` (used here).
- Ordinary `BufReader` is often **as fast** and needs no `unsafe`.
  Measure before choosing the map (see
  [Performance Engineering](../performance-and-internals/rust-performance-engineering.md)).

## 8. "How do I handle Ctrl-C and signals, and the environment?"

```rust
let stop = Arc::new(AtomicBool::new(false));
let s2 = stop.clone();
ctrlc::set_handler(move || s2.store(true, Ordering::SeqCst))?;
while !stop.load(Ordering::SeqCst) {
    std::thread::sleep(std::time::Duration::from_millis(10));
}
println!("got Ctrl-C, shutting down cleanly");
```

Real output (the sample sends itself `SIGINT` with `kill -INT`):

```text
PATH set: true  MISSING: Err(NotPresent)
got Ctrl-C, shutting down cleanly
```

**Answer:**

- A **signal** is a message from the operating system: Ctrl-C sends
  `SIGINT`, a container stop sends `SIGTERM`. The default is to kill
  the process, with no clean-up.
- Handlers run in a **restricted context**: they may only do a few safe
  things. The standard pattern is what the sample does: the handler sets an
  **atomic flag**, and the main loop checks it and shuts down normally. (More
  on atomics: [Atomics & Memory Ordering](../concurrency-and-async/rust-atomics-and-memory-ordering.md).)
- `ctrlc` handles Ctrl-C (and, with a feature, `SIGTERM`). For other
  signals use `signal-hook` (Unix). In an async program use
  `tokio::signal` (see
  [Tokio & Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md)).
- **Environment:** `std::env::var("NAME")` returns `Result<String,
  VarError>`; a missing variable is `Err(NotPresent)` (shown above).
  `var_os` returns an `OsString` for values that are not valid UTF-8.
  `std::env::args()` panics on non-UTF-8 arguments; use `args_os()` to be
  safe.
- Since the 2024 edition, **`std::env::set_var` is `unsafe`**, because
  changing the environment while another thread reads it is a data race at
  the C library level. Set variables **before** starting threads, or pass
  values explicitly. (Editions:
  [Modules, Crates & Editions §5](../foundations/rust-modules-crates-and-editions.md#5-what-changed-in-the-2024-edition).)
- Read configuration in a fixed order: **defaults, then config file, then
  environment, then command-line flags**, with flags winning. `clap` can
  read an environment variable as a fallback for a flag with
  `#[arg(env = "NAME")]` (needs the `env` feature of `clap`).
- **Terminal user interfaces** (full-screen apps, tables, key handling)
  are a separate topic. The common crates are `ratatui` and
  `crossterm`; not covered or run here.

## 9. "How do I make a CLI feel professional?"

**Answer:**

- **Unix conventions:** data to stdout, messages to stderr, meaningful exit
  codes, `--help` and `--version`, `-` meaning "read standard input",
  respect `NO_COLOR`, and no color or progress bars when output is not a
  terminal (`std::io::IsTerminal` is in the standard library).
- **Separate the library from the binary.** Put the logic in `src/lib.rs`
  and keep `main.rs` to a few lines, so you can test the logic and reuse
  it. The sample's `search` function takes `impl BufRead` and `impl Write`
  for exactly this reason.
- **Test the binary itself** with the `assert_cmd` and `predicates` crates
  (run the compiled program, check output and exit code); not run here.
- **Ship it:** `cargo install --path .` for developers; static binaries
  and installers through release tooling (see
  [CI/CD & Supply Chain](rust-ci-cd-and-supply-chain.md)). Strip and
  optimize the release profile for size if it matters.
- **Be explicit about platforms.** Paths, line endings, signals and file
  locks differ on Windows. Decide what you support and test it in CI.

## 10. "How do AI tools help or hurt with CLI and systems code?"

**Answer:**

- Good for: the `clap` struct from a description of the flags, test cases
  for argument combinations, and translating a shell script into Rust.
- They often write `Command::new("sh").arg("-c").arg(format!(..))` with
  user input in it. That is command injection. Ask for `Command::new(program)`
  with separate `.arg(..)` calls.
- They use `unwrap()` on every I/O call and `println!` in loops (which panics
  on a closed pipe, §4). Ask for `?` with context and handle `BrokenPipe`.
- They recall the old `clap` 2 or 3 builder syntax (`App::new`, `.get_matches()`)
  and the `fs2` crate for locks. Current `clap` is the derive API of this
  page and locks are in `std` since 1.89.
- They reach for `unsafe` memory maps as "faster" without measuring.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Basics**

- "How do you parse arguments in Rust?" — expects `clap` derive, a struct
  with doc comments, automatic help and errors,
  [§1](#1-how-do-i-parse-arguments-and-print-help).
- "What should `main` return in a CLI?" — expects `ExitCode` (or
  `Result`), stdout for data and stderr for messages, avoid
  `process::exit`,
  [§2](#2-what-should-my-tool-return-how-do-exit-codes-work).
- "Why write `fn search(input: impl BufRead, out: impl Write)`?" —
  expects the same code for files, stdin and tests,
  [§3](#3-how-do-i-read-and-write-files-and-streams-efficiently).

**Practical**

- "What happens when your tool's output is piped to `head`?" — expects
  SIGPIPE is ignored, `write` returns `BrokenPipe`, `println!` panics,
  [§4](#4-what-happens-when-the-reader-closes-the-pipe-head).
- "How do you run a child process safely?" — expects no shell, separate
  args, a non-zero exit is not an `Err`,
  [§5](#5-how-do-i-run-other-programs).
- "What is wrong with `Command::new("sh").arg("-c").arg(user_input)`?" —
  expects command injection,
  [§5](#5-how-do-i-run-other-programs).
- "Why do you flush a `BufWriter` yourself?" — expects errors in `Drop`
  are ignored,
  [§3](#3-how-do-i-read-and-write-files-and-streams-efficiently).

**Systems**

- "Is memory mapping safe in Rust?" — expects `unsafe`, because the file
  can change or shrink; when it helps,
  [§7](#7-what-is-a-memory-mapped-file-and-when-should-i-use-one).
- "How do you shut down cleanly on Ctrl-C?" — expects a handler that sets
  an atomic flag, the main loop checks it,
  [§8](#8-how-do-i-handle-ctrl-c-and-signals-and-the-environment).
- "Are file locks mandatory?" — expects advisory only, platform
  differences,
  [§6](#6-how-do-i-lock-a-file-so-two-processes-dont-corrupt-it).

---

## Code Samples

Package `code_samples/rust/cli_grep/` (own `Cargo.toml`; Rust 1.99.1).

- `src/main.rs` — the `grep`-like tool, with 2 unit tests.
- `examples/sys_tour.rs` — child processes and a hand-built pipeline,
  file locks, a memory map, the environment, and Ctrl-C handling.

```bash
cd code_samples/rust/cli_grep
cargo test
printf 'Alpha\nbeta\nalphabet\n' > /tmp/g1.txt
cargo run -q -- -i alpha /tmp/g1.txt; echo "exit=$?"
cargo run -q -- --help
seq 1 2000000 | cargo run -q -- 1 | head -1
cargo run --example sys_tour
```
