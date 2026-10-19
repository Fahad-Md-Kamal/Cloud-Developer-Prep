---
title: "Consistency & Consensus"
---

# Consistency & Consensus

Picking a consistency model per use case instead of defaulting to
strong consistency everywhere, and knowing when a problem genuinely
needs a consensus protocol — part of the same distributed-systems
discussion as [Fault Tolerance Patterns](fault-tolerance-patterns.md).

## 1. The Consistency Spectrum: From Strong to Eventual

Not every piece of data in a system needs the same guarantee. There's a
whole range of options between "always exactly right, everywhere,
instantly" and "right eventually, no promise of when" — and the right
choice is made **per feature**, not once for the entire system.

`Strong consistency`
:   Every read gets the latest write, everywhere, as if there's only
    one copy of the data in the world. The most expensive option —
    slower, and less able to keep serving during a network problem.
    Worth paying for where being wrong actually hurts: a bank balance,
    how many items are left in stock, anything billing touches.

`Causal consistency`
:   Operations that are genuinely related to each other (a comment,
    then a reply to that comment) are always seen in the right order
    by everyone. Operations with no relationship to each other can
    still show up in different orders for different people. Cheaper
    than strong consistency, but still respects cause and effect.

`Read-your-own-writes`
:   After you make a change, you always see that change the next time
    you read — even if other people might not see it yet. You post a
    comment and see it appear immediately; a friend loading the same
    page a moment later might not, yet.

`Monotonic reads`
:   Once you've seen a value, a later read never shows you something
    *older* than what you already saw — even if that later read
    happens to land on a different, lagging copy of the data. Without
    this guarantee, simply refreshing a page could show you something
    older than what you already had on screen.

`Session consistency`
:   Read-your-own-writes and monotonic reads together, guaranteed for
    the length of one user's session. This is what most apps that
    "feel" perfectly consistent are actually delivering underneath —
    not full strong consistency, just a guarantee scoped to you.

`Eventual consistency`
:   The loosest useful guarantee: if nothing new gets written, every
    copy of the data will *eventually* agree — with no promise of
    exactly when. The cheapest, fastest, and most available option,
    and the right fit for most read-heavy, non-financial data (a
    dashboard, a search index, an activity feed).

`Bounded staleness`
:   Eventual consistency with a number attached — "never more than 5
    seconds behind" or "never more than 100 writes behind," instead of
    an open-ended "eventually." Some managed databases (Azure Cosmos
    DB) offer this as a setting you pick directly.

**The question that actually picks one:** for this specific piece of
data, what really breaks if it's wrong for a few seconds? A like-count
being off by a few is fine — eventual consistency. A payment being
charged twice is not — strong consistency. That answer, asked per
feature, is the actual design decision; a textbook default isn't.

## 2. Eventual Consistency in Practice: Event Sourcing

**"Does everything in a distributed system need to be strongly
consistent?"**

```python
event_log.append(Event(aggregate_id="doc-541", type="CLASSIFIED", payload={"tag": "Tax"}))
for event in event_log.replay():
    read_model.apply(event)  # projection can lag; rebuildable from the log
```

**Answer:** No. One concrete way to actually build eventual consistency,
rather than just describe it, is **event sourcing**:

- Every business event gets appended to an immutable, ordered log —
  this log is the one source of truth, never edited after the fact.
- A **read model** (a "projection") is built from that log, separately,
  and kept up to date by replaying new events as they arrive.
- The read model is allowed to lag a little behind the log — that lag
  *is* the eventual-consistency window from §1.
- Because the read model is just a replay of the log, it's cheap to
  throw away and rebuild from scratch — which doubles as a disaster
  recovery plan: if a projection gets corrupted, replay the log into a
  fresh one instead of trying to repair broken derived state directly.

| Pros | Cons / Trade-offs |
|---|---|
| A read model can lag without threatening the correctness of the source of truth | Consumers must handle events arriving out of order or more than once — idempotency isn't optional |
| Rebuilding a projection from the log is a real recovery mechanism, not just a backup | The event log itself must never lose data — it's now the actual source of truth |
| A full audit trail of every change, for free | Querying "the current state" directly against a raw log is awkward — you need the projection anyway |

## 3. When You Actually Need Consensus

**"When do you reach for a consensus protocol (Raft/Paxos) instead of
just eventual consistency?"**

**Answer:** When several nodes must agree on one single value, and
disagreeing is genuinely not an option — electing a leader, rolling out
a config or feature-flag change that can't apply inconsistently across
regions, or gating a schema migration.

- You rarely implement Raft or Paxos yourself — you rely on something
  already built on one (etcd, Zookeeper, Spanner, a managed consensus
  service) and reason about the trade-off it hands you.
- That trade-off is the **quorum**: a majority of nodes (say, 2 out of
  3) has to agree before a write is accepted. This means the system can
  survive a minority of nodes failing without ever having two nodes
  both think they're in charge at once (**split-brain**) — but every
  write now needs a round trip to a majority of nodes first, which is
  real added latency a single node would never need to pay.

---

## Code Samples

Runnable examples in `code_samples/chapter-7/` (shared with
[Fault Tolerance Patterns](fault-tolerance-patterns.md) /
[Load Balancing & Auto-Scaling](load-balancing-and-autoscaling.md) /
[Data & Capacity Scaling](data-and-capacity-scaling.md)):

- `consistency_strategies.py` — `EventLog`/`ReadModel` (event sourcing +
  projection) and a `ConsensusCoordinator` (quorum voting)

```bash
pip install -r code_samples/chapter-7/requirements.txt
python code_samples/chapter-7/consistency_strategies.py
```
