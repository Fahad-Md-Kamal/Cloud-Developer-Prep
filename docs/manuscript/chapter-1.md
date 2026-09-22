---
title: "Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)"
---

<!--  -->

# Chapter 1: Modern Python Mastery (Typing, AsyncIO, Memory, Concurrency)

Master advanced Python concepts essential for senior backend engineering roles at scale. This chapter covers type systems, asynchronous programming, memory optimization, and concurrency patterns critical for both Lawstronaut's legal data crawling infrastructure and Optimizely's AI-powered backend systems.

## Learning Objectives

- Design type-safe APIs with advanced typing patterns and generics
- Build high-performance async applications with event loop optimization
- Implement memory-efficient data processing for large-scale systems
- Create thread-safe concurrent applications with proper synchronization
- Profile and optimize Python applications for production workloads

---

## 1. Advanced Type System Mastery

In modern Python engineering, **type systems are not just optional safety nets** — they are the backbone of scalable, maintainable, and reliable enterprise codebases. This section focuses on building a deep understanding of Python's advanced typing ecosystem and its strategic role in large-scale backend systems like those at Optimizely or Lawstronaut.

You'll learn how to **design type-safe APIs**, **build robust data models**, and **detect logical inconsistencies at compile time**, long before they surface in production. Beyond the basics of `List`, `Dict`, and `Optional`, this section dives into **generic types**, **protocols**, and **runtime type introspection** — the key ingredients of clean, flexible, and refactor-friendly backend architectures.

### 1.1 Generic Types and Advanced Typing Patterns

**Generic types** enable you to write flexible, reusable code while maintaining type safety. They're essential for building robust API clients, data processing pipelines, and service layers.

```python
# Quick example: Generic API response handler
from typing import TypeVar, Generic, List
T = TypeVar('T')

class APIResponse(Generic[T]):
    def __init__(self, data: T, status: int):
        self.data = data
        self.status = status

# Usage: Type-safe for different response types
user_response = APIResponse[User](user_data, 200)
document_response = APIResponse[List[Document]](docs, 200)
```

**Key Concepts:**

- **TypeVar**: Creates type variables for generic functions and classes
- **Generic**: Base class for generic types that can work with multiple data types
- **Bounded TypeVars**: Restrict generic types to specific base classes or protocols
- **Variance**: Control how generic types relate to their type arguments (covariant, contravariant, invariant)

**Benefits for Enterprise Systems:**
- **Code Reusability**: Write once, use with multiple types safely
- **API Consistency**: Ensure consistent interfaces across different data types
- **Refactoring Safety**: Type checker catches breaking changes during refactoring
- **Documentation**: Types serve as living documentation for complex systems

**Common Pitfalls (to avoid in reviews/interviews):**
- Using `Any` or unbounded `TypeVar` in public interfaces hides errors; prefer bounded types or Protocols
- Generic classes without variance annotations can block safe substitution; mark containers `covariant` where appropriate
- Overusing inheritance instead of composition/Protocols leads to fragile hierarchies

**Practical Checklist:**
- Surface types at the boundary: request/response models, repository interfaces, external SDK wrappers
- Keep type helpers colocated: `types.py` for aliases and Protocols to prevent import cycles
- Gate merges with `mypy --strict` on new/modified modules while keeping legacy areas permissive
- Add targeted regression tests when tightening types to ensure no behavior drift

**Interview Signals:** Be ready to discuss how generics reduced regressions during a refactor (e.g., swapping a storage backend) and how you proved safety via type checks plus integration tests.

**Scenario**: At Lawstronaut, you need to process different types of legal documents (statutes, regulations, case law) while maintaining type safety across your document processing pipeline. Generic types allow you to create a unified processing framework that works with any document type while preserving specific type information.

### 1.2 Advanced Protocol Usage

**Protocols** define structural typing (duck typing with type checking). They're crucial for building flexible, testable interfaces in large-scale systems.

```python
# Quick example: Protocol for crawlable data sources
from typing import Protocol

class Crawlable(Protocol):
    def fetch_content(self, url: str) -> str: ...
    def extract_links(self, content: str) -> List[str]: ...

# Any class with these methods satisfies the protocol
class WebCrawler: ...  # implements fetch_content, extract_links
class APICrawler: ...  # implements fetch_content, extract_links
```

