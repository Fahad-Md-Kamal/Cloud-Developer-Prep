---
title: Typing & Generics
---

# Typing & Generics

Generic types and Protocols — the two typing features that come up
most in senior interviews, each as a question with the code and the
trade-offs.

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

**Answer:**

- `Generic[T]` lets a class work with any type while the type checker
  still tracks *which* type.
- A `Repository[T]` base class works for `UserRepository` and
  `OrderRepository` without duplicating CRUD logic or falling back to
  untyped `Any`.

**Likely follow-up — "what's wrong with just using `TypeVar` unbounded, or `Any`?"**

- Both hide exactly the errors typing exists to catch.
- Bound it (`TypeVar('T', bound=BaseModel)`) once the generic needs to
  call a specific method on `T`.

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

**Answer:**

- A `Protocol` checks structurally — "anything with this method
  counts" — instead of requiring a shared base class.
- It's duck typing with static verification: `WebCrawler` and
  `APICrawler` both satisfy `Crawlable` just by having the right
  method signature.

**Likely follow-up — "when would you reach for this over inheritance?"**

- Swapping HTTP clients (`requests` for `httpx`) or mocking a
  dependency in a test — both work because they satisfy the same
  Protocol, without forcing every implementation through one base
  class.

| Pros | Cons / Trade-offs |
|---|---|
| No shared base class needed — existing classes satisfy it retroactively | Less discoverable than inheritance — no simple "find subclasses" search |
| Great for adapting third-party classes you don't control | `@runtime_checkable` + `isinstance()` only checks method names exist, not correct behavior |
| Encourages small, role-based interfaces that are easy to mock in tests | Overuse can make it unclear which concrete types are actually expected at a call site |

---

## Code Samples

- `code_samples/chapter-1/typing/generic_document_processing.py`
- `code_samples/chapter-1/typing/protocol_crawling_system.py`
- `code_samples/chapter-1/typing/type_driven_api.py`

```bash
pip install pydantic fastapi
python code_samples/chapter-1/typing/generic_document_processing.py
mypy code_samples/chapter-1/ --config-file code_samples/chapter-1/config/mypy.ini
```
