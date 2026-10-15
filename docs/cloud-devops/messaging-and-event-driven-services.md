---
title: "Messaging & Event-Driven Services: SQS, SNS, EventBridge, Kinesis & Amazon MQ"
---

# Messaging & Event-Driven Services: SQS, SNS, EventBridge, Kinesis & Amazon MQ

[Messaging: Kafka, Redis & AWS](../backend/messaging-kafka-redis-and-aws.md)
already covers the *design* questions — SQS vs Kafka, idempotent
consumers, the
[SNS fan-out pattern](../backend/messaging-kafka-redis-and-aws.md#4-aws-sns-vs-sqs-and-the-fan-out-pattern).
This page covers the specific service mechanics the exam actually asks
about: queue types, DLQs, and the services that don't come up in that
chapter at all — EventBridge, Kinesis, and Amazon MQ.

## SQS: Standard vs FIFO, Visibility Timeout & DLQs

|  | Standard | FIFO |
|---|---|---|
| Ordering | Best-effort, not guaranteed | Strict, within a message group |
| Delivery | At-least-once, can also duplicate | Exactly-once processing |
| Throughput | Nearly unlimited | Up to 3,000 msg/sec with batching |
| Name must end in | Anything | `.fifo` |

- **Visibility timeout** — once a consumer receives a message, it
  becomes invisible to other consumers for this window, so it isn't
  processed twice in parallel. If the consumer doesn't delete the
  message before the timeout expires (crash, or just slow processing),
  it becomes visible again and gets redelivered.

    !!! danger "Set this longer than your actual processing time"

        A visibility timeout shorter than how long the consumer actually
        takes to process a message guarantees duplicate processing under
        normal operation, not just on failure — the message becomes
        visible again and a second consumer picks it up while the first
        is still working. For a Lambda consumer, set it to at least 6×
        the function's timeout (AWS's own documented guidance), since
        Lambda may retry internally too.

- **Dead-letter queue (DLQ)** — after a message fails to process
  `maxReceiveCount` times, SQS moves it to a separate DLQ instead of
  retrying forever, so one poison-pill message can't block the queue
  indefinitely and the failure is visible somewhere instead of silently
  retried into oblivion.
- **Long polling vs short polling** — long polling (`WaitTimeSeconds >
  0`) holds the connection open until a message arrives or the timeout
  elapses, instead of returning empty immediately; cuts the number of
  empty API calls (and their cost) dramatically for a queue that isn't
  constantly full.

!!! success "The exam signal"

    "Strict ordering, exactly-once, e.g. processing financial
    transactions in sequence" → FIFO. "A function keeps processing the
    same message more than once" → visibility timeout set too short.
    "One malformed message is blocking the whole queue" → needs a DLQ.

## SNS: Filtering on Top of Fan-Out

[Fan-out](../backend/messaging-kafka-redis-and-aws.md#4-aws-sns-vs-sqs-and-the-fan-out-pattern)
already covers publishing once to many subscribed queues. **Subscription
filter policies** add selectivity on top of that: each subscriber
declares a filter (e.g. `{"orderType": ["international"]}`), and SNS
only delivers messages matching it — so one topic can fan out to five
subscribers, each only receiving the subset of events it actually cares
about, instead of every subscriber filtering out irrelevant messages
itself after receiving everything.

## EventBridge: Rules, Buses & Scheduling

A step beyond SNS — not just "publish to subscribers," but routing
events from many sources (AWS services, SaaS partners, your own
applications) to many targets based on the event's actual *content*.

- **Event bus** — where events land; the `default` bus receives events
  from AWS services automatically, or create a **custom bus** for your
  own application's events.
- **Rules** — match events by a pattern against the event's JSON
  content (not just a single attribute like SNS filtering) and route
  matches to one or more targets (Lambda, SQS, Step Functions, …).
- **Schema registry** — EventBridge can infer and store the schema of
  events flowing through it, so a consumer can generate code bindings
  instead of guessing the event's shape from examples.
- **EventBridge Scheduler** — cron-like scheduled invocations, the
  modern replacement for a CloudWatch Events cron rule.

!!! success "The exam signal"

    "Route events from many different AWS services and SaaS partners to
    many different targets, based on rich content matching" →
    EventBridge. A simple "notify several subscribers of one event" with
    no complex routing logic is still SNS's sweet spot — EventBridge
    wins once the routing itself has real conditional logic behind it.

## Kinesis: Streams, Firehose & Data Analytics

The AWS-managed streaming family —
[Kafka's AWS-managed equivalent](../backend/messaging-kafka-redis-and-aws.md#3-aws-sqs-vs-kafka-and-how-to-actually-handle-duplicate-events),
when replay and multiple independent consumers reading the same stream
are actually needed.

`Kinesis Data Streams`
:   The core service — a durable, ordered, replayable stream, retained
    from 24 hours up to 365 days. You manage **shards** (each a fixed
    throughput unit) and write your own consumer application.

`Kinesis Data Firehose`
:   Fully managed, no shards to manage — loads streaming data directly
    into a destination (S3, Redshift, OpenSearch) with optional
    transformation via Lambda along the way. No replay, no custom
    consumer code — it's a pipe, not a stream you read from yourself.

`Kinesis Data Analytics`
:   Runs SQL or Apache Flink queries directly against a streaming
    source, for real-time aggregation/analysis without first landing
    the data somewhere and querying it after the fact.

!!! success "The exam signal"

    "Needs to be read by multiple independent consumer applications,
    with replay" → Kinesis Data Streams. "Just needs to land streaming
    data into S3/Redshift reliably, no custom consumer" → Firehose.
    "Real-time analytics/aggregation on data while it's still in
    motion" → Data Analytics.

## Amazon MQ

A managed message broker for **ActiveMQ or RabbitMQ** specifically —
exists for one reason: migrating an existing application already built
against one of those brokers' own protocols (JMS, AMQP, MQTT, STOMP)
without rewriting it to use SQS/SNS's APIs.

!!! success "The exam signal"

    "Migrate an existing application using RabbitMQ/ActiveMQ to AWS with
    minimal code changes" → Amazon MQ. A new, greenfield application
    with no existing broker dependency → SQS/SNS, not Amazon MQ — there's
    no reason to take on a traditional broker's operational model when
    nothing requires its specific protocol.
