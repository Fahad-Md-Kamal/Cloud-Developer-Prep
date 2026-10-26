---
title: "Inter-Service Communication"
---

# Inter-Service Communication

Sync vs. async calls, the Saga pattern for cross-service transactions,
and service discovery — how independent services actually talk to each
other once [Service Boundaries & Architecture](service-boundaries-and-architecture.md)
has drawn the lines between them.

## 1. Synchronous vs. Asynchronous, and the Hybrid Middle Ground

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

## 2. The Saga Pattern for Distributed Transactions

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
| Both: failures are recoverable instead of leaving half-applied state | Both: compensating actions must be idempotent — a saga step can be retried or replayed, the exact mechanism covered in [Messaging §3](messaging-kafka-redis-and-aws.md#3-aws-sqs-vs-kafka-and-how-to-actually-handle-duplicate-events) |

## 3. Service Discovery and Inter-Service Load Balancing

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

Runnable examples in `code_samples/chapter-6/` (shared with
[Service Boundaries & Architecture](service-boundaries-and-architecture.md) /
[Messaging: Kafka, Redis & AWS](messaging-kafka-redis-and-aws.md)):

- `service_communication.py` — `RoundRobinLoadBalancer`/
  `WeightedRandomLoadBalancer`/`LeastConnectionsLoadBalancer`, a
  `CircuitBreaker`, a retrying `ResilientHttpClient`, and an in-memory
  `ServiceRegistry`

```bash
pip install -r code_samples/chapter-6/requirements.txt
python code_samples/chapter-6/service_communication.py
```
