---
title: "EC2 Instance Families, Purchasing Options & Placement Groups"
---

# EC2 Instance Families, Purchasing Options & Placement Groups

[EC2, AMIs & Launch Templates](compute-and-scaling.md) covers actually
launching and managing instances. This page covers the two decisions
that come before that: *which* instance type, and *how you pay for it*
— the pair of questions nearly every "most cost-effective" exam question
is built around.

## Instance Families: The Letter Tells You the Trade-off

| Family | Letter examples | Optimized for | Typical use |
|---|---|---|---|
| General purpose | `t3`, `m6i` | Balanced CPU/memory/network | Web servers, small databases, dev/test |
| Compute optimized | `c6i` | High CPU-to-memory ratio | Batch processing, video encoding, scientific modeling |
| Memory optimized | `r6i`, `x2idn` | High memory-to-CPU ratio | In-memory databases, large caches, real-time big data analytics |
| Storage optimized | `i4i`, `d3` | High-speed local (NVMe) storage, high IOPS | NoSQL databases, data warehousing, distributed file systems |
| Accelerated computing | `p5`, `g5` | GPUs / dedicated hardware | ML training/inference, graphics rendering |

!!! success "The exam signal"

    A question describing the *workload* ("CPU-intensive video
    transcoding," "an in-memory cache holding terabytes of data," "GPU
    training a model") is really asking you to pick the family, not a
    specific instance size — size (`.large`, `.2xlarge`, …) just scales
    the same ratio up or down.

## Purchasing Options: Trading Flexibility for Discount

| Option | Discount vs On-Demand | Commitment | Best for |
|---|---|---|---|
| On-Demand | None (baseline) | None | Unpredictable, short-term, or spiky workloads |
| Reserved Instances | Up to ~72% | 1 or 3 years, a *specific* instance family/region | Steady-state workloads you're confident won't change shape |
| Savings Plans | Up to ~72% | 1 or 3 years, a *dollar-per-hour* commitment | Steady-state spend, but flexible across instance family/size/region (even across EC2, Fargate, and Lambda for Compute Savings Plans) |
| Spot Instances | Up to ~90% | None — AWS can reclaim it with a 2-minute warning | Fault-tolerant, interruptible workloads |

- **Reserved Instances vs Savings Plans** is the pairing the exam tests
  most: both need a 1/3-year commitment for a steep discount, but a
  Savings Plan commits to a *spend rate* and lets the actual instance
  family/size/region vary underneath it, while an RI locks in a specific
  configuration. A Savings Plan is almost always the more flexible
  choice for a question that doesn't specifically require RI-only
  features (like Reserved Instance *marketplace* resale).
- **Spot** is reclaimed with only a two-minute warning — never for
  anything that can't tolerate an abrupt interruption. Good fits: batch
  jobs, CI build fleets, stateless web tier capacity behind an ASG
  alongside On-Demand instances, big data processing that checkpoints
  its progress.

!!! success "The exam signal"

    "Cost-effective" + "fault-tolerant" / "can be interrupted" / "batch
    processing" → Spot. "Cost-effective" + "steady-state," "predictable,"
    "running 24/7 for the next year" → Savings Plan (or RI if the
    question is specifically about reselling unused capacity). "No
    upfront commitment, usage is unpredictable" → On-Demand.

## Placement Groups: Controlling Where Instances Physically Land

| Strategy | What it does | Trade-off |
|---|---|---|
| Cluster | Packs instances close together, on the same low-latency, high-throughput network | A single hardware failure can take out the whole group — use for a single AZ workload that needs the throughput badly enough to accept that risk |
| Spread | Spreads each instance onto distinct underlying hardware | Limited to 7 instances per AZ per group — use for a small number of critical instances that must never share a failure domain |
| Partition | Groups instances into partitions (up to 7 per AZ), each on separate hardware, instances *within* a partition can share hardware | Used by distributed systems that already understand "partitions" themselves (HDFS, Cassandra, Kafka) and want partition-aware placement |

!!! success "The exam signal"

    "Needs the lowest possible network latency between instances, same
    AZ" → Cluster. "A handful of critical instances that must never fail
    together" → Spread. "A distributed data system like Hadoop/Cassandra
    that wants rack-awareness" → Partition.
