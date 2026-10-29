---
title: Rust Collections & Strings
---

# Rust Collections & Strings

Almost every program is "put things in a container, look them up, loop
over them." Rust's standard library gives you a small, well-chosen set of
containers, and **strings are the most surprising of them**: Rust text is
always UTF-8, so a "character" is not a byte and you cannot index into a
string with a number. This page explains how the main containers are laid
out in memory (so you can predict their cost), how to choose between
them, and how to handle text correctly.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Examples were run
    on 1.99.1. Implementation details marked "currently" can change
    between releases. The guarantees are the documented complexities.

## 1. "Which collections does the standard library have, and how do you choose?"

**Answer:**

| Type | Shape | Lookup | Insert / remove | Keeps order? |
|---|---|---|---|---|
| `Vec<T>` | Growable array | by index O(1); by value O(n) | end O(1) amortized; middle O(n) | insertion order |
| `VecDeque<T>` | Ring buffer | by index O(1) | both ends O(1) | insertion order |
| `HashMap<K, V>` / `HashSet<T>` | Hash table | O(1) average | O(1) average | **no** (random) |
| `BTreeMap<K, V>` / `BTreeSet<T>` | Sorted tree | O(log n) | O(log n) | **sorted by key** |
| `BinaryHeap<T>` | Max-heap | peek max O(1) | push, pop O(log n) | only the max is guaranteed |
| `LinkedList<T>` | Doubly linked list | O(n) | O(1) at a known node (rarely useful) | insertion order |

- **`Vec` is the default.** Start with it. Contiguous memory is friendly to
  the CPU cache, and for small and medium sizes a linear scan of a `Vec`
  often **beats** a `HashMap`.
- Choose another container when you have a **specific need**:
    - Fast lookup by key, order does not matter: `HashMap`.
    - Sorted iteration or range queries (`range(80..)`): `BTreeMap`.
    - A queue (push one end, pop the other): `VecDeque`.
    - "Give me the largest or smallest next": `BinaryHeap`.
- `LinkedList` is almost never the right choice in Rust. The standard
  library documentation itself says to use `Vec` or `VecDeque` unless you
  have measured a reason.
- Third-party containers fill gaps: `indexmap` (a map that keeps insertion
  order), `smallvec` and `arrayvec` (small arrays without a heap
  allocation), `slotmap` (stable ids), `hashbrown` (the hash table the
  standard `HashMap` is built on, with more options).

## 2. "How does `Vec` work inside, and what are `Vec`, array, and slice?"

**Answer:**

- A `Vec<T>` is three words on the stack: a **pointer** to a heap buffer,
  a **length** (items in use), and a **capacity** (slots allocated). Items
  sit next to each other in the buffer.
- `push` writes into spare capacity. When the buffer is full, the `Vec`
  **allocates a bigger buffer** (currently about **double**), moves the items,
  and frees the old one. This makes `push` **amortized O(1)**: most pushes
  are cheap, and a rare one is expensive. The sample output shows the
  growth `4 → 8 → 16 → 32 → 64`.
- **Reallocation invalidates addresses.** This is exactly the bug the
  borrow checker prevents: holding `&v[0]` while calling `v.push(...)` is a
  compile error, because the push may move the buffer.
- **Preallocate** when you know the size:
  `Vec::with_capacity(n)` or `v.reserve(n)`. It avoids repeated
  reallocation. `shrink_to_fit` gives memory back.
- The three related types:

| Type | Owns data? | Size known at compile time? | Use |
|---|---|---|---|
| `[T; N]` (array) | Yes | Yes | Fixed-size data, often on the stack |
| `Vec<T>` | Yes (heap) | No | Growable list |
| `&[T]` / `&mut [T]` (slice) | **No**, a view | No | The **parameter type** for "a sequence of T" |

- **Accept `&[T]` in function parameters**, not `&Vec<T>`. A slice accepts a
  `Vec`, an array, or part of either.
- Useful operations: `swap_remove` (O(1) remove, order not kept), `drain(..)`
  (remove a range and iterate it), `retain` (keep matching), `dedup`,
  `extend`, `windows(n)` and `chunks(n)`, `split_at_mut`, and
  `binary_search` (on sorted data).
- **`extract_if`** (stable since Rust 1.87 for `Vec`, and for `HashMap`,
  `HashSet`, and `BTreeMap`/`BTreeSet` in later versions) removes the items
  matching a predicate and **yields them**, in one pass. The sample
  splits evens out of a vector with it.
