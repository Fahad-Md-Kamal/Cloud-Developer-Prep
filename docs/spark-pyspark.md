---
title: "Apache Spark & PySpark"
---

# Apache Spark & PySpark

Distributed data processing questions, framed the way a staff-level
interview actually asks them — diagnosis and trade-offs, not API syntax.

---

## 1. "Explain how Spark achieves parallelism. What's a partition?"

**Answer:** Spark splits a dataset into **partitions** — chunks of data
distributed across the cluster's executors. Each partition is processed
independently by a single task on a single core, so parallelism is
bounded by partition count: too few partitions and cores sit idle, too
many and per-task overhead (scheduling, small files) dominates. A
common starting rule of thumb is 2–4 partitions per core, then tune from
there based on actual data size and job behavior.

```python
df = spark.read.parquet("s3://bucket/patients/")
print(df.rdd.getNumPartitions())

df = df.repartition(200)   # full shuffle, redistributes evenly
df = df.coalesce(50)       # no shuffle, only merges existing partitions
```

**Likely follow-up — "`repartition` vs `coalesce`, when do you use
each?"** `coalesce` only *reduces* partition count and avoids a full
shuffle by merging existing partitions — cheap, but can leave partitions
uneven if the source was already skewed. `repartition` can increase or
decrease partition count and always shuffles to redistribute evenly —
more expensive, but the right call after a filter drops most of the
rows and you're left with too many now-tiny partitions.

## 2. "What's a shuffle, and why is it expensive?"

**Answer:** A shuffle redistributes data across the cluster so rows with
the same key land on the same partition — required by `groupBy`,
`join`, `distinct`, `repartition`. It's expensive because it involves
disk I/O (writing shuffle files), network transfer (moving data between
executors), and serialization — all things a purely in-partition
operation (`filter`, `map`, `select`) never needs.

**The distinction interviewers want:** **narrow transformations**
(`filter`, `map`, `select`) — each output partition depends on exactly
one input partition, no shuffle needed. **Wide transformations**
(`groupBy`, `join`, `repartition`, `distinct`) — output partitions
depend on multiple input partitions, shuffle required. Minimizing wide
transformations, or filtering/aggregating *before* a shuffle-heavy
operation to reduce what needs to move, is the core Spark performance
lever.

## 3. "A join between two large tables is slow and skewed. Walk me through diagnosing it."

**Answer:** First check the Spark UI's stage view for **task duration
skew** — if most tasks finish in seconds but a handful run for minutes,
that's a partition with a disproportionate share of the data, usually
from a join key with a few extremely common values (a "null" or
default-value key, or one entity ID that dominates).

**Fixes, in order of how often they apply:**

```python
from pyspark.sql import functions as F

# 1. Broadcast join -- when one side is small enough to fit in memory
#    on every executor (skips the shuffle for that side entirely)
result = large_df.join(F.broadcast(small_df), "patient_id")

# 2. Salting -- when both sides are large AND skewed on the same key
salted = large_df.withColumn("salt", (F.rand() * 10).cast("int"))
# join on (key, salt) after also exploding the small side across salt values
```

Broadcast join is the first thing to reach for when one side is small
(a lookup/dimension table) — Spark ships it to every executor instead of
shuffling the large side. When both sides are genuinely large and
skewed on the same key, salting spreads a hot key's rows across
multiple synthetic partitions instead of one.

## 4. "Explain lazy evaluation. Why does Spark work this way?"

**Answer:** Transformations (`filter`, `map`, `select`, `join`) don't
execute immediately — Spark builds a logical execution plan (a DAG) and
only runs it when an **action** (`.collect()`, `.count()`, `.write()`)
is called. This lets Spark's Catalyst optimizer see the *whole* chain of
operations before running anything, so it can push filters earlier,
combine operations, and skip unnecessary work — optimizations that
would be impossible if each line executed immediately in isolation.

**Where this actually bites people:** calling `.count()` or `.show()`
mid-pipeline for debugging silently triggers the *entire* upstream
computation each time, which is why an unexpectedly slow pipeline often
has several debug actions accidentally left in it re-running the same
expensive upstream work repeatedly.

## 5. "A job that ran fine on sample data runs out of memory in production. What's your process?"

**Answer:** Check the Spark UI's executor tab for spill (data that
didn't fit in memory and got written to disk — a warning sign, not
necessarily a crash, but a real slowdown) versus an actual OOM kill.
Common causes, roughly in order of how often they're the actual
culprit:

- **Skew** (§3) — one partition holding far more data than
  `executor-memory` was sized for, even though the *average* partition
  is fine.
- **A `collect()` on a large DataFrame** — pulls the entire dataset to
  the driver's memory; fine on a 10-row sample, fatal at production
  scale. Use `.write()` to persist results distributedly instead.
- **Broadcasting a table that turned out to be large in production** —
  the sample's "small" lookup table isn't small in production; disable
  auto-broadcast or explicitly control it if this is suspected.
- **Wide transformations without enough partitions** for the actual
  data volume, concentrating too much data per task.

## 6. "How would you design an idempotent, incrementally-processing Spark pipeline?"

**Answer:** Idempotent means re-running the same batch produces the same
result, not duplicate data — essential once retries or backfills are in
play. The core pattern:

```python
# Read only new/changed data since the last successful run
new_data = spark.read.format("delta").load(source_path) \
    .filter(F.col("updated_at") > last_checkpoint)

# MERGE instead of append -- upsert, not duplicate, on retry
delta_table.alias("target").merge(
    new_data.alias("source"),
    "target.id = source.id"
).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

`MERGE` (an upsert) instead of `append` is what actually makes a retry
safe — appending the same batch twice duplicates rows; merging on a
stable key doesn't. Track progress with an explicit checkpoint (a
processed-watermark table, not just "whatever's in the source since last
time I looked"), so a failed run can resume from a known point instead
of guessing what already succeeded.

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable PySpark example added under `code_samples/`.
