---
title: "FastAPI: Dependency Injection & Background Tasks"
---

# FastAPI: Dependency Injection & Background Tasks

Async-first, automatic request validation via Pydantic, and dependency
injection as the core extensibility mechanism. For general REST API
design principles (resource modeling, versioning, caching, rate
limiting) that apply regardless of framework, see
[REST Deep Dive](../architecture/rest-deep-dive.md) and
[API Production Readiness](../architecture/api-production-readiness.md). For Django/DRF,
see [Django & DRF Deep Dive](django-drf.md). For routing and Pydantic
validation, see
[FastAPI Fundamentals: Routing & Pydantic Validation](fastapi-routing-and-validation.md).
For connection pooling, concurrency, and response-encoding patterns,
see [FastAPI: Performance & Production Patterns](fastapi-performance-patterns.md).

---

## 1. Dependency Injection

```python
async def get_db() -> AsyncSession:
    async with get_session() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await authenticate_user(db, token)

@app.get("/me")
async def read_me(user: User = Depends(get_current_user)):
    return user
```

- `Depends` wires a function's return value into another function's
  parameters.
- Dependencies can depend on other dependencies (`get_current_user`
  depends on `get_db`), building a resolution chain FastAPI handles
  automatically — this chaining is covered in more depth in
  [§2](#2-sub-dependencies-and-per-request-caching).
- This is also what makes testing straightforward: override `get_db`
  with a test database session via
  `app.dependency_overrides[get_db] = get_test_db`, and every endpoint
  using it picks up the override without touching endpoint code — the
  full testing pattern is in
  [FastAPI: Database Integration & Testing §5](fastapi-database-and-testing.md#5-dependency-overrides-for-testing).

**Know this:**

- Dependencies should be side-effect-free at *definition* time — don't
  open a socket or spawn a thread while FastAPI is wiring dependencies
  together, only when the dependency actually runs per request.

## 2. Sub-Dependencies and Per-Request Caching

```python
async def get_settings() -> Settings:
    return Settings()

async def get_rate_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    return RateLimiter(settings.rate_limit_per_minute)

@router.get("/search")
async def search(
    limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),  # same instance, not re-run
):
    ...
```

- By default FastAPI **caches a dependency's result for the lifetime
  of a single request** — `get_settings` above runs once even though
  it's needed both directly and as `get_rate_limiter`'s own
  dependency. This matters for correctness (every consumer in that
  request sees the same instance) and for cost (an expensive
  dependency isn't recomputed per use).
- `Depends(get_settings, use_cache=False)` opts a specific usage out
  of that caching, for the rare case where a dependency genuinely
  needs to run fresh every time it's referenced within the same
  request.
- **Interview point:** this per-request cache is the direct reason a
  dependency chain several levels deep (auth → tenant lookup →
  permission check, each depending on the last) doesn't re-run the
  expensive early steps multiple times just because several
  route-level dependencies each need the result.

## 3. Yield Dependencies: Setup, Teardown & Exception Propagation

```python
async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- Code before `yield` runs as setup, before the route executes; code
  after `yield` runs as teardown, after the route returns — even if
  the route raised an exception, which is why this pattern (not a
  plain `return`) is how FastAPI dependencies express "close/clean up
  this resource no matter what happened."
- An exception raised inside the route **propagates back into the
  dependency's `except` block** at the `yield` point — the pattern
  above uses that to commit on success and roll back on failure, the
  same transactional shape a Django view gets for free from
  `transaction.atomic()`, done explicitly here since FastAPI has no
  built-in equivalent.
- **Know this:** forgetting the `try`/`except` around `yield` means an
  exception in the route skips the session close entirely in some
  setups — always pair `yield` with cleanup that runs
  unconditionally (a `finally`, or `async with` around the `yield` as
  above, where the context manager's own `__aexit__` guarantees the
  close regardless of how the `try` block exits).

## 4. Class-Based Dependencies

```python
class Paginator:
    def __init__(self, limit: int = Query(default=20, le=100), offset: int = Query(default=0)):
        self.limit = limit
        self.offset = offset

@router.get("/orders")
async def list_orders(pagination: Paginator = Depends()):
    return await order_service.list(limit=pagination.limit, offset=pagination.offset)
```

- A class works as a dependency because FastAPI calls it the same way
  it calls a function — `__init__`'s parameters get resolved exactly
  like a dependency function's parameters would.
- `Depends()` with no argument, used on a parameter already typed as
  the class, tells FastAPI to use the type itself as the dependency —
  a shorthand for `Depends(Paginator)`, useful when the class is also
  genuinely the type being injected (as with `Paginator` above).
- Where this actually shows up: bundling several related query
  parameters (pagination, a common filter set) into one reusable,
  typed object instead of repeating the same three `Query(...)`
  parameters on every list endpoint that needs them.

## 5. Background Tasks

```python
@app.post("/documents/{doc_id}/analyze")
async def analyze_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    background_tasks.add_task(extract_entities, doc_id)
    return {"status": "analysis_started", "doc_id": doc_id}
```

- `BackgroundTasks` runs a function *after* the response is sent —
  good for "fire and forget, but not so important it needs a real
  message queue."
- It runs in the same process though, so it's not a substitute for
  Celery when the work is heavy, needs retries, or must survive a
  process restart — for that, hand off to a real task queue (see
  [Practical Patterns §4](practical-patterns.md#4-when-do-you-reach-for-celery-instead-of-just-handling-something-in-the-request))
  instead.
- A dependency with a `yield` (like `get_db` in
  [§3](#3-yield-dependencies-setup-teardown-exception-propagation))
  runs its teardown *before* a background task scheduled in the same
  route actually executes — a background task that needs a DB
  session should open its own, not assume the route's `db` dependency
  is still valid by the time it runs.

**Where this actually shows up:**

- Kicking off a slow analysis or notification after returning `202
  Accepted` to the client immediately, rather than making the client
  wait for work that doesn't need to block the response.

## 6. Interview Questions You're Likely to Get Asked

**Dependency resolution**

- "Two different route-level dependencies both depend on the same
  sub-dependency — does it run twice?" — expects no, FastAPI caches a
  dependency's result per-request by default,
  [§2](#2-sub-dependencies-and-per-request-caching).
- "How do you clean up a resource a dependency opened, even when the
  route raises an exception?" — expects a `yield` dependency with the
  cleanup wrapped so it runs unconditionally,
  [§3](#3-yield-dependencies-setup-teardown-exception-propagation).

**Testing & structure**

- "How would you swap a real database session for a test one across
  every endpoint that uses it, without touching route code?" —
  expects `app.dependency_overrides`, [§1](#1-dependency-injection),
  detailed in
  [FastAPI: Database Integration & Testing §5](fastapi-database-and-testing.md#5-dependency-overrides-for-testing).
- "When would you use a class instead of a function as a
  dependency?" — expects bundling several related parameters into
  one reusable typed object, [§4](#4-class-based-dependencies).

**Background work**

- "When is `BackgroundTasks` the wrong tool, and what replaces it?" —
  expects: heavy work, anything needing retries, or anything that
  must survive a process restart — a real task queue like Celery
  instead, [§5](#5-background-tasks).

---

## Code Samples

- `code_samples/chapter-3/fastapi_document_service.py` — async
  processing, dependency injection, background tasks

```bash
pip install fastapi uvicorn
uvicorn code_samples.chapter-3.fastapi_document_service:app --reload
```