- Sorting: `sort` is **stable** (equal items keep their order, currently
  driftsort), `sort_unstable` is faster and may reorder equal items
  (currently ipnsort). Both are **fast on already-sorted and nearly sorted
  data**.
- **Bounds checks**: `v[i]` panics if out of range. `v.get(i)` returns an
  `Option`. Iterators avoid the checks entirely.
- `Box<[T]>` is a slice owned on the heap with **no spare capacity**: two
  words instead of three. Use it for read-only lists that stay for a long
  time.

## 3. "How do strings work? Why can't you index them?"

```rust
let s = String::from("héllo 🦀");
s.len()                  // 11 (bytes)
s.chars().count()        // 7  (Unicode scalar values)
s.get(0..2)              // None: byte 2 is in the middle of 'é'
s.get(0..3)              // Some("hé")
s.floor_char_boundary(2) // 1  (stable since Rust 1.91)
```

**Answer:**

- **All Rust text is UTF-8.** A `char` is one Unicode scalar value (4 bytes
  in memory), but in a string it takes **1 to 4 bytes**: `é` takes 2 and
  `🦀` takes 4.
- Types:

| Type | What it is |
|---|---|
| `String` | Owned, growable UTF-8 text (like a `Vec<u8>` that is always valid UTF-8) |
| `&str` | A borrowed UTF-8 slice: a pointer and a byte length |
| `char` | One Unicode scalar value |
| `&[u8]` / `Vec<u8>` | Raw bytes, no text guarantee |
| `OsString`, `&OsStr` | Operating-system strings (may not be valid UTF-8, for example on Windows or Linux file names) |
| `PathBuf`, `&Path` | File paths, built on `OsString` |
| `CString`, `&CStr` | Zero-terminated C strings, for FFI |

- **Why no `s[i]`:** an index would have to mean a byte, a `char`, or a
  user-perceived character, and each answer is wrong for someone. Also,
  finding the Nth `char` takes O(n). Rust makes you **say which one you
  want**:
    - `s.len()` is bytes. `s.chars().count()` counts scalar values (O(n)).
    - `s.chars()`, `s.bytes()`, `s.char_indices()` iterate.
    - `&s[a..b]` slices by **byte** offsets, and **panics** if an offset is
      not on a character boundary. Use `s.get(a..b)` to get `None` instead,
      and `floor_char_boundary` or `ceil_char_boundary` to find a safe cut.
- A **user-perceived character** (a "grapheme") can be several scalar
  values: `é` can be `e` plus a combining accent, and a flag emoji is two
  scalars. The standard library does not handle graphemes. Use the
  `unicode-segmentation` crate.
