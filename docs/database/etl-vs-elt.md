---
title: "ETL vs. ELT: Data Pipeline Architecture"
---

# ETL vs. ELT: Data Pipeline Architecture

Both acronyms name the same three steps — Extract, Transform, Load.
The entire difference between them is **which order the last two
happen in**, and that single reordering is what explains the cost,
flexibility, and governance trade-offs between them, not two
fundamentally different technologies.

## 1. "What do ETL and ELT actually stand for, and what's the one real difference?"

**Answer:**

- **Extract** — pull data out of the source system (an application
  database, an API, event logs).
- **Transform** — clean, reshape, join, and aggregate it into the shape
  the destination actually needs.
- **Load** — write the result into the destination (a data warehouse or
  lake).
- **ETL** transforms *before* loading — a separate processing stage
  takes raw extracted data, cleans and reshapes it, and only the
  finished result ever reaches the destination.
- **ELT** loads *first* — raw extracted data lands in the destination
  essentially as-is, and transformation happens afterward, as queries
  run *inside* the destination against the raw data already sitting
  there.
- Nothing else about the three steps changes — it's purely a reordering
  of where transformation happens relative to loading.

## 2. "Why did ELT become viable, when ETL was the default for decades?"

**Answer:**

- ETL's dominance was a direct consequence of **expensive storage and
  limited destination compute** — a traditional data warehouse had
  real, metered capacity, so transforming first (dropping anything
  unneeded, reshaping into a compact final form) before loading was
  the only economical option.
- Modern cloud warehouses and lakes (Snowflake, BigQuery, Redshift,
  Databricks) made both halves of that constraint stop being true at
  once: storage became cheap enough that keeping raw, unreduced data
  around is no longer wasteful, and these destinations now have their
  own elastic, massively parallel compute — powerful enough to do the
  transformation work themselves, at scale, as ordinary queries.
- Once the destination can cheaply store raw data *and* cheaply
  transform it internally, running a separate transform stage before
  loading stops paying for itself — ELT is a direct consequence of that
  economic shift, not a newer, inherently better idea.

## 3. "What are the actual trade-offs — is ELT just strictly better now?"

**Answer:**

- **ETL** — only clean, validated data ever reaches the destination,
  which makes compliance and governance more straightforward: PII can
  be scrubbed or masked *before* it ever lands anywhere persistent. The
  cost is flexibility — raw data was never kept, so a new question that
  needs something the original transform discarded means re-extracting
  from the source and rerunning the whole pipeline.
- **ELT** — raw data's full fidelity and history are preserved, so any
  question the business comes up with later is still answerable from
  what's already loaded, and transforms are just rerunnable queries
  against the warehouse rather than a pipeline that has to be
  re-executed end to end. The cost is governance: unvalidated, possibly
  sensitive raw data sits in the destination — even if only briefly,
  even if access-controlled — before any cleaning happens at all.
- Neither one wins outright — the deciding factor is whether the
  destination can be trusted to briefly hold raw data at all, and
  whether re-running extraction is cheap or expensive for a given
  source system.

## 4. "How does this map to the medallion architecture already covered for Delta Lake?"

**Answer:**

- [Medallion architecture](databricks-delta-lake.md#3-whats-the-medallion-architecture-and-why-use-it)
  — bronze (raw) → silver (cleaned/conformed) → gold
  (aggregated/business-ready) — is ELT, implemented as an explicit,
  layered pattern inside a lakehouse.
- Bronze is literally the "L" happening first: raw data lands exactly
  as extracted, nothing discarded. Silver and gold are the "T" —
  transformation applied progressively, afterward, as Spark jobs or
  SQL running against data that's already loaded.
- Recognizing this mapping is the useful interview move: "medallion
  architecture" isn't a separate concept to memorize — it's one
  concrete, named implementation of ELT's general shape.

## 5. "When would you still reach for ETL today?"

**Answer:**

- Strict regulatory requirements where sensitive raw data genuinely
  can't land in a shared destination even transiently — healthcare or
  financial PII that must be scrubbed before storage, not after, by
  policy rather than preference.
- A legacy or on-premises destination that doesn't have the elastic,
  cheap compute ELT depends on — transforming first still makes sense
  when the destination itself would struggle to do that work.
- A source system that's expensive or risky to re-extract from
  (a fragile legacy API, a system with hard rate limits) — ETL's
  "transform once, carefully, before loading" reduces how often that
  source gets hit, compared to ELT's assumption that re-running a
  transform is cheap because the raw data is already sitting in the
  warehouse.

| Pros | Cons / Trade-offs |
|---|---|
| ETL: only validated data reaches the destination — simpler compliance | ETL: no raw data kept — a new requirement means re-extracting and rerunning the whole pipeline |
| ELT: raw data's full history is preserved for any future question | ELT: unvalidated, possibly sensitive data sits in the destination before cleaning |
| ELT: transforms are rerunnable queries, not a pipeline that must be re-executed | ELT: the destination's compute bill now includes transformation work, not just storage |
| ETL: a separate transform stage can shield a fragile source from repeated re-extraction | ETL: that separate stage is its own infrastructure to run, scale, and maintain |

---

## Code Samples

No dedicated code samples for this page — see
[Apache Spark & PySpark](spark-pyspark.md) and
[Databricks & Delta Lake](databricks-delta-lake.md) for the engines
that actually run ETL/ELT transformation workloads.
