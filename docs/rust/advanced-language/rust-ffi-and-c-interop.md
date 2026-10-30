---
title: Rust FFI and C Interoperability
---

# Rust FFI and C Interoperability

**FFI (Foreign Function Interface)** is how code written in one language calls
code written in another. Almost every language can talk to **C**, because C's
calling rules (the **ABI**, Application Binary Interface: how arguments are
passed and results returned) are simple and stable. So C is the common
language between Rust, Python, Node.js, Java, Swift and the operating system.
Rust can **call** C functions and **be called** from C. The compiler cannot
check anything across the border, so every crossing has a contract you must
state and keep: **types, ownership, panics and errors**. This page shows both
directions with a real C program, and the real compiler and runtime output.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. The package
    `code_samples/rust/ffi_demo/` was built and run on Rust 1.99.1 with
    Apple clang 21 (macOS, Apple Silicon). Static and dynamic linking both
    worked. The 2024 syntax (`unsafe extern`, `#[unsafe(no_mangle)]`) and
    C-variadic definitions (stable in 1.99) were compiled to confirm. Tools
    named in §10 (`bindgen`, `cbindgen`, PyO3, `napi-rs`, `uniffi`) were
    **not** run for this page. Prerequisites:
    [Unsafe Rust & Miri](rust-unsafe-and-miri.md) and
    [Memory Layout](rust-memory-layout-and-dsts.md).

## 1. "How does Rust call a C function?"

```rust
use std::ffi::{CStr, CString, c_char, c_int, c_void};

unsafe extern "C" {
    // `safe fn`: calling it cannot cause UB, so no `unsafe` block is needed.
    pub safe fn abs(x: c_int) -> c_int;
    // Takes a pointer, so it stays unsafe to call.
    pub fn strlen(s: *const c_char) -> usize;
}

println!("abs(-7) = {}", abs(-7));
let s = CString::new("héllo").unwrap();
println!("strlen = {}", unsafe { strlen(s.as_ptr()) });
```

```text
abs(-7) = 7
strlen("héllo") = 6 (bytes, not characters)
```

**Answer:**

- An **`extern` block** declares functions defined elsewhere. The linker
  finds them (here in the C standard library, which every Rust program on
  these platforms already links).
- **Edition 2024**: the block must be written **`unsafe extern`**. The
  declaration is a **claim** you make about the real function. If the
  signature you wrote is wrong, that is UB. Plain `extern "C" { ... }` is an
  error:

```text
error: extern blocks must be unsafe
 --> compile_fail/extern_block_not_unsafe_2024.rs:2:1
  |
2 |   extern "C" {
  |   ^
  |   |
  |  _help: needs `unsafe` before the extern keyword: `unsafe`
```

- Inside an `unsafe extern` block, an item can be marked **`safe fn`** when
  you know **every** call is sound, or left plain (call needs `unsafe`).
  `abs` takes a number and cannot misbehave. `strlen` reads through a
  pointer, so it stays unsafe.
- Use the **C types** from `std::ffi` (`c_int`, `c_char`, `c_void`, ...). A C
  `int` is **not** always `i32` on every platform. `c_int` is right
  everywhere.
- `strlen` returns **6** for `"héllo"` because it counts **bytes** up to the
  zero byte, and `é` is 2 bytes in UTF-8.
- `libc` (the crate) has ready-made declarations for the whole C library, so
  in real projects you rarely write these by hand.

## 2. "How do I pass strings across the boundary?"

```rust
let name = CString::new("HOME").unwrap();
let home = unsafe { getenv(name.as_ptr()) };      // *const c_char, may be NULL
if !home.is_null() {
    let len = unsafe { CStr::from_ptr(home) }.to_bytes().len();
}
```

**Answer:**

- A **C string** is a pointer to bytes ending in a **zero byte** (NUL), with
  **no length** stored. A Rust `&str` is the opposite: **length stored, no
  terminator, may contain zero bytes**. They are not the same thing.
