---
title: API Design Fundamentals
---

# API Design Fundamentals

Resource modeling, HTTP semantics, and versioning — framework-agnostic,
applies whether the implementation is Django, FastAPI, or anything
else. For framework-specific depth, see
[Frameworks → Django & DRF](django-orm.md) or
[Frameworks → FastAPI](fastapi-dependency-injection.md).

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
