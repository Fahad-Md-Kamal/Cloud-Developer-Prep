---
title: "Serverless & Managed Compute: Lambda Limits, Beanstalk, Batch & Step Functions"
---

# Serverless & Managed Compute: Lambda Limits, Beanstalk, Batch & Step Functions

[Terraform: EKS, Worked Examples & Lambda](terraform-eks-and-lambda.md#aws-lambda-iam-packaging-the-s3-deployment-pattern)
covers actually deploying a Lambda function. This page covers its
operational limits, the handful of managed compute services that sit
alongside EC2/ECS/EKS/Lambda in "which compute service" exam questions,
and when each one actually wins.

## Lambda: Limits, Concurrency & Event Sources

`Timeout`
:   Up to 15 minutes, hard limit — anything longer needs a different
    service (Step Functions orchestrating multiple invocations, Batch,
    or a long-running compute option entirely).

`Memory`
:   128 MB – 10,240 MB, configurable — and CPU scales proportionally
    with memory, so a CPU-bound function that's slow can sometimes be
    fixed by raising memory, not by rewriting the code.

`Concurrency`
:   Every simultaneous invocation uses one concurrent execution. Without
    limits, a traffic spike can consume an account's entire concurrency
    pool and start throttling other functions in the same account/region.

    - **Reserved concurrency** — guarantees (and caps) a specific
      function's slice of the pool, isolating it from other functions'
      spikes.
    - **Provisioned concurrency** — keeps a set number of execution
      environments pre-initialized and warm, eliminating **cold starts**
      for latency-sensitive functions, at a cost (you pay for that
      capacity whether it's invoked or not).

`Event sources`
:   What actually invokes a function — API Gateway (synchronous,
    request/response), S3 event notifications, DynamoDB Streams, SQS,
    SNS, EventBridge, and a direct invoke/schedule. Synchronous sources
    (API Gateway) propagate an error straight back to the caller;
    asynchronous sources (S3, SNS) retry automatically and can route
    exhausted failures to a **dead-letter queue** or `OnFailure`
    destination instead of silently dropping them.

!!! success "The exam signal"

    "Eliminate cold starts for a latency-sensitive API" → provisioned
    concurrency. "One noisy function shouldn't be able to starve every
    other function's concurrency" → reserved concurrency. "A job that
    might run for over 15 minutes" → not Lambda at all.

## Elastic Beanstalk

A platform-as-a-service layer over EC2/ASG/ELB/RDS — upload application
code, and Beanstalk provisions and wires together the underlying
infrastructure for you.

- Still gives access to the underlying resources (you can see and tweak
  the EC2 instances, the ASG, the load balancer it created) — not a
  black box the way Lambda is.
- Supports blue/green-style **swap environment URLs**: deploy a new
  version to a separate environment, test it, then swap which
  environment the production URL points to.

!!! success "The exam signal"

    "Deploy a web application quickly without managing the underlying
    infrastructure yourself, but still want access to the EC2 instances
    if needed" → Elastic Beanstalk. Compare against ECS/EKS when
    containers are explicitly in the picture, and against Lambda when
    there's no need for a persistent server process at all.

## AWS Batch

Runs batch computing jobs — on EC2 (On-Demand or **Spot**, batch's most
common pairing, since a failed job just gets retried) or Fargate —
without managing the scheduling, queuing, or scaling of compute
resources yourself.

- You submit jobs to a **job queue**; Batch provisions the right amount
  and type of compute (a **compute environment**) to run them, and tears
  it back down when the queue is empty.
- The obvious fit for anything "run to completion and done" at scale:
  genomics processing, financial risk simulations, nightly ETL,
  render farms — work Lambda's 15-minute ceiling can't hold, and that
  doesn't need a persistent service like ECS/EKS running 24/7.

!!! success "The exam signal"

    "Run thousands of batch computing jobs as cheaply as possible,
    don't manage the underlying compute provisioning" → AWS Batch,
    usually paired with Spot for the compute environment.

## Step Functions

Orchestrates multiple AWS services (Lambda functions, Batch jobs, ECS
tasks, API calls) into a single visual **state machine**, instead of
one Lambda function awkwardly calling the next one itself.

- **Standard workflows** — can run for up to a year, exactly-once
  execution, full execution history — the default choice.
- **Express workflows** — higher throughput, shorter duration (up to 5
  minutes), at-least-once execution — built for high-volume,
  short-lived workloads like streaming data processing.
- Built-in error handling (retry/catch per state) and branching — the
  same `block`/`rescue` idea already covered for
  [Ansible error handling](ansible-handlers-templates-roles-vault.md#error-handling-block-rescue-always),
  expressed as a visual workflow instead of YAML.

!!! success "The exam signal"

    "Coordinate a multi-step process across several Lambda
    functions/services, with visibility into which step failed and
    built-in retry logic" → Step Functions, instead of chaining Lambda
    functions together by hand and losing all of that visibility.
