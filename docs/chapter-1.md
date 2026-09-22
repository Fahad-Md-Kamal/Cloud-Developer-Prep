---
title: "Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)"
---

# Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)

Advanced Python for senior backend roles: type systems, async programming,
memory management, and concurrency — the mechanics interviewers expect
you to explain, not just use.

## Learning Objectives

- Design type-safe APIs with generics and Protocols
- Build high-performance async applications with proper event-loop hygiene
- Process large datasets without blowing the memory budget
- Write thread-safe concurrent code and know when *not* to use threads
- Profile and optimize instead of guessing

---

## 1. Advanced Type System Mastery

Type hints aren't optional decoration on a large codebase — they're what
lets a team refactor with confidence instead of dread. Beyond `List`,
`Dict`, `Optional`, this section covers generics, Protocols, and the MyPy
config that makes strict typing actually adoptable on an existing
codebase.

### 1.1 Generic Types

```python
from typing import TypeVar, Generic, List
T = TypeVar('T')

class APIResponse(Generic[T]):
    def __init__(self, data: T, status: int):
        self.data = data
        self.status = status

user_response = APIResponse[User](user_data, 200)
document_response = APIResponse[List[Document]](docs, 200)
```

`TypeVar` creates a placeholder type; `Generic[T]` lets a class parameterize
over it. Bounded TypeVars (`TypeVar('T', bound=BaseModel)`) restrict what
can fill that placeholder — prefer them, or a Protocol, over an unbounded
`TypeVar` or `Any` in a public interface, since both hide errors that
generics exist to catch. Variance (covariant/contravariant/invariant)
governs whether `Container[Dog]` can substitute for `Container[Animal]` —
worth knowing exists, rarely worth hand-annotating outside library code.

**Practical checklist:** surface types at boundaries (request/response
models, repository interfaces, SDK wrappers); keep type aliases and
Protocols in one `types.py` to avoid import cycles; gate new/changed
modules with `mypy --strict` while legacy code stays permissive; add a
regression test whenever tightening a type, since the type checker alone
doesn't prove behavior didn't change.

**Interview signal:** have one real story ready — a refactor (e.g.
swapping a storage backend) where generics caught a regression before it
shipped, and how you verified safety with types *plus* tests, not types
alone.

### 1.2 Protocols (Structural Typing)

```python
from typing import Protocol

class Crawlable(Protocol):
    def fetch_content(self, url: str) -> str: ...
    def extract_links(self, content: str) -> List[str]: ...

class WebCrawler: ...  # satisfies Crawlable by having the right methods
class APICrawler: ...  # so does this, no inheritance needed
```

A Protocol defines "anything with these methods counts" instead of
"anything that inherits from this class" — duck typing with a type
checker's backing. Mark one `@runtime_checkable` only when you actually
need `isinstance()` checks (e.g. validating a plugin at load time); keep
Protocols small, since a large one usually means missing composition and
makes tests brittle. Reach for a Protocol over inheritance when adapting
between interchangeable implementations (swapping `aiohttp` for `httpx`,
for instance) — it lets both coexist without a shared base class.

### 1.3 MyPy Configuration for an Existing Codebase

```ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True

[mypy-external_lib.*]
ignore_missing_imports = True

[mypy-legacy_module]
check_untyped_defs = False
```

The real skill isn't the config syntax, it's the rollout plan: turn on
`strict = True` for new modules, then progressively widen the strict set
directory by directory rather than flipping it repo-wide. Track
`--warn-unused-ignores` to catch stale `# type: ignore` comments rotting
in the codebase, and budget cleanup time for it every sprint or it never
happens. Add stubs (`stubgen`, `types-<package>`) for third-party
libraries instead of reaching for a blanket `ignore_missing_imports`,
which silently swallows real type errors from that dependency too. Run
it as a fast pre-merge CI check, not a nightly job nobody looks at.

### 1.4 Type-Driven API Design

```python
from pydantic import BaseModel
from typing import Literal

class DocumentRequest(BaseModel):
    doc_type: Literal["statute", "regulation", "case"]
    jurisdiction: str
    max_results: int = 100

def search_documents(request: DocumentRequest) -> List[Document]:
    return search_engine.query(request.doc_type, request.jurisdiction)
```

Pydantic models, `TypedDict`, `Literal`, and `Enum` all push validation
to the boundary instead of scattering `if` checks through business
logic — the API contract becomes explicit, verifiable, and the source
for auto-generated docs (OpenAPI/Swagger) and typed client libraries.

