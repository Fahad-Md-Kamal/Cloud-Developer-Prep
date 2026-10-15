---
title: "SAA-C03 Practice Quiz: Domain-by-Domain"
---

# SAA-C03 Practice Quiz: Domain-by-Domain

Questions drawn directly from the comparisons and "exam signal" callouts
across the
[Domain Review Index](saa-c03-exam-prep-index.md) — these are a
self-check against material already on this site, not reproductions of
real AWS exam questions. Organized by the same 4 scored domains as the
index, for the same reason: review by domain weight, not by study week.

## Domain 1: Design Secure Architectures (30%)

**Q1.** An account's Sandbox OU has an SCP attached that allows
`s3:*` and `ec2:*`. A developer in that OU has an IAM identity policy
granting `dynamodb:*`. Can they call a DynamoDB action?

- **A.** Yes, because the SCP doesn't explicitly deny it.
- **B.** No, because the SCP's allow list doesn't include DynamoDB.
- **C.** Yes, because SCPs only block actions, never restrict them by omission.
- **D.** It depends on the account's root user settings.

??? success "✓ Correct — B) No, because the SCP's allow list doesn't include DynamoDB"

    **A) Yes, because the SCP doesn't explicitly deny it** — SCPs set a
    ceiling, not a floor. An action missing from that ceiling is denied
    exactly as if it had been explicitly denied.

    **B) No, because the SCP's allow list doesn't include DynamoDB** —
    ✓ Correct. An SCP defines the maximum available permissions; an
    IAM identity policy can never grant anything the SCP doesn't also
    allow, regardless of how permissive that identity policy is.

    **C) Yes, because SCPs only block actions, never restrict them by
    omission** — Backwards. The whole point of an SCP's allow list is
    that *anything outside it* is unavailable, which is restriction by
    omission.

    **D) It depends on the account's root user settings** — SCPs apply
    to every principal in the account, including the root user.

    See: [AWS Organizations & Control Tower](aws-organizations-and-control-tower.md#scps-set-a-ceiling-they-never-grant-anything)

**Q2.** A Lambda function has an IAM policy granting `kms:Decrypt` on a
specific customer-managed KMS key, but every decrypt call still fails
with `AccessDenied`. What's the most likely cause?

- **A.** Lambda functions can never call KMS directly.
- **B.** The KMS key's own key policy doesn't grant this role permission.
- **C.** The key needs to be an AWS managed key, not customer managed.
- **D.** `kms:Decrypt` requires MFA on every call.

??? success "✓ Correct — B) The KMS key's own key policy doesn't grant this role permission"

    **A) Lambda functions can never call KMS directly** — False; this is
    an extremely common, fully supported pattern.

    **B) The KMS key's own key policy doesn't grant this role
    permission** — ✓ Correct. A key policy (resource-based, attached to
    the key) and an IAM identity policy are evaluated together — both
    must allow the action. An IAM policy granting `kms:Decrypt` with no
    matching key policy still results in `AccessDenied`.

    **C) The key needs to be an AWS managed key, not customer managed**
    — Customer managed keys support this exact pattern; the issue is the
    missing key-policy grant, not the key type.

    **D) `kms:Decrypt` requires MFA on every call** — Not a KMS
    requirement by default.

    See: [Key policies work the same AND logic as S3](kms-secrets-and-cognito.md#key-policies-work-the-same-and-logic-as-s3)

**Q3.** An application needs database credentials that rotate
automatically on a schedule, with minimal setup. Which service?

- **A.** Systems Manager Parameter Store (SecureString)
- **B.** Secrets Manager
- **C.** KMS
- **D.** AWS Config

??? success "✓ Correct — B) Secrets Manager"

    **A) Parameter Store (SecureString)** — Encrypts the value, but has
    no built-in rotation — you'd have to build that yourself with
    EventBridge + a custom Lambda.

    **B) Secrets Manager** — ✓ Correct. Built-in, one-click automatic
    rotation for RDS/Aurora/Redshift/DocumentDB, with AWS managing the
    rotation Lambda.

    **C) KMS** — Manages encryption keys, not application secret values.

    **D) AWS Config** — Tracks resource configuration compliance, unrelated to secrets.

    See: [Secrets Manager vs Parameter Store](kms-secrets-and-cognito.md#secrets-manager-vs-parameter-store)

**Q4.** Security needs to know whether an EC2 fleet has any unpatched,
known CVEs — not whether anything is actively being exploited right now.
Which service?

- **A.** GuardDuty
- **B.** Inspector
- **C.** Macie
- **D.** AWS Config

??? success "✓ Correct — B) Inspector"

    **A) GuardDuty** — Continuous, ML-based detection of *active,
    unusual behavior* (compromised credentials, malicious IP traffic) —
    reactive, not a vulnerability scan.

    **B) Inspector** — ✓ Correct. Proactive, automated scanning for
    known CVEs and network exposure on EC2, ECR images, and Lambda.

    **C) Macie** — Scans S3 specifically for sensitive data, not
    vulnerabilities.

    **D) AWS Config** — Tracks configuration *state* over time, not
    vulnerabilities.

    See: [GuardDuty vs Inspector](aws-security-and-compliance-services.md#inspector-vulnerability-scanning)

## Domain 2: Design Resilient Architectures (26%)

**Q5.** VPC A peers with VPC B. VPC B peers with VPC C. Can an instance
in VPC A reach an instance in VPC C through this setup?

- **A.** Yes, peering is transitive by default.
- **B.** No — VPC A would need its own direct peering connection to VPC C.
- **C.** Yes, but only if all three CIDR blocks are identical.
- **D.** Yes, if a Transit Gateway is also attached to VPC B.

??? success "✓ Correct — B) No — VPC A would need its own direct peering connection to VPC C"

    **A) Yes, peering is transitive by default** — The single most
    tested fact about VPC Peering: it is explicitly **not** transitive.

    **B) No — VPC A would need its own direct peering connection to VPC
    C** — ✓ Correct. Every pair that needs to communicate needs its own
    peering connection.

    **C) Yes, but only if all three CIDR blocks are identical** —
    Overlapping CIDRs would actually break peering entirely, not enable
    transitivity.

    **D) Yes, if a Transit Gateway is also attached to VPC B** — A
    Transit Gateway solves this, but by *replacing* the peering mesh
    with hub attachments — VPC A and C would need to attach to the same
    Transit Gateway, not rely on B's peering connections.

    See: [VPC Peering](vpc-connectivity-and-hybrid-networking.md#vpc-peering)

**Q6.** An application needs an RTO of about 15 minutes and an RPO of a
few minutes, at moderate cost — not the expense of running full capacity
in two regions all the time. Which DR strategy?

- **A.** Backup and Restore
- **B.** Pilot Light
- **C.** Multi-Site Active/Active
- **D.** Doing nothing and relying on a single region's Multi-AZ setup

??? success "✓ Correct — B) Pilot Light"

    **A) Backup and Restore** — Cheapest, but RTO is measured in hours,
    not minutes — too slow for this requirement.

    **B) Pilot Light** — ✓ Correct. The data layer stays continuously
    replicated and running; compute is provisioned on demand at
    failover — minutes-scale RTO at a fraction of Warm Standby's cost.

    **C) Multi-Site Active/Active** — Meets the RTO/RPO easily, but at
    the highest cost — full production capacity running in both regions
    at all times, which the question explicitly rules out.

    **D) Single-region Multi-AZ only** — Protects against an AZ failure,
    not a full regional outage, which is what RTO/RPO targets like these
    are normally guarding against.

    See: [The Four DR Strategies](disaster-recovery-strategies.md#the-four-dr-strategies-in-order-of-cost-and-speed)

**Q7.** An application writes to the same logical dataset from users in
three different regions simultaneously, and every region must accept
writes with no single "primary." Which replication model fits?

- **A.** Aurora Global Database
- **B.** DynamoDB Global Tables
- **C.** RDS Multi-AZ
- **D.** S3 Cross-Region Replication

??? success "✓ Correct — B) DynamoDB Global Tables"

    **A) Aurora Global Database** — One primary region accepts writes;
    secondary regions are read-only until explicitly promoted. Doesn't
    fit "every region accepts writes."

    **B) DynamoDB Global Tables** — ✓ Correct. Multi-active by design —
    every replica in every region accepts both reads and writes, with
    last-writer-wins conflict resolution.

    **C) RDS Multi-AZ** — A single-region high-availability feature, not
    multi-region at all.

    **D) S3 Cross-Region Replication** — One-directional object
    replication, not a multi-writer database pattern.

    See: [Global Tables](dynamodb-and-elasticache.md#global-tables)

**Q8.** A Lambda function consuming an SQS queue keeps processing the
same message more than once under normal operation, not just after a
crash. What's the most likely misconfiguration?

- **A.** The queue is Standard instead of FIFO.
- **B.** The visibility timeout is shorter than the function's actual processing time.
- **C.** The dead-letter queue's `maxReceiveCount` is set too high.
- **D.** Long polling is disabled.

??? success "✓ Correct — B) The visibility timeout is shorter than the function's actual processing time"

    **A) Standard instead of FIFO** — Standard queues can occasionally
    duplicate, but *systematic* duplication under normal operation
    points to a specific, fixable misconfiguration, not just the queue
    type.

    **B) Visibility timeout too short** — ✓ Correct. If the timeout
    expires before the consumer finishes and deletes the message, it
    becomes visible again and a second invocation picks it up while the
    first is still running — duplication by design, not failure.

    **C) `maxReceiveCount` too high** — Affects when a message moves to
    the DLQ, not duplicate processing before that point.

    **D) Long polling disabled** — Affects empty-poll efficiency and
    cost, not duplicate delivery.

    See: [SQS: Visibility Timeout](messaging-and-event-driven-services.md#sqs-standard-vs-fifo-visibility-timeout-dlqs)

## Domain 3: Design High-Performing Architectures (24%)

**Q9.** A company needs to insert a fleet of third-party intrusion
detection appliances transparently in front of all traffic entering a
VPC, and scale that appliance fleet with load. Which service?

- **A.** Application Load Balancer
- **B.** Network Load Balancer
- **C.** Gateway Load Balancer
- **D.** AWS WAF

??? success "✓ Correct — C) Gateway Load Balancer"

    **A) ALB** — Layer 7, routes HTTP traffic to application targets —
    not built for transparently passing all traffic through inspection
    appliances.

    **B) NLB** — Layer 4, extreme TCP/UDP throughput — closer, but still
    not built for the appliance-fleet insertion pattern.

    **C) Gateway Load Balancer** — ✓ Correct. Purpose-built for
    distributing traffic through a scalable fleet of third-party
    virtual appliances via GENEVE encapsulation.

    **D) AWS WAF** — Operates at layer 7 against HTTP-specific threats
    (SQLi, XSS) — not a generic traffic-inspection appliance fleet.

    See: [Gateway Load Balancer (GWLB)](load-balancing-and-dns.md#gateway-load-balancer-gwlb)

**Q10.** An application in a private subnet calls S3 frequently. The
team wants to cut data transfer cost and avoid routing this traffic
through the NAT Gateway. What should they add?

- **A.** An Interface VPC Endpoint
- **B.** A Gateway VPC Endpoint
- **C.** A second NAT Gateway in the same AZ
- **D.** AWS PrivateLink to a third-party VPC Endpoint Service

??? success "✓ Correct — B) A Gateway VPC Endpoint"

    **A) Interface VPC Endpoint** — Works for most services, but **not**
    S3 or DynamoDB, and it carries its own hourly + per-GB charge rather
    than being free.

    **B) Gateway VPC Endpoint** — ✓ Correct. Free, supports exactly S3
    and DynamoDB, and removes this traffic from the NAT Gateway's
    per-GB data-processing charge entirely.

    **C) A second NAT Gateway** — Adds redundancy, not cost reduction —
    every NAT Gateway bills its own per-GB charge.

    **D) PrivateLink to a third-party service** — PrivateLink is for
    reaching a *specific* service exposed by a provider, not AWS's own
    S3 service.

    See: [VPC Endpoints](vpc-connectivity-and-hybrid-networking.md#vpc-endpoints-reaching-aws-services-without-the-internet)

**Q11.** A team wants to cache responses directly in API Gateway to
reduce load on a Lambda backend. They've built the API as an HTTP API
for its lower cost and latency. What should they know?

- **A.** HTTP APIs support caching identically to REST APIs.
- **B.** API Gateway caching isn't available for HTTP APIs — they'd need a REST API, or caching elsewhere (e.g. CloudFront).
- **C.** Caching requires switching the backend from Lambda to an ALB.
- **D.** HTTP APIs cache automatically with no configuration needed.

??? success "✓ Correct — B) API Gateway caching isn't available for HTTP APIs"

    **A) Identical support** — False; this is the actual trap in the
    question.

    **B) Not available for HTTP APIs** — ✓ Correct. Built-in API Gateway
    caching is a REST API feature only. An HTTP API needs caching built
    another way, typically CloudFront in front of it.

    **C) Requires switching to an ALB backend** — The backend type
    doesn't change the HTTP-API caching limitation.

    **D) Caches automatically** — No API Gateway caching is automatic;
    REST API caching is opt-in and configured per stage.

    See: [API Gateway Caching](caching-layers-and-global-accelerator.md#api-gateway-caching)

**Q12.** Multiple EC2 instances across several AZs need to read and
write the same shared directory concurrently. Which storage option?

- **A.** A single EBS volume, attached to all instances
- **B.** EFS
- **C.** Instance Store
- **D.** FSx for Windows File Server, for a Linux fleet

??? success "✓ Correct — B) EFS"

    **A) A single EBS volume on all instances** — EBS attaches to one
    instance at a time (Multi-Attach is a narrow, specific exception,
    not a general shared-filesystem solution).

    **B) EFS** — ✓ Correct. A managed NFS file system built to be
    mounted by many instances across AZs at once.

    **C) Instance Store** — Physically local to one host, and wiped on
    stop/termination — the opposite of shared and persistent.

    **D) FSx for Windows File Server for a Linux fleet** — Built for
    Windows/SMB workloads, not a general Linux shared-filesystem fit.

    See: [EBS vs EFS vs FSx vs Instance Store](storage-options-ebs-efs-fsx.md#ebs-vs-efs-vs-fsx-vs-instance-store)

## Domain 4: Design Cost-Optimized Architectures (20%)

**Q13.** A nightly batch job runs for a few hours, can tolerate being
interrupted and restarted, and needs to run as cheaply as possible.
Which EC2 purchasing option?

- **A.** On-Demand
- **B.** Reserved Instances
- **C.** Spot Instances
- **D.** Savings Plans

??? success "✓ Correct — C) Spot Instances"

    **A) On-Demand** — No commitment needed, but no discount either —
    the most expensive fit for a workload with no special requirements.

    **B) Reserved Instances** — A 1/3-year commitment for a steady-state
    workload; a nightly interruptible batch job doesn't need or benefit
    from that commitment.

    **C) Spot Instances** — ✓ Correct. Up to ~90% off, and the
    "can tolerate interruption" requirement is exactly Spot's target
    workload — AWS can reclaim the instance with a two-minute warning.

    **D) Savings Plans** — Same commitment trade-off as Reserved
    Instances — a discount for predictable, steady-state spend, not
    interruptible workloads.

    See: [Purchasing Options](ec2-instance-types-and-purchasing-options.md#purchasing-options-trading-flexibility-for-discount)

**Q14.** Compliance data must be retained for 7 years, retrieval within
12 hours is acceptable, and storage cost should be as low as possible.
Which S3 storage class?

- **A.** S3 Standard-IA
- **B.** S3 Glacier Instant Retrieval
- **C.** S3 Glacier Deep Archive
- **D.** S3 Intelligent-Tiering

??? success "✓ Correct — C) S3 Glacier Deep Archive"

    **A) Standard-IA** — Millisecond retrieval, but far more expensive
    than needed for data that's rarely, if ever, accessed again.

    **B) Glacier Instant Retrieval** — Cheaper than Standard-IA, but
    still priced for millisecond access this use case doesn't need.

    **C) Glacier Deep Archive** — ✓ Correct. The cheapest S3 storage
    class; a 12-hour retrieval window is exactly what it's built for,
    and long-term compliance retention is its textbook use case.

    **D) Intelligent-Tiering** — Built for unpredictable/changing access
    patterns, not known long-term archival with no expected access.

    See: [S3 Storage Classes](storage-and-observability.md#storage-classes)

**Q15.** A FinOps team wants the most detailed, line-item-level billing
data available, to feed into their own custom cost-allocation tool.
Which should they use?

- **A.** AWS Budgets
- **B.** Cost Explorer
- **C.** Cost and Usage Reports (CUR)
- **D.** Trusted Advisor

??? success "✓ Correct — C) Cost and Usage Reports (CUR)"

    **A) AWS Budgets** — Sets alerts/thresholds on spend; not a detailed
    billing data export.

    **B) Cost Explorer** — Interactive, visual analysis of spend
    trends — the right tool for exploring "what happened," but not the
    rawest possible data export.

    **C) CUR** — ✓ Correct. The most detailed, granular billing data AWS
    produces, delivered as files to S3 specifically for custom analysis
    and tooling.

    **D) Trusted Advisor** — Gives optimization recommendations, not a
    billing data export.

    See: [Cost Explorer vs CUR](cost-management-tools.md#cost-and-usage-reports-cur)

**Q16.** A workload has highly variable, unpredictable traffic, and the
team wants to avoid paying for idle database capacity overnight and on
weekends. Which fits best?

- **A.** A fixed-size RDS instance sized for peak load
- **B.** Aurora Serverless
- **C.** A Reserved Instance for the database
- **D.** DynamoDB with provisioned capacity sized for peak load

??? success "✓ Correct — B) Aurora Serverless"

    **A) Fixed-size RDS for peak** — Pays for peak capacity 24/7, the
    exact idle-cost problem the question is trying to avoid.

    **B) Aurora Serverless** — ✓ Correct. Capacity (ACUs) scales up and
    down automatically with actual load — the textbook fit for
    unpredictable, spiky traffic where idle capacity is a real cost
    concern.

    **C) A Reserved Instance for the database** — Locks in a specific
    size for a 1/3-year term — the opposite of what variable,
    unpredictable load wants.

    **D) DynamoDB provisioned for peak** — Same idle-capacity problem as
    (A); on-demand DynamoDB capacity would fit, but *provisioned at peak
    size* doesn't.

    See: [Aurora Serverless](aurora-and-rds-proxy.md#aurora-serverless)
