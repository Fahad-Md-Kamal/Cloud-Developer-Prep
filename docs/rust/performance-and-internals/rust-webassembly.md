---
title: Rust and WebAssembly — Targets, wasm-bindgen, Size Tuning, WASI, and the Component Model
---

# Rust and WebAssembly

**WebAssembly (Wasm)** is a compact binary format for programs, run by a
small **virtual machine** (VM) inside a browser, in Node.js, or in a
standalone runtime. The VM is a **sandbox**: a Wasm module can only touch
the memory it owns and call the functions the host gives it. Rust compiles
to Wasm well because it has no garbage collector and no heavy runtime, so
files are small and fast to start.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**, with `wasm-bindgen`
    **0.2.130**. Everything below was built and run on one machine
    (aarch64 macOS, Node.js 22.18) using Node as the host. **Not run:**
    `wasm-pack`, `trunk`, `wasm-opt`, `wasmtime`, and the component-model
    tools. They are described, with that said where it matters. Sizes are
    for the sample crates and will differ for real programs.

## 1. "What is a Wasm module, and what can it do?"

**Answer:**

- A **module** is a file (`.wasm`) of typed functions. It has four kinds of
  things at its edge:
    - **Exports**: functions the host can call (the sample exports `add`,
      `fib`, `alloc`, `checksum`).
    - **Imports**: functions the module needs from the host (a logger, a
      clock). **The sandbox has no other way out.**
    - **Linear memory**: one resizable array of bytes that the module
      reads and writes. It is exported, so the host can read it too.
    - **Tables**: arrays of function references (used for function
      pointers).
- Wasm has **only four value types** at the boundary: `i32`, `i64`, `f32`,
  `f64`. Strings, structs, and lists are **not** wasm types. They are bytes
  in linear memory, and the module passes **a pointer and a length** (§4).
- Wasm is **not only for browsers**. The same file runs in Node.js, in
  edge platforms, in plugin systems, and in standalone runtimes
  (`wasmtime`, `wasmer`), because the sandbox is the security model.
- Pointers are **32 bits** on `wasm32` targets, so a module can address at
  most 4 GiB.

## 2. "Which Rust targets are there, and which one do I pick?"

**Answer:**

- A target says what the module expects from its host. `rustup target
  list` on 1.99.1 shows these Wasm targets:

| Target | Host it assumes | Use it for |
|---|---|---|
| `wasm32-unknown-unknown` | **nothing** (no OS, no files); a browser or JS host | browser apps, `wasm-bindgen` libraries |
| `wasm32-wasip1` | **WASI** preview 1 (a small system interface: files, args, env, clock) | command-line tools and servers on a Wasm runtime |
| `wasm32-wasip2` | WASI preview 2, built on the **component model** (§8) | new work on runtimes that support it (**Tier 2** since 1.82) |
| `wasm32-wasip1-threads` | WASI with threads | threaded WASI programs |
| `wasm32v1-none` | no OS, **only the original Wasm 1.0 features** (**Tier 2** since 1.84) | the widest compatibility, embedded hosts |
| `wasm32-unknown-emscripten` | the Emscripten C/C++ toolchain | porting code that links C libraries |

- **Names changed:** the old `wasm32-wasi` target was **removed** (1.84).
  Use `wasm32-wasip1`. Old tutorials with `wasm32-wasi` will fail.
- **Rule of thumb:** browser or JS glue: `wasm32-unknown-unknown`. Runs on
  a server runtime with files and clock: `wasm32-wasip1` or `wasip2`.
- Install a target once: `rustup target add wasm32-unknown-unknown`.

## 3. "What is the smallest Rust program that runs as Wasm?"

**Answer:**

- A `cdylib` (a C-style dynamic library, which is what Wasm needs) with
  `extern "C"` functions:

```toml
[lib]
crate-type = ["cdylib"]
```

```rust
#[unsafe(no_mangle)]
pub extern "C" fn add(a: i32, b: i32) -> i32 { a + b }

#[unsafe(no_mangle)]
pub extern "C" fn fib(n: u32) -> u64 {
    let (mut a, mut b) = (0u64, 1u64);
    for _ in 0..n { (a, b) = (b, a + b); }
    a
}
```

