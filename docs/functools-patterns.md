---
title: "Functools: Caching & Decorators"
---

# Functools: Caching & Decorators

Memoization with `lru_cache`, and building a decorator that itself
takes arguments — the `functools` patterns that show up in real
production code, not just interview trivia.

## 1. "`@lru_cache` vs `@cache` — when would caching actually hurt you?"

```python
from functools import lru_cache

@lru_cache(maxsize=10_000)
def expensive_computation(text: str) -> dict:
    # pure, deterministic, no side effects
    ...
```

**Answer:**

- `functools.lru_cache(maxsize=N)` memoizes a function's results,
  evicting the least-recently-used entry once `maxsize` is reached.
  `functools.cache` (3.9+) is the unbounded version — equivalent to
  `lru_cache(maxsize=None)`.
- Only correct for **pure functions** — same input always produces
  the same output, no side effects — and every argument must be
  hashable.
- Caching hurts when: inputs are effectively always unique (the cache
  never hits, it's pure memory overhead), the underlying data changes
  but the cache has no way to know to invalidate (stale results), or
  arguments include large or mutable objects that shouldn't be hashed
  at all.
- `cache_info()` reports hits, misses, and current size — check it
  before assuming a cache is actually helping.

**Likely follow-up — "how would you cache something that has side effects, or needs a TTL?"**

- `lru_cache` has no TTL and isn't safe for anything with side
  effects — don't force it to do a job it wasn't built for.
- Reach for a real cache (Redis, a custom TTL wrapper) instead. This
  is the same territory as
  [LLM Response Caching](llm-response-caching.md), just applied at
  function-call scale instead of API-response scale.

| Pros | Cons / Trade-offs |
|---|---|
| One line, zero custom eviction/bookkeeping code | Only safe for pure, hashable-argument functions |
| `cache_info()` gives visibility into whether it's actually helping | No TTL — stale results persist until evicted by LRU pressure or process restart |
| Unbounded `cache` is simplest when memory isn't a concern | Unbounded caching on a long-running process can leak memory if inputs are unbounded |

## 2. "Write a decorator that itself takes arguments — e.g. `@monitor_performance('db_query')`."

```python
from functools import wraps
import time

def monitor_performance(metric_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return func(*args, **kwargs)
            finally:
                record_metric(metric_name, time.monotonic() - start)
        return wrapper
    return decorator

@monitor_performance("db_query")
def fetch_user(user_id: int):
    ...
```

**Answer:**

- Three levels of nesting: the outer function takes the decorator's
  *own* arguments (`metric_name`), returns the actual decorator, which
  takes the function being wrapped, which returns the final wrapper.
- `functools.wraps(func)` on the wrapper preserves the original
  function's `__name__`, `__doc__`, and other metadata — skip it and
  debugging tools, introspection, and stack traces show `wrapper`
  everywhere instead of the real function name.
- This is the same closure mechanism covered in
  [Practical Patterns §1](practical-patterns.md#1-write-a-decorator-that-takes-an-argument-then-explain-why-it-works),
  applied here to cross-cutting concerns — performance monitoring,
  rate limiting, retry logic — instead of a toy example.

**Likely follow-up — "what's a real cross-cutting concern you'd implement this way, beyond monitoring?"**

- Retry logic with backoff around a flaky external call
  (`@retry(max_attempts=3)`), rate limiting on a per-endpoint basis, or
  role-based access checks — all "wrap this function with extra
  behavior, configured per call site" problems that this same
  three-level pattern solves.

| Pros | Cons / Trade-offs |
|---|---|
| Reusable cross-cutting behavior without touching the wrapped function's body | Three levels of nesting is genuinely harder to read than a plain function |
| `functools.wraps` keeps introspection/debugging accurate | Easy to forget `@wraps` and lose the original function's identity everywhere |
| Composable — multiple parameterized decorators stack cleanly | Stacking order still matters and is easy to get backwards |

---

## Code Samples

- `code_samples/chapter-38/functools_enterprise_patterns.py` —
  production caching, decorator factories, performance monitoring
- `code_samples/chapter-38/testing_stdlib_patterns.py` — unit-testing
  strategies for stdlib-based code, mocking, performance testing
