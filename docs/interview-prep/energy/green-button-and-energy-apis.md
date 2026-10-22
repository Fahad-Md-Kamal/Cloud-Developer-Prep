---
title: "Green Button & Energy Data APIs"
---

# Green Button & Energy Data APIs

The modern, standardized way a customer shares their own utility usage
data with a third-party app — a budgeting tool, a solar-savings
calculator, a demand-response program. The direct energy-sector parallel
to [Open Banking](../fintech/open-banking-and-financial-apis.md) and
[FHIR](../healthcare/fhir-r4.md): consent-based, standardized access
replacing manual bill uploads and screen scraping.

## 1. "What is Green Button, structurally?"

**Answer:**

- **Green Button** is a US initiative (backed by NAESB, the North
  American Energy Standards Board) defining a standard data format
  (**ESPI — Energy Services Provider Interface**, an XML schema) for a
  utility customer's own energy usage data — interval meter reads,
  billing history, account information.
- Two concrete capabilities worth distinguishing: **"Download My
  Data"** (the customer manually exports their own data as a file) and
  **"Connect My Data"** (an ongoing, consent-authorized, API-based
  sharing relationship with a third-party app) — the same
  one-time-export-vs-ongoing-authorized-access distinction that shows up
  across every data-sharing standard on this site.

## 2. "What problem did this solve that existed before?"

**Answer:**

- Before Green Button, a third-party energy app (a budgeting tool, a
  solar ROI calculator) either asked customers to manually type in usage
  numbers off a paper bill, or — the riskier pattern already named for
  [screen-scraped bank data](../fintech/open-banking-and-financial-apis.md#2-what-problem-did-this-actually-solve-that-existed-before) —
  stored the customer's actual utility account login and automated a
  fake session to scrape it.
- Green Button Connect replaces both with the same token-based, scoped,
  revocable consent model already covered for Open Banking — the
  customer's real utility login never leaves the utility's own site, and
  the third-party app only ever holds a token limited to exactly the
  usage data category and time range approved.

## 3. "What does the actual usage data look like, and why does interval granularity matter?"

**Answer:**

- Modern **AMI (Advanced Metering Infrastructure)** smart meters report
  usage in regular intervals — commonly every 15 or 60 minutes — not
  just one aggregate monthly total the way older meters did.
- This granularity is the entire reason Green Button-powered apps are
  useful at all: a monthly total can't show *when* within the day usage
  spikes (useful for a time-of-use rate recommendation, or for a solar
  app estimating when stored battery power would actually offset grid
  draw), while interval data can. The data model exists specifically
  because the underlying metering technology finally made this
  granularity available to report in the first place.

## 4. "How does a third-party energy app actually read a customer's data across multiple different utilities?"

**Answer:**

- The same **aggregator** pattern already covered for
  [Open Banking](../fintech/open-banking-and-financial-apis.md#4-how-does-a-budgeting-app-actually-get-read-access-to-a-users-transactions-across-multiple-different-banks) —
  real utility implementations of Green Button Connect vary in exactly
  the same way real banks' Open Banking APIs do, so an app targeting
  customers across many different utility service territories
  integrates with an aggregator that normalizes those differences,
  rather than building and maintaining a bespoke integration per
  utility itself.

| Pros | Cons / Trade-offs |
|---|---|
| Token-based consent replaces utility credential sharing entirely | Still requires trusting the utility's own authorization implementation and any aggregator in between |
| Interval-level AMI data enables genuinely useful time-of-use analysis | Not every meter/utility has been upgraded to report at this granularity yet |
| A standardized ESPI format makes cross-utility tooling tractable | Real-world conformance still varies utility to utility |
| Aggregators absorb that variance for apps targeting multiple service territories | Adds a third party, and its own reliability/cost, to the data path |

---

## Code Samples

No dedicated code samples yet for this section.
