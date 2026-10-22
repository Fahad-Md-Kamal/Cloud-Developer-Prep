---
title: "Entity Resolution: KYC, AML & Beneficial Ownership"
---

# Entity Resolution: KYC, AML & Beneficial Ownership

The same record-linkage problem already covered in
[Patient Matching & MPI](../healthcare/patient-matching-mpi.md), applied
to customer identity instead of patient identity — with one genuinely
different complication healthcare doesn't have: the entity being
identified isn't always a person at all.

## 1. "What's KYC, and what matching problem does it actually involve?"

**Answer:**

- **KYC (Know Your Customer)** means verifying and maintaining one
  durable identity per real customer, linked across every account,
  transaction, and screening event involving them — the same "resolve
  fragmented identity across systems" problem an MPI solves for
  patients, except the trigger here is regulatory: **AML
  (Anti-Money-Laundering)** law requires it, not a patient-safety
  concern.
- The mechanics of resolving that identity — deterministic matching on
  exact fields vs. probabilistic scoring across imperfect ones — are the
  same ones already covered in
  [Patient Matching & MPI §2](../healthcare/patient-matching-mpi.md#2-explain-deterministic-vs-probabilistic-patient-matching),
  applied here to name, date of birth, national ID/SSN, and address
  instead of clinical identifiers.

## 2. "What's genuinely different about entity resolution in finance vs. healthcare — what's beneficial ownership?"

**Answer:**

- A patient is always an individual. A **bank account** is not always
  owned by one — it can be owned by a legal entity (an LLC, a trust, a
  shell company), and AML regulation requires identifying the actual
  human **beneficial owners** standing behind that entity.
- This is where the problem stops being pure record linkage and becomes
  a genuine **graph** problem: a shell company can itself be owned by
  another shell company, which can be owned by another — resolving "who
  actually controls this account" means traversing an ownership chain,
  potentially several layers deep, not matching one flat record to
  another.
- This is a direct, practical application of
  [Graph Databases §2](../../database/graph-databases-neo4j.md#2-give-a-concrete-example-where-a-join-heavy-query-becomes-painful-but-a-graph-traversal-doesnt) —
  "who ultimately owns this account" is structurally the same multi-hop
  traversal problem as "friend of a friend of a friend," and a
  relational join chained several layers deep to answer it gets
  painfully slow at exactly the scale real ownership-chain investigation
  needs.

## 3. "Why does the false-positive/false-negative trade-off matter here, and is the asymmetry the same as in healthcare?"

**Answer:**

- [Patient Matching §4](../healthcare/patient-matching-mpi.md#4-why-does-the-false-positivefalse-negative-tradeoff-matter-more-here-than-in-typical-record-deduplication)
  established that a false *positive* (an incorrect merge) is the worse
  failure mode in healthcare, because it mixes one patient's clinical
  history into another's chart.
- In **sanctions screening** specifically, the asymmetry genuinely
  points the other way: a false *negative* — failing to match a customer
  against an entry on a sanctions list (OFAC and similar) — is the worse
  failure mode here, carrying real compliance and legal risk, up to
  potential liability for facilitating a transaction with a sanctioned
  party.
- This is worth stating explicitly as a real, defensible point of
  contrast rather than assuming the same conclusion transfers
  automatically — the *mechanism* (deterministic vs. probabilistic
  matching, a precision/recall trade-off) is identical across both
  domains; which direction the trade-off should actually be tuned
  depends entirely on which failure mode carries the worse real-world
  consequence in that specific context.

## 4. "Given that asymmetry, how would you actually evaluate and tune a KYC/sanctions-matching system?"

**Answer:**

- Tune for **high recall** on sanctions screening specifically — catch
  every plausible match, even at a real precision cost (more
  false-positive alerts to review) — the opposite tuning direction from
  [Patient Matching §5](../healthcare/patient-matching-mpi.md#5-how-would-you-evaluate-whether-a-matching-algorithm-is-actually-working-well)'s
  "optimize for precision" conclusion, for exactly the reason named in
  §3.
- Route matches above a lower confidence threshold to a **human
  compliance review queue** as an alert, not an automatic block — a
  flagged-but-unconfirmed match shouldn't silently freeze a legitimate
  customer's account, but it also can't be silently dismissed.
- Track **alert volume and review-queue throughput** as an ongoing
  operational metric, not a one-time accuracy number — the same
  reasoning as patient matching's production-drift concern, since a
  change in customer-data quality or a new sanctions list update can
  shift match rates in ways a point-in-time validation won't catch.

| Pros | Cons / Trade-offs |
|---|---|
| High-recall sanctions screening catches the matches that actually carry legal risk | Generates more false-positive alerts for human review to work through |
| Graph-based ownership-chain traversal scales to multi-layer shell structures | Real infrastructure investment — a relational-only system hits this wall hard |
| A human review queue avoids auto-blocking legitimate customers on a borderline match | Review capacity itself becomes an operational bottleneck at volume |
| Tuning direction is explicit and defensible, not copied blindly from another domain | Requires genuinely understanding which failure mode is actually worse in context |

---

## Code Samples

No dedicated code samples yet for this section.
