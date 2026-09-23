---
title: "Chapter 9: API Gateway, Rate Limiting, and Circuit Breaking Patterns"
---

# Chapter 9: API Gateway, Rate Limiting, and Circuit Breaking Patterns

API gateway responsibilities, rate limiting algorithms, circuit breaking,
and API versioning — each as a question you should be able to answer
cold, with the trade-offs named explicitly.

---

## Part 1: API Gateway Architecture

### 1. "What does an API gateway actually do that a plain load balancer doesn't?"

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

### 2. "How would you handle authentication at the gateway vs. in each service?"

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

### 3. "What's request aggregation, and when do you actually need it?"

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

## Part 2: Rate Limiting Strategies

### 4. "Compare token bucket and sliding window rate limiting. Which would you pick and why?"

```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

**Answer:** Token bucket allows short bursts up to the bucket's capacity
as long as the *average* rate stays within the refill rate — good for
bursty-but-legitimate traffic (a client that fires 20 requests at once
then goes quiet). Sliding window counts requests in a rolling time
window and rejects once the count is exceeded — smoother, more
predictable, but punishes legitimate bursts the same as abuse. For most
public APIs, token bucket (or its close cousin, leaky bucket for
smoothing egress rate) is the better default; sliding window fits
better when the guarantee that matters is "never more than N in any
window," full stop.

| Algorithm | Pros | Cons / Trade-offs |
|---|---|---|
| Token bucket | Tolerates legitimate bursts; simple to reason about | A client can "save up" tokens and burst harder than the average rate suggests |
| Sliding window | Precise, hard rate cap over any window | More expensive to compute exactly (log of timestamps) or approximate (fixed-window edge effects) |

### 5. "How do you implement rate limiting across multiple gateway or app instances?"

```python
# Atomic in Redis via Lua -- avoids a check-then-increment race
# between two gateway instances hitting the same key concurrently.
RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""

def is_allowed(redis_client, user_id: str, limit: int, window_seconds: int) -> bool:
    key = f"ratelimit:{user_id}:{int(time.time()) // window_seconds}"
    current = redis_client.eval(RATE_LIMIT_SCRIPT, 1, key, window_seconds)
    return current <= limit
```

**Answer:** An in-memory counter only sees traffic that hit *that*
process — with N gateway replicas behind a load balancer, each one
would allow up to the full limit independently. The counter has to live
somewhere shared, almost always Redis, with the increment-and-check
done atomically (a Lua script, or `INCR` + `EXPIRE` accepted as
"close enough") so two concurrent requests from the same user can't
both read "0" and both get allowed.

**Likely follow-up — "what happens to rate limiting if Redis goes down?"**
That's a fail-open vs. fail-closed decision made up front. Fail-open
(let requests through when the limiter is unreachable) protects
availability but leaves you unprotected during exactly the kind of
incident abuse traffic loves; fail-closed protects the backend but turns
a Redis outage into a full API outage. Most production systems fail
open for rate limiting specifically, since an unprotected-but-up API beats
a fully down one.

### 6. "Design per-user and per-endpoint rate limits for a Django/DRF API."

```python
from rest_framework.throttling import SimpleRateThrottle

class TieredUserRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None
        return f"throttle:user:{request.user.pk}"

    def get_rate(self):
        tier = getattr(self.request.user, "plan_tier", "free")
        return {"free": "100/hour", "pro": "5000/hour"}[tier]
```

**Answer:** DRF's throttle classes key naturally on user vs. anonymous
IP, and a custom throttle can vary the *rate* itself per user attribute
(subscription tier) rather than hardcoding one number for everyone.
Per-endpoint limits (a cheap read endpoint vs. an expensive export
endpoint) are handled with `ScopedRateThrottle` plus a `throttle_scope`
per view, so a heavy endpoint doesn't need to share a budget with a
cheap one.

| Pros | Cons / Trade-offs |
|---|---|
| Different tiers/endpoints get appropriately different budgets | More configuration surface to keep consistent as endpoints are added |
| Enforced centrally, not duplicated per view | Throttle state (cache backend) becomes another shared dependency to keep healthy |
| Easy to expose remaining quota to clients via headers | Getting the *rate*, not just the mechanism, right requires real usage data |

### 7. "What should actually happen when a client gets rate limited?"

**Answer:** Return `429 Too Many Requests` with a `Retry-After` header —
never silently drop the request or return a misleading `200`/`5xx`.
"Graceful degradation" beyond that depends on what the endpoint is: a
non-critical read can serve a cached/stale response instead of
rejecting outright; a write that matters can be queued and processed
slightly late instead of rejected; a truly abusive pattern just gets a
hard reject. The API contract should make the difference between "you
were rejected" and "you were served something slightly stale" explicit
to the caller, not silent.

---

## Part 3: Circuit Breaker Patterns

### 8. "Explain circuit breaker states and when each transition happens."

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.state = "closed"
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.opened_at = None

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.monotonic() - self.opened_at > self.recovery_timeout:
                self.state = "half_open"          # let one probe request through
            else:
                raise CircuitOpenError("failing fast, not calling downstream")
        try:
            result = func(*args, **kwargs)
        except Exception:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state, self.opened_at = "open", time.monotonic()
            raise
        else:
            self.state, self.failure_count = "closed", 0   # success resets it
            return result
```