- `#[unsafe(no_mangle)]` keeps the exported name exactly `add` (2024
  edition syntax: `no_mangle` is an unsafe attribute).
- Build and run it from Node:

```bash
cargo build --release --target wasm32-unknown-unknown
node run.mjs
```

```js
const { instance } = await WebAssembly.instantiate(readFileSync(path), {});
console.log("add(2, 40) =", instance.exports.add(2, 40));
console.log("fib(50)    =", instance.exports.fib(50));
```

```text
add(2, 40) = 42
fib(50)    = 12586269025n
checksum   = 2690260274
exports    = memory, add, alloc, checksum, fib
```

- Read the output:
    - `fib(50)` printed `12586269025n`: the `n` means a JavaScript
      **BigInt**. A Rust `u64` is a Wasm `i64`, and JS maps `i64` to BigInt.
    - A `u32` result arrives in JS as a **signed** `i32`: the sample uses
      `>>> 0` to read it as unsigned.
    - `memory` is exported automatically: that is the linear memory.
- **Since 1.89** the `extern "C"` ABI on `wasm32-unknown-unknown` follows
  the **standard C ABI for Wasm**. Before, Rust differed from C in how
  structs were passed, which broke linking Rust and C.
- An older, related change: a future-compatibility warning about this ABI
  (`wasm_c_abi`) became a hard error, and `wasm-bindgen` older than 0.2.89
  stopped building. Keep `wasm-bindgen` current.

## 4. "How do you pass strings and structs to and from JavaScript?"

**Answer:**

- **By hand:** put bytes in linear memory and pass a pointer and a length.
  The sample exports an allocator the host can call, then a function that
  takes ownership back:

```rust
#[unsafe(no_mangle)]
pub extern "C" fn alloc(len: usize) -> *mut u8 {
    let mut v = Vec::<u8>::with_capacity(len);
    let p = v.as_mut_ptr();
    core::mem::forget(v);          // do not free: the host will fill it
    p
}

/// # Safety
/// `ptr` and `len` must come from `alloc` (same length).
#[unsafe(no_mangle)]
pub unsafe extern "C" fn checksum(ptr: *mut u8, len: usize) -> u32 {
    let v = unsafe { Vec::from_raw_parts(ptr, len, len) };   // takes ownership: freed on drop
    v.iter().fold(0u32, |h, &b| h.wrapping_mul(31).wrapping_add(b as u32))
}
```

```js
const bytes = new TextEncoder().encode("hello wasm");
const ptr = w.alloc(bytes.length);
new Uint8Array(w.memory.buffer, ptr, bytes.length).set(bytes);   // write into wasm memory
console.log("checksum =", w.checksum(ptr, bytes.length) >>> 0);
```

- **Rules of the hand-written way**: who allocates and who frees must
  be agreed. Here Rust allocates, JS fills, Rust frees. A JS view of
  `memory.buffer` becomes **invalid if memory grows**, so make the view
  right before use. The same ownership questions appear in
  [FFI & C Interop](../advanced-language/rust-ffi-and-c-interop.md).
- **With `wasm-bindgen`:** a build step generates the glue code, so you
  write ordinary Rust and use strings, structs, and callbacks. Sample
  (`wasm_bindgen_demo`):

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn greet(name: &str) -> String {
    format!("Hello, {name}!")
}

#[wasm_bindgen]
pub struct Counter { n: u32 }

