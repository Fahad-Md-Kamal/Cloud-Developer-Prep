---
title: "FastAPI: Performance & Production Patterns"
---

# FastAPI: Performance & Production Patterns

Connection pooling, concurrent outbound calls, response encoding,
streaming, WebSockets, and the ASGI mechanics underneath — the
patterns that matter once an endpoint is correct and needs to hold up
under real load. For the core request-handling mechanics (dependency
injection, background tasks), see
[FastAPI: Dependency Injection & Background Tasks](fastapi-dependency-injection.md).

---

## 1. Performance Patterns

- **Connection pooling** — reuse a single `AsyncSession`/connection
  pool across requests rather than opening a new DB connection per
  request; create the pool once in `lifespan`'s startup phase (see
  [Auth, Middleware & Lifecycle Events §5](fastapi-auth-and-middleware.md#5-lifespan-events-startup-shutdown)).
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
  [AsyncIO Internals' cooperative scheduling](asyncio-internals.md#cooperative-scheduling),
  applied specifically to a FastAPI handler.

## 2. WebSockets

```python
@app.websocket("/ws/orders/{order_id}")
async def order_updates(websocket: WebSocket, order_id: int):
    await websocket.accept()
    try:
        while True:
            update = await get_next_update(order_id)
            await websocket.send_json(update)
    except WebSocketDisconnect:
        pass
```

- A WebSocket route is declared with `@app.websocket`, not
  `@app.get`/`@app.post` — a genuinely different protocol (a single
  long-lived, bidirectional connection) from a normal request/response
  route, not just a route that happens to stay open longer.
- `websocket.accept()` completes the handshake; from there both sides
  can send/receive independently — `send_json`/`receive_json` (or
  `receive_text`) for the actual messages, with a `WebSocketDisconnect`
  exception raised when the client closes the connection.
- **Interview point:** each WebSocket connection holds a worker/process
  slot open for its entire duration — this is exactly why a WebSocket
  server is scaled and load-balanced differently from a normal
  request/response API (sticky sessions or a pub/sub backend like Redis
  to fan a message out to the right connection, wherever it's held).

## 3. API Versioning

| Strategy | Example | Trade-off |
|---|---|---|
| URL path | `/v1/orders/` via a versioned `APIRouter(prefix="/v1")` | Most explicit/cacheable; clutters URLs with version churn |
| Header | `X-API-Version: 1` read via a dependency | Clean URLs; invisible to casual API exploration |
| Separate app mount | `app.mount("/v2", app_v2)` for a fully separate FastAPI app | Clean separation for a genuinely breaking rewrite; two codebases to maintain in parallel |

- Same strategies and the same underlying trade-off as
  [Django & DRF §13](django-drf.md#13-api-versioning) — FastAPI just
  implements "URL path" via a prefixed `APIRouter` instead of a
  Django/DRF versioning class.
- **Interview point:** the harder problem, same as in DRF, is never
  the mechanism — it's the policy of how long an old version stays
  supported and whether a change needs a new version at all versus
  shipping as an additive, non-breaking field.

## 4. OpenAPI Schema Customization

```python
app = FastAPI(title="Orders API", version="2.1.0")

@router.get(
    "/orders/{order_id}",
    response_model=OrderRead,
    summary="Fetch a single order",
    responses={404: {"description": "Order not found"}},
)
async def get_order(order_id: int):
    ...
```

- FastAPI generates an OpenAPI schema (and `/docs`'s Swagger UI,
  `/redoc`) **automatically from route signatures and Pydantic
  models** — no separate introspection library needed, unlike DRF's
  `drf-spectacular` in
  [Django & DRF §17](django-drf.md#17-api-schema-documentation). This
  is a genuine structural advantage of type-hint-driven design: the
  schema can't drift from the code the way a hand-maintained OpenAPI
  YAML file can, since both are generated from the same source.
- `responses={404: {...}}` documents a non-default response FastAPI
  can't infer on its own (a route raising `HTTPException(404)`
  conditionally isn't visible from the return type alone) — the
  FastAPI analogue of `drf-spectacular`'s `@extend_schema` for
  behavior the auto-introspection can't see.

## 5. Caching

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
import redis.asyncio as redis

redis_client = redis.from_url(REDIS_URL)

async def get_dashboard_stats(organization_id: int):
    key = f"dashboard_stats:{organization_id}"
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)
    stats = await compute_expensive_stats(organization_id)
    await redis_client.set(key, json.dumps(stats), ex=300)
    return stats
```

- FastAPI has no built-in cache framework the way Django ships
  `django.core.cache` — a cheap in-process cache for something like
  settings uses plain `functools.lru_cache`; a shared cache across
  multiple worker processes (the common real case) needs an external
  store like Redis, accessed directly or via a library like
  `fastapi-cache2`.
- The same invalidation discipline from
  [Django & DRF §9](django-drf.md#9-caching) still applies regardless
  of framework: key the cache by everything the value depends on, and
  invalidate explicitly on the write path rather than relying on TTL
  alone for data that needs to be fresh.

## 6. ASGI and the Request/Response Lifecycle

- FastAPI is built on **Starlette**, which implements **ASGI**
  (Asynchronous Server Gateway Interface) — the async-capable
  successor to **WSGI**, the interface Django (and Flask) use by
  default. WSGI handles one request at a time per worker and has no
  native concept of a connection that stays open (a WebSocket,
  Server-Sent Events); ASGI's single
  `async def app(scope, receive, send)` interface can represent all
  three — HTTP request/response, WebSocket, and lifespan events —
  uniformly.
- This is the actual mechanism behind every async feature covered
  above: WebSockets, concurrent request handling without a thread per
  connection, and `lifespan` startup/shutdown events all exist
  *because* ASGI's interface supports them, not because FastAPI added
  special-case support for each on top of a fundamentally synchronous
  base the way Django's native async support had to be retrofitted
  onto WSGI's synchronous foundation.
- **Interview point:** "Why is FastAPI async-first while Django added
  async support later?" — expects naming ASGI vs. WSGI specifically:
  FastAPI/Starlette were built on an async-native interface from the
  start, while Django's async views
  ([Django & DRF §16](django-drf.md#16-async-views-in-djangodrf)) are
  a newer layer added on top of a framework whose request-handling
  core (and still, much of DRF) remains fundamentally synchronous.

## 7. Interview Questions You're Likely to Get Asked

**Concurrency & performance**

- "An endpoint makes three independent outbound calls sequentially
  and is slow — what's the fix?" — expects `asyncio.gather`,
  [§1](#1-performance-patterns).
- "Why is FastAPI considered async-first while Django added async
  support later?" — expects the ASGI vs. WSGI distinction,
  [§6](#6-asgi-and-the-requestresponse-lifecycle).

**Real-time & scaling**

- "How does scaling a WebSocket server differ from scaling a normal
  REST API?" — expects recognizing each connection holds a slot open
  for its duration, needing sticky sessions or a pub/sub backend to
  route messages to the right held connection, [§2](#2-websockets).

**Schema & caching**

- "How does FastAPI's auto-generated OpenAPI schema avoid drifting
  from the actual code, unlike a hand-maintained spec?" — expects:
  it's generated from the same route signatures and Pydantic models
  that define the actual behavior, not introspected or hand-written
  separately, [§4](#4-openapi-schema-customization).
- "FastAPI has no built-in cache framework — what replaces
  `django.core.cache` in a multi-worker deployment?" — expects an
  external store like Redis, since an in-process cache like
  `lru_cache` doesn't share state across worker processes,
  [§5](#5-caching).

---

## Code Samples

- `code_samples/chapter-3/fastapi_analytics_api.py` — WebSockets,
  streaming responses, caching
