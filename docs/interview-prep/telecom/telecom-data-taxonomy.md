---
title: "Telecom Data Taxonomy: CDRs, MCC/MNC & Number Formats"
---

# Telecom Data Taxonomy: CDRs, MCC/MNC & Number Formats

The same coded-vocabulary normalization problem already covered in
[Healthcare Terminology](../healthcare/healthcare-terminology.md) and
[Financial Data Taxonomy](../fintech/financial-data-taxonomy.md) — with
one genuinely confusing wrinkle worth naming upfront: telecom reuses the
acronym **MCC** for something entirely unrelated to fintech's MCC.

## 1. "What's a CDR, and what does it actually record?"

**Answer:**

- A **Call Detail Record (CDR)** is a structured log entry generated
  for every call, SMS, or data session — who placed/received it, when,
  how long it lasted, which network elements it traversed, and how it
  should be billed.
- This is the record that both billing systems and the SS7/Diameter
  signaling covered in
  [Legacy Signaling](ss7-and-diameter.md) ultimately produce as a
  byproduct — the signaling sets up and routes the call in real time;
  the CDR is the durable record of what happened, generated once the
  session completes.
- CDRs are also exactly the kind of metadata (who contacted whom, when
  — not message content) referenced in
  [the Snowflake customer campaign breach case study](../../security/real-world-breach-case-studies.md) —
  AT&T's 2024 disclosure was specifically about this category of data,
  not call/message content itself.

## 2. "MCC and MNC — and why does this genuinely clash with a term already used in Fintech?"

**Answer, the disambiguation worth stating explicitly:**

- In telecom, **MCC means Mobile Country Code** — a 3-digit code
  identifying the country a mobile network belongs to (e.g., `310` for
  the US), paired with an **MNC (Mobile Network Code)** identifying the
  specific carrier within that country. Together, MCC+MNC uniquely
  identify a mobile network operator worldwide — the piece of
  information that lets one carrier's network recognize which other
  carrier a roaming subscriber belongs to.
- This is a **completely different thing** from fintech's **MCC
  (Merchant Category Code)** already covered in
  [Financial Data Taxonomy](../fintech/financial-data-taxonomy.md) —
  same three-letter acronym, two unrelated domains, two unrelated
  meanings. Worth naming this collision directly in an interview if it
  comes up — confusing the two is an easy, visible tell that someone is
  pattern-matching an acronym rather than actually understanding either
  domain.

## 3. "What's E.164, and why does phone number formatting actually matter for data quality?"

**Answer:**

- **E.164** is the international standard format for phone numbers — a
  leading `+`, country code, then the national number, with a defined
  maximum length — e.g. `+14155552671`.
- Real-world source systems store numbers in wildly inconsistent
  formats — with or without the country code, with local formatting
  punctuation, sometimes with leading zeros that mean different things
  in different countries. Without normalizing every number to E.164
  before matching or deduplicating, the same real subscriber can appear
  as several different "distinct" numbers across source systems — the
  same silent-data-quality-gap pattern already established for
  unnormalized terminology and transaction codes elsewhere on this site.

## 4. "How would you approach normalizing a source system's inconsistent number/network codes at scale?"

**Answer:**

- The same layered approach already established for
  [Healthcare Terminology §4](../healthcare/healthcare-terminology.md#4-how-would-you-approach-mapping-a-source-systems-localproprietary-codes-to-a-standard-terminology-at-scale)
  and
  [Financial Data Taxonomy §3](../fintech/financial-data-taxonomy.md#3-how-would-you-approach-mapping-a-source-systems-localproprietary-transaction-codes-to-a-standard-taxonomy-at-scale) —
  deterministic normalization first (a well-defined E.164 parsing/
  formatting library handles the overwhelming majority of real numbers
  correctly), a maintained MCC/MNC reference table (these change
  relatively rarely and are centrally published, making a direct lookup
  table the right tool rather than any fuzzy matching), and explicit
  handling for the genuine edge cases (ported numbers, numbers that
  don't cleanly parse) rather than silently dropping or mis-normalizing
  them.

| Pros | Cons / Trade-offs |
|---|---|
| CDRs are a rich, structured record of every real network event for billing and analytics | Also exactly the sensitive metadata real breaches (AT&T/Snowflake) have exposed |
| MCC+MNC uniquely and reliably identify any mobile network worldwide | The acronym collision with fintech's MCC is a genuine, easy mistake to make |
| E.164 normalization makes cross-system subscriber matching reliable | Real-world source data is messy enough that edge cases still need explicit handling |
| A maintained MCC/MNC lookup table is simple and reliable, not fuzzy-matching-dependent | Still needs upkeep as new networks and codes are published |

---

## Code Samples

No dedicated code samples yet for this section.