- **`CString`** (owned) and **`CStr`** (borrowed) are the bridge:
    - `CString::new("text")` copies and adds the NUL. It **fails** if the
      text contains an interior zero byte (the `Result` tells you).
    - `.as_ptr()` gives a `*const c_char` for C. The pointer is valid
      **only while the `CString` lives**. A classic bug is
      `CString::new(s).unwrap().as_ptr()`: the temporary dies at the end of the
      statement and the pointer **dangles**. Keep the `CString` in a variable.
    - `CStr::from_ptr(p)` wraps a C string you were handed. It is `unsafe`
      (the pointer must be valid and NUL-terminated). Then
      `.to_str()` (checks UTF-8) or `.to_string_lossy()`.
- C strings are **not** guaranteed to be UTF-8. Never assume it for text
  from C, file names, or the environment. See
  [Collections & Strings](../foundations/rust-collections-and-strings.md).

## 3. "How do I expose Rust to C?"

```rust
#[unsafe(no_mangle)]
pub extern "C" fn demo_add(a: c_int, b: c_int) -> c_int {
    a.wrapping_add(b)
}
```

```c
int demo_add(int a, int b);                       /* in the C file */
printf("demo_add(2, 3) = %d\n", demo_add(2, 3));
```

```text
demo_add(2, 3) = 5
```

**Answer:**

- **`extern "C"`** makes the function use the C calling convention.
- **`#[unsafe(no_mangle)]`** keeps the symbol name exactly `demo_add`.
  Without it Rust **mangles** names (adds crate and type information) and C
  cannot find it. In edition 2024 the attribute **must** be written inside
  `unsafe(...)`, because a name clash with another symbol can break the
  program:

```text
error: unsafe attribute used without unsafe
 --> compile_fail/no_mangle_unsafe_attr_2024.rs:2:3
  |
2 | #[no_mangle]
  |   ^^^^^^^^^ usage of unsafe attribute
  |
help: wrap the attribute in `unsafe(...)`
```

- The **library must be built for C**. In `Cargo.toml`:

```toml
[lib]
crate-type = ["cdylib", "staticlib", "rlib"]
```

- `cdylib`: a **dynamic** library (`.so` on Linux, `.dylib` on macOS,
  `.dll` on Windows). `staticlib`: a **static** archive (`.a`) that the C
  linker copies into its program. `rlib`: the normal Rust library format, so
  Rust code and tests can still use the crate.
- Compile the C file against the Rust library with `build.sh`:

```bash
cargo build --release --lib
cc demo.c target/release/libffi_demo.a -o demo_static             # static
cc demo.c -Ltarget/release -lffi_demo -o demo_dynamic             # dynamic
```

