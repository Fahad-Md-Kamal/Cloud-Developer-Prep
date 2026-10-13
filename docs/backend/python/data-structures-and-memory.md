---
title: "Data Structures & Their Memory Model"
---

# Data Structures & Their Memory Model

One file, one core memory idea per built-in data structure — `list`,
`tuple`, `dict`, `set`, `str`, `bytes` — each measured, not guessed.
For dict/hash-table internals specifically, see
[Python Internals §6](python-internals-and-advanced-oop.md#6-how-is-a-dict-or-a-hash-map-in-any-language-actually-structured);
for GC/reference counting, see
[Python Internals §5](python-internals-and-advanced-oop.md#5-explain-pythons-memory-model-how-does-it-actually-know-when-to-free-an-object).

## 1. List — a resizable array of pointers, over-allocated to grow cheaply

**Core idea:** a list doesn't store your objects inline — it stores
*pointers* to them, in a C array that over-allocates extra room so
`append()` doesn't resize on every single call.

```python
import sys
l = []
for i in range(20):
    l.append(i)
    print(len(l), sys.getsizeof(l))
# len=1 -> 88 bytes, len=5 -> 120, len=9 -> 184, len=17 -> 248 ...
# grows in jumps, not on every append
```

- Each growth jump allocates noticeably more than the current length
  needs (roughly +12% plus a small constant) — the extra slots absorb
  the next several appends for free, which is why `append()` is
  **amortized** O(1), not exactly O(1) on every call.
- This is also why `list` is bigger than `tuple` for the same elements
  — the spare capacity costs real memory:

| n elements | `list` | `tuple` |
|---|---|---|
| 0 | 56 bytes | 40 bytes |
| 5 | 104 bytes | 80 bytes |
| 10 | 136 bytes | 120 bytes |

- If you know the final size up front, `list(range(n))` or
  pre-sizing avoids the repeated-growth overhead entirely compared to
  appending one at a time from empty.

## 2. Tuple — fixed-size, no growth, no spare capacity

**Core idea:** a tuple's size is fixed at creation — no over-allocation,
because nothing can ever be appended to it.

- Immutability is what makes this safe: since a tuple can never grow,
  there's no reason to reserve extra slots the way `list` does.
- This is the entire reason a `tuple` is consistently smaller than the
  equivalent `list` (table above) — pure data, no growth headroom.
- A `namedtuple` is a `tuple` subclass with named-field access bolted
  on at the *class* level — it has the exact same per-instance memory
  footprint as a plain tuple (see
  [Memory & Caching §3](memory-and-caching.md#3-a-live-coding-exercise-used-a-dict-to-return-a-record-why-would-that-take-more-memory-than-the-alternatives)
  for the full dict-vs-tuple-vs-namedtuple comparison).

## 3. Dict — a hash table, covered in depth elsewhere

**Core idea:** a dict is a hash table — array + hash function +
collision resolution — and Python's specific version splits that into
a sparse index table plus a dense, insertion-ordered array.

- Full structure (open addressing, the compact-dict sparse/dense
  split, resizing, why lookup is *amortized* O(1) not guaranteed) is
  covered in
  [Python Internals §6](python-internals-and-advanced-oop.md#6-how-is-a-dict-or-a-hash-map-in-any-language-actually-structured) —
  not repeated here.
- The one fact worth knowing *for this page specifically*: a dict's
  memory cost is dominated by its hash table, not by whatever values
  it holds — see §4 below for how that compares to `set`.

## 4. Set — the same hash table as dict, minus the values, with more fixed startup cost

**Core idea:** a `set` reuses the same open-addressing hash-table
machinery as `dict` — it's a dict with no values, just keys — which is
why membership testing (`x in my_set`) is O(1) the same way dict
lookup is.

```python
d = {i: None for i in range(5)}
s = {i for i in range(5)}
print(sys.getsizeof(d), sys.getsizeof(s))   # 224, 728
```

- **Surprising, measured fact:** a small `set` is noticeably *bigger*
  than a same-size `dict` — `set`'s table has a higher minimum
  allocation than dict's compact two-table design. At larger sizes
  this gap disappears — a 50-item dict and a 50-item set measure
  identically (2264 bytes each), since both are now dominated by the
  same underlying table growth, not the small-set startup cost.
- `frozenset` measures identically to `set` — same structure, just
  immutable (no insert/delete after creation), the same relationship
  `tuple` has to `list`.
- **Practical answer:** for a handful of flags/small lookups, a
  `tuple` + `in` (linear scan) can beat a tiny `set` on *memory*, even
  though `set` wins on lookup *speed* at any real size — know which
  one the question is actually asking about.

## 5. String — immutable, and smaller than a naive 4-bytes-per-character guess

**Core idea:** CPython stores a string in the *smallest* fixed-width
encoding that fits every character it contains — not always 4 bytes
per character, which is the assumption most people start from.

```python
sys.getsizeof("a" * 10)   # 51  -- fits in Latin-1 (1 byte/char)
sys.getsizeof("é" * 10)   # 67  -- still Latin-1, but a non-ASCII code point
sys.getsizeof("中" * 10)   # 78  -- needs 2 bytes/char (UCS-2 range)
sys.getsizeof("😀" * 10)  # 100 -- needs 4 bytes/char (outside the BMP)
```

- This is PEP 393's "flexible string representation" — a pure-ASCII
  string costs roughly a quarter of what the same string would cost if
  Python always used 4-byte-wide characters, which is the real-world
  common case (most text is ASCII or Latin-1) paying for itself.
- **Interning is narrower than people assume.** Identifier-like string
  *literals* (and short strings the compiler constant-folds) get
  reused automatically — two occurrences of `"hello_world"` in the
  same file can be the *same object* (`is` returns `True`). A string
  *built at runtime* (`"".join([...])`, an f-string, anything computed)
  is **not** automatically interned — `a is b` is `False` even for
  identical content, until you explicitly call `sys.intern()` on both.
- **Interview trap:** never rely on `is` to compare strings for
  equality because of this — interning is an implementation detail
  that can silently stop applying the moment a string is built
  dynamically instead of written as a literal. Always use `==`.

## 6. Bytes / bytearray — raw values, no per-element object overhead

**Core idea:** `bytes`/`bytearray` store raw byte values directly in
one contiguous block — not as individual Python objects per element,
which is exactly what a `list` of integers does.

```python
data = list(range(10))         # 10 separate int objects + the list itself
sys.getsizeof(data)             # 136 (just the list's own array)
#   + 10 * sys.getsizeof(1)     # 28 bytes each int object actually costs
#   = 416 bytes, real total

sys.getsizeof(bytes(range(10))) # 43 -- the whole thing, one allocation
```

- A `list[int]` pays for a full Python `int` object (type pointer,
  refcount, the value itself — 28 bytes minimum) *per element*, plus
  the list's own pointer array. `bytes` skips all of that — each value
  is just a raw byte in one block.
- **Practical answer:** anything that's genuinely raw binary/numeric
  data at any real scale (file contents, a byte buffer, numeric arrays)
  belongs in `bytes`/`bytearray` or `array.array`, not a `list` of
  Python number objects — the per-element object overhead dominates
  at scale.
- `bytes` is immutable (like `tuple`/`str`); `bytearray` is the mutable
  version (like `list`) — same relationship pattern as the other pairs
  on this page.

---

## Quick Reference

| Structure | Mutable? | Memory shape | Core trade-off |
|---|---|---|---|
| `list` | Yes | Pointer array, over-allocated | Fast append, costs spare capacity |
| `tuple` | No | Pointer array, exact size | Smaller than list, can't grow |
| `dict` | Yes | Sparse index + dense array (hash table) | O(1) average lookup, real per-entry overhead |
| `set` | Yes | Hash table, no values | O(1) membership, higher fixed cost than dict when small |
| `frozenset` | No | Same as set | Immutable set |
| `str` | No | Smallest fixed-width encoding that fits | Compact for ASCII/Latin-1; interning is literal-only |
| `bytes` | No | Raw contiguous bytes | No per-element object overhead |
| `bytearray` | Yes | Raw contiguous bytes | Mutable `bytes` |

---

## Code Samples

No dedicated code samples yet for this section — every measurement
above is a one-line `sys.getsizeof()` call, runnable directly in a REPL.
