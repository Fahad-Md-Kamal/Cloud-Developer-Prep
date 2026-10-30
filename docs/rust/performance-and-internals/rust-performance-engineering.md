---
title: Rust Performance Engineering — Measuring, Profiling, Allocation, Cache, SIMD, and Release Tuning
---

# Rust Performance Engineering

Rust gives you the **tools** for fast programs (no garbage collector,
control over memory layout, an optimizer that removes abstraction cost),
but it does **not** make a slow design fast. Performance work is a loop:
**measure, find the one thing that costs most, change it, measure again**.
This page teaches the loop first, then the usual causes of slow Rust, then
the build settings.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Every number below
    was measured on one machine: an Apple-silicon Mac (aarch64, macOS),
    release builds, Rust 1.99.1. **Your numbers will differ.** The
    *ratios* and the *method* are what to take away. `core::hint::cold_path`
    (stable 1.95) and `hint::select_unpredictable` (stable 1.88) were
    compiled and run. `std::simd` (portable SIMD) is **still unstable** on
    1.99; the real error is quoted in §8.

## 1. "Why must you measure first, and what must you never measure?"

**Answer:**

- **Guessing is wrong most of the time.** The slow part of a program is
  rarely the part that looks slow. Measure, then change one thing.
- **Never benchmark a debug build.** The `dev` profile has `opt-level = 0`
  and is often 10 to 100 times slower. See
  [Toolchain & Cargo §4](../foundations/rust-toolchain-and-cargo.md#4-what-are-profiles-and-what-do-dev-and-release-really-change).
    - Use `cargo run --release` or `cargo bench`.
- **Stop the optimizer from deleting your test.** If the result is unused,
  the compiler may remove the work. Wrap inputs and outputs in
  `std::hint::black_box`, which hides a value from the optimizer.
- **Warm up, repeat, and take the median.** The first run pays for cold
  caches and page faults. One run proves nothing.
- **Measure the real workload size.** An algorithm that wins on 10 items can
  lose on 10 million, and the other way round.
- **Keep debug symbols in release profiling builds** so a profiler can show
  function names:

```toml
[profile.release]
debug = 1        # line tables only: no speed cost, big help for profilers
```

## 2. "How do you benchmark Rust code?"

**Answer:**

- **Hand-rolled timing** is fine for a first look (the sample uses
  `Instant`, `black_box`, a warm-up call, and many repeats).
- **Use a benchmark harness** for decisions: it handles warm-up, outlier
  noise, and statistics.
    - **`divan`**: simple attribute API, prints a tree. Used in the sample.
    - **`criterion`**: the long-standing choice, with HTML reports and
      comparison against a saved baseline.
- The built-in `#[bench]` attribute is **not usable on stable** (it was
  fully de-stabilized in 1.88). Use one of the crates above.
- `divan` example from the samples (`benches/divan_demo.rs`):

```rust
#[divan::bench]
fn fast(bencher: divan::Bencher) {
    let words = make_words(20_000, 500);
    bencher.bench(|| count_fast(divan::black_box(&words)));
}
```

- Real output on the author's machine:

```text
divan_demo         fastest       │ slowest       │ median        │ mean
├─ fast            286.1 µs      │ 573.3 µs      │ 320.8 µs      │ 331.7 µs
├─ slow            9.889 ms      │ 14.19 ms      │ 10.2 ms       │ 10.31 ms
├─ sum_iter_bench                │               │               │
│  ├─ 1000         56.28 ns      │ 57.91 ns      │ 56.93 ns      │ 56.98 ns
│  ╰─ 100000       7.082 µs      │ 8.582 µs      │ 7.207 µs      │ 7.24 µs
╰─ sum_loop_bench                │               │               │
   ├─ 1000         55.95 ns      │ 71.58 ns      │ 56.93 ns      │ 57.42 ns
   ╰─ 100000       6.249 µs      │ 14.99 µs      │ 7.207 µs      │ 7.254 µs
```

- Read it: `slow` vs `fast` is about **32x** at the median (§9 explains
  why). The index loop and `iter().sum()` are **the same speed** (§6).
- **Micro-benchmarks lie in one way:** they run with hot caches and a
  predictable branch pattern. Confirm a win in the real program too.

## 3. "How do you find where the time goes?"

**Answer:**

- A **profiler** samples the program many times per second and records the
  call stack. Functions that appear in many samples are where time goes.
- Tools by platform (the commands below were **not** run for this page;
  only the numbers in §2 and §5 to §9 were):

| Tool | Platform | Notes |
|---|---|---|
| `perf` | Linux | `perf record --call-graph dwarf ./target/release/app`, then `perf report` |
| `cargo flamegraph` | Linux, macOS | wraps `perf` or `dtrace`, writes an SVG flame graph |
| `samply` | Linux, macOS, Windows | opens the Firefox Profiler UI in the browser |
| Instruments (Time Profiler) | macOS | ships with Xcode |
| `dhat`, `heaptrack`, Instruments (Allocations) | varies | count and place **allocations** |

- **Flame graph:** the x-axis is the share of samples (width), the y-axis
  is call depth. A **wide box** is a function that is on the stack often.
- Profile the **release build with `debug = 1`** (§1), or names are missing
  and inlined code is hard to map back to source.
- **Count allocations separately.** The `dhat` crate can replace the global
  allocator in a test and report totals, so "this loop allocates once per
  item" becomes a number you can assert on.

## 4. "What does an allocation cost, and how do you avoid it?"

**Answer:**

- A heap allocation asks the allocator for memory. It costs time (find a
  free block, maybe lock, maybe ask the OS) and **hurts the cache**,
  because heap blocks are scattered.
- The fixes, in order of effort:
    - **`Vec::with_capacity`**: when you know the size, reserve it once.
      Without it, `Vec` grows by doubling and **copies** every time.
    - **Reuse buffers.** Keep one `String` or `Vec` outside a loop and
      call `.clear()` inside it. `clear` keeps the capacity.
    - **Borrow instead of clone.** A `HashMap<&str, _>` keyed by slices of
      data you already own does not copy a single string (§9).
    - **Avoid `collect` in the middle of a chain** when the next step can
      consume the iterator directly.
    - **Small-buffer types** (`smallvec`, `arrayvec`, `heapless`) keep a
      few items inline and only allocate when they overflow.
    - **Arena allocation** (`bumpalo`): allocate many objects from one
      region and free them together.
- Measured (1 million `u64` pushes):

```text
Vec::new + push                        1479.6 us
Vec::with_capacity + push               561.0 us      (2.64x faster)
```

- See also
  [Collections & Strings §7](../foundations/rust-collections-and-strings.md#7-what-makes-collection-code-fast-or-slow).
- **Do not add a faster allocator first.** Swapping the global allocator
  (`mimalloc`, `jemalloc`) can help allocation-heavy servers, but it hides
  the design problem. Measure before and after.

## 5. "Why does data layout matter for speed?"

**Answer:**

- The CPU reads memory in **cache lines** (commonly 64 bytes). Reading one
  byte pulls in its whole line. A program is fast when the bytes it needs
  next are **already in the same line**: this is **cache locality**.
- **Array of structs (AoS)** stores whole records one after another.
  **Struct of arrays (SoA)** stores each field in its own array.
    - Summing one field: AoS loads the other fields too and wastes cache.
      SoA reads only the bytes it needs.
- Measured (summing `x` over 100 000 particles; each `Particle` is **72
  bytes**):

```text
AoS: sum p.x                             61.4 us
SoA: sum x[]                             48.8 us      (1.26x faster)
```

- The gap is modest here because the data is small and one pass is cheap.
  It grows when the struct is bigger, the data does not fit in the cache,
  or several passes touch only a few fields.
- **Small collections:** for 8 keys, a `Vec` linear scan and a `HashMap`
  lookup are close in cost, and the `Vec` can win because there is no
  hashing. In the sample, 1000 lookups took 1.2 us in the `Vec` and 3.2 us
  in the `HashMap` (the default `HashMap` hasher, SipHash, is built to
  resist attacks, not to be fastest). Past a few dozen keys the `HashMap`
  wins. **Measure with your real sizes.**
- Layout rules (field order, padding, niches) are in
  [Memory Layout & DSTs](../advanced-language/rust-memory-layout-and-dsts.md).
  Smaller types (a `u32` index instead of a pointer) mean more items per
  cache line.

## 6. "Are iterators really as fast as loops?"

**Answer:**

- **Yes, for ordinary code.** Iterator chains are generic, so the compiler
  **monomorphizes** them (makes a copy for the exact types) and inlines the
  closures. The result is the same machine code as a hand-written loop.
  See
  [Iterators & Closures §5](../foundations/rust-iterators-and-closures.md#5-why-is-this-zero-cost-and-when-is-it-not).
- Measured (sum 1 million `u64`):

```text
index loop                               85.9 us
iter().sum()                             77.5 us
```

- **Bounds checks.** `v[i]` checks `i < v.len()` and panics if not. In a
  `for i in 0..v.len()` loop the compiler can usually prove the check is
  unnecessary and remove it. When it cannot, three fixes:
    - **Use iterators** (`iter`, `zip`, `chunks_exact`): no index, no check.
    - **Assert once** before the loop (`assert_eq!(a.len(), b.len());`,
      as in `dot` in `hints_and_simd.rs`) so the optimizer knows the
      lengths match.
    - **Slice first** (`let a = &a[..n];`) for the same reason.
- **`get_unchecked` is a last resort.** It is `unsafe`, and a wrong index
  is undefined behaviour. Prefer the three fixes above.
- **Where iterators are not free:** `collect` into a `Vec` allocates;
  `Box<dyn Iterator>` costs a virtual call per item; very long chains can
  slow compilation.

## 7. "What do `#[inline]`, `#[cold]`, and `cold_path` do?"

**Answer:**

- **`#[inline]`** is a hint to copy a function's body into the caller.
    - Inlining is automatic **inside one crate**. Across crates, only
      `#[inline]` functions and generic functions have their bodies
      visible. Put `#[inline]` on small, hot, non-generic library functions.
    - `#[inline(always)]` forces it, `#[inline(never)]` forbids it (useful
      to see a function in a profile or to limit code size).
    - **More inlining is not always faster**: it grows the code, which
      can overflow the instruction cache.
- **`#[cold]`** marks a function as rarely called, so the optimizer moves
  it away from the hot path.
- **`core::hint::cold_path()`** (stable 1.95) marks a **branch** as rare,
  inside a function:

```rust
use std::hint::cold_path;

fn parse(s: &str) -> u32 {
    match s.parse::<u32>() {
        Ok(n) => n,
        Err(_) => {
            cold_path(); // the error path is rare
            0
        }
    }
}
```

- **`hint::select_unpredictable(cond, a, b)`** (stable 1.88) asks for a
  branch-free select (a conditional move) when the branch cannot be
  predicted by the CPU, for example comparing random data.
  `clamp_branchless` in the sample uses it.
- These are **hints**: the compiler may ignore them, and none changes the
  program's result. Output of `hints_and_simd`:

```text
parse: 42 0
clamp: 0 5 10
dot: 32
```

## 8. "How do you use SIMD in Rust?"

**Answer:**

- **SIMD (Single Instruction, Multiple Data)** means one CPU instruction
  works on several values at once (for example four `f32`s).
- Three routes, from easiest to most manual:
    - **Auto-vectorization.** Write a simple loop over slices with no
      early exit and the optimizer often emits SIMD itself. The
      `iter().sum()` on integers above is likely vectorized. Check with
      `--emit=asm` (see
      [How rustc Works §9](rustc-how-the-compiler-works.md#9-how-do-you-look-at-what-the-compiler-produced)).
    - **`std::arch` intrinsics** (stable): functions per CPU family, such
      as `std::arch::aarch64::vaddq_f32` or `std::arch::x86_64::_mm256_add_ps`.
      They are `unsafe`, and code that needs a feature the CPU may lack
      must be guarded with run-time detection (`is_x86_feature_detected!`)
      or compile-time `-C target-feature`. NEON is part of the aarch64
      baseline, so the sample can use it directly (`add4_neon`, which
      printed `[11.0, 22.0, 33.0, 44.0]`).
    - **`std::simd` (portable SIMD)**: one API for all CPUs. **Still
      unstable on 1.99.** On stable:

```text
error[E0658]: use of unstable library feature `portable_simd`
 --> compile_fail/portable_simd_fails.rs:3:5
  |
3 | use std::simd::f32x4;
  |     ^^^^^^^^^^^^^^^^
  |
  = note: see issue #86656 <https://github.com/rust-lang/rust/issues/86656> for more information
```

    - Crates such as `wide` give a portable, stable SIMD API today.
- **Safe functions with `#[target_feature]`** (stable since 1.86) let
  you write a safe function that is compiled for a feature, and the
  compiler enforces that callers have checked the feature.
- Floating-point sums are **not** auto-vectorized the same way as integer
  sums, because adding floats in a different order changes the result. The
  `f32` sums in §5 run sequentially. Write the chunked version by hand
  (accumulate into several lanes) if you need the speed.

## 9. "Make this slow program ten times faster. How?"

**Answer:**

- The task: count how often each word appears in 200 000 words (500
  distinct). The first version is the one many people write on day one:

```rust
pub fn count_slow(words: &[String]) -> Vec<(String, usize)> {
    let mut counts: Vec<(String, usize)> = Vec::new();
    for w in words {
        let key = w.clone();                                   // allocation per word
        match counts.iter_mut().find(|(k, _)| *k == key) {     // scan up to 500 entries
            Some((_, n)) => *n += 1,
            None => counts.push((key, 1)),
        }
    }
    counts.sort();
    counts
}
```

- **Two costs a profiler would show:** a `String` clone (one allocation)
  per word, and a linear search (up to 500 comparisons) per word. That is
  O(n x d) work, where n is the word count and d the distinct count.
- The fix removes both:

```rust
pub fn count_fast(words: &[String]) -> Vec<(&str, usize)> {
    let mut counts: HashMap<&str, usize> = HashMap::with_capacity(1024);
    for w in words {
        *counts.entry(w.as_str()).or_insert(0) += 1;           // borrows, no clone
    }
    let mut v: Vec<_> = counts.into_iter().collect();
    v.sort_unstable();                                         // sort once, at the end
    v
}
```

- Measured (200 000 words, release):

```text
count_slow                           105966.5 us
count_fast                             2384.5 us
   speed-up 44x
```

- What changed, in order of impact:
    - **Algorithm:** linear search to hash lookup (the big one).
    - **Allocation:** no clone per word, and the map is pre-sized.
    - **Sorting:** `sort_unstable` is faster than `sort` when equal
      elements need no stable order (here every key is unique anyway).
- **The order of work matters.** Fix the algorithm, then allocation, then
  layout, then micro-details. Reaching for SIMD before removing an O(n x d)
  scan is wasted effort.

## 10. "Which release-profile settings change performance?"

**Answer:**

- These are Cargo profile keys. Each is a trade-off between **run speed**,
  **binary size**, and **compile time**:

| Setting | Effect | Cost |
|---|---|---|
| `opt-level = 3` (release default) | most optimization | longer compile |
| `opt-level = "s"` / `"z"` | smaller binary (`z` smallest) | usually slower code |
| `lto = "thin"` / `true` | optimize across crates (**Link-Time Optimization**) | slower link; often 5 to 20 percent faster and smaller |
| `codegen-units = 1` | one unit, better inlining and optimization | no parallel codegen, slower build |
| `panic = "abort"` | no unwinding tables, smaller code | a panic ends the process; no `catch_unwind` |
| `strip = true` | removes symbols | no names in backtraces and profilers |
| `-C target-cpu=native` | uses every feature of **this** CPU | binary may crash on other CPUs |
| **PGO** (Profile-Guided Optimization) | compiler uses a recorded real run to lay out code | extra build steps; `cargo-pgo` helps |

- A common production profile:

```toml
[profile.release]
lto = "fat"
codegen-units = 1
panic = "abort"
```

- **Always measure these on your program.** The size effect is easy to
  see; the speed effect depends on the code. In the WebAssembly sample
  (see [Rust & WebAssembly §6](rust-webassembly.md#6-how-do-you-make-a-webassembly-file-small)),
  `opt-level = 3` gave 15 006 bytes and `"s"` or `"z"` gave 13 873.
- **Linker speed:** since **1.90** the default linker on
  `x86_64-unknown-linux-gnu` is `lld`, which is faster than the system
  linker. Other platforms can opt in, or use `mold`.
- Compile time is its own topic:
  [How rustc Works §8](rustc-how-the-compiler-works.md#8-why-are-rust-builds-slow-and-how-do-you-speed-them-up).

## 11. "How do AI tools help or hurt here?"

**Answer:**

- **Help:**
    - Ask for the **benchmark harness**, not the optimization: "write a
      `divan` benchmark for this function with inputs of 1k and 1M items."
    - Ask it to **explain a flame graph** or a hot function you paste, and
      to list candidate causes (allocation, clone, locking, cache misses).
    - Ask for the `--emit=asm` output to be **read** for you ("is this loop
      vectorized?"), then check the claim yourself.
- **Hurt:**
    - An AI will confidently say "this is faster" with **no measurement**.
      Treat every speed claim as a hypothesis until a benchmark in release
      mode agrees.
    - It tends to add `unsafe`, `get_unchecked`, `#[inline(always)]`, or a
      different allocator **before** any profile. Reject the change unless
      it shows a number.
    - Benchmarks it writes often forget `black_box`, so the compiler
      removes the work and the result is meaningless.
- In an interview where an AI assistant is available, **state your
  method out loud** (measure, profile, fix the biggest cost, re-measure).
  See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 12. Interview Questions You're Likely to Get Asked

**Method**

- "A Rust service is slow. What do you do first?" — expects: reproduce with
  a release build, profile (flame graph), find the widest function, change
  one thing, re-measure, [§1](#1-why-must-you-measure-first-and-what-must-you-never-measure),
  [§3](#3-how-do-you-find-where-the-time-goes).
- "Why does a benchmark need `black_box`?" — expects: otherwise the
  optimizer may remove unused work, [§1](#1-why-must-you-measure-first-and-what-must-you-never-measure).

**Memory and layout**

- "Why is `Vec::with_capacity` faster?" — expects: avoids repeated growth
  and copying, [§4](#4-what-does-an-allocation-cost-and-how-do-you-avoid-it).
- "AoS or SoA, and when?" — expects: SoA when a pass touches few fields of
  many items, cache lines, [§5](#5-why-does-data-layout-matter-for-speed).
- "When is a `Vec` faster than a `HashMap`?" — expects: small sizes, no
  hashing, contiguous memory, [§5](#5-why-does-data-layout-matter-for-speed).

**Code generation**

- "Is `iter().map().sum()` slower than a `for` loop?" — expects: no,
  monomorphization and inlining, [§6](#6-are-iterators-really-as-fast-as-loops).
- "How do you remove bounds checks safely?" — expects: iterators, one assert
  before the loop, slicing first, [§6](#6-are-iterators-really-as-fast-as-loops).
- "What does `lto` do, and what does it cost?" — expects: cross-crate
  optimization, slower link, [§10](#10-which-release-profile-settings-change-performance).
- "How would you use SIMD on stable Rust?" — expects: auto-vectorization,
  `std::arch`, crates like `wide`; `std::simd` unstable,
  [§8](#8-how-do-you-use-simd-in-rust).

**Design**

- "Walk me through making a slow word counter 10x faster." — expects: find
  the clone and the linear scan, switch to a borrowed-key `HashMap`,
  measure each step, [§9](#9-make-this-slow-program-ten-times-faster-how).

---

## Code Samples

All files are in `code_samples/rust/perf_demo/` (its own package, so the
main samples crate gets no extra dependencies) and were run on Rust 1.99.1
on an aarch64 Mac.

- `src/lib.rs` — `count_slow` and `count_fast`, the loop and iterator sums,
  and a word generator.
- `examples/bench_demo.rs` — hand-rolled timing: `with_capacity`, loop vs
  iterator, AoS vs SoA, `Vec` vs `HashMap`, and the word-count speed-up.
- `examples/hints_and_simd.rs` — `cold_path`, `select_unpredictable`, the
  assert-before-loop pattern, and an aarch64 NEON add.
- `benches/divan_demo.rs` — the `divan` benchmarks quoted in §2.
- `compile_fail/portable_simd_fails.rs` — must fail: `std::simd` is unstable.

```bash
cd code_samples/rust/perf_demo
cargo run --release --example bench_demo
cargo run --release --example hints_and_simd
cargo bench
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/portable_simd_fails.rs
```