**Key Concepts:**

- **Structural Typing**: Objects are compatible if they have the required methods/attributes
- **Runtime Checkable**: Protocols can be used with `isinstance()` checks
- **Protocol Inheritance**: Protocols can extend other protocols
- **Generic Protocols**: Combine protocols with generic types for maximum flexibility

**Benefits for Scalable Systems:**
- **Interface Flexibility**: Multiple implementations can satisfy the same protocol
- **Testing**: Easy to mock and test different implementations
- **Extensibility**: New implementations can be added without changing existing code
- **Documentation**: Protocols clearly define expected behavior

**Runtime Guardrails:**
- Mark critical Protocols with `@runtime_checkable` when you need `isinstance` checks for plugin validation
- Keep Protocols lean; large ones signal missing composition and make tests brittle
- Prefer Protocols over inheritance for adapters (e.g., swapping `aiohttp` vs `httpx` clients)

**Scenario**: At Lawstronaut, your crawling system needs to handle different data sources (web pages, APIs, databases) through a unified interface. Protocols allow you to define common crawling behavior while supporting diverse implementations.

### 1.3 MyPy Configuration for Enterprise Codebases

**MyPy configuration** is critical for maintaining type safety across large codebases and ensuring consistent code quality across development teams.

```ini
# Quick example: mypy.ini for production
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

**Key Configuration Areas:**

- **Strictness Levels**: Configure how strict type checking should be
- **Per-Module Settings**: Different rules for different parts of your codebase
- **Third-Party Integration**: Handle libraries without type stubs
- **CI/CD Integration**: Automated type checking in build pipelines

**Production Configuration Strategy:**

**Core Settings:**
- Enable strict mode for new code while allowing gradual adoption
- Configure warnings to catch common type-related bugs
- Set up per-module overrides for legacy code migration
- Integrate with IDE for real-time feedback

**Benefits:**
- **Early Bug Detection**: Catch type-related errors before runtime
- **Refactoring Safety**: Confident code changes with type verification  
- **Documentation**: Types serve as always-current documentation
- **Team Consistency**: Enforced coding standards across the team

**Incremental Rollout Plan:**
- Start with `strict = True` on new modules; progressively add directories to strict mode
- Track `--warn-unused-ignores` to remove stale suppressions; budget time each sprint for cleanup
- Add stubs for third-party libs (`stubgen`, `types-<package>`) to avoid blanket `ignore_missing_imports`
- Integrate into CI as a fast pre-merge check and publish `mypy.html` reports for large refactors

### 1.4 Type-Driven API Design

**Type-driven API design** creates self-documenting, predictable interfaces that catch errors at compile time rather than runtime.

```python
# Quick example: Type-safe API endpoint
from pydantic import BaseModel
from typing import Literal

class DocumentRequest(BaseModel):
    doc_type: Literal["statute", "regulation", "case"]
    jurisdiction: str
    max_results: int = 100

def search_documents(request: DocumentRequest) -> List[Document]:
    # Type checker ensures request has correct structure
    return search_engine.query(request.doc_type, request.jurisdiction)
```

**Key Principles:**

- **Precise Types**: Use specific types rather than generic `Any` or `Dict`
- **Validation Integration**: Combine type hints with runtime validation
- **API Documentation**: Types automatically generate accurate API docs
- **Error Prevention**: Catch API misuse before deployment

**Modern Approaches:**
- **Pydantic Models**: Runtime validation with type hints
- **TypedDict**: Precise dictionary structures
- **Literal Types**: Exact string/number values
- **Enum Classes**: Controlled vocabulary for API parameters

**Benefits for Large Systems:**
- **Contract Clarity**: API contracts are explicit and verified
- **Breaking Change Detection**: Type checker catches API changes
- **Automatic Documentation**: OpenAPI/Swagger generation from types
- **Client Generation**: Type-safe client libraries from API definitions

**API Change Management:**
- Use versioned request/response models; deprecate fields via `Optional[...]` plus explicit sunset dates
- Encode business invariants in validators (e.g., mutually exclusive fields) instead of ad-hoc checks downstream
- Standardize error shapes (problem+json) and make them typed; return machine-actionable codes
- Backwards compatibility tests: run contract tests against previous model snapshots before releasing

---

## 2. AsyncIO and Concurrency

AsyncIO is fundamental to building high-performance Python applications that can handle thousands of concurrent connections efficiently. This section covers advanced AsyncIO patterns, event loop optimization, and when to choose AsyncIO over threading or multiprocessing.

### 2.1 Event Loop Optimization and Custom Event Loops

**Event loop optimization** is crucial for maximizing performance in async applications, especially for I/O-intensive workloads like web crawling and API processing.

```python
# Quick example: Using uvloop for better performance
import asyncio
import uvloop

