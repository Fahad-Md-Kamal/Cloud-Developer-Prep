---
title: "PostgreSQL for Scale"
---

# PostgreSQL for Scale

Knowing *when* to add a B-tree index is the tool-usage version of
indexing. The fundamentals below — what a B-tree actually looks like on
disk, how Postgres lets reads and writes happen at the same time
without locking everything, and what "committed" really means — are
what let you reason about a slow query or a bloated table in a way
"add an index" alone never will. The practical decision-making
(indexing, query diagnosis, partitioning, replication, JSONB) follows
below that. For pushing computation into SQL from Django specifically
(query count, `F()` expressions, row locking), see
[Django ORM Query Cheat Sheet](../python/django-orm.md).

## How Postgres Actually Works

### B-Tree Indexes: Why They're Fast, and Why They Cost Writes

A B-tree index is a **sorted, balanced tree of pages** — not a list,
not a hash table. That shape is exactly what makes it fast for both
lookups and ranges, and exactly why every write has to pay for it.

- Each page holds a sorted run of keys, plus pointers down to the next
  level — the very top (**root**) narrows down to a handful of
  **branch** pages, which narrow down further to the **leaf** pages
  that actually point at table rows.
- A page typically holds hundreds of keys, so each level of the tree
  narrows the search dramatically — a table with a billion rows still
  only needs a handful of page reads to find one value, not a billion
  comparisons.
- Because the leaves are **sorted**, a range query (`WHERE created_at
  BETWEEN ...`) finds the start once, then just walks sideways through
  neighboring leaves — no repeated searching per row.

<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of a B-tree index lookup touching only three pages, then an insert into a full leaf page splitting it and adding a pointer to the parent" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="460" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<line x1="472" y1="95" x2="260" y2="150" stroke="#c7cedb" stroke-width="2"></line>
<line x1="472" y1="95" x2="685" y2="150" stroke="#c7cedb" stroke-width="2"></line>
<line x1="260" y1="205" x2="90" y2="270" stroke="#c7cedb" stroke-width="2"></line>
<line x1="260" y1="205" x2="260" y2="270" stroke="#c7cedb" stroke-width="2"></line>
<line x1="685" y1="205" x2="600" y2="270" stroke="#c7cedb" stroke-width="2"></line>
<line x1="685" y1="205" x2="770" y2="270" stroke="#c7cedb" stroke-width="2"></line>
<line x1="260" y1="205" x2="430" y2="270" stroke="#2f6fb3" stroke-width="2" stroke-dasharray="5,5" opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.62;0.68;1" dur="13s" repeatCount="indefinite"></animate></line>
<rect x="397" y="40" width="150" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="472" y="72" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">Root</text>
<rect x="180" y="150" width="160" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="260" y="182" font-size="13" font-weight="600" text-anchor="middle" fill="#2b313b">Branch A (1–500)</text>
<rect x="605" y="150" width="160" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="685" y="182" font-size="13" font-weight="600" text-anchor="middle" fill="#2b313b">Branch B (501–1000)</text>
<rect x="20" y="270" width="140" height="65" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="90" y="307" font-size="12" text-anchor="middle" fill="#434d5c">Leaf (1–120)</text>
<rect x="190" y="270" width="140" height="65" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"><animate attributeName="stroke" values="#434d5c;#434d5c;#c0392b;#c0392b;#434d5c;#434d5c" keyTimes="0;0.4;0.46;0.6;0.66;1" dur="13s" repeatCount="indefinite"></animate></rect>
<text x="260" y="300" font-size="12" text-anchor="middle" fill="#434d5c">Leaf (121–500)</text>
<text x="260" y="316" font-size="11" fill="#c0392b" opacity="0" text-anchor="middle"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.4;0.46;0.6;0.66;1" dur="13s" repeatCount="indefinite"></animate>full — splitting</text>
<rect x="530" y="270" width="140" height="65" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="600" y="307" font-size="12" text-anchor="middle" fill="#434d5c">Leaf (501–750)</text>
<rect x="700" y="270" width="140" height="65" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="770" y="307" font-size="12" text-anchor="middle" fill="#434d5c">Leaf (751–1000)</text>
<rect x="360" y="270" width="140" height="65" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2" opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.62;0.68;1" dur="13s" repeatCount="indefinite"></animate></rect>
<text x="430" y="300" font-size="12" text-anchor="middle" fill="#0f6b45" opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.62;0.68;1" dur="13s" repeatCount="indefinite"></animate>new leaf page</text>
<text x="430" y="316" font-size="11" text-anchor="middle" fill="#3d9a73" opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.62;0.68;1" dur="13s" repeatCount="indefinite"></animate>(split result)</text>
<circle r="9" fill="#d9822b" cy="302"><animate attributeName="cx" values="472;472;260;260;260;260;260" keyTimes="0;0.06;0.14;0.2;0.36;0.38;1" dur="13s" repeatCount="indefinite"></animate><animate attributeName="cy" values="67;67;182;182;302;302;302" keyTimes="0;0.06;0.14;0.2;0.36;0.38;1" dur="13s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="1;1;1;1;1;0;0" keyTimes="0;0.06;0.14;0.2;0.36;0.38;1" dur="13s" repeatCount="indefinite"></animate></circle>
<text x="450" y="400" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.36;0.4;1" dur="13s" repeatCount="indefinite"></animate>Looking up one row touches 3 pages total — root, branch, leaf — even across a billion rows.</text>
<text x="450" y="400" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.4;0.44;0.6;0.64;1" dur="13s" repeatCount="indefinite"></animate>Inserting into a full leaf page splits it — that split has to happen on every write-heavy index.</text>
<text x="450" y="400" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="13s" repeatCount="indefinite"></animate>The new page gets linked into the parent — one index, now one more page to keep balanced on every future write.</text>
</svg>

