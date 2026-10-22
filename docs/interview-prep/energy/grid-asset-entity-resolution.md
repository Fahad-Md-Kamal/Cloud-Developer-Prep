---
title: "Entity Resolution: Grid Assets, Service Points & Customer-Meter Matching"
---

# Entity Resolution: Grid Assets, Service Points & Customer-Meter Matching

The same record-linkage problem already covered in
[Patient Matching & MPI](../healthcare/patient-matching-mpi.md),
[KYC/AML Entity Resolution](../fintech/kyc-aml-entity-resolution.md),
and
[Subscriber Identity Resolution](../telecom/subscriber-identity-and-fraud-resolution.md) —
with its own distinct twist: the entity being resolved here is as often
a **physical asset** (a meter, a transformer, a feeder line) as it is a
person, and getting the physical topology wrong has a physical-world
consequence.

## 1. "What does 'matching a customer to their meter' actually involve, and why is it harder than it sounds?"

**Answer:**

- A customer's billing account, their physical service address, and the
  specific meter serial number actually installed at that address exist
  as separate records across separate systems (customer information
  system, billing system, the AMI head-end system managing the meters
  themselves) — resolving "which meter actually serves this customer's
  account" requires linking across all three.
- The same deterministic-vs-probabilistic matching trade-off already
  covered in
  [Patient Matching & MPI §2](../healthcare/patient-matching-mpi.md#2-explain-deterministic-vs-probabilistic-patient-matching)
  applies here too — a stable, correctly-maintained meter-to-account
  mapping is the deterministic case; address changes, meter swaps during
  maintenance, and new-construction service points without a clean
  historical record are where probabilistic matching or manual
  reconciliation becomes necessary.

## 2. "What's genuinely different here compared to matching a patient or a bank customer — what's grid topology?"

**Answer:**

- A patient or a bank customer is always a person (or, in fintech's
  case,
  [occasionally a legal entity](../fintech/kyc-aml-entity-resolution.md#2-whats-genuinely-different-about-entity-resolution-in-finance-vs-healthcare-whats-beneficial-ownership)).
  Here, a huge share of the entities being resolved are **physical grid
  assets** — which meter is connected to which transformer, which
  transformer is fed by which feeder line, which feeder traces back to
  which substation.
- This is a genuine **graph/topology** problem, the same shape as
  [beneficial ownership chains](../fintech/kyc-aml-entity-resolution.md#2-whats-genuinely-different-about-entity-resolution-in-finance-vs-healthcare-whats-beneficial-ownership)
  and
  [fraud-ring detection](../telecom/subscriber-identity-and-fraud-resolution.md#3-what-makes-fraud-ring-detection-a-genuinely-different-problem-from-matching-one-subscriber-to-themselves) —
  "which customers are actually affected if this specific transformer
  fails" is a multi-hop traversal query up the grid hierarchy, exactly
  the kind of query where
  [graph-based index-free adjacency](../../database/graph-databases-neo4j.md#2-give-a-concrete-example-where-a-join-heavy-query-becomes-painful-but-a-graph-traversal-doesnt)
  stays fast at scale where a chain of relational joins gets painfully
  slow.
- The practical stakes are also physical, not just informational: an
  incorrect topology record means an outage-management system genuinely
  doesn't know which customers are actually affected by a given piece of
  failed equipment, directly delaying real-world restoration.

## 3. "Why does the false-positive/false-negative trade-off matter here, and which direction does it point?"

**Answer:**

- Closer to healthcare's asymmetry than finance's: an incorrect
  customer-to-meter link (a false positive, in the sense of an
  incorrect match) can mean billing the wrong customer, or — more
  operationally serious — an outage-management system reporting a
  customer as affected (or unaffected) incorrectly during a real
  restoration event.
- As with
  [Patient Matching §4](../healthcare/patient-matching-mpi.md#4-why-does-the-false-positivefalse-negative-tradeoff-matter-more-here-than-in-typical-record-deduplication),
  the practical answer is to be conservative about auto-merging
  ambiguous topology/account links — flag genuinely uncertain
  connections for field verification or manual review rather than
  silently asserting a connection that might be wrong, since an
  incorrect assertion here can misdirect real crews during a real
  outage.

## 4. "How would you actually evaluate whether grid-topology and customer-meter matching data is accurate, on an ongoing basis?"

**Answer:**

- **Outage correlation** is a genuinely useful ongoing validation
  signal unique to this domain: when equipment actually fails, compare
  which customers the topology record predicts should be affected
  against which customers actually report an outage — a persistent
  mismatch is a strong, concrete signal the topology data itself has
  drifted from physical reality (equipment was replaced or rewired
  without the record being updated).
- This is a stronger, more grounded validation loop than a one-time
  accuracy audit, the same "track accuracy as an ongoing operational
  metric, not a point-in-time number" principle already established in
  [Patient Matching §5](../healthcare/patient-matching-mpi.md#5-how-would-you-evaluate-whether-a-matching-algorithm-is-actually-working-well) —
  here using a genuinely physical, real-world event (an actual outage)
  as the ground truth rather than a manually labeled sample.

| Pros | Cons / Trade-offs |
|---|---|
| Graph-based topology modeling scales to "who's affected by this failure" queries relational joins can't | Real infrastructure investment, same case as every other graph-shaped problem on this site |
| Outage correlation gives a genuinely grounded, ongoing accuracy signal | Only validates topology where an actual outage happens to occur |
| Conservative matching avoids misdirecting crews during a real restoration event | Leaves more ambiguous links requiring manual/field verification |
| Linking customer, billing, and AMI systems enables accurate billing and outage response together | Three separate systems of record to keep consistent, not one |

---

## Code Samples

No dedicated code samples yet for this section.
