---
title: "Test Doubles & TDD"
---

# Test Doubles & TDD

"Just mock it" is doing a lot of work hiding four genuinely different
techniques with different guarantees. Getting the vocabulary precise is
also the single most common gap in an otherwise strong testing answer —
being able to say exactly which kind of test double you reached for,
and why, reads as real experience rather than cargo-culting `Mock()`.

## 1. "Mock, stub, fake, spy — what's actually different between them?"

```python
from unittest.mock import Mock, MagicMock

# Stub -- returns canned data, no behavior verification
stub_repo = Mock()
stub_repo.get_user.return_value = {"id": 1, "name": "Alex"}

# Mock -- also verifies HOW it was called, not just what it returns
mock_email = Mock()
service.notify_user(mock_email)
mock_email.send.assert_called_once_with(to="alex@example.com")

# Fake -- a real, working (simplified) implementation, not a canned response
class FakeUserRepository:
    def __init__(self):
        self._users = {}
    def save(self, user):
        self._users[user.id] = user
    def get(self, user_id):
        return self._users.get(user_id)
```

**Answer:**

- **Stub** — returns pre-programmed, canned responses to calls made
  during the test. It doesn't care whether or how it was called, only
  that it hands back the data the test needs.
- **Mock** — adds behavior *verification* on top of a stub's canned
  responses: the test asserts the mock was called a specific number of
  times, with specific arguments — verifying the code under test did
  the right thing, not just that it produced the right output.
- **Fake** — a real, working, simplified implementation of the
  dependency (an in-memory dictionary standing in for a database),
  rather than a pre-programmed response. A fake behaves correctly across
  a range of inputs the way the real thing would, just without its real
  infrastructure — more work to build than a stub, but catches a wider
  class of bugs a canned-response stub would miss entirely.
- **Spy** — wraps a *real* object and records how it was called, while
  still letting the real implementation run. Used when you want the
  actual behavior to happen but also need to verify it happened a
  specific way.
- The practical interview signal: naming "mock" as a catch-all for all
  four is a surface-level answer. Naming the specific one you reached
  for, and why a stub wouldn't have been enough (or why a full fake was
  overkill), is the deeper one.

**Likely follow-up — "when would a fake be worth the extra effort over a stub?"**

- When the test needs realistic behavior across several interactions —
  save, then get, then update — a stub returning one canned response per
  call can't model that, but a fake (even a simple in-memory one)
  naturally can.
- A fake is also reusable across many tests exercising the same
  dependency, where hand-coding stub responses per test gets repetitive
  fast.

## 2. "What's the actual TDD cycle, and what does each step buy you?"

<svg viewBox="0 0 820 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of the TDD red-green-refactor cycle: write a failing test, write the minimum code to pass it, then refactor, repeating" style="width:100%;height:auto;max-width:820px;display:block;margin:0 auto;font-family:inherit;">
<circle cx="410" cy="210" r="150" fill="none" stroke="#c7cedb" stroke-width="2"></circle>
<rect x="330" y="30" width="160" height="60" rx="8" fill="#fbe7e4" stroke="#c0392b" stroke-width="3"><animate attributeName="stroke" values="#c0392b;#c0392b;#9aa5b3;#9aa5b3" keyTimes="0;0.3;0.33;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="410" y="56" font-size="14" font-weight="600" text-anchor="middle" fill="#8e2d20">Red</text>
<text x="410" y="75" font-size="12" text-anchor="middle" fill="#8e2d20">write a failing test</text>
<rect x="590" y="260" width="160" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="3"><animate attributeName="stroke" values="#9aa5b3;#9aa5b3;#1f9d6b;#1f9d6b;#9aa5b3;#9aa5b3" keyTimes="0;0.3;0.33;0.63;0.66;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="670" y="286" font-size="14" font-weight="600" text-anchor="middle" fill="#0f6b45">Green</text>
<text x="670" y="305" font-size="12" text-anchor="middle" fill="#0f6b45">minimum code to pass</text>
<rect x="70" y="260" width="160" height="60" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="3"><animate attributeName="stroke" values="#9aa5b3;#9aa5b3;#2f6fb3;#2f6fb3;#9aa5b3" keyTimes="0;0.63;0.66;0.96;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="150" y="286" font-size="14" font-weight="600" text-anchor="middle" fill="#1d4a78">Refactor</text>
<text x="150" y="305" font-size="12" text-anchor="middle" fill="#1d4a78">clean up, tests still pass</text>
<circle r="9" fill="#434d5c"><animate attributeName="cx" values="410;670;150;410" keyTimes="0;0.33;0.66;1" dur="16s" repeatCount="indefinite"></animate><animate attributeName="cy" values="90;260;260;90" keyTimes="0;0.33;0.66;1" dur="16s" repeatCount="indefinite"></animate></circle>
<text x="410" y="400" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.3;0.33;1" dur="16s" repeatCount="indefinite"></animate>Write a test for behavior that doesn't exist yet — it must fail, for a real reason.</text>
<text x="410" y="400" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.33;0.36;0.63;0.66;1" dur="16s" repeatCount="indefinite"></animate>Write the simplest code that makes it pass — not the most elegant code.</text>
<text x="410" y="400" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.69;1" dur="16s" repeatCount="indefinite"></animate>Clean up the implementation, with the passing test as a safety net.</text>
</svg>

