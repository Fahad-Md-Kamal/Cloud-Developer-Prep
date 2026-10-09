---
title: Memory & Caching
---

# Memory & Caching

Processing data that doesn't fit in memory, and memoizing expensive
calls — two efficiency questions with the same underlying theme: pay
only for what you actually use.

## 1. "How would you process a file too large to fit in memory?"

```python
# Loads the whole file into memory at once
def process_all(filename):
    with open(filename) as f:
        return [process_line(line) for line in f]

# Processes one line at a time -- memory stays flat regardless of file size
def process_streaming(filename):
    with open(filename) as f:
        for line in f:
            yield process_line(line)
```

**Answer:**

- A generator — trade "have the whole result ready immediately" for
  "produce one item at a time."
- Memory stays flat whether the file is 1MB or 10GB.

**Likely follow-up — "how would you cut memory further for a class you're instantiating millions of times?"**

```python
class Document:
    __slots__ = ['id', 'title', 'content']  # no per-instance __dict__
```

- `__slots__` removes the per-instance `__dict__` a normal Python
  object carries.
- Real memory savings at scale, at the cost of losing dynamic
  attribute assignment.

**If asked how you'd actually measure it:** `tracemalloc` (built in) —
enough to name it and explain what it does; the deep profiling-tooling
tour isn't interview material.

| Pros | Cons / Trade-offs |
|---|---|
| Generators: memory stays flat regardless of input size | Generators: can only be iterated once — no random access or `len()` |
| `__slots__`: real memory savings for classes instantiated millions of times | `__slots__`: no dynamic attributes, and multiple inheritance with slots gets awkward |
| Both are "pay for what you use" — no cost when data is already small | Neither helps if the actual bottleneck is CPU, not memory |

## 2. "Implement an LRU cache. What data structures does it need, and why both?"

```python
import functools

@functools.lru_cache(maxsize=128)
def get_user_data(user_id: int) -> dict:
    return db.fetch_user(user_id)

get_user_data(123)  # hits the DB
get_user_data(123)  # cache hit, no DB call
```

**Answer for the built-in version:**

- `functools.lru_cache` for memoizing an expensive, pure function
  (same input → same output, no side effects).
- `cache_info()` gives hit-rate stats.

**Answer for "build it from scratch":**

- A hash map for O(1) lookup, plus a doubly linked list for O(1)
  move-to-front and eviction.
- Be ready to explain *why both* are needed — a hash map alone can't
  cheaply track recency order, and a linked list alone can't do O(1)
  lookup by key.

| Pros | Cons / Trade-offs |
|---|---|
| `functools.lru_cache`: one line, zero custom code, battle-tested | Only works for pure functions — hashable args, no side effects, no built-in TTL |
| From-scratch hash map + linked list: full control (custom eviction, TTL, size limits) | More code to maintain — off-by-one bugs in eviction logic are easy to introduce |
| Both give O(1) lookup and O(1) eviction | A cache never invalidated on write is a classic source of stale-data bugs |

## 3. "Explain Python's memory model — how does it actually know when to free an object?"

**Answer:**

- CPython's primary mechanism is **reference counting**: every object
  carries a count of how many references point to it. `x = Document()`
  sets the count to 1; `y = x` bumps it to 2; when a reference goes out
  of scope or is reassigned, the count drops. The moment it hits `0`,
  the object is freed **immediately** — not on some later GC pass.
- This is why Python's memory reclamation feels more deterministic
  than Java's or Go's garbage-collected heaps for most objects — a
  local variable going out of scope at the end of a function typically
  frees its object right then, not at some unpredictable future pause.
- **Reference counting alone can't free a cycle** — two objects that
  reference each other (`a.child = b; b.parent = a`) never hit a
  refcount of `0` even after nothing else references either one. For
  this, CPython runs a separate **cyclic garbage collector**
  (the `gc` module) periodically, which specifically looks for and
  collects groups of objects that are unreachable from outside the
  group even though their internal refcounts are non-zero.
- `sys.getrefcount(obj)` shows an object's current reference count (it
  reports one more than you'd expect, since passing `obj` to
  `getrefcount` itself creates a temporary reference).

### Weak references: holding a reference that doesn't count

