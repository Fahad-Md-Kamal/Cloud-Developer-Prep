---
title: "SMART on FHIR & Bulk Data Export"
---

# SMART on FHIR & Bulk Data Export

[FHIR R4](fhir-r4.md) defines the resource model and REST API — it says
nothing about how an app actually proves it's allowed to see a given
patient's data in the first place. SMART on FHIR is the authorization
layer that sits on top, and it's the piece that makes FHIR real apps
(an app launched from inside Epic, a patient-facing mobile app) actually
possible rather than just a data format.

## 1. "Why does a FHIR server need a separate authorization standard at all — isn't OAuth2 already enough?"

**Answer:**

- Plain OAuth2 defines the mechanics of getting a scoped access token —
  it says nothing about **healthcare-specific context**: which patient
  is this app actually looking at, which encounter, launched from where.
- SMART on FHIR is a specific **profile** of OAuth2 and OpenID Connect —
  the same "constrain a general standard for one specific context"
  pattern already covered for
  [FHIR Profiles](fhir-r4.md#3-whats-a-profile-and-why-would-you-need-one-beyond-the-base-resource) —
  defining exactly which scopes, launch parameters, and context exist
  specifically for a clinical app requesting access to clinical data.
- Without this layer, every EHR vendor would need its own bespoke
  authorization scheme — SMART on FHIR is what lets one app be written
  once and actually launch correctly inside Epic, Cerner, or any other
  SMART-compliant EHR, the same interoperability goal FHIR itself
  already serves for data, applied here to authorization.

## The SMART Launch Sequence

<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of a SMART on FHIR app launch: the app redirects to the EHR's authorization server, the clinician approves access, an authorization code is returned and exchanged for a scoped access token, which the app then uses to call the FHIR API" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="440" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<rect x="40" y="40" width="190" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="135" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">SMART App</text>
<rect x="670" y="40" width="190" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="765" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">EHR Authorization Server</text>
<line x1="230" y1="70" x2="670" y2="70" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.04;0.08;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#2f6fb3" cy="70"><animate attributeName="cx" values="230;670" keyTimes="0;1" dur="2.2s" begin="0.4s;18.4s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" dur="2.2s" begin="0.4s;18.4s" repeatCount="indefinite"></animate></circle>
<rect x="340" y="140" width="220" height="60" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="450" y="166" font-size="13" font-weight="600" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate>Clinician logs in, approves</text>
<text x="450" y="184" font-size="12" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate>the requested scope &amp; patient context</text>
<line x1="670" y1="90" x2="230" y2="90" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.3;0.34;0.5;0.54;1" dur="18s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#b5831f" cy="90"><animate attributeName="cx" values="670;230" keyTimes="0;1" dur="2.2s" begin="6.3s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" dur="2.2s" begin="6.3s" repeatCount="indefinite"></animate></circle>
<rect x="340" y="240" width="220" height="60" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.52;0.56;0.74;0.78;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="450" y="266" font-size="13" font-weight="600" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.52;0.56;0.74;0.78;1" dur="18s" repeatCount="indefinite"></animate>App exchanges the code</text>
<text x="450" y="284" font-size="12" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.52;0.56;0.74;0.78;1" dur="18s" repeatCount="indefinite"></animate>for a scoped access token</text>
<rect x="340" y="340" width="220" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.78;0.82;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="450" y="366" font-size="13" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.78;0.82;1" dur="18s" repeatCount="indefinite"></animate>App calls the FHIR API</text>
<text x="450" y="384" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.78;0.82;1" dur="18s" repeatCount="indefinite"></animate>with the token, scoped to what was approved</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.22;0.26;1" dur="18s" repeatCount="indefinite"></animate>The app redirects to the authorization server, requesting a specific scope.</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.26;0.3;0.48;0.52;1" dur="18s" repeatCount="indefinite"></animate>An authorization code is returned to the app — not a usable token yet.</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.82;0.86;1" dur="18s" repeatCount="indefinite"></animate>Every subsequent FHIR call carries that token — scoped to exactly what was approved.</text>
</svg>

## 2. "Walk through standalone launch vs. EHR launch — why does it matter which one an app uses?"

**Answer:**

- **Standalone launch** — the app is opened directly (a patient opening
  a mobile app on their own phone), with no pre-existing clinical
  context. The user authenticates and picks/confirms which patient
  record they're accessing as part of the authorization flow itself.
- **EHR launch** — the app is launched *from inside* the EHR (a
  clinician clicking an app icon within their existing Epic/Cerner
  session). The EHR passes a special `launch` parameter carrying the
  current clinical context (which patient, which encounter is already
  open) — the app doesn't need to ask "which patient" at all, since it's
  already implied by where the clinician was when they launched it.
- This distinction matters because it changes what the app can assume:
  an EHR-launched app can trust the context it was handed; a standalone
  app has to establish that context itself as part of its own
  authorization and user-identification flow.

## 3. "What's the difference between `patient/*.read`, `user/*.read`, and `system/*.read` scopes?"

**Answer:**

- **`patient/*.read`** — the app acts on behalf of a specific patient,
  scoped to exactly that patient's own data — the pattern for a
  patient-facing app.
- **`user/*.read`** — the app acts on behalf of an authenticated
  clinical user (a doctor, a nurse), scoped to whatever that user is
  themselves authorized to see across potentially many patients — the
  pattern for a provider-facing clinical app.
- **`system/*.read`** — no human user in the flow at all — a backend
  service authenticating directly, typically via a signed JWT client
  assertion (the app proves its own identity cryptographically, the
  same [digital-signature trust mechanism](../../security/cryptography-fundamentals.md#4-whats-a-digital-signature-and-how-is-it-different-from-encryption)
  covered in Cyber Security, applied here to app-to-app authentication
  instead of a user login) rather than a human ever approving anything
  interactively. This is the scope used for the backend, unattended
  services that consume Bulk Data Export (§4).

## 4. "What is Bulk Data Export, and why is it architected completely differently from a normal FHIR search?"

```http
GET [fhir-base]/Patient/$export
Accept: application/fhir+json
Prefer: respond-async
```

**Answer:**

- Ordinary FHIR search (`GET /Patient?name=Doe`) is built for
  **interactive, single-patient-scale** queries — fast, synchronous,
  one request/response.
- Bulk Data Export is built for **population-scale** extraction — every
  patient, every observation, across an entire health system — a request
  that could take minutes or hours to fulfill, structurally wrong to
  handle as one synchronous HTTP response.
- The actual mechanism: the client kicks off the export and gets back an
  immediate `202 Accepted` with a polling URL, not the data itself. The
  client polls that URL until the job completes, at which point it
  receives a manifest listing output files to download — one file **per
  resource type**, in **NDJSON** (newline-delimited JSON: one complete
  JSON object per line, not one giant array) specifically because a
  multi-gigabyte extract can be streamed and processed line by line,
  the exact same
  [streaming-over-loading](../../python/memory-and-caching.md#1-how-would-you-process-a-file-too-large-to-fit-in-memory)
  reasoning already covered for ordinary large-file processing, applied
  here to a healthcare-specific export format.

## 5. "When does a real pipeline actually reach for Bulk Data Export instead of normal FHIR search?"

**Answer:**

- Population health analytics — computing a metric (average HbA1c
  across every diabetic patient in a health system) needs every matching
  patient's data, not one patient looked up interactively.
- Large-scale payer-provider data exchange, or migrating an entire
  patient population from one system to another — the same "this is a
  batch extraction problem, not an interactive query problem" reasoning
  that distinguishes
  [ETL/ELT-style batch processing](../../database/etl-vs-elt.md) from a
  normal application query path elsewhere on this site.
- The deciding signal, practically: if the question is "give me this one
  patient's data right now," that's normal FHIR search; if it's "give me
  every patient's data for analysis," normal search doesn't scale to
  that shape of request at all, and Bulk Data Export is the only
  correctly-architected option.

| Pros | Cons / Trade-offs |
|---|---|
| SMART's scope model lets authorization be as narrow as patient-specific or as broad as system-wide | Real complexity — three distinct scope models to design around correctly |
| EHR launch context removes the need for an app to re-establish "which patient" itself | Only works when actually launched from inside a SMART-compliant EHR session |
| Bulk Data's async job + NDJSON design scales to population-level extracts normal search can't | Meaningfully more pipeline complexity (polling, manifest handling, streaming parse) than a simple REST call |
| `system/*` scopes with signed JWT assertions enable unattended backend access securely | No human approval step at all — the signing-key security of that credential matters enormously |

---

## Code Samples

No dedicated code samples yet for this section.
