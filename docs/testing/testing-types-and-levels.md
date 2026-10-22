---
title: "Testing Types & Levels: Smoke, Sanity, Regression & UAT"
---

# Testing Types & Levels: Smoke, Sanity, Regression & UAT

[Testing Strategy](testing-strategy-pyramid-and-trophy.md) already
covers unit, integration, and E2E — that's one axis, organized by
*scope* (how much of the system a test exercises). This page covers a
different axis: testing types organized by *purpose and timing* —
smoke, sanity, regression, and acceptance testing — plus the
black-box/white-box/gray-box distinction that describes *how much the
tester knows about the code underneath*.

## 1. "Smoke test vs. sanity test — these get used interchangeably, what's actually different?"

**Answer:**

- **Smoke testing** — a quick, broad check that the build's most basic
  functions work at all, run immediately after a new build or
  deployment, before investing any further testing effort in it. The
  name comes from hardware testing: power it on, check it doesn't
  literally smoke, before testing anything more specific. If the smoke
  test fails, the build is rejected outright — no further testing
  happens on a build that can't even do the basics.
- **Sanity testing** — a quick, *narrow* check focused on one specific
  area, typically run right after a small fix or minor change, to
  confirm that specific area now works as expected before investing in
  broader regression testing. "We just fixed the checkout discount bug
  — does checkout work now" is a sanity check, not a smoke test.
- The practical difference is **breadth vs. depth, and when each runs**:
  smoke is broad-and-shallow, gatekeeping a whole new build; sanity is
  narrow-and-focused, gatekeeping a specific fix before deeper testing
  resumes.

## 2. "What does 'regression testing' actually mean, and how do you decide what to re-run?"

**Answer:**

- Regression testing means re-running existing tests after a change, to
  confirm that change didn't break something that used to work — the
  core insight being that a fix or new feature in one place can silently
  break *unrelated* behavior elsewhere, and the only way to catch that
  reliably is to re-check what already worked, not just what was
  intentionally changed.
- **Full regression** (re-run everything) gives the strongest
  confidence but costs the most time — reserved for major releases or
  changes touching core, widely-depended-on code.
- **Risk-based regression** (re-run tests covering the areas most likely
  to be affected, based on what actually changed and what's historically
  been fragile) trades some confidence for speed — the practical default
  for most day-to-day changes, since full regression on every small
  change doesn't scale.
- This is the same tension automated CI pipelines already manage with
  [test selection](flaky-tests-and-ci-strategy.md#3-how-do-you-structure-a-ci-pipelines-test-stage-as-the-test-suite-grows-large-and-slow) —
  running a scoped, change-relevant subset fast, with a full run
  happening less frequently to catch anything the scoped run missed.

## 3. "Black-box, white-box, gray-box testing — what's the actual distinction, and why does it matter which one you're doing?"

**Answer:**

- **Black-box testing** — the tester has no knowledge of the internal
  code, only the specification/requirements and the actual input/output
  behavior. Test design comes from "what should this do," not "how is
  this implemented" — equivalence partitioning and boundary value
  analysis (see
  [Manual Testing Fundamentals](manual-testing-fundamentals.md)) are
  classic black-box techniques.
- **White-box testing** — the tester has full visibility into the
  code and designs tests around its actual structure — covering specific
  branches, loops, and paths through the implementation. Unit tests
  written by the developer who wrote the code are the most common
  real-world example.
- **Gray-box testing** — a deliberate middle ground: partial knowledge
  of the internals (the database schema, the API's internal structure)
  used to design smarter black-box-style tests, without full white-box
  visibility into every line. A tester who knows an API is backed by a
  specific database can design more targeted tests around that schema's
  actual constraints, without reading the application code itself.
- This matters because it's a real axis of **who's actually positioned**
  to do each kind of testing — a dedicated QA tester without code access
  is doing black-box testing by necessity; a developer's own unit tests
  are inherently white-box; gray-box is where a tester with some
  technical/architectural knowledge but not full code access typically
  operates.

## 4. "What's UAT (User Acceptance Testing), and how is it different from everything above?"

**Answer:**

- Every testing type covered so far (and across this site's other
  testing pages) answers "does this work correctly, from a technical
  standpoint." **UAT** answers a different question entirely: "does this
  actually meet the *business's* real need" — performed by actual
  end users or business stakeholders, not testers or developers.
- A feature can pass every unit, integration, E2E, and regression test
  perfectly and still fail UAT — because it was built exactly to a
  misunderstood or incomplete specification. UAT is the check that
  catches "we built the wrong thing correctly," which no amount of
  technical testing against that same specification can catch on its
  own.
- **Alpha testing** (internal staff, in a controlled environment) and
  **beta testing** (a limited external group, in something closer to
  real-world conditions) are both common precursors to a full release,
  each trading some risk exposure for earlier, real-world feedback
  before the general release.

| Pros | Cons / Trade-offs |
|---|---|
| Smoke testing rejects a fundamentally broken build before wasting further test effort on it | Only catches the most basic failures — passing a smoke test proves very little beyond "it starts" |
| Sanity testing gives fast confidence after a small, targeted fix | Narrow by design — doesn't substitute for full regression on a risky change |
| Risk-based regression scales to frequent changes better than full regression | Carries real risk of missing an unrelated break the risk assessment didn't predict |
| UAT catches "built the wrong thing correctly," which technical testing structurally can't | Expensive and slow — real stakeholders' time, late in the process to discover a fundamental mismatch |

---

## Code Samples

No dedicated code samples for this page.
