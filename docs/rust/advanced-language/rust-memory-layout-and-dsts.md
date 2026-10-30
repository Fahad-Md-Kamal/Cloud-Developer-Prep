---
title: Rust Memory Layout and Dynamically Sized Types
---

# Rust Memory Layout and Dynamically Sized Types

**Memory layout** is how a value is arranged in bytes: how big it is, where
each field sits, and how it must be aligned in memory. Rust chooses a
layout for every type at compile time. Most of the time you never think
about it. You start to need it when you write `unsafe` code, talk to C,
shrink a hot data structure, or wonder why `Option<Box<T>>` costs nothing
extra. This page builds the mental model from the bottom: bytes, then
structs and enums, then pointers, then the types whose size is **not**
known at compile time.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Every number on
    this page was printed by the samples on a 64-bit macOS (Apple Silicon)
    machine with Rust 1.99.1. Sizes of pointers are 8 bytes on 64-bit
    targets and 4 on 32-bit targets. `mem::size_of_val_raw` and
    `mem::align_of_val_raw` were confirmed stable on 1.99 by compiling a
    call to each. Prerequisite:
    [Types, Enums & Patterns](../foundations/rust-types-enums-and-patterns.md).

## 1. "Where do values live: stack, heap, or static memory?"

**Answer:**

- **Stack**: a fast region that grows and shrinks as functions are called
  and return. Local variables live here. Every value on the stack has a
  size known at compile time.
- **Heap**: memory you ask the allocator for at run time (`Box`, `Vec`,
  `String`, `Rc`). Use it when the size is only known at run time, or the
  value must outlive the current function. See
  [Smart Pointers](../foundations/rust-smart-pointers.md).
- **Static memory**: data baked into the program file, such as string
  literals and `static` items. It lives for the whole run (`'static`).
- A `Vec<u8>` is **two** places at once: a 24-byte header on the stack
  (pointer, capacity, length), plus the elements on the heap.
- Rust has no garbage collector. A value is freed when its owner goes out
  of scope. See
  [Ownership & Borrowing](../foundations/rust-ownership-and-borrowing.md).

## 2. "What are size and alignment, and why does padding exist?"

**Answer:**

- **Size** is how many bytes a value takes. **Alignment** is the rule that
  its address must be a multiple of some number (usually its size, up to a
  limit). A `u32` must sit at an address divisible by 4.
- CPUs read aligned data fast, and some CPUs refuse misaligned reads. So
  the compiler inserts **padding** (unused bytes) between fields.
- The size of a type is always a **multiple of its alignment**. That is
  what lets `[T; N]` place elements one after another with no gaps.
- `size_of::<T>()` and `align_of::<T>()` tell you both, as constants.

```text
-- primitive sizes
u8=1 u16=2 u32=4 u64=8 u128=16 usize=8 char=4 bool=1 ()=0
```