# Install high-performance event loop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

async def main():
    # Your async code runs 2-4x faster
    tasks = [fetch_url(url) for url in urls]
    await asyncio.gather(*tasks)
```

**Key Concepts:**

- **Event Loop Selection**: Choosing between default asyncio and high-performance alternatives
- **Task Scheduling**: Understanding how the event loop schedules and executes tasks
- **Performance Monitoring**: Tracking event loop performance and bottlenecks
- **Custom Event Loops**: When and how to implement specialized event loops

**Performance Optimization Strategies:**

**uvloop Integration:**
- **Performance Boost**: 2-4x performance improvement over default asyncio
- **Production Ready**: Battle-tested in high-traffic applications
- **Drop-in Replacement**: Minimal code changes required
- **Memory Efficiency**: Lower memory overhead per connection

**Task Management:**
- **Connection Pooling**: Reuse connections to reduce overhead
- **Semaphore Limiting**: Control concurrent operations to prevent resource exhaustion  
- **Task Monitoring**: Track task execution times and failure rates
- **Graceful Degradation**: Handle overload scenarios properly

**Operational Guardrails:**
- Set explicit timeouts (connect/read/total) and cancellation points (`asyncio.wait_for`) to avoid hung tasks
- Propagate context (request IDs, tenant IDs) via `contextvars` for traceability
- Implement backpressure: bounded queues and 429-aware retry policies with jitter
- Instrument the loop: track slow callbacks (`asyncio.get_running_loop().slow_callback_duration`) and event loop lag metrics

**Scenario**: At Lawstronaut, you need to crawl millions of legal documents efficiently. Proper event loop optimization allows you to handle 1000+ concurrent connections while maintaining low memory usage and high throughput.

### 2.2 AsyncIO vs Threading vs Multiprocessing Trade-offs

**Choosing the right concurrency model** is critical for application performance and depends on your workload characteristics.

```python
# Quick comparison: Same task, different approaches

# AsyncIO - Best for I/O-bound (web requests)
async def fetch_async(session, url):
    async with session.get(url) as response:
        return await response.text()

# Threading - Good for mixed workloads
def fetch_threaded(url):
    return requests.get(url).text

# Multiprocessing - Best for CPU-bound tasks
def process_document(doc_text):
    return heavy_nlp_analysis(doc_text)  # CPU-intensive
