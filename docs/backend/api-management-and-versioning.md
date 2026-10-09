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

**Answer:** The safest option is never needing a new version at all —
additive-only changes (new optional fields, new endpoints) don't break
existing clients and cost nothing. When a real breaking change is
unavoidable, URL versioning is the pragmatic default: visible, trivial
to route at the gateway, easy for clients to pin. Header/media-type
versioning is more "correct" (the URL is a stable resource identifier;
the representation format is metadata) but harder to discover, test,
and cache correctly. See [REST Deep Dive §3](../architecture/rest-deep-dive.md#3-versioning)
for the same decision from the API-design side.

| Approach | Pros | Cons / Trade-offs |
|---|---|---|
| URL versioning (`/v1/`, `/v2/`) | Simple, visible, trivial gateway routing, easy client debugging | The URL now encodes representation, not just resource identity |
| Header/media-type versioning | URL stays a stable identifier; cleaner REST semantics | Invisible in browser/curl by default; harder to test and cache |

## 2. "How do you maintain backward compatibility while a schema keeps evolving?"

**Answer:** Expand-contract: add new fields as optional with sensible
defaults, never repurpose or remove an existing field while any client
still depends on it, and mark deprecated fields explicitly (a `Sunset`
or `Deprecation` response header, docs, and — ideally — usage metrics
showing which clients still call the old shape) before actually
removing anything. The failure mode to avoid is silently changing what
a field means; that breaks clients without ever returning an error they
can detect.

## 3. "What would you actually put in an API SLA, and how would you monitor it?"

**Answer:** Concrete, measurable commitments: availability (e.g.,
99.9% of requests succeed), and latency at specific percentiles (p95,
p99 — not just an average, which hides the tail that actual users feel).
An SLA is only real if it's backed by monitoring that measures the same
thing it promises — per-route latency histograms and status-code
counters at the gateway, feeding the dashboards and alerts covered in
[Dashboards & Alerting](dashboards-and-alerting.md). Promising a number
nobody is actually tracking is worse than not having an SLA at all.

---

## Code Samples

No dedicated code samples yet for this page — the versioning examples
above are URL/header shapes, not runnable scripts.
