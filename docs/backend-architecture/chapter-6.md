---
title: "Chapter 6: Microservices Design with FastAPI & Message Queues (Kafka/Redis)"
---

# Chapter 6: Microservices Design with FastAPI & Message Queues (Kafka/Redis)

Service boundaries, inter-service communication, and the messaging
patterns (Kafka, Redis) that hold a microservices system together — as
questions you should be able to answer cold. FastAPI's own mechanics live in
[Dependency Injection & Background Tasks](../programming-languages/python/fastapi-dependency-injection.md)
and [Performance & Production Patterns](../programming-languages/python/fastapi-performance-patterns.md)
and aren't repeated here; general REST API design
(resource modeling, versioning, caching) lives in
[API Design Fundamentals](../core-engineering-foundations/api-design-fundamentals.md). This chapter is about the architecture
*around* the services, not the framework inside any one of them.

---

## Part 1: Service Boundaries

### 1. Domain-Driven Design and Bounded Contexts

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

### 2. API Gateway vs. Service Mesh

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
by reading logs.

| Pros | Cons / Trade-offs |
|---|---|
| Gateway: one place to enforce auth/rate-limits instead of N | Gateway becomes a single point of failure and a latency hop for every request |
| Mesh: uniform retries/mTLS/observability without each service reimplementing them | Mesh adds a sidecar proxy per service — real memory/CPU/operational cost |
| Both: cross-cutting concerns move out of application code | Two extra systems to run, monitor, and debug when something's slow |

---

## Part 2: Messaging with Kafka and Redis

### 3. Choosing Between Kafka and Redis

**"A service needs to hand work off asynchronously — when do you reach
for Kafka, and when is Redis enough?"**

```python
# Redis: simple task queue, fire-and-forget, short retention
redis_queue.enqueue("process_document", doc_id=doc.id, priority="high")

# Kafka: durable event log, multiple independent consumers, replay
producer.send("document.events", key=doc.id, value={"type": "UPLOADED", "doc_id": doc.id})
```

