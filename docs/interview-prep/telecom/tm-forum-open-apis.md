---
title: "TM Forum Open APIs"
---

# TM Forum Open APIs

The modern, standardized way telecom operators expose their own
systems — billing, order management, network inventory — to internal
teams, partners, and third-party apps. The direct telecom parallel to
[FHIR](../healthcare/fhir-r4.md) and
[Open Banking](../fintech/open-banking-and-financial-apis.md): a
resource-oriented REST standard replacing decades of bespoke,
incompatible integrations between carriers and vendors.

## 1. "What are TM Forum Open APIs, structurally?"

**Answer:**

- TM Forum (the telecom industry's standards body) defines a large
  catalog of standardized REST/JSON APIs — `TMF620` (Product Catalog),
  `TMF622` (Product Ordering), `TMF637` (Product Inventory), `TMF639`
  (Resource Inventory) — each a numbered specification covering one
  functional domain of a telecom operator's business, the same
  resource-oriented shape as FHIR's numbered resource types or Open
  Banking's `Account`/`Transaction` endpoints.
- Before this existed, integrating a new partner or launching a new
  product channel meant custom point-to-point integration with each
  operator's own bespoke internal systems — TM Forum APIs exist
  specifically to make "order a product" or "check inventory" mean the
  same request/response shape across operators, the same
  interoperability goal every standard on this site's parallel tracks
  solves for its own domain.

## 2. "What's the CAMARA project, and how does it relate to TM Forum's own API catalog?"

**Answer:**

- **CAMARA** (a Linux Foundation project, backed by GSMA's Open Gateway
  initiative) defines a newer, narrower set of **network capability
  APIs** — exposing specific carrier-network functions (SIM swap
  detection, number verification, device location, quality-on-demand for
  a specific session) as simple, standardized APIs any developer can
  call, not just internal/partner integrations.
- The practical distinction: TM Forum's catalog is broad and
  business-process-oriented (ordering, billing, inventory); CAMARA is
  narrow and **network-capability**-oriented, aimed specifically at
  letting ordinary app developers tap into carrier network functions
  (like confirming a phone number is genuinely active on the network
  it claims) without needing a deep carrier partnership to access a
  single capability.
- A real example worth naming: a **SIM swap detection API** — a
  fintech app can call this before approving a high-risk transaction to
  check whether the user's SIM was recently swapped, a direct,
  concrete mitigation for the exact SIM-swap MFA weakness already
  covered in
  [Identity Security §2](../../security/identity-security-zero-trust-and-pam.md#2-mfa-exists-but-not-all-mfa-is-equally-strong-whats-actually-different-between-the-common-methods) —
  this API exists specifically because that attack is common and real
  enough to need a standardized, carrier-backed check for it.

## 3. "How does order management actually work across these APIs — walk through 'a customer orders a new mobile plan.'"

**Answer:**

- `TMF620` (Product Catalog) defines what's actually available to
  order — the plans, their pricing, their characteristics.
- `TMF622` (Product Ordering) accepts the order itself, tracking it
  through a defined state lifecycle (acknowledged, in progress,
  completed, failed) rather than treating "place an order" as a single
  synchronous action — provisioning a real telecom service can involve
  multiple downstream systems (billing, network activation, SIM
  assignment) that don't all complete instantly.
- `TMF637`/`TMF639` (Product/Resource Inventory) reflect what the
  customer actually has active once provisioning completes — the
  order and the inventory are deliberately separate concerns, the order
  being the *request*, inventory being the *current state* that results
  from it.

## 4. "Why does a real integration still need to handle significant variation between operators, even though the APIs are 'standardized'?"

**Answer:**

- The same real-world conformance variation already named for
  [C-CDA across EHR vendors](../healthcare/hl7-ccda.md#3-walk-me-through-the-general-shape-of-a-c-cda-to-fhir-transformation)
  and
  [Open Banking across different banks](../fintech/open-banking-and-financial-apis.md#4-how-does-a-budgeting-app-actually-get-read-access-to-a-users-transactions-across-multiple-different-banks) —
  TM Forum's specifications define the resource shape, but individual
  operators' actual implementations vary in which optional fields they
  populate, how strictly they follow state-transition rules, and
  real-world edge cases the spec doesn't fully pin down.
- A platform integrating with multiple operators needs the same
  normalization-layer thinking already established across every
  parallel track on this site — build for the standard, but validate
  and handle real deviation from it, rather than assuming conformance.

| Pros | Cons / Trade-offs |
|---|---|
| A shared numbered API catalog replaces bespoke per-operator integration | Real conformance still varies operator to operator, same as every standard on this site |
| CAMARA's narrow network-capability APIs are accessible without a deep carrier partnership | Narrower in scope than TM Forum's full business-process catalog |
| Separating order management from inventory models async provisioning honestly | More moving parts to track than a single synchronous "place order" call |
| A SIM-swap-detection API gives a concrete, carrier-backed MFA-risk signal | Only useful if the calling app actually checks it before approving a risky action |

---

## Code Samples

No dedicated code samples yet for this section.
