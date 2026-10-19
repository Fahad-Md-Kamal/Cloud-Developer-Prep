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

## Official AWS Practice Question Set

The questions above are self-made, drawn from this site's own content. The
20 below are different: they're AWS's own **free, official Practice
Question Set** for SAA-C03 (© Amazon Web Services), reproduced here in
full because it's publicly published training material, not a leaked or
reconstructed exam dump. Numbered Q17-Q36 to continue from the set above.

**Q17.** A solutions architect is designing a containerized web
application on Amazon ECS. To minimize cost, multiple copies of a task
run on each container instance, and the number of copies must scale up
and down with load. Which routing solution distributes load across the
multiple tasks?

- **A.** An Application Load Balancer using path-based routing.
- **B.** An Application Load Balancer using dynamic host port mapping.
- **C.** A Route 53 alias record set using a failover routing policy.
- **D.** A Route 53 alias record set using a weighted routing policy.

??? success "✓ Correct — B) An Application Load Balancer using dynamic host port mapping"

    **A) Path-based routing** — Routes by URL path to different target
    groups for different *services*. It doesn't help distribute load
    across multiple identical tasks of the *same* service on the same
    instance.

    **B) Dynamic host port mapping** — ✓ Correct. ECS picks a random free
    host port for each task when the container port isn't fixed, and
    registers each one with the ALB's target group — letting several
    copies of the same task share one container instance without port
    conflicts.

    **C) Route 53 failover routing** — Routes to a backup destination
    when a primary fails; not built for distributing load across many
    tasks on one instance.

    **D) Route 53 weighted routing** — Splits traffic by a fixed
    proportion between destinations; same mismatch as failover routing.

    See: [ALB Integration and Service Discovery](container-orchestration-ecs-eks.md#alb-integration-and-service-discovery)

**Q18.** A company has strict data protection requirements. A solutions
architect must ensure backend RDS DB instances can't be reached from the
internet, and are reachable from the application tier over one specific
port only. Which two actions meet this? (Select TWO.)

- **A.** Specify a DB subnet group that contains only private subnets.
- **B.** Attach an elastic network interface with a private IPv4 address to each DB instance.
- **C.** Configure AWS Shield with the VPC, and update the route tables for the DB subnets.
- **D.** Configure a Direct Connect connection on the database port between the application tier and the backend.
- **E.** Add an inbound rule to the database security group allowing requests from the application tier's security group, and remove other inbound rules.

??? success "✓ Correct — A) DB subnet group with only private subnets, and E) security group restricted to the app tier"

    **A) Private-subnets-only DB subnet group** — ✓ Correct. No route to
    an internet gateway means no path in from the internet, regardless of
    any other setting.

    **B) An elastic network interface with a private IP** — Every
    instance already has one; attaching an extra one doesn't restrict
    anything.

    **C) Shield + route table updates** — Shield protects against DDoS;
    it isn't a routing or access-control mechanism and can't be a route
    table target.

    **D) Direct Connect on the DB port** — A dedicated network link
    between premises and AWS — solves a completely different problem
    than restricting access within a VPC.

    **E) Security group scoped to the app tier's security group** —
    ✓ Correct. Referencing the app tier's security group (rather than an
    IP range) as the source means only traffic actually originating from
    that tier is allowed, over exactly the port specified.

    See: [Keeping the database layer unreachable from outside](../database/database-security-and-breach-prevention.md#2-how-do-you-architect-a-database-so-its-not-directly-reachable-even-if-the-application-layer-is-compromised)

**Q19.** An application runs on two EC2 instances behind a Network Load
Balancer, both in a single Availability Zone. What should a solutions
architect do to make this more highly available?

- **A.** Create a new VPC with two new EC2 instances in the same AZ as the originals, peered to the first VPC.
- **B.** Replace the NLB with an ALB configured with the EC2 instances in an Auto Scaling group.
- **C.** Configure Route 53 health checks on the EC2 instances behind the NLB, with a failover routing policy.
- **D.** Place the EC2 instances in an Auto Scaling group that extends across multiple AZs, and target that ASG from the NLB.

??? success "✓ Correct — D) An Auto Scaling group spanning multiple AZs, targeted by the NLB"

    **A) A peered VPC, same AZ** — Adds a second VPC, but every instance
    is still in one AZ — a single AZ failure still takes the whole
    application down.

    **B) Switching to an ALB** — Both ALB and NLB are already inherently
    highly available load balancers; the real gap is that the *targets*
    only exist in one AZ, which swapping load balancer type doesn't fix.

    **C) Route 53 failover with no secondary AZ** — Failover routing
    needs an actual secondary destination; this option never puts
    instances in a second AZ at all.

    **D) An Auto Scaling group across multiple AZs** — ✓ Correct. This is
    what actually removes the single-AZ dependency, and the NLB can
    target an ASG directly, automatically picking up new instances as
    they launch.

    See: [Network Load Balancer (NLB)](load-balancing-and-dns.md#network-load-balancer-nlb)

**Q20.** A reporting application behind an ALB runs on an Auto Scaling
group across multiple AZs. Complex reports can take up to 15 minutes to
respond. A solutions architect wants to avoid users seeing HTTP 5xx
errors when a request is mid-flight during a scale-in event. What should
they do?

- **A.** Enable sticky sessions (session affinity) for the target group.
- **B.** Increase the instance size in the ALB target group.
- **C.** Increase the ASG's cooldown period beyond the longest response time.
- **D.** Increase the target group's deregistration delay timeout to more than 900 seconds.

??? success "✓ Correct — D) Increase the deregistration delay beyond 900 seconds"

    **A) Sticky sessions** — Keeps a client routed to the same instance
    across requests; doesn't change what happens to an in-flight request
    when that instance is slated for removal.

    **B) A larger instance size** — Would likely speed up processing, but
    doesn't guarantee an in-flight request survives a scale-in event —
    it's a performance change, not a lifecycle guarantee.

    **C) A longer ASG cooldown** — Cooldown controls how soon Auto
    Scaling takes its *next* scaling action; it has no effect on whether
    an *already-targeted* instance finishes serving a request before
    being deregistered.

    **D) A longer deregistration delay** — ✓ Correct. The target group
    waits this long before completing deregistration, giving an
    in-flight request time to finish. Default is 300 seconds; a 15-minute
    response time needs it raised past 900.

    See: [Health Checks — Debugging Guide](load-balancing-and-dns.md#health-checks-debugging-guide)

**Q21.** A company is migrating to AWS. An application server sends
email notifications to customers, and the migration must use only
managed AWS services. Which solution meets this?

- **A.** Amazon SQS with a standard queue.
- **B.** An EC2 instance hosting the application server, sending email notifications itself.
- **C.** Amazon SQS with a FIFO queue.
- **D.** Amazon SNS with the email protocol.

??? success "✓ Correct — D) Amazon SNS with the email protocol"

    **A) / C) SQS (standard or FIFO)** — SQS queues messages between
    software components; it has no built-in way to push a message out to
    a person's inbox.

    **B) A self-hosted EC2 mail sender** — Works, but isn't a *managed*
    service — exactly what the requirement rules out.

    **D) SNS with the email protocol** — ✓ Correct. SNS is a fully
    managed pub/sub service that supports delivering directly to an email
    address as one of its native subscription protocols.

    See: [Messaging & Event-Driven Services](messaging-and-event-driven-services.md)

