---
title: "JD: Intellias — Staff Healthcare Data Engineer"
---

# JD: Intellias — Staff Healthcare Data Engineer

**Logged:** 2026-09-23 · **Level:** Staff IC · **Domain:** Healthcare
interoperability / FHIR data platform

Notes only at this stage — extracting keypoints for later cross-reference
against other JDs, not yet building study content from this. See
[Gap vs. current profile](#gap-vs-current-profile) before treating this
as a near-term realistic target.

## The role in one paragraph

Staff-level IC setting technical direction for a FHIR-based healthcare
data platform: ingesting from EHRs, payer systems, and reference
datasets, transforming heterogeneous data into standards-conformant
FHIR, and owning data quality (dedup, patient/record linking, terminology
normalization) at production scale. Explicitly "AI-native" — coding
agents (Claude Code named directly) are part of the expected engineering
workflow, with judgment required on AI vs. deterministic approaches.

## Core tech stack

| Area | Named technologies |
|---|---|
| Language | Python |
| Distributed processing | Apache Spark / PySpark (partitioning, perf tuning, memory tuning) |
| Lakehouse | Databricks, Delta Lake |
| Data | SQL, CDC, incremental/delta processing, schema evolution, batch + streaming |
| Healthcare interop | FHIR R4 (resources, profiles, Bundles, validation), HL7 v2.x, C-CDA→FHIR |
| Healthcare data models | US Core, USCDI, clinical/claims/coverage/eligibility |
| Terminology standards | SNOMED CT, LOINC, RxNorm |
| Compliance | HIPAA, PHI-safe engineering |
| AI-native dev | Claude Code / coding agents integrated into the dev lifecycle |
| Ops | Git, CI/CD, automated testing, observability |

## Required skills, bucketed

**Distributed data engineering**
- 8+ years data engineering / healthcare data / interoperability
- Spark/PySpark at scale — partitioning, performance optimization, memory tuning, distributed processing
- Databricks/Delta Lake or comparable lakehouse platform
- Large-scale ETL/ELT: CDC, incremental/delta processing, idempotency, schema evolution, batch/streaming
- Diagnosing and eliminating performance/scalability bottlenecks in distributed systems

**Healthcare interoperability (the domain-specific core)**
- FHIR R4 hands-on: resources, profiles, Bundles, validation, large-scale transformation
- US Core, USCDI, HL7 v2.x, C-CDA-to-FHIR transformation patterns
- Terminology: SNOMED CT, LOINC, RxNorm
- Clinical, claims, coverage, eligibility data models
- Data quality: deduplication, record/patient linking, terminology normalization, validation

**Staff-level scope**
- Technical direction across ingestion/transformation/validation/normalization/delivery
- End-to-end architecture ownership for large-scale distributed pipelines
- Establishing reusable frameworks/standards adopted by other engineers
- Mentoring Senior/Middle engineers via design review, pairing
- Driving ambiguous problems from investigation through production

**AI-native engineering (explicitly called out, unusual to see this explicit)**
- Practical use of AI coding agents (Claude Code named specifically) as part of the dev lifecycle
- Engineering guardrails for AI-assisted development: correct, tested, secure, observable, PHI-safe
- Judgment on when deterministic processing beats AI/LLM approaches (correctness/cost/performance/PHI safety)

**General**
- Strong SQL, data modeling, schema evolution
- Git, CI/CD, automated testing, observability, production ops
- Professional English for direct US stakeholder collaboration

## Nice to have

- Master Patient Index (MPI), patient matching, identity resolution, large-scale record linkage
- Payer data exchange: CARIN Blue Button, Da Vinci implementation guides
- Pharmacy/lab specialized datasets
- ICD-10, CPT, CVX and other clinical code systems
- 21st Century Cures Act, ONC certification, CMS Interoperability Rule
- Building LLM/agent-based capabilities specifically for clinical data extraction/normalization/terminology mapping
- Designing reusable AI skills/agentic workflows adopted across teams
- OSS contributions to healthcare/FHIR/HL7 communities

## Gap vs. current profile

Honest read against the current CV (6+ years Python/Django/DRF/FastAPI,
SQL, AWS working knowledge, PostGIS/geospatial, RAG/LangChain/Azure
OpenAI, some React/Vue):

| Requirement | Current standing |
|---|---|
| Python, SQL, production data engineering | ✅ Strong overlap |
| RAG/LLM engineering experience | ✅ Directly relevant to the "AI-native" angle — genuine differentiator |
| Apache Spark/PySpark at scale | ❌ Not on the CV at all |
| Databricks/Delta Lake | ❌ Not on the CV at all |
| FHIR R4 / HL7 / C-CDA | ❌ No healthcare interoperability experience |
| SNOMED CT / LOINC / RxNorm | ❌ No healthcare terminology experience |
| MPI / patient matching | ❌ Not applicable from current background |
| HIPAA / PHI-safe engineering | ❌ Not evidenced |
| Staff-level scope (8+ yrs, cross-team technical direction) | ⚠️ 6+ years total; Lead Developer on current project shows some of this scope, but not at the "sets direction across multiple teams" level this JD implies |

**Bottom line:** this is a large gap, concentrated entirely in the
healthcare-domain and big-data-at-scale axes — not a "brush up for the
interview" gap like AWS services was for the BJIT client role. Spark/
Databricks and FHIR/HL7/terminology are each substantial standalone
domains, not something to crash-review in a weekend. Worth treating as
a longer-term target (if pursued at all) rather than an active
application, unless there's healthcare/Spark background not reflected
in the current CV.

## Topics to add to prep, if pursued

Not building these out now — flagging what a future prep track would
need:

- Apache Spark/PySpark fundamentals and performance tuning
- Databricks + Delta Lake (CDC, schema evolution, incremental processing)
- FHIR R4 basics: resource model, profiles, Bundles
- HL7 v2.x and C-CDA, and the shape of C-CDA→FHIR transformation
- Core terminology systems: SNOMED CT, LOINC, RxNorm (what each covers, not memorization)
- Patient/record matching and MPI concepts
- HIPAA / PHI-safe engineering practices
