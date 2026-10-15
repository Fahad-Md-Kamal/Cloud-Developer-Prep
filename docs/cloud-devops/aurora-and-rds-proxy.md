---
title: "Aurora & RDS Proxy: Serverless, Global Database & Connection Pooling"
---

# Aurora & RDS Proxy: Serverless, Global Database & Connection Pooling

[Databases: RDS Operations](databases-rds-operations.md) covers Multi-AZ,
read replicas, backups, and parameter groups — the operational layer
that applies to RDS generally. This page covers what Aurora adds on top
of that, and the connection-pooling service that sits in front of either.

## Aurora, Compared to Plain RDS

Aurora is MySQL/PostgreSQL-**compatible** (same wire protocol, same
client libraries, same SQL) but replaces RDS's underlying storage
architecture entirely:

- Storage auto-scales in 10 GB increments up to 128 TB, with no manual
  resizing.
- Data is replicated **6 ways across 3 AZs** automatically, underneath
  the database engine — a different mechanism than RDS Multi-AZ's
  synchronous standby copy, and part of why Aurora can tolerate losing
  two copies without losing write availability and three without losing
  read availability.
- Up to **15 read replicas** (vs 5 for plain RDS), all reading from the
  same underlying shared storage layer rather than streaming replication
  — replica lag is typically single-digit milliseconds.
- Costs more per hour than equivalent RDS, in exchange for this.

## Aurora Serverless

Auto-scaling compute capacity for Aurora, measured in **Aurora
Capacity Units (ACUs)**, that scales up and down (v2: in fine-grained
increments; can scale to zero in v1) based on actual load, instead of a
fixed, always-on instance size.

!!! success "The exam signal"

    "Infrequent, unpredictable, or spiky database traffic — don't pay for
    idle capacity 24/7" → Aurora Serverless. "Dev/test environment only
    used during work hours" is the other classic fit — scales down (or
    to zero) automatically overnight instead of someone remembering to
    stop it.

## Aurora Global Database

One primary Aurora cluster in one region, with up to 5 **secondary
regions** receiving replicated data with typical lag under a second —
using dedicated replication infrastructure, not standard read-replica
streaming.

- Secondary regions serve **low-latency local reads** for a globally
  distributed user base.
- In a regional outage, a secondary region can be promoted to take
  writes, typically within about a minute.

!!! success "The exam signal"

    "Low-latency reads for users in multiple regions, with disaster
    recovery across regions" → Aurora Global Database. Compare against
    [Route 53 latency-based routing](load-balancing-and-dns.md#routing-policies)
    pointed at regional read replicas — Global Database gets you fast,
    consistent cross-region replication without building that yourself.

## RDS Proxy

A fully managed connection pooler sitting between an application and
RDS/Aurora.

- **The problem it solves:** a database has a hard connection limit, but
  Lambda functions (and other bursty clients) can spin up far more
  concurrent connections than that during a traffic spike — each one
  opening its own direct database connection. RDS Proxy pools and
  reuses connections instead of letting every client exhaust the
  database directly.
- Also shortens **failover time** — the proxy holds the connections and
  transparently redirects to the new primary during a Multi-AZ failover,
  instead of every client needing to detect the failover and reconnect
  itself.
- Supports IAM authentication to the database, so credentials don't need
  to be distributed to every client at all.

!!! success "The exam signal"

    "Lambda functions are exhausting the database's connection limit
    under load" → RDS Proxy — this is the single most common RDS Proxy
    exam scenario, almost always phrased around Lambda specifically
    because Lambda's concurrency model is exactly what creates the
    connection-storm problem in the first place.
