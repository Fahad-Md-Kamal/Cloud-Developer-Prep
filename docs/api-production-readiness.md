---
title: API Production Readiness
---

# API Production Readiness

Caching, rate limiting, and observability — what turns a working API
into one that survives real production traffic. For resource modeling
and versioning, see
[API Design Fundamentals](api-design-fundamentals.md).

## 1. Caching

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

## 2. Rate Limiting & Security

- Per-IP, per-tenant, *and* per-user limits — a single compromised or
  buggy client shouldn't be able to exhaust a limit shared across an
  entire tenant.
- Return `429` with a `Retry-After` hint, not a bare rejection.
- Enforce request size limits and timeouts; stream large
  uploads/downloads instead of buffering the whole body in memory.
- Standard security headers (CORS, CSP, HSTS) and strict input
  validation — reject unexpected fields early rather than silently
  ignoring them, which can hide a client-side bug.

## 3. Observability

Structured logs carrying a request/trace ID, not just a message string
— the ID is what lets you follow one request across services in a log
aggregator. Track the RED metrics per endpoint (Rate, Errors, Duration)
and set SLOs on latency percentiles and error budget, not just raw
error counts — a service can have a low error *rate* and still be
burning its error *budget* fast if traffic just spiked.

---

## Code Samples

Framework-agnostic API patterns — rate limiting, circuit breakers,
integration testing strategies:

- `code_samples/chapter-3/api_integration_testing.py`

Framework-specific examples live with their framework:
[Django code samples](django-drf.md#code-samples) ·
[FastAPI code samples](fastapi-dependency-injection.md#code-samples).
