---
title: "Chapter 3: REST API Design Principles"
---

# Chapter 3: REST API Design Principles

Framework-agnostic REST API design — resource modeling, HTTP semantics,
versioning, caching, rate limiting, and observability. Applies whether
the implementation is Django, FastAPI, or anything else. For
framework-specific depth, see
[Frameworks → Django & DRF](django-orm.md) or
[Frameworks → FastAPI](fastapi.md).

## 1. Resource Modeling

```python
# Good: resource-oriented
GET /api/v1/documents/{doc_id}/sections
POST /api/v1/experiments/{exp_id}/variants

# Bad: RPC-style
POST /api/getDocumentSections
GET /api/createExperimentVariant
```

Model endpoints around business entities (nouns), not actions (verbs) —
this is what makes an API predictable enough that a new developer can
guess the next endpoint's shape correctly. Model parent/child
relationships as nested resources, keep naming (pluralization, casing)
consistent across the whole API, and expose opaque IDs/pagination
cursors rather than leaking DB internals (auto-increment PKs, internal
enum values) into the public contract.

## 2. HTTP Methods & Status Codes

```
201 Created               # resource successfully created
202 Accepted              # async operation started, not yet complete
409 Conflict               # resource version mismatch (optimistic locking)
422 Unprocessable Entity  # validation failed
```

**Idempotency:** `PUT`/`DELETE` must be safe to retry — calling them
twice with the same input produces the same end state as calling once.
`POST` isn't idempotent by default; if a client might retry a mutation
(network timeout, no response received), require an idempotency key so
a retried request doesn't double-create the resource.

**Concurrency:** ETags + `If-Match` for optimistic locking — a client
sends back the ETag it last read, and a `409` tells it someone else
changed the resource first, instead of silently overwriting their
change.

**`PATCH` vs `PUT`:** `PUT` replaces the whole resource; `PATCH` updates
specific fields. Document `PATCH`'s merge semantics explicitly — a
client sending `{"status": "shipped"}` should update only `status`, not
silently null out every other field.

## 3. Versioning

```
# URI versioning -- simplest, most common
GET /api/v2/documents/{doc_id}

# Header-based
Accept: application/vnd.example.v2+json
```

Prefer additive changes (new optional fields) over breaking ones — most
API evolution doesn't need a version bump at all. When a breaking change
is unavoidable: URI versioning is the simplest to reason about and
debug; header/media-type versioning is more "correct" REST but harder
for clients to work with and harder to debug from a raw request log.
Communicate deprecation via `Deprecation`/`Sunset` headers with a real
timeline, and run contract tests between versions so a breaking change
gets caught in CI, not by a client in production.

## 4. Caching

Layer caching at the point closest to the client that's still safe:
CDN for public, cacheable `GET`s; application-level caching (Redis) for
computed values expensive to recompute per request; conditional
requests (`ETag`/`If-Modified-Since`) so a client with a fresh copy gets
a `304 Not Modified` instead of the full payload again.

**The hard part is always invalidation, not caching.** Key cache entries
by everything they depend on (tenant + resource + version), and
invalidate explicitly on the write path rather than relying on a short
TTL to paper over staleness for data that needs to be fresh immediately
after a write.

## 5. Rate Limiting & Security

- Per-IP, per-tenant, *and* per-user limits — a single compromised or
  buggy client shouldn't be able to exhaust a limit shared across an
  entire tenant.
- Return `429` with a `Retry-After` hint, not a bare rejection.
- Enforce request size limits and timeouts; stream large
  uploads/downloads instead of buffering the whole body in memory.
- Standard security headers (CORS, CSP, HSTS) and strict input
  validation — reject unexpected fields early rather than silently
  ignoring them, which can hide a client-side bug.

## 6. Observability

Structured logs carrying a request/trace ID, not just a message string
— the ID is what lets you follow one request across services in a log
aggregator. Track the RED metrics per endpoint (Rate, Errors, Duration)
and set SLOs on latency percentiles and error budget, not just raw
error counts — a service can have a low error *rate* and still be
burning its error *budget* fast if traffic just spiked.

---

## REST vs. GraphQL vs. gRPC

| | REST | GraphQL | gRPC |
|---|---|---|---|
| Paradigm | Resource-oriented | Query-based | Service/RPC-oriented |
| Data fetching | Over/under-fetching risk; multiple round trips | Client specifies exact fields, one request | Strong contracts, less flexible ad-hoc queries |
| Payload | JSON | JSON | Protobuf (compact binary) |
| Transport | HTTP/1.1 | HTTP/1.1 | HTTP/2 (streaming, multiplexing) |
| Best fit | Public APIs, cacheable CRUD | Mobile/SPA clients needing tailored data | Internal high-performance service-to-service |

## Webhooks vs. Polling

Webhooks push events to the consumer instead of the consumer repeatedly
asking "anything new?" — right for real-time notifications and
async-workflow integrations, wrong for consumers behind a firewall that
can't receive inbound requests, or for ultra-high-volume low-value
events where the overhead of a webhook per event isn't worth it.
Basics: a subscription URL to register, retries with backoff on
delivery failure, signature verification so the consumer can trust the
payload actually came from you, and a small payload + follow-up fetch
for anything large rather than pushing the full object every time.

---

## Code Samples

Framework-agnostic API patterns — rate limiting, circuit breakers,
integration testing strategies:

- `code_samples/chapter-3/api_integration_testing.py`

Framework-specific examples live with their framework:
[Django code samples](django-drf.md#code-samples) · [FastAPI code samples](fastapi.md#code-samples).
