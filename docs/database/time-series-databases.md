---
title: "Time-Series Databases"
---

# Time-Series Databases

Timestamped data — metrics, sensor readings, prices, logs — can
technically live in any relational table with a `timestamp` column. Time-
series databases exist because that workload's actual shape (near-100%
appends, queried by time range and aggregation, with old data expected
to shrink or disappear) makes a general-purpose table pay for guarantees
it never needs, while missing features it needs by default.

## 1. "Why can't you just use Postgres for time-series data at scale?"

**Answer:**

- Time-series workloads are **almost pure appends** — new readings
  arrive constantly, existing rows are essentially never updated, and
  queries almost always filter by a time range and aggregate (average,
  max, percentile) rather than looking up one specific row.
- A general relational table still pays full index-maintenance cost on
  every insert, even though a time-series table's only meaningful index
  is "time, in order" — work a purpose-built engine can skip or do far
  more cheaply.
- Retention is a core, constant requirement — old data needs to shrink,
  downsample, or disappear on a schedule — which a relational database
  has no built-in concept of; you'd be hand-rolling scheduled deletes and
  rollups yourself.
- Postgres *can* be made to handle this reasonably well (see
  [TimescaleDB in §4](#4-timescaledb-vs-influxdb-vs-prometheus-whats-actually-different-between-them)),
  which is exactly why that option exists as a middle ground rather than
  "never use Postgres for this."

## 2. "What's actually different about how a time-series database stores data?"

**Answer:**

- Data is stored in **time-ordered chunks**, compressed far more
  aggressively than a general-purpose row store, because adjacent
  values in a time series are usually close to each other.
- The core trick is **delta encoding**: instead of storing each full
  timestamp and value, store the *difference* from the previous one —
  a sensor reporting every second has nearly identical consecutive
  timestamps and often only slightly different values, so storing small
  deltas instead of full numbers compresses dramatically better than a
  generic row-based format would.
- Some engines go a step further with **delta-of-delta** encoding
  (storing how much the delta itself changed), which compresses almost
  perfectly fixed-interval data (a reading every exact 10 seconds) down
  to nearly nothing extra per point.

## 3. "What is downsampling, and why do time-series databases build it in as a first-class feature?"

**Answer:**

- **Downsampling** keeps full, high-resolution data for a short recent
  window (the last day, say, at one-second resolution) and automatically
  aggregates older data into coarser rollups (one-minute averages, then
  one-hour averages) as it ages.
- Without this, storage grows forever at full resolution — in practice
  nobody needs second-by-second data from a year ago, but everyone needs
  *some* historical trend to still be queryable.
- Because this need is universal to the workload, time-series databases
  build it in as configuration (a retention/rollup policy) rather than
  leaving every team to write and schedule their own aggregation jobs,
  the way you'd have to on a general-purpose relational table.

## 4. "TimescaleDB vs. InfluxDB vs. Prometheus — what's actually different between them?"

**Answer:**

- **TimescaleDB** — time-series as a Postgres extension: your data lives
  in real Postgres tables (**hypertables**, automatically partitioned by
  time under the hood), so you keep full SQL, joins, and ACID guarantees
  alongside time-series-specific compression and retention features.
  The right choice when you need time-series data to join against
  regular relational data in the same system.
- **InfluxDB** — purpose-built from the ground up for this one workload,
  with its own query language and storage engine optimized purely for
  time-series ingest and query patterns, at the cost of not being a
  general-purpose relational database alongside it.
- **Prometheus** — narrower still: a **pull-based** metrics system
  specifically for monitoring (see
  [Prometheus's four metric types](../distributed-systems/metrics-and-prometheus.md#1-explain-prometheuss-four-metric-types-and-when-youd-reach-for-each)),
  built for short-retention operational metrics with alerting as a
  first-class feature, not a general-purpose time-series store for
  arbitrary application data.
- The deciding question is usually: does this data need to join against
  other relational data (TimescaleDB), is it a dedicated high-volume
  time-series workload on its own (InfluxDB), or is it specifically
  operational monitoring data feeding alerts (Prometheus)?

| Pros | Cons / Trade-offs |
|---|---|
| Delta/delta-of-delta encoding compresses time-ordered data far better than a generic row store | Not built for arbitrary relational queries — the data model is narrow by design |
| Built-in downsampling/retention removes the need to hand-build rollup jobs | Retention policy choices are a real design decision — getting them wrong loses data you later want |
| TimescaleDB keeps full SQL/joins alongside time-series features | InfluxDB/Prometheus trade that relational generality for workload-specific optimization |

---

## Code Samples

No dedicated code samples for this page.
