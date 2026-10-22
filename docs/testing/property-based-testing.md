---
title: "Property-Based Testing"
---

# Property-Based Testing

An example-based test checks one specific input you thought to write
down. Property-based testing flips that: you describe a rule the code
should always satisfy, and a library generates hundreds of inputs —
including ones you'd never have thought to try — looking specifically
for one that breaks the rule.

## 1. "What's actually different about property-based testing, mechanically?"

```python
from hypothesis import given, strategies as st

def test_sort_is_idempotent(lst):
    assert sorted(sorted(lst)) == sorted(lst)

# Example-based: you pick the input
def test_sort_example():
    assert sorted([3, 1, 2]) == [1, 2, 3]

# Property-based: Hypothesis picks (and tries to break) the input
@given(st.lists(st.integers()))
def test_sort_is_idempotent_property(lst):
    assert sorted(sorted(lst)) == sorted(lst)
```

**Answer:**

- An example-based test asserts a specific output for a specific,
  hand-picked input — it only ever proves the code is correct for the
  handful of cases someone thought to write down.
- A property-based test instead asserts a **property** — a rule that
  should hold true for *any* valid input, not a single expected output
  — and the library (Hypothesis, in Python) generates many different
  inputs automatically, actively searching for one that violates the
  property.
- Good properties to look for: **idempotence** (`sorted(sorted(x)) ==
  sorted(x)`), **round-tripping** (`decode(encode(x)) == x`),
  **invariants** (a shopping cart's total never goes negative, no matter
  what sequence of adds/removals happens), and **equivalence between two
  implementations** (a new, optimized function should produce the same
  output as the old, slow-but-trusted one, across every input).
- This catches a real class of bugs example-based tests structurally
  miss: an edge case nobody thought to write down as an example —
  an empty list, a deeply nested structure, a Unicode string with
  unusual characters, a number right at an overflow boundary.

## 2. "A property-based test finds a failing input — then what? What's 'shrinking'?"

**Answer:**

- The first failing input Hypothesis finds is often large and
  complicated — a list of 40 semi-random integers, say — not something
  a human would want to debug directly.
- **Shrinking** is Hypothesis automatically simplifying that failing
  input afterward, searching for the smallest, simplest input that still
  reproduces the same failure — reducing "a list of 40 integers fails"
  down to, ideally, something like "`[0, -1]` fails," which is actually
  debuggable at a glance.
- This is the practical reason property-based testing is usable at all
  in day-to-day work, rather than just a research curiosity — without
  shrinking, a failing property test would hand you a confusing
  needle-in-a-haystack input instead of a minimal reproduction.

## 3. "When is property-based testing actually worth reaching for, versus just writing more examples?"

**Answer:**

- It earns its setup cost specifically where a genuine **property** or
  **invariant** exists to state — serialization round-trips, sorting/
  ordering functions, mathematical operations, parsers, anything with a
  "two different paths should agree" structure.
- It's a poor fit, or at least no better than example-based testing, for
  logic that's fundamentally about specific business rules with no
  general mathematical property — "a user with a premium subscription
  gets a 20% discount" is just a fact to assert with an example, not a
  property to generalize over.
- A common, high-value pattern worth knowing by name: using
  property-based testing to check a new, optimized implementation
  against an old, trusted one — generate many random inputs, assert both
  implementations agree on every one — catches a regression in the
  rewrite far more thoroughly than hand-picking a handful of comparison
  cases ever would.
- It composes well with [mutation testing](mutation-testing.md) rather
  than replacing it: property-based testing finds inputs your examples
  missed; mutation testing checks whether your assertions (property-based
  or example-based) would actually catch a real bug if one were
  introduced. They're answering different questions about the same test
  suite.

| Pros | Cons / Trade-offs |
|---|---|
| Finds edge cases no one thought to write down as an example | Needs a genuine property to state — not every piece of logic has one |
| Shrinking turns a complex failing input into a minimal, debuggable one | Property definitions themselves can be subtly wrong, masking real bugs |
| Strong fit for serialization, parsers, and comparing two implementations | Slower per test run than a handful of fixed examples — many generated cases |
| Catches regressions a rewrite introduces far more thoroughly than hand-picked cases | A learning curve beyond `assert expected == actual` — a real shift in how you think about a test |

---

## Code Samples

No dedicated code samples for this page.
