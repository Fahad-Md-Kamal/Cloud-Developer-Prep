---
title: "NewSQL: Distributed SQL"
---

# NewSQL: Distributed SQL

Everywhere else on this site, "relational" means ACID and joins on one
strongly-consistent box, and "scale horizontally" means giving some of
that up (see [Database Types: The Decision Framework](database-types-overview.md)).
NewSQL databases — CockroachDB, Google Spanner, YugabyteDB — exist
specifically to question that trade-off. The mechanism that makes it
possible is **consensus**, not a cleverer query planner.

## 1. "How does NewSQL get both ACID and horizontal scale, when everything else treats that as a trade-off?"

**Answer:**

- The relational model, SQL, and ACID transactions stay exactly as they
  are — what changes is that data is split into small ranges, and each
  range is replicated across multiple nodes using a **consensus
  protocol** (commonly Raft, or a Paxos variant) instead of living on
  one single-writer machine.
- Consensus is what lets a *group* of machines behave like one reliable
  machine — the actual mechanism is explained in §2, and it's the one
  piece of engineering that makes "distributed" and "strongly
  consistent" stop being contradictory.
- This is a direct, deeper answer to the question already raised in
  [Consistency & Consensus §3](../backend/consistency-and-consensus.md#3-when-you-actually-need-consensus):
  a NewSQL database is a concrete, full-database example of "something
  already built on Raft/Paxos" that most engineers only ever interact
  with as a client, never having to implement the consensus layer
  themselves.

## How Raft Consensus Actually Works

Each data range has a small set of replicas (often 3 or 5), one of which
is elected **leader**. Every write goes to the leader, which appends it
to its own local log and sends it to the followers (`AppendEntries`).
Once a **majority** of replicas — leader included — have the entry in
their log, the leader considers it **committed** and acknowledges the
write as durable. If the leader ever stops responding, the remaining
replicas time out, one nominates itself **candidate**, requests votes
from the others, and — once it wins a majority — becomes the new leader,
continuing from the last committed entry with nothing lost.

<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of Raft consensus: a leader replicating a write to followers and committing it once a majority acknowledge, then a leader failure triggering an election where a follower becomes the new leader" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="460" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<rect x="360" y="30" width="180" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="3"><animate attributeName="fill" values="#e8f7f0;#e8f7f0;#f0f1f3;#f0f1f3;#e8f7f0" keyTimes="0;0.46;0.5;0.86;1" dur="20s" repeatCount="indefinite"></animate><animate attributeName="stroke" values="#1f9d6b;#1f9d6b;#9aa5b3;#9aa5b3;#1f9d6b" keyTimes="0;0.46;0.5;0.86;1" dur="20s" repeatCount="indefinite"></animate></rect>
<text x="450" y="65" font-size="15" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.46;0.5;0.86;1" dur="20s" repeatCount="indefinite"></animate>Leader</text>
<text x="450" y="65" font-size="15" font-weight="600" text-anchor="middle" fill="#8e2d20"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.46;0.5;0.86;1" dur="20s" repeatCount="indefinite"></animate>Crashed</text>
<rect x="100" y="310" width="200" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"><animate attributeName="fill" values="#eef1f5;#eef1f5;#fdf3e3;#fdf3e3;#e8f7f0;#e8f7f0;#eef1f5" keyTimes="0;0.5;0.54;0.7;0.74;0.96;1" dur="20s" repeatCount="indefinite"></animate><animate attributeName="stroke" values="#434d5c;#434d5c;#b5831f;#b5831f;#1f9d6b;#1f9d6b;#434d5c" keyTimes="0;0.5;0.54;0.7;0.74;0.96;1" dur="20s" repeatCount="indefinite"></animate></rect>
<text x="200" y="345" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.54;1" dur="20s" repeatCount="indefinite"></animate>Follower A</text>
<text x="200" y="345" font-size="14" font-weight="600" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.54;0.58;0.7;0.74;1" dur="20s" repeatCount="indefinite"></animate>Candidate</text>
<text x="200" y="345" font-size="14" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.74;0.78;1" dur="20s" repeatCount="indefinite"></animate>New Leader</text>
<rect x="600" y="310" width="200" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="700" y="345" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">Follower B</text>
<line x1="400" y1="90" x2="240" y2="310" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.46;0.5;1" dur="20s" repeatCount="indefinite"></animate></line>
<line x1="500" y1="90" x2="660" y2="310" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.46;0.5;1" dur="20s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#2f6fb3" cx="450" cy="90"><animate attributeName="cx" values="450;240;450;450" keyTimes="0;0.12;0.16;1" dur="20s" repeatCount="indefinite"></animate><animate attributeName="cy" values="90;310;90;90" keyTimes="0;0.12;0.16;1" dur="20s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.02;0.12;0.16;1" dur="20s" repeatCount="indefinite"></animate></circle>
<circle r="8" fill="#2f6fb3" cx="450" cy="90"><animate attributeName="cx" values="450;660;450;450" keyTimes="0;0.12;0.16;1" dur="20s" repeatCount="indefinite"></animate><animate attributeName="cy" values="90;310;90;90" keyTimes="0;0.12;0.16;1" dur="20s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.02;0.12;0.16;1" dur="20s" repeatCount="indefinite"></animate></circle>
<line x1="300" y1="340" x2="600" y2="340" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.58;0.62;0.7;0.74;1" dur="20s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#b5831f" cy="340"><animate attributeName="cx" values="300;600;600" keyTimes="0;0.66;1" dur="20s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.6;0.62;0.68;0.7;1" dur="20s" repeatCount="indefinite"></animate></circle>
<text x="450" y="430" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.4;0.44;1" dur="20s" repeatCount="indefinite"></animate>The leader replicates each write to followers, committing once a majority have it in their log.</text>
<text x="450" y="430" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.46;0.5;0.68;0.72;1" dur="20s" repeatCount="indefinite"></animate>The leader crashes — Follower A times out, becomes a candidate, and requests votes.</text>
<text x="450" y="430" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.74;0.78;1" dur="20s" repeatCount="indefinite"></animate>A majority votes yes — Follower A becomes the new leader, continuing where the old one left off.</text>
</svg>

!!! success "Why this one mechanism unlocks both guarantees at once"

    Committing only once a *majority* has the entry means the data
    survives any single node failure without being lost, and electing a
    new leader through the same majority vote means the cluster never
    has two nodes simultaneously believing they're in charge
    (**split-brain**) — the same quorum idea from
    [Consistency & Consensus](../backend/consistency-and-consensus.md),
    now doing double duty for both durability and leader election.

## 2. "How does a transaction spanning multiple ranges commit atomically?"

**Answer:**

- A single Raft group only guarantees consensus *within one range* — a
  transaction touching several ranges (likely, on tables large enough to
  be split across many ranges) needs a further coordination layer on
  top.
- A coordinator (often the node that received the client's request)
  runs something functionally like a two-phase commit across the
  affected ranges: it asks each range's leader to prepare the write,
  and only tells every range to actually commit once all of them have
  confirmed they're ready — if any range can't commit, the whole
  transaction aborts everywhere, not just where it failed.
- The practical consequence: a transaction spanning more ranges costs
  more round trips and more latency than one confined to a single range
  — schema and data layout decisions that keep related data in the same
  range (or the same node) pay off directly in transaction speed.

## 3. "What's the actual cost of all this — why isn't NewSQL just strictly better than relational and NoSQL?"

**Answer:**

- Every write needs network round trips to replicate to a majority
  **before** it can be acknowledged — a cost a single-node database
  never pays at all, and one that gets materially worse the further
  apart (geographically) the replicas are.
- Running a distributed consensus-based cluster is operationally more
  complex than running one Postgres instance with read replicas — more
  moving parts, more subtle failure modes to reason about.
- None of this is a flaw so much as the direct, unavoidable price of the
  guarantee being bought: strong consistency across physically separate
  machines cannot be free, and NewSQL is explicit about paying that
  price rather than hiding it.

## 4. "When would you actually reach for CockroachDB/Spanner instead of Postgres with read replicas?"

**Answer:**

- When writes themselves — not just reads — need to scale beyond what a
  single-writer Postgres instance can do, which
  [read replicas and partitioning](postgresql-for-scale.md#3-when-would-you-reach-for-table-partitioning-and-what-does-it-cost-you)
  don't solve (they scale reads, not the single-writer write path).
- When the system is genuinely multi-region and needs strongly
  consistent writes across those regions — a financial ledger or
  inventory system that can't tolerate two regions briefly disagreeing
  about a balance.
- Not simply "when the site has a lot of traffic" — plenty of
  high-traffic systems are read-heavy and well served by Postgres plus
  read replicas and caching; NewSQL earns its operational cost
  specifically when the write path itself is the bottleneck and strong
  consistency can't be relaxed.

| Pros | Cons / Trade-offs |
|---|---|
| Keeps full SQL, joins, and ACID transactions while scaling horizontally | Every write pays a replication round trip before it's acknowledged |
| Survives node failure with no data loss and no manual failover | More operationally complex than a single-node database with replicas |
| Genuinely consistent multi-region writes, not just multi-region reads | Cross-range transactions cost more latency than single-range ones |

---

## Code Samples

No dedicated code samples for this page.