**Answer:** **Closed** is normal operation — calls go through, failures
are counted. Once failures cross a threshold, it trips to **open** —
every call fails immediately without touching the downstream at all
("failing fast"). After a recovery timeout, it moves to **half-open**
and lets a single probe request through: success closes the circuit
again, failure reopens it. The point of failing fast in the open state
is to stop wasting threads, connections, and time waiting on timeouts
to a dependency that's already known to be down — without it, every
caller keeps queuing up behind a slow failure instead of failing
instantly and freeing resources.

### 9. "How does a circuit breaker interact with retries and timeouts — what breaks if you get the order wrong?"

**Answer:** All three solve different problems and have to compose
correctly. A **timeout** bounds how long one call waits. A **retry**
(with backoff and jitter, never a tight loop) handles a transient blip.
A **circuit breaker** wraps both and stops trying *at all* once the
failure rate shows the dependency is genuinely down, not just having a
bad millisecond. Get the order wrong — retrying without a circuit
breaker, or retrying with no backoff — and a struggling downstream
service gets hit with a **retry storm**: every failed call spawns more
retries, multiplying load on a service that's already failing, which is
exactly the cascading-failure scenario circuit breakers exist to
prevent.

| Pros | Cons / Trade-offs |
|---|---|
| Stops cascading failure from taking down callers of a dead dependency | Adds real complexity — three mechanisms to tune, not one |
| Downstream gets a chance to recover instead of being retried into the ground | A too-sensitive threshold trips on normal transient blips, hurting availability unnecessarily |
| Fast, predictable failure beats a caller hanging on a timeout | Requires per-dependency tuning — one size doesn't fit all backends |

### 10. "What is the bulkhead pattern, and why do you need it alongside a circuit breaker?"

```python
# Each downstream dependency gets its own bounded resource pool --
# a slow payment provider can't starve the connection pool that
# calls the (healthy) inventory service.
payment_pool = ThreadPoolExecutor(max_workers=10)
inventory_pool = ThreadPoolExecutor(max_workers=10)
```

**Answer:** Named after a ship's watertight compartments — a leak in
one doesn't sink the whole vessel. Applied to services, it means giving
each downstream dependency its *own* isolated resource pool (threads,
connections, queue capacity) instead of one shared pool for everything.
A circuit breaker stops you from *calling* a failing dependency once
it's known to be bad; a bulkhead limits the *blast radius* while it's
still degrading but hasn't tripped the breaker yet — without it, a slow
dependency can exhaust a shared thread pool and take down calls to
completely unrelated, healthy dependencies.

---

## Part 4: API Management

### 11. "How do you version an API without breaking existing clients?"

```python
# URL versioning -- simple, visible, easy to route at the gateway
GET /api/v1/orders/123
GET /api/v2/orders/123

# Header/media-type versioning -- URL stays stable, version is metadata
GET /api/orders/123
Accept: application/vnd.myapi.v2+json
```

**Answer:** The safest option is never needing a new version at all —
additive-only changes (new optional fields, new endpoints) don't break
existing clients and cost nothing. When a real breaking change is
unavoidable, URL versioning is the pragmatic default: visible, trivial
to route at the gateway, easy for clients to pin. Header/media-type
versioning is more "correct" (the URL is a stable resource identifier;
the representation format is metadata) but harder to discover, test,
and cache correctly.

| Approach | Pros | Cons / Trade-offs |
|---|---|
| URL versioning (`/v1/`, `/v2/`) | Simple, visible, trivial gateway routing, easy client debugging | The URL now encodes representation, not just resource identity |
| Header/media-type versioning | URL stays a stable identifier; cleaner REST semantics | Invisible in browser/curl by default; harder to test and cache |

### 12. "How do you maintain backward compatibility while a schema keeps evolving?"

**Answer:** Expand-contract: add new fields as optional with sensible
defaults, never repurpose or remove an existing field while any client
still depends on it, and mark deprecated fields explicitly (a `Sunset`
or `Deprecation` response header, docs, and — ideally — usage metrics
showing which clients still call the old shape) before actually
removing anything. The failure mode to avoid is silently changing what
a field means; that breaks clients without ever returning an error they
can detect.

### 13. "What would you actually put in an API SLA, and how would you monitor it?"

**Answer:** Concrete, measurable commitments: availability (e.g.,
99.9% of requests succeed), and latency at specific percentiles (p95,
p99 — not just an average, which hides the tail that actual users feel).
An SLA is only real if it's backed by monitoring that measures the same
thing it promises — per-route latency histograms and status-code
counters at the gateway, feeding the dashboards and alerts covered in
[Chapter 10](chapter-10.md). Promising a number nobody is actually
tracking is worse than not having an SLA at all.

---

## Summary

1. **API gateway** — one place for auth, routing, and protocol
   translation; it centralizes cross-cutting concerns at the cost of a
   new critical dependency and an extra network hop.
2. **Rate limiting** — token bucket for bursty legitimate traffic,
   sliding window for a hard cap; distributed limits need a shared,
   atomically-updated store, and the fail-open/fail-closed decision
   matters as much as the algorithm.
3. **Circuit breaking** — closed/open/half-open states stop cascading
   failure by failing fast; it only works correctly alongside sane
   timeouts, bounded retries with backoff, and bulkheaded resource
   pools per dependency.
4. **API management** — version only when a change is genuinely
   breaking, keep changes additive where possible, and back any SLA
   with monitoring that measures the exact thing being promised.
