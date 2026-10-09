---
title: "Healthcare Terminology: SNOMED CT, LOINC, RxNorm"
---

# Healthcare Terminology: SNOMED CT, LOINC, RxNorm

Three separate standard code systems interviewers expect you to
distinguish cleanly, plus the normalization problem that makes them
matter for a data pipeline.

---

## 1. "What's the difference between SNOMED CT, LOINC, and RxNorm — what does each actually cover?"

**Answer, the clean split:**

| System | Covers | Example |
|---|---|---|
| **SNOMED CT** | Clinical findings, diagnoses, procedures, body structures — the broadest clinical vocabulary | `44054006` = Type 2 diabetes mellitus |
| **LOINC** | Laboratory and clinical *observations* — the identity of a test/measurement, not the result value itself | `4548-4` = Hemoglobin A1c |
| **RxNorm** | Medications — normalized drug names, ingredients, strengths, dose forms | `860975` = Metformin 500mg oral tablet |

**The distinction interviewers actually probe:** LOINC identifies
*what was measured* ("Hemoglobin A1c" as a concept); the *result*
("7.2%") is a separate value on the `Observation`, not part of the
LOINC code itself. Mixing these up — treating LOINC as if it encodes
results — is the tell that someone hasn't actually worked with lab data.

## 2. "Why does terminology normalization matter at all — why not just store whatever code the source system sent?"

**Answer:** Different source systems code the same clinical fact
differently — one EHR's local code for "penicillin allergy" is
meaningless to a payer's system or a second EHR unless it's mapped to a
standard code both sides understand. Without normalization, a query
like "find all patients with diabetes" only finds patients coded with
*that specific source system's* diabetes code — silently missing every
patient whose diabetes was recorded by a different system under a
different local code. Interoperability is the whole point of FHIR, and
interoperability without shared terminology is an illusion — two
systems can both speak valid FHIR JSON and still fail to actually
understand each other's data if the codes inside don't mean the same
thing.

## 3. "In FHIR terms, what's the difference between a code system, a value set, and a concept map?"

**Answer:**

- **Code system** — the full vocabulary itself (SNOMED CT in its
  entirety, LOINC in its entirety).
- **Value set** — a *constrained subset* of one or more code systems,
  scoped to a specific use — e.g. "the SNOMED CT codes valid for a
  `Condition.clinicalStatus` field" is a small value set, not the whole
  of SNOMED CT.
- **Concept map** — an explicit mapping *between* two code systems (or
  between a local/proprietary code system and a standard one) — this is
  the actual mechanism used to translate a source system's local code
  into a standard terminology during transformation.

## 4. "How would you approach mapping a source system's local/proprietary codes to a standard terminology at scale?"

**Answer, the realistic process, not the naive one:**

1. **Exact/direct mapping first** — if the source system already
   carries a standard code alongside its local one (common for LOINC in
   modern lab systems), use it directly; no mapping work needed.
2. **Deterministic mapping table** for known, stable local codes — a
   maintained concept map (a lookup table, effectively) covering the
   source system's actual code inventory, built once and versioned as
   the source system's codes change.
3. **Fuzzy/similarity matching** as a fallback for free-text or
   unmapped codes — genuinely a candidate for an LLM-assisted step
   (suggesting a probable SNOMED/LOINC match from a free-text
   description), but **never auto-accepted without validation** in a
   clinical context — surface it for human/rule-based review rather
   than silently trusting a probabilistic match, since a wrong
   terminology mapping in a clinical record is a patient-safety issue,
   not just a data-quality one.
4. **Track mapping provenance** — record *which* mapping path produced
   a given code (direct, deterministic table, or reviewed fuzzy match)
   on the resulting resource, so a downstream consumer (or an auditor)
   can tell how much confidence to place in it.

**This is exactly the kind of place a JD's "AI vs. deterministic
processing" judgment call shows up concretely** — deterministic mapping
tables for known, stable code inventories; AI-assisted suggestion (with
mandatory review) for the long tail of free-text/unmapped codes; never
silent, unreviewed AI output in the codepath a clinical decision could
ever touch.

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable terminology-mapping example added under `code_samples/`.
