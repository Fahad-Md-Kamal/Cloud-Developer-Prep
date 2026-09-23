---
title: "Chapter 2: Clean Code, Design Patterns, and SOLID Principles"
---

# Chapter 2: Clean Code, Design Patterns, and SOLID Principles

SOLID, the design patterns that actually come up in senior interviews,
clean code standards, and legacy refactoring — each topic as a question
you should be able to answer cold, with the trade-offs named explicitly,
not just the upside.

---

## Part 1: SOLID Principles

### 1. Single Responsibility Principle (SRP)

**"What is SRP, and how do you know when a class violates it?"**

```python
class DocumentParser:
    def parse(self, content: str) -> ParsedDocument: ...

class DocumentValidator:
    def validate(self, doc: ParsedDocument) -> bool: ...

class DocumentStorage:
    def save(self, doc: ParsedDocument) -> str: ...
```

**Answer:** A class should have exactly one reason to change. The
practical test isn't counting methods — it's asking "if the business
requirement for parsing changes, does this class also change for an
unrelated reason like storage format?" If yes, it's doing too much.
Splitting `DocumentParser`/`DocumentValidator`/`DocumentStorage` means a
new storage backend never touches parsing logic.

| Pros | Cons / Trade-offs |
|---|---|
| Each piece is independently testable in isolation | More classes/files to navigate for a simple change |
| Different people/teams can own different concerns without stepping on each other | Over-applying it fragments trivial logic into needless indirection |
| A bug in one concern can't silently break an unrelated one | Requires more upfront thought about where boundaries actually are |

### 2. Open/Closed Principle (OCP)

**"Explain Open/Closed. How would you add a new crawler strategy without touching existing code?"**

```python
from abc import ABC, abstractmethod

class CrawlerStrategy(ABC):
    @abstractmethod
    def crawl(self, url: str) -> CrawlResult: ...

class WebCrawler:
    def __init__(self, strategy: CrawlerStrategy):
        self.strategy = strategy

    def process(self, url: str) -> CrawlResult:
        return self.strategy.crawl(url)

class JavaScriptCrawler(CrawlerStrategy): ...  # new capability, zero changes above
```

**Answer:** Open for extension, closed for modification — new behavior
comes from adding a new class that implements the existing interface,
not editing code that's already shipped and tested. `WebCrawler` never
changes when `JavaScriptCrawler` is added.

| Pros | Cons / Trade-offs |
|---|---|
| Existing, tested code stays untouched and stable | Requires designing the right abstraction *up front* — hard to retrofit cleanly |
| New features ship without re-testing the whole system | Too many extension points for things that never actually vary is wasted abstraction |
| Multiple teams can add strategies independently | Can obscure control flow — "which strategy runs?" isn't always obvious from the call site |

### 3. Liskov Substitution Principle (LSP)

**"Explain LSP with an example of a subclass that technically compiles but violates it."**

```python
class DocumentProcessor(ABC):
    @abstractmethod
    def process(self, content: str) -> ProcessedDocument: ...

# Violates LSP: narrows the contract by raising on inputs the base class accepts
class StrictProcessor(DocumentProcessor):
    def process(self, content: str) -> ProcessedDocument:
        if not content.strip():
            raise ValueError("empty content not supported")  # base never promised this
        return self._parse(content)
```

**Answer:** Subtypes must be substitutable for their base type without
the caller noticing — same accepted inputs, same guarantees, no
surprise exceptions the base type never advertised. `StrictProcessor`
above type-checks fine but breaks any code written against
`DocumentProcessor` that happily passes empty strings.

| Pros | Cons / Trade-offs |
|---|---|
| Code written against the base type keeps working when a new subtype ships | Genuinely hard to verify by reading code alone — needs contract tests |
| Enables safe polymorphism — callers don't need `isinstance` checks | Overly rigid contracts can force subclasses into awkward no-op implementations |
| Refactoring one implementation can't silently break callers using another | Violations often only surface at runtime, not compile/type-check time |

### 4. Interface Segregation Principle (ISP)

**"Why is one large 'God interface' worse than several small ones?"**

```python
from typing import Protocol

class Readable(Protocol):
    def read(self) -> str: ...

class Writable(Protocol):
    def write(self, data: str) -> None: ...

class DocumentReader:
    def __init__(self, source: Readable):  # doesn't know Writable even exists
        self.source = source
```