**Q22.** A company used EC2 Spot Instances for a now-complete
demonstration. A solutions architect must remove them to stop incurring
cost. What should they do?

- **A.** Cancel the Spot request only.
- **B.** Terminate the Spot Instances only.
- **C.** Cancel the Spot request, then terminate the Spot Instances.
- **D.** Terminate the Spot Instances, then cancel the Spot request.

??? success "✓ Correct — C) Cancel the Spot request, then terminate the Spot Instances"

    **A) Cancel the request only** — The running instances keep running
    and keep incurring cost; canceling the request doesn't touch them.

    **B) Terminate the instances only** — With the request still active,
    new instances can launch to fulfill it.

    **C) Cancel, then terminate** — ✓ Correct. Canceling the request
    first stops it from replacing what you're about to terminate.

    **D) Terminate, then cancel** — Backwards — terminating first, while
    the request is still open, can let a replacement instance launch
    before the cancel takes effect.

    See: [Purchasing Options: Trading Flexibility for Discount](ec2-instance-types-and-purchasing-options.md#purchasing-options-trading-flexibility-for-discount)

**Q23.** A company needs to look up configuration details about how a
Linux EC2 instance was launched. Which command gathers that system
metadata?

- **A.** `curl http://169.254.169.254/latest/meta-data`
- **B.** `curl http://localhost/latest/meta-data`
- **C.** `curl http://254.169.254.169/latest/meta-data`
- **D.** `curl http://192.168.0.1/latest/meta-data`

??? success "✓ Correct — A) curl http://169.254.169.254/latest/meta-data"

    **A) 169.254.169.254** — ✓ Correct. This is the fixed link-local
    address the Instance Metadata Service always listens on, from inside
    the instance only.

    **B) localhost (127.0.0.1)** — Not where the metadata service
    listens; the link-local address is a deliberately different,
    non-routable address.

    **C) 254.169.254.169** — A digit-scrambled version of the real
    address — not it.

    **D) 192.168.0.1** — A private, routable address, not the reserved
    link-local block the metadata service uses.

    See: [Instance Profiles and IMDSv2](aws-accounts-and-iam.md#instance-profiles-and-imdsv2)

**Q24.** A company's on-premises app exports 20-30 GB log files, uploaded
directly to S3 over a connection with intermittent failures, and the
upload sometimes fails. A solutions architect must fix this with minimal
operational overhead. Which solution?

- **A.** Enable S3 Transfer Acceleration.
- **B.** Copy the files to an EC2 instance in the closest Region, then use an S3 Lifecycle policy to copy them to S3.
- **C.** Use multipart upload to S3.
- **D.** Upload to two Regions simultaneously with two-way Cross-Region Replication enabled.

??? success "✓ Correct — C) Use multipart upload to S3"

    **A) Transfer Acceleration** — Speeds uploads via edge locations, but
    doesn't address a single large `PUT` failing partway through on a
    flaky connection.

    **B) Route through EC2 + Lifecycle policies** — Lifecycle policies
    move objects *between S3 storage classes*; they can't pull files in
    from EC2 block storage, and this adds operational overhead rather
    than minimizing it.

    **C) Multipart upload** — ✓ Correct. Splits a large file into parts
    uploaded independently; if one part fails on a flaky connection, only
    that part needs to be retried, not the whole file.

    **D) Dual-region upload + replication** — Doesn't solve the
    size/failure problem at all, and adds real operational overhead.

    See: [S3 Deep Dive](storage-and-observability.md#s3-deep-dive)

**Q25.** A new EC2-hosted database workload needs a single EBS volume
that can support up to 20,000 IOPS. Which EBS volume type?

- **A.** Throughput Optimized HDD
- **B.** Provisioned IOPS SSD
- **C.** General Purpose SSD
- **D.** Cold HDD

??? success "✓ Correct — B) Provisioned IOPS SSD"

    **A) Throughput Optimized HDD** — Capped around 500 IOPS per volume —
    nowhere close.

    **B) Provisioned IOPS SSD** — ✓ Correct. Built specifically to
    guarantee a chosen IOPS figure, up into the tens of thousands per
    volume — the only type that reliably clears 20,000.

    **C) General Purpose SSD** — Tops out around 16,000 IOPS per
    volume — under the requirement.

    **D) Cold HDD** — The lowest-cost, lowest-performance HDD tier, sized
    for throughput on sequential cold data, not IOPS.

    See: [EBS vs EFS vs FSx vs Instance Store](storage-options-ebs-efs-fsx.md#ebs-vs-efs-vs-fsx-vs-instance-store)

**Q26.** An image-processing app's usage spikes unpredictably; processing
time scales with image size and can take up to 20 minutes for large
files. It uses a web tier, an SQS standard queue, and EC2 consumers.
Under high volume, the SQS backlog grows and users see delays. What
should a solutions architect do to improve performance, following cloud
best practices?

- **A.** Purchase enough Dedicated Instances to meet peak demand, deployed as consumers.
- **B.** Convert the standard queue to a FIFO queue, and increase the visibility timeout.
- **C.** Configure a scalable Lambda function as the consumer.
- **D.** Make the consumer an Auto Scaling group, scaling on the `ApproximateNumberOfMessages` CloudWatch metric.

??? success "✓ Correct — D) An Auto Scaling group scaling on ApproximateNumberOfMessages"

    **A) Dedicated Instances for peak** — Pays for peak capacity
    constantly, and still doesn't *automatically* track a variable,
    unpredictable backlog.

    **B) FIFO + longer visibility timeout** — FIFO solves ordering
    problems, not throughput under load — it doesn't scale the consumer
    fleet at all.

    **C) A scalable Lambda consumer** — Lambda has a 15-minute maximum
    execution duration; some of these jobs can take up to 20 minutes,
    which would simply fail.

    **D) ASG scaling on the queue backlog metric** — ✓ Correct. Scaling
    the consumer fleet directly off `ApproximateNumberOfMessages` lets
    capacity track the backlog automatically, with EC2 consumers that
    have no execution-time ceiling.

    See: [Worker Pools & Backpressure](../backend/python/worker-pools-and-backpressure.md)