- Only use **FFI-safe types** in the signature: integers, floats, raw
  pointers, `#[repr(C)]` structs, `Option<&T>`/`Option<Box<T>>`/`Option<extern fn>`
  (null is `None`, see
  [Memory Layout §6](rust-memory-layout-and-dsts.md#6-what-is-niche-optimization-and-why-is-optionboxt-free)).
  A `String`, `Vec` or `&str` has **no C layout**, and the compiler warns:

```text
warning: `extern` fn uses type `String`, which is not FFI-safe
 --> compile_fail/extern_c_returns_string.rs:3:29
  |
3 | pub extern "C" fn name() -> String {
  |                             ^^^^^^ not FFI-safe
  |
  = help: consider adding a `#[repr(C)]` or `#[repr(transparent)]` attribute to this struct
  = note: this struct has unspecified layout
  = note: `#[warn(improper_ctypes_definitions)]` on by default
```

## 4. "How do I share a struct, and who owns what?"

```rust
#[repr(C)]
pub struct Point { pub x: f64, pub y: f64 }

#[unsafe(no_mangle)]
pub extern "C" fn demo_distance(p: *const Point, q: *const Point, out: *mut f64) -> c_int {
    if p.is_null() || q.is_null() || out.is_null() {
        return -1;                       // error code instead of a panic
    }
    unsafe {
        let (p, q) = (&*p, &*q);
        *out = ((p.x - q.x).powi(2) + (p.y - q.y).powi(2)).sqrt();
    }
    0
}
```

```text
demo_distance -> rc=0 distance=5.0
demo_distance(NULL) -> rc=-1
```

**Answer:**

- **`#[repr(C)]`** gives the struct the same layout a C compiler would use.
  Without it the layout is unspecified and C would read garbage. See
  [Memory Layout §3](rust-memory-layout-and-dsts.md#3-why-is-a-struct-sometimes-smaller-than-the-sum-of-its-fields-in-c-order).
  C declares the matching `typedef struct { double x; double y; } Point;`.
- **Errors**: C has no `Result` and no exceptions. The usual conventions are
  a **return code** (`0` ok, negative error) with the **real result in an
  out-parameter** (`*mut f64`), or returning `NULL` on failure. Document
  which. A Rust `Result` cannot cross the border.
- **Null**: a raw pointer may be null. Check it first. A `&T` or `&mut T`
  parameter would **promise** non-null, so a C caller passing `NULL` is UB.
  Use raw pointers at the boundary, then convert after checking.
- **The central rule: whoever allocates must free.** Rust's allocator and
  C's `malloc` are **different**. Freeing a Rust `Box` with C's `free`, or a
  `malloc`ed block with Rust's `drop`, is **UB**.

## 5. "How do I give C an object it can hold but not look inside?"

```rust
pub struct Counter { count: u64 }

#[unsafe(no_mangle)]
pub extern "C" fn demo_counter_new() -> *mut Counter {
    Box::into_raw(Box::new(Counter { count: 0 }))
}

#[unsafe(no_mangle)]
pub extern "C" fn demo_counter_incr(c: *mut Counter) -> u64 {
    let c = unsafe { c.as_mut() }.expect("null counter");
    c.count += 1;
    c.count
}

/// # Safety
/// `c` must come from `demo_counter_new` and must not be used afterwards.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn demo_counter_free(c: *mut Counter) {
    if !c.is_null() {
        drop(unsafe { Box::from_raw(c) });
    }
}
```

```c
typedef struct Counter Counter;            /* opaque: no fields declared */
Counter *c = demo_counter_new();
demo_counter_incr(c);
printf("counter = %llu\n", (unsigned long long)demo_counter_incr(c));
demo_counter_free(c);
```

```text
counter = 2
```

**Answer:**

- This is the **opaque handle** pattern, the most common safe-ish FFI
  design. C only sees `Counter *`. It cannot read or write fields, so Rust is
  free to change the struct without breaking C.
- **`Box::into_raw`** gives up Rust's ownership and returns a raw pointer
  (the box is **not** dropped). **`Box::from_raw`** takes it back, so
  dropping the box frees the memory **with the right allocator**.
- You **must** provide the matching `*_free` function. Without it, C can
  only leak.
- Same idea for strings. `CString::into_raw` hands C an owned string; the
  **only** correct way to free it is `CString::from_raw` back in Rust
  (`demo_string_free`). C must never call `free` on it:

```c
char *greeting = demo_greet("C");
printf("%s\n", greeting);        /* Hello, C! */
demo_string_free(greeting);      /* freed by RUST, because Rust allocated it */
```

- **Double free** and **use after free** become C's responsibility. Say in
  the header comment: "call free exactly once, do not use after".
- Never hand C a pointer **into** a Rust `Vec` or `String` buffer that may
  later reallocate, unless the contract says it is valid only during the call.
- **Threads**: if C may call from many threads, the type behind the pointer
  must be `Send`/`Sync`, and you must synchronize inside (`Mutex`).

## 6. "How does C call back into Rust?"

```rust
pub type Visitor = extern "C" fn(value: c_int, user: *mut std::ffi::c_void);

#[unsafe(no_mangle)]
pub extern "C" fn demo_for_each(values: *const c_int, len: usize, visit: Visitor, user: *mut c_void) {
    let slice = unsafe { std::slice::from_raw_parts(values, len) };
    for &v in slice {
        visit(v, user);
    }
}
```

```c
static void sum_visitor(int value, void *user) { *(int *)user += value; }
int total = 0;
demo_for_each(values, 4, sum_visitor, &total);
```

```text
callback sum = 10
```

**Answer:**

- A C callback is a plain **function pointer**. In Rust it is
  `extern "C" fn(...)`. A Rust **closure** cannot be passed directly, because
  it has captured data and C has no place to put it.
- The C idiom is a **`void *user` pointer** that is passed back to the
  callback. Put a pointer to your state there, and cast it back inside the
  callback. This is exactly what the `qsort`-style APIs do.
- The first example in this page does the reverse: Rust passes
  `extern "C" fn compare_ints` to libc's `qsort`:

```text
qsort -> [1, 3, 5, 7, 9]
```

- Lifetime rule: the `user` pointer must stay valid for as long as C may call
  back. Documenting "only during this call" is the safest contract.

## 7. "What happens if Rust panics inside an `extern "C"` function?"

```rust
#[unsafe(no_mangle)]
pub extern "C" fn demo_panics() {
    panic!("boom");
}
```

```text
calling demo_panics()...

thread '<unnamed>' panicked at src/lib.rs:99:5:
boom

thread '<unnamed>' panicked at /rustc/.../library/core/src/panicking.rs:225:5:
panic in a function that cannot unwind
stack backtrace:
thread caused non-unwinding panic. aborting.
```

The process exit code was **134** (abort signal).

**Answer:**

- **Unwinding** (the panic machinery that runs destructors as it climbs the
  stack) **into C code is undefined behaviour**: C frames have no unwind
  information that Rust understands. So Rust makes an `extern "C"` function
  **abort the process** when a panic would escape. Safe, but fatal.
- To **recover**, catch the panic yourself and turn it into an error code:

```rust
pub extern "C" fn demo_checked_divide(a: c_int, b: c_int, out: *mut c_int) -> c_int {
    let result = std::panic::catch_unwind(|| a / b);    // panics when b == 0
    match result {
        Ok(v) if !out.is_null() => { unsafe { *out = v }; 0 }
        Ok(_) => -1,
        Err(_) => -2,
    }
}
```

```text
checked_divide(10, 2) -> rc=0 out=5
checked_divide(1, 0) -> rc=-2
```

- The panic **message still prints** to stderr (the line "attempt to divide
  by zero"); only the unwinding is stopped. `catch_unwind` needs the closure
  to be `UnwindSafe` and does not catch an abort (`panic = "abort"` builds
  skip unwinding entirely).
- **`extern "C-unwind"`** is the opposite choice: it **allows** a panic to
  unwind through the boundary, for the case where the **other side is also
  unwind-aware** (C++ with exceptions, or Rust-to-Rust through C). It compiled
  on 1.99 (not exercised against C++ here). Do not use it for plain C.
- Rule for any boundary function: **no panic may escape**. Check inputs, use
  `catch_unwind` at the edge, return codes for errors.

## 8. "Can Rust define a C-variadic function, like `printf`?"

```rust
#[unsafe(no_mangle)]
pub unsafe extern "C" fn demo_sum(n: c_int, mut args: ...) -> c_int {
    let mut total: c_int = 0;
    for _ in 0..n {
        total = total.wrapping_add(unsafe { args.next_arg::<c_int>() });
    }
    total
}
```

```text
demo_sum(3, 10, 20, 30) = 60
```

**Answer:**

- A **variadic** function takes a variable number of arguments (`...`).
  Rust has long been able to **declare and call** them (`printf` in an
  `extern` block). **Defining** one in Rust became stable in **1.99**
  (release notes: "Stabilize C-variadic function definitions").
- The extra arguments are read **one by one** with `args.next_arg::<T>()`.
  The method name is `next_arg` (confirmed against the standard library docs
  for `VaList`).
- It is **unsafe by nature**: C does not tell you how many arguments there are
  or what types. Wrong count or type is UB. Here the count is the first
  parameter `n`. Variadics are rare; prefer a normal signature with an array
  and a length.

## 9. "Do I write the C declarations by hand?"

**Answer:**

- For small APIs, yes. For large ones, **generate** them:
    - **`bindgen`**: reads C headers and generates Rust `extern` declarations
      and `#[repr(C)]` structs (**C to Rust**). Used in a `build.rs`.
    - **`cbindgen`**: reads your Rust `extern "C"` items and generates a C or C++
      header (**Rust to C**). This keeps `demo.c`'s declarations from drifting
      away from the real code.
    - **`cc`** crate: compiles a C file in `build.rs` and links it into your
      Rust crate.
- **Linking** a system library from `build.rs`:

```rust
// build.rs
fn main() {
    println!("cargo::rustc-link-lib=z");           // link libz
    println!("cargo::rustc-link-search=/opt/lib"); // extra search path
}
```

- Also set `links = "z"` in `Cargo.toml` when you wrap a native library
  (it makes Cargo ensure only one crate links it). The `-sys` crate
  convention: `foo-sys` holds the raw `unsafe extern` bindings, and `foo`
  is the safe wrapper.
- A **build script** runs arbitrary code at build time, which is a
  supply-chain risk. See
  [CI/CD & Supply Chain](../production/rust-ci-cd-and-supply-chain.md).

## 10. "How do Python, Node and mobile apps call Rust?"

**Answer:**

- All of them load a **C-ABI library**. Higher-level crates generate the
  glue so you do not write the `extern "C"` layer yourself:

| Target language | Tool | What it does |
|---|---|---|
| Python | **PyO3** + **maturin** | Write Rust functions and classes, `maturin develop` builds a Python module (`import mymodule`). Handles the GIL and type conversion. |
| Node.js | **napi-rs** | Builds a native Node addon through Node-API. |
| Kotlin, Swift, Python | **uniffi** | Describe the API once (Rust attributes or a UDL file), get typed bindings for several languages. |
| C and C++ | **cbindgen** | Generates a header from your `extern "C"` items. |
| Go (via cgo) | the C ABI directly | Go calls your `cdylib`/`staticlib` as C. |

- A strong reason to use Rust here is **speed with memory safety** inside a
  Python or Node app: rewrite a hot function, keep the rest. For the Python
  side see [Python's Execution Model](../../python/language-fundamentals/pythons-execution-model.md).
- These tools were **not run** for this page. Read each project's guide,
  and check its current version, before you depend on it.
- Even with a generator, the same questions apply: **who frees what**,
  **panics**, **threads** (Python's GIL, Node's event loop), and
  **error mapping** (a Rust `Result` becomes an exception).

## 11. "How do I test an FFI boundary?"

**Answer:**

- **From C**: the `demo.c` and `build.sh` in the sample. Add the build to
  CI so a header that drifts from the code fails the build.
- **From Rust**: call your own `extern "C"` functions in unit tests. Because
  the `rlib` crate type is enabled, `ffi_demo::demo_add(2, 3)` works as a
  normal function call (the last line of the Rust demo does exactly this).
- **Miri** runs Rust code that uses raw pointers and `Box::into_raw` /
  `from_raw` correctly, and catches leaks, double frees and dangling
  pointers **inside Rust**. It **cannot execute C code**, so for the C side
  use **AddressSanitizer** (`-fsanitize=address`) and Valgrind. See
  [Unsafe Rust & Miri §8](rust-unsafe-and-miri.md#8-how-do-i-find-undefined-behaviour-show-me-miri).
- **Fuzz** the boundary with random bytes and lengths. Null pointers, zero
  lengths and huge lengths are the usual crashes.

## 12. "What are the common FFI mistakes?"

**Answer:**

- **Dangling `CString` pointer** (the temporary dies, §2).
- **Mixed allocators**: freeing Rust memory with `free` or the reverse (§4, §5).
- **Using `&T` / `&mut T` / `bool` / enums in the signature** where C may
  pass null, a non-0/1 byte, or an unknown value. All of those are UB for
  the Rust type. Use raw pointers, `u8`, or `c_int` at the boundary and
  **convert after validating**.
- **Panic crossing the boundary** (§7).
- **Forgetting `#[repr(C)]`** on a shared struct or enum (use
  `#[repr(C)]` or `#[repr(u8)]`-style enums).
- **Assuming `usize` = `unsigned long`**, or `int` = `i32`. Use `c_int`,
  `c_long`, `size_t` as `usize`, and read the platform notes.
- **Calling into a non-thread-safe library** from several threads.
- **A header that drifted** from the Rust code. Generate it with `cbindgen`.

## 13. "How do AI tools help or hurt here?"

**Answer:**

- **Good at**: writing the `extern` block for a C function if you paste the
  prototype, drafting a `bindgen` `build.rs`, and the `PyO3` module
  boilerplate.
- **Bad at**: **ownership across the boundary**. Generated code often frees
  with the wrong allocator, forgets the `*_free` function, or returns a pointer
  to a temporary. It also tends to use old syntax (`extern "C" {` and
  `#[no_mangle]`) that fails in edition 2024. Compile to see.
- Give it the header **and** the ownership rules in words ("the caller frees
  with `lib_free`"). Ask it to list, for every pointer, **who owns it and who
  frees it**. Check that list yourself.
- Always run the C side under a sanitizer.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 14. Interview Questions You're Likely to Get Asked

**Basics**

- "How do you call a C function from Rust, and what changed in edition
  2024?" — expects `unsafe extern "C"`, `safe fn`, C types,
  [§1](#1-how-does-rust-call-a-c-function).
- "How do you make a Rust function callable from C?" — expects
  `extern "C"`, `#[unsafe(no_mangle)]`, `crate-type`,
  [§3](#3-how-do-i-expose-rust-to-c).
- "`CString` vs `CStr` vs `&str`?" — expects NUL-terminated vs length-prefixed,
  and the dangling-temporary trap,
  [§2](#2-how-do-i-pass-strings-across-the-boundary).

**Depth**

- "Who frees memory that crosses the boundary?" — expects the allocator that
  made it; `into_raw`/`from_raw`; provide a `*_free`,
  [§5](#5-how-do-i-give-c-an-object-it-can-hold-but-not-look-inside).
- "What happens if a Rust panic reaches C?" — expects abort for `extern "C"`,
  `catch_unwind`, and `C-unwind`,
  [§7](#7-what-happens-if-rust-panics-inside-an-extern-c-function).
- "Why not use `&T` or `bool` in an FFI signature?" — expects null and invalid
  values are UB for those types,
  [§12](#12-what-are-the-common-ffi-mistakes).
- "How do you pass a callback with state?" — expects function pointer plus
  `void *user`,
  [§6](#6-how-does-c-call-back-into-rust).

**Design**

- "How would you expose a Rust library to Python and Node?" — expects PyO3 and
  maturin, napi-rs, or a C ABI with `cbindgen`; error and thread mapping,
  [§10](#10-how-do-python-node-and-mobile-apps-call-rust).
- "How do you test the C side of an FFI boundary?" — expects a C test in CI,
  sanitizers, since Miri cannot run C,
  [§11](#11-how-do-i-test-an-ffi-boundary).

---

## Code Samples

All files are in `code_samples/rust/ffi_demo/` (its own package, so it does not
change the main samples crate) and were built and run on Rust 1.99.1.

- `src/lib.rs` — the C-callable library: `demo_add`, `#[repr(C)] Point`,
  strings (`demo_greet`, `demo_string_free`), an opaque `Counter`, a callback,
  a panic that aborts, `catch_unwind`, and a C-variadic `demo_sum`.
- `src/main.rs` — Rust calling libc (`abs`, `strlen`, `qsort`, `getenv`)
  through `unsafe extern "C"`.
- `demo.c` and `build.sh` — a C program that uses the library, built and run
  both statically and dynamically.
- `../compile_fail/extern_block_not_unsafe_2024.rs`,
  `no_mangle_unsafe_attr_2024.rs`, `extern_c_returns_string.rs` — the three
  diagnostics quoted above.

```bash
cd code_samples/rust/ffi_demo
cargo run                      # Rust calling C
sh build.sh                    # C calling Rust, static and dynamic
# to see the abort, after build.sh:  target/release/demo_static panic
```
