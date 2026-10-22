---
title: "Testing Tools & Frameworks by Type"
---

# Testing Tools & Frameworks by Type

Other pages in this section cover testing *concepts* — what a mock is,
why coverage lies, how to design a test case. This page is the practical
map on top of that: which concrete tool or framework actually fits each
type of testing, organized by what each one mechanically does
differently, not just by name recognition.

## 1. "Unit testing frameworks — what's actually different between them, beyond the language?"

**Answer:**

- Most share the same underlying **xUnit pattern**: discover test
  functions/methods automatically, run setup before each test and
  teardown after, provide `assert`-style methods, and report
  pass/fail/error per test.
- **pytest vs. `unittest` (Python)** — `unittest` requires class-based
  tests inheriting from `TestCase`, in the Java-originated xUnit style.
  `pytest` allows plain functions, uses Python's native `assert`
  directly (rewriting it at import time to give readable failure
  messages, rather than requiring `self.assertEqual`), and adds
  **fixtures** — reusable, composable setup/teardown via dependency
  injection into test function parameters — plus **parametrization**
  (running the same test body against many input sets with one
  decorator). `unittest` still runs underneath most Python CI, but
  `pytest` is the practical default for new code.
- **JUnit5 / TestNG (Java, Kotlin)** — annotation-driven (`@Test`,
  `@BeforeEach`), the JVM ecosystem's equivalent of pytest's fixture
  model via `@BeforeEach`/`@AfterEach` and dependency-injected
  parameters.
- **Jest vs. Mocha (JavaScript/TypeScript)** — a real architectural
  difference worth knowing: **Jest bundles the test runner, assertion
  library, and mocking utilities into one package** — install one thing,
  get everything. **Mocha is runner-only** by design, composed with a
  separate assertion library (Chai) and mocking library (Sinon) —
  more setup, more flexibility to swap pieces independently.
- **Go's built-in `testing` package** — no external framework needed at
  all; testing is part of the standard toolchain (`go test`).
  **Table-driven tests** (a slice of input/expected-output structs,
  looped over in one test function) are the idiomatic Go pattern for
  what pytest would do with parametrization.

## 2. "Mocking libraries — how do they actually substitute a real dependency, mechanically?"

```python
from unittest.mock import patch

# Patch WHERE the name is looked up, not where it's defined --
# a classic, genuinely common gotcha
with patch("myapp.services.order_service.send_email") as mock_send:
    process_order(order)
    mock_send.assert_called_once()
```

**Answer:**

- [Test Doubles & TDD](test-doubles-and-tdd.md) already covers the
  mock/stub/fake/spy *vocabulary* — this is how each language's library
  actually implements the substitution underneath that vocabulary.
- **Python's `unittest.mock`** — monkey-patches an attribute reference
  at a target location for the duration of the patch, then restores the
  original afterward. The real, commonly-missed gotcha: you patch the
  name **where it's looked up** (the importing module's namespace), not
  where it's originally defined — patching the wrong location silently
  does nothing, because the code under test is still holding a reference
  to the un-patched original.
- **Mockito (Java)** — uses bytecode manipulation/dynamic proxies to
  generate a fake implementation of an interface or class at runtime,
  which is then injected wherever the real dependency would go — no
  monkey-patching of existing code needed, since Java's static typing
  requires an actual substitutable object, not a patched reference.
- **Sinon.js / `jest.mock` (JavaScript)** — intercepts module imports
  (Jest) or wraps individual functions/objects (Sinon) to replace their
  behavior while tracking calls — conceptually close to Python's
  patching approach, since JS modules are similarly reference-based.

## 3. "UI/E2E frameworks — Selenium and Playwright are covered elsewhere; what's actually different about Cypress?"

**Answer:**

