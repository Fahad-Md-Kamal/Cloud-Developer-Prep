---
title: "Mutation Testing"
---

# Mutation Testing

[Testing Strategy §2](testing-strategy-pyramid-and-trophy.md#2-what-does-code-coverage-percentage-actually-tell-you-and-what-does-it-miss)
showed a test that hits 100% coverage while asserting nothing at all.
Mutation testing is the mechanism that actually catches that gap —
instead of asking "did the test suite run this line," it asks "would
the test suite notice if this line were wrong."

## 1. "What does a mutation testing tool actually do?"

```python
# Original code
def calculate_discount(price: float, is_premium: bool) -> float:
    if is_premium:
        return price * 0.8
    return price

# One generated "mutant" -- a small, deliberate change
def calculate_discount(price: float, is_premium: bool) -> float:
    if is_premium:
        return price * 0.9   # mutated: 0.8 -> 0.9
    return price
```

**Answer:**

- A mutation testing tool (`mutmut` or `cosmic-ray` in Python)
  automatically generates many small, deliberate bugs — **mutants** —
  by making tiny changes to the code: flipping a comparison operator
  (`<` to `<=`), changing a constant (`0.8` to `0.9`), negating a
  boolean condition, removing a line.
- It then runs the **existing test suite** against each mutant,
  one at a time.
- If a test fails against the mutant, the mutant is **killed** — the
  test suite successfully caught that specific bug, exactly as intended.
- If every test still passes against the mutant, it **survives** — the
  bug slipped through completely undetected, which is the real,
  actionable signal: either nothing exercises that code path at all, or
  something does but never actually asserts on the behavior that
  changed (exactly the empty-assertion pattern from
  [Testing Strategy §2](testing-strategy-pyramid-and-trophy.md#2-what-does-code-coverage-percentage-actually-tell-you-and-what-does-it-miss)).

## 2. "Why is 'mutation score' a stronger signal than line coverage?"

**Answer:**

- Line coverage only asks "did this line execute." A test can execute
  every line in a function and still assert nothing meaningful about the
  result — coverage is satisfied, but the test provides zero actual
  protection against a bug.
- Mutation score asks a fundamentally harder question: "if this exact
  line were subtly wrong, would any test actually notice." A survived
  mutant is direct, concrete proof that a specific category of bug in
  that specific line would currently ship to production undetected.
- This is the difference between a coverage report that just lists which
  lines ran, and a mutation report that hands you an actual list of
  genuine, specific test gaps — "your test suite wouldn't catch this
  particular off-by-one here" — each one directly actionable, not a
  vague percentage.

## 3. "What's the actual cost of running mutation testing, and how do you use it practically?"

**Answer:**

- The real cost is **compute time** — generating dozens or hundreds of
  mutants and running the full test suite against each one individually
  is far slower than running the suite once, often by one or two orders
  of magnitude.
- Because of that cost, mutation testing is rarely run on every commit
  the way unit tests are — common practice is running it periodically
  (nightly, or before a release) or scoped narrowly to a specific
  module under active work, rather than across an entire large codebase
  on every push.
- A survived mutant isn't automatically a bug to fix in the mutant
  itself — it's a prompt to go strengthen the *test* that should have
  caught it. The output of mutation testing is a to-do list for test
  quality, not a list of production bugs.
- Some survived mutants are genuinely **equivalent mutants** — a change
  that doesn't actually alter observable behavior at all (mutating dead
  code, or a change masked by surrounding logic) — these are expected
  noise, not real gaps, and part of using the tool well is learning to
  recognize and ignore them rather than chasing an unreachable 100%
  mutation score.

| Pros | Cons / Trade-offs |
|---|---|
| Directly measures whether tests would catch a real bug, not just whether they ran | Significantly slower than running the test suite once — real compute cost |
| Produces a specific, actionable list of genuine test gaps | Not practical to run on every commit — usually scheduled or scoped narrowly |
| Exposes the exact "high coverage, weak assertions" problem line coverage can't see | Some survived mutants are equivalent/unreachable noise, not real gaps — needs judgment to filter |

---

## Code Samples

No dedicated code samples for this page.
