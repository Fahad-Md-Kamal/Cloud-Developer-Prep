---
title: "Energy Data Taxonomy: Meter Reads, Interval Data & Rate Schedules"
---

# Energy Data Taxonomy: Meter Reads, Interval Data & Rate Schedules

The same coded/structured-vocabulary normalization problem already
covered in
[Healthcare Terminology](../healthcare/healthcare-terminology.md),
[Financial Data Taxonomy](../fintech/financial-data-taxonomy.md), and
[Telecom Data Taxonomy](../telecom/telecom-data-taxonomy.md) — applied
to usage and billing data, where the central complication is that the
*meaning* of a raw number depends entirely on a rate schedule most
pipelines treat as an afterthought.

## 1. "What's the actual shape of interval usage data, and why isn't it just 'a number per hour'?"

**Answer:**

- A single interval read is more than a kilowatt-hour value — it
  carries a **reading type** (consumption vs. generation, relevant for a
  customer with solar panels feeding power back), a **direction**, a
  **unit**, and a **quality flag** (was this an actual meter reading, or
  an estimated value filled in because the real read was missing or
  failed validation).
- This is the direct energy-sector parallel to
  [LOINC identifying what was measured, separately from the result value itself](../healthcare/healthcare-terminology.md#1-whats-the-difference-between-snomed-ct-loinc-and-rxnorm-what-does-each-actually-cover) —
  the *kind* of reading and the *value* are genuinely separate pieces of
  information, and conflating them (treating every raw number as a
  straightforward, trustworthy consumption value regardless of its
  quality flag or direction) is the exact kind of mistake that reveals
  someone hasn't actually worked with real metering data.

## 2. "Why does a rate schedule matter so much for interpreting usage data correctly?"

**Answer:**

- The same kilowatt-hour value means a genuinely different cost
  depending on **when** it was consumed, under a **time-of-use** rate
  schedule — peak-hour usage can cost several times more per unit than
  off-peak usage on the exact same meter, under the exact same account.
- A pipeline that normalizes usage data but ignores which rate schedule
  applied to a given interval produces technically-correct consumption
  numbers that are still **unusable for any accurate cost or billing
  analysis** — the raw usage taxonomy (§1) and the rate-schedule context
  are both required together; neither alone answers "what did this
  actually cost."
- This mirrors the same lesson from
  [ISO 20022 purpose codes](../fintech/financial-data-taxonomy.md#1-mcc-iso-4217-iso-20022-purpose-codes-what-does-each-actually-cover) —
  classifying *what* happened and explaining *why it matters financially*
  are separate axes that both have to be captured, not collapsed into
  one field.

## 3. "What's the difference between a billed read and an interval/AMI read, and why does a pipeline need to handle both?"

**Answer:**

- A **billed read** is the traditional, lower-frequency reading used to
  generate an actual bill (historically monthly, from a human meter
  reader or an older automated meter) — the authoritative number a
  customer is actually charged against.
- An **interval/AMI read** (already covered in
  [Green Button & Energy Data APIs §3](green-button-and-energy-apis.md#3-what-does-the-actual-usage-data-look-like-and-why-does-interval-granularity-matter))
  is the much higher-resolution data smart meters report — useful for
  analytics, time-of-use insight, and demand response, but not
  necessarily the exact number a bill is calculated from, depending on
  the utility's own billing system design.
- A pipeline serving both billing-adjacent and analytics use cases needs
  to treat these as genuinely separate data streams with separate
  authority — reconciling "what the interval data shows" against "what
  the bill actually says" when they diverge is a real, recurring
  operational question, not an edge case to ignore.

## 4. "How would you approach normalizing meter/reading-type codes from different utility source systems at scale?"

**Answer:**

- The same layered approach established across every parallel track on
  this site: deterministic mapping first for known, stable source-system
  codes (a maintained lookup table), fuzzy/AI-assisted suggestion only
  for genuinely unmapped or free-text entries, **never auto-accepted
  without review** in a codepath feeding a billing or demand-response
  decision, and **provenance tracking** on every mapped value — the same
  "never trust unreviewed AI output in a consequential codepath" rule
  already established for
  [healthcare terminology mapping](../healthcare/healthcare-terminology.md#4-how-would-you-approach-mapping-a-source-systems-localproprietary-codes-to-a-standard-terminology-at-scale)
  and
  [financial transaction code mapping](../fintech/financial-data-taxonomy.md#3-how-would-you-approach-mapping-a-source-systems-localproprietary-transaction-codes-to-a-standard-taxonomy-at-scale),
  carrying over directly here with a billing-accuracy consequence in
  place of a clinical or compliance one.

| Pros | Cons / Trade-offs |
|---|---|
| Separating reading type/direction/quality from the raw value catches real data-quality issues | Requires every pipeline consumer to actually respect the quality flag, not just read the number |
| Rate-schedule-aware processing enables real cost/billing accuracy, not just consumption totals | Rate schedules themselves change over time and need their own maintained reference data |
| Treating billed and interval reads as separate authoritative streams avoids silent reconciliation errors | Real operational complexity when the two genuinely diverge and need to be reconciled |
| The same deterministic-first mapping discipline carries over cleanly from other verticals | Still needs real upkeep as utilities onboard new meter types and reading codes |

---

## Code Samples

No dedicated code samples yet for this section.
