---
title: Unsafe Rust and Miri
---

# Unsafe Rust and Miri

**`unsafe` is a promise, not a switch.** Safe Rust guarantees that no
program can cause undefined behaviour. `unsafe` marks the few places where
**you**, not the compiler, guarantee it. Inside an `unsafe` block the compiler
still checks types, lifetimes and borrows on safe operations. It only unlocks
five extra abilities (§1), and each carries a contract you must uphold.
**Miri** is an interpreter that runs your code and **detects** many broken
promises. This page teaches the contracts, how to wrap `unsafe` in a safe API,
and how to prove it with Miri, with the real error messages.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Samples ran on stable
    1.99.1. Miri runs came from `miri 0.1.0 (92ffebecea 2026-10-28)` on the
    nightly toolchain (`rustc 1.101.0-nightly`). Miri is **only on nightly**.
    Its messages change often, so expect small wording differences.
    Prerequisites: [Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md),
    [Smart Pointers](../foundations/rust-smart-pointers.md) and
    [Memory Layout](rust-memory-layout-and-dsts.md).

## 1. "What does `unsafe` actually allow?"

```text
error[E0133]: dereference of raw pointer is unsafe and requires unsafe block
 --> compile_fail/deref_raw_outside_unsafe.rs:5:20
  |
5 |     println!("{}", *p);
  |                    ^^ dereference of raw pointer
  |
  = note: raw pointers may be null, dangling or unaligned; they can violate aliasing rules and cause data races: all of these are undefined behavior
```

**Answer:**

- `unsafe` unlocks exactly **five** abilities:
    1. **Dereference a raw pointer** (`*const T`, `*mut T`).
    2. **Call an `unsafe` function** (including `extern` functions and
       compiler intrinsics).
    3. **Access or modify a `static mut`.**
    4. **Implement an `unsafe` trait** (`Send`, `Sync`, `GlobalAlloc`).
    5. **Read a field of a `union`.**
- It does **not** turn off the borrow checker, type checking, or bounds
  checks. `unsafe { v[10] }` on a short `Vec` still panics.
- Creating a raw pointer (`&x as *const i32`) is **safe**. Only using it is
  not.
- The five abilities are the only things that can introduce undefined
  behaviour. That is why you can **search a codebase for `unsafe`** and audit
  only those places.
