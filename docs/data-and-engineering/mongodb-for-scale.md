---
title: "MongoDB for Scale"
---

# MongoDB for Scale

Document schema design, aggregation pipeline performance, and
sharding — the MongoDB questions that come up once a system moves
past "just use the default collection shape."

## 1. "How do you decide document schema shape — embed or reference?"

```python
# Embed: bounded, always read together
{
    "_id": "post_1",
    "title": "...",
    "comments": [
        {"user": "alice", "text": "nice post", "at": "..."},
        {"user": "bob", "text": "agreed", "at": "..."},
    ],
}

# Reference: unbounded or independently-updated
{"_id": "post_1", "title": "...", "author_id": "user_42"}
```

**Answer:**

- Embed data that's bounded in size and almost always read together
  with its parent — a handful of comments read alongside a post.
- Reference (a separate collection, joined manually via `$lookup` or a
  second query) once the child data is unbounded, updated
  independently of the parent, or shared across many parents — an
  author referenced by thousands of posts shouldn't be duplicated into
  every one of them.
- MongoDB has no enforced foreign keys, so this is a design decision
  made once at schema time, not something the database catches for
  you later.

| Pros | Cons / Trade-offs |
|---|---|
| Embedding: one read gets everything, no join needed | Embedding an unbounded array risks hitting the 16MB document size limit |
| Referencing: no duplication, independent updates | Referencing needs `$lookup` or app-level joins — no enforced FK integrity |
| Schema shape can match actual read patterns exactly | Getting it wrong early means a real migration later, not a quick index add |

## 2. "What makes an aggregation pipeline slow, and how do you fix it?"

```python
pipeline = [
    {"$match": {"status": "completed", "created_at": {"$gte": start_date}}},  # early, indexed
    {"$project": {"customer_id": 1, "total": 1}},                             # shrink documents
    {"$group": {"_id": "$customer_id", "revenue": {"$sum": "$total"}}},
]
```

**Answer:**

- Put `$match` (and `$sort`, if it can use an index) as early as
  possible in the pipeline so MongoDB can use an index instead of
  scanning every document before filtering.
- `$project` early to drop fields the rest of the pipeline doesn't
  need, shrinking what flows through every later stage.
- Watch for stages that fundamentally can't use an index — `$group`
  and `$unwind` need the documents in hand first.
- Watch for an unbounded `$lookup` fanning out into a huge join with
  no matching filter.

## 3. "How does MongoDB scale writes and reads, and how do you pick a shard key?"

**Answer:**

- A replica set gives high availability and read scaling (routing
  reads to secondaries) but every write still goes through one
  primary — it doesn't scale write throughput.
- Sharding scales writes by partitioning data across multiple shards
  by a **shard key**, so different writes land on different machines.
- The shard key has to be high-cardinality and evenly distributed
  relative to actual query patterns — a monotonically increasing key
  (an auto-incrementing ID or a timestamp) sends all new writes to the
  same shard, creating a hot shard that defeats the whole point.

**Likely follow-up — "what if you picked the wrong shard key after the collection is already sharded?"**

- Expensive and risky — resharding a live, already-large sharded
  collection is real production work, not a config change.
- This is a decision worth getting right before data volume makes it
  painful to fix.

---

## Summary

- Schema shape (embed vs. reference) is a design decision with a real
  migration cost if it's wrong.
- Sharding scales writes, but only if the shard key actually
  distributes load — a poorly chosen key creates a hot shard that
  defeats the point of sharding at all.