```

**Decision Framework:**

**AsyncIO - Best for I/O-Bound Tasks:**
- **Web Crawling**: Downloading thousands of web pages
- **API Calls**: Making concurrent HTTP requests
- **Database Operations**: Concurrent database queries
- **File Operations**: Reading/writing multiple files

**Threading - Good for Mixed Workloads:**
- **Legacy Code**: Integrating with non-async libraries  
- **CPU + I/O**: Tasks that combine computation and I/O
- **Limited Concurrency**: When you need dozens, not thousands of threads

**Multiprocessing - Best for CPU-Bound Tasks:**
- **Data Processing**: Heavy computational work
- **Document Analysis**: Text parsing and analysis
- **Machine Learning**: Model inference and training
- **Cryptographic Operations**: Encryption/decryption tasks

**Performance Characteristics:**

- **Memory Usage**: AsyncIO < Threading < Multiprocessing
- **Startup Cost**: AsyncIO < Threading < Multiprocessing  
- **CPU Utilization**: Multiprocessing > Threading ≈ AsyncIO (for I/O)
- **Scalability**: AsyncIO (thousands) > Threading (hundreds) > Multiprocessing (cores)

**Scenario**: At Optimizely, your AI system needs to handle concurrent user requests (I/O-bound) while performing model inference (CPU-bound). A hybrid approach using AsyncIO for request handling and multiprocessing for model execution provides optimal performance.

**Decision Cheatsheet:**
- If workload is mostly network-bound with 1–2 small CPU steps: AsyncIO + bounded semaphores
- If you must call blocking libs (DB drivers, legacy SDKs): threads around the blocking calls, or move to async-native libraries
- If CPU dominates (tokenization, embeddings, PDF parsing): multiprocessing or offload to a worker pool; pin process count to core count
- Mix models carefully: never block the event loop; isolate CPU work behind `run_in_executor` or separate services

**Threading Deep Dive (GIL-aware):**
- Prefer `ThreadPoolExecutor` for blocking I/O; submit small CPU work only when it is cheaper than process spin-up
- Keep thread counts bounded (`min(32, 5*cpu_count)` as a starting point); measure context-switch overhead and tune
- Protect shared state with locks or immutable data; avoid sharing large mutable objects—pass copies or views
- Detect contention with profiling (`sys.setswitchinterval`, `faulthandler`, thread dump scripts) and simplify critical sections

**Multiprocessing Deep Dive (GIL bypass):**
- Use `ProcessPoolExecutor` or `multiprocessing.Pool` for CPU-bound tasks; size pool to cores and leave headroom for the OS
- Choose start method explicitly: `spawn` for safety (default on macOS/Windows), `fork` for speed on Linux, `forkserver` to avoid copy-on-fork hazards
- Minimize pickling overhead: send small, serializable inputs; reuse large read-only data via shared memory (`multiprocessing.shared_memory`) or memory-mapped files
- Capture worker failures and timeouts; wrap tasks to emit structured errors and make retries idempotent

### 2.3 Building Async Web Crawlers and API Clients

**High-performance async crawlers** are essential for large-scale data collection and processing systems.

```python
# Quick example: Async crawler with rate limiting
import asyncio
import aiohttp
from asyncio import Semaphore

class AsyncCrawler:
    def __init__(self, max_concurrent=10):
        self.semaphore = Semaphore(max_concurrent)
    
    async def crawl(self, url):
        async with self.semaphore:  # Limit concurrency
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()
```

**Architecture Principles:**

- **Rate Limiting**: Respect server limits and avoid being blocked
- **Error Handling**: Graceful failure handling and retry logic
- **Resource Management**: Efficient connection pooling and cleanup
- **Scalability**: Handle millions of URLs with bounded resource usage

**Key Components:**

**Connection Management:**
- **Session Reuse**: Persistent connections reduce overhead
- **Connection Limits**: Per-host and total connection limits
- **Timeout Configuration**: Prevent hanging connections
- **SSL/TLS Optimization**: Efficient certificate handling

**Content Processing:**
- **Streaming**: Process large responses without loading into memory
- **Content Type Detection**: Handle different document formats
- **Encoding Handling**: Proper text encoding detection and conversion
- **Link Extraction**: Efficient parsing of HTML/XML for crawling

**Monitoring and Observability:**
- **Performance Metrics**: Track throughput, error rates, response times
- **Progress Tracking**: Monitor crawling progress and completion
- **Resource Utilization**: Memory, CPU, and network usage
- **Error Classification**: Categorize and handle different error types

**Production Blueprint:**
- Budget timeouts per domain; implement per-host rate limits and global concurrency caps
- Normalize errors (DNS, TLS, 4xx/5xx) into typed categories with retry/backoff policies
- Store crawl manifests (URL, status, attempts, checksum) to enable resumable crawls
- Add sampling-based content hashing to detect soft bans or mirrored content
- Ship metrics (success rate, p95 latency, queue depth) and structured logs (URL, domain, attempt, duration)

---

## 3. Memory Management and Optimization

**Memory optimization** is crucial for processing large datasets and maintaining stable long-running applications, especially important for both legal document processing and AI systems.

### 3.1 Python Memory Model and Garbage Collection

**Understanding Python's memory model** helps you write memory-efficient applications and debug memory-related issues.

```python
# Quick example: Memory-efficient data processing
def process_large_file(filename):
    # Bad: Loads entire file into memory
    # with open(filename) as f:
    #     return [process_line(line) for line in f]
    
    # Good: Generator - processes one line at a time
    with open(filename) as f:
        for line in f:
            yield process_line(line)