- `char` is 4 bytes because it holds any Unicode scalar value. `()` is
  zero bytes (see [§9](#9-what-is-a-zero-sized-type-and-why-is-it-useful)).

## 3. "Why is a struct sometimes smaller than the sum of its fields in C order?"

```rust
struct Reordered { a: u8, b: u32, c: u8, d: u16 }

#[repr(C)]
struct CLayout { a: u8, b: u32, c: u8, d: u16 }
```

```text
Reordered (default repr): size 8 align 4
CLayout   (repr(C))      : size 12 align 4
CLayout offsets: a=0 b=4 c=8 d=10
```

**Answer:**

- The default representation, **`repr(Rust)`**, gives the compiler **freedom
  to reorder fields**. It sorts them to cut padding: the four fields above
  fit in 8 bytes (4 + 2 + 1 + 1).
- **`repr(C)`** lays fields out **in declaration order**, as a C compiler
  would. Padding goes in between: `a` at 0, three padding bytes, `b` at 4,
  `c` at 8, one padding byte, `d` at 10, total 12.
- The first byte of a `repr(C)` struct is its first field. For
  `repr(Rust)` you cannot know.
- **The layout of `repr(Rust)` is not guaranteed.** It can change between
  compiler versions. Never cast a `repr(Rust)` struct to bytes, send it to
  C, or write it to disk and expect to read it back later.
- Rule of thumb for hot structs: list fields largest first if you use
  `repr(C)`. With the default repr the compiler already does it for you.
- `mem::offset_of!(Type, field)` gives a field's byte offset. It works on
  `repr(Rust)` types too, but the answer is only valid for **this** build.

## 4. "What do `repr(C)`, `packed`, `align`, `transparent` and `repr(u8)` do?"

**Answer:**

| Attribute | What it does | Use it for |
|---|---|---|
| `repr(C)` | Fields in declaration order, C rules | Sharing a struct with C (FFI), stable layout |
| `repr(C, packed)` | No padding at all (alignment 1) | Binary file or network formats |
| `repr(align(N))` | Raises alignment to `N` | Cache-line alignment (avoid false sharing) |
| `repr(transparent)` | Same layout as its single non-zero-sized field | Newtypes passed over FFI |
| `repr(u8)` and friends on an enum | Fixes the size of the tag | C-compatible enums, stable tag |

```text
Packed: size 5 align 1
CacheLine: size 64 align 64
Status (repr(u8)): 1
Meters (transparent f64) = 8
```

- **`packed` has a trap.** Fields may sit at misaligned addresses, so
  taking a **reference** to one is undefined behaviour. The compiler
  refuses:

```text
error[E0793]: reference to field of packed struct is unaligned
  --> compile_fail/packed_reference.rs:10:13
   |
10 |     let r = &p.value;
   |             ^^^^^^^^
   |
   = note: this struct is 1-byte aligned, but the type of this field may require higher alignment
   = note: creating a misaligned reference is undefined behavior (even if that reference is never dereferenced)
   = help: copy the field contents to a local variable, or replace the reference with a raw pointer and use `read_unaligned`/`write_unaligned` (loads and stores via `*p` must be properly aligned even when using raw pointers)
```

- The fix is to **copy** the field (`let v = p.value;`) or use
  `ptr::read_unaligned`. Copying works because the compiler emits an
  unaligned load for you.
- `repr(align(64))` is how you keep two hot counters on different cache
  lines so two threads do not fight over one line. See
  [Atomics & Memory Ordering](../concurrency-and-async/rust-atomics-and-memory-ordering.md).
- `repr(transparent)` matters for FFI: `Meters(f64)` is passed exactly
  like a bare `f64`. A plain `repr(Rust)` newtype carries no such promise.

## 5. "How are enums laid out?"

```text
Shape = 24 (tag + two f64 = 24), Tagged(repr(u8)) = 8
Message (String payload is the biggest): 24
```

**Answer:**

- An enum is a **tag** (which variant) plus room for the **largest
  variant's data**. All variants share the same bytes, like a C `union`
  with a label.
- `Shape::Rect(f64, f64)` needs 16 bytes of data. The tag needs 1 byte, but
  the `f64` demands alignment 8, so the tag takes 8: total 24.
- A **field-less** enum (`Status`) is just the tag. With `repr(u8)` the tag
  is exactly one byte and the numbers are fixed, so you can cast
  `Status::Warn as u8`.
- `repr(u8)` on an enum **with data** gives a defined layout: a `repr(C)`
  union of `repr(C)` structs, each starting with the tag. `Tagged` is 8
  bytes: a 1-byte tag, padding, then a `u32`.
- `repr(C)` on an enum uses the C `int`-sized tag, which is the right thing
  when C code reads it.

## 6. "What is niche optimization, and why is `Option<Box<T>>` free?"

```text
Option<u32>=8 Option<NonZeroU32>=4
Option<bool>=1 Option<Option<bool>>=1
Option<char>=4 Option<&u8>=8 Option<Box<u8>>=8
Option<String>=24 Option<Vec<u8>>=24
```

**Answer:**

- A **niche** is a bit pattern a type **never uses**. A `bool` is only 0 or
  1, so 254 other byte values are invalid. A reference is never null, so
  address 0 is invalid.
- The compiler stores the "no value" case of `Option` **in the niche**.
  `None` for `Option<&u8>` is the null pointer. No tag is needed, so the
  `Option` is the same size as the pointer.
- `Option<u32>` is 8 bytes because `u32` uses every bit pattern: there is no
  niche, so a separate tag (plus padding) is needed. `Option<NonZeroU32>`
  is 4 bytes, because zero is free to mean `None`.
- Niches **stack**: `Option<Option<bool>>` is still 1 byte, because the
  unused values 2 and above can mean `Some(None)` and `None`.
- `String` and `Vec` hold a non-null pointer, so their `Option` is free too
  (24 bytes each).
- Niches are why `Option<Box<T>>` is a **safe** replacement for a nullable
  pointer, and why FFI can pass `Option<extern "C" fn()>` as a nullable
  function pointer. See
  [FFI & C Interoperability](rust-ffi-and-c-interop.md).
- This is an **optimization, not a guarantee**, except for a few
  documented cases (`Option<&T>`, `Option<Box<T>>`, `Option<NonZero*>`,
  `Option<fn>`). Do not rely on others for `unsafe` code.

## 7. "What is the difference between a thin pointer and a fat pointer?"

```text
&u8=8 Box<u8>=8 Rc<u8>=8
&[u8]=16 &str=16 Box<[u8]>=16 Rc<str>=16
&dyn Debug=16 Box<dyn Debug>=16
fn pointer=8 closure(no capture)=0
closure capturing one i32=4
```

**Answer:**

- A **thin pointer** is one address (8 bytes). It points to a value whose
  size the compiler already knows.
- A **fat pointer** is **two** words: the address plus **metadata** that the
  pointer needs to use the target.
    - For a slice (`&[T]`, `&str`, `Box<[T]>`, `Rc<str>`): the **length**.
    - For a trait object (`&dyn Trait`, `Box<dyn Trait>`): a pointer to the
      **vtable** (a table of function pointers, the size, and the
      alignment of the real type).
- That is why `&str` is 16 bytes and a `&String` is 8: the `String` is a
  sized struct, the `str` is not.
- A **closure** is a struct that holds its captured variables. One that
  captures nothing is zero bytes. One that captures an `i32` is 4 bytes. A
  `fn` pointer is 8 bytes. That is why a generic `F: Fn()` costs nothing
  but `Box<dyn Fn()>` is a heap allocation plus a fat pointer. See
  [Iterators & Closures](../foundations/rust-iterators-and-closures.md).
- A call through `dyn Trait` is an **indirect call** via the vtable, so
  the compiler usually cannot inline it. See
  [Traits & Generics §2](../foundations/rust-traits-and-generics.md#2-what-is-the-difference-between-generics-and-dyn-trait).

## 8. "What does `Sized` mean, and what is `?Sized`?"

**Answer:**

- **`Sized`** is a marker trait: "the size of this type is known at compile
  time". The compiler adds `T: Sized` to **every** generic parameter
  automatically.
- A **dynamically sized type (DST)** has a size known only at run time.
  There are three kinds: **slices** `[T]`, **string slices** `str`, and
  **trait objects** `dyn Trait`.
- You cannot hold a DST by value, because the compiler would not know how
  much stack to reserve. You use it **behind a pointer**: `&str`,
  `Box<[T]>`, `Rc<dyn Trait>`. The fat pointer carries the missing size.

```text
error[E0277]: the size for values of type `str` cannot be known at compilation time
 --> compile_fail/unsized_local.rs:2:12
  |
2 | fn show(s: str) {
  |            ^^^ doesn't have a size known at compile-time
  |
  = help: the trait `Sized` is not implemented for `str`
help: function arguments must have a statically known size, borrowed types always have a known size
  |
2 | fn show(s: &str) {
  |            +
```

- **`T: ?Sized`** means "`T` may or may not be `Sized`". It **relaxes** the
  default. The standard library uses it so `Box<T>`, `Rc<T>` and `&T` work
  for `str` and `dyn Trait` too.
- `size_of_val(&value)` gives the real size of a DST value:

```text
[u32; 4] = 16, as &[u32] = 16, str "héllo" = 6
```

- `"héllo"` is 6 bytes because `é` is two bytes in UTF-8 (Unicode
  Transformation Format, 8-bit). See
  [Collections & Strings](../foundations/rust-collections-and-strings.md).
- `size_of_val_raw` and `align_of_val_raw` do the same for a **raw
  pointer** (they are `unsafe`, because the pointer must be valid):

```text
slice: size 12 align 4; &dyn Debug(u16): size 2 align 2
size_of_val(&*Box<dyn Debug> of [u8;100]) = 100
```

- For a `dyn Trait` the size comes **from the vtable**. That is how
  `Box<dyn Trait>` knows how much to free.
- A struct's **last field** may itself be a DST, making the whole struct a
  DST (this is how `Rc<str>` stores its counts and the string together).
  You cannot write one in safe code without help, but you can use `Rc<str>`.

## 9. "What is a zero-sized type, and why is it useful?"

```text
Empty=0 PhantomData<String>=0 [u8; 0]=0
Vec<()> with 1000 items: len=1000 capacity=18446744073709551615 (never allocates)
```

**Answer:**

- A **zero-sized type (ZST)** holds no data: `()`, `struct Empty;`, an
  empty array, `PhantomData<T>`, a closure that captures nothing, a
  fn item.
- Because it has **one possible value**, there is nothing to store. A
  `Vec<()>` never allocates and reports a capacity of `usize::MAX`.
- ZSTs carry information in the **type**, at no cost. Typestate, unit
  markers, and `HashSet<T>` (which is a `HashMap<T, ()>`) all rely on
  this. See
  [Advanced Traits & Type-Level Design](rust-advanced-traits-and-type-level-design.md).
- Raw pointer code must handle ZSTs on purpose: `alloc` with a zero size is
  **undefined behaviour**, so a hand-written `Vec` must special-case it.
  See [Unsafe Rust & Miri](rust-unsafe-and-miri.md).

## 10. "How do I use `Layout` and the allocator API?"

```rust
use std::alloc::{Layout, alloc, dealloc};

let layout = Layout::array::<u32>(10).unwrap();   // size 40, align 4
unsafe {
    let p = alloc(layout) as *mut u32;
    p.add(3).write(9);
    dealloc(p as *mut u8, layout);                // SAME layout
}
```

```text
Layout::new::<u64>() -> size 8 align 8
Layout::array::<u32>(10) -> size 40 align 4
from_size_align(10, 3) is_err: true
raw buffer[9] = 81
```

**Answer:**

- A **`Layout`** is a validated pair of (size, alignment). The alignment
  must be a power of two, so `from_size_align(10, 3)` fails.
- `alloc(layout)` returns a raw pointer (or null on failure). `dealloc`
  needs the **same layout** you allocated with. A wrong layout is
  undefined behaviour.
- `Vec`, `Box` and `Rc` do exactly this under the hood. You write it
  yourself only when building a data structure from scratch.
- A **global allocator** (`#[global_allocator]` with `GlobalAlloc`) swaps
  the allocator for the whole program, for example `jemalloc` or `mimalloc`.
  See [Performance Engineering](../performance-and-internals/rust-performance-engineering.md).
- The newer `Allocator` trait (per-collection allocators) is **not stable**
  as of 1.99 (using it gives `E0658`, "use of unstable library feature
  `allocator_api`"). Use a global allocator or a crate such as `bumpalo`
  (arena).

## 11. "What does Rust guarantee about layout, and what should I never assume?"

**Answer:**

- **Guaranteed**: `repr(C)`, `repr(transparent)`, `repr(packed)`,
  `repr(align)`, `repr(u8)`-style enums; `size` is a multiple of
  `align`; arrays are packed back to back; `Option<&T>`, `Option<Box<T>>`,
  `Option<NonZero*>` have the pointer's size.
- **Not guaranteed**: field order of `repr(Rust)`, the exact size of any
  `repr(Rust)` enum, which niche is used, the layout of `Vec`'s three
  words, the vtable shape.
- **Never** transmute between two `repr(Rust)` types, and never assume a
  struct has no padding. Padding bytes are **uninitialized** and reading
  them is undefined behaviour.
- When the layout matters, **say so in the type**: `repr(C)`,
  `repr(transparent)`, or `repr(u8)`.
- When you only want to know the size, **assert it at compile time**:

```rust
const _: () = assert!(size_of::<Option<Box<u8>>>() == size_of::<Box<u8>>());
```

## 12. "How do AI tools help or hurt here?"

**Answer:**

- They are **good at explaining** why a struct is a given size and at
  drafting `repr(C)` mirrors of a C struct.
- They are **unreliable at predicting exact sizes** of `repr(Rust)` types
  and enums. Ask them for the number, then **print it** with `size_of`.
- Treat a generated `#[repr(packed)]` with suspicion: check that nothing
  takes a reference to a field.
- A generated `unsafe { transmute(...) }` between structs is a red flag.
  Ask for `from_ne_bytes`, `bytemuck`, or `zerocopy` instead.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 13. Interview Questions You're Likely to Get Asked

**Basics**

- "Why is `Option<Box<T>>` the same size as `Box<T>`?" — expects niche
  optimization: `None` is the null pointer,
  [§6](#6-what-is-niche-optimization-and-why-is-optionboxt-free).
- "What is padding and why does it exist?" — expects alignment for fast
  or legal loads,
  [§2](#2-what-are-size-and-alignment-and-why-does-padding-exist).
- "Why is `&str` 16 bytes but `&u32` 8?" — expects fat pointer: address plus
  length,
  [§7](#7-what-is-the-difference-between-a-thin-pointer-and-a-fat-pointer).

**Depth**

- "Does Rust keep struct fields in the order you wrote them?" — expects no,
  `repr(Rust)` reorders; `repr(C)` keeps order,
  [§3](#3-why-is-a-struct-sometimes-smaller-than-the-sum-of-its-fields-in-c-order).
- "Why can't you take a reference to a field of a packed struct?" — expects
  misaligned reference is undefined behaviour,
  [§4](#4-what-do-reprc-packed-align-transparent-and-repru8-do).
- "What is `?Sized`, and name the three DSTs." — expects the relaxed bound
  and slice, `str`, `dyn Trait`,
  [§8](#8-what-does-sized-mean-and-what-is-sized).
- "How does `Box<dyn Trait>` know its size when dropped?" — expects the
  vtable stores size and alignment,
  [§8](#8-what-does-sized-mean-and-what-is-sized).

**Design**

- "When would you use `repr(transparent)`?" — expects a newtype that must be
  ABI-identical to its field, for FFI,
  [§4](#4-what-do-reprc-packed-align-transparent-and-repru8-do).
- "How do you keep two atomics from false sharing?" — expects
  `repr(align(64))` or a padding wrapper,
  [§4](#4-what-do-reprc-packed-align-transparent-and-repru8-do).
- "What layout facts can `unsafe` code rely on?" — expects only the
  documented guarantees,
  [§11](#11-what-does-rust-guarantee-about-layout-and-what-should-i-never-assume).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/memory_layout.rs` — padding, `repr`, enums, niches, fat
  pointers, closures, ZSTs.
- `examples/layout_api.rs` — `Layout`, raw `alloc`/`dealloc`,
  `size_of_val_raw`, enum tags, `repr(transparent)`, a packed field read.
- `compile_fail/packed_reference.rs`, `compile_fail/unsized_local.rs` — the
  two errors quoted above.

```bash
cd code_samples/rust
cargo run --example memory_layout
cargo run --example layout_api
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/packed_reference.rs
```
