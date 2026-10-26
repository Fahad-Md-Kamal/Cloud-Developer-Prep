---
title: "Distributed Crawling Architecture: Celery, Kafka & Ray"
---

# Distributed Crawling Architecture: Celery, Kafka & Ray

One machine crawling runs into real ceilings — bandwidth, CPU, and a
single IP's reputation with the target site all cap out eventually (see
[Web Crawling at Scale](web-crawling-at-scale.md)). Spreading the work
across many machines introduces three genuinely new problems that a
single process never had to solve: distributing tasks reliably, avoiding
duplicate work across workers that don't share memory, and surviving a
worker dying mid-task. Each tool below answers a different one of those.

## 1. "What problem does Celery actually solve here, and how is it different from a worker pool on one machine?"

**Answer:**

- This is exactly the
  [from-scratch worker pool to Celery](../python/worker-pools-and-backpressure.md#from-your-own-worker-pool-to-celery)
  jump already covered in Worker Pools & Backpressure — a crawling task
  queue is a direct application of that same pattern, not a different
  one.
- The shape stays identical: a queue of pending work, a set of workers
  pulling from it. What Celery adds for a *distributed* crawler
  specifically: the queue is a real broker (Redis/RabbitMQ) reachable
  from any machine, so crawl workers can run on an entire fleet instead
  of one process's thread pool, and a worker crashing mid-fetch doesn't
  lose that task — the broker redelivers it to another worker instead.
- Retries with backoff (a target site returning a 503, a timeout) and
  routing different task types (fetch vs. parse vs. store) to different
  worker pools come built in, rather than needing to be hand-rolled the
  way a single-process worker pool would need them.

## 2. "Where does Kafka actually fit, if Celery already handles task distribution?"

**Answer:**

- Celery is built for **discrete tasks** — "fetch this one URL," each
  with its own start and end. Kafka fits a different shape: a continuous
  **event log** — "a new URL was discovered" — that multiple independent
  systems can consume from at their own pace, without the producer
  needing to know who's listening or how many consumers there are.
- Concretely: a crawler discovering 50 new links on a page doesn't need
  to know whether those links feed a dedup checker, a priority scorer,
  and an archival system, or just one of them — it publishes "URL
  discovered" events, and each downstream system subscribes
  independently.
- See [Messaging: Kafka, Redis & AWS §1](../distributed-systems/messaging-kafka-redis-and-aws.md#1-choosing-between-kafka-and-redis)
  for the deeper mechanism of why Kafka fits this "many independent
  consumers, replayable log" shape specifically, versus a task queue's
  "one worker takes this task, then it's gone" model.
- In practice, a large crawling system often uses both at once: Kafka as
  the backbone for "URLs discovered" and "pages fetched" events, Celery
  (or an equivalent task queue) for the actual bounded fetch/parse work
  items pulled off the back of those events.

## 3. "What does Ray add that Celery's task-per-message model doesn't cover well?"

**Answer:**

- Celery's model is fundamentally **stateless per task** — each task
  message is self-contained, and a worker shouldn't assume anything
  persisted from the last task it ran.
- Ray is built around **actors** — a distributed object that holds state
  across many calls, running on a specific worker, callable repeatedly
  without re-establishing that state each time.
- This matters concretely for crawling when the state itself is
  expensive to set up: a headless browser session with cookies and login
  state already established is exactly the kind of thing worth keeping
  alive as a Ray actor and reusing across many page fetches, rather than
  paying the cost of a fresh browser launch and re-authentication per
  Celery task.
- The trade-off: an actor holding state is a single point of failure for
  that state specifically — if the actor's worker dies, whatever session
  state it held is gone, unlike Celery's stateless tasks where any
  worker can pick up the next one with no lost context.

## 4. "How do you avoid two workers crawling the same URL, when there's no shared memory between them?"

**Answer:**

- A shared, centralized **URL frontier** — the set of URLs already seen
  or queued — has to live somewhere every worker can check against, not
  in any single worker's local memory.
- Checking a growing set of billions of URLs for membership by storing
  every one explicitly gets expensive fast — the standard answer is a
  **Bloom filter**: a compact probabilistic structure that can say
  "definitely not seen" with certainty, or "probably seen" with a small,
  tunable false-positive rate, using a fraction of the memory a literal
  set of every URL would need.
- That false-positive trade-off is deliberate and usually acceptable
  here: occasionally skipping a URL that was actually new (a false
  positive) costs a little missed coverage; the alternative (storing
  every URL exactly) doesn't scale to real crawl sizes at all.
- The frontier itself is typically backed by the same broker already
  coordinating tasks (Redis, commonly) — a set-membership check plus
  enqueue happens atomically, so two workers racing to claim the same
  newly-discovered URL can't both win.

## 5. "A worker dies mid-fetch — what actually happens to its in-progress task?"

**Answer:**

- This is the same **visibility timeout** mechanism already covered for
  SQS: a task pulled off the queue becomes invisible to other workers
  for a configured window, and is automatically redelivered if that
  window expires without the task being marked complete. See
  [SQS: Standard vs FIFO, Visibility Timeout & DLQs](../cloud-devops/messaging-and-event-driven-services.md#sqs-standard-vs-fifo-visibility-timeout-dlqs)
  for the full mechanism — Celery's broker-backed task queues implement
  the identical idea under different naming.
- The practical tuning question is the same one raised there too: the
  timeout needs to be comfortably longer than a normal fetch takes (slow
  target site, large page), or a perfectly healthy worker gets its own
  in-progress task redelivered to someone else before it finishes —
  duplicate work, not a crash recovery.
- A **dead-letter queue** catches a task that's failed and been
  redelivered too many times (a permanently broken URL, a page that
  always times out) — without one, a genuinely unfetchable URL cycles
  through the retry loop forever instead of being flagged for a human to
  look at.

| Pros | Cons / Trade-offs |
|---|---|
| Celery gives durable, retryable, cross-machine task distribution for discrete fetch/parse work | Stateless by design — not a fit for anything that needs to reuse expensive per-session state |
| Kafka decouples "URL discovered" from however many downstream systems need to react to it | Genuinely new infrastructure to run, beyond whatever's already coordinating tasks |
| Ray's actors let an expensive browser session be set up once and reused across many fetches | An actor is a single point of failure for the state it holds |
| A Bloom filter makes frontier dedup practical at billions of URLs | Accepts a small, tunable false-positive rate — not a perfect guarantee |

---

## Code Samples

No dedicated code samples for this page.