**Answer:** Redis (as a queue, via RQ/Celery's broker) fits a
straightforward task hand-off — one producer, one consumer group, work
gets done once and the message is gone. Kafka fits when the *same
event* needs to reach multiple independent consumers (analytics, search
indexing, and notifications all reacting to "document uploaded" without
knowing about each other), when messages need to be replayed or
reprocessed, or when throughput and durability guarantees matter more
than latency. Kafka's log is retained and replayable; a Redis queue's
job disappears the moment it's consumed.

**Likely follow-up — "why not just use Kafka for everything, then?"**
Operational weight. Kafka needs partitioning, consumer-group, and
offset-management decisions Redis doesn't — reaching for it to send one
background job (send this email) is solving a problem you don't have
yet. For a single-process, no-fan-out background job, plain Celery
([Practical Patterns §3](../programming-languages/python/practical-patterns.md#3-when-do-you-reach-for-celery-instead-of-just-handling-something-in-the-request))
is often enough on its own.

### 4. Schema Evolution for Long-Lived Event Streams

**"A Kafka topic has been running in production for a year. How do you
change the event shape without breaking every consumer?"**

```python
# Additive change: safe -- old consumers ignore the new field
{"type": "DOCUMENT_CLASSIFIED", "doc_id": "541", "tag": "Tax", "confidence": 0.94}

# Breaking change: needs a new event type/version, not an in-place rename
{"type": "DOCUMENT_CLASSIFIED_V2", "doc_id": "541", "category": {"primary": "Tax"}}
```

**Answer:** A schema registry (Avro/Protobuf with backward/forward
compatibility checks) enforces this at write time instead of
discovering it in production. The safe changes are additive — new
optional fields old consumers simply ignore. Renaming, retyping, or
removing a field is a breaking change; it needs a new event type or
version field, with both old and new shapes coexisting until every
consumer has migrated, then a deprecation timeline for the old shape —
the same dual-write discipline as a
[database migration](../core-engineering-foundations/refactoring-legacy-systems.md#database-migration-dual-read-dual-write),
applied to a message format instead of a table.

---

## Part 3: Inter-Service Communication

### 5. Synchronous vs. Asynchronous, and the Hybrid Middle Ground

**"When would you use a REST call between two services instead of an
event, and vice versa?"**

**Answer:** Synchronous REST gives immediate consistency and a simple
failure mode (the caller knows right away if it failed) but couples the
caller's availability to the callee's — if the downstream service is
slow or down, the caller is too. Asynchronous events decouple that — the
publisher doesn't wait, and a consumer being down just means a backlog,
not an outage — at the cost of eventual consistency and harder-to-trace
failures. Most real systems mix both: a synchronous call for anything
the user is waiting on an answer for right now (place an order), and
events for everything that can happen a moment later (send the
confirmation email, update analytics, warm a cache).

### 6. The Saga Pattern for Distributed Transactions

**"An order touches inventory, payment, and shipping services — none
share a database. How do you keep that consistent, and what happens
when payment fails after inventory is already reserved?"**

```python
class OrderSaga:
    async def run(self, order: Order) -> None:
        await inventory.reserve(order)
        try:
            await payment.charge(order)
        except PaymentFailed:
            await inventory.release(order)  # compensating action
            raise
        await shipping.schedule(order)
```

**Answer:** There's no distributed transaction across independent
databases, so a Saga breaks the operation into a sequence of local
transactions, each with a **compensating action** that undoes it if a
later step fails — `inventory.release` compensates `inventory.reserve`.
**Choreography** lets each service publish an event and react to
others' events with no central coordinator — simple for a few steps,
but "what's the current state of this order?" gets hard to answer as
steps grow. **Orchestration** uses a saga manager that explicitly calls
each step and its compensation — more visibility and easier debugging,
at the cost of a coordinator that's now a dependency (and needs its own
high availability) for every saga it runs.

| Pros | Cons / Trade-offs |
|---|---|
| Choreography: no single point of failure, services stay fully decoupled | Choreography: transaction state is implicit, spread across every participant's logs |
| Orchestration: one place to see and debug the whole transaction's state | Orchestration: the coordinator is now a critical dependency for every saga |
| Both: failures are recoverable instead of leaving half-applied state | Both: compensating actions must be idempotent — a saga step can be retried or replayed |

### 7. Service Discovery and Inter-Service Load Balancing

**"Service A needs to call Service B, which has five replicas that
scale up and down. How does A find a healthy instance?"**

**Answer:** Client-side discovery (A queries a registry — Consul/etcd/
Kubernetes DNS — and picks an instance itself) or server-side discovery
(A always calls a fixed address; a load balancer or the service mesh
resolves it to a live instance). Kubernetes' built-in Service
abstraction is server-side discovery via DNS + iptables/IPVS, which is
why most teams don't hand-roll this anymore. Whichever mechanism, it
needs to be health-aware — a registry entry for an instance that's up
but not ready to serve traffic is worse than no entry at all, since
requests get routed straight into failures.

---

## Code Samples

Runnable examples in `code_samples/chapter-6/`:

- `service_template.py` — a production FastAPI service skeleton: health
  checks, a `CircuitBreaker`, Postgres/Kafka dependency wiring, and
  config via `ServiceConfig`
- `service_communication.py` — `RoundRobinLoadBalancer`/
  `WeightedRandomLoadBalancer`/`LeastConnectionsLoadBalancer`, a
  `CircuitBreaker`, a retrying `ResilientHttpClient`, and an in-memory
  `ServiceRegistry`
- `event_driven_system.py` — `KafkaEventBus`, `EventStore`, and a full
  `SagaOrchestrator` with compensating steps for document processing
- `message_queues.py` — `KafkaMessageProducer`/`KafkaMessageConsumer`
  and a `RedisTaskQueue`, side by side, sharing one `TaskWorker`
- `observability.py` — a `Tracer`/`TraceSpan` pair, `MetricsCollector`,
  `StructuredLogger`, and `HealthMonitor`
- `docker-compose.yml` / `requirements.txt` — local Kafka + Redis for
  running the examples above

```bash
pip install -r code_samples/chapter-6/requirements.txt
docker-compose -f code_samples/chapter-6/docker-compose.yml up -d
python code_samples/chapter-6/service_template.py
python code_samples/chapter-6/event_driven_system.py
```

---

## Summary

1. **Service boundaries** follow business capabilities, not technical
   layers — database-per-service is what makes a boundary real instead
   of nominal.
2. **API Gateway** handles edge traffic; a **service mesh** handles
   service-to-service traffic — most systems need the former long
   before they need the latter.
3. **Kafka** fits durable, multi-consumer, replayable event streams;
   **Redis** fits a simple task hand-off — reach for the heavier tool
   only when fan-out or replay is a real requirement.
4. **Schema evolution** needs the same additive-first, dual-shape
   discipline as a database migration.
5. **Sagas** replace distributed transactions with a sequence of local
   transactions and explicit compensating actions — choreography and
   orchestration trade decentralization for visibility.
6. **Service discovery** must be health-aware, or a load balancer will
   happily route traffic into an instance that's up but not ready.
