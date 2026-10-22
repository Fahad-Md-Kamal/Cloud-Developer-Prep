---
title: "Contract Testing"
---

# Contract Testing

[Clean Code Practices](../architecture/clean-code-practices.md#testing-strategy)
already named the exact gap this fills: "two correctly-tested services
that don't actually agree on a contract." Each service's own unit and
integration tests can pass perfectly while the two together are broken
— contract testing is built specifically to catch that, without paying
for a full, slow, flaky end-to-end test across real deployed services.

## 1. "How do two services both pass their own tests and still be broken together?"

**Answer:**

- Service A's tests verify *its own* behavior in isolation — including,
  typically, a mocked or stubbed version of how it expects Service B to
  respond.
- Service B's tests verify *its own* behavior in isolation too — with no
  visibility into what Service A actually expects from it.
- Nothing in either test suite checks that Service A's assumption about
  B's response shape (which fields exist, what type they are, what a
  specific status code means) still matches what B's team actually
  builds and ships — the two services can drift apart silently, each
  one fully green in CI, only discovered when they're deployed together
  and something breaks.
- This is a direct consequence of microservices' core trade-off —
  independent deployability means independent test suites, with nothing
  structurally forcing the two to stay in sync on their own.

## 2. "What's consumer-driven contract testing, and how does it actually prevent this?"

```python
# Consumer (Service A) defines what it expects, as a contract
# (simplified Pact-style example)
contract = {
    "request": {"method": "GET", "path": "/users/123"},
    "response": {
        "status": 200,
        "body": {"id": 123, "name": "string", "email": "string"},
    },
}

# Provider (Service B) verifies it can actually satisfy every
# contract published by every consumer, as part of ITS OWN CI pipeline
```

**Answer:**

- The **consumer** (the service calling another service) writes a
  **contract** — a precise description of exactly what it expects from
  the **provider**'s response, generated directly from the consumer's
  own tests, not hand-written separately and prone to drifting from what
  the consumer's code actually checks.
- That contract gets published somewhere both sides can reach (a shared
  broker, like Pact Broker).
- The **provider**'s own CI pipeline then runs **provider verification**
  — replaying every published contract against the provider's real,
  currently-running code, and failing the provider's build if it can no
  longer satisfy a contract some consumer still depends on.
- This flips the failure point from "silent drift, discovered in
  production" to "the provider's own CI breaks the moment a change would
  violate what a consumer actually needs" — catching the exact gap from
  §1 without either service needing the other one actually running, and
  without a slow, environment-fragile full E2E test.

## 3. "How is this different from just writing integration tests against a shared staging environment?"

**Answer:**

- A shared staging environment requires both services to actually be
  deployed and running together to test anything — slow, often flaky
  (shared environments accumulate state and conflicts between teams),
  and only catches a mismatch *after* both sides have already been
  built and deployed to that environment.
- Contract testing requires **neither** service to be running against
  the other at all — the consumer's tests generate and verify against
  the contract locally; the provider verifies against the same contract
  locally, independently, in its own pipeline. Each side runs fast,
  in isolation, as part of its own normal CI — not waiting on a shared
  resource.
- The trade-off: contract testing verifies the **shape and rules** of
  an interaction precisely, but it doesn't prove the full system
  actually works end to end the way a real E2E test does — see
  [Integration & End-to-End Testing](integration-and-e2e-testing.md)
  for what still needs that slower, costlier tier, and why neither
  replaces the other.

| Pros | Cons / Trade-offs |
|---|---|
| Catches contract drift between services without either one needing to run live | Needs both teams to actually adopt the practice — one-sided contract testing doesn't work |
| Runs fast, in each service's own CI, independent of shared environments | A broker/shared contract store is new infrastructure to run and maintain |
| Provider verification fails the build the moment a real consumer need breaks | Doesn't prove the full system works end to end — a narrower guarantee than E2E |
| Contracts are generated from real consumer tests, not hand-written and driftable | Requires discipline to keep contracts genuinely reflecting what consumers actually use |

---

## Code Samples

No dedicated code samples for this page.