- [Web Crawling at Scale §2](../database/web-crawling-at-scale.md#selenium-vs-playwright-the-actual-protocol-difference)
  already covers Selenium's WebDriver protocol vs. Playwright's direct
  DevTools Protocol connection — both drive the browser **externally**,
  as a separate process issuing commands to it.
- **Cypress** takes a genuinely different architecture: its test code
  runs **inside the browser itself**, in the same run-loop as the
  application under test, rather than driving the browser from the
  outside through a separate protocol.
- The payoff: automatic waiting and retrying on assertions (Cypress can
  directly observe the DOM's actual state in real time, since it's
  running alongside the app, not polling it externally) and direct
  access to real network traffic without a separate interception layer.
- The trade-off: that same in-browser architecture historically made
  testing across multiple tabs or multiple origins in one test
  genuinely harder than it is for an externally-driven tool like
  Playwright, which isn't bound to running inside any one page's context.
- **WebdriverIO** is a third option in the same external-driver family
  as Selenium — worth knowing by name as another WebDriver-protocol
  client, without needing deep separate coverage beyond that.

## 4. "BDD frameworks (Cucumber, Behave) — what problem do these actually solve, mechanically?"

```gherkin
Feature: Checkout discount
  Scenario: Premium member gets 20% off orders over $100
    Given a premium member with an empty cart
    When they add a $150 item and proceed to checkout
    Then the order total should reflect a 20% discount
```

```python
# Behave (Python) step definition -- maps the Gherkin line to real code
@when('they add a {price}$ item and proceed to checkout')
def step_impl(context, price):
    context.cart.add_item(price=float(price))
    context.checkout_result = context.checkout.process(context.cart)
```

**Answer:**

- **Gherkin** (`Given`/`When`/`Then`) is a structured, deliberately
  constrained English syntax readable by both non-technical stakeholders
  and automation tooling — the same scenario the decision-table example
  in
  [Manual Testing Fundamentals §2](manual-testing-fundamentals.md#2-beyond-boundaries-on-a-single-field-how-do-you-test-a-feature-with-several-fields-that-interact)
  would express as a table, written instead as a readable sentence a
  product owner can review directly.
- **Step definitions** are the actual translation layer — code (Cucumber
  for Java/JS, Behave for Python, SpecFlow for .NET) that matches each
  Gherkin line against a pattern (often a regex) and runs real test code
  when it matches.
- The genuine value: a shared, reviewable specification that both
  defines expected behavior *and* drives automated tests from the same
  source — reducing the gap between "what the business agreed to" and
  "what the automation actually checks."
- The real trade-off, worth naming honestly: the step-definition layer
  is itself code that needs maintaining, and a poorly organized set of
  step definitions (duplicated logic, overly specific steps that can't
  be reused) becomes its own maintenance burden — BDD frameworks don't
  remove the need for good test-code hygiene, they add a layer on top of
  it.

## 5. "API testing — Postman vs. a code-first approach like REST Assured or pytest + httpx?"

**Answer:**

- [QA Tools & the Path from Manual to Automation §2](qa-tools-and-the-sdet-path.md#2-what-does-api-testing-with-a-tool-like-postman-actually-verify-that-ui-testing-doesnt)
  already covers what API testing verifies and Postman's GUI-first
  workflow (collections, environments, Collection Runner).
- **REST Assured (Java)** offers a fluent `given().when().then()` DSL
  specifically for asserting on HTTP responses — API testing written and
  version-controlled as real code alongside the rest of a Java codebase,
  rather than living in a separate GUI tool's collection file.
- **pytest + `httpx`/`requests` (Python)** is the equivalent code-first
  approach without a dedicated API-testing framework at all — ordinary
  HTTP calls and assertions inside normal pytest functions, which is why
  most of this site's own backend code samples already test APIs this
  way without naming a separate "API testing tool."
- The real trade-off: a GUI tool like Postman is faster to get started
  with and better suited to manual/exploratory API testing by someone
  without a coding background; a code-first approach integrates
  naturally into the same CI pipeline and version-control history as
  the application code itself, which matters more as a team moves from
  manual API checks toward the automation path covered in
  [QA Tools §3](qa-tools-and-the-sdet-path.md#3-whats-the-actual-path-from-manual-tester-to-sdetautomation-engineer-and-what-changes-along-the-way).

## 6. "Mobile test automation — what's Appium, and is it a completely different tool family?"

**Answer:**

- Appium drives **native and hybrid mobile apps** (iOS, Android) using
  the same underlying WebDriver protocol family as Selenium — not a
  different mechanism, the same JSON-wire-protocol approach, extended to
  mobile UI elements instead of a desktop browser's DOM.
- This means a team already fluent in Selenium's external-driver model
  transfers that knowledge directly to mobile automation, rather than
  needing to learn a conceptually new testing paradigm — the main
  difference is the target (a mobile OS's accessibility tree instead of
  a browser's DOM), not the driving mechanism.

## 7. "Visual regression testing (Percy, Chromatic, Applitools) — what does this catch that functional tests structurally can't?"

**Answer:**

- A functional UI test checks that the right elements and text exist
  and behave correctly — it has no concept of what the page actually
  **looks like** rendered.
- Visual regression tools capture a screenshot of a component or page,
  then diff it — pixel-by-pixel, or with a smarter perceptual/DOM-aware
  comparison that tolerates trivial rendering noise — against an
  approved baseline image, flagging anything visually different for a
  human to review and either accept as the new baseline or reject as a
  real regression.
- This catches exactly the class of bug a functional test is blind to: a
  CSS change that breaks layout, an element silently overlapping
  another, a responsive breakpoint that stopped working — all while
  every functional assertion about "the button exists and is clickable"
  still passes perfectly.

## Summary: Test Type → Tooling

| Test type | Tools/frameworks | Deeper coverage |
|---|---|---|
| Unit | pytest, unittest, JUnit5/TestNG, Jest, Mocha+Chai+Sinon, Go `testing` | [Test Doubles & TDD](test-doubles-and-tdd.md) |
| UI/E2E | Selenium, Playwright, Cypress, WebdriverIO | [Web Crawling at Scale §2](../database/web-crawling-at-scale.md#selenium-vs-playwright-the-actual-protocol-difference), [Integration & E2E Testing](integration-and-e2e-testing.md) |
| API | Postman, REST Assured, pytest+httpx/requests, Supertest | [QA Tools §2](qa-tools-and-the-sdet-path.md#2-what-does-api-testing-with-a-tool-like-postman-actually-verify-that-ui-testing-doesnt) |
| BDD | Cucumber, Behave, SpecFlow | [Manual Testing Fundamentals](manual-testing-fundamentals.md) |
| Mobile | Appium | — same mechanism as Selenium, above |
| Visual regression | Percy, Chromatic, Applitools | — |
| Performance | JMeter, k6, Locust | [Non-Functional Testing §1](non-functional-testing.md#1-what-does-a-load-testing-tool-actually-do-mechanically-before-picking-jmeter-vs-k6-vs-locust) |
| Security | OWASP ZAP, Burp Suite | [Non-Functional Testing §2](non-functional-testing.md#2-what-does-testing-for-security-actually-mean-for-a-qa-engineer-as-opposed-to-a-developer-preventing-vulnerabilities-in-the-code) |
| Accessibility | axe, Lighthouse | [Non-Functional Testing §3](non-functional-testing.md#3-what-does-accessibility-testing-actually-check-and-why-cant-it-be-fully-automated) |
| Contract | Pact | [Contract Testing](contract-testing.md) |
| Property-based | Hypothesis | [Property-Based Testing](property-based-testing.md) |
| Mutation | mutmut, cosmic-ray | [Mutation Testing](mutation-testing.md) |
| Test management | TestRail, Zephyr, Jira | [QA Tools §1](qa-tools-and-the-sdet-path.md#1-test-management-tools-like-testrailzephyr-vs-a-bug-tracker-like-jira-whats-actually-different) |

---

## Code Samples

No dedicated code samples for this page.