**Answer:** A client shouldn't be forced to depend on methods it never
calls. A single `DocumentStorage` interface with `read`, `write`,
`delete`, `search` forces every consumer — including one that only ever
reads — to depend on (and mock, in tests) the whole surface. Splitting
into `Readable`/`Writable` means `DocumentReader` only depends on
`read`.

| Pros | Cons / Trade-offs |
|---|---|
| Tests mock only what's actually used, not a whole fat interface | More interfaces to define and keep track of |
| A change to `write()` semantics can't accidentally affect a read-only consumer | Can fragment a genuinely cohesive interface into pieces that always travel together anyway |
| Makes a class's real dependencies visible from its constructor signature | Requires discipline — easy to let one interface creep back to "just add one more method" |

### 5. Dependency Inversion Principle (DIP)

**"How does DIP relate to dependency injection? Aren't they the same thing?"**

```python
class DocumentRepository(Protocol):
    async def save(self, doc: Document) -> str: ...

class DocumentService:
    def __init__(self, repo: DocumentRepository):  # depends on the abstraction
        self.repo = repo

# Wiring happens at the edge, not inside DocumentService
service = DocumentService(repo=PostgreSQLDocumentRepository())
```

**Answer:** They're related but not identical. **DIP** is the design
principle: high-level modules (`DocumentService`) shouldn't depend on
low-level details (`PostgreSQLDocumentRepository`) — both should depend
on an abstraction (`DocumentRepository`). **Dependency injection** is
one *technique* for achieving that — passing the concrete implementation
in from outside rather than constructing it internally. You can follow
DIP without a DI framework (plain constructor injection, like above); a
DI framework just automates the wiring.

| Pros | Cons / Trade-offs |
|---|---|
| Swap PostgreSQL for a test double or a different DB with zero changes to business logic | Adds a layer of indirection that can make "what actually runs" harder to trace |
| High-level policy code stays testable without a real database | Over-abstracting a dependency that will *never* realistically change is wasted ceremony |
| Different environments (dev/test/prod) wire different concrete implementations | Constructor signatures grow as dependencies accumulate — needs its own discipline |

### All Five Together

One example is worth more than five isolated snippets — here's a small
order-processing system where every SOLID principle is doing real work
at once, annotated inline:

```python
from abc import ABC, abstractmethod
from typing import Protocol


# --- S: Single Responsibility -----------------------------------------
# Each class has exactly one reason to change.
class Order:
    def __init__(self, order_id: str, total: float):
        self.order_id = order_id
        self.total = total


class OrderValidator:
    def validate(self, order: Order) -> bool:
        return order.total > 0


# --- O: Open/Closed -----------------------------------------------------
# New channels are added by subclassing -- OrderService below never changes.
class NotificationChannel(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...


class EmailChannel(NotificationChannel):
    def send(self, message: str) -> None:
        print(f"Email: {message}")


class SMSChannel(NotificationChannel):
    def send(self, message: str) -> None:
        print(f"SMS: {message}")


# --- L: Liskov Substitution ----------------------------------------------
# Works identically no matter which concrete NotificationChannel is passed --
# no isinstance checks, no channel-specific branching.
def notify_all(channels: list[NotificationChannel], message: str) -> None:
    for channel in channels:
        channel.send(message)


# --- I: Interface Segregation ---------------------------------------------
# OrderRepository only commits to the narrow Writable role -- callers that
# only need to persist data never see (or have to mock) a read/search API.
class Writable(Protocol):
    def write(self, data: str) -> None: ...


class OrderRepository:
    def write(self, data: str) -> None:
        print(f"Saving: {data}")


# --- D: Dependency Inversion ------------------------------------------------
# OrderService depends on abstractions (Writable, NotificationChannel),
# injected from outside -- it never constructs a concrete class itself.
class OrderService:
    def __init__(
        self,
        validator: OrderValidator,
        repo: Writable,
        channels: list[NotificationChannel],
    ):
        self.validator = validator
        self.repo = repo
        self.channels = channels

    def place_order(self, order: Order) -> None:
        if not self.validator.validate(order):
            raise ValueError("Invalid order")
        self.repo.write(f"Order {order.order_id}: ${order.total}")
        notify_all(self.channels, f"Order {order.order_id} placed")


# Usage -- OrderService knows nothing about email, SMS, or how orders
# are actually stored. Swap any piece without touching this class.
service = OrderService(
    validator=OrderValidator(),
    repo=OrderRepository(),
    channels=[EmailChannel(), SMSChannel()],
)
service.place_order(Order(order_id="1001", total=49.99))
```

