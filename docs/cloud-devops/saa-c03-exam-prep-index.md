---
title: "SAA-C03 Exam Prep: Domain-by-Domain Review Index"
---

# SAA-C03 Exam Prep: Domain-by-Domain Review Index

65 scenario-based questions, 130 minutes, 720/1000 to pass. Nearly every
question is "which option best meets these requirements" — cheapest,
most available, least operational overhead, most secure. This page
organizes everything added across this prep series by the exam's actual
four scored domains, not by the week it was studied in, since that's how
a final review (and the real exam) is actually structured.

## Domain 1: Design Secure Architectures — 30%

- [AWS Accounts & IAM](aws-accounts-and-iam.md) — policy evaluation
  logic, permission boundaries, trust vs permission policies, SCPs,
  cross-account `AssumeRole`
- [Encryption, Secrets & Identity Federation](kms-secrets-and-cognito.md) —
  KMS, Secrets Manager vs Parameter Store, Cognito
- [AWS Organizations & Control Tower](aws-organizations-and-control-tower.md)
- [Security & Compliance Services](aws-security-and-compliance-services.md) —
  WAF, Shield, GuardDuty, Inspector, Macie, Config
- [AWS Systems Manager](aws-systems-manager.md) — Session Manager, Patch
  Manager, Run Command

## Domain 2: Design Resilient Architectures — 26%

- [VPC Connectivity & Hybrid Networking](vpc-connectivity-and-hybrid-networking.md) —
  endpoints, peering, Transit Gateway, VPN/Direct Connect
- [Auto Scaling Groups & Scaling Policies](auto-scaling-groups.md)
- [Load Balancing & DNS](load-balancing-and-dns.md) — ALB/NLB/GWLB,
  Route 53 routing policies
- [Aurora & RDS Proxy](aurora-and-rds-proxy.md) — Multi-AZ, Aurora
  Global Database
- [DynamoDB & ElastiCache](dynamodb-and-elasticache.md) — Global Tables
- [Messaging & Event-Driven Services](messaging-and-event-driven-services.md) —
  SQS/SNS/EventBridge decoupling
- [Disaster Recovery Strategies & AWS Backup](disaster-recovery-strategies.md) —
  Backup & Restore, Pilot Light, Warm Standby, Multi-Site Active/Active,
  RTO/RPO

## Domain 3: Design High-Performing Architectures — 24%

- [EC2 Instance Families, Purchasing Options & Placement Groups](ec2-instance-types-and-purchasing-options.md)
- [Caching Layers & Global Accelerator](caching-layers-and-global-accelerator.md) —
  CloudFront, API Gateway caching, ElastiCache, DAX, Global Accelerator
  tied together
- [Storage Classes, Object Lock & Encryption](storage-and-observability.md#s3-deep-dive) —
  S3 performance/access-pattern decisions
- [EBS, EFS, FSx & Data Transfer](storage-options-ebs-efs-fsx.md)
- [Serverless & Managed Compute](serverless-and-managed-compute.md) —
  Lambda concurrency, Batch, Step Functions
- [Container Orchestration: ECS & EKS](container-orchestration-ecs-eks.md)
- [Data Analytics: Glue, Lake Formation & EMR](data-analytics-glue-lake-formation-emr.md)

## Domain 4: Design Cost-Optimized Architectures — 20%

- [EC2 Purchasing Options](ec2-instance-types-and-purchasing-options.md#purchasing-options-trading-flexibility-for-discount) —
  On-Demand vs Reserved vs Savings Plans vs Spot
- [S3 Storage Classes](storage-and-observability.md#storage-classes) —
  lifecycle tiering
- [Cost Management: Cost Explorer, CUR & Data Transfer](cost-management-tools.md)
- [AWS Budgets](storage-and-observability.md#aws-budgets-cost-alerts-tracking)
- Serverless's pay-per-use model (above) is itself a recurring
  cost-optimization answer — "no idle capacity" almost always points
  back to Lambda, Fargate, or Aurora Serverless over an always-on EC2
  fleet.

## Using This for the Practice & Review Weeks

- **Practice exams first, this index second.** Take the official
  practice set and timed full-length exams (Tutorials Dojo's
  explanations in particular teach more than most video courses) —
  this page isn't a substitute for that, it's where to go *after* a
  question exposes a gap.
- **For every wrong or guessed answer:** find the matching chapter
  above, read the "exam signal" callout there, and write your own
  one-line note on *why* the right answer won. Keep those notes
  somewhere you'll actually re-read the night before the exam — the
  act of writing the line is what makes it stick, not just reading the
  chapter a second time.
- **Compare similar services side by side** before the exam, not during
  it: SQS vs SNS vs Kinesis, EBS vs EFS vs FSx, ALB vs NLB vs GWLB,
  Pilot Light vs Warm Standby — every one of these pairings has its own
  comparison table above; re-reading the table beats re-reading the
  whole chapter.
- **Book the exam once practice-exam scores sit consistently around 80%
  or higher** — not before, and not much past that point either, since
  the material stays freshest right after it clicks.
