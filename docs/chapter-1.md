---
title: "Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)"
---

# Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)

Nine interview questions, each with the answer you should be able to
give cold — code plus the reasoning behind it. Read a question, try to
answer it yourself first, then check against the answer.

---

## 1. "How would you write a generic repository class instead of one per model?"

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class APIResponse(Generic[T]):
    def __init__(self, data: T, status: int):
        self.data = data
        self.status = status

user_response = APIResponse[User](user_data, 200)
```

**Answer:** `Generic[T]` lets a class work with any type while the type
checker still tracks *which* type — a `Repository[T]` base class works
for `UserRepository` and `OrderRepository` without duplicating CRUD
logic or falling back to untyped `Any`.

**Likely follow-up — "what's wrong with just using `TypeVar` unbounded,
or `Any`?"** Both hide exactly the errors typing exists to catch. Bound
it (`TypeVar('T', bound=BaseModel)`) once the generic needs to call a
specific method on `T`.

| Pros | Cons / Trade-offs |
|---|---|
| One implementation works for every model — no duplicated CRUD logic | Harder to read for developers unfamiliar with `TypeVar`/`Generic` |
| Type checker still catches misuse (passing an `Order` where a `User` is expected) | Bounding a TypeVar adds coupling to a specific base class |
| Refactoring a shared method updates every concrete repository at once | Overly generic abstractions can hide simple, one-off logic behind unnecessary machinery |

## 2. "Explain Protocols — how are they different from inheritance-based interfaces?"

```python
from typing import Protocol

class Crawlable(Protocol):
    def fetch(self, url: str) -> str: ...

class WebCrawler:
    def fetch(self, url: str) -> str: ...  # satisfies Crawlable, no inheritance

class APICrawler:
    def fetch(self, url: str) -> str: ...  # so does this
```

**Answer:** A `Protocol` checks structurally — "anything with this
method counts" — instead of requiring a shared base class. It's duck
typing with static verification: `WebCrawler` and `APICrawler` both
satisfy `Crawlable` just by having the right method signature.

**Likely follow-up — "when would you reach for this over inheritance?"**
Swapping HTTP clients (`requests` for `httpx`) or mocking a dependency
in a test — both work because they satisfy the same Protocol, without
forcing every implementation through one base class.

| Pros | Cons / Trade-offs |
|---|---|
| No shared base class needed — existing classes satisfy it retroactively | Less discoverable than inheritance — no simple "find subclasses" search |
| Great for adapting third-party classes you don't control | `@runtime_checkable` + `isinstance()` only checks method names exist, not correct behavior |
| Encourages small, role-based interfaces that are easy to mock in tests | Overuse can make it unclear which concrete types are actually expected at a call site |

## 3. "Write a decorator that takes an argument. Then explain why it works."

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

**Answer:** Three nested levels — `outer(args) → decorator(func) →
wrapper(*a, **kw)`. Be able to draw that shape cold.

**Likely follow-up — "why can `wrapper` still see `n` after `repeat(3)`
already returned?"** It's a closure — `wrapper` references `n`, so
Python keeps it alive as long as `wrapper` exists, even though
`repeat`'s own stack frame is long gone.

**Where you'd actually use this:** `@login_required`,
`@transaction.atomic`, `@retry(max_attempts=3)` around a flaky external
call, a timing decorator wrapped around a slow endpoint during a perf
investigation.

| Pros | Cons / Trade-offs |
|---|---|
| Cross-cutting concerns added without touching the function body | Stack traces get noisier — an error inside `wrapper` obscures the original call site |
| Reusable across many functions with zero duplication | Debugging requires understanding closures — a real barrier for less experienced reviewers |
| Composable — multiple decorators stack cleanly | Stacking order matters and is easy to get wrong |

## 4. "What are the two ways to build a context manager, and what does `__exit__`'s return value control?"

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

**Answer:** A class with `__enter__`/`__exit__`, or (simpler, most of
the time) a generator wrapped in `@contextmanager`. The point is
deterministic cleanup — `finally` runs whether the block succeeded or
raised.

**The part people miss:** `__exit__` returning `True` **swallows** an
exception raised inside the `with` block instead of propagating it.
Rarely what you actually want — know it's there because interviewers
specifically probe this.

**Where you'd actually use this:** `with transaction.atomic():`,
file/socket handling, temporarily overriding a setting in a test.

| Pros | Cons / Trade-offs |
|---|---|
| Cleanup always runs, even on exception — no forgotten `f.close()` | `@contextmanager` generators can be tricky to debug if an exception crosses the `yield` |
| `with` blocks make resource lifetime visible at the call site | A class-based version needs two extra methods for what a `finally` block could do inline |
| Composable — multiple resources nest cleanly (`with a, b:`) | Swallowing exceptions via `__exit__` returning `True` is an easy, hard-to-spot bug |

## 5. "Explain the GIL. Then explain why threads still help I/O-bound code despite it."

**Answer:** The GIL is a single mutex in CPython that prevents more than
one thread from executing Python bytecode at a time. Threads still help
I/O-bound work because a thread **releases** the GIL while blocked on
I/O (network call, file read, DB query) — another thread runs during
that wait. CPU-bound work gets no benefit from threads at all, since
only one thread can be *executing* Python at any instant no matter how
many exist.

**If asked to demonstrate it live:** run the same CPU-bound loop three
ways — sequential, threaded, multiprocessed. Threaded comes out roughly
equal to sequential (no real parallelism gained); multiprocessed
actually scales, because separate processes each get their own GIL.

**The one-liner to lead with:** "threads for I/O-bound, processes for
CPU-bound" — then be ready to explain *why*, not just recite it.

| Pros of the GIL's existence | Cons / Trade-offs |
|---|---|
| Simplifies CPython's internals — no fine-grained locking on every object | Wastes multi-core hardware for CPU-bound pure-Python code |
| Makes single-threaded code fast — no lock overhead per operation | Real parallelism needs multiprocessing or a native extension that releases it |
| C extensions can release it during I/O/blocking calls for real concurrency | A frequent source of confusion — many candidates think threads never help at all |

## 6. "A Django view calling three third-party APIs is slow. Walk me through fixing it."

```python
import asyncio