---

## Part 2: Design Patterns

### Factory

**"When would you reach for a Factory instead of just calling the constructor directly?"**

```python
class ModelFactory:
    @staticmethod
    def create(provider: str, **config) -> ConversationModel:
        if provider == "openai":
            return OpenAIModel(api_key=config["api_key"])
        if provider == "claude":
            return ClaudeModel(api_key=config["api_key"])
        raise ValueError(f"Unknown provider: {provider}")
```

**Answer:** When *which* concrete class to instantiate depends on
runtime data (a config value, a feature flag, a request parameter) —
centralizing that decision means the `if/elif` chain lives in exactly
one place instead of scattered through the codebase.

| Pros | Cons / Trade-offs |
|---|---|
| One place to add a new provider/type — not N places | Just another layer of indirection if there's genuinely only ever one implementation |
| Fails fast with a clear error on an unknown/misconfigured type | The factory itself can become a dumping ground if left unmaintained |
| Easy to swap in a fake for tests | Doesn't help if construction logic itself is complex — consider a builder instead |

### Strategy

**"How is Strategy different from just an if/else inside one function?"**

```python
class ProcessingStrategy(ABC):
    @abstractmethod
    async def process(self, content: str) -> ProcessedDocument: ...

class DocumentProcessor:
    def __init__(self, strategy: ProcessingStrategy):
        self.strategy = strategy

    async def run(self, content: str) -> ProcessedDocument:
        return await self.strategy.process(content)
```

**Answer:** Functionally similar for two or three cases — the payoff
shows up as the number of variants grows, or when they need independent
testing/deployment. Each strategy is isolated, swappable at runtime, and
addable without editing a growing conditional.

| Pros | Cons / Trade-offs |
|---|---|
| Each algorithm variant is independently testable | Overkill for 2 stable, simple branches — a plain `if` is more readable |
| New variants added without touching existing ones (this is OCP in practice) | One more class per variant — real overhead if variants are trivial |
| Runtime-swappable, useful for A/B testing or per-tenant behavior | The "which strategy got picked" decision needs to live and be logged *somewhere* clear |

### Observer

**"What problem does Observer solve that a direct function call doesn't?"**

```python
class DocumentEventObserver(Protocol):
    async def on_processed(self, doc: Document) -> None: ...

class DocumentProcessor:
    def __init__(self):
        self.observers: list[DocumentEventObserver] = []

    async def process(self, content: str):
        doc = await self._process(content)
        for observer in self.observers:
            await observer.on_processed(doc)
```

**Answer:** When one event needs to trigger several independent,
unrelated reactions (analytics, billing, cache invalidation) and the
publisher shouldn't need to know any of them exist. A direct function
call would mean `DocumentProcessor` importing and calling analytics,
billing, and caching code directly — tight coupling to things that have
nothing to do with document processing.

| Pros | Cons / Trade-offs |
|---|---|
| Publisher stays decoupled from every consumer | Failure handling gets harder — does one failing observer block the rest? |
| New observers added without touching the publisher | Execution order between observers is often undefined/unreliable |
| Natural fit for cross-cutting concerns (logging, metrics, notifications) | Debugging "who reacted to this event" means hunting across the codebase |

### Repository

**"What does Repository actually abstract away, concretely?"**

```python
class DocumentRepository(Protocol):
    async def save(self, doc: Document) -> str: ...
    async def find_by_id(self, doc_id: str) -> Document | None: ...
```

**Answer:** The fact that "save a document" might mean a SQL `INSERT`
today and a call to Elasticsearch plus S3 tomorrow. Business logic calls
`repo.save(doc)` and never needs to know which storage technology is
behind it, or that it might be more than one.

| Pros | Cons / Trade-offs |
|---|---|
| Swap storage tech without touching business logic | Can turn into a leaky abstraction if storage-specific query needs keep bubbling up |
| Trivial to substitute an in-memory fake for unit tests | An extra layer for simple CRUD apps with one obvious backend can be unneeded ceremony |
| Centralizes error mapping (DB errors → domain errors) | Risk of becoming a "thin wrapper that adds nothing" if it just mirrors the ORM 1:1 |