**Change management:** version request/response models explicitly;
deprecate a field with `Optional[...]` plus a stated sunset date rather
than silently dropping it; encode business invariants (mutually
exclusive fields, etc.) in validators instead of ad-hoc downstream
checks; standardize error responses (problem+json, typed/machine-
actionable codes) and run contract tests against previous model
snapshots before releasing a breaking change.

---

## 2. AsyncIO and Concurrency

AsyncIO handles thousands of concurrent I/O-bound operations on a single
thread by cooperatively yielding at `await` points instead of blocking.
Knowing when it's the right tool — and when threads or processes are —
matters more than knowing the syntax.

### 2.1 Event Loop Optimization

```python
import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

async def main():
    tasks = [fetch_url(url) for url in urls]
    await asyncio.gather(*tasks)
```

`uvloop` is close to a drop-in replacement for the default event loop and
typically runs 2–4x faster with lower per-connection memory overhead —
reach for it in production before considering a custom loop.

**Operational guardrails:** set explicit timeouts (connect/read/total)
and cancellation points (`asyncio.wait_for`) so nothing hangs
indefinitely; propagate request/tenant IDs through `contextvars` for
traceability across awaits; apply backpressure with bounded queues and
jittered, 429-aware retries; instrument the loop itself — track slow
callbacks (`loop.slow_callback_duration`) and event-loop lag, since a
blocked loop degrades *everything* running on it, not just one task.

### 2.2 AsyncIO vs. Threading vs. Multiprocessing

```python
# AsyncIO -- I/O-bound (network calls)
async def fetch_async(session, url):
    async with session.get(url) as response:
        return await response.text()

# Threading -- mixed or blocking-library workloads
def fetch_threaded(url):
    return requests.get(url).text

# Multiprocessing -- CPU-bound work
def process_document(doc_text):
    return heavy_nlp_analysis(doc_text)
```

**Decision rule:** mostly network-bound with a couple of small CPU steps
→ AsyncIO with bounded semaphores. Must call a blocking library (a DB
driver or legacy SDK with no async variant) → thread pool around the
blocking calls, or migrate to an async-native client. CPU-dominated work
(tokenization, embeddings, PDF parsing) → multiprocessing, sized to core
count. Never block the event loop with CPU work directly — isolate it
behind `run_in_executor` or a separate service.

Rough characteristics: memory and startup cost both go AsyncIO < Threading
< Multiprocessing; scalability goes the other way (AsyncIO to thousands
of concurrent tasks, threading to hundreds, multiprocessing bound by
core count).

**Threading, GIL-aware:** use `ThreadPoolExecutor` for blocking I/O, not
CPU work — the GIL means threads don't parallelize CPU-bound Python.
Keep the pool bounded (`min(32, 5*cpu_count)` as a starting point) and
measure context-switch overhead before tuning further. Protect shared
state with locks or, better, avoid sharing mutable state at all — pass
copies.

**Multiprocessing, GIL bypass:** `ProcessPoolExecutor` sized to cores,
with headroom left for the OS. Choose the start method deliberately —
`spawn` is safer (and the default on macOS/Windows), `fork` is faster on
Linux but riskier around copy-on-fork state, `forkserver` avoids that
risk while keeping most of the speed. Minimize what gets pickled across
the process boundary; share large read-only data via
`multiprocessing.shared_memory` instead of copying it into every worker.

### 2.3 Async Crawlers and API Clients

```python
import asyncio
import aiohttp
from asyncio import Semaphore

class AsyncCrawler:
    def __init__(self, max_concurrent=10):
        self.semaphore = Semaphore(max_concurrent)

    async def crawl(self, url):
        async with self.semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()
```

A semaphore caps in-flight requests so you don't overwhelm the target
server or your own connection pool. Reuse the `ClientSession` across
requests rather than creating one per call — that's what actually gives
you connection pooling.

**Production blueprint:** per-domain timeouts and rate limits plus a
global concurrency cap; normalize failures (DNS, TLS, 4xx/5xx) into
typed categories with their own retry/backoff policy rather than one
generic retry-everything rule; persist a crawl manifest (URL, status,
attempt count, checksum) so a crash doesn't mean starting over; sample
content hashes to catch soft bans or mirrored/duplicate content early;
ship p95 latency, success rate, and queue depth as metrics, not just logs.

---

## 3. Memory Management and Optimization

### 3.1 Python's Memory Model

```python
# Bad: loads the whole file into memory
# with open(filename) as f:
#     return [process_line(line) for line in f]

# Good: generator, one line at a time
def process_large_file(filename):
    with open(filename) as f:
        for line in f:
            yield process_line(line)

class Document:
    __slots__ = ['id', 'title', 'content']  # ~40% less memory per instance
    def __init__(self, id, title, content):
        self.id, self.title, self.content = id, title, content
```

