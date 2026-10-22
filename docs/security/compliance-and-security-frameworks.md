---
title: "Compliance & Security Frameworks"
---

# Compliance & Security Frameworks

[AWS Organizations & Control Tower](../cloud-devops/aws-organizations-and-control-tower.md)
and [AWS Security & Compliance Services](../cloud-devops/aws-security-and-compliance-services.md)
already cover how AWS's own services help satisfy compliance
requirements. This page covers the frameworks themselves — what each
one actually audits, and the core distinction every one of them shares:
compliance certifies a **process**, not a product.

## 1. "What's actually being verified when a company says it's 'SOC 2 compliant'?"

**Answer:**

- **SOC 2** audits an organization against five **Trust Service
  Criteria**: security, availability, processing integrity,
  confidentiality, and privacy — not a specific technical
  implementation, but whether the organization's actual *processes and
  controls* genuinely satisfy each criterion, consistently.
- **Type I** certifies that the right controls are *designed*
  correctly, verified at a single point in time. **Type II** — the far
  more meaningful certification in practice — certifies that those
  controls were actually **operating effectively over a sustained
  period** (typically 6-12 months), verified by an auditor reviewing
  real evidence across that window, not just a policy document.
- The practical reason Type II matters more: a company can have a
  perfectly written security policy (satisfying Type I) while
  routinely failing to actually follow it day to day — Type II is what
  catches that gap, because it audits evidence of real, ongoing
  behavior, not just the existence of a documented intention.

## 2. "How is ISO 27001 different from SOC 2 — aren't they both just 'security compliance'?"

**Answer:**

- **ISO 27001** certifies an organization's **ISMS (Information
  Security Management System)** — the overall, systematic *process* an
  organization uses to identify, manage, and continuously improve its
  handling of information security risk, evaluated against an
  international standard.
- The key distinction from SOC 2: ISO 27001 is broader and more
  process-oriented — it's less about proving specific controls worked
  over a specific window (SOC 2 Type II's focus) and more about proving
  a genuinely systematic, risk-based *management process* exists and
  actually operates — identifying risks, choosing proportionate
  controls, and continuously reassessing, as an ongoing cycle rather
  than a fixed point-in-time or fixed-window audit.
- In practice, many organizations pursue both — SOC 2 is especially
  common for US-based SaaS companies selling to other US businesses;
  ISO 27001 carries more recognition internationally — and the controls
  satisfying one framework substantially overlap with satisfying the
  other, since both are ultimately auditing real security discipline,
  just through different lenses and scopes.

## 3. "GDPR and PCI-DSS — how are these different in kind from SOC 2/ISO 27001?"

**Answer:**

- **GDPR** is a legal requirement (EU regulation), not a voluntary
  certification — it mandates specific rights for individuals over their
  personal data (access, correction, deletion — "the right to be
  forgotten") and specific obligations on organizations handling that
  data (lawful basis for processing, breach notification within a fixed
  window, data minimization). Non-compliance carries real legal/financial
  penalty, not just a failed audit.
- **PCI-DSS** is an industry-mandated standard (from the payment card
  industry, not a government) specifically for anyone handling
  credit/debit card data — its requirements are narrower in *scope*
  (cardholder data specifically) but highly prescriptive in *detail*
  (network segmentation of cardholder data environments, specific
  encryption requirements, regular vulnerability scanning cadence).
- The common thread tying all four frameworks together, regardless of
  whether they're voluntary certifications (SOC 2, ISO 27001) or
  mandatory requirements (GDPR, PCI-DSS): every one of them is
  fundamentally auditing **process and discipline over time**, not
  certifying that a specific piece of software is secure — a compliant
  organization can still ship a vulnerable feature; compliance
  certifies that the *process* around how it handles risk, data, and
  incidents meets a defined bar, not that every line of code is
  flawless.

| Pros | Cons / Trade-offs |
|---|---|
| SOC 2 Type II verifies real, sustained operational behavior, not just written policy | A months-long audit window — slow to achieve, slow to demonstrate |
| ISO 27001's systematic ISMS approach drives genuinely continuous improvement | Broader and more process-heavy — real organizational overhead to maintain |
| GDPR gives individuals real, legally enforceable rights over their own data | Genuinely complex to implement correctly across a large, varied system |
| PCI-DSS's prescriptive detail leaves less ambiguity about what's actually required | Narrow scope (cardholder data) — doesn't cover an organization's security posture broadly |

---

## Code Samples

No dedicated code samples for this page.
