---
title: "Green Button Connect: Authorization & Consent"
---

# Green Button Connect: Authorization & Consent

[Green Button & Energy Data APIs](green-button-and-energy-apis.md)
covers the data model — this page covers how a third-party app actually
gets authorized to pull it on an ongoing basis. The flow is the same
OAuth2 redirect-based consent pattern already diagrammed in full for
[FAPI & Consent Authorization Flows](../fintech/fapi-and-consent-flows.md);
this page focuses on where energy data's specific consent model
genuinely differs.

## 1. "Is Green Button Connect's authorization flow the same redirect-based consent flow already covered for Open Banking?"

**Answer:**

- Yes, structurally — the app redirects the customer to their own
  utility's authorization page, the customer logs in and approves a
  scoped request there (never inside the third-party app), an
  authorization code comes back, and the app exchanges it for an access
  token. Nothing new to re-derive from
  [the consent flow already diagrammed for Open Banking/FAPI](../fintech/fapi-and-consent-flows.md#the-consent-authorization-flow).
- The genuine difference is in **what's actually being consented to**
  and **how long that consent typically lasts**, not the mechanical
  shape of the handshake itself.

## 2. "What's actually different about what a customer is consenting to, compared to a bank transaction feed?"

**Answer:**

- A Green Button Connect authorization typically grants **ongoing,
  recurring access** to a defined usage-data feed — not a one-time read,
  but a standing subscription the third-party app polls or receives
  updates from on a regular cadence (new interval data as it becomes
  available from the meter).
- This matters because the consent scope usually needs to specify not
  just *which* data (usage, billing, account info) but the **time range
  and update cadence** — a demand-response program needs near-real-time
  interval data; a yearly savings-report app only needs periodic
  historical updates — the scope granularity genuinely matters more here
  than in a typical one-off financial-transaction read.

## 3. "Why does consent duration and renewal matter more for an ongoing feed like this than for a single data pull?"

**Answer:**

- The same revocation-handling principle already established in
  [FAPI & Consent Authorization Flows §4](../fintech/fapi-and-consent-flows.md#4-whats-consent-expiry-and-revocation-and-why-is-this-a-harder-ux-problem-in-finance-than-in-most-oauth2-contexts) —
  the utility, not the third-party app, remains the actual source of
  truth for whether a standing authorization is still valid, and a
  customer can revoke it from the utility's own account settings at any
  time, independent of what the app's own UI shows.
- Because the access here is ongoing rather than a single read, an app
  needs an explicit plan for **what happens to the service it provides**
  once consent lapses or is revoked — a demand-response program losing
  its real-time feed mid-event has a more immediate operational
  consequence than a budgeting app simply failing to refresh.

| Pros | Cons / Trade-offs |
|---|---|
| Reuses the exact OAuth2 consent mechanics already proven for financial data | Ongoing-feed consent scoping (time range, cadence) is genuinely more granular to design well |
| Utility-controlled revocation keeps the customer in real control of a standing feed | Apps must gracefully handle losing an active feed mid-use, not just at the next refresh |
| Standardized flow across utilities lowers integration cost for multi-territory apps | Real conformance variation still exists, same as every parallel standard on this site |

---

## Code Samples

No dedicated code samples yet for this section.