CPython uses reference counting as the primary reclaim mechanism, with a
generational cycle collector as backup for reference cycles a simple
refcount can't resolve. Generators, `itertools`, appropriately-chosen
collections (`deque`, `Counter`), and `__slots__` are the everyday levers
for keeping memory bounded.

**Where leaks actually come from in review:** unbounded caches/dicts
keyed by user input with no eviction; a global list quietly accumulating
references from background tasks; reference cycles in long-lived objects
that define `__del__`; a large pandas/NumPy intermediate kept alive by a
lingering reference in a notebook or REPL session.

### 3.2 Memory Profiling

```python
import tracemalloc

def analyze_memory():
    tracemalloc.start()
    data = [i**2 for i in range(10000)]
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current: {current / 1024 / 1024:.2f} MB")
    print(f"Peak: {peak / 1024 / 1024:.2f} MB")
    tracemalloc.stop()
```

`tracemalloc` is built in and enough for most cases; `memory_profiler`
gives line-by-line numbers when you need to localize a hotspot;
`objgraph` answers "what's still holding a reference to this" via
`show_backrefs`, which is usually the actual question once you already
know *something* is leaking. Compare `tracemalloc` snapshots over time
rather than a single reading, and treat memory as a budget (e.g. peak MB
per request) enforced in tests, not just watched in production after
the fact.

### 3.3 Memory-Efficient Data Structures

```python
import array
import numpy as np
from collections import deque

numbers_list = [1, 2, 3, 4, 5] * 100000        # ~3.8 MB
numbers_array = array.array('i', [1, 2, 3, 4, 5] * 100000)  # ~1.9 MB
data = np.array([1, 2, 3, 4, 5] * 100000, dtype=np.int32)   # tightest

queue = deque(maxlen=1000)  # bounded, auto-evicts oldest
```

For numeric data, a typed `array.array` or NumPy array beats a plain
list by roughly half the memory, since a Python list stores pointers to
boxed objects rather than the raw values. `__slots__` and
`dataclasses(slots=True)` cut per-instance overhead for classes with a
fixed, known set of fields — skip both if you need dynamic attributes or
multiple inheritance, since `__slots__` complicates both. Memory-map
large read-mostly files (`mmap`) instead of loading them whole; prefer
vectorized NumPy operations over Python-level loops for numeric work;
batch and serialize to a compact format (e.g. msgpack) before caching.

---

## 4. Concurrent Programming Patterns

### 4.1 Thread Safety

```python
import threading
from queue import Queue

class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._value += 1

    @property
    def value(self):
        return self._value

task_queue = Queue()  # already thread-safe
```

`Lock` for mutual exclusion, `RLock` when the same thread needs to
re-acquire a lock it already holds, `Semaphore` to cap concurrent access
to a limited resource, `Condition`/`Event` for thread coordination and
signaling. Prefer eliminating the need for synchronization in the first
place — immutable objects, thread-local storage, or queue-based
message-passing — over adding more locks.

**Deadlock avoidance:** pick a lock-acquisition order and never violate
it; use `lock.acquire(timeout=...)` instead of blocking forever, and log
on contention; when debugging a stuck process,
`faulthandler.dump_traceback_later` or `threading.enumerate()` with
stack dumps will show you exactly where threads are stuck.

### 4.2 Producer-Consumer with `asyncio.Queue`

```python
import asyncio

async def producer(queue, urls):
    for url in urls:
        await queue.put(url)
    await queue.put(None)  # sentinel: signal completion

async def consumer(queue):
    while True:
        url = await queue.get()
        if url is None:
            break
        await fetch_and_process(url)
        queue.task_done()

queue = asyncio.Queue(maxsize=100)  # bounded -- prevents unbounded memory growth
asyncio.create_task(producer(queue, urls))
asyncio.create_task(consumer(queue))
```

A bounded queue is what actually provides backpressure — an unbounded
one just moves the memory problem from "too many open connections" to
"too many queued items." On shutdown, drain gracefully: send sentinels,
`await queue.join()`, then cancel anything still outstanding rather than
killing tasks mid-work. Emit queue depth and item age as metrics; page
when either breaches its SLO, since a growing queue is usually the
earliest visible sign of a downstream slowdown.

### 4.3 Distributed Tasks with Celery