---

## Part 3: Clean Code Practices

### Function & Class Design

**"What makes a function hard to review, independent of what it does?"**

**Answer:** Too many parameters (especially several of the same
primitive type, which is easy to pass in the wrong order), no type
hints (a reviewer has to infer shapes from usage), and doing more than
one thing (fetching *and* transforming *and* saving in one function body
means a bug fix in one concern risks touching the others).

| Pros of disciplined design | Cons / Trade-offs |
|---|---|
| Reviewable in isolation, without loading the whole module into your head | Takes real upfront design time most people skip under deadline pressure |
| Type hints double as always-current documentation | Excessive granularity (a function per line) hurts readability the other direction |
| Easy to unit test with clear inputs/outputs | Grouping related params into a dataclass adds a type to maintain |

### Error Handling & Exception Design

**"Design an exception hierarchy for a document processing pipeline. Why not just raise `Exception` everywhere?"**

```python
class DocumentProcessingError(Exception):
    def __init__(self, message: str, document_id: str | None = None):
        super().__init__(message)
        self.document_id = document_id

class DocumentParsingError(DocumentProcessingError):
    pass

class DocumentValidationError(DocumentProcessingError):
    def __init__(self, message: str, validation_errors: list[str], document_id: str | None = None):
        super().__init__(message, document_id)
        self.validation_errors = validation_errors
```

**Answer:** A caller catching a bare `Exception` can't distinguish "this
document is malformed, skip it" from "the database connection died,
page someone." A typed hierarchy lets each caller catch precisely the
failure mode it knows how to handle, and lets each exception carry the
context (a `document_id`, a list of validation failures) needed to
actually act on it.

| Pros | Cons / Trade-offs |
|---|---|
| Callers can react differently to different failure classes | An overly deep hierarchy becomes its own maintenance burden |
| Exceptions carry structured context instead of just a string | Easy to over-engineer for failure modes that never actually need distinct handling |
| Pairs naturally with structured logging/alerting by exception type | Requires discipline to not just default back to bare `except Exception` under pressure |

### Testing Strategy

**"How do you decide what to unit test vs. integration test vs. not test at all?"**

```python
@pytest.fixture
async def mock_repo() -> AsyncMock:
    repo = AsyncMock(spec=DocumentRepository)
    repo.save.return_value = "doc_123"
    return repo

@pytest.mark.asyncio
async def test_create_document_success(mock_repo):
    service = DocumentService(mock_repo)
    doc_id = await service.create_document("test content")
    assert doc_id == "doc_123"
```

**Answer:** Unit tests with mocked dependencies for business logic — 
fast, isolated, run on every commit. Integration tests (real DB, real
external calls where feasible) for the handful of paths where the
*wiring itself* is the risk, not the logic. Test pyramid shape: many
unit tests, fewer integration, fewest end-to-end — chasing 100% coverage
on everything is lower value than deep coverage on auth, billing, and
anything touching PII.

| Pros | Cons / Trade-offs |
|---|---|
| Fast feedback loop — unit tests run in seconds | Over-mocking can mean tests pass while real integration is broken |
| Integration tests catch wiring bugs unit tests structurally can't | Integration tests are slower and flakier — a smaller, deliberate set is better than "test everything twice" |
| Tests double as executable documentation of expected behavior | Coverage numbers alone don't tell you if the *right* things are covered |

---

## Part 4: Refactoring Legacy Systems

### Incremental Modernization

**"How do you add type hints to a large, untyped legacy codebase without a big-bang rewrite?"**

```python
# Before
def process_document(doc, options):
    if options.get('validate', True) and not validate_doc(doc):
        return None
    return transform_doc(doc, options)

# After -- accepts both old and new shapes during the transition
def process_document(
    doc: dict | Document,
    options: dict,
) -> ProcessedDocument | None:
    if isinstance(doc, dict):
        doc = Document.from_dict(doc)
    if options.get('validate', True) and not validate_doc(doc):
        return None
    return transform_doc(doc, options)
```

**Answer:** Support both the old and new shape simultaneously during
the transition, add types to the highest-traffic/highest-risk modules
first, and never require every caller to migrate at once. A full
rewrite risks a long-lived branch that diverges from production while
it's being built.