**Q27.** A chat application stores messages with a key-value data model.
Groups of users read the same messages repeatedly, and the database must
scale to a high read rate with microsecond latency. Which database
solution?

- **A.** Aurora with Aurora Replicas
- **B.** DynamoDB with DynamoDB Accelerator (DAX)
- **C.** Aurora with ElastiCache for Memcached
- **D.** Neptune with ElastiCache for Memcached

??? success "✓ Correct — B) DynamoDB with DAX"

    **A) Aurora + Replicas** — Aurora is relational, not key-value, and
    typical latency is milliseconds, not microseconds.

    **B) DynamoDB + DAX** — ✓ Correct. DynamoDB is a native key-value
    store; DAX is an in-memory cache purpose-built in front of it,
    delivering microsecond read latency for exactly this repeated-read
    pattern.

    **C) Aurora + ElastiCache** — Same relational mismatch as (A), even
    with a cache layered in front.

    **D) Neptune + ElastiCache** — Neptune is a graph database, built for
    highly connected data, not simple key-value lookups.

    See: [DAX — DynamoDB Accelerator](dynamodb-and-elasticache.md#dax-dynamodb-accelerator)

**Q28.** One AWS account runs production workloads; a separate account
holds the security team. During audits, the security team needs to view
specific account settings and resource configurations in the production
account. Which solution follows AWS security best practices?

- **A.** Create an IAM user per security team member in the production account, with a permissions policy attached to each.
- **B.** Create an IAM role in the production account with the needed permissions, and add the security account to its trust policy.
- **C.** Create a new IAM user with administrative privileges in the production account, shared by the security team.
- **D.** Create an IAM user per security team member in the production account, attached to a new IAM group with the needed permissions.

??? success "✓ Correct — B) An IAM role with the security account in its trust policy"

    **A) / D) Per-member IAM users in the production account** — Both
    create long-lived credentials *in the account being audited*, which
    is exactly what cross-account roles exist to avoid.

    **B) A role with the security account trusted** — ✓ Correct. A role
    grants temporary credentials assumed from the other account, with no
    long-lived production-account credentials ever created for the
    security team at all.

    **C) A shared admin IAM user** — Both over-privileged (violates least
    privilege) and shared credentials, a security anti-pattern on its
    own.

    See: [Trust Policies vs Permission Policies](aws-accounts-and-iam.md#trust-policies-vs-permission-policies)

**Q29.** A new application has an application layer and an OLTP
relational database. It must be available at all times, but the company
wants to pay the minimum for compute during idle periods. Which solution
is most cost-effective?

- **A.** Run the application in containers with ECS on AWS Fargate, using Aurora Serverless for the database.
- **B.** Run the application on burstable EC2 instances, using Redshift for the database.
- **C.** Deploy to EC2 via CloudFormation, deleting the stack at the start of each idle period.
- **D.** Run the application on EC2 in an Auto Scaling group behind an ALB, using RDS for MySQL.

??? success "✓ Correct — A) ECS on Fargate + Aurora Serverless"

    **A) Fargate + Aurora Serverless** — ✓ Correct. Fargate bills only
    for compute actually used by running tasks, and Aurora Serverless
    scales capacity down toward zero when idle — both layers avoid
    paying for idle capacity, while the application stays available.

    **B) Burstable EC2 + Redshift** — Redshift is built for OLAP
    analytics, not OLTP, and burstable instances still run (and bill)
    continuously whether idle or not.

    **C) Deleting the stack during idle periods** — Breaks the "available
    at all times" requirement outright, and loses the database's data
    along with the stack unless handled separately.

    **D) EC2 ASG + RDS MySQL** — Always-available, but at least one
    instance and the RDS instance run continuously — no idle-cost
    savings.

    See: [Aurora Serverless](aurora-and-rds-proxy.md#aurora-serverless) · [Cost, Compared](container-orchestration-ecs-eks.md#cost-compared)

**Q30.** A company must retain data records for a minimum of 5 years.
The data is rarely accessed once stored, but must be retrievable within
2 hours. Which solution is most cost-effective?

- **A.** Store the data on EFS, accessed via Direct Connect.
- **B.** Store the data in S3, with a Lifecycle policy moving it to S3 Glacier.
- **C.** Store the data on an EBS volume, and store EBS snapshots in S3.
- **D.** Store the data in S3, with a Lifecycle policy moving it to S3 Standard-IA.

??? success "✓ Correct — B) S3 with a Lifecycle policy to S3 Glacier"

    **A) EFS + Direct Connect** — A live, mounted file system plus a
    dedicated network circuit — far more expensive than this
    rarely-accessed, long-retention use case needs.

    **B) S3 → S3 Glacier via Lifecycle** — ✓ Correct. Glacier's
    (Flexible Retrieval) retrieval times fit comfortably inside the
    2-hour requirement, at a fraction of Standard-IA's storage cost for
    data kept this long.

    **C) EBS + snapshots in S3** — Adds an EBS volume's cost for no
    benefit — the data doesn't need to be attached to a running instance
    at all.

    **D) S3 Standard-IA** — Meets the retrieval-time requirement easily,
    but costs more per GB than Glacier for data retained this long with
    this little access.

    See: [Storage Classes](storage-and-observability.md#storage-classes)

**Q31.** A company stores legal documents in S3, frequently re-uploading
revised documents to the same object key, and needs to both recover
older versions and protect against accidental deletion. What's the most
operationally efficient solution?

- **A.** Enable S3 Versioning on the bucket.
- **B.** Enable MFA delete on the bucket.
- **C.** Configure S3 Cross-Region Replication to a bucket in another Region.
- **D.** Configure an S3 Lifecycle policy to archive to Glacier after 30 days.

??? success "✓ Correct — A) Enable S3 Versioning"

    **A) S3 Versioning** — ✓ Correct. Keeps every revision uploaded under
    the same key, letting any older version be retrieved, and a
    "deleted" object becomes a recoverable delete marker rather than
    being gone.

    **B) MFA delete** — Adds an extra authentication step to *permanent*
    deletes; it doesn't give access to older revisions on its own.

    **C) Cross-Region Replication** — Requires Versioning as a
    prerequisite anyway, and solves a different problem (regional
    redundancy), not version history.

    **D) Lifecycle policy to Glacier** — Changes storage class over time;
    doesn't preserve multiple versions of a document by itself.

    See: [Versioning](storage-and-observability.md#versioning)

**Q32.** A company runs its website on EC2 behind an ALB that's the
origin for a CloudFront distribution, and wants to protect against
cross-site scripting and SQL injection. What should a solutions architect
recommend?

- **A.** Enable AWS Shield Advanced, listing the CloudFront distribution as a protected resource.
- **B.** Define an AWS Shield Advanced policy in Firewall Manager to block XSS and SQL injection.
- **C.** Set up AWS WAF on the CloudFront distribution, with rules that block XSS and SQL injection.
- **D.** Deploy Firewall Manager on the EC2 instances, with rules that block XSS and SQL injection.

??? success "✓ Correct — C) AWS WAF on the CloudFront distribution"

    **A) / B) Shield Advanced (alone or via Firewall Manager)** — Shield
    protects against DDoS attacks specifically; it has no visibility into
    HTTP request content like SQL injection payloads or injected script
    tags.

    **C) AWS WAF with XSS/SQLi rules** — ✓ Correct. WAF inspects request
    content against rules purpose-built to detect exactly these two
    attack patterns, attached directly to the CloudFront distribution.

    **D) Firewall Manager on EC2 instances** — Firewall Manager centrally
    manages services like WAF and Shield across accounts; it isn't
    something installed on instances, and doesn't itself inspect HTTP
    content.

    See: [WAF — Web Application Firewall](aws-security-and-compliance-services.md#waf-web-application-firewall)

**Q33.** Which two components are required to build a Site-to-Site VPN
connection on AWS? (Select TWO.)

- **A.** An internet gateway
- **B.** A NAT gateway
- **C.** A customer gateway
- **D.** Amazon API Gateway
- **E.** A virtual private gateway

??? success "✓ Correct — C) A customer gateway, and E) a virtual private gateway"

    **A) Internet gateway** — Routes general internet traffic in and out
    of a VPC; a Site-to-Site VPN connection doesn't route through it.

    **B) NAT gateway** — Lets private instances reach the internet
    outbound; unrelated to establishing an encrypted VPN tunnel.

    **C) Customer gateway** — ✓ Correct. Represents the on-premises side
    of the tunnel — configured with the on-premises device's public IP.

    **D) API Gateway** — An entirely unrelated service, for publishing
    APIs, not networking tunnels.

    **E) Virtual private gateway** — ✓ Correct. The AWS-side VPN
    endpoint, attached to the VPC, that terminates the tunnel from the
    customer gateway.

    See: [Connecting to an Actual On-Premises Network](vpc-connectivity-and-hybrid-networking.md#connecting-to-an-actual-on-premises-network)

**Q34.** A media company's graphic-rendering app needs up to 400 GB of
temporary storage, discarded after rendering, and needs around 40,000
random IOPS. What's the most cost-effective storage option?

- **A.** A storage-optimized EC2 instance with instance store storage.
- **B.** A storage-optimized EC2 instance with a Provisioned IOPS SSD (io1/io2) EBS volume.
- **C.** A burstable EC2 instance with a Throughput Optimized HDD (st1) EBS volume.
- **D.** A burstable EC2 instance with S3 storage over a VPC endpoint.

??? success "✓ Correct — A) Storage-optimized instance with instance store"

    **A) Instance store** — ✓ Correct. Storage-optimized (`i`-family)
    instances ship with local NVMe instance store delivering well over
    300,000 IOPS at no extra cost beyond the instance's own hourly rate —
    and since this data is temporary and discarded anyway, instance
    store's wipe-on-stop behavior costs nothing here.

    **B) Provisioned IOPS SSD (EBS)** — Can hit the IOPS target, but EBS
    bills separately from the instance — real added cost for data that's
    thrown away afterward, with no need for EBS's persistence.

    **C) Throughput Optimized HDD** — Tuned for sequential throughput,
    not the random-IOPS pattern this workload needs — a straight
    mismatch.

    **D) S3 over a VPC endpoint** — Object storage, not a mounted block
    device — not how a rendering process reads/writes scratch data at
    all.

    See: [EBS vs EFS vs FSx vs Instance Store](storage-options-ebs-efs-fsx.md#ebs-vs-efs-vs-fsx-vs-instance-store)

**Q35.** A company is building a mobile version of its web app. It must
be accessible to internal and external users, with authorization,
authentication, and user management handled from one central source.
Which solution meets these requirements?

- **A.** IAM roles
- **B.** IAM users and groups
- **C.** Amazon Cognito user pools
- **D.** AWS Security Token Service (STS)

??? success "✓ Correct — C) Amazon Cognito user pools"

    **A) IAM roles** — Grant AWS API permissions to AWS principals; not
    built for managing an application's own end users.

    **B) IAM users and groups** — Same mismatch — meant for people and
    workloads accessing AWS itself, not an app's customer base.

    **C) Cognito user pools** — ✓ Correct. A managed, central directory
    for an application's own users — handles sign-up, sign-in, and
    federated/third-party login in one place, for both internal and
    external users.

    **D) STS** — Issues temporary AWS credentials for an already-known
    principal; it doesn't handle the sign-up/sign-in/user-management
    layer itself.

    See: [Cognito: Identity for Your Application's Own Users](kms-secrets-and-cognito.md#cognito-identity-for-your-applications-own-users)

**Q36.** A company processing satellite images stores them in S3 and
must replicate all data monthly to an on-premises location for
compliance — about 60 TB each time. What's the most cost-effective way
to transfer this data?

- **A.** Export monthly from S3 to an AWS Snowball Edge Storage Optimized device; ship it, transfer, and return it a week later.
- **B.** Replicate to a new S3 Standard-IA bucket, then use Storage Gateway File Gateway to transfer to on-premises, deleting the copy afterward.
- **C.** Replicate to a new S3 Standard-IA bucket, then transfer to on-premises directly from that bucket, deleting the copy afterward.
- **D.** Create a CloudFront distribution for the objects, and download from CloudFront to on-premises every month.

??? success "✓ Correct — A) AWS Snowball Edge Storage Optimized, shipped monthly"

    **A) Snowball Edge, shipped monthly** — ✓ Correct. At 60 TB, physical
    transfer beats moving the data over the internet — the device's flat
    base price (covering the device plus on-premises usage time) comes
    out cheaper than the data-transfer-out charges the other options all
    still have to pay.

    **B) / C) Replicate to Standard-IA, then transfer out** — Both add an
    extra S3 Cross-Region/same-Region Replication step with no cost
    benefit — the data could be transferred directly from the original
    bucket instead, and either way the transfer-out cost for 60 TB over
    the internet still applies.

    **D) CloudFront, monthly download** — Data transfer *into* CloudFront
    is free, but CloudFront-to-on-premises transfer *out* still bills
    per GB — at 60 TB/month this roughly doubles the cost of just
    shipping a Snowball device.

    See: [Moving Data Into and Out of AWS](storage-options-ebs-efs-fsx.md#moving-data-into-and-out-of-aws)
