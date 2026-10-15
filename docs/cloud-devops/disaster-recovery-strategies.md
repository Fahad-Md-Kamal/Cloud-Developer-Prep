---
title: "Disaster Recovery Strategies & AWS Backup"
---

# Disaster Recovery Strategies & AWS Backup

[DevOps Principles & Delivery](devops-principles-and-delivery.md#multi-region-architecture)
already covers
[Active-Active](devops-principles-and-delivery.md#active-active) vs
[Active-Passive](devops-principles-and-delivery.md#active-passive)
multi-region design, and the
[RTO/RPO](devops-principles-and-delivery.md#rto-and-rpo) trade-off table
behind every DR decision. This page adds the specific four named
strategies AWS's own Well-Architected Framework (and the exam) uses to
describe the spectrum between those two extremes, plus the services that
implement them.

## The Four DR Strategies, in Order of Cost and Speed

| Strategy | RTO | RPO | Cost | What's actually running in the DR region |
|---|---|---|---|---|
| Backup and Restore | Hours | Hours (since last backup) | Lowest | Nothing — restore from backup when disaster strikes |
| Pilot Light | Minutes to tens of minutes | Minutes | Low-moderate | Core data layer replicated and running (e.g. a replica database); everything else provisioned on demand |
| Warm Standby | Minutes | Seconds to minutes | Moderate-high | A scaled-down but fully functional copy of the whole stack, running at reduced capacity |
| Multi-Site Active/Active | Near-zero | Near-zero | Highest | Full production capacity in both regions, both serving live traffic |

- This is the same spectrum as
  [Active-Active vs Active-Passive](devops-principles-and-delivery.md#multi-region-architecture),
  broken into finer steps — Backup and Restore and Pilot Light are both
  flavors of "passive," Warm Standby sits in between, and Multi-Site
  Active/Active is the named version of "active-active."

### Pilot Light, Specifically

The name comes from a gas furnace's pilot light — a small flame always
burning, ready to ignite the full furnace instantly rather than
starting a fire from nothing.

- The DR region keeps the **data layer** continuously replicated and
  running (an RDS read replica, or Aurora Global Database's secondary
  region) — this is the piece that takes too long to recreate from a
  backup during an actual disaster.
- The **application/compute layer** (EC2, ECS) is NOT running — AMIs and
  launch templates are kept ready, and Auto Scaling launches the full
  fleet only when failover actually happens.
- Cheaper than Warm Standby because the expensive, always-on compute
  layer doesn't exist until needed; slower to fail over because that
  layer has to actually start up first.

### Warm Standby, Specifically

- A complete copy of the production stack runs continuously in the DR
  region, just at **minimal/reduced capacity** — a handful of instances
  behind an ASG instead of the full fleet.
- On failover, the ASG scales the DR region up to full production
  capacity, and traffic is redirected (typically via Route 53 failover
  routing).
- Faster than Pilot Light (everything is already running, just small),
  more expensive than Pilot Light (compute is running 24/7, not
  provisioned on demand).

!!! success "The exam signal"

    The question almost always gives you a target RTO/RPO and a budget
    constraint, and expects you to pick the cheapest strategy that still
    meets it. "A few hours of downtime is acceptable, cost is the main
    concern" → Backup and Restore. "Need to be back up in minutes, some
    cost is acceptable" → Pilot Light or Warm Standby depending on how
    many minutes. "Cannot have any downtime or data loss at all" →
    Multi-Site Active/Active, and expect the question to also mention
    cost being a secondary concern.

## AWS Backup

A centralized backup service across AWS resources (EBS, RDS, DynamoDB,
EFS, and more) — one place to define a backup policy instead of each
service's own separate backup configuration.

- **Backup plans** — define schedule, retention, and lifecycle (e.g.
  transition to cold storage after 90 days) once, and apply it via tags
  to every matching resource automatically — a new resource tagged
  correctly is backed up without anyone touching the backup
  configuration again.
- Supports **cross-region and cross-account** backup copies, directly
  relevant to the Backup and Restore DR strategy above.
- This is also what the detective-guardrail-style
  [backup policies in AWS Organizations](aws-organizations-and-control-tower.md#aws-organizations)
  enforce org-wide — a central policy that every account's resources
  comply with, rather than trusting each account to configure its own
  backups correctly.

## AWS Elastic Disaster Recovery (DRS)

Continuous, block-level replication of an entire server (on-premises or
another cloud) into a low-cost "staging area" in AWS, ready to launch as
a full EC2 instance within minutes of an actual disaster.

- Different scope than AWS Backup: Backup protects AWS-native
  resources' *data*; DRS protects an entire *server*, including its OS
  and everything installed on it, and is built specifically for
  migrating an existing DR process (or an entire physical/virtual
  server) into AWS rather than a cloud-native resource's backup.
- The staging area itself is cheap (low-cost storage and a minimal
  footprint) — the full-sized recovery instances are only launched
  during an actual drill or disaster, which is what makes DRS
  effectively a managed, automated version of Pilot Light for
  server-level (not just data-level) recovery.

!!! success "The exam signal"

    "Continuously replicate entire on-premises servers to AWS for
    disaster recovery, launch full recovery instances only when needed"
    → Elastic Disaster Recovery. "Back up AWS-native resources like RDS
    and EBS on a schedule" → AWS Backup.
