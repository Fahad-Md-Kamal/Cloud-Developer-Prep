---
title: "Integration & End-to-End Testing in Practice"
---

# Integration & End-to-End Testing in Practice

[Clean Code Practices](../architecture/clean-code-practices.md#testing-strategy)
already draws the conceptual line between integration and E2E testing.
This page covers the practical concerns that only show up once you
actually try to run these tests for real: where the test data comes
from, how tests avoid stepping on each other, and whether E2E coverage
is actually worth what it costs.

## 1. "An integration test needs a real database — where does that database actually come from?"

**Answer:**

- A **shared test database** (one long-lived instance every test run
  connects to) is the simplest setup, but accumulates state across runs
  and across developers — one test's leftover data can quietly break
  another test weeks later, a direct cause of the shared-mutable-state
  flakiness covered in
  [Flaky Tests §1](flaky-tests-and-ci-strategy.md#1-a-test-fails-intermittently-in-ci-but-always-passes-locally-whats-actually-going-on-and-how-do-you-find-the-cause).
- A **fresh database per test run** (spun up in a container, migrated,
  torn down after) avoids that entirely — every run starts from a known,
  clean state — at the cost of real setup/teardown time added to every
  test run.
- A **transaction-per-test** pattern (common with `pytest-django`'s
  `django_db` fixture) splits the difference: each test runs inside its
  own database transaction, which gets rolled back at the end — fast,
  because there's no real container startup cost, and clean, because
  nothing a test writes actually persists past it.
- **Seed data** — the baseline data a test needs to exist before it
  runs — should be created explicitly by the test (or its fixtures), not
  assumed to already be sitting in the database from some other process.
  A test that silently depends on data it didn't create itself is a test
  that breaks the moment that assumption stops being true.

## 2. "How do you stop integration tests from stepping on each other when run in parallel?"

**Answer:**

- The transaction-per-test pattern from §1 already solves most of this
  for free — if each test's writes roll back before the next test
  starts, parallel tests touching the same tables simply can't see each
  other's data at all.
- Where a real shared resource genuinely can't be isolated this way (a
  test hitting a real external sandbox API with rate limits, a shared
  file on disk), scope test data by a unique identifier per test run —
  a UUID prefix on created records — so parallel runs operate on
  disjoint data even while sharing the same underlying resource.
- This is the integration-testing-specific version of the general
  parallelization trade-off in
  [Flaky Tests §3](flaky-tests-and-ci-strategy.md#3-how-do-you-structure-a-ci-pipelines-test-stage-as-the-test-suite-grows-large-and-slow) —
  parallelization is exactly where un-isolated shared state turns from
  "never noticed" into "constant, confusing flakiness."

## 3. "E2E tests with Playwright/Selenium are slow and occasionally flaky — is the coverage actually worth it?"

**Answer:**

- The mechanism question — why these tools need a real browser, and
  what makes Playwright more reliable than Selenium's WebDriver protocol
  — is covered in
  [Web Crawling at Scale](../database/web-crawling-at-scale.md#selenium-vs-playwright-the-actual-protocol-difference);
  the tools are the same regardless of whether they're scraping a page
  or testing one, only the purpose differs.
- E2E tests catch a specific, real class of bug that nothing earlier in
  the pyramid can: misconfigured infrastructure, a missing environment
  variable, two independently-correct services that don't actually agree
  once genuinely wired together — exactly the gap
  [Clean Code Practices](../architecture/clean-code-practices.md#testing-strategy)
  already names as E2E's reason to exist.
- The honest trade-off: they're the slowest and most expensive tests to
  write, run, and maintain, and the ones most exposed to every flakiness
  cause in [Flaky Tests §1](flaky-tests-and-ci-strategy.md#1-a-test-fails-intermittently-in-ci-but-always-passes-locally-whats-actually-going-on-and-how-do-you-find-the-cause)
  at once — real network timing, a real browser rendering asynchronously,
  real infrastructure that can itself be flaky.
- The practical answer isn't "skip E2E" or "test everything E2E" —
  it's covering only the **critical user journeys** (sign up, check out,
  the handful of flows where a silent failure would be a real incident)
  end to end, and leaving everything else to the cheaper, faster,
  more reliable tiers below it — which is exactly why the pyramid puts
  the fewest tests here, not zero.

| Pros | Cons / Trade-offs |
|---|---|
| Transaction-per-test gives clean isolation with no container startup cost | Doesn't work for resources outside the database's own transaction boundary |
| Per-run unique identifiers let parallel tests share a resource safely | Extra bookkeeping — every test needs to scope its own data explicitly |
| E2E tests catch real wiring/infrastructure bugs nothing else structurally can | Slowest, flakiest, most expensive tier — covering everything this way doesn't scale |
| Scoping E2E to critical journeys only keeps the suite fast and trustworthy | Requires real judgment about what's actually "critical" — easy to over- or under-scope |

---

## Code Samples

No dedicated code samples for this page.
