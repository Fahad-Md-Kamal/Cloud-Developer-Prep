---
title: "Messaging: Kafka, Redis & AWS (SQS/SNS)"
---

# Messaging: Kafka, Redis & AWS (SQS/SNS)

Choosing between Kafka and Redis as a queue, evolving an event's shape
without breaking consumers, and the AWS-managed equivalents (SQS, SNS)
— the messaging decisions that hold an event-driven system together.
Part of the same architecture discussion as
[Service Boundaries & Architecture](service-boundaries-and-architecture.md)
and [Inter-Service Communication](inter-service-communication.md).

## 1. Choosing Between Kafka and Redis

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
([Practical Patterns §3](python/practical-patterns.md#3-when-do-you-reach-for-celery-instead-of-just-handling-something-in-the-request))
is often enough on its own.

## 2. Schema Evolution for Long-Lived Event Streams

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
[database migration](../architecture/refactoring-legacy-systems.md#database-migration-dual-read-dual-write),
applied to a message format instead of a table.

## 3. AWS SQS vs. Kafka, and How to Actually Handle Duplicate Events

**"Where have you used AWS SQS, and how does it differ from Kafka?"**

**Answer:**

- This is the AWS-managed version of
  [§1's Kafka-vs-Redis decision](#1-choosing-between-kafka-and-redis),
  with SQS playing Redis's role — a simple, durable, point-to-point
  queue with no partitioning or consumer-group concepts to manage.
- **SQS**: fully managed, scales transparently, messages are deleted
  once consumed (or after a visibility timeout expires and they're
  redelivered) — no replay, no multiple independent consumer groups
  reading the same stream at different offsets.
- **Kafka**: a durable, replayable log — multiple independent consumer
  groups can read the same topic at their own pace, and a consumer can
  rewind and reprocess history. This is the capability SQS fundamentally
  doesn't have, and it's the real reason to reach for Kafka (or
  Kinesis, its AWS-managed equivalent) over SQS: needing replay, or
  needing the *same* event stream read by several independent systems
  without an [SNS fan-out](#4-aws-sns-vs-sqs-and-the-fan-out-pattern)
  in front of it.
- **Operational trade-off**: SQS requires essentially no operational
  decisions — create a queue, send, receive. Kafka (or Kinesis)
  requires partition-count and retention decisions up front, the same
  "don't reach for the heavier tool before you need its specific
  capability" judgment as §1.

**"How does event-driven architecture actually work, and how do you handle duplicate events?"**

```python
# The naive version -- processes every message exactly as delivered.
# At-least-once delivery (SQS, Kafka, SNS) means a message CAN be
# delivered more than once -- a consumer crash after processing but
# before acknowledging is enough to trigger redelivery.
def handle_order_placed(event):
    charge_customer(event["order_id"], event["amount"])  # runs twice -> double charge

# The idempotent version -- the operation is made safe to run more than once.
def handle_order_placed(event):
    if ProcessedEvent.objects.filter(event_id=event["event_id"]).exists():
        return  # already handled -- this is a redelivery, not a new event
    with transaction.atomic():
        charge_customer(event["order_id"], event["amount"])
        ProcessedEvent.objects.create(event_id=event["event_id"])
```

**Answer:**

- Event-driven architecture means a service publishes a fact ("order
  placed") without knowing or caring who reacts to it — each consumer
  independently decides what to do when that fact occurs, the same
  decoupling [Observer](../architecture/design-patterns.md#observer)
  provides inside a single process, at the scale of whole services.
- **The duplicate-event problem is not an edge case — it's the default
  guarantee.** Virtually every real message system (SQS, Kafka, SNS)
  offers **at-least-once** delivery, not exactly-once: a consumer that
  crashes after processing a message but before acknowledging it will
  see that message redelivered. Design for this up front, don't treat
  it as a rare failure to patch later.
- **The actual fix is idempotency, not "try to prevent duplicates"** —
  trying to guarantee exactly-once delivery at the messaging layer is
  the wrong layer to solve it at. Instead, make *handling* a duplicate
  safe: record the event's unique ID as having been processed (in the
  same transaction as the side effect itself, as in the example above)
  and check that record before acting, so redelivery becomes a cheap
  no-op instead of a double-charge.
- This is the same pattern named in passing in
  [Inter-Service Communication's Saga Pattern](inter-service-communication.md#2-the-saga-pattern-for-distributed-transactions)
  ("compensating actions must be idempotent") — this is the concrete
  mechanism behind that requirement, not just the name of it.

## 4. AWS SNS vs. SQS, and the Fan-Out Pattern

**"Describe the difference between SNS and SQS in terms of architecture."**

```
# SQS alone: one queue, work consumed once -- a point-to-point queue
Producer -> [SQS Queue] -> Consumer

# SNS + SQS fan-out: one event, multiple independent consumers
                 +-> [SQS Queue A] -> Service A (e.g. billing)
Producer -> [SNS Topic] -+-> [SQS Queue B] -> Service B (e.g. analytics)
                 +-> [SQS Queue C] -> Service C (e.g. notifications)
```

**Answer:**

- **SQS** is a queue — a point-to-point hand-off. A message put on a
  queue is delivered to (and removed by) exactly one consumer. This is
  the AWS-native equivalent of the Redis task-queue role from
  [§1 above](#1-choosing-between-kafka-and-redis): one producer, work
  consumed once.
- **SNS** is a pub/sub topic — a publisher sends one message to a
  topic, and the topic pushes a copy to *every* subscriber, with no
  single subscriber "consuming" it away from the others. On its own,
  SNS has no durable storage or retry queue — if a subscriber is down
  when the message is published, that subscriber simply misses it.
- **The fan-out pattern** combines both: publish once to an SNS topic,
  and subscribe multiple SQS queues to that topic — each queue gets
  its own durable copy of every message. This is the AWS-native way to
  get Kafka's "same event reaches multiple independent consumers"
  property ([§1](#1-choosing-between-kafka-and-redis)) without running
  Kafka: SNS does the broadcasting, SQS gives each consumer its own
  durable, retriable, independently-scaled queue to work through at
  its own pace.
- **Why not subscribe services directly to SNS without SQS in
  between?** Durability and backpressure — a direct SNS subscription
  (HTTP endpoint, Lambda) has to process a message essentially
  immediately or risk it being retried and eventually dropped per
  SNS's own retry policy. Putting an SQS queue between the topic and
  the consumer means a slow or temporarily-down consumer doesn't lose
  messages — they sit durably in its queue until it catches up.

| | SQS alone | SNS + SQS fan-out |
|---|---|---|
| Delivery | One message to one consumer | One message to every subscribed queue |
| Use when | A single, well-defined worker does the work | Multiple independent services each need to react to the same event |
| Failure isolation | N/A — one consumer | A slow/down consumer's queue backs up without affecting the others |

---

## Code Samples

Runnable examples in `code_samples/chapter-6/` (shared with
[Service Boundaries & Architecture](service-boundaries-and-architecture.md) /
[Inter-Service Communication](inter-service-communication.md)):

- `event_driven_system.py` — `KafkaEventBus`, `EventStore`, and a full
  `SagaOrchestrator` with compensating steps for document processing
- `message_queues.py` — `KafkaMessageProducer`/`KafkaMessageConsumer`
  and a `RedisTaskQueue`, side by side, sharing one `TaskWorker`
- `docker-compose.yml` / `requirements.txt` — local Kafka + Redis for
  running the examples above

```bash
pip install -r code_samples/chapter-6/requirements.txt
docker-compose -f code_samples/chapter-6/docker-compose.yml up -d
python code_samples/chapter-6/event_driven_system.py
```
