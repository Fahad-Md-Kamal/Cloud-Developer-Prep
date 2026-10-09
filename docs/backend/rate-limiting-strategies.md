---
title: "Rate Limiting Strategies"
---

# Rate Limiting Strategies

Token bucket vs. sliding window, making limits work across multiple
gateway instances, and per-user/per-endpoint limits in Django/DRF —
part of the same gateway discussion as
[API Gateway Architecture](api-gateway-architecture.md).

## 1. "Compare token bucket and sliding window rate limiting. Which would you pick and why?"

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

## 2. "How do you implement rate limiting across multiple gateway or app instances?"

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

## 3. "Design per-user and per-endpoint rate limits for a Django/DRF API."

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

## 4. "What should actually happen when a client gets rate limited?"

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

## Code Samples

No dedicated code samples yet for this page — the `TokenBucket` and
Redis Lua snippets above are small enough to run directly.
