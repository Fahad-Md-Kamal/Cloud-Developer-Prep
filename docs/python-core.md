---
title: Python Core
---

# Python Core

Fundamentals to be able to *explain and code*, not just recognize. Senior
interviews test these with short "what does this print, and why" prompts
more often than trivia questions.

## Checklist

- Generators vs iterators; `yield` and `yield from`
- Decorators (with and without arguments), `functools.wraps`
- Context managers (`with`, `__enter__`/`__exit__`,
  `contextlib.contextmanager`)
- `*args`/`**kwargs`, the mutable default argument gotcha (see worked
  example below)
- The GIL — what it is, why it matters, when `asyncio` /
  `multiprocessing` / `threading` each apply
- List/dict/set comprehensions vs generator expressions (memory
  tradeoffs)
- `@staticmethod` vs `@classmethod` vs instance method
- Exception handling: custom exceptions, `finally`, exception chaining
- Type hints: `Optional`, `Union`, basic `mypy` awareness

## Worked example: mutable default arguments

```python
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item("a"))
print(add_item("b"))
```

**Output:**

```
['a']
['a', 'b']
```

**Why:** default arguments are evaluated **once, at function definition
time**, not on each call. `items=[]` creates a single list object bound to
the parameter default, and it persists (and gets mutated) across every
call that doesn't pass its own `items` — it's not "reusing the parameter
value" so much as "there's only ever one default object, mutated in
place."

**Fix — the standard idiom:**

```python
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

Default to `None` (immutable, safe to reuse), then create a fresh mutable
object inside the function body on each call if none was passed. Same
pattern applies to any mutable default (`{}`, `[]`, or a custom mutable
object).

!!! note "Session note"
    Covered in the [session log](session-log.md#2026-09-22) — answered
    correctly, including the fix, after a nudge on the "why."