```python
import weakref

class Node:
    def __init__(self, name):
        self.name = name

parent = Node("parent")
child = Node("child")
child.parent_ref = weakref.ref(parent)  # doesn't increment parent's refcount

print(child.parent_ref())  # call it to get the actual object (or None if freed)
```

- A `weakref.ref` points at an object **without** incrementing its
  reference count — the referenced object can still be freed as if the
  weak reference didn't exist. Calling the weak reference returns the
  live object, or `None` if it's already been garbage collected.
- **Two real uses this solves:**
    - **Breaking reference cycles deliberately** — a parent/child
      relationship where the child needs to point back to its parent
      (`child.parent_ref`) without that back-pointer keeping the
      parent alive forever, or forcing it to wait for a cyclic-GC pass
      instead of being freed immediately via refcounting.
    - **Caches that shouldn't keep entries alive** — `weakref.WeakValueDictionary`
      (or `WeakKeyDictionary`) holds entries only as long as something
      *else* in the program still references the value. The moment the
      real owner drops its reference, the cache entry disappears on
      its own — useful for an object-identity cache that must never be
      the reason an object stays in memory.
- **Interview point:** this is the mechanism-level answer to "what's
  the difference between a cache that leaks memory and one that
  doesn't" — a plain `dict` cache (or `functools.lru_cache` from
  [§2](#2-implement-an-lru-cache-what-data-structures-does-it-need-and-why-both))
  holds a real, counted reference and keeps every cached object alive
  until explicitly evicted; a `WeakValueDictionary` never does that by
  itself.

## 4. "A live-coding exercise used a dict to return a record — why would that take more memory than the alternatives?"

```python
# dict -- flexible, but carries its own hash table overhead per instance
result = {"product_names": ["A", "B"], "product_total": 19.98}

# tuple -- fixed-size, minimal per-instance overhead
result = (["A", "B"], 19.98)

# namedtuple -- tuple's memory footprint, with named field access
from collections import namedtuple
OrderResult = namedtuple("OrderResult", ["product_names", "product_total"])
result = OrderResult(["A", "B"], 19.98)

# a __slots__ class -- no per-instance __dict__
class OrderResult:
    __slots__ = ("product_names", "product_total")
    def __init__(self, product_names, product_total):
        self.product_names = product_names
        self.product_total = product_total
```

**Measured, not guessed** (`sys.getsizeof`, same two fields in each):

| Shape | Size |
|---|---|
| `dict` | 184 bytes |
| `tuple` | 56 bytes |
| `namedtuple` | 56 bytes |
| `__slots__` class | 48 bytes (no `__dict__` at all) |
| plain class (no `__slots__`) | 48 bytes **+ 296 bytes** for its instance `__dict__` — 344 total |

**Answer:**

- A `dict` is a general-purpose hash table built to support *arbitrary*
  future inserts, deletes, and resizes at any key — it over-allocates
  table slots and stores hashes alongside keys and values to make that
  flexibility fast. A fixed, known-at-creation-time record (exactly two
  fields, always those two fields) never uses that flexibility, so it's
  paying overhead for a capability it doesn't need.
- A `tuple` is a fixed-size, immutable array — no hash table, no
  resize headroom, just a pointer per element. A `namedtuple` is a
  `tuple` subclass, so it has the *exact same* memory footprint as a
  plain tuple — the field names are a class-level lookup, not
  per-instance storage.
- A `__slots__` class goes even further: it tells CPython the exact
  fixed set of attributes up front, so instances skip the per-instance
  `__dict__` entirely — the single biggest win here, since a plain
  object's `__dict__` alone (296 bytes, from the measurement above) is
  larger than the entire `dict` record it's being compared against.
- **The practical answer in an interview:** for a known, fixed-shape
  record returned from a function — exactly the `{"product_names":
  ..., "product_total": ...}` pattern — a `namedtuple`, a
  `@dataclass`, or a `@dataclass(slots=True)` communicates the shape
  explicitly (so a typo like `"product_totle"` becomes an `AttributeError`
  at the call site instead of a silent `KeyError` or `None`), and costs
  less memory per instance than a dict, especially at the scale of
  "one per row in a report with 10 million rows."