#[wasm_bindgen]
impl Counter {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Counter { Counter { n: 0 } }
    pub fn bump(&mut self) -> u32 { self.n += 1; self.n }
}
```

```bash
cargo build --release --target wasm32-unknown-unknown
wasm-bindgen --target nodejs --out-dir pkg target/wasm32-unknown-unknown/release/wasm_bindgen_demo.wasm
node run.cjs
```

```text
Rust sees name = Rust
Hello, Rust!
counter = 2
callback 1
callback 2
callback 3
```

- What `wasm-bindgen` produced in `pkg/`: `wasm_bindgen_demo_bg.wasm` (23 144
  bytes), a `.js` file of glue (5 396 bytes), and TypeScript declarations
  (`.d.ts`) so JS and TS callers get types.
- **Two details:**
    - **The CLI and the crate must have the same version.** Both were
      `0.2.130` here. A mismatch is rejected with an error.
    - **JS owns Rust structs.** `Counter` lives in Wasm memory, and
      JavaScript's garbage collector does not know its size, so the sample
      calls `c.free()`. Forgetting it leaks.
- **Which tool wraps the steps:**
    - **`wasm-pack`** runs `cargo build`, `wasm-bindgen`, and optionally
      `wasm-opt`, then writes an npm-ready package (not run here).
    - **`trunk`** builds and serves a whole browser app, with Rust in
      the front end (not run here).
    - **`web-sys` and `js-sys`** are crates with the browser and JS
      built-ins (DOM, `fetch`, `Promise`) already declared.
    - **Frameworks** (Yew, Leptos, Dioxus) build whole web apps in Rust on
      top of these.

## 5. "How does Wasm call back into the host?"

**Answer:**

- A Wasm module **imports** host functions. In Rust, declare them in an
  `unsafe extern` block (the 2024 edition requires the `unsafe`):

```rust
#[link(wasm_import_module = "env")]
unsafe extern "C" {
    fn host_log(x: i32);
}
```

- The host must supply `env.host_log` in the **import object** when it
  instantiates the module: `WebAssembly.instantiate(bytes, { env: { host_log } })`.
- `wasm-bindgen` writes this glue for you (`#[wasm_bindgen] extern "C" {
  fn log(s: &str); }` in the sample calls `console.log`).
- **Since 1.96** `rustc` no longer passes `--allow-undefined` to the
  linker on Wasm targets (listed under *Compatibility Notes* in the 1.96
  release notes). An `extern` function with **no definition and no import
  module** is now a link error, not a silent import. Real output (the
  same code without `#[link(wasm_import_module)]`):

```text
error: linking with `rust-lld` failed: exit status: 1
  = note: rust-lld: error: ...undefined_import...rcgu.o: undefined symbol: host_log
```

- Adding the `#[link(wasm_import_module = "env")]` attribute made the same file
  build, because it declares where the import comes from.
- **Cost of crossing the boundary:** each call between JS and Wasm has a
  fixed price, and copying strings is real work. Make **few, large calls**
  (pass a whole buffer) instead of many tiny ones.

## 6. "How do you make a WebAssembly file small?"

**Answer:**

- Size matters because the browser **downloads** the file. Measured with
  the plain sample (`wasm_demo`), same code each time:

| Build | `.wasm` size |
|---|---|
| debug (`cargo build`, no `--release`) | 1 766 516 bytes |
| release, `opt-level = 3`, stripped | 15 006 bytes |
| release, `opt-level = "s"` or `"z"`, stripped | 13 873 bytes |
| release, `"z"` **without** `strip = true` | 97 876 bytes |

- Read it: the **debug build is over 100 times bigger**; **stripping**
  symbols and debug info is the biggest release-mode win; `"s"` versus `"z"`
  made no difference for this tiny crate.
- The profile used:

```toml
[profile.release]
opt-level = "z"      # optimize for size ("s" is similar)
lto = true           # cross-crate optimization
codegen-units = 1    # one unit: better size
panic = "abort"      # no unwinding tables
strip = true         # remove names and debug info
```

- More steps, **not run here**:
    - **`wasm-opt -Oz`** (from the Binaryen project; `wasm-pack` can call
      it) usually shrinks the result further.
    - **`twiggy`** shows which functions take space, like `cargo bloat`
      for Wasm.
    - **Avoid the formatting machinery** (`format!`, `{:?}`) and large
      dependencies in size-critical code. They pull in hundreds of
      kilobytes. `panic = "abort"` plus `no_std` is the smallest path (see
      [no_std & Embedded](rust-no-std-and-embedded.md)).
    - **Compress on the wire.** Servers should send `.wasm` with **gzip or
      Brotli**; text-like Wasm compresses well.