```python
from celery import Celery

app = Celery('document_processor', broker='redis://localhost:6379')

@app.task(bind=True, max_retries=3)
def process_document(self, doc_id, doc_content):
    try:
        result = analyze_document(doc_content)
        return {'doc_id': doc_id, 'analysis': result}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)

for i, doc in enumerate(documents):
    process_document.delay(i, doc.content)
```

Celery distributes work across processes/machines with built-in retry
and result tracking — the production concerns are less about the
decorator syntax and more about operational discipline: isolate
latency-sensitive queues from batch work so one doesn't starve the
other; set per-task-type visibility timeouts and a retry cap (unbounded
retries turn a transient failure into a storm); add an idempotency key
to each task so a retry can't double-process; monitor broker health
(Redis/RabbitMQ), worker memory, and task success rate, and scale
workers conservatively rather than reactively.

---

## Quick-Fire Interview Drills

Short, common senior-level prompts — practice explaining and coding each
one cold.

**LRU Cache.** `functools.lru_cache(maxsize=128)` for the fast path; know
`cache_info()` to talk about hit rates. From scratch: a hash map for O(1)
lookup plus a doubly linked list for O(1) eviction/move-to-front.

```python
import functools

@functools.lru_cache(maxsize=128)
def get_user_data(user_id: int) -> dict:
    return db.fetch_user(user_id)

get_user_data(123)
get_user_data(123)  # cache hit
print(get_user_data.cache_info())
```

**Mixins vs. decorators.** A mixin is a thin, single-purpose behavior
(logging, serialization) composed into a concrete class to avoid deep
inheritance chains. A parameterized decorator nests three levels —
`outer(args) -> decorator(func) -> wrapper(*a, **kw)` — know that shape
cold, and be ready to explain the closure that makes `args` visible
inside `wrapper`.

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

**Descriptor protocol.** Any object defining `__get__`/`__set__`/
`__delete__` customizes attribute access on the class that holds it —
this is the mechanism underneath `@property`, bound methods, and
`@classmethod`/`@staticmethod`. The interview hook: bound methods work
because functions are themselves descriptors, binding `self` via
`__get__`.

**Context managers.** Two ways to build one: a class with
`__enter__`/`__exit__`, or a generator wrapped in
`contextlib.contextmanager`. The point is deterministic cleanup (files,
sockets, DB transactions) — know that `__exit__`'s return value controls
whether an exception raised inside the `with` block propagates or is
suppressed.

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

**GIL.** A mutex preventing more than one thread from executing Python
bytecode at a time. Threads still help I/O-bound work (they release the
GIL during I/O waits); CPU-bound work needs multiprocessing or a native
extension that releases the GIL. A good live demo: the same CPU-bound
loop run sequentially, then threaded, then multiprocessed — threaded
comes out roughly equal to sequential, multiprocessed actually scales.

**Memory & `__slots__`.** Reference counting frees most objects
immediately and deterministically; the generational GC only needs to
step in for reference cycles. For leak debugging,
`gc.get_objects()`/`get_referrers()` plus `tracemalloc` snapshots
localize the allocation site. `__slots__` trades away dynamic attributes
and complicates multiple inheritance in exchange for real memory savings
at scale — worth it for high-volume, fixed-shape objects, not worth it
for everything.

---

## Code Samples

Runnable, self-contained examples for the concepts above live under
`code_samples/chapter-1/`:

| Area | Files |
|---|---|
| Typing | `typing/generic_document_processing.py`, `typing/protocol_crawling_system.py`, `typing/type_driven_api.py` |
| AsyncIO | `asyncio/event_loop_optimization.py`, `asyncio/concurrency_benchmark.py`, `asyncio/async_legal_crawler.py` |
| Config | `config/mypy.ini` |

```bash
pip install aiohttp beautifulsoup4 pydantic fastapi requests psutil uvloop numpy

python code_samples/chapter-1/typing/generic_document_processing.py
python code_samples/chapter-1/asyncio/event_loop_optimization.py

mypy code_samples/chapter-1/ --config-file code_samples/chapter-1/config/mypy.ini
```

---

## Summary

1. **Type systems** — generics, Protocols, a staged MyPy rollout, and
   type-driven API design push validation to the boundary and make
   large-codebase refactors safe.
2. **AsyncIO** — the right tool for thousands of concurrent I/O-bound
   operations; know when threading or multiprocessing is the better
   call instead.
3. **Memory** — generators, `__slots__`, typed arrays, and actually
   profiling before optimizing keep long-running processes stable.
4. **Concurrency** — thread safety, bounded producer-consumer queues,
   and distributed task queues (Celery) for scaling past one process.

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
