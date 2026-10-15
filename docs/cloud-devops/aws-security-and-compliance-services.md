---
title: "Security & Compliance Services"
---

# Security & Compliance Services

[AWS Accounts & IAM](aws-accounts-and-iam.md#debugging-accessdenied-with-cloudtrail)
already covers CloudTrail from the "debug this AccessDenied" angle. This
page covers the rest of the services the exam groups under security,
identity, and compliance — each watching for, or blocking, a different
kind of problem. The distinctions between them (which watches *actions*
vs *configuration* vs *known vulnerabilities* vs *active attacks*) are
what the exam actually tests, more than any single service's feature list.

## WAF — Web Application Firewall

- Protects against **application-layer (layer 7)** attacks: SQL
  injection, cross-site scripting, and rate-based rules (block an IP
  making too many requests per 5 minutes).
- Attaches to **CloudFront, an Application Load Balancer, API Gateway,
  or AppSync** — never directly to EC2 or a Network Load Balancer, since
  those don't terminate HTTP themselves.
- A **Web ACL** holds an ordered list of **rules** — hand-written, or
  pulled from an AWS/Marketplace **managed rule group** (e.g. a
  ready-made "block the OWASP Top 10" rule set) instead of writing every
  pattern yourself.

## Shield — DDoS Protection

|  | Shield Standard | Shield Advanced |
|---|---|---|
| Cost | Free, automatic, every AWS customer | Paid subscription |
| Protects against | Common layer 3/4 attacks (e.g. SYN floods) | Same, plus more sophisticated/large-scale attacks |
| Support | None dedicated | 24/7 access to the DDoS Response Team (DRT) |
| Cost protection | None | Covers scaling charges incurred from an attack-driven traffic spike |

- Shield guards the **network/transport layer**; WAF guards the
  **application layer** — a real production setup typically runs both
  together, not one instead of the other.

## GuardDuty — Continuous Threat Detection

- Machine-learning-based threat detection that's **always on** once
  enabled — no agent to install, analyzes CloudTrail logs, VPC Flow
  Logs, and DNS logs it already has access to.
- Finds *active, unusual behavior*: credentials being used from a
  geography they've never been used from, an EC2 instance suddenly
  talking to a known cryptomining or command-and-control IP.
- This is **reactive/continuous** monitoring for things already
  happening — contrast with Inspector below, which looks for problems
  *before* they're exploited.

## Inspector — Vulnerability Scanning

- Automated, continuous vulnerability scanning for **EC2 instances,
  container images in ECR, and Lambda functions**.
- Finds **known CVEs** and unintended network exposure (e.g. a security
  group that's wider than it needs to be).
- This is **proactive** — it scans for known weaknesses in what you've
  deployed, not for an attack already underway.

!!! note "GuardDuty vs Inspector, the exam's favorite pairing here"

    GuardDuty asks "is something bad happening right now." Inspector
    asks "does this resource already have a known weakness, whether or
    not it's being exploited yet." A question about finding *unpatched
    software* points to Inspector; a question about *detecting a
    compromised credential in active use* points to GuardDuty.

## Macie — Sensitive Data Discovery

- Machine-learning-powered scanning, specifically of **S3**, that finds
  sensitive data sitting in a bucket — PII, credit card numbers, API
  keys committed by mistake.
- The typical exam scenario: "find out if any S3 bucket mistakenly made
  public contains sensitive customer data" — Macie, not Inspector (which
  doesn't look at S3 object contents at all) and not GuardDuty (which
  watches behavior, not data content).

## AWS Config — Resource Configuration Compliance

- Records **configuration changes to resources over time** — a
  timeline answering "what did this security group's rules actually
  look like at 3 PM yesterday," independent of who made the change.
- **Config Rules** continuously evaluate resources against a desired
  state (e.g. "every EBS volume must be encrypted") and flag — or,
  with a remediation action attached, automatically fix — anything
  non-compliant.
- This is exactly what
  [Control Tower's detective guardrails](aws-organizations-and-control-tower.md#control-tower)
  are built from.

!!! danger "Config vs CloudTrail — the exam's other favorite pairing"

    - **CloudTrail** answers "who made this API call, and when" — an
      audit log of *actions*, already covered for
      [debugging AccessDenied](aws-accounts-and-iam.md#debugging-accessdenied-with-cloudtrail).
    - **AWS Config** answers "what did this resource's *configuration*
      look like at a given point in time" — a history of *state*, not
      actions.
    - A question about "who deleted this S3 bucket" is CloudTrail. A
      question about "show me every time this security group's rules
      changed, and what they changed to" is Config.

## Quick Reference: Which Service, Which Question

| Exam phrase | Service |
|---|---|
| "Block SQL injection / XSS on our web app" | WAF |
| "Protect against a large-scale DDoS attack, with cost protection" | Shield Advanced |
| "Detect a compromised credential being used unusually" | GuardDuty |
| "Find unpatched CVEs on our EC2 fleet" | Inspector |
| "Find out if sensitive data is sitting in a public S3 bucket" | Macie |
| "Track every configuration change to this resource over time" | AWS Config |
| "Find out who made this API call" | CloudTrail |