!!! success "This is the mechanism behind the pros/cons table in §1 below"

    "Every index slows down writes" isn't just a rule to memorize — a
    full leaf page splitting, and that split propagating up to its
    parent, is the actual cost being paid on an `INSERT` into an
    indexed column. More indexes means more trees that can each need
    this rebalancing on the exact same write.

### MVCC: How Reads and Writes Happen at the Same Time

Without some trick, a writer updating a row would have to lock it —
blocking any reader who just wants to *see* a value, not change one.
Postgres avoids this with **MVCC** (Multi-Version Concurrency Control):

- An `UPDATE` never overwrites a row in place — it writes a **new
  version** of the row, stamped with the transaction that created it.
  The old version stays on disk as long as any other transaction might
  still need to see it.
- Every transaction reads from a consistent **snapshot** — whatever was
  committed *before that transaction started* — regardless of what
  other transactions are doing concurrently, right now, to the same
  rows.
- The direct payoff: readers never block writers, and writers never
  block readers. They're simply looking at different versions of the
  same row at once.

!!! danger "Old versions don't clean themselves up"

    Row versions nothing needs anymore are called **dead tuples**, and
    they just sit there taking up space until something reclaims them
    — that something is `VACUUM`. A table that's rarely or never
    vacuumed accumulates dead tuples indefinitely, a condition known as
    **table bloat**: the table physically grows even though the number
    of *live* rows hasn't, and every sequential scan now has to skip
    past all that dead weight too.

### The Write-Ahead Log (WAL): Durability and Crash Recovery

Before Postgres changes anything in its actual data pages, it first
writes that change to a separate, purely sequential log — the **WAL**
— and it's *that* write the database waits for before telling you
`COMMIT` succeeded.

- **Why log first, not the real page first:** writing to a random data
  page on disk means a seek, and a crash mid-write there can leave a
  half-written, corrupted page. Appending to the end of a sequential
  log is fast, and trivial to make atomic — either the whole new
  record is there, or it isn't.
- **Crash recovery is just replay:** if Postgres crashes before fully
  applying a change to its real data pages, startup replays the WAL
  from the last checkpoint — the log is authoritative; the data pages
  are just a cache of how far that replay has gotten.
- **This is what "replication ships the WAL" actually means** (see §4
  below): a replica is a separate process continuously replaying that
  exact same log against its own copy of the data pages — not a
  different mechanism, the same one, just running somewhere else.

## 1. "Walk me through choosing an index — B-tree vs. GIN vs. GiST."