**Answer:**

- **Red** — write a test for behavior that doesn't exist yet, and watch
  it fail. This step is often skipped by developers new to TDD, but it's
  the one that actually matters most: a test that's never been seen to
  fail might be passing for the wrong reason (a typo in the assertion, a
  test that doesn't actually exercise the code path it claims to).
- **Green** — write the *minimum* code needed to make the test pass, not
  the most elegant or general solution. This constraint is deliberate —
  it keeps the design driven by actual required behavior, not
  speculation about what might be needed later.
- **Refactor** — now, with a passing test as a safety net, clean up the
  implementation (remove duplication, improve naming) without changing
  behavior. The test suite is what makes this safe — a refactor that
  breaks something gets caught immediately, not discovered later.
- The cycle repeats in small steps — each loop adds one small piece of
  verified behavior, rather than writing a large chunk of code and
  testing it all at once at the end.

## 3. "Is TDD actually worth it, or is it dogma?"

**Answer:**

- TDD's real payoff is **design pressure**, not just test coverage —
  writing the test first forces you to think about the interface (what
  inputs, what output, what's actually being verified) before
  implementation details, which tends to produce more testable,
  decoupled code than writing the implementation first and bolting tests
  on afterward.
- It's genuinely less valuable for exploratory work — when you don't yet
  know what the right interface even looks like, writing tests first
  against a design that's about to change several times just adds
  rework. Prototype first, then backfill tests once the shape settles,
  is a reasonable alternative in that specific situation.
- **London school (mockist) vs. Chicago school (classicist)** — a real,
  substantive split in how TDD gets practiced: the London school mocks
  every collaborator, testing a unit in complete isolation and verifying
  interactions between objects; the Chicago school prefers real
  collaborators where practical and verifies actual state/behavior,
  reaching for a test double only when a real collaborator is
  genuinely too slow, flaky, or external to use directly. Neither is
  objectively correct — know both exist, and that reaching for a mock by
  default (London-style) isn't the only legitimate way to practice TDD.

| Pros | Cons / Trade-offs |
|---|---|
| Fakes catch a wider class of bugs than stubs, at more build cost | Building a good fake takes real effort — not worth it for a rarely-used dependency |
| Mocks verify interaction, not just output — catches "called wrong" bugs | Over-specifying mock expectations makes tests brittle to harmless refactors |
| TDD's red step catches a test that passes for the wrong reason | Strict TDD slows down genuinely exploratory work where the design isn't settled yet |
| Red-green-refactor keeps refactoring safe with a passing-test net | Requires real discipline — skipping red or refactor quietly erodes the whole benefit |

---

## Code Samples

No dedicated code samples for this page.
