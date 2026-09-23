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

**Answer:** A generator — trade "have the whole result ready
immediately" for "produce one item at a time." Memory stays flat
whether the file is 1MB or 10GB.

**Likely follow-up — "how would you cut memory further for a class
you're instantiating millions of times?"**

```python
class Document:
    __slots__ = ['id', 'title', 'content']  # no per-instance __dict__
```

`__slots__` removes the per-instance `__dict__` a normal Python object
carries — real memory savings at scale, at the cost of losing dynamic
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

**Answer for the built-in version:** `functools.lru_cache` for
memoizing an expensive, pure function (same input → same output, no
side effects). `cache_info()` gives hit-rate stats.

**Answer for "build it from scratch":** a hash map for O(1) lookup, plus
a doubly linked list for O(1) move-to-front and eviction. Be ready to
explain *why both* are needed — a hash map alone can't cheaply track
recency order, and a linked list alone can't do O(1) lookup by key.

| Pros | Cons / Trade-offs |
|---|---|
| `functools.lru_cache`: one line, zero custom code, battle-tested | Only works for pure functions — hashable args, no side effects, no built-in TTL |
| From-scratch hash map + linked list: full control (custom eviction, TTL, size limits) | More code to maintain — off-by-one bugs in eviction logic are easy to introduce |
| Both give O(1) lookup and O(1) eviction | A cache never invalidated on write is a classic source of stale-data bugs |
