---
title: "Cloud Security Fundamentals"
---

# Cloud Security Fundamentals

This site already has deep, AWS-specific security coverage — [AWS
Security & Compliance Services](../cloud-devops/aws-security-and-compliance-services.md)
(WAF, Shield, GuardDuty, Inspector, Macie, Config),
[VPC Security Groups & Flow Logs](../cloud-devops/vpc-security-groups-and-flow-logs.md),
and [Encryption, Secrets & Identity Federation](../cloud-devops/kms-secrets-and-cognito.md).
This page is the vendor-agnostic layer underneath all of that — the
shared responsibility model every cloud provider operates on, and why
most real cloud breaches trace back to misconfiguration, not a flaw in
the provider's own infrastructure.

## 1. "What does the shared responsibility model actually mean in practice, beyond the diagram every provider shows?"

**Answer:**

- The full mechanics of AWS's version are already covered in
  [Shared Responsibility Model](../cloud-devops/aws-accounts-and-iam.md#shared-responsibility-model)
  — the core idea, true across every major cloud provider, not just AWS:
  the provider secures the infrastructure **"of" the cloud** (physical
  data centers, host hardware, the virtualization layer); the customer
  secures what they put **"in" the cloud** (data, access configuration,
  application code, network rules).
- The practical consequence worth internalizing: a misconfigured S3
  bucket, an overly permissive security group, or a hardcoded credential
  in application code are **never** the provider's failure, no matter
  how the incident gets reported publicly — they sit squarely on the
  customer's side of the line, every time.
- This single model is the reason **most real cloud security incidents
  are misconfiguration, not a provider vulnerability** — the provider's
  own infrastructure is generally extremely well-secured and
  continuously audited at a scale almost no individual customer could
  match; the customer's own configuration of what they control is where
  real-world incidents overwhelmingly actually originate.

## 2. "What does Cloud Security Posture Management (CSPM) actually do, as a category of tool?"

**Answer:**

- A CSPM tool continuously scans an organization's actual cloud
  configuration — IAM policies, storage bucket permissions, security
  group rules, encryption settings — against a known-good baseline
  (an internal policy, or a standard like CIS Benchmarks), flagging
  drift or outright misconfiguration automatically and continuously,
  rather than relying on a one-time manual audit.
- This directly operationalizes §1's core insight: since
  misconfiguration — not provider-side flaws — is where real incidents
  originate, a tool built specifically to continuously catch
  misconfiguration drift is addressing the actual, dominant risk
  category directly, rather than a secondary concern.
- AWS Config (already covered in
  [AWS Security & Compliance Services](../cloud-devops/aws-security-and-compliance-services.md#aws-config-resource-configuration-compliance))
  is AWS's own native example of this category — the general CSPM
  concept, named here, is what that specific service is an instance of.

## 3. "What's the actual mechanism behind a publicly exposed S3 bucket or database — how does this keep happening despite how well-known the risk is?"

**Answer:**

- The recurring real-world pattern: a resource created with a
  permissive default (or deliberately opened "temporarily," during
  development, for convenience) that's simply never locked back down —
  not a sophisticated attack, a configuration that was always wrong,
  sitting unnoticed until someone finds it.
- **Defense in depth** is the standard mitigation layering, each layer
  catching what the one before it might miss: restrictive defaults
  (new resources start locked down, not open), automated scanning
  (CSPM, §2) catching drift continuously rather than relying on a human
  to remember, and **least privilege** applied consistently (a resource
  or role only ever granted exactly the access its actual function
  needs, nothing broader "just in case") so that even a real
  misconfiguration has a smaller realistic blast radius.
- This is the cloud-infrastructure-level application of the same
  database-specific principle already covered in
  [Database Security §2](../database/database-security-and-breach-prevention.md#2-how-do-you-architect-a-database-so-its-not-directly-reachable-even-if-the-application-layer-is-compromised)
  — architecting so a single mistake doesn't cascade into full exposure,
  rather than relying entirely on every individual configuration step
  being done correctly forever.

| Pros | Cons / Trade-offs |
|---|---|
| The shared responsibility model gives a clear, unambiguous line of ownership | Easy to misunderstand or assume the provider covers more than it actually does |
| CSPM catches configuration drift continuously, not just at audit time | Only as good as the baseline/policy it's checking against — a wrong baseline gives false confidence |
| Restrictive defaults prevent the "opened temporarily, forgotten" pattern at the source | Can slow down legitimate day-to-day development work if applied without any fast-path |
| Defense in depth limits blast radius even when one layer genuinely fails | More layers to configure, maintain, and keep consistent with each other |

---

## Code Samples

No dedicated code samples for this page.