- The `wasm-bindgen` module above was 23 144 bytes because it also holds
  string-passing code and the allocator glue.

## 7. "What is WASI, and how is it different from the browser?"

**Answer:**

- **WASI (WebAssembly System Interface)** is a standard set of host
  functions for **files, command-line arguments, environment variables, the
  clock, and random numbers**, so an ordinary Rust program with `std` can
  run outside a browser. Capabilities are **granted by the host**: a
  program sees only the directories it was given.
- The sample is a normal `std` program:

```rust
fn main() {
    println!("args: {:?}", env::args().collect::<Vec<_>>());
    println!("HOME-like var: {:?}", env::var("DEMO"));
    fs::write("/sandbox/out.txt", "written from wasm").unwrap();
    println!("read back: {}", fs::read_to_string("/sandbox/out.txt").unwrap());
}
```

```bash
rustup target add wasm32-wasip1
cargo build --release --target wasm32-wasip1 --example hello_wasi
node run_wasi.mjs        # Node's built-in node:wasi host; a temp dir is preopened as /sandbox
```

```text
args: ["hello_wasi", "x"]
HOME-like var: Ok("1")
read back: written from wasm
host sees: written from wasm
```

- `/sandbox` is the **only** path the program could write; Node mapped it
  to a temporary directory. The same file also runs on `wasmtime` or
  `wasmer` (not run here).
- The binary was 66 895 bytes in `release`, larger than the plain Wasm
  sample because `std` (formatting, file code) is included.
- **`wasm32-unknown-unknown` has `std` types that exist but do nothing.**
  They compile and then fail when called. Real results from a test module
  built for that target:

```text
spawn ok = 0                          (std::thread::Builder::spawn returned Err)
clock trapped: RuntimeError unreachable   (std::time::Instant::now() panicked)
```

- `unreachable` is a panic with `panic = "abort"`. On this target use
  JavaScript's clock (through an import), not `Instant`.

## 8. "What is the component model?"

**Answer:**

- A plain Wasm module only speaks numbers, so every language pair needs
  hand-made glue (§4). The **component model** is the standard answer: a
  **component** is a Wasm module plus a typed description of its imports
  and exports, written in **WIT (Wasm Interface Type)** files with real
  types (strings, records, lists, variants, resources).
- Any language that targets components can call any other **without custom
  glue**. `wasm32-wasip2` produces components, and WASI preview 2 is itself
  defined in WIT.
- Rust tools: **`wit-bindgen`** generates Rust bindings from a WIT file;
  **`cargo component`** builds components. **`wasmtime`** is the main
  runtime. (None run here; check the current docs before relying on them,
  since this area still moves.)
- Choose by need: **browser** work still uses `wasm-bindgen`; **server and
  plugin** work is moving toward components.

## 9. "What are the limits of Wasm in Rust?"

**Answer:**

- **No direct DOM or network.** The module calls JS imports (`web-sys`
  declares them), so browser work always goes through the JS side.
- **No clock, threads, or files** on `wasm32-unknown-unknown` (§7).
  Threads in a browser need special set-up (shared memory) and are an
  advanced topic not covered here.
- **32-bit address space**: at most 4 GiB; `usize` is 32 bits.
- **Speed**: close to native for number crunching, but **not** free: every
  call to JS costs, and a module that spends its time crossing the boundary
  is slower than JS.
- **Debugging**: browser DevTools can step through Wasm, and `debug = true`
  keeps names; panics show as `unreachable` unless you add a panic hook
  (the `console_error_panic_hook` crate prints the message).
- **Good fits:** image and audio processing, parsers, crypto, games, and
  moving a proven Rust library to the browser. **Poor fits:** code that is
  mostly DOM updates.

## 10. "How do AI tools help or hurt here?"

**Answer:**

- **Help:**
    - Ask for the **JS glue** (`run.mjs`, import objects, typed array
      views) once you have the Rust exports.
    - Ask it to **port** a function from JavaScript to Rust and write the
      `wasm-bindgen` annotations.
    - Ask what the **build step** is for your goal (browser bundler, Node,
      WASI runtime).