# Using slots to reduce memory overhead
class Document:
    __slots__ = ['id', 'title', 'content']  # 40% less memory
    def __init__(self, id, title, content):
        self.id, self.title, self.content = id, title, content
```

**Core Concepts:**

- **Reference Counting**: Primary garbage collection mechanism
- **Cycle Detection**: Handling circular references  
- **Memory Pools**: How Python manages memory allocation
- **Object Lifecycle**: Creation, usage, and cleanup patterns

**Memory Management Strategies:**

**Efficient Data Structures:**
- **Generators**: Process data without loading everything into memory
- **Itertools**: Memory-efficient iteration patterns
- **Collections**: Choose appropriate data structures (deque, Counter, etc.)
- **Slots**: Reduce memory overhead for classes

**Memory Monitoring:**
- **Profile Memory Usage**: Track memory consumption patterns
- **Identify Leaks**: Find and fix memory leaks
- **Optimize Allocation**: Reduce unnecessary object creation
- **Monitor Growth**: Track memory usage over time

**Common Leak Sources (watch during incident reviews):**
- Caches without eviction; unbounded LRU or dicts keyed by user input
- Global lists holding references from background tasks
- Reference cycles in long-lived objects with `__del__` methods
- Large pandas/NumPy intermediates kept alive by lingering references in notebooks or REPLs

### 3.2 Memory Profiling Tools and Techniques

**Memory profiling** helps identify bottlenecks and optimize memory usage in production applications.

```python
# Quick example: Memory profiling with tracemalloc
import tracemalloc

def analyze_memory():
    tracemalloc.start()
    
    # Your code here
    data = [i**2 for i in range(10000)]
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current: {current / 1024 / 1024:.2f} MB")
    print(f"Peak: {peak / 1024 / 1024:.2f} MB")
    tracemalloc.stop()

# Line-by-line profiling with @profile decorator
@profile  # requires memory_profiler
def memory_intensive_function():
    data = list(range(1000000))  # Line 1: ~38 MB
    processed = [x * 2 for x in data]  # Line 2: ~76 MB
    return processed
```

**Profiling Tools:**

- **memory_profiler**: Line-by-line memory usage analysis
- **tracemalloc**: Built-in memory tracking
- **objgraph**: Object reference analysis
- **pympler**: Advanced memory analysis

**Profiling Strategies:**
- **Baseline Measurement**: Establish memory usage baselines
- **Hotspot Identification**: Find memory-intensive code sections
- **Growth Analysis**: Track memory usage over time
- **Leak Detection**: Identify and fix memory leaks

**Reading Profiler Output:**
- Look for retaining references: use `objgraph.show_backrefs` to find owners of unexpectedly-live objects
- Compare snapshots over time (`tracemalloc.take_snapshot`) to spot lines growing the most
- Treat memory budgets as SLOs (e.g., per-request peak MB); fail fast when exceeded in tests

### 3.3 Optimizing Data Structures for Memory Efficiency

**Data structure optimization** can dramatically reduce memory usage and improve performance.

```python
# Quick example: Memory-efficient data structures
import array
import numpy as np
from collections import deque

# Regular list vs array for numeric data
numbers_list = [1, 2, 3, 4, 5] * 100000  # ~3.8 MB
numbers_array = array.array('i', [1, 2, 3, 4, 5] * 100000)  # ~1.9 MB

# Deque for efficient append/pop operations
queue = deque(maxlen=1000)  # Automatically removes old items

