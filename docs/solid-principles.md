---
title: SOLID Principles
---

# SOLID Principles

Five principles for change-tolerant design — each as a question you
should be able to answer cold, with the trade-offs named explicitly,
not just the upside.

## 1. Single Responsibility Principle (SRP)

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

## 2. Open/Closed Principle (OCP)

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

## 3. Liskov Substitution Principle (LSP)

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

## 4. Interface Segregation Principle (ISP)

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

## 5. Dependency Inversion Principle (DIP)

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

## All Five Together

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

## Code Samples

- `code_samples/chapter-2/solid_principles_enterprise.py` — all five SOLID principles applied together

```bash
python code_samples/chapter-2/solid_principles_enterprise.py
```
