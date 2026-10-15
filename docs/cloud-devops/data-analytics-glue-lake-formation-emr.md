---
title: "Data Analytics: Glue, Lake Formation & EMR"
---

# Data Analytics: Glue, Lake Formation & EMR

[Messaging & Event-Driven Services](messaging-and-event-driven-services.md#kinesis-streams-firehose-data-analytics)
covers getting streaming data *into* S3. This page covers what turns a
pile of files sitting in S3 into something queryable: cataloging it,
governing access to it, and running large-scale processing jobs against
it.

## AWS Glue

A managed **ETL (Extract, Transform, Load)** service, built around one
central piece that everything else in this page leans on:

`Glue Data Catalog`
:   A persistent metadata store — table definitions, schemas, partition
    info — for data sitting in S3 (or other sources). This is what lets
    Athena, Redshift Spectrum, and EMR all query the same S3 data as if
    it were a real database table, without duplicating the data itself
    anywhere.

`Glue Crawlers`
:   Scans data sitting in S3, infers its schema, and automatically
    populates the Data Catalog — so a new batch of files landing in a
    bucket becomes queryable without anyone manually defining a schema.

`Glue Jobs`
:   Serverless Spark (or Python shell) scripts that transform data —
    reading from one source, applying transformations, writing to a
    destination — without provisioning or managing any cluster
    yourself.

!!! success "The exam signal"

    "Automatically discover the schema of new data landing in S3, so it
    can be queried without manual schema definition" → Glue Crawler +
    Data Catalog. "Transform data at scale with minimal infrastructure
    management" → Glue Jobs, not a hand-run EMR cluster.

## Lake Formation

Built on top of the Glue Data Catalog — adds **centralized, fine-grained
access control** for a data lake, instead of managing S3 bucket
policies and IAM policies separately for every consumer of the data.

- Define permissions **once**, at the table, column, or even row level,
  and every service reading through the Data Catalog (Athena, Redshift
  Spectrum, EMR) respects them consistently.
- This is the data-lake equivalent of what
  [AWS Organizations](aws-organizations-and-control-tower.md#aws-organizations)
  does for account-level governance — one place to define policy,
  applied everywhere, instead of per-consumer configuration drifting out
  of sync.

!!! success "The exam signal"

    "Need column-level or row-level security on data in a data lake,
    enforced consistently across every tool that queries it" → Lake
    Formation. Plain S3 bucket policies and IAM can't express
    column-level restrictions at all — that granularity is specifically
    what Lake Formation adds.

## EMR (Elastic MapReduce)

A managed cluster platform for big data frameworks — **Spark, Hadoop,
Hive, Presto** — for processing that genuinely needs a cluster you
control, rather than the fully serverless model Glue Jobs offers.

- Choose when a job needs **long-running, tunable clusters**: a specific
  Spark version/configuration, a persistent cluster multiple teams share,
  or processing that doesn't fit Glue's serverless job model.
- Can run on EC2 (full control over instance types, including **Spot**
  for the task nodes — a classic cost-optimization pairing, since a lost
  Spot node just gets recomputed by the framework's own fault
  tolerance) or on EKS/serverless EMR for less operational overhead.

!!! success "The exam signal"

    "Needs a long-running or highly customized Spark/Hadoop cluster,
    full control over the processing environment" → EMR. "Simple,
    serverless ETL job, don't want to manage a cluster at all" → Glue
    Jobs — this is the core EMR-vs-Glue decision the exam tests, and it
    comes down to how much control vs how little operational overhead
    the question actually wants.