# NumPy for numerical operations
data = np.array([1, 2, 3, 4, 5] * 100000, dtype=np.int32)  # Most efficient
```

**Optimization Techniques:**

**Array-Based Structures:**
- **NumPy Arrays**: Efficient numerical data storage
- **array.array**: Typed arrays for basic types
- **bytes/bytearray**: Efficient binary data handling
- **memoryview**: Zero-copy slicing operations

**Custom Classes:**
- **__slots__**: Reduce memory overhead
- **Property Optimization**: Lazy loading and caching
- **Weak References**: Avoid circular reference cycles
- **Flyweight Pattern**: Share immutable objects

**Additional Patterns:**
- Memory map large files (`mmap`) for read-mostly workloads; stream chunks through iterators
- Prefer vectorized NumPy operations over Python loops for heavy numeric work
- Use `dataclasses` with `slots=True` for light, typed models; avoid dict-based records in hot paths
- Batch DB fetches and serialize to compact formats (e.g., msgpack) when caching

**Scenario**: Processing millions of legal documents requires careful memory management. Using generators for document streaming, efficient data structures for metadata storage, and proper cleanup ensures your system can handle large datasets without memory issues.

---

## 4. Concurrent Programming Patterns

**Concurrent programming patterns** help you build thread-safe, scalable applications that can handle multiple operations simultaneously.

### 4.1 Thread-Safe Data Structures and Synchronization

**Thread safety** ensures your application works correctly when accessed by multiple threads simultaneously.

```python
# Quick example: Thread-safe operations
import threading
from queue import Queue
from collections import deque

# Thread-safe counter with lock
class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:  # Only one thread can modify at a time
            self._value += 1
    
    @property
    def value(self):
        return self._value  # Reading is atomic for simple types

# Thread-safe queue for producer-consumer
task_queue = Queue()  # Built-in thread safety
task_queue.put("task1")
task = task_queue.get()
```

**Synchronization Primitives:**

- **Locks**: Mutual exclusion for critical sections
- **RLocks**: Reentrant locks for nested locking
- **Semaphores**: Control access to limited resources
- **Conditions**: Coordinate between threads
- **Events**: Simple thread signaling

**Thread-Safe Patterns:**
- **Immutable Objects**: Eliminate need for synchronization
- **Thread-Local Storage**: Per-thread data isolation
- **Lock-Free Algorithms**: High-performance alternatives to locking
- **Queue-Based Communication**: Safe inter-thread messaging

**Deadlock Avoidance & Diagnostics:**
- Establish a lock ordering discipline and document it; never nest locks out of order
- Prefer time-bounded lock acquisition (`lock.acquire(timeout=...)`) and emit structured logs on contention
- For debugging, use `faulthandler.dump_traceback_later` or `threading.enumerate()` with stack dumps to spot stuck threads

### 4.2 Producer-Consumer Patterns with asyncio.Queue

**Producer-consumer patterns** are fundamental for building scalable async applications with proper work distribution.

```python
# Quick example: Async producer-consumer pattern
import asyncio

async def producer(queue, urls):
    """Add URLs to queue for processing"""
    for url in urls:
        await queue.put(url)
        print(f"Queued: {url}")
    
    # Signal completion
    await queue.put(None)

async def consumer(queue):
    """Process URLs from queue"""
    while True:
        url = await queue.get()
        if url is None:  # End signal
            break
        result = await fetch_and_process(url)
        queue.task_done()

# Usage
queue = asyncio.Queue(maxsize=100)  # Bounded queue
asyncio.create_task(producer(queue, urls))
asyncio.create_task(consumer(queue))
```

**Key Concepts:**

- **Bounded Queues**: Prevent memory exhaustion under load
- **Priority Queues**: Process high-priority items first
- **Multi-Producer/Consumer**: Scale processing across multiple workers
- **Backpressure**: Handle situations when consumers can't keep up

**Implementation Strategies:**
- **Queue Sizing**: Balance memory usage and throughput
- **Worker Scaling**: Dynamically adjust worker count
- **Error Handling**: Handle worker failures gracefully
- **Monitoring**: Track queue depth and processing rates

**Backpressure Patterns:**
- Apply per-consumer timeouts and retries; drop or park low-priority work during spikes
- Emit queue depth and age metrics; page when age or size breaches SLO
- Gracefully drain on shutdown: send sentinels, `queue.join()`, then cancel remaining tasks

### 4.3 Distributed Task Execution with Celery

**Distributed task execution** enables scaling beyond single-machine limitations and provides fault tolerance.

```python
# Quick example: Celery distributed tasks
from celery import Celery

app = Celery('document_processor', broker='redis://localhost:6379')

@app.task(bind=True, max_retries=3)
def process_document(self, doc_id, doc_content):
    try:
        # Heavy processing work
        result = analyze_legal_document(doc_content)
        return {'doc_id': doc_id, 'analysis': result}
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60, max_retries=3)

