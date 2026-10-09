---
title: "Consistency & Consensus"
---

# Consistency & Consensus

Picking a consistency model per use case instead of defaulting to
strong consistency everywhere, and knowing when a problem genuinely
needs a consensus protocol — part of the same distributed-systems
discussion as [Fault Tolerance Patterns](fault-tolerance-patterns.md).

## 1. Picking a Consistency Model Per Use Case

**"Does everything in a distributed system need to be strongly
consistent?"**

```python
event_log.append(Event(aggregate_id="doc-541", type="CLASSIFIED", payload={"tag": "Tax"}))
for event in event_log.replay():
    read_model.apply(event)  # projection can lag; rebuildable from the log
```

**Answer:** No — and treating everything as if it did is how systems
end up needlessly slow and coupled. Strong consistency earns its cost
where a stale read causes real harm (a balance, an inventory count,
anything billing touches). Everything else — a dashboard, a search
index, an activity feed — is a legitimate candidate for eventual
consistency via **event sourcing**: business events are appended to an
immutable log, and **read models** (projections) are derived from it
asynchronously. The read model can lag, but it's cheap to rebuild from
the log from scratch, which doubles as a disaster-recovery story —
replay the log instead of trying to repair corrupted derived state
directly.

| Pros | Cons / Trade-offs |
|---|---|
| Read models can lag without threatening correctness of the source of truth | Consumers must handle out-of-order/duplicate events — idempotency isn't optional |
| Rebuilding a projection from the log is a real recovery mechanism, not just a backup | The event log itself must never be lossy — it's now the actual source of truth |
| Full audit trail of every state change, for free | Querying "current state" directly against a log is awkward — you need the projection anyway |

## 2. When You Actually Need Consensus

**"When do you reach for a consensus protocol (Raft/Paxos) instead of
just eventual consistency?"**

**Answer:** When multiple nodes must agree on a single value and
*disagreeing* is unacceptable — leader election, a config/feature-flag
change that must not apply inconsistently across regions, or a schema
migration gate. You rarely implement Raft yourself; you rely on
something built on it (etcd, Zookeeper, Spanner, a managed consensus
service) and reason about the trade-off it exposes: a quorum (e.g., 2 of
3 nodes) tolerates the minority failing, at the cost of every write
needing a round trip to a majority of nodes — more latency than a
single node ever needs, in exchange for surviving a node failure without
split-brain.

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