- The goal is never "use `unsafe`". It is to put a **small `unsafe` core**
  behind a **safe API**, as `Vec`, `Rc` and `Mutex` do. See
  [§5](#5-how-do-i-build-a-safe-abstraction-over-unsafe-code).

## 2. "What is undefined behaviour, and why is it so bad?"

**Answer:**

- **Undefined behaviour (UB)** means the program has **no meaning**. The
  compiler assumes it never happens, so it can **delete checks and reorder
  code** based on that assumption. The result may be a crash, wrong output,
  a security hole, or something that works until the next compiler upgrade.
- It is not "a bad value". Even a **correct-looking run** can be UB, and a
  later optimization turns it into a bug.
- The list of things that are UB includes:
    - Reading or writing **freed, out-of-bounds, null, or dangling** memory.
    - A **data race** (two threads, one write, no synchronization).
    - **Misaligned** reads or writes through a pointer.
    - Producing an **invalid value**: a `bool` that is not 0 or 1, a `char`
      that is not a Unicode scalar value, a null `&T` or `Box<T>`, an invalid
      enum tag, a `&T` that dangles (even if never read).
    - Reading **uninitialized** memory as an integer or similar type.
    - Breaking the **aliasing rules**: a `&mut T` must be the only way to
      reach its data while it is live.
    - Calling a function through the **wrong ABI** or with the wrong
      signature, or unwinding out of an `extern "C"` function.
- Reference of record: the Rust Reference chapter "Behavior considered
  undefined".
- Because UB is about the **abstract machine**, not the CPU, **you cannot
  find it by testing on your machine**. That is the problem Miri solves
  (§8).

## 3. "What is the difference between an `unsafe` block, `unsafe fn` and `unsafe trait`?"

```rust
/// Returns the element at `index` without a bounds check.
///
/// # Safety
/// `index` must be less than `slice.len()`.
unsafe fn get_unchecked_demo<T>(slice: &[T], index: usize) -> &T {
    // SAFETY: the caller guarantees `index < slice.len()`.
    unsafe { &*slice.as_ptr().add(index) }
}
```

**Answer:**

- An **`unsafe` block** says: "I checked the contract of what is inside."
  Write a `// SAFETY:` comment saying **why** it holds.
- An **`unsafe fn`** says: "**my caller** must uphold a contract." Write it
  in a **`# Safety`** section of the doc comment. Calling it needs an
  `unsafe` block.
- An **`unsafe trait`** says: "**implementors** must uphold a contract
  that other code relies on" (`Send`, `Sync`). Implementing it needs
  `unsafe impl`.
- Rule: if a function **cannot** be misused from safe code, it must be a
  **safe** function that contains an `unsafe` block. Mark a function
  `unsafe` only when the **caller** can break it.
- Clippy has `clippy::undocumented_unsafe_blocks` and
  `clippy::missing_safety_doc` to enforce the comments. Turn them on in
  libraries.
- **Edition 2024 change**: the body of an `unsafe fn` is **no longer** an
  implicit `unsafe` block. The lint `unsafe_op_in_unsafe_fn` warns, so each
  unsafe operation needs its own block:

```text
warning[E0133]: dereference of raw pointer is unsafe and requires unsafe block
 --> compile_fail/unsafe_op_in_unsafe_fn_2024.rs:3:5
  |
3 |     *p
  |     ^^ dereference of raw pointer
  |
note: an unsafe function restricts its caller, but its body is safe by default
  = note: `#[warn(unsafe_op_in_unsafe_fn)]` (part of `#[warn(rust_2024_compatibility)]`) on by default
```

## 4. "What other things did edition 2024 make `unsafe`?"

```text
error[E0133]: call to unsafe function `set_var` is unsafe and requires unsafe block
 --> compile_fail/set_var_unsafe.rs:3:5
  |
3 |     std::env::set_var("DEMO", "1");
  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ call to unsafe function
```

**Answer:**

- **`std::env::set_var` and `remove_var` are `unsafe`.** Changing the
  environment while another thread reads it is a data race inside the C
  library. In edition 2021 the same code compiles with no error; in 2024
  it is rejected. Set variables **before** starting threads, or pass
  configuration explicitly.
- **References to a `static mut` are denied** (`static_mut_refs`). Use
  `&raw mut` and raw pointer access:

```text
error: creating a mutable reference to mutable static
 --> compile_fail/static_mut_ref_edition_2024.rs:5:17
  |
5 |         let r = &mut COUNTER;
  |                 ^^^^^^^^^^^^ mutable reference to mutable static
  |
help: use `&raw mut` instead to create a raw pointer
```

- **`extern` blocks must be written `unsafe extern`**, and attributes such as
  `no_mangle` become `#[unsafe(no_mangle)]`. See
  [FFI & C Interoperability](rust-ffi-and-c-interop.md).
- **Better than `static mut`**: use `AtomicU32`, `Mutex`, `OnceLock` or
  `thread_local!`. Almost every `static mut` has a safe replacement.
- **`&raw const` and `&raw mut`** create a raw pointer to a place **without
  first making a reference**. This matters for packed fields and for places
  that are not valid to reference:

```rust
let p = Packed { tag: 1, value: 0xCAFE };
let ptr = &raw const p.value;           // no reference, so no alignment promise
let v = unsafe { ptr.read_unaligned() };
```

```text
packed read via raw pointer: 0xcafe (tag 1)
static mut COUNTER = 1
```

## 5. "How do I build a safe abstraction over unsafe code?"

```rust
fn my_split_at_mut<T>(slice: &mut [T], mid: usize) -> (&mut [T], &mut [T]) {
    let len = slice.len();
    assert!(mid <= len, "mid out of range");
    let ptr = slice.as_mut_ptr();
    // SAFETY: `mid <= len`, the halves do not overlap, and both come from
    // the one exclusive borrow `slice`.
    unsafe {
        (std::slice::from_raw_parts_mut(ptr, mid),
         std::slice::from_raw_parts_mut(ptr.add(mid), len - mid))
    }
}
```

```text
split_at_mut: [10, 2, 30, 4, 5, 6]
```

**Answer:**

- Safe Rust cannot split one `&mut [T]` into two, because the borrow
  checker cannot see that the halves do not overlap. The standard library
  does it with `unsafe`. The function above is the same idea.
- The pattern has **three steps**:
    1. **State the contract**: here "the halves are disjoint".
    2. **Check it in safe code first** (`assert!(mid <= len)`), so no
       caller can break it.
    3. Do the **smallest possible** `unsafe` operation, and write a
       `// SAFETY:` comment that names the facts you rely on.
- An abstraction is **sound** if **no safe caller can cause UB**, whatever
  arguments they pass. If any safe call can trigger UB, the abstraction is
  **unsound**, and that is a bug in **your** `unsafe` code, not in the caller.
- **Privacy is part of the contract.** Keep the fields that hold the
  invariant private, so outside code cannot break it (for example the `len`
  field of a hand-written `Vec`).
- The invariant often spans the whole **module**: a safe function in the same
  module can break an `unsafe` function's assumption. Keep the `unsafe`
  code and its invariants in a tiny module.

## 6. "How would I write a tiny `Vec` with raw pointers?"

```rust
struct MiniVec<T> {
    ptr: NonNull<T>,
    cap: usize,
    len: usize,
    _owns: PhantomData<T>,
}
```

```text
MiniVec: len 9 cap 16 last Some("item9") slice[3] item3
```

**Answer:**

- The skeleton is the sample `examples/unsafe_basics.rs`. Its invariants,
  written once:
    - `ptr` is **non-null and aligned**, and is allocated with
      `Layout::array::<T>(cap)` (or is `NonNull::dangling()` when
      `cap == 0`).
    - The first `len` slots are **initialized**; the rest are **not**.
    - `len <= cap`.
- **`NonNull<T>`** is a non-null raw pointer that is **covariant** in `T`
  (which `*mut T` is not). **`PhantomData<T>`** tells the drop checker that
  the type **owns** `T`s. Both choices are explained in
  [Variance, Drop Check & PhantomData](rust-variance-dropck-and-phantomdata.md).
- **`push`** grows (`alloc` or `realloc`), then `write`s into an
  **uninitialized** slot. Use `ptr.write(value)`, never `*ptr = value`,
  because assignment would **drop the old (uninitialized) value**.
- **`pop`** decrements `len` **first**, then `read`s the slot. After the
  read the slot is logically uninitialized again.
- **`Drop`** must drop every initialized element, then `dealloc` with the
  **same layout**.
- Things this demo skips on purpose, which a real `Vec` handles:
    - **Zero-sized types** (`alloc` with a size of 0 is UB, see
      [Memory Layout §9](rust-memory-layout-and-dsts.md#9-what-is-a-zero-sized-type-and-why-is-it-useful)).
      The sample asserts `size_of::<T>() != 0`.
    - **Panic safety**: if `T::drop` or `clone` panics halfway.
    - **Overflow** of `cap * size_of::<T>()` (`Layout::array` checks it).
- Run the sample under Miri (§8). It **passes cleanly**, which is the
  evidence that the invariants hold, at least for that run.
- The Rustonomicon's chapter "Implementing Vec" is the full version.

## 7. "What are `MaybeUninit`, `ManuallyDrop` and `transmute`, and what are their traps?"

```rust
let mut arr: [MaybeUninit<u32>; 5] = [const { MaybeUninit::uninit() }; 5];
for (i, slot) in arr.iter_mut().enumerate() {
    slot.write((i * i) as u32);
}
// SAFETY: every element was written above.
let squares = unsafe { std::mem::transmute::<[MaybeUninit<u32>; 5], [u32; 5]>(arr) };
```

```text
MaybeUninit squares: [0, 1, 4, 9, 16]
dropping manual
dropping automatic
```

**Answer:**

- **`MaybeUninit<T>`** is the **only** correct way to hold memory that may
  not be initialized yet. Reading an uninitialized integer through a normal
  `u32` is UB, even if you "don't care" about the value. `MaybeUninit<T>`
  has the **same size and layout** as `T` (documented explicitly since
  Rust 1.92).
- The contract of **`assume_init()`**: the memory **really is** a valid `T`.
  Breaking it is UB, and Miri catches it:

```text
error: Undefined Behavior: constructing invalid value of type u32: encountered uninitialized memory, but expected an integer
  --> examples/ub_cases.rs:45:30
   |
45 |             let x = unsafe { m.assume_init() };
   |                              ^^^^^^^^^^^^^^^ Undefined Behavior occurred here
```

- Do **not** write `mem::uninitialized()` or `mem::zeroed()` for types where
  zero is not a valid value (references, `Box`, `NonZero*`). Both are
  traps that `MaybeUninit` replaced.
- **`ManuallyDrop<T>`** wraps a value so the compiler does **not** drop it
  automatically. You decide when, with `ManuallyDrop::drop(&mut x)` (once),
  or take the value out with `ManuallyDrop::take`. Use it in low-level types
  that move values in and out of raw memory.
- **`mem::transmute`** reinterprets the **bits** of one type as another. The
  compiler checks only that the **sizes match**:

```text
error[E0512]: cannot transmute between types of different sizes, or dependently-sized types
 --> compile_fail/transmute_size_mismatch.rs:4:27
  |
4 |     let b: u64 = unsafe { std::mem::transmute(a) };
  |                           ^^^^^^^^^^^^^^^^^^^
  |
  = note: source type: `u32` (32 bits)
  = note: target type: `u64` (64 bits)
```

- Everything else is on you: validity (a `bool` from `3u8` is UB, §8),
  `repr(Rust)` layout that may differ, lifetimes you can extend by accident.
  **Prefer the safe tool**: `u32::from_ne_bytes`, `f32::to_bits`, `as`
  casts, `bytemuck` or `zerocopy` for plain data.
- Transmuting a **reference** to a longer lifetime, or `&T` to `&mut T`, is
  almost always UB. It is the classic way to "fix" a lifetime error wrongly.

## 8. "How do I find undefined behaviour? Show me Miri."

```bash
rustup toolchain install nightly --profile minimal --component miri --component rust-src
cargo +nightly miri run  --example unsafe_basics
cargo +nightly miri test
cargo +nightly miri run  --example ub_cases -- oob
```

**Answer:**

- **Miri** interprets Rust's intermediate form (MIR, see
  [How the Compiler Works](../performance-and-internals/rustc-how-the-compiler-works.md))
  with **extra bookkeeping**: it tracks every allocation, every pointer's
  **provenance**, initialization of each byte, and thread
  synchronization. When your code breaks a rule, it stops and says where.
- `cargo miri test` runs your tests under Miri. `cargo miri nextest`
  works too. Miri is **much slower** than a normal run, so run it on the tests
  that touch `unsafe`, or in CI on a schedule.
- Miri **isolates** the program from the host by default (no direct access to
  the real file system, clock or environment). Use
  `-Zmiri-disable-isolation` if a test needs them.
- Miri finds UB **on the paths your test executes**. It is a **test tool**,
  not a proof. Run it with several seeds for threaded code
  (`-Zmiri-many-seeds`).

Real messages from the sample `examples/ub_cases.rs` (one case each):

**Out-of-bounds read**

```text
error: Undefined Behavior: memory access failed: attempting to access 1 byte, but got alloc732+0x3 which is at or beyond the end of the allocation of size 3 bytes
  --> examples/ub_cases.rs:15:30
   |
15 |             let x = unsafe { *p.add(3) };
   |                              ^^^^^^^^^ Undefined Behavior occurred here
help: alloc732 was allocated here:
  --> examples/ub_cases.rs:13:21
   |
13 |             let v = vec![1u8, 2, 3];
   |                     ^^^^^^^^^^^^^^^
```

**Use after free**

```text
error: Undefined Behavior: memory access failed: alloc737 has been freed, so this pointer is dangling
  --> examples/ub_cases.rs:24:30
   |
24 |             let x = unsafe { *p };
   |                              ^^ Undefined Behavior occurred here
help: alloc737 was allocated here:
help: alloc737 was deallocated here:
```

**Invalid `bool`**

```text
error: Undefined Behavior: constructing invalid value of type bool: encountered 0x03, but expected a boolean
  --> examples/ub_cases.rs:29:36
   |
29 |             let b: bool = unsafe { std::mem::transmute(3u8) };
   |                                    ^^^^^^^^^^^^^^^^^^^^^^^^ Undefined Behavior occurred here
```

**Misaligned read**

```text
error: Undefined Behavior: accessing memory based on pointer with alignment 2, but alignment 4 is required
  --> examples/ub_cases.rs:52:30
```

**Dangling reference (UB to create, even unused)**

```text
error: Undefined Behavior: constructing invalid value of type &i32: encountered a dangling reference (0x4[noalloc] has no provenance)
```

**Data race**

```text
error: Undefined Behavior: Data race detected between (1) non-atomic write on thread `main` and (2) non-atomic read on thread `unnamed-1` at alloc199
  --> examples/ub_cases.rs:63:52
   |
63 |             let t = std::thread::spawn(|| unsafe { *(&raw mut N) += 1 });
   |                                                    ^^^^^^^^^^^^^^^^^^ (2) just happened here
help: and (1) occurred earlier here
```

**Integer turned into a pointer (no provenance)**

```text
error: Undefined Behavior: memory access failed: attempting to access 4 bytes, but got 0x84cc4[noalloc] which is a dangling pointer (it has no provenance)
```

- Other tools, not run for this page: **sanitizers** (`-Zsanitizer=address`
  and `thread`, nightly), **`cargo-careful`** (extra runtime checks in
  `std`), **`loom`** (explores thread interleavings, see
  [Atomics & Memory Ordering](../concurrency-and-async/rust-atomics-and-memory-ordering.md)),
  and **fuzzing** (`cargo fuzz`). Miri cannot run foreign C code, so for FFI
  use the sanitizers.

## 9. "What are pointer provenance and the aliasing models?"

```text
error: Undefined Behavior: attempting a write access using <1849> at alloc732[0x0], but that tag does not exist in the borrow stack for this location
  --> examples/ub_cases.rs:39:13
   |
39 |             *r1 = 1; // r1 was invalidated when r2 was created and used
   |             ^^^^^^^ this error occurs as part of an access at alloc732[0x0..0x4]
   |
   = help: this indicates a potential bug in the program: it performed an invalid operation, but the Stacked Borrows rules it violated are still experimental
help: <1849> was created by a Unique retag at offsets [0x0..0x4]
help: <1849> was later invalidated at offsets [0x0..0x4] by a Unique retag
```

**Answer:**

- **Provenance**: a pointer is **not just an address**. It also carries
  **which allocation, and which borrow, it is allowed to access**. Two
  pointers with the same address but different provenance are different
  things to the abstract machine. That is why turning an integer back into a
  pointer (the last example in §8) is a problem.
- Provenance APIs, **stable** (compiled on 1.99): `ptr.addr()` (address
  only), `ptr.with_addr(a)` and `ptr.map_addr(f)` (keep the old provenance),
  `ptr.expose_provenance()` plus `ptr::with_exposed_provenance(addr)`
  (the explicit "round trip through an integer"), and
  `ptr::without_provenance(addr)` (a pointer that points to nothing, for
  sentinels). Lints (`integer_to_ptr_transmutes`) warn against the
  transmute shortcut.
- **Aliasing**: a `&mut T` is a **unique** path to the data, so the
  compiler may assume nothing else reads or writes it while it is live.
  Breaking this is UB even if both pointers "point to the same place" and
  it "works". The example above makes two `&mut` from one raw pointer, uses
  the second, then the first.
- Rust has **no official** aliasing model yet. Miri implements two
  **experimental** ones:
    - **Stacked Borrows**: **Miri's default** (the message above says so).
      Each memory location keeps a stack of permissions.
    - **Tree Borrows**: the newer alternative, designed to accept more real-world code.
      Enable it with `MIRIFLAGS="-Zmiri-tree-borrows"`. The same code gives:

```text
error: Undefined Behavior: write access through <1792> at alloc732[0x0] is forbidden
   = help: this indicates a potential bug in the program: it performed an invalid operation, but the Tree Borrows rules it violated are still experimental
   = help: the accessed tag <1792> has state Disabled which forbids this child write access
help: the accessed tag <1792> later transitioned to Disabled due to a foreign write access at offsets [0x0..0x4]
```

- Practical rule: code that passes under **both** models is the safest
  bet. Code that only passes under Tree Borrows may break if the final
  model is stricter.
- Safe habits: **derive** raw pointers from the reference you will use
  (`&mut x as *mut _`), **do not reuse** an old pointer after a newer
  `&mut` was used, and prefer `&raw` over making a reference just to take a
  pointer.

## 10. "What are the common mistakes in unsafe code?"

**Answer:**

- **Assuming layout** of a `repr(Rust)` type (cast to bytes, or pass to C).
  See [Memory Layout §11](rust-memory-layout-and-dsts.md#11-what-does-rust-guarantee-about-layout-and-what-should-i-never-assume).
- **`*ptr = value` on uninitialized memory**. The assignment drops the old
  value. Use `ptr.write(value)`.
- **Forgetting the invariant on the safe side**: `unsafe fn pop` is fine,
  but a **safe** `fn set_len(&mut self, n)` that is public breaks every
  other method. Keep invariant-carrying fields private.
- **Panic safety**: a panic between "freed" and "updated" leaves a
  half-built state. Update the bookkeeping first, or use a guard struct.
- **`unsafe impl Send`** added to silence an error. See
  [Variance, Drop Check & PhantomData §7](rust-variance-dropck-and-phantomdata.md#7-what-are-send-and-sync-and-how-are-they-computed).
- **Extending a lifetime** with `transmute` or `&*(ptr)` to escape a borrow
  error. The borrow checker was right; **change the design**.
- **Trusting "it runs fine"**. UB does not announce itself. Run Miri.
- **Missing `SAFETY` comments**. They are how the next reader (and you in a
  year) checks the code.

## 11. "How do AI tools help or hurt here?"

**Answer:**

- **Good at**: explaining a Miri message, drafting a `# Safety` doc
  comment, listing the invariants of a type if you paste it.
- **Bad at**: knowing whether an `unsafe` block is sound. The generated code
  usually **looks** right and **often** violates aliasing or uninitialized
  rules. Models also often write `mem::uninitialized`, `static mut` references,
  and `transmute` for lifetimes.
- A habit that works: ask for the **invariants first**, then the code, then
  **run Miri** and paste the output back. Treat Miri, not the model, as the
  judge.
- Be careful of the opposite claim as well: an AI saying "this is sound"
  proves nothing.
- Never let an assistant **add `unsafe`** to make an error go away. The usual
  fix is a design change (indices instead of references, `Rc`, `split_at_mut`).
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 12. Interview Questions You're Likely to Get Asked

**Basics**

- "What can you do in `unsafe` that you cannot do otherwise?" — expects the
  five powers, and that borrow checking still runs,
  [§1](#1-what-does-unsafe-actually-allow).
- "Name five kinds of undefined behaviour." — expects dangling access, data
  race, invalid value, uninitialized read, aliasing violation,
  [§2](#2-what-is-undefined-behaviour-and-why-is-it-so-bad).
- "`unsafe` block vs `unsafe fn` vs `unsafe trait`?" — expects who owes the
  contract,
  [§3](#3-what-is-the-difference-between-an-unsafe-block-unsafe-fn-and-unsafe-trait).

**Depth**

- "How would you implement `split_at_mut`?" — expects `from_raw_parts_mut`
  with the disjoint-halves argument and a check first,
  [§5](#5-how-do-i-build-a-safe-abstraction-over-unsafe-code).
- "What is wrong with `*ptr = value` into fresh memory?" — expects it drops
  the old uninitialized value; use `write`,
  [§6](#6-how-would-i-write-a-tiny-vec-with-raw-pointers).
- "Why is `MaybeUninit` needed?" — expects reading uninitialized memory as
  `T` is UB,
  [§7](#7-what-are-maybeuninit-manuallydrop-and-transmute-and-what-are-their-traps).
- "What is pointer provenance?" — expects a pointer carries permission, not
  only an address,
  [§9](#9-what-are-pointer-provenance-and-the-aliasing-models).
- "Stacked Borrows vs Tree Borrows?" — expects both experimental, Stacked is
  Miri's default,
  [§9](#9-what-are-pointer-provenance-and-the-aliasing-models).
- "What changed about `unsafe` in edition 2024?" — expects `unsafe_op_in_unsafe_fn`,
  `set_var` unsafe, `static mut` refs denied, `unsafe extern`,
  [§3](#3-what-is-the-difference-between-an-unsafe-block-unsafe-fn-and-unsafe-trait)
  and [§4](#4-what-other-things-did-edition-2024-make-unsafe).

**Design**

- "How do you prove an `unsafe` module is sound?" — expects documented
  invariants, private fields, `SAFETY` comments, Miri and loom tests,
  [§5](#5-how-do-i-build-a-safe-abstraction-over-unsafe-code) and
  [§8](#8-how-do-i-find-undefined-behaviour-show-me-miri).
- "When is `unsafe` the wrong answer?" — expects a design fix first,
  [§10](#10-what-are-the-common-mistakes-in-unsafe-code).

---

## Code Samples

All files are in `code_samples/rust/`. `unsafe_basics` was run on stable
1.99.1 **and** under Miri (clean). `ub_cases` was run **only under Miri**
(nightly): running it on a normal build is undefined behaviour.

- `examples/unsafe_basics.rs` — `split_at_mut`, an `unsafe fn` with a
  `# Safety` section, `MiniVec`, `MaybeUninit`, `ManuallyDrop`, `&raw`,
  `static mut`, a union.
- `examples/ub_cases.rs` — nine deliberate UB cases chosen by argument.
- `compile_fail/deref_raw_outside_unsafe.rs`, `set_var_unsafe.rs`,
  `unsafe_op_in_unsafe_fn_2024.rs`, `static_mut_ref_edition_2024.rs`,
  `transmute_size_mismatch.rs` — compile-time errors quoted above.

```bash
cd code_samples/rust
cargo run --example unsafe_basics
rustup toolchain install nightly --profile minimal --component miri --component rust-src
cargo +nightly miri run --example unsafe_basics
cargo +nightly miri run --example ub_cases -- oob
# cases: oob uaf bool alias uninit align dangling-ref race transmute-ptr
MIRIFLAGS="-Zmiri-tree-borrows" cargo +nightly miri run --example ub_cases -- alias
```