- **Hurt:**
    - It often uses **removed names** (`wasm32-wasi`) or **old
      `wasm-bindgen` APIs**, and may pair a CLI and crate of different
      versions. Pin both, and read the build error.
    - It may claim "Wasm is always faster than JavaScript". Measure, with
      the boundary cost included.
    - It may suggest `std::time` or threads on `wasm32-unknown-unknown`,
      which compile and then fail (§7).
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Basics**

- "What can cross the Wasm boundary directly?" — expects: only `i32`, `i64`,
  `f32`, `f64`; everything else goes through linear memory,
  [§1](#1-what-is-a-wasm-module-and-what-can-it-do).
- "`wasm32-unknown-unknown` or `wasm32-wasip1`?" — expects: no OS, JS host vs
  WASI with files and clock; `wasm32-wasi` is gone,
  [§2](#2-which-rust-targets-are-there-and-which-one-do-i-pick).

**Data across the boundary**

- "How do you pass a string to Wasm?" — expects: write bytes into linear
  memory, pass pointer and length, agree who frees; or `wasm-bindgen`,
  [§4](#4-how-do-you-pass-strings-and-structs-to-and-from-javascript).
- "Why must `wasm-bindgen` CLI and crate versions match?" — expects: the
  generated glue and the crate's embedded schema must agree,
  [§4](#4-how-do-you-pass-strings-and-structs-to-and-from-javascript).
- "Why does a `u64` come back as a BigInt?" — expects: `i64` maps to BigInt
  in JS, [§3](#3-what-is-the-smallest-rust-program-that-runs-as-wasm).

**Size and performance**

- "Your `.wasm` is 2 MB. What do you try?" — expects: release, `opt-level =
  "z"`, `lto`, `strip`, `panic = "abort"`, `wasm-opt`, avoid `format!`, check
  with `twiggy`, compress, [§6](#6-how-do-you-make-a-webassembly-file-small).
- "When is Wasm slower than JS?" — expects: many small calls across the
  boundary, DOM-heavy work, [§9](#9-what-are-the-limits-of-wasm-in-rust).

**Beyond the browser**

- "What is WASI?" — expects: standard host functions with capabilities
  granted by the host, [§7](#7-what-is-wasi-and-how-is-it-different-from-the-browser).
- "What does the component model add?" — expects: typed interfaces in WIT,
  no hand-made glue between languages, [§8](#8-what-is-the-component-model).

---

## Code Samples

All files are in `code_samples/rust/` as separate packages (each has its
own `Cargo.toml`) and were run on Rust 1.99.1 with Node.js 22.

- `wasm_demo/` — plain Wasm with no dependencies:
    - `src/lib.rs` (exports `add`, `fib`, `alloc`, `checksum`), `run.mjs`
    - `examples/hello_wasi.rs` and `run_wasi.mjs` (WASI with `node:wasi`)
    - `compile_fail/undefined_import.rs` (must fail to link)
    - `limits/limits_run.rs` (compiles; thread spawn fails and the clock
      traps at run time)
- `wasm_bindgen_demo/` — `wasm-bindgen` 0.2.130: string, struct, JS callback;
  `run.cjs`.

```bash
rustup target add wasm32-unknown-unknown wasm32-wasip1

cd code_samples/rust/wasm_demo
cargo build --release --target wasm32-unknown-unknown
node run.mjs
cargo build --release --target wasm32-wasip1 --example hello_wasi
node run_wasi.mjs
rustc --edition 2024 --target wasm32-unknown-unknown --crate-type=cdylib compile_fail/undefined_import.rs   # fails to link

cd ../wasm_bindgen_demo
cargo install wasm-bindgen-cli --version 0.2.130
cargo build --release --target wasm32-unknown-unknown
wasm-bindgen --target nodejs --out-dir pkg target/wasm32-unknown-unknown/release/wasm_bindgen_demo.wasm
node run.cjs
```
