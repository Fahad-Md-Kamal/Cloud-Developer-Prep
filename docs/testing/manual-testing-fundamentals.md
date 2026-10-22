---
title: "Manual Testing Fundamentals: Test Case Design & Bug Reports"
---

# Manual Testing Fundamentals: Test Case Design & Bug Reports

Everything else in this section assumes you're already writing
automated test code. This page is the layer underneath that — the
systematic techniques for deciding *what* to test in the first place,
and how to report what you find so a developer can actually act on it.
These are the core skills a testing career starts with, automated or not.

## 1. "You can't test every possible input — how do you systematically pick which ones actually matter?"

```text
Age field: must accept 18-65

Equivalence classes: below 18 (invalid), 18-65 (valid), above 65 (invalid)
Boundary values to actually test: 17, 18, 65, 66
```

**Answer:**

- **Equivalence partitioning** — group all possible inputs into classes
  where every member of a class should behave the same way, then test
  *one representative value per class* instead of every possible value.
  Testing age 25 and age 40 separately adds no new information once
  both are confirmed to be in the same "valid" class — one is enough.
- **Boundary value analysis** — bugs cluster at the edges of a valid
  range far more often than in the middle of it (an off-by-one in a
  `>=` vs `>` comparison, for one). Testing the boundary values
  themselves (17, 18, 65, 66 above) catches far more real bugs per test
  than testing values safely in the middle of each class.
- Together, these two techniques turn "test everything" (impossible) into
  a small, deliberate, high-value set of test cases — the systematic
  foundation underneath good manual (and automated) test design alike.

## 2. "Beyond boundaries on a single field, how do you test a feature with several fields that interact?"

```text
Decision table: discount eligibility

| Premium member? | Order > $100? | → Discount |
|---|---|---|
| Yes | Yes | 20% |
| Yes | No | 10% |
| No | Yes | 5% |
| No | No | 0% |
```

**Answer:**

- **Decision table testing** — lay out every combination of the
  conditions that affect an outcome, and the expected result for each
  combination, as an explicit table. This is most valuable exactly where
  bugs actually hide: the interaction *between* conditions, which
  testing each field in isolation can completely miss (a feature can
  work correctly for a premium member alone and for a large order alone,
  and still get the combination wrong).
- **State transition testing** — for a feature with distinct states and
  rules about which transitions are even valid (an order going
  `pending` → `paid` → `shipped`, but never `shipped` → `pending`), the
  table of valid and invalid transitions *is* the test design — testing
  that an invalid transition is correctly rejected is just as important
  as testing that a valid one succeeds.
- Both techniques share the same underlying discipline: write the
  expected behavior down explicitly, as a table, *before* testing —
  this surfaces ambiguous or missing requirements (what discount should
  an edge case actually get?) before they become a bug found in
  production instead of a design question asked up front.

## 3. "What's exploratory testing, and how is it different from just 'clicking around'?"

**Answer:**

- Exploratory testing is **simultaneous learning, test design, and test
  execution** — you're not following a pre-written script; you're
  forming a hypothesis about where a bug might be hiding, based on what
  you're seeing as you go, and immediately testing it.
- The difference from aimless clicking is **structure and documentation**
  — a real exploratory session has a time-boxed **charter** (a specific
  area or question to explore, e.g. "explore the checkout flow's error
  handling for 30 minutes"), and the tester takes notes on what was
  actually covered and what was found, so the session's value survives
  past the tester's own memory.
- It earns its place specifically where scripted test cases structurally
  can't reach: genuinely novel interactions nobody wrote a test case for
  in advance, and the kind of "that's weird" observation that only comes
  from a human actually using the feature, not from executing a
  predetermined checklist.
- Scripted and exploratory testing aren't competitors — scripted testing
  gives repeatable, regression-safe coverage of known behavior;
  exploratory testing is what finds the bug nobody thought to write a
  script for in the first place.

## 4. "You found a bug — what actually makes a bug report useful instead of a developer coming back asking ten clarifying questions?"

```text
Title: Checkout fails with 500 error when applying a discount code
       to an order containing only digital products

Steps to reproduce:
1. Add a digital-only product (e.g. "E-book: Python Basics") to cart
2. Apply discount code SAVE20 at checkout
3. Click "Place Order"

Expected: Order completes with 20% discount applied
Actual: Page shows a 500 error; order is not created

Environment: Staging, Chrome 131, test account test-buyer@example.com
Severity: High (blocks checkout entirely for this cart type)
Priority: P1 (affects a real, common product combination)
```

**Answer:**

- **Exact steps to reproduce** — numbered, specific, and complete enough
  that someone who's never seen the bug can follow them and hit it
  themselves on the first try. "Checkout is broken" is not a bug report;
  it's a complaint.
- **Expected vs. actual, stated explicitly and separately** — not
  implied. A developer shouldn't have to infer what *should* have
  happened from context.
- **Severity vs. priority — a real, commonly confused distinction**:
  severity is *how bad the impact is* (does it crash the app, corrupt
  data, or just look slightly off) — a fact about the bug itself, not
  about scheduling. Priority is *how soon it should be fixed* — a
  business/scheduling decision. A cosmetic typo on the homepage can be
  high priority (it's embarrassing, fix it today) while being low
  severity (nothing is actually broken); a severe crash in a rarely-used
  admin tool can be low priority despite high severity, if almost no one
  hits it.
- **Environment details** — browser/OS version, account/test data used,
  which environment (staging vs. production) — the difference between a
  bug a developer can reproduce in five minutes and one that eats half a
  day chasing "works on my machine."

| Pros | Cons / Trade-offs |
|---|---|
| Equivalence partitioning + boundary analysis finds most bugs with far fewer test cases than exhaustive testing | Still requires judgment to identify the actual classes and boundaries correctly |
| Decision tables catch interaction bugs between fields that isolated field testing structurally misses | Table size grows fast with more conditions — needs pruning for genuinely independent ones |
| Exploratory testing finds novel bugs no script anticipated | Without charters and notes, its value is lost the moment the session ends |
| A precise bug report (steps, expected/actual, severity vs. priority) gets fixed faster with less back-and-forth | Takes real discipline to write well under time pressure — easy to shortcut |

---

## Code Samples

No dedicated code samples for this page.
