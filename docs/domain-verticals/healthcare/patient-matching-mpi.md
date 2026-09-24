---
title: "Patient Matching & MPI"
---

# Patient Matching & MPI

Record linkage in a healthcare context — where the stakes and failure
modes are genuinely different from typical deduplication work.

---

## 1. "What's an MPI, and what problem does it solve?"

**Answer:** A Master Patient Index maintains one durable identity per
real-world patient, linked across every source system that has a record
for them — a hospital EHR, a lab system, a payer's claims system each
have their own local patient ID for the same person, with no shared
identifier connecting them. The MPI is what resolves "MRN-00123 in
System A" and "PT-9981 in System B" to the same underlying person, so a
platform can assemble one coherent longitudinal record instead of
several disconnected fragments.

## 2. "Explain deterministic vs. probabilistic patient matching."

**Answer:** **Deterministic matching** requires an exact match on a
defined set of fields (e.g. SSN + date of birth + last name, exact
string match) — simple, explainable, but brittle: a typo, a nickname
("Bill" vs "William"), or a missing SSN produces a false *non*-match
even when it's genuinely the same person. **Probabilistic matching**
scores similarity across multiple fields (name, DOB, address, phone,
partial SSN) and produces a *confidence score* rather than a binary
yes/no — commonly using something like the Fellegi-Sunter model, which
weights each field by how discriminating a match on that field actually
is (a DOB match is more informative than a common last-name match).
Production systems typically use both: deterministic for
high-confidence exact matches, probabilistic scoring with a threshold
for everything else, and a manual review queue for scores landing in an
ambiguous middle band.

## 3. "What fields are actually used for patient matching, and why isn't 'just use SSN' a complete answer?"

**Answer:** Typical fields: name (and known aliases/maiden names), date
of birth, sex, address, phone, and identifiers (SSN, MRN, driver's
license) where available. SSN alone isn't sufficient because it's
frequently missing, sometimes shared (in specific populations),
occasionally wrong from a data-entry error, and — the practical reason
— many source systems simply don't collect or transmit it at all.
Effective matching needs to work with the fields that are actually
reliably present, which in practice means composite matching across
several imperfect fields rather than relying on one "perfect"
identifier that doesn't reliably exist.

## 4. "Why does the false-positive/false-negative tradeoff matter more here than in typical record deduplication?"

**Answer:** A **false positive** (incorrectly merging two different
people into one identity) mixes one patient's clinical history into
another's record — a direct patient-safety risk: wrong allergy history,
wrong medication list, wrong diagnosis showing up on the wrong person's
chart. A **false negative** (failing to link records that are actually
the same person) leaves a fragmented, incomplete view of one patient's
history across systems — a real problem, but a fundamentally safer
failure mode than a false merge, since nothing incorrect is being
asserted, just something incomplete.

**The answer this is building toward:** given that asymmetry, MPI
systems are typically tuned to be conservative — a bias toward
under-merging (leaving ambiguous cases unlinked or flagged for manual
review) over aggressively auto-merging borderline matches, because the
cost of a false positive is categorically worse than the cost of a
false negative in this domain.

## 5. "How would you evaluate whether a matching algorithm is actually working well?"

**Answer:** Precision and recall against a labeled gold-standard set
(a manually-reviewed sample of known true/false matches) — but frame
the target asymmetrically given §4: optimize for very high precision
(minimize false merges) even at some recall cost, and route the
resulting lower-confidence non-matches to a review queue rather than
silently dropping them as "not a match." Track match-rate and
review-queue volume over time as an operational metric, not just a
one-time accuracy number — a source system change (a new EHR onboarded,
a data-quality regression upstream) can silently shift match rates in
production long after the algorithm itself was validated.

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable probabilistic-matching example added under `code_samples/`.
