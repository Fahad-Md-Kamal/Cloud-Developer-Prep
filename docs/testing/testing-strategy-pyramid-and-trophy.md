---
title: "Testing Strategy: The Pyramid, the Trophy & What Not to Test"
---

# Testing Strategy: The Pyramid, the Trophy & What Not to Test

[Clean Code Practices: Testing Strategy](../architecture/clean-code-practices.md#testing-strategy)
already covers the core distinction — unit vs. integration vs. E2E, and
why the pyramid puts fewest tests at the most expensive level. This
page goes further: the pyramid-vs-trophy debate, what coverage
percentage actually tells you (and doesn't), and the harder skill —
deciding what's *not* worth testing at all.

## 1. "Is the test pyramid still the right shape for every kind of application?"

**Answer:**

- The classic pyramid (many unit tests, fewer integration, fewest E2E)
  assumes most of the risk lives in business logic — true for a
  logic-heavy backend service, where unit tests cheaply cover the bulk
  of what can go wrong.
- **The testing trophy** (popularized by Kent C. Dodds) argues the
  opposite shape for UI-heavy and integration-heavy applications: more
  integration tests, fewer unit tests, because the actual risk in a
  frontend or a thin API layer is mostly in how pieces connect — a
  component rendering correctly with real child components, a request
  actually reaching the right handler — not in isolated logic a unit
  test would catch.
- Neither shape is universally correct — the deciding question is
  **where the real risk in this specific codebase actually lives**. A
  payment-calculation service genuinely has pyramid-shaped risk (complex
  isolated logic). A CRUD-heavy API with thin handlers and a UI stitching
  several calls together genuinely has trophy-shaped risk (the wiring is
  the risk, not any one function).
- The practical interview answer: name both, and justify the shape by
  pointing at where bugs have actually come from in a system you've
  worked on — not by reciting the pyramid as a universal law.

## 2. "What does code coverage percentage actually tell you, and what does it miss?"

```python
def calculate_discount(price: float, is_premium: bool) -> float:
    if is_premium:
        return price * 0.8
    return price

def test_calculate_discount():
    calculate_discount(100, True)  # executes both branches via two calls...
    calculate_discount(100, False)  # ...but asserts NOTHING
```

**Answer:**

- Coverage measures **which lines executed** during the test suite —
  nothing about whether the test actually verified the right behavior.
- The snippet above gets 100% line and branch coverage while asserting
  absolutely nothing — a textbook case of coverage being a necessary but
  nowhere-near-sufficient signal.
- High coverage with weak assertions is common enough that
  [mutation testing](mutation-testing.md) exists specifically to catch
  it — deliberately breaking the code and checking whether the test
  suite notices, which line coverage structurally cannot measure.
- The honest use of a coverage number: a floor, not a target. "This file
  has 40% coverage" is a real signal something's under-tested; "this
  file has 100% coverage" tells you almost nothing about test quality on
  its own.

## 3. "How do you decide what's genuinely not worth testing?"

**Answer:**

- Framework code, trivial getters/setters, and anything with no real
  logic (a pass-through function that just calls another function with
  the same arguments) — testing these mostly tests that Python works,
  not that your code works.
- Code that changes constantly and isn't load-bearing (a quick internal
  admin script) often isn't worth the maintenance cost of keeping its
  tests passing through every change — weigh the cost of a broken test
  against the cost of the bug it might have caught.
- The actual risk-based framework: prioritize depth of testing by
  **consequence of being wrong**, not by how much code there is — auth,
  billing, anything touching PII, and anything hard to manually verify
  in production earn disproportionate test investment; a cosmetic
  formatting helper doesn't, even if it has more lines.
- This is the same reasoning
  [Clean Code Practices](../architecture/clean-code-practices.md#testing-strategy)
  already applies to "chasing 100% coverage on everything is lower value
  than deep coverage on auth, billing, and anything touching PII" — this
  page just names the general principle (consequence-weighted, not
  volume-weighted) behind that specific example.

| Pros | Cons / Trade-offs |
|---|---|
| Pyramid shape minimizes cost for logic-heavy, business-rule-dense code | Wrong shape for UI/integration-heavy code, where the wiring is the real risk |
| Trophy shape catches integration bugs unit tests structurally can't | More integration tests means slower, more expensive test suites |
| Coverage is a fast, objective floor signal | Says nothing about assertion quality — 100% coverage can still mean untested behavior |
| Risk-based prioritization focuses effort where bugs are actually costly | Requires real judgment calls, not a mechanical rule — easy to get wrong without domain context |

---

## Code Samples

No dedicated code samples for this page.
