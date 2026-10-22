---
title: "Telecom Compliance: CALEA, Number Portability & Data Retention"
---

# Telecom Compliance: CALEA, Number Portability & Data Retention

The direct telecom parallel to
[HIPAA & PHI-Safe Engineering](../healthcare/hipaa-phi-safety.md) and
[PCI-DSS & Financial Data Safety Engineering](../fintech/pci-dss-and-financial-data-safety.md) —
the engineering-relevant slice of what carriers are legally required to
build and maintain, not the legal framework itself.

## 1. "What is CALEA, and what does it actually require an engineering team to build?"

**Answer:**

- **CALEA (Communications Assistance for Law Enforcement Act)** requires
  carriers to build their networks with the technical capability to
  provide **lawful intercept** — the ability to isolate and deliver a
  specific target's communications to law enforcement, under valid legal
  authorization, without the capability being generally accessible or
  usable for anything broader than that.
- The engineering-relevant distinction: this isn't "law enforcement can
  just read anyone's traffic" — it's a narrowly scoped, auditable
  capability, activated only against a specific, legally authorized
  target, which means the actual engineering requirement is building
  **precise targeting and strict access control** around the capability
  itself, not broad network-wide interception.
- This is the same **least-privilege, narrow-scope** principle already
  established repeatedly across this site's security content — the
  capability exists, but its *scope* and *who can activate it* are
  exactly what has to be engineered tightly, the same discipline as
  [Privileged Access Management](../../security/identity-security-zero-trust-and-pam.md#3-what-is-privileged-access-management-pam-and-why-does-it-need-to-be-a-distinct-discipline-from-regular-access-control)
  applied to a legally mandated capability instead of an internal admin
  account.

## 2. "How does number portability actually work across carriers, mechanically?"

**Answer:**

- When a subscriber switches carriers and keeps their number, that
  number's **routing record** — which carrier (and which specific
  network element within it) currently serves that number — has to be
  updated in a centralized registry that every other carrier's own
  signaling (see
  [SS7 & Diameter](ss7-and-diameter.md)) consults when routing a call or
  text to that number.
- This is the exact mechanism underneath the "home registry" step in the
  [SS7 call-routing diagram](ss7-and-diameter.md#how-a-call-actually-gets-routed-across-carriers-via-ss7)
  already covered — number portability is what makes that lookup return
  the subscriber's *new* carrier instead of their original one, and
  getting this update wrong or delayed means calls/texts to a ported
  number can fail or route to the wrong place during the transition
  window.

## 3. "What does CDR data retention actually require, and why does it matter for a data platform specifically?"

**Answer:**

- Regulations in most jurisdictions require carriers to retain
  [CDRs](telecom-data-taxonomy.md#1-whats-a-cdr-and-what-does-it-actually-record)
  for a defined minimum period — both for billing-dispute resolution
  and to remain available for a lawful request under CALEA-style
  authority.
- The practical engineering tension: this is exactly the kind of
  sensitive metadata named in
  [the Snowflake customer campaign breach case study](../../security/real-world-breach-case-studies.md) —
  AT&T's exposure was specifically call/text metadata covering a roughly
  six-month retained window. A data platform storing CDRs at retention
  scale is holding a large, long-lived, genuinely sensitive dataset by
  regulatory requirement, which makes the
  [access-control and shared-responsibility discipline](../../security/cloud-security-fundamentals.md#1-what-does-the-shared-responsibility-model-actually-mean-in-practice-beyond-the-diagram-every-provider-shows)
  already covered for cloud security a direct, concrete requirement
  here, not an abstract best practice — retention duration is mandated;
  how securely that retained data is actually held is squarely the
  platform team's responsibility.

## 4. "Design a pipeline step so CDR/subscriber metadata stays appropriately scoped, the same way PHI and cardholder data need to be."

**Answer, reusing the same pattern established twice already:**

1. **Minimize what actually needs broad access** — most analytics and
   product use cases need aggregated or pseudonymized patterns (call
   volume by region, usage trends), not raw, individually-identifiable
   CDRs — scope access to the minimum necessary, the same principle as
   [HIPAA §4](../healthcare/hipaa-phi-safety.md#4-design-a-pipeline-step-so-phi-never-reaches-a-non-compliant-environment-eg-a-general-purpose-llm-api-call)
   and
   [PCI-DSS §4](../fintech/pci-dss-and-financial-data-safety.md#4-design-a-pipeline-step-so-cardholder-data-never-reaches-a-non-pci-compliant-environment-say-an-llm-call-for-fraud-pattern-analysis).
2. **Scope the CALEA-capable interception path separately and narrowly**
   — the lawful-intercept capability itself should be an isolated,
   tightly access-controlled path, not something reachable from the
   same broad systems that run general analytics.
3. **Apply the retention window strictly in both directions** — data
   held past its required retention period is unnecessary risk with no
   corresponding legal requirement justifying it; data deleted before
   the mandated window is itself a compliance failure. Both directions
   need explicit, enforced handling, not an assumption that "keep it
   indefinitely" is the safe default.

| Pros | Cons / Trade-offs |
|---|---|
| CALEA's narrow-scope design keeps lawful intercept from becoming broad surveillance | Requires real engineering discipline to keep the capability genuinely narrow in practice |
| Number portability's registry keeps routing correct across carrier switches | A real transition window where routing can briefly fail or lag |
| Minimum-necessary access scoping reuses the exact pattern already proven for PHI/cardholder data | Requires the same discipline to actually enforce consistently across every analytics use case |
| A strict retention window avoids both regulatory and risk-exposure failure modes | Needs explicit lifecycle management, not a default-keep-everything posture |

---

## Code Samples

No dedicated code samples yet for this section.
