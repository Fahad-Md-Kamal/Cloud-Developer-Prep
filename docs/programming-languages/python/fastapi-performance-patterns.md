---
title: "FastAPI: Performance & Production Patterns"
---

# FastAPI: Performance & Production Patterns

Connection pooling, concurrent outbound calls, response encoding, and
streaming — the patterns that matter once an endpoint is correct and
needs to hold up under real load. For the core request-handling
mechanics (dependency injection, background tasks), see
[FastAPI: Dependency Injection & Background Tasks](fastapi-dependency-injection.md).

## Performance Patterns

- **Connection pooling** — reuse a single `AsyncSession`/connection
  pool across requests rather than opening a new DB connection per
  request.
- **`asyncio.gather`** — batch independent outbound calls (multiple
  third-party API calls, multiple DB queries with no dependency
  between them) to run concurrently instead of sequentially awaiting
  each one.
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

- Three independent calls awaited one at a time triples the latency
  for no reason — `asyncio.gather` runs them concurrently since none
  depends on another's result.
- This is the same "why is this endpoint slow" diagnostic covered in
  [Concurrency & AsyncIO §2](concurrency-and-asyncio.md#2-a-django-view-calling-three-third-party-apis-is-slow-walk-me-through-fixing-it),
  applied specifically to a FastAPI handler.

---

## Code Samples

- `code_samples/chapter-3/fastapi_analytics_api.py` — WebSockets,
  streaming responses, caching
