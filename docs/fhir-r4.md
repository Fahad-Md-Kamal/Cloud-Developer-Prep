---
title: "FHIR R4"
---

# FHIR R4

FHIR (Fast Healthcare Interoperability Resources) questions — the
resource model, how validation and profiling work, and where
transformation pipelines actually get complicated.

---

## 1. "What is FHIR, structurally? What's a 'resource'?"

**Answer:** FHIR models healthcare data as **resources** — discrete,
independently-addressable units like `Patient`, `Observation`,
`Condition`, `Encounter`, `MedicationRequest`. Each resource type has a
defined structure (a base specification), is identified by a stable
`id`, and can be created, read, updated, and searched via a standard
REST API (`GET /Patient/123`, `POST /Observation`). Roughly 150 resource
types exist in R4, covering clinical, administrative, and financial
healthcare data.

```json
{
  "resourceType": "Patient",
  "id": "example-123",
  "identifier": [
    { "system": "http://hospital.org/mrn", "value": "MRN-00123" }
  ],
  "name": [{ "family": "Doe", "given": ["Jane"] }],
  "birthDate": "1985-03-14",
  "gender": "female"
}
```

**Where this actually shows up in a transformation pipeline:** mapping
a source system's flat patient record (from an EHR extract, an HL7 v2
message, a C-CDA document) into this resource shape — the hard part is
almost never the JSON structure itself, it's getting the *semantics*
right (which source field maps to `identifier` vs a plain custom
extension, what `system` URI correctly identifies where an ID came
from).

## 2. "Explain a FHIR Bundle."

**Answer:** A `Bundle` is a container for multiple resources sent or
received together — used for search results (`type: searchset`),
grouped transactional writes (`type: transaction`, all-or-nothing), or a
document (`type: document`, e.g. a full clinical document composed of a
`Composition` plus everything it references). A C-CDA-to-FHIR
transformation typically produces a `Bundle` containing a `Patient`,
several `Condition`/`Observation`/`MedicationStatement` resources, and
the references tying them together — not one resource in isolation.

## 3. "What's a Profile, and why would you need one beyond the base resource?"

**Answer:** The base FHIR `Patient` resource is deliberately generic —
almost every field is optional, to accommodate every possible use case
globally. A **Profile** constrains a base resource for a specific
context: marks certain fields as required, restricts allowed values (a
`ValueSet` binding), or adds extensions for data the base resource
doesn't model. **US Core** is the most common profile set in US
healthcare interoperability work — it defines, for example, that a
US Core Patient *must* have a name and *should* have a race/ethnicity
extension, neither of which the base `Patient` resource requires.

**Likely follow-up — "how does this affect a transformation
pipeline?"** Producing "valid FHIR" and producing "valid *US Core*
FHIR" are different bars — code that generates a technically-correct
base `Patient` can still fail US Core conformance validation if it's
missing a required extension. Validate against the actual target
profile, not just the base spec.

## 4. "How does FHIR validation actually work?"

**Answer:** A **StructureDefinition** (the machine-readable form of a
profile) defines cardinality (`0..1`, `1..*`), required fields, and
value set bindings for each element. A validator (the HL7 reference
validator, or a Databricks/Spark-integrated equivalent for pipeline use)
checks a resource instance against a StructureDefinition and reports
violations. In a production pipeline, this needs to run **as part of
the pipeline itself**, not as a manual post-hoc check — a common pattern
is validating each transformed resource before it's written to the
Gold/output layer, routing failures to a quarantine location rather
than either silently dropping bad data or letting it through unvalidated.

## 5. "How do references between resources work, and what goes wrong with them in practice?"

```json
{
  "resourceType": "Observation",
  "subject": { "reference": "Patient/example-123" },
  "encounter": { "reference": "Encounter/enc-456" }
}
```

**Answer:** Resources reference each other by `resourceType/id` (or a
full URL). The practical problem in a transformation pipeline: a
resource can reference another resource that doesn't exist yet, or ever
(a source record referencing a patient ID that was never actually
ingested, or that failed validation and got quarantined). A production
pipeline needs an explicit policy for this — either the whole
referencing resource fails together with what it depends on, or it's
allowed through with a dangling reference and flagged, but "silently
succeed with a reference to nothing" is the failure mode to design
against.

## 6. "US Core, USCDI, HL7 v2 — how do all these relate to FHIR R4?"

**Answer, disambiguated:**

- **FHIR R4** — the base specification (the resource model, the REST
  API, the JSON/XML formats).
- **US Core** — a *profile* of FHIR R4 for the US market, defining
  minimum required data elements per resource.
- **USCDI** (US Core Data for Interoperability) — a *policy-level* data
  set defined by ONC (a US regulatory body), specifying the classes of
  data that must be interoperable (e.g. "Problems," "Medications," "Lab
  Results") — US Core is largely the *FHIR implementation* of what
  USCDI requires at a data-element level.
- **HL7 v2.x** — an older (1980s-era), still heavily-used messaging
  standard, structurally nothing like FHIR (pipe-delimited segments, not
  resources/JSON) — most legacy EHR interfaces still speak HL7 v2, which
  is exactly why v2-to-FHIR transformation is its own substantial body
  of work (see [HL7 v2 & C-CDA](hl7-ccda.md)).

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable FHIR validation/transformation example added under
`code_samples/`.
