---
title: "Wide-Column Stores (Cassandra)"
---

# Wide-Column Stores (Cassandra)

Cassandra looks like a table with rows and columns, which makes it
tempting to reason about like a relational table with looser rules.
It isn't — the storage engine underneath it is built around a
completely different question than Postgres asks, and that's what
actually explains its no-joins rule, its write speed, and its most
common production failure mode (a "hot partition"). Mechanism first,
modeling practice after.

## How Cassandra Actually Stores a Write: the LSM-Tree

Every write hits two places **at the same time**: an append-only
**commit log** on disk (pure durability — if the process crashes, this
is replayed to recover anything not yet flushed) and an in-memory,
sorted **memtable** (what actually serves reads of recent data). Neither
is updated in place — Cassandra never seeks to an existing row on disk
and rewrites it.

Once a memtable fills up, it **flushes** to disk as a new, immutable
**SSTable** (Sorted String Table) — a file that, once written, is never
modified again. Over time a node accumulates many SSTables, and a
background process called **compaction** periodically merges them,
combining overlapping keys and discarding data that's been overwritten
or deleted (Cassandra's deletes are actually a special marker called a
**tombstone**, physically removed only once compaction processes it).

<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of Cassandra's LSM-tree write path: a write going to the commit log and memtable at once, the memtable later flushing to a new SSTable, and compaction merging SSTables together" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="360" y="20" width="180" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="450" y="53" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">New Write</text>
<line x1="420" y1="75" x2="250" y2="140" stroke="#9aa5b3" stroke-width="2"></line>
<line x1="480" y1="75" x2="650" y2="140" stroke="#9aa5b3" stroke-width="2"></line>
<rect x="130" y="140" width="240" height="60" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="250" y="166" font-size="14" font-weight="600" text-anchor="middle" fill="#7a5c14">Commit Log</text>
<text x="250" y="186" font-size="12" text-anchor="middle" fill="#7a5c14">append-only, disk</text>
<rect x="530" y="140" width="240" height="60" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="3"><animate attributeName="stroke" values="#2f6fb3;#2f6fb3;#9aa5b3;#9aa5b3" keyTimes="0;0.33;0.36;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="650" y="166" font-size="14" font-weight="600" text-anchor="middle" fill="#1d4a78">Memtable</text>
<text x="650" y="186" font-size="12" text-anchor="middle" fill="#1d4a78">sorted, in-memory</text>
<circle r="9" fill="#d9822b" cy="110"><animate attributeName="cx" values="450;250;450;450" keyTimes="0;0.12;0.16;1" dur="18s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.02;0.12;0.16;1" dur="18s" repeatCount="indefinite"></animate></circle>
<circle r="9" fill="#2f6fb3" cy="110"><animate attributeName="cx" values="450;650;650;450" keyTimes="0;0.12;0.16;1" dur="18s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.02;0.12;0.16;1" dur="18s" repeatCount="indefinite"></animate></circle>
<line x1="650" y1="200" x2="650" y2="260" stroke="#9aa5b3" stroke-width="2" stroke-dasharray="5,5"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.33;0.36;0.63;0.66;1" dur="18s" repeatCount="indefinite"></animate></line>
<rect x="130" y="260" width="200" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="230" y="286" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">SSTable A</text>
<text x="230" y="304" font-size="12" text-anchor="middle" fill="#5b6472">older, immutable, disk</text>
<rect x="550" y="260" width="200" height="55" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.33;0.36;0.63;0.66;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="650" y="286" font-size="14" font-weight="600" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.33;0.36;0.63;0.66;1" dur="18s" repeatCount="indefinite"></animate>SSTable B</text>
<text x="650" y="304" font-size="12" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.33;0.36;0.63;0.66;1" dur="18s" repeatCount="indefinite"></animate>just flushed, disk</text>
<line x1="280" y1="315" x2="380" y2="375" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.69;1" dur="18s" repeatCount="indefinite"></animate></line>
<line x1="620" y1="315" x2="520" y2="375" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.69;1" dur="18s" repeatCount="indefinite"></animate></line>
<rect x="280" y="375" width="240" height="55" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.69;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="400" y="401" font-size="14" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.69;1" dur="18s" repeatCount="indefinite"></animate>Compacted SSTable</text>
<text x="400" y="419" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.69;1" dur="18s" repeatCount="indefinite"></animate>obsolete/deleted data discarded</text>
<text x="450" y="450" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.30;0.33;1" dur="18s" repeatCount="indefinite"></animate>Every write goes to the commit log (durability) and the memtable (speed) at once.</text>
<text x="450" y="450" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.33;0.36;0.63;0.66;1" dur="18s" repeatCount="indefinite"></animate>Once full, the memtable flushes to disk as a new, immutable SSTable.</text>
<text x="450" y="450" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.69;1" dur="18s" repeatCount="indefinite"></animate>Compaction later merges SSTables, discarding overwritten or deleted data.</text>
</svg>