async def fetch_async(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    tasks = [fetch_async(session, url) for url in urls]
    results = await asyncio.gather(*tasks)  # all concurrent, one thread
```

**Answer:** If the calls are sequential — awaiting each one in turn —
they're slow because the total time is the *sum* of three round trips
instead of the *max*. `asyncio.gather` (or a thread pool, in sync
Django) runs them concurrently instead.

**Likely follow-up — "when would you reach for threading or
multiprocessing instead of asyncio here?"** Decision rule: mostly
network-bound → AsyncIO. Must call a blocking library with no async
client → thread pool around the blocking calls. CPU-dominated (parsing,
number-crunching, ML inference) → multiprocessing, sized to core count.
Never run CPU work directly inside an async event loop — it blocks
*every* other task on that loop, not just the one doing the work.

| Pros | Cons / Trade-offs |
|---|---|
| AsyncIO: thousands of concurrent tasks on one thread, low memory overhead | AsyncIO: one blocking or CPU-heavy call stalls the entire event loop |
| Threading: works with existing blocking libraries with minimal code changes | Threading: no real CPU parallelism due to the GIL — bounded scalability (hundreds, not thousands) |
| Multiprocessing: true parallel CPU execution, bypasses the GIL entirely | Multiprocessing: higher memory/startup cost, and data must be pickled across process boundaries |

## 7. "How would you process a file too large to fit in memory?"

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

## 8. "Implement an LRU cache. What data structures does it need, and why both?"

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

## 9. "When do you reach for Celery instead of just handling something in the request?"

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

**Answer:** Anything slow or non-critical to the immediate HTTP response
— sending an email, processing an upload, calling a slow third-party
API — moves out of the request/response cycle into a task, backed by
Redis or RabbitMQ. `.delay()` queues it; a separate worker process picks
it up.

**Likely follow-up — "what breaks if this task runs twice?"** Retries
mean it can. Add an idempotency key so a retried task doesn't
double-process — "charge the customer twice" is the textbook version of
this bug.

| Pros | Cons / Trade-offs |
|---|---|
| Request/response stays fast — slow work doesn't block the HTTP response | Adds infrastructure (a broker, worker processes) that can itself fail or fall behind |
| Built-in retry/backoff for transient failures | Retries mean tasks can run more than once — must be designed idempotent |
| Workers scale independently from web servers | Debugging is harder — failures happen out-of-band, not in the request that triggered them |

---

## Code Samples

Runnable examples for the typing/async material above, in
`code_samples/chapter-1/`:

- `typing/generic_document_processing.py`, `typing/protocol_crawling_system.py`, `typing/type_driven_api.py`
- `asyncio/event_loop_optimization.py`, `asyncio/concurrency_benchmark.py`, `asyncio/async_legal_crawler.py`

```bash
pip install aiohttp pydantic fastapi requests uvloop
python code_samples/chapter-1/typing/generic_document_processing.py
mypy code_samples/chapter-1/ --config-file code_samples/chapter-1/config/mypy.ini
```

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

Default arguments are evaluated **once, at function definition time**,
not on each call. `items=[]` creates a single list object bound to the
parameter default, and it persists (and gets mutated) across every call
that doesn't pass its own `items` — it's not "reusing the parameter
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
