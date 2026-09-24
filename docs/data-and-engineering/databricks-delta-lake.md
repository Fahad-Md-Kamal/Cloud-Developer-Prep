---
title: "Databricks & Delta Lake"
---

# Databricks & Delta Lake

Lakehouse-specific questions — what Delta Lake actually adds over plain
files, and the production patterns built on top of it.

---

## 1. "What does Delta Lake add on top of plain Parquet files in blob storage?"

**Answer:** Parquet files in S3/ADLS are just files — no transaction
guarantees, no way to know if a write is complete, no schema
enforcement, no history. Delta Lake adds a **transaction log** (`_delta_log/`,
a sequence of JSON commit files) on top of Parquet that provides:

- **ACID transactions** — a write either fully commits or fully doesn't;
  a reader never sees a half-written batch, which plain Parquet writes to
  a directory can't guarantee if a job dies mid-write.
- **Schema enforcement** — a write with an incompatible schema is
  rejected by default, instead of silently landing and corrupting
  downstream reads.
- **Time travel** — every version is queryable
  (`VERSION AS OF` / `TIMESTAMP AS OF`), since the transaction log
  records exactly which files belonged to which version.
- **Unified batch + streaming** — the same table can be a streaming
  source and sink, something plain Parquet has no native support for.

## 2. "Explain how Delta Lake gets ACID transactions on top of files in object storage, which has no native transaction support."

**Answer:** The transaction log is the mechanism. Every write (append,
update, delete, merge) creates a new JSON entry in `_delta_log/`
listing exactly which Parquet files are added or removed for that
version. Readers always read a *specific, consistent version* by
reading the log up to a point, not by scanning whatever files happen to
exist in the directory at that instant — so a concurrent writer adding
new files mid-read never produces a torn read. Object storage's
"write-once" semantics for individual files is actually what makes this
safe: files are never mutated in place, only added or marked removed in
the log.

## 3. "What's the medallion architecture, and why use it?"

```
Bronze (raw)  →  Silver (cleaned/conformed)  →  Gold (aggregated/business-ready)
```

**Answer:** Bronze holds raw, unmodified source data (schema-on-read,
minimal transformation) — the point is having an unimpeachable copy of
what actually arrived, for reprocessing if a downstream bug is found
later. Silver applies validation, deduplication, and type/schema
conformance — this is where most data-quality work happens. Gold is
aggregated, business-level data shaped for consumption (a specific
dashboard, a specific downstream FHIR export). The value is
reprocessability: a bug found in the Silver transformation logic can be
fixed and Silver/Gold rebuilt from Bronze, without needing to re-ingest
from the original source.

## 4. "How do you implement CDC (Change Data Capture) with Delta Lake?"

```python
# Delta's Change Data Feed -- row-level change tracking, enabled per table
spark.sql("""
    ALTER TABLE silver.patients
    SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

changes = spark.read.format("delta") \
    .option("readChangeFeed", "true") \
    .option("startingVersion", last_processed_version) \
    .table("silver.patients")

# changes includes a _change_type column: insert / update_preimage /
# update_postimage / delete
```

**Answer:** Delta's Change Data Feed (CDF) tracks row-level changes
between versions once enabled, so a downstream consumer can read just
what changed since the last version it processed, instead of
re-scanning the whole table. This is the mechanism behind incremental
pipelines — a Gold-layer job reading Silver's CDF only reprocesses
actually-changed rows.

**Likely follow-up — "how do you make the downstream consumer of that
CDC feed idempotent?"** Same answer as the Spark pipeline pattern: MERGE
into the target table keyed by a stable ID, not append — so re-reading
the same CDF version twice (a retry after a partial failure) doesn't
duplicate anything.

## 5. "What's schema evolution, and how does Delta Lake handle a source field that changes?"

```python
new_data.write.format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .saveAsTable("bronze.claims")
```

**Answer:** Source schemas drift over time — a new optional field
appears, a field's type changes, a field gets dropped. By default,
Delta rejects a write with a mismatched schema (safe default, catches
upstream breakage early). `mergeSchema` explicitly allows *additive*
changes (a new column) to merge into the table schema automatically.

**Know this:** `mergeSchema` handles additive changes safely; it does
**not** handle a type change on an existing column (e.g. a field going
from `string` to `integer`) — that needs an explicit migration, since
silently reinterpreting existing data under a new type is exactly the
kind of silent corruption schema enforcement exists to prevent.

## 6. "What does `OPTIMIZE` / `Z-ORDER` do, and why would a table need it?"

```sql
OPTIMIZE silver.patients ZORDER BY (patient_id, last_updated)
```

**Answer:** Every small write (a frequent `MERGE`, a streaming
micro-batch) creates its own small Parquet files — over time, a table
accumulates thousands of small files, which hurts read performance
(more file-open overhead than actual data reading). `OPTIMIZE` compacts
small files into fewer, larger ones. `ZORDER BY` additionally
co-locates rows with similar values in the given columns physically
close together in those compacted files, so a query filtering on that
column can skip reading files that don't contain matching values
entirely (data skipping) — the query-time payoff for having run
`OPTIMIZE` at all.

## 7. "What's time travel useful for beyond 'oops, undo my mistake'?"

```sql
SELECT * FROM silver.patients VERSION AS OF 42;
SELECT * FROM silver.patients TIMESTAMP AS OF '2026-09-01';
```

**Answer:** Reproducing a report or a downstream FHIR export exactly as
it looked at a point in time (audit/compliance requirement in
healthcare data specifically); diffing two versions to understand what
a specific pipeline run actually changed; and yes, recovering from a bad
write — but the audit/reproducibility use case is the one worth naming
first in a healthcare-data context, since regulatory questions about
"what did this record say on this date" come up in ways they don't in
most other domains.

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Delta Lake example added under `code_samples/`.
