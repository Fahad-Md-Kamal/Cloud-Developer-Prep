---
title: "API Management & Versioning"
---

# API Management & Versioning

Versioning without breaking existing clients, maintaining backward
compatibility as a schema evolves, and what actually belongs in an API
SLA — the gateway-adjacent concerns that outlive any single endpoint.
Part of the same discussion as
[API Gateway Architecture](api-gateway-architecture.md).

## 1. "How do you version an API without breaking existing clients?"

```python
# URL versioning -- simple, visible, easy to route at the gateway
GET /api/v1/orders/123
GET /api/v2/orders/123

# Header/media-type versioning -- URL stays stable, version is metadata
GET /api/orders/123
Accept: application/vnd.myapi.v2+json
```

**Answer:** The safest version bump is the one you never have to make.

- **Additive-only changes** (a new optional field, a new endpoint)
  don't break existing clients at all, and cost nothing — prefer these
  whenever the change actually allows it.
- When a real breaking change is unavoidable, **URL versioning**
  (`/v1/`, `/v2/`) is the pragmatic default: visible, trivial to route
  at the gateway, and easy for a client to pin to.
- **Header/media-type versioning** is more "correct" in a strict REST
  sense — the URL stays a stable identifier for the resource, and the
  version is just metadata about its representation — but it's harder
  to discover, test, and cache correctly, since it's invisible in a
  browser or a plain `curl`.
- See [REST Deep Dive §3](../architecture/rest-deep-dive.md#3-versioning)
  for the same decision from the API-design side, not the gateway side.

| Approach | Pros | Cons / Trade-offs |
|---|---|---|
| URL versioning (`/v1/`, `/v2/`) | Simple, visible, trivial gateway routing, easy client debugging | The URL now encodes representation, not just resource identity |
| Header/media-type versioning | URL stays a stable identifier; cleaner REST semantics | Invisible in browser/curl by default; harder to test and cache |

## 2. "How do you maintain backward compatibility while a schema keeps evolving?"

**Answer:** Expand, then contract — never the other way around.

- **Expand:** add new fields as optional, with sensible defaults, so
  existing clients keep working without any changes on their end.
- **Never repurpose or remove a field** while any client still depends
  on it — not even to "just clean it up."
- **Deprecate explicitly** before actually removing anything: a
  `Sunset` or `Deprecation` response header, documentation, and —
  ideally — real usage metrics showing which clients are still calling
  the old shape, so you know when it's actually safe to contract.
- **The failure mode to avoid above all:** silently changing what a
  field *means* without changing its name or shape. That breaks
  clients with no error they can ever detect — they just start getting
  quietly wrong data.

## 3. "What would you actually put in an API SLA, and how would you monitor it?"

**Answer:** Concrete, measurable commitments — not a vague promise of
"fast and reliable."

- **Availability** — e.g. 99.9% of requests succeed.
- **Latency at specific percentiles** — p95, p99, not just an average.
  An average hides exactly the slow tail that real users actually feel.
- **The SLA is only real if something is actually measuring it** —
  per-route latency histograms and status-code counters at the gateway,
  feeding the dashboards and alerts covered in
  [Dashboards & Alerting](dashboards-and-alerting.md).
- Promising a number nobody is tracking is worse than not having an
  SLA at all — it's a commitment you can't even tell you're breaking.

---

## Code Samples

No dedicated code samples yet for this page — the versioning examples
above are URL/header shapes, not runnable scripts.
