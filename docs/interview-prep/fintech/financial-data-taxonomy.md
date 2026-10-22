---
title: "Financial Data Taxonomy: MCC, ISO 4217 & ISO 20022 Codes"
---

# Financial Data Taxonomy: MCC, ISO 4217 & ISO 20022 Codes

Three separate coded vocabularies interviewers expect you to
distinguish cleanly, plus the same normalization problem that made
[Healthcare Terminology](../healthcare/healthcare-terminology.md)
matter — applied here to transactions instead of clinical facts.

## 1. "MCC, ISO 4217, ISO 20022 purpose codes — what does each actually cover?"

**Answer, the clean split:**

| System | Covers | Example |
|---|---|---|
| **MCC (Merchant Category Code)** | What *kind* of merchant a transaction was with | `5411` = Grocery Stores |
| **ISO 4217** | What *currency* an amount is denominated in | `USD`, `EUR`, `GBP` |
| **ISO 20022 purpose/reason codes** | *Why* a payment was made, or why it was returned | A specific code for "insufficient funds" vs. "invalid account" on a returned payment |

**The distinction interviewers actually probe:** these three classify
three genuinely independent things about the same transaction — what,
in what currency, and why — not three overlapping or competing
standards. A $50 grocery purchase in USD declined for insufficient
funds carries an MCC, a currency code, *and* a return-reason code
simultaneously, each answering a different question.

## 2. "Why does normalization matter here — why not just store whatever code the source system sent?"

**Answer:**

- Different source systems and banks code the same real-world fact
  differently — one institution's proprietary internal merchant
  categorization doesn't mean anything to a downstream analytics or
  compliance system expecting standard MCCs.
- Without normalization, a query like "find all transactions at
  restaurants" only finds transactions coded with *that specific
  system's* restaurant category — silently missing transactions from any
  source using a different internal scheme, the exact same silent gap
  already covered in
  [Healthcare Terminology §2](../healthcare/healthcare-terminology.md#2-why-does-terminology-normalization-matter-at-all-why-not-just-store-whatever-code-the-source-system-sent).
- This matters with real regulatory teeth here specifically: certain
  MCCs trigger mandatory extra scrutiny under AML (Anti-Money-Laundering)
  screening rules — a transaction miscoded (or left in a proprietary,
  unmapped scheme) can silently evade a compliance control built on the
  assumption that MCCs are standardized and reliable.

## 3. "How would you approach mapping a source system's local/proprietary transaction codes to a standard taxonomy at scale?"

**Answer, the realistic process:**

- **Exact/direct mapping first** — where the source system already
  carries a standard code alongside its own, use it directly.
- **Deterministic mapping table** for known, stable local codes — a
  maintained, versioned lookup covering the source system's actual code
  inventory, the exact same approach already established in
  [Healthcare Terminology §4](../healthcare/healthcare-terminology.md#4-how-would-you-approach-mapping-a-source-systems-localproprietary-codes-to-a-standard-terminology-at-scale).
- **Fuzzy/AI-assisted matching** as a fallback for free-text or unmapped
  entries — genuinely useful for suggesting a probable MCC or purpose
  code from a messy merchant description, but **never auto-accepted
  without review** in a codepath a compliance or fraud-screening
  decision could touch — the same "surface for review, never silently
  trust" rule already established there, with the consequence here being
  a compliance/regulatory miss rather than a clinical-safety one.
- **Track mapping provenance** — record which path (direct,
  deterministic table, reviewed fuzzy match) produced a given code, so a
  downstream consumer or an auditor can tell how much confidence to
  place in it — directly relevant here since a regulator reviewing a
  flagged (or missed) AML case will ask exactly this question.

| Pros | Cons / Trade-offs |
|---|---|
| Standard taxonomies make cross-institution analytics and reporting possible at all | Real mapping effort for every source system's own proprietary codes |
| MCC/purpose-code normalization is what makes automated compliance screening reliable | A missed or wrong mapping can silently defeat a regulatory control |
| AI-assisted mapping handles the free-text long tail faster than manual review alone | Never safe to auto-accept unreviewed in a compliance-relevant codepath |
| Provenance tracking gives auditors a real, inspectable trail | Adds metadata and process overhead to every mapped record |

---

## Code Samples

No dedicated code samples yet for this section.
