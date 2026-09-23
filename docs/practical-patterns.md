---
title: Practical Patterns
---

# Practical Patterns

Decorators, context managers, and background tasks — the everyday
Python patterns that show up in real code far more than the flashier
topics do.

## 1. "Write a decorator that takes an argument. Then explain why it works."

```python
def repeat(n: int):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(n):
                func(*args, **kwargs)
        return wrapper
    return decorator

@repeat(3)
def say_hello(name: str):
    print(f"Hello, {name}!")
```

**Answer:**

- Three nested levels — `outer(args) → decorator(func) →
  wrapper(*a, **kw)`.
- Be able to draw that shape cold.

**Likely follow-up — "why can `wrapper` still see `n` after `repeat(3)` already returned?"**

- It's a closure — `wrapper` references `n`, so Python keeps it alive
  as long as `wrapper` exists, even though `repeat`'s own stack frame
  is long gone.

**Where you'd actually use this:**

- `@login_required`
- `@transaction.atomic`
- `@retry(max_attempts=3)` around a flaky external call
- A timing decorator wrapped around a slow endpoint during a perf
  investigation

| Pros | Cons / Trade-offs |
|---|---|
| Cross-cutting concerns added without touching the function body | Stack traces get noisier — an error inside `wrapper` obscures the original call site |
| Reusable across many functions with zero duplication | Debugging requires understanding closures — a real barrier for less experienced reviewers |
| Composable — multiple decorators stack cleanly | Stacking order matters and is easy to get wrong |

## 2. "What are the two ways to build a context manager, and what does `__exit__`'s return value control?"

```python
from contextlib import contextmanager

@contextmanager
def managed_file(path: str, mode: str):
    f = open(path, mode)
    try:
        yield f
    finally:
        f.close()
```

**Answer:**

- A class with `__enter__`/`__exit__`, or (simpler, most of the time)
  a generator wrapped in `@contextmanager`.
- The point is deterministic cleanup — `finally` runs whether the
  block succeeded or raised.

**The part people miss:**

- `__exit__` returning `True` **swallows** an exception raised inside
  the `with` block instead of propagating it.
- Rarely what you actually want — know it's there because interviewers
  specifically probe this.

**Where you'd actually use this:**

- `with transaction.atomic():`
- File/socket handling
- Temporarily overriding a setting in a test

| Pros | Cons / Trade-offs |
|---|---|
| Cleanup always runs, even on exception — no forgotten `f.close()` | `@contextmanager` generators can be tricky to debug if an exception crosses the `yield` |
| `with` blocks make resource lifetime visible at the call site | A class-based version needs two extra methods for what a `finally` block could do inline |
| Composable — multiple resources nest cleanly (`with a, b:`) | Swallowing exceptions via `__exit__` returning `True` is an easy, hard-to-spot bug |

## 3. "When do you reach for Celery instead of just handling something in the request?"

```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379')

@app.task(bind=True, max_retries=3)
def process_document(self, doc_id, doc_content):
    try:
        return analyze(doc_content)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

process_document.delay(doc_id, content)  # runs in a worker, not this request
```

**Answer:**

- Anything slow or non-critical to the immediate HTTP response —
  sending an email, processing an upload, calling a slow third-party
  API — moves out of the request/response cycle into a task, backed by
  Redis or RabbitMQ.
- `.delay()` queues it; a separate worker process picks it up.

**Likely follow-up — "what breaks if this task runs twice?"**

- Retries mean it can.
- Add an idempotency key so a retried task doesn't double-process —
  "charge the customer twice" is the textbook version of this bug.

| Pros | Cons / Trade-offs |
|---|---|
| Request/response stays fast — slow work doesn't block the HTTP response | Adds infrastructure (a broker, worker processes) that can itself fail or fall behind |
| Built-in retry/backoff for transient failures | Retries mean tasks can run more than once — must be designed idempotent |
| Workers scale independently from web servers | Debugging is harder — failures happen out-of-band, not in the request that triggered them |

---

## Practice Notes (from live session)

### Mutable default arguments

**Asked:** what does this print, and why?

```python
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item("a"))
print(add_item("b"))
```

**Answer:**

```
['a']
['a', 'b']
```

- Default arguments are evaluated **once, at function definition
  time**, not on each call.
- `items=[]` creates a single list object bound to the parameter
  default, and it persists (and gets mutated) across every call that
  doesn't pass its own `items`.
- It's not "reusing the parameter value" so much as "there's only ever
  one default object, mutated in place."

**Fix — the standard idiom:**

```python
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

- Default to `None` (immutable, safe to reuse), then create a fresh
  mutable object inside the function body on each call if none was
  passed.
- Same pattern applies to any mutable default (`{}`, `[]`, or a custom
  mutable object).

!!! note "Session note"
    Covered in the [session log](session-log.md#2026-09-22) — answered
    correctly, including the fix, after a nudge on the "why."
