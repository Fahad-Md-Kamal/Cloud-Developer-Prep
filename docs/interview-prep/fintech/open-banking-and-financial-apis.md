---
title: "Open Banking & Financial Data APIs"
---

# Open Banking & Financial Data APIs

The modern, standardized way a third-party app reads a customer's bank
data — the direct fintech parallel to
[FHIR](../healthcare/fhir-r4.md) in healthcare. Before this existed,
"connect your bank account" meant something genuinely dangerous; this
page covers what actually replaced it, and why.

## 1. "What is Open Banking / FDX, structurally? What's the core data model?"

**Answer:**

- FDX (Financial Data Exchange, the primary US standard) and Open
  Banking/PSD2 (the UK/EU equivalent) both define standardized,
  token-authorized REST/JSON APIs exposing a customer's financial data —
  `Account`, `Transaction`, `Balance`, `Identity` — the same
  resource-oriented shape as FHIR's `Patient`/`Observation`/`Condition`,
  just modeling financial relationships instead of clinical ones.
- A third-party app requests exactly the data it needs (balances,
  90 days of transactions) through this API, with the customer's
  explicit, scoped, revocable consent — never the customer's actual bank
  login credentials.

## 2. "What problem did this actually solve that existed before?"

**Answer:**

- Before Open Banking, third-party fintech apps (budgeting apps, early
  lenders) got bank data through **screen scraping** — the app stored
  the customer's actual bank username and password, then automated a
  fake browser session logging in and scraping the account page as if
  it were the customer.
- This is a direct, severe violation of the same principle already
  covered in
  [Identity Security](../../security/identity-security-zero-trust-and-pam.md) —
  an app holding a customer's actual full-access credentials, rather
  than a narrowly scoped token, has far more access than it needs and
  becomes a serious liability the moment it's breached, leaked, or
  simply misused.
- Open Banking replaced credential-sharing with token-based, scoped
  access entirely — the customer's real password never leaves their own
  bank's login page, and the app only ever holds a token limited to
  exactly what was approved.

## 3. "FDX vs. PSD2/Open Banking UK — what's actually different?"

**Answer:**

- **FDX** is a US, industry-consortium-led **voluntary** standard — a
  published API specification that banks and data aggregators choose to
  adopt.
- **PSD2/Open Banking** (UK/EU) is **regulatory-mandated** — a law
  requiring banks to expose standardized APIs at all, with a dedicated
  body (the UK's Open Banking Implementation Entity) defining the actual
  technical standard banks must implement to comply.
- This is the exact same policy-vs-implementation split already drawn
  for healthcare in
  [FHIR R4 §6](../healthcare/fhir-r4.md#6-us-core-uscdi-hl7-v2-how-do-all-these-relate-to-fhir-r4) —
  USCDI is the policy-level mandate, US Core is its FHIR-level technical
  implementation. PSD2 plays USCDI's role here; Open Banking's technical
  standard plays US Core's.

## 4. "How does a budgeting app actually get read access to a user's transactions across multiple different banks?"

**Answer:**

- Through an **account aggregator** (Plaid, Finicity/Mastercard,
  TrueLayer, Tink) sitting between the fintech app and every individual
  bank — the app integrates with one aggregator API, and the aggregator
  handles the actual per-bank connection and normalization underneath.
- This matters because real banks' conformance to "the standard" varies
  in practice — the exact same real-world variation problem already
  named for
  [C-CDA vendor variation](../healthcare/hl7-ccda.md#3-walk-me-through-the-general-shape-of-a-c-cda-to-fhir-transformation):
  two banks can both claim Open Banking compliance while differing
  meaningfully in field coverage, pagination behavior, or how strictly
  they follow the spec. The aggregator absorbs that variance so the
  downstream app doesn't have to handle every bank's own quirks itself.

| Pros | Cons / Trade-offs |
|---|---|
| Token-scoped access replaces full credential sharing entirely | Still requires trusting the token issuer (the bank) and the aggregator in the middle |
| Standardized resource shapes make building across multiple banks tractable | Real-world conformance still varies meaningfully bank to bank |
| Consent is explicit, scoped, and revocable by the customer | Revocation handling has to be designed for, not assumed away (see FAPI §4) |
| Aggregators absorb per-bank variance so apps integrate once | Adds a third party, and its own cost/reliability, into the data path |

---

## Code Samples

No dedicated code samples yet for this section.