- **`&str` in parameters, `String` in fields.** `fn f(s: &str)` accepts
  `&String` too (auto-deref). See
  [Ownership & Borrowing §7](rust-ownership-and-borrowing.md#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it).
- Building text:
    - `s.push_str("..")` and `s.push('c')` append.
    - `a + &b` **moves** `a` and appends `b`. It is efficient but surprising.
    - `format!("{a}{b}")` allocates a new string and borrows both.
    - To append formatted text without a temporary, `use std::fmt::Write;`
      and `write!(s, "{n}")`.
    - `String::with_capacity(n)` avoids reallocation when you know the size.
- Bytes to text: `String::from_utf8(bytes)` checks validity and returns a
  `Result`. `String::from_utf8_lossy` replaces bad bytes with `�`.
  `from_utf8_unchecked` is `unsafe`.
- Case conversion is Unicode-aware: `"ß".to_uppercase()` is `"SS"`, so the
  length can change.

## 4. "How does `HashMap` work, and what should you know before using it?"

```rust
let mut counts: HashMap<&str, usize> = HashMap::new();
for word in text.split_whitespace() {
    *counts.entry(word).or_insert(0) += 1;   // one lookup: find-or-insert
}
```

**Answer:**

- A `HashMap` is a **hash table**: it hashes the key to find a slot. The
  standard one is built on the **hashbrown** library, a "Swiss table", which
  checks groups of slots at once with CPU vector instructions.
- The **default hasher** is **SipHash** (currently 1-3), chosen to resist
  **HashDoS** attacks (an attacker sending keys that all collide, to slow
  the program down). It is **randomly seeded per map**, which has two
  effects:
    - **Iteration order is random** and changes between runs. Never rely on
      it. Sort the keys, or use a `BTreeMap` or `IndexMap`, when order
      matters.
    - It is **slower** than simple hashers. For internal data with trusted
      keys, `FxHash` or `ahash` can be much faster. For keys that come from
      users, keep the default.
- **The key contract:** if `k1 == k2`, then `hash(k1) == hash(k2)`. The
  `Hash` and `Eq` implementations must agree. `#[derive(Hash, PartialEq,
  Eq)]` on a struct does this for you.
- **Floats cannot be keys** (`f64` is not `Eq` or `Hash`) because of NaN.
  Wrap them, or use integers.
- **The Entry API** does "get or insert" with **one** lookup and **no**
  borrow problems:
    - `entry(k).or_insert(v)`, `.or_insert_with(|| ...)`, `.or_default()`.
    - `entry(k).and_modify(|v| ...).or_insert(v)`.
- Lookups take a **borrowed form** of the key: a `HashMap<String, V>` can be
  queried with a `&str` (`map.get("name")`) because of the `Borrow` trait.
- **Mutating while iterating** is a compile error. Collect the keys first,
  or use `retain`, or `extract_if` to remove items in one pass.
- `with_capacity(n)` avoids repeated resizing. A resize **rehashes** every
  entry.
- `HashSet<T>` is a `HashMap<T, ()>` with set operations (`intersection`,
  `union`, `difference`).

## 5. "When do you want a `BTreeMap`, `VecDeque`, or `BinaryHeap`?"

**Answer:**

- **`BTreeMap` / `BTreeSet`**: a **B-tree**. Nodes hold several keys (currently
  up to 11) in a small sorted array, which is cache-friendly. Keys must be
  `Ord`. You get:
    - **Sorted iteration.**
    - **Range queries**: `map.range(80..)` or `range(..=10)`.
    - `first_key_value()`, `last_key_value()`, `pop_first()`, `pop_last()`.
    - Lookups cost **O(log n)**, slower than a hash map, but the order is
      free.
- **`VecDeque`**: a **ring buffer**. Push and pop at **both ends** in O(1),
  and index in O(1). Use it as a **queue**, a sliding window, or for BFS
  (breadth-first search). Use `make_contiguous()` to get one slice.
- **`BinaryHeap`**: a **max-heap**. `push`, `pop` are O(log n) and `peek`
  is O(1). For a **min-heap**, wrap items in `std::cmp::Reverse`. It is the
  tool for **priority queues**, schedulers, and Dijkstra's algorithm.
  `into_sorted_vec()` sorts in place.
- The sample shows a score index with `range`, a deque used from both
  ends, and a min-heap built with `Reverse`.

## 6. "What are the iteration forms, and how does ownership flow through a collection?"

**Answer:**

- Three ways to loop over a `Vec<T>`:

| Form | Items | Collection afterwards |
|---|---|---|
| `for x in &v` (or `v.iter()`) | `&T` | still usable |
| `for x in &mut v` (or `v.iter_mut()`) | `&mut T` | still usable, items modified |
| `for x in v` (or `v.into_iter()`) | `T` (owned) | **moved**, gone |

- **`drain(range)`** removes items and yields them while keeping the `Vec`
  alive. **`into_iter`** consumes the whole thing.
- **Edition 2021 and later:** arrays implement `IntoIterator` by value, so
  `for x in [1, 2, 3]` gives `i32`, not `&i32`. Edition 2024 does the same
  for `Box<[T]>`.
- A map or collection **owns** its items. Putting a `String` into a
  `Vec<String>` **moves** it. To keep the original, clone, or store a
  reference (`Vec<&str>`) and accept the lifetime that comes with it. See
  [Lifetimes §10](rust-lifetimes.md#10-when-should-you-avoid-lifetime-parameters-entirely).
- **Indexing a map** with `map["key"]` **panics** if the key is missing.
  Prefer `get`.
- To change a value you looked up, use `get_mut` or the Entry API, not a
  stored reference. See the borrow rules in
  [Ownership & Borrowing §5](rust-ownership-and-borrowing.md#5-what-are-the-rules-of-borrowing-and-why-do-they-exist).
- Iterator chains such as `.iter().map(...).collect::<Vec<_>>()` are covered
  in [Iterators & Closures](rust-iterators-and-closures.md).

## 7. "What makes collection code fast or slow?"

**Answer:**

- **Memory layout beats big-O for small data.** A `Vec` scan over 50 items
  is usually faster than a `HashMap` lookup. Measure with real data.
- **Preallocate** with `with_capacity`. Pushing 1 million items one at a
  time causes about 20 reallocations.
- **Avoid `clone()` in loops.** Borrow, or move.
- **A `Vec<Vec<T>>` is many separate allocations.** For a grid or matrix,
  one flat `Vec<T>` with index arithmetic (`row * width + col`) is faster and
  uses less memory.
- **Struct of arrays vs array of structs**: when you scan one field of many
  items, storing each field in its own `Vec` is more cache-friendly.
- **Reuse buffers**: `v.clear()` keeps the capacity, so a loop that
  clears and refills one `Vec` allocates only once. The same goes for
  `String::clear`.
- **Small collections**: `smallvec` or `arrayvec` keep a few items inline
  with no heap allocation.
- Profile before tuning. See
  [Performance Engineering](../performance-and-internals/rust-performance-engineering.md).

## 8. "How do AI tools help or hurt here?"

**Answer:**

- Good for: choosing a container, writing Entry-API code, and converting
  loops to iterator chains.
- They often write `s[i]` or `.chars().nth(i)` for text indexing without
  noting the O(n) cost, `clone()` inside loops, and `HashMap` where a
  sorted `Vec` or `BTreeMap` would do. Ask "what is the time cost of each
  line, and what happens with non-ASCII text?"
- They sometimes assume `HashMap` keeps insertion order (that is Python's
  `dict`, not Rust's). It does not.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Vec and slices**

- "How is a `Vec` laid out, and why is `push` amortized O(1)?" — expects
  pointer, length, capacity, and geometric growth,
  [§2](#2-how-does-vec-work-inside-and-what-are-vec-array-and-slice).
- "Why can't you hold `&v[0]` across `v.push(1)`?" — expects reallocation
  can move the buffer, so the borrow checker rejects it,
  [§2](#2-how-does-vec-work-inside-and-what-are-vec-array-and-slice).
- "Why take `&[T]` instead of `&Vec<T>`?" — expects slices accept more
  callers,
  [§2](#2-how-does-vec-work-inside-and-what-are-vec-array-and-slice).
- "`sort` vs `sort_unstable`?" — expects stable vs faster-but-unstable,
  [§2](#2-how-does-vec-work-inside-and-what-are-vec-array-and-slice).

**Strings**

- "Why can't you write `s[0]` on a `String`?" — expects UTF-8: bytes vs
  scalar values vs graphemes, and O(n) to find the Nth character,
  [§3](#3-how-do-strings-work-why-cant-you-index-them).
- "What does `s.len()` return for `"héllo"`?" — expects bytes (6),
  [§3](#3-how-do-strings-work-why-cant-you-index-them).
- "What happens if you slice a string in the middle of a character?" —
  expects a panic, and `get` for a safe version,
  [§3](#3-how-do-strings-work-why-cant-you-index-them).
- "`String`, `&str`, `OsString`, `CString`?" — expects the table,
  [§3](#3-how-do-strings-work-why-cant-you-index-them).

**Maps**

- "Why is `HashMap` iteration order random, and what is the default hasher
  for?" — expects per-map random seed and HashDoS resistance,
  [§4](#4-how-does-hashmap-work-and-what-should-you-know-before-using-it).
- "Why can't `f64` be a hash key?" — expects NaN breaks `Eq`,
  [§4](#4-how-does-hashmap-work-and-what-should-you-know-before-using-it).
- "What does the Entry API solve?" — expects one lookup, no double borrow,
  [§4](#4-how-does-hashmap-work-and-what-should-you-know-before-using-it).
- "When `BTreeMap` over `HashMap`?" — expects ordered iteration and range
  queries,
  [§5](#5-when-do-you-want-a-btreemap-vecdeque-or-binaryheap).
- "How do you build a min-heap with `BinaryHeap`?" — expects `Reverse`,
  [§5](#5-when-do-you-want-a-btreemap-vecdeque-or-binaryheap).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/collections_and_strings.rs` — `Vec` capacity growth, UTF-8
  byte offsets, `get` and `floor_char_boundary`, the Entry API, `BTreeMap`
  ranges, `VecDeque`, a min-heap, set operations, and `extract_if`.

```bash
cd code_samples/rust
cargo run --example collections_and_strings
```
