---
title: "AWS Services Quick Reference"
---

# AWS Services Quick Reference

Targeted at the current job-search track's JD requirements (basic AWS
knowledge including ECS, Lambda, S3, Aurora RDS, SQS, DynamoDB) — see
also Chapter 8 (Database Architecture), Chapter 16 (Docker), and
Chapter 17 (Kubernetes & Orchestration) for deeper related material.

## Already hands-on

Lambda, S3, SQS, EC2, Docker — comfortable discussing real usage and
design tradeoffs for these.

## Gap services to crash-review

Job descriptions for this track often list services not yet in hands-on
experience. 30–45 minutes each is enough to hold a competent conversation
— target depth is "basic knowledge," not expert.

### ECS (Elastic Container Service)

- Managed container orchestration — alternative to running your own K8s
- Fargate vs EC2 launch type: Fargate = serverless containers, no
  instance management
- Task definitions, services, target groups (usually behind an ALB)
- Framing: "similar to deploying with Docker directly, ECS adds
  orchestration/scaling on top"

### Aurora RDS

- MySQL/PostgreSQL-compatible managed relational DB, with AWS's own
  storage layer (faster replication, auto-scaling storage, up to 15 read
  replicas)
- Aurora Serverless — auto-scaling capacity for variable workloads
- Framing (strong PostgreSQL background applies directly): "Aurora
  Postgres is wire-compatible with Postgres — the DBA-facing work is
  nearly identical, the difference is in the replication/failover
  architecture underneath"

### DynamoDB

- NoSQL key-value/document store, single-digit ms latency at scale
- Partition key (+ optional sort key), no joins, denormalize by design
- When to use it vs RDS: high-throughput, simple access patterns, no need
  for relational queries
- Be honest about depth here: convey understanding of *when* to reach for
  it, not hands-on expertise

!!! note "Why this appendix exists"
    The risk with "basic knowledge of AWS Services (including but not
    limited to ECS, Lambda, S3, Aurora RDS, SQS, DynamoDB)" style
    requirements isn't being under-qualified — it's having *nothing* to
    say about a named service. This appendix exists to make sure that
    never happens.