| Pros | Cons / Trade-offs |
|---|---|
| Ships continuously — no long-lived "big rewrite" branch | The transitional dual-shape code is itself extra complexity, temporarily |
| Each step is independently revertible | Momentum can stall — "incremental" sometimes means "never finished" without a deadline |
| Team keeps shipping features alongside modernization | Requires real discipline to actually sunset the legacy path, not just leave both forever |

### Monolith → Microservices (Strangler Fig)

**"Walk me through extracting one service from a monolith without a risky big-bang cutover."**

```python
# Step 1: define the interface the extracted service must satisfy
class DocumentStorageService(Protocol):
    async def store(self, doc: Document) -> str: ...

# Step 2: implement it as a remote call to the new service
class RemoteDocumentStorageService:
    async def store(self, doc: Document) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/documents", json=doc.to_dict()) as resp:
                return (await resp.json())["document_id"]

# Step 3: the monolith depends on the interface, routes a small % of
# traffic to the new implementation, and compares results before cutover
```

**Answer:** The Strangler Fig pattern: put a seam (an interface) around
the capability being extracted, route a small percentage of traffic to
the new service, compare outputs against the old path for consistency,
and only fully cut over once confidence is high — the old and new
implementations coexist during the transition instead of a single
risky switch.

| Pros | Cons / Trade-offs |
|---|---|
| Each extraction is small and independently revertible | Slower than a big-bang rewrite — deliberately so |
| Real production traffic validates the new service before full cutover | Running both implementations in parallel has real infra cost during transition |
| Failure is contained to the one service being extracted | Requires genuine discipline to actually finish — a half-migrated system is worse than either extreme |

### Database Migration (Dual Read / Dual Write)

**"How do you migrate a schema with zero downtime when the table is actively being read and written?"**

```python
class DocumentMigrationService:
    async def migrate_v1_to_v2(self, doc_v1: DocumentV1) -> DocumentV2:
        metadata = json.loads(doc_v1.metadata or "{}")
        return DocumentV2(
            id=doc_v1.id,
            content=doc_v1.content,
            title=metadata.get("title"),
            raw_metadata=doc_v1.metadata,  # kept for rollback
        )

    async def read_with_fallback(self, doc_id: str) -> DocumentV2:
        if doc_v2 := await self.read_v2(doc_id):
            return doc_v2
        if doc_v1 := await self.read_v1(doc_id):
            return await self.migrate_v1_to_v2(doc_v1)  # migrate-on-read
        raise DocumentNotFoundError(doc_id)
```

**Answer:** Add the new column/table nullable → deploy code that writes
to *both* old and new shapes → backfill existing rows asynchronously →
switch reads to the new shape (falling back to the old shape + migrating
on read for anything not yet backfilled) → once fully migrated, drop the
old column. Skipping the dual-write step is the most common way this
goes wrong — old code still running mid-deploy writes to a column a
migration already dropped.

| Pros | Cons / Trade-offs |
|---|---|
| Genuinely zero downtime — no maintenance window needed | More moving parts to coordinate correctly than a single migration script |
| Rollback stays possible until the old shape is actually dropped | Dual-write/dual-read code is real, if temporary, complexity |
| Backfill can be throttled to protect production load | Easy to forget to actually clean up and drop the legacy path afterward |

---

## Code Samples

- `code_samples/chapter-2/solid_principles_enterprise.py` — all five SOLID principles applied together
- `code_samples/chapter-2/factory_strategy_patterns.py` — Factory and Strategy patterns

```bash
pip install pytest pytest-asyncio
python code_samples/chapter-2/solid_principles_enterprise.py
pytest code_samples/chapter-2/
```

---

## Summary

1. **SOLID** — five principles for change-tolerant design; each has a
   real cost (more classes, more indirection) that's worth paying once,
   not applied reflexively everywhere.
2. **Design patterns** — Factory, Strategy, Observer, Repository each
   solve a specific recurring problem; know the problem each one
   actually solves, not just its shape.
3. **Clean code** — function/class design, typed exception hierarchies,
   and a deliberate test pyramid are what make a codebase reviewable
   and safe to change at team scale.
4. **Refactoring** — incremental modernization, the Strangler Fig
   pattern, and dual-read/dual-write migrations are how production
   systems change without a risky big-bang cutover.
