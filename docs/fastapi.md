---
title: FastAPI
---

# FastAPI

Async-first, automatic request validation via Pydantic, and dependency
injection as the core extensibility mechanism. For general REST API
design principles (resource modeling, versioning, caching, rate
limiting) that apply regardless of framework, see
[Chapter 3: REST API Design Principles](chapter-3.md). For Django/DRF,
see [Frameworks → Django & DRF](django-orm.md).

## Dependency Injection

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

`Depends` wires a function's return value into another function's
parameters — dependencies can depend on other dependencies (`get_current_user`
depends on `get_db`), building a resolution chain FastAPI handles
automatically. This is also what makes testing straightforward: override
`get_db` with a test database session via
`app.dependency_overrides[get_db] = get_test_db`, and every endpoint
using it picks up the override without touching endpoint code.

**Know this:** dependencies should be side-effect-free at *definition*
time — don't open a socket or spawn a thread while FastAPI is wiring
dependencies together, only when the dependency actually runs per
request.

## Background Tasks

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

`BackgroundTasks` runs a function *after* the response is sent — good
for "fire and forget, but not so important it needs a real message
queue." It runs in the same process, though, so it's not a substitute
for Celery when the work is heavy, needs retries, or must survive a
process restart — for that, hand off to a real task queue (see
[Practical Patterns §3](practical-patterns.md#3-when-do-you-reach-for-celery-instead-of-just-handling-something-in-the-request))
instead.

**Where this actually shows up:** kicking off a slow analysis or
notification after returning `202 Accepted` to the client immediately,
rather than making the client wait for work that doesn't need to block
the response.

## Performance Patterns

- **Connection pooling** — reuse a single `AsyncSession`/connection pool
  across requests rather than opening a new DB connection per request.
- **`asyncio.gather`** — batch independent outbound calls (multiple
  third-party API calls, multiple DB queries with no dependency between
  them) to run concurrently instead of sequentially awaiting each one.
- **`ORJSONResponse`** — a faster JSON encoder than the default, worth
  using on high-throughput endpoints once correctness is already
  verified.
- **Streaming responses** (`StreamingResponse`) for large payloads,
  instead of building the full response body in memory first.

```python
async def get_dashboard(user_id: int):
    stats, notifications, recent_orders = await asyncio.gather(
        fetch_stats(user_id),
        fetch_notifications(user_id),
        fetch_recent_orders(user_id),
    )
    return {"stats": stats, "notifications": notifications, "orders": recent_orders}
```

Three independent calls awaited one at a time triples the latency for no
reason — `asyncio.gather` runs them concurrently since none depends on
another's result. This is the same "why is this endpoint slow"
diagnostic covered in
[Concurrency & AsyncIO §2](concurrency-and-asyncio.md#2-a-django-view-calling-three-third-party-apis-is-slow-walk-me-through-fixing-it),
applied specifically to a FastAPI handler.

---

## Code Samples

- `code_samples/chapter-3/fastapi_document_service.py` — async
  processing, dependency injection, background tasks
- `code_samples/chapter-3/fastapi_analytics_api.py` — WebSockets,
  streaming responses, caching

```bash
pip install fastapi uvicorn
uvicorn code_samples.chapter-3.fastapi_document_service:app --reload
```
