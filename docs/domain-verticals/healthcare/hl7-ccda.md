---
title: "HL7 v2.x & C-CDA"
---

# HL7 v2.x & C-CDA

The legacy messaging/document standards most real transformation
pipelines actually ingest from — and why turning them into FHIR is
genuinely hard, not just a format conversion.

---

## 1. "What does an HL7 v2 message actually look like, structurally?"

```
MSH|^~\&|EHR|HOSPITAL|LAB|LABCORP|20260923120000||ADT^A01|MSG001|P|2.5
PID|1||MRN00123^^^HOSPITAL^MR||DOE^JANE||19850314|F
PV1|1|I|WARD1^101^A
```

**Answer:** Pipe-delimited **segments** (`MSH`, `PID`, `PV1` —
three-letter codes with defined meanings: Message Header, Patient
Identification, Patient Visit), each made of `|`-separated **fields**,
which can further split into `^`-separated **components**. `MSH^~\&`
literally declares the delimiters the rest of the message uses. An
`ADT^A01` message type means "Admit/Discharge/Transfer, Admit a
patient" — the message type plus trigger event determines which
segments are expected and in what order.

**Where this actually shows up:** most hospital EHR interfaces still
send HL7 v2 for real-time events (admit, discharge, lab result
available, order placed) — it predates FHIR by decades and is far from
retired. A healthcare data platform ingesting from real EHRs is
ingesting HL7 v2 whether or not the target format is FHIR.

## 2. "What is C-CDA, and how is it different from HL7 v2 and FHIR?"

**Answer:** C-CDA (Consolidated Clinical Document Architecture) is an
XML-based **document** standard — a full clinical document (a discharge
summary, a continuity-of-care document) with human-readable narrative
text *and* structured, coded data side by side, wrapped in a defined
XML schema (itself based on HL7's CDA standard). Where HL7 v2 is a
real-time event message and FHIR is a set of discrete addressable
resources, C-CDA is a whole document meant to be both machine-processed
and human-readable as-is (a clinician can open a C-CDA and read it like
a report).

## 3. "Walk me through the general shape of a C-CDA-to-FHIR transformation."

**Answer:** A C-CDA document is organized into **sections** (Problems,
Medications, Allergies, Results, each with a defined template ID) —
each section maps to one or more FHIR resource types. Problems section
→ `Condition` resources; Medications section → `MedicationStatement`/
`MedicationRequest`; Results section → `Observation` resources;
demographics in the header → `Patient`. The transformation walks each
section, extracts the structured entries (C-CDA nests codes and values
inside verbose XML templates), and maps them into the corresponding
FHIR resources, tying them together with references back to the
`Patient` and the source `Encounter`.

**The actual hard part, and the thing worth naming unprompted:** C-CDA
allows a huge amount of structural variation between EHR vendors for
representing "the same" clinical fact — two systems' C-CDA output for
an identical diagnosis can differ meaningfully in which template
variant they used, which coding system they picked, or whether a field
is coded at all versus left as free text. **Template conformance
varies by vendor in practice, even when both claim standard
compliance** — a transformation pipeline has to handle real-world
variation, not just the spec's happy path.

## 4. "What kinds of data-quality problems come up specifically in this kind of transformation, that don't come up in typical ETL?"

**Answer, the ones worth naming:**

- **Free text where structured data should be** — a source system
  recording "penicillin allergy" as narrative text in a field that's
  supposed to carry a coded `AllergyIntolerance`, because whoever
  entered it skipped the coded picker.
- **Missing or non-standard terminology codes** — a lab result present
  with a local, proprietary code instead of (or alongside) a LOINC code,
  requiring a terminology mapping step (see
  [Healthcare Terminology](healthcare-terminology.md)) before the data
  is actually usable across systems.
- **Duplicate patients across source systems** — the same person
  appearing under different local MRNs from different source systems,
  needing patient matching (see
  [Patient Matching & MPI](patient-matching-mpi.md)) before merging
  their clinical data safely.
- **Vendor-specific C-CDA template variation** (§3) — the same clinical
  fact structured differently depending on which EHR generated the
  document.

**The framing to lead with in an interview:** this isn't "parse XML,
map to JSON" — the format conversion is the easy 20%. The hard 80% is
data quality and semantic normalization once the structural mapping is
done.

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable HL7 v2 parsing or C-CDA transformation example added under
`code_samples/`.
