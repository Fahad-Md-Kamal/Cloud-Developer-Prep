---
title: "Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)"
---

# Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)

Nine focused topics, each one a thing interviewers actually ask a senior
Python candidate to explain or code. Each section stands alone — read
one, understand it, move on.

---

## 1. Type Hints & Generics

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class APIResponse(Generic[T]):
    def __init__(self, data: T, status: int):
        self.data = data
        self.status = status

user_response = APIResponse[User](user_data, 200)
```

`Generic[T]` lets a class or function work with any type while keeping
that type checkable — a repository class that works for `User`,
`Order`, or `Document` without losing type safety on each one.

**Where this actually shows up:** a generic `Repository[T]` base class
in a Django/FastAPI codebase, so `UserRepository` and `OrderRepository`
share CRUD logic without duplicating it or falling back to untyped
`Any`.

**Know this:** an unbounded `TypeVar` (or `Any`) in a public function
signature defeats the point — it hides exactly the errors typing exists
to catch. Bound it (`TypeVar('T', bound=BaseModel)`) when the generic
needs to call a specific method.

## 2. Protocols — Structural Typing

```python
from typing import Protocol

class Crawlable(Protocol):
    def fetch(self, url: str) -> str: ...

class WebCrawler:
    def fetch(self, url: str) -> str: ...  # satisfies Crawlable, no inheritance

class APICrawler:
    def fetch(self, url: str) -> str: ...  # so does this
```

A `Protocol` says "anything with this method counts," checked
structurally instead of by inheritance — duck typing with static
verification. This is how you type a function argument that accepts
"anything file-like" or "anything with a `.save()` method" without
forcing every caller through a shared base class.

**Where this actually shows up:** swapping HTTP clients (`requests` for
`httpx`) or mocking a dependency in a test — both work because they
satisfy the same Protocol, not because they inherit from anything.

## 3. Decorators

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

A parameterized decorator nests three levels:
`outer(args) → decorator(func) → wrapper(*a, **kw)`. Be able to draw
that shape cold, and explain *why* `wrapper` can still see `n` after
`repeat(3)` has already returned — it's a closure, `n` stays alive
because `wrapper` references it.

**Where this actually shows up:** `@login_required`, `@transaction.atomic`,
a `@retry(max_attempts=3)` around a flaky external API call, a timing
decorator wrapped around a slow endpoint during a perf investigation.

## 4. Context Managers

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

Two ways to build one: a class with `__enter__`/`__exit__`, or a
generator wrapped in `@contextmanager` (simpler for most cases). The
point is deterministic cleanup — the `finally` runs whether the block
succeeded or raised.

**Know this:** `__exit__`'s return value controls exception propagation
— return `True` and an exception raised inside the `with` block gets
swallowed instead of propagating. Rarely what you want; know it's there
because interviewers ask.

**Where this actually shows up:** DB transactions (`with
transaction.atomic():`), file/socket handling, temporarily overriding a
setting in a test.

## 5. The GIL

A single mutex preventing more than one thread from executing Python
bytecode at a time, in CPython specifically. Threads still help
I/O-bound work, because a thread releases the GIL while it's blocked on
I/O (a network call, a file read) — another thread runs during that
wait. CPU-bound work doesn't benefit from threads at all, since only one
thread can be *executing* Python at any instant regardless of how many
exist.

**The demo interviewers want:** the same CPU-bound loop run three ways —
sequential, threaded, multiprocessed. Threaded comes out roughly equal
to sequential (no real parallelism gained); multiprocessed actually
scales, because separate processes each have their own GIL.

**The one-line answer:** "threads for I/O-bound, processes for
CPU-bound" — then be ready to explain *why*, not just recite it.

## 6. AsyncIO vs. Threading vs. Multiprocessing

```python
# AsyncIO -- I/O-bound, one thread, thousands of concurrent tasks
async def fetch_async(session, url):
    async with session.get(url) as response:
        return await response.text()

# Threading -- blocking libraries with no async variant
def fetch_threaded(url):
    return requests.get(url).text

# Multiprocessing -- CPU-bound work, bypasses the GIL entirely
def process_document(doc_text):
    return heavy_nlp_analysis(doc_text)
```

**Decision rule:** mostly network-bound → AsyncIO. Must call a blocking
library with no async client → a thread pool around the blocking calls.
CPU-dominated (parsing, number-crunching, ML inference) →
multiprocessing, sized to core count. Never run CPU work directly inside
an async event loop — it blocks *every* other task on that loop, not
just the one doing the work.

```python
import asyncio

async def main():
    urls = [...]
    tasks = [fetch_async(session, url) for url in urls]
    results = await asyncio.gather(*tasks)  # all concurrent, one thread
```

**Where this actually shows up:** a Django view that calls three
third-party APIs sequentially is slow because it waits for each one in
turn; the same three calls under `asyncio.gather` (or a thread pool, in
sync Django) run concurrently instead — the classic "why is this
endpoint slow" interview follow-up.

## 7. Memory: Generators & `__slots__`

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


class Document:
    __slots__ = ['id', 'title', 'content']  # no per-instance __dict__
    def __init__(self, id, title, content):
        self.id, self.title, self.content = id, title, content
```

A generator trades "have the whole result ready immediately" for
"produce one item at a time" — the right trade whenever the input might
be large (a big file, a paginated API, a DB cursor) and you don't need
everything in memory simultaneously. `__slots__` removes the per-instance
`__dict__` that a normal Python object carries, cutting memory
meaningfully for classes you instantiate a lot — at the cost of losing
dynamic attribute assignment.

**Know this exists, don't over-invest:** `tracemalloc` (built in) for
measuring where memory actually goes when something's using more than
expected — enough to name it in an interview; the deep profiling
tooling tour isn't interview material.

## 8. LRU Cache

```python
import functools

@functools.lru_cache(maxsize=128)
def get_user_data(user_id: int) -> dict:
    return db.fetch_user(user_id)

get_user_data(123)  # hits the DB
get_user_data(123)  # cache hit, no DB call
print(get_user_data.cache_info())
```

`functools.lru_cache` is the fast path for memoizing an expensive, pure
function (same input → same output, no side effects) — a DB lookup, a
slow computation. Know `cache_info()` exists to talk about hit rates.
From scratch, an LRU cache is a hash map (O(1) lookup) plus a doubly
linked list (O(1) move-to-front / eviction) — be ready to explain why
both pieces are needed, not just one.

## 9. Background Tasks: Celery

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

Anything slow or non-critical to the immediate HTTP response — sending
an email, processing an upload, calling a slow third-party API — moves
out of the request/response cycle and into a Celery task, backed by
Redis or RabbitMQ as the broker. `.delay()` queues it; a separate worker
process picks it up.

**Know this:** an idempotency key on the task matters once retries are
in play — `max_retries=3` means the task can run more than once, and
"process this payment twice" is a real bug class if the task isn't safe
to repeat.

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
