---
title: "Flaky Tests & CI Test Strategy"
---

# Flaky Tests & CI Test Strategy

A test that fails randomly is worse than no test at all — it doesn't
just fail to catch bugs, it actively trains the team to ignore red CI,
which is how a real failure eventually slips through a sea of "oh,
that one's just flaky." Fixing the root cause matters more than any
retry mechanism papering over it.

## 1. "A test fails intermittently in CI but always passes locally — what's actually going on, and how do you find the cause?"

**Answer — the four real causes, in order of how often they're the culprit:**

- **Shared mutable state between tests** — a global variable, a module-level
  cache, or a database row one test modifies that another test (run in
  the same process, same DB) depends on being in its original state.
  The fix is test isolation — each test gets its own fixture data, and
  nothing persists between tests by default.
- **Time dependencies** — a test that asserts against `datetime.now()`
  or sleeps a fixed duration and hopes that's enough. Freeze time
  explicitly in the test (a library like `freezegun`) instead of relying
  on wall-clock timing, and replace a fixed `sleep()` with polling for
  the actual condition the test cares about.
- **Race conditions in async/concurrent code** — a test that doesn't
  properly wait for an async operation to complete before asserting on
  its result. This is the hardest category to spot, because it often
  only manifests under CI's different timing/load characteristics, not
  locally.
- **External dependency flakiness** — a real network call, a real
  third-party API, or a real database connection that occasionally times
  out or rate-limits. The test isn't actually flaky — the thing it calls
  is — which is the argument for mocking or faking anything external in
  a unit/integration test, saving real external calls for a narrow band
  of contract or E2E tests (see
  [Contract Testing](contract-testing.md) and
  [Integration & End-to-End Testing](integration-and-e2e-testing.md)).
- **Why CI specifically surfaces these**: CI runners typically have
  different (often more constrained) CPU/memory than a developer's
  machine, and frequently run tests in parallel across more workers —
  both widen timing windows and increase the chance of a race condition
  or resource contention actually manifesting, compared to one
  developer running one test file alone, slowly, on a fast local
  machine.

## 2. "Someone suggests just adding a retry to the flaky test instead of fixing it — what's wrong with that?"

**Answer:**

- A retry treats the symptom, not the cause — the test is still
  nondeterministic, it's just nondeterministic in a way that's less
  visible, since it now passes on attempt 2 or 3 without anyone
  investigating why attempt 1 failed.
- This quietly erodes trust in the whole suite the same way skipping the
  TDD "red" step does — a passing test that doesn't reliably mean "this
  behavior works" is worse than an honest failure, because nobody knows
  which passing tests to actually trust.
- A narrow, legitimate exception: a genuinely external, occasionally
  unreliable dependency in an E2E test (a third-party sandbox API with
  its own uptime issues) can reasonably retry — but that's a deliberate,
  documented exception for a known-external cause, not a blanket policy
  applied to hide an unknown one.
- The better first move: **quarantine** the flaky test (mark it,
  exclude it from blocking CI, but keep it running and visibly tracked)
  while actually investigating — this keeps the signal honest (CI stays
  green for real reasons) without silently deleting the test's value
  entirely.

## 3. "How do you structure a CI pipeline's test stage as the test suite grows large and slow?"

```yaml
test-unit:
  stage: test
  script: [pytest tests/unit --numprocesses=auto]  # parallelized, fast

test-integration:
  stage: test
  needs: []                        # doesn't wait for the rest of its own stage
  script: [pytest tests/integration]

test-e2e:
  stage: test
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
  script: [pytest tests/e2e]       # slowest tier, run more selectively
```

**Answer:**

- Mirror the test pyramid in the pipeline itself — unit tests run on
  every single commit, fast and parallelized; integration tests run on
  every commit too, but separately staged since they're slower;
  E2E tests, the slowest and priciest tier, often run only on a merge
  request or before a deploy rather than on every single push, trading
  some feedback latency for not blocking fast iteration on the cheapest
  checks. See
  [GitLab CI §3: Job Ordering](../cloud-devops/gitlab-ci.md#3-job-ordering-stages-vs-a-real-dag)
  for how `needs` lets jobs within a stage actually run in parallel
  instead of waiting on each other unnecessarily.
- **Parallelization** — splitting a large test suite across multiple
  CI workers (`pytest-xdist`'s `--numprocesses=auto`, or test sharding
  by file/class) cuts wall-clock time roughly in proportion to worker
  count, at the cost of needing tests to be genuinely independent —
  parallelization is exactly where hidden shared-state flakiness (§1)
  gets exposed, since tests that happened to never collide when run
  sequentially can now run at the same time.
- **Test selection** — on a very large suite, running only tests
  affected by a given change (via dependency analysis, or a simpler
  heuristic like "tests in the same module as changed files") trades
  some coverage-per-commit for much faster feedback, with a full-suite
  run still happening on a schedule or before merge to catch anything
  the heuristic missed.

| Pros | Cons / Trade-offs |
|---|---|
| Fixing the root cause of flakiness keeps CI results actually trustworthy | Takes real investigation time — a retry is faster to apply, which is exactly the trap |
| Quarantining a flaky test keeps CI green honestly while it's investigated | Still needs someone to actually follow up — an ignored quarantine list grows forever |
| Staged pipeline (unit → integration → E2E) gives fast feedback on cheap checks first | More pipeline configuration to maintain than one flat test stage |
| Parallelization cuts wall-clock CI time significantly on large suites | Exposes shared-state bugs that sequential runs never triggered |

---

## Code Samples

No dedicated code samples for this page.
