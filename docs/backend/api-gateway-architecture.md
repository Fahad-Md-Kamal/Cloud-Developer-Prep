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

**Answer:** A load balancer operates at the connection/request level,
distributing traffic across identical replicas of *one* service — it
doesn't inspect what the request means. An API gateway is a single
entry point that does L7-aware work: authenticate the caller, apply
rate limits, route by path/version to the *right* service, translate
protocols (REST in, gRPC to a backend), and sometimes aggregate several
backend calls into one response. Every cross-cutting concern moves out
of individual services and into one place.

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

**Answer:** Validate the token once at the gateway, then pass a trusted
identity (a header, or a re-signed internal token) downstream — services
never see raw credentials and never re-implement JWT validation. The
trade-off is that the gateway becomes the security boundary: if it's
bypassed (a service reachable directly on the internal network) or
compromised, every downstream service is exposed. Most real setups pair
gateway-level auth with a lighter internal check (mTLS or a shared
secret) so services don't blindly trust *any* traffic that reaches them.

**Likely follow-up — "should the gateway own authorization too, not just authentication?"**
Usually not entirely. Coarse authorization (is this token valid, is this
scope present) fits at the gateway; fine-grained authorization ("can
*this* user edit *this* specific order") needs domain data the gateway
doesn't have, so it stays in the owning service.

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

**Answer:** A mobile or web client that needs data from three services
to render one screen shouldn't have to make three round trips (each
with its own latency and failure mode) — a gateway or
backend-for-frontend fans the calls out concurrently and merges the
results into one response. The cost is that this composition logic is
now business logic living in the gateway layer, which can turn a "dumb
router" into something that needs its own testing, versioning, and
on-call ownership.

---

## Code Samples

No dedicated code samples yet for this page — the snippets above are
small enough to run directly against a local FastAPI/Starlette app.
