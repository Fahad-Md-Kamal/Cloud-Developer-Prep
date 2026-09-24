---
title: Design Patterns
---

# Design Patterns

The four patterns that actually come up in senior interviews — each as
a question, with the specific problem it solves and its real cost.

## Factory

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

## Strategy

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

## Observer

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

## Repository

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

## Code Samples

- `code_samples/chapter-2/factory_strategy_patterns.py` — Factory and Strategy patterns

```bash
python code_samples/chapter-2/factory_strategy_patterns.py
```
