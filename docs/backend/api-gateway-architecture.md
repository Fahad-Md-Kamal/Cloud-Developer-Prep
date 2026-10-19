---
title: "API Gateway Architecture"
---

# API Gateway Architecture

What an API gateway actually does that a plain load balancer doesn't,
authentication at the edge, and request aggregation — the gateway's own
responsibilities, distinct from [Service Boundaries & Architecture](service-boundaries-and-architecture.md)'s
gateway-vs-mesh framing. For the concrete product behind "API Gateway
(Kong)" in a JD, see [Kong API Gateway](kong-api-gateway.md); for rate
limiting and circuit breaking specifically, see
[Rate Limiting Strategies](rate-limiting-strategies.md) and
[Circuit Breakers, Retries & Bulkheads](circuit-breakers-retries-and-bulkheads.md).

## 1. "What does an API gateway actually do that a plain load balancer doesn't?"

```python
# A load balancer picks *which replica* handles a request.
# A gateway decides *what happens* to the request before it gets there:
# auth, rate limiting, routing by path/version, response shaping.

ROUTES = {
    "/api/v1/users":  {"service": "user-service:8001",  "auth_required": True},
    "/api/v1/orders": {"service": "order-service:8002", "auth_required": True},
    "/api/v1/health":  {"service": "*", "auth_required": False},
}
```

**Answer:** A load balancer only decides *which identical replica*
handles a request — it never looks at what the request actually is. A
gateway does, and acts on it.

- **A load balancer** operates at the connection/request level,
  spreading traffic across copies of *one* service, with no
  understanding of what's inside the request.
- **A gateway** is a single entry point that reads the request itself
  and does real work with it: authenticate the caller, apply rate
  limits, route by path or version to the *correct* service, translate
  protocols (REST coming in, gRPC going to a backend), and sometimes
  combine several backend calls into one response.
- The underlying shift: cross-cutting concerns (auth, rate limiting,
  logging) move out of every individual service and into one shared
  place.

| Pros | Cons / Trade-offs |
|---|---|
| Auth, rate limiting, logging implemented once, not N times per service | New single point of failure — must be run highly available itself |
| Services stay simpler — no need to each reimplement cross-cutting concerns | Adds one more network hop of latency to every request |
| Central place to see and control all external traffic | Can become a bottleneck or a dumping ground for business logic that doesn't belong there |

## 2. "How would you handle authentication at the gateway vs. in each service?"

```python
async def gateway_auth_middleware(request, call_next):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    try:
        claims = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    except jwt.InvalidTokenError:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    # Downstream services trust this header instead of re-validating the token
    request.headers.__dict__["_list"].append(
        (b"x-user-id", str(claims["sub"]).encode())
    )
    return await call_next(request)
```

**Answer:** Validate the token once, at the gateway — not again in
every service behind it.

- The gateway checks the token, then passes a trusted identity
  downstream (a header, or a re-signed internal token). Services never
  see the raw credentials, and never have to implement JWT validation
  themselves.
- **The trade-off:** the gateway is now the security boundary. If it's
  bypassed (a service that's also reachable directly, without going
  through the gateway) or compromised, every service behind it is
  exposed.
- **The usual mitigation:** pair gateway-level auth with a lighter
  internal check too (mTLS, or a shared secret) — so a service doesn't
  blindly trust *any* traffic that happens to reach it, only traffic
  that's actually come through the gateway.

**Likely follow-up — "should the gateway own authorization too, not
just authentication?"**

- Usually not entirely.
- **Coarse authorization** — "is this token valid, does it carry the
  right scope" — fits fine at the gateway.
- **Fine-grained authorization** — "can *this* user edit *this*
  specific order" — needs domain data the gateway doesn't have, so it
  has to stay in the service that owns that data.

## 3. "What's request aggregation, and when do you actually need it?"

```python
async def get_order_summary(order_id: str):
    order, customer, inventory = await asyncio.gather(
        order_service.get(order_id),
        customer_service.get_for_order(order_id),
        inventory_service.check(order_id),
    )
    return {"order": order, "customer": customer, "in_stock": inventory.available}
```

**Answer:** A client that needs data from three services to render one
screen shouldn't have to make three separate round trips — each with
its own latency and its own way to fail.

- A gateway (or a dedicated backend-for-frontend) fans the three calls
  out *concurrently* and merges the results into one response, so the
  client makes one request instead of three.
- **The cost:** this merging logic is now real business logic living
  in the gateway layer — which can quietly turn a "dumb router" into
  something that needs its own tests, its own versioning, and its own
  on-call ownership.

---

## Code Samples

No dedicated code samples yet for this page — the snippets above are
small enough to run directly against a local FastAPI/Starlette app.