# Distribute work across multiple workers
for i, doc in enumerate(documents):
    process_document.delay(i, doc.content)
```

**Celery Fundamentals:**

- **Task Distribution**: Spread work across multiple machines
- **Result Storage**: Track task completion and results
- **Retry Logic**: Handle transient failures automatically
- **Monitoring**: Track task execution and performance

**Production Patterns:**
- **Task Routing**: Direct tasks to appropriate workers
- **Priority Queues**: Handle urgent tasks first
- **Resource Management**: Manage worker resources efficiently
- **Fault Tolerance**: Handle worker and broker failures

**Production Checklist:**
- Isolate critical queues; avoid cross-contamination between latency-sensitive and batch work
- Set visibility timeouts and retry policies per task type; cap max retries to avoid storms
- Add idempotency keys to tasks to make retries safe; log dedup hits
- Monitor broker health (Redis/RabbitMQ), worker memory, and task success rate; auto-scale conservatively

**Scenario**: At Lawstronaut, legal document processing tasks (parsing, analysis, storage) are distributed across multiple workers using Celery, enabling horizontal scaling and fault tolerance for the document processing pipeline.

---

## Interview Prep Alignment: Advanced Python Internals (Week 1)

These drills mirror common senior-level interview prompts and align with the weekly prep syllabus. Emphasize trade-offs, core mechanisms, and concise demos you can whiteboard or code live.

### LRU Cache (When and How)
- **Why**: Memoize expensive, pure functions (DB/API calls, heavy computation) to cut latency.
- **Built-in**: `functools.lru_cache(maxsize=128)` for the fastest path; discuss `cache_info()` to explain hit rates.
- **From-scratch pattern**: Hash map for O(1) lookups plus doubly linked list for O(1) eviction/move-to-front.

```python
import functools
import time

@functools.lru_cache(maxsize=128)
def get_user_data(user_id: int) -> dict:
    print(f"Fetching user {user_id} from DB...")
    time.sleep(1)
    return {"id": user_id, "name": "John Doe"}

get_user_data(123)
get_user_data(123)  # warm, hits cache
print(get_user_data.cache_info())
```

### Mixins and Decorators
- **Mixin role**: Thin, single-purpose behaviors (logging, serialization) composed into concrete classes to avoid deep inheritance.
- **Decorator with args**: Practice the triple-nesting pattern (`outer -> decorator -> wrapper`) and be ready to explain closure mechanics.

```python
import json

class ToJsonMixin:
    def to_json(self) -> str:
        return json.dumps(self.__dict__)

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

### Descriptor Protocol
- Objects defining `__get__`, `__set__`, or `__delete__` customize attribute access; this powers `@property`, bound methods, and `@classmethod/@staticmethod`.
- Interview hook: Explain how method binding works via the function descriptor’s `__get__`.

### Context Managers
- Two creation paths: class with `__enter__/__exit__` or generator with `contextlib.contextmanager`.
- Why: Deterministic cleanup for files, sockets, DB transactions; highlight exception handling via the `__exit__` return value.

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

### Global Interpreter Lock (GIL)
- Mutex prevents multiple threads executing Python bytecode simultaneously.
- Threads help I/O-bound workloads; CPU-bound work needs multiprocessing or native extensions.
- Demo: Run a CPU-bound loop sequentially, with threads, then with processes to show threads ≈ sequential while processes scale.

### Memory Management & `__slots__`
- Ref counting + generational GC: deterministic frees except for cycles; GC handles cycles in younger generations first.
- Leak debugging: `gc.get_objects()/get_referers()` and `tracemalloc` snapshots to pinpoint allocation sites.
- `__slots__` trade-offs: memory savings for many instances; no dynamic attrs; plan inheritance carefully.

### Idiomatic Constructs
- Prefer context managers for resources, generators for streaming large datasets, decorators for cross-cutting concerns (auth/logging/timing).
- Keep a concise timing decorator handy for perf discussions; use it to anchor “measure before optimize” answers.

---

## Code Examples and Implementations

This section provides comprehensive code examples demonstrating all the concepts covered in the theoretical sections above. All code examples have been organized into separate files for better maintainability and testing.