```sql
-- B-tree: the default, for equality/range on scalar columns
CREATE INDEX idx_orders_created_at ON orders (created_at);

-- GIN: for containment queries on JSONB, arrays, and full-text search
CREATE INDEX idx_orders_metadata ON orders USING GIN (metadata jsonb_path_ops);

-- GiST: for geometric types, ranges, and nearest-neighbor queries
CREATE INDEX idx_venues_location ON venues USING GiST (location);
```

**Answer:**

- B-tree is the right default for equality and range lookups on
  ordinary scalar columns — it's what you get without specifying
  anything, and it covers the large majority of indexing needs.
- GIN earns its keep on composite/multi-valued data: `JSONB`
  containment (`@>`), array membership, or full-text search vectors,
  where a B-tree can't express the query at all.
- GiST fits geometric and range types, and supports
  approximate/nearest-neighbor operators GIN doesn't.
- The practical mistake isn't picking the wrong one of these three —
  it's adding an index without first looking at what the query
  actually filters, joins, or orders on.

| Pros | Cons / Trade-offs |
|---|---|
| Right index type turns a sequential scan into an index scan | Every index slows down writes — more structures to update per `INSERT`/`UPDATE` |
| GIN/GiST enable queries a B-tree structurally can't answer | GIN indexes are larger and slower to build than B-tree for the same data |
| Composite/partial indexes can target the exact query shape in use | An unused index is pure cost — no query benefit, still paid on every write |

