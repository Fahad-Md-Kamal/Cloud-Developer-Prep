---
title: "Rate Limiting Strategies"
---

# Rate Limiting Strategies

Token bucket vs. sliding window, making limits work across multiple
gateway instances, and per-user/per-endpoint limits in Django/DRF —
part of the same gateway discussion as
[API Gateway Architecture](api-gateway-architecture.md).

## 1. "Compare token bucket and sliding window rate limiting. Which would you pick and why?"

!!! example "Real-world analogy: an actual bucket of tokens"
    - Picture a literal bucket that holds up to, say, 20 tokens. It
      refills at a steady rate — one new token every 3 seconds, up to
      the bucket's capacity. Every request takes one token out of the
      bucket; no token left means no request allowed.
    - A client that's been quiet for a while has a full bucket — it
      can fire off a burst of 20 requests at once, instantly. That's
      the whole point of a *bucket*: it stores up unused capacity.
    - A client sending requests steadily just drains and refills the
      bucket at roughly the same rate, never hitting the limit at all.

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

**Answer:**

- **Token bucket** allows a short burst up to the bucket's capacity, as
  long as the *average* rate over time still respects the refill rate
  — good for traffic that's legitimately bursty (a client firing 20
  requests at once, then going quiet for a while).
- **Sliding window** counts requests inside a rolling time window and
  rejects once that count is exceeded. Smoother and more predictable,
  but it punishes a legitimate burst exactly the same as it punishes
  abuse — it doesn't distinguish between the two.
- **Which to pick:** token bucket (or its close cousin, leaky bucket,
  used for smoothing *outgoing* rate instead) is the better default for
  most public APIs. Sliding window fits better when the actual
  requirement is a hard guarantee — "never more than N requests in any
  given window," no exceptions.

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

**Answer:** A counter that only lives in one process's memory can't see
traffic that landed on a *different* process.

- With N gateway replicas behind a load balancer, an in-memory counter
  on each one would independently allow up to the full limit — the
  real, effective limit ends up multiplied by however many replicas
  there are.
- The counter has to live somewhere **shared** instead — almost always
  Redis — with the increment-and-check done **atomically** (a Lua
  script, or `INCR` + `EXPIRE` treated as close enough), so two
  concurrent requests from the same user can't both read "0" and both
  get allowed through.

**Likely follow-up — "what happens to rate limiting if Redis goes
down?"**

- This is a **fail-open vs. fail-closed** decision, and it needs to be
  made deliberately, ahead of time.
- **Fail-open** — let requests through when the limiter itself is
  unreachable. Protects availability, but leaves the API unprotected
  during exactly the kind of incident abuse traffic tends to show up
  in.
- **Fail-closed** — block requests when the limiter is unreachable.
  Protects the backend, but turns a Redis outage into a full API
  outage.
- Most production systems choose fail-open specifically for rate
  limiting — an API that's up but temporarily unprotected beats one
  that's fully down.

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

**Answer:**

- DRF's throttle classes key naturally on the authenticated user (or
  the caller's IP, if anonymous) — a custom throttle can go further and
  vary the **rate itself** per user attribute, like subscription tier,
  instead of hardcoding one number for everyone.
- **Per-endpoint limits** (a cheap read vs. an expensive export) use
  `ScopedRateThrottle` plus a `throttle_scope` on each view, so a heavy
  endpoint doesn't have to share a budget with a cheap one.

| Pros | Cons / Trade-offs |
|---|---|
| Different tiers/endpoints get appropriately different budgets | More configuration surface to keep consistent as endpoints are added |
| Enforced centrally, not duplicated per view | Throttle state (cache backend) becomes another shared dependency to keep healthy |
| Easy to expose remaining quota to clients via headers | Getting the *rate*, not just the mechanism, right requires real usage data |

## 4. "What should actually happen when a client gets rate limited?"

**Answer:** Return `429 Too Many Requests` with a `Retry-After` header
— never silently drop the request, and never return a misleading `200`
or an unrelated `5xx`.

- What "graceful" looks like beyond the status code depends on the
  endpoint: a non-critical read can serve a cached/stale response
  instead of rejecting outright.
- A write that actually matters can be queued and processed slightly
  late, instead of rejected entirely.
- A clearly abusive pattern just gets a hard reject — no special
  handling needed.
- The important part either way: the API contract should make the
  difference between "you were rejected" and "you were served
  something slightly stale" **explicit** to the caller, not something
  they have to guess at.

---

## Code Samples

No dedicated code samples yet for this page — the `TokenBucket` and
Redis Lua snippets above are small enough to run directly.