### Type System Examples

**Generic Document Processing System**
- File: `code_samples/chapter-1/generic_document_processing.py`
- Demonstrates: Generic types, TypeVar, Protocol usage, and type-safe repository patterns

**Protocol-Based Crawling System**
- File: `code_samples/chapter-1/protocol_crawling_system.py`
- Demonstrates: Runtime checkable protocols, structural typing, and flexible implementations

**Type-Driven API Design**
- File: `code_samples/chapter-1/type_driven_api.py`
- Demonstrates: Pydantic models, FastAPI integration, and comprehensive type validation

### AsyncIO Examples

**Event Loop Optimization**
- File: `code_samples/chapter-1/event_loop_optimization.py`
- Demonstrates: uvloop integration, connection pooling, and performance monitoring

**Concurrency Benchmarking**
- File: `code_samples/chapter-1/concurrency_benchmark.py`
- Demonstrates: Performance comparison between AsyncIO, threading, and multiprocessing

**Production Async Crawler**
- File: `code_samples/chapter-1/async_legal_crawler.py`
- Demonstrates: Production-ready web crawler with rate limiting, error handling, and statistics

### Memory Management Examples

**Memory Profiling and Optimization**
- File: `code_samples/chapter-1/memory_profiling.py`
- Demonstrates: tracemalloc usage, memory-efficient data structures, and optimization techniques

**Data Structure Optimization**
- File: `code_samples/chapter-1/data_structure_optimization.py`
- Demonstrates: Array-based structures, slots optimization, and memory-efficient patterns

### Concurrency Examples

**Thread-Safe Patterns**
- File: `code_samples/chapter-1/thread_safe_patterns.py`
- Demonstrates: Locks, semaphores, thread-safe data structures, and synchronization primitives

**Producer-Consumer with AsyncIO**
- File: `code_samples/chapter-1/async_producer_consumer.py`
- Demonstrates: asyncio.Queue, backpressure handling, and scalable worker patterns

**Distributed Task Processing**
- File: `code_samples/chapter-1/celery_distributed_tasks.py`
- Demonstrates: Celery task distribution, retry logic, and fault tolerance

### Running the Examples

```bash
# Install dependencies
pip install aiohttp beautifulsoup4 pydantic fastapi requests psutil uvloop numpy

# Run individual examples (when code files are created)
python code_samples/chapter-1/generic_document_processing.py
python code_samples/chapter-1/event_loop_optimization.py
python code_samples/chapter-1/concurrency_benchmark.py

# Type checking with MyPy
mypy code_samples/chapter-1/ --config-file code_samples/chapter-1/mypy.ini
```

### Code Organization

The code samples are organized by chapter:

```
code_samples/
└── chapter-1/
    ├── generic_document_processing.py
    ├── protocol_crawling_system.py
    ├── type_driven_api.py
    ├── event_loop_optimization.py
    ├── concurrency_benchmark.py
    ├── async_legal_crawler.py
    ├── memory_profiling.py
    ├── data_structure_optimization.py
    ├── thread_safe_patterns.py
    ├── async_producer_consumer.py
    ├── celery_distributed_tasks.py
    └── mypy.ini
```

Each file is self-contained and can be run independently to demonstrate specific concepts. The examples are specifically designed for interview scenarios at companies like Lawstronaut and Optimizely, focusing on real-world patterns used in production systems.

---

## Summary

This chapter covers the essential advanced Python concepts needed for senior backend engineering roles:

1. **Advanced Type Systems**: Generic types, protocols, MyPy configuration, and type-driven API design
2. **AsyncIO Mastery**: Event loop optimization, concurrency patterns, and high-performance web crawling
3. **Memory Optimization**: Understanding Python's memory model and optimization techniques
4. **Concurrent Programming**: Thread-safe patterns, producer-consumer systems, and distributed task execution

These concepts are specifically chosen to align with the requirements for both Lawstronaut (web crawling and data processing) and Optimizely (AI systems and high-performance APIs). The examples demonstrate production-ready patterns used in enterprise systems.

**Next Steps**: Practice implementing these patterns in your own projects, focusing on the specific areas most relevant to your target roles. Each concept builds upon the others to create a comprehensive foundation for advanced Python engineering.

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
