---
title: Clean Code Practices
---

# Clean Code Practices

Function/class design, error handling, and testing strategy — the
standards that keep a codebase reviewable and safe to change at team
scale.

## Function & Class Design

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

## Error Handling & Exception Design

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

## Testing Strategy

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