!!! success "Why this is the mechanism behind Cassandra's reputation for fast writes"

    A write never seeks to an existing location on disk to update it —
    it's always a sequential append to the commit log plus an in-memory
    insert. Sequential append is dramatically cheaper than random
    in-place update on real disks, which is the actual reason
    LSM-tree-based stores like Cassandra write so much faster than a
    B-tree-based store like Postgres under heavy write load — at the
    cost of reads sometimes needing to check several SSTables, and
    compaction running as an ongoing background cost.

## 1. "What does 'wide-column' actually mean, and how is a Cassandra table different from a relational table?"

**Answer:**

- Rows in the same table can have different columns — there's no single
  fixed schema every row must match the way a relational table enforces.
- More importantly, Cassandra tables are modeled around the **query**,
  not the entity — the same underlying data is often duplicated across
  several tables, each shaped for one specific access pattern, rather
  than normalized once and joined at read time.
- This is the opposite instinct from relational modeling (see
  [SQL & Relational Data Modeling](sql-data-modeling-fundamentals.md)):
  normalize first there, denormalize-by-query-pattern here.

## 2. "Why no joins at all — what's actually being enforced here?"

**Answer:**

- At Cassandra's intended scale — many nodes, each holding only a
  partition of the total data — a join would mean fetching rows that
  live on different machines and combining them over the network,
  per query, which gets slower as the cluster (not just the data) grows.
- Cassandra forbids this by design: you denormalize **at write time**
  instead of joining **at read time**, trading extra storage and
  write-side duplication for read latency that stays flat and
  predictable regardless of cluster size.
- This is a deliberate, load-bearing constraint, not a missing feature —
  removing it would remove the exact property (flat read latency at
  scale) that makes Cassandra worth reaching for.

## 3. "What's a partition key, and why does getting it wrong wreck a cluster?"

**Answer:**

- The **partition key** determines which node(s) in the cluster actually
  store a given row, via consistent hashing over the key.
- A well-chosen partition key spreads writes and reads evenly across
  every node — the entire point of a wide-column cluster's horizontal
  scalability.
- A poorly chosen one — say, partitioning by `status` when 90% of rows
  share the same status — sends the overwhelming majority of traffic to
  whichever node owns that one hash value, a **hot partition**. The rest
  of the cluster sits idle while one node gets overwhelmed, which is the
  most common real production failure mode in Cassandra deployments, and
  it's a data-modeling mistake, not an infrastructure one.

## 4. "What's tunable consistency, and what does 'eventual consistency' actually mean here?"

**Answer:**

- Cassandra replicates each row to multiple nodes (a configurable
  replication factor), and lets you choose, **per query**, how many
  replicas must respond before a read or write is considered successful
  — this is the "tunable" part.
- A write or read at `QUORUM` requires a majority of replicas to agree,
  giving strong consistency at the cost of latency; a write or read at
  `ONE` only needs a single replica to respond, giving low latency at the
  cost of a real window where different replicas can briefly disagree.
- This is the same spectrum covered generally in
  [Consistency & Consensus §1](../backend/consistency-and-consensus.md#1-the-consistency-spectrum-from-strong-to-eventual) —
  Cassandra is simply a concrete system where that spectrum is a literal,
  per-query setting rather than a fixed architectural choice.

| Pros | Cons / Trade-offs |
|---|---|
| Very fast writes — sequential append, no in-place update, no join overhead | Reads can need to check multiple SSTables, and compaction is an ongoing background cost |
| Horizontal write scale that stays predictable as the cluster grows | No joins — every access pattern needs its own denormalized table, planned in advance |
| Tunable per-query consistency fits a range of latency/correctness needs | A poorly chosen partition key creates a hot partition that no amount of hardware fixes |

---

## Code Samples

No dedicated code samples for this page.