## 2. "How do you find out why a query is slow, instead of guessing?"

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE customer_id = 42 AND status = 'pending';
```

**Answer:**

- Run `EXPLAIN (ANALYZE, BUFFERS)` and compare the planner's
  *estimated* row count against the *actual* row count at each node.
- A big gap usually means stale statistics (`ANALYZE` the table)
  rather than a genuinely bad plan.
- Look for a sequential scan where an index scan was expected, and
  check `BUFFERS` for how much came from disk versus cache.
- Guessing at "add an index" or "denormalize this" without first
  looking at the actual plan is the single most common way engineers
  waste time optimizing the wrong thing.

## 3. "When would you reach for table partitioning, and what does it cost you?"

**Answer:**

- Reach for it when a table is large enough that most queries only
  ever touch a slice of it — typically time-series data filtered by
  date — and that slice lines up with a natural partition key.
- Range-partitioning by month means a query for "last 30 days" only
  scans one or two partitions instead of the whole table (partition
  pruning), and old partitions can be dropped instantly instead of run
  through a slow `DELETE`.
- The cost: any unique constraint or index must include the partition
  key, cross-partition queries and joins get harder to reason about,
  and migrating an existing large table into partitions is itself a
  real, careful piece of operational work — not a config flag.

| Pros | Cons / Trade-offs |
|---|---|
| Partition pruning skips irrelevant partitions entirely | Unique constraints/PKs must include the partition key |
| Dropping an old partition is instant vs. a slow bulk `DELETE` | Cross-partition queries and joins are harder to optimize |
| Vacuum/maintenance can operate per-partition | Migrating an existing large table into partitions is a real, risky project |

## 4. "Explain PostgreSQL replication for HA — what's the actual failover story?"

**Answer:**

- Streaming replication ships the WAL to one or more replicas
  continuously.
- **Asynchronous** replication is the default — the primary doesn't
  wait for a replica to confirm, so a crash can lose the last few
  committed transactions that hadn't shipped yet.
- **Synchronous** replication waits for at least one replica to
  confirm before acknowledging the commit — zero data loss on
  failover, at the cost of added write latency and the primary
  blocking if that replica is slow or down.
- Either way, PostgreSQL itself does **not** auto-promote a replica on
  primary failure — that requires an external tool (Patroni, repmgr,
  or a cloud provider's managed failover) watching health and doing
  the promotion and DNS/connection redirect.

## 5. "When does JSONB in Postgres make sense vs. a normalized column, or vs. reaching for Mongo?"

```sql
CREATE INDEX idx_orders_metadata_gin ON orders USING GIN (metadata jsonb_path_ops);
SELECT * FROM orders WHERE metadata @> '{"source": "mobile_app"}';
```

**Answer:**

- `JSONB` is a good fit for attributes that are genuinely sparse or
  variable across rows and queried only occasionally — it saves a
  schema migration for every new optional field.
- The moment a field inside that JSON is filtered, joined, or ordered
  on *constantly*, it should be promoted to a real, indexed column — a
  GIN index on JSONB helps but never beats a proper B-tree on a
  first-class column.
- None of this is a reason to reach for MongoDB instead: JSONB gives
  flexible schema *inside* a single ACID, transactional database,
  which is a different trade-off than moving the data to a separate
  store entirely.

---

## Summary

- Index type follows the actual query shape, not a default habit;
  `EXPLAIN ANALYZE` replaces guessing; partitioning and replication
  both trade real operational complexity for real scaling headroom.
- Pushing computation into SQL instead of Python, fixing N+1, and
  scoping row locks correctly is Django-ORM-specific — see
  [Django ORM Query Cheat Sheet](../python/django-orm.md) for that.

---

## Practice Notes (from live session)

### SQL practice sandbox

A real SQLite database (`employees`/`departments`, seeded with deliberate
salary ties) plus an 8-problem set (joins through
`RANK`/`ROW_NUMBER`/`LAG`/`LEAD`) and verified solutions live in this
repo at [`practice/sql/`](https://github.com/Fahad-Md-Kamal/Cloud-Developer-Prep/tree/main/practice/sql):

```bash
cd practice/sql
sqlite3 practice.db < schema.sql   # one-time setup
sqlite3 practice.db                # open the shell and start querying
```

Beyond that, [PG Exercises](https://pgexercises.com/) for more query
volume, *Use The Index, Luke* for reading query plans and indexes.

### Worked example: rank within a group (window functions)

Schema: `employees(id, name, department_id, salary, hire_date)`,
`departments(id, name)`.

**Task:** each employee's name, department name, salary, and their salary
rank *within their department* (1 = highest paid), ordered by department
then rank.

```sql
SELECT
    e.name,
    d.name AS department_name,
    e.salary,
    RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS salary_rank
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name, salary_rank;
```

#### Tracing it on real data

Abstract syntax doesn't stick — trace it on actual rows instead.

**Sample data:**

| name | department_id | salary |
|---|---|---|
| Alice | 10 | 90000 |
| Bob | 10 | 80000 |
| Carol | 10 | 80000 |
| Dave | 20 | 70000 |
| Eve | 20 | 60000 |

Running `RANK() OVER (PARTITION BY department_id ORDER BY salary DESC)`
produces:

| name | department_id | salary | salary_rank |
|---|---|---|---|
| Alice | 10 | 90000 | 1 |
| Bob | 10 | 80000 | 2 |
| Carol | 10 | 80000 | 2 |
| Dave | 20 | 70000 | 1 |
| Eve | 20 | 60000 | 2 |

**Step by step:**

1. **`PARTITION BY department_id`** — mentally split the table into
   buckets, one per department. Nothing is deleted or merged; every row
   is still there.
2. **`ORDER BY salary DESC`** (inside `OVER(...)`) — within *each bucket
   separately*, sort by salary, highest first.
3. **`RANK()`** — walk down each bucket's sorted order and assign 1st,
   2nd, etc., restarting at 1 every time you cross into a new bucket.
   Tied rows (Bob and Carol, both 80000) get the same rank.

**Why not plain `ORDER BY` + row position?** That gives one ranking
across the *whole table* (Alice would be #1 overall, Dave #4 overall).
`RANK() OVER (PARTITION BY ...)` gives a ranking that resets **per
group**, in a single query, without collapsing rows the way `GROUP BY`
would.

**The core idea, stated generally:** `PARTITION BY` splits the result
set into groups — here, one per department — **without collapsing rows**
the way `GROUP BY` does (`GROUP BY` produces one row per group; a window
function keeps every row and just annotates it). `ORDER BY salary DESC`
inside the `OVER (...)` clause then ranks rows within each partition.

**Tie handling — the other thing this tests:**

| Function | Ties | Next rank after a tie |
|---|---|---|
| `ROW_NUMBER()` | always unique (1,2,3,4...) | n/a |
| `RANK()` | same rank | **skips** (1,1,3,4) |
| `DENSE_RANK()` | same rank | **doesn't skip** (1,1,2,3) |
