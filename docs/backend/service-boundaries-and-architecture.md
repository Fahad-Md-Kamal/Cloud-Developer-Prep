---
title: "Service Boundaries & Architecture"
---

# Service Boundaries & Architecture

Where one microservice ends and another begins, and how an API gateway
and a service mesh divide the traffic-handling work between them — as
questions you should be able to answer cold. FastAPI's own mechanics live in
[Dependency Injection & Background Tasks](python/fastapi-dependency-injection.md)
and [Performance & Production Patterns](python/fastapi-performance-patterns.md)
and aren't repeated here; general REST API design
(resource modeling, versioning, caching) lives in
[REST Deep Dive](../architecture/rest-deep-dive.md). This page is about the
architecture *around* the services, not the framework inside any one of them.

## 1. Domain-Driven Design and Bounded Contexts

**"How do you decide where one microservice ends and another begins?"**

```python
# Wrong axis: split by technical layer
class DocumentControllerService: ...
class DocumentDatabaseService: ...

# Right axis: split by business capability (bounded context)
class DocumentIngestionService: ...       # upload, OCR, initial metadata
class DocumentClassificationService: ...  # ML categorization
class SearchIndexService: ...             # indexing and query
```

**Answer:** Boundaries should follow business capabilities (bounded
contexts, in DDD terms), not technical layers — "everything about
ingesting a document" is a better seam than "everything that talks to
the database." A capability-aligned service owns its data and its
logic, and can be deployed, scaled, and staffed independently of the
others. Splitting by technical layer instead (a "controller service"
and a "database service") just recreates the monolith's coupling with
network calls in between.

| Pros | Cons / Trade-offs |
|---|---|
| A team can own a capability end-to-end without cross-team coordination for every change | Getting the boundary wrong early is expensive to undo — data and contracts calcify fast |
| Each service scales independently based on its own load pattern | Too many fine-grained services turns every feature into a multi-service change |
| Failure in one capability doesn't take down unrelated ones | Requires real domain knowledge up front, not just a technical org chart |

**Likely follow-up — "what's 'database per service' actually protecting
against?"** Shared databases are the most common way service boundaries
erode — two "independent" services silently coupled through the same
tables can't evolve their schemas separately, and a slow query in one
can degrade the other. Each service getting its own datastore (not
necessarily its own database technology) is what makes the boundary
real instead of nominal.

**Where FastAPI fits:** Django for the primary web app and
admin/back-office, FastAPI for a specific high-throughput or
async-heavy service (an AI/LLM gateway, a webhook processor) — not
mutually exclusive at the org level, treating FastAPI as one service
type among several here, not the only way to build a service. See
[Choosing a Python Web Framework](python/choosing-a-python-web-framework.md)
for the full decision.

## 2. API Gateway vs. Service Mesh

**"What's the difference between an API Gateway and a service mesh —
do you need both?"**

**Answer:** They solve traffic problems at different layers. An **API
Gateway** sits at the edge, between external clients and the system —
one entry point handling auth, rate limiting, request routing, and
protocol translation (public HTTPS in, internal gRPC out). A **service
mesh** (Envoy/Istio-style sidecars) handles *service-to-service* traffic
inside the system — mutual TLS, retries, load balancing, and
distributed tracing between internal services that never talk to an
external client directly. A small system usually needs only the
gateway; a mesh earns its operational overhead once there are enough
internal services that "which service is slow" stops being answerable
by reading logs. For the gateway side specifically — rate limiting,
circuit breaking, versioning — see
[API Gateway Architecture](api-gateway-architecture.md).

| Pros | Cons / Trade-offs |
|---|---|
| Gateway: one place to enforce auth/rate-limits instead of N | Gateway becomes a single point of failure and a latency hop for every request |
| Mesh: uniform retries/mTLS/observability without each service reimplementing them | Mesh adds a sidecar proxy per service — real memory/CPU/operational cost |
| Both: cross-cutting concerns move out of application code | Two extra systems to run, monitor, and debug when something's slow |

---

## Code Samples

Runnable examples in `code_samples/chapter-6/` (covering this page and
[Messaging: Kafka, Redis & AWS](messaging-kafka-redis-and-aws.md) /
[Inter-Service Communication](inter-service-communication.md)):

- `service_template.py` — a production FastAPI service skeleton: health
  checks, a `CircuitBreaker`, Postgres/Kafka dependency wiring, and
  config via `ServiceConfig`

```bash
pip install -r code_samples/chapter-6/requirements.txt
python code_samples/chapter-6/service_template.py
```
