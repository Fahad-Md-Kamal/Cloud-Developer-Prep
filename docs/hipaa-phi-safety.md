---
title: "HIPAA & PHI-Safe Engineering"
---

# HIPAA & PHI-Safe Engineering

The engineering-relevant slice of HIPAA — not the legal framework, the
practical patterns a data engineer is actually responsible for
implementing.

---

## 1. "What counts as PHI, precisely?"

**Answer:** Protected Health Information is any individually
identifiable health information — health data *plus* something that
ties it to a specific person. HIPAA's Safe Harbor method lists 18
specific identifier categories that make data identifiable, including
the obvious ones (name, SSN, MRN) and several people miss: **dates**
more specific than a year (birth date, admission date, discharge date),
**geographic subdivisions smaller than a state** (a zip code, in most
cases), and any other unique identifying number or characteristic.

**The part worth naming unprompted:** a dataset with names removed can
still be PHI — a birth date plus a zip code plus a rare diagnosis can be
enough to re-identify someone even with no name present at all.
Removing the obvious fields isn't the same as de-identifying the data.

## 2. "De-identification vs. anonymization vs. pseudonymization — what's the actual difference, and why does it matter for using an LLM on healthcare data?"

**Answer:**

- **De-identification** (HIPAA's specific term) — removing or
  generalizing the 18 identifier categories per Safe Harbor, *or* having
  a qualified statistician certify the re-identification risk is very
  small (the "Expert Determination" method). Properly de-identified data
  is no longer considered PHI under HIPAA.
- **Pseudonymization** — replacing identifiers with a consistent token
  (a stable but reversible mapping) — the data is *not* de-identified
  under HIPAA, since the mapping back to the real identity still exists
  somewhere; it reduces exposure but doesn't remove regulatory
  obligations.
- **Anonymization** — irreversible removal of identifying information,
  no mapping back exists at all, even in principle.

**Why this matters concretely:** sending data to an external LLM API
(a third-party service) is a data-sharing event — if the data is still
PHI (identifiable, or merely pseudonymized), that call needs a Business
Associate Agreement with the provider and falls under HIPAA's technical
safeguards. Properly de-identified data sent to the same API is a
categorically different, much lower-risk situation. This distinction —
not "did we mask the SSN" — is what actually determines whether an
AI-assisted pipeline step is compliant.

## 3. "How do you keep PHI out of logs and error messages, practically?"

**Answer:** The realistic failure mode isn't a deliberate leak — it's an
exception handler that logs a full record object, or a debug log
statement left in from development that dumps request payloads. Practical
patterns: structured logging with an explicit allowlist of loggable
fields (log the `patient_id`'s hash or an internal correlation ID, never
the raw record); redaction middleware/formatters that strip known PHI
field names before a log line is emitted, as a safety net rather than
the only line of defense; and treating "don't log the whole object" as
a code-review checklist item specifically for any code path handling
clinical or patient records.

## 4. "Design a pipeline step so PHI never reaches a non-compliant environment (e.g. a general-purpose LLM API call)."

**Answer, the pattern to describe:**

1. **De-identify or pseudonymize before the boundary** — strip/tokenize
   identifiers *before* the data leaves the compliant environment, not
   after, so the external call never receives raw PHI in the first
   place.
2. **Scope what actually needs to cross the boundary** — an LLM call
   for, say, "suggest a probable terminology mapping for this free-text
   diagnosis" needs the diagnosis text, not the patient's name or MRN
   alongside it. Send the minimum necessary field, not the whole record.
3. **Re-attach the identity after the response returns**, inside the
   compliant environment, using the same token/mapping used to
   de-identify going out.
4. **Prefer a provider with a signed BAA and documented data-handling
   guarantees** when PHI genuinely must cross the boundary in some form
   — this is a vendor/contract decision as much as an engineering one,
   worth naming as part of a complete answer.

**This is the concrete version of the JD's "AI-native but PHI-safe"
requirement** — the architecture pattern is de-identify-before-boundary,
scope-to-minimum-necessary, re-attach-after, not "just don't use AI on
healthcare data" (too restrictive to be useful) or "send everything,
trust the vendor" (not compliant).

## 5. "What are the three categories of HIPAA safeguards, and which one is actually your job as an engineer?"

**Answer:** HIPAA's Security Rule defines three categories:
**Administrative** (policies, training, access-review processes —
largely an organizational/compliance function), **Physical** (data
center security, device controls — largely an infrastructure/facilities
concern), and **Technical** (access controls, audit logs, encryption at
rest and in transit, automatic logoff) — this last category is squarely
an engineer's responsibility: authentication/authorization enforcement,
comprehensive audit logging of who accessed what PHI and when, and
encryption on every storage layer and every network hop the data
travels across.

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable PHI-redaction/logging example added under `code_samples/`.
