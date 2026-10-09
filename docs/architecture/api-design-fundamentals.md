---
title: API Design Fundamentals
---

# API Design Fundamentals

Resource modeling, HTTP semantics, and versioning — framework-agnostic,
applies whether the implementation is Django, FastAPI, or anything
else. For framework-specific depth, see
[Frameworks → Django & DRF](../backend/python/django-orm.md) or
[Frameworks → FastAPI](../backend/python/fastapi-dependency-injection.md).

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

## 4. "What's the actual purpose of using REST?"

**Answer:**

- A uniform, resource-oriented interface that lets client and server
  evolve independently — the client only needs to understand
  resources, URIs, and a small, standard set of HTTP verbs/status
  codes, not a bespoke contract per endpoint.
- Statelessness — each request carries everything needed to
  understand it, with no server-side session required to interpret
  it — is the real enabler of horizontal scaling: any server instance
  can handle any request, so load balancing never needs sticky
  sessions.
- The RPC-style alternative (§1's "Bad" example) works too, but
  couples client and server to a growing list of bespoke method names
  instead of a small, predictable set of verbs applied consistently
  across every resource — the thing that makes a well-designed REST
  API's next endpoint guessable without reading its docs.

**"What are the main components of REST?"**

- **Resources** — everything addressable is a noun with a URI
  (`/documents/{id}`), not a verb (§1).
- **A uniform interface** — the same small set of HTTP methods
  (`GET`/`POST`/`PUT`/`PATCH`/`DELETE`) means the same thing on every
  resource, rather than each endpoint inventing its own semantics.
- **Representations** — a client interacts with a *representation* of
  a resource's state (typically JSON), not the resource itself. The
  same resource can have multiple representations (JSON, XML, a
  paginated vs. full view) without changing what resource it is.
- **Statelessness** — covered above: no server-side session required
  to interpret a request.
- **(Rarely implemented in practice) HATEOAS** — responses include
  links to related actions/resources, so a client discovers what it
  can do next from the response itself rather than from hardcoded
  knowledge of the API's URL structure. Most real-world "REST" APIs
  skip this — it's worth naming as the most commonly-omitted part of
  the original REST definition, not something to claim you've built
  unless it's actually there.

**"What's the difference between stateful and stateless, concretely?"**

```
# Stateless -- every request is fully self-contained
GET /orders/42
Authorization: Bearer <token>          # the token IS the identity, every time

# Stateful (the alternative REST avoids) -- server remembers prior requests
POST /login                             # server creates a session, stores it server-side
GET /orders/42
Cookie: session_id=abc123               # server looks up session state to know who this is
```

- **Stateless**: the server holds no memory of a client between
  requests — every request carries everything needed to authenticate
  and process it (a bearer token, not a server-side session lookup).
  Any server instance can handle any request, which is what makes load
  balancing trivial — no "sticky sessions" requirement.
- **Stateful**: the server stores per-client state (a session) between
  requests, and the client refers back to it (a session cookie). The
  *server* has to remember the conversation, which means a load
  balancer must route a given client back to the *same* server
  instance — or the session store itself has to be a shared, external
  system (Redis), adding infrastructure just to keep statelessness's
  scaling property.
- REST's statelessness constraint is specifically about this — not
  "the application has no state anywhere" (a database is state), but
  "the server process handling this specific request doesn't need to
  remember the previous one to process it correctly."

**"How does gRPC compare to REST?"** — covered in depth, with a full
comparison table against GraphQL/SOAP/WebSocket/SSE too, in
[API Paradigms & Patterns §4](api-paradigms-and-patterns.md#4-grpc).
