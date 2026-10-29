---
title: "Non-Functional Testing: Performance, Security & Accessibility"
---

# Non-Functional Testing: Performance, Security & Accessibility

Every testing type covered so far asks "does this feature do the right
thing." Non-functional testing asks a different question: does it do
the right thing *fast enough*, *safely enough*, and *for everyone who
needs to use it* — qualities a functionally perfect feature can still
completely fail on.

## 1. "What does a load testing tool actually do, mechanically, before picking JMeter vs. k6 vs. Locust?"

**Answer:**

- The core mechanism behind every load testing tool is the same: simulate
  many **virtual users** making requests concurrently, ramping the number
  up over time, while measuring response time, error rate, and
  throughput at each load level — looking for the point where the
  system's behavior degrades.
- **Load testing** — expected, normal-to-peak traffic, checking the
  system meets its performance targets under realistic conditions.
- **Stress testing** — deliberately pushing well past expected peak,
  specifically to find the actual breaking point and observe *how* the
  system fails (a clean, graceful degradation and recovery vs. a hard
  crash that needs manual intervention to recover from).
- **Soak testing** — sustained, moderate load held for an extended
  period (hours, not minutes) — built specifically to catch problems
  that only show up over time, like a slow [memory
  leak](../python/language-fundamentals/python-internals-and-advanced-oop.md#memory-leaks-what-they-actually-are-and-how-one-happens-even-with-a-garbage-collector)
  or a resource that's never properly released, invisible in a short
  burst test.
- The tools differ mainly in how virtual users are scripted and scaled,
  not in this underlying concept: JMeter uses a GUI-driven or XML test
  plan and runs on the JVM; k6 is scripted in JavaScript and built for
  CI integration and cloud-scale distributed load generation; Locust is
  scripted in Python, with virtual user behavior defined as ordinary
  Python code — the natural choice for a Python-heavy team that wants
  load-testing logic to live in the same language as the rest of the
  codebase.

## 2. "What does 'testing for security' actually mean for a QA engineer, as opposed to a developer preventing vulnerabilities in the code?"

**Answer:**

- The developer-prevention side of this (parameterized queries against
  SQL injection, output escaping against XSS, the actual mechanisms)
  is covered in
  [Database Security & Breach Prevention](../database/database-security-and-breach-prevention.md).
  Security *testing* is the adversarial-mindset complement: deliberately
  trying to break the application's security the way an attacker would,
  to confirm those preventive mechanisms actually hold up in practice.
- The **OWASP Top 10** is the standard reference list of the most common,
  highest-impact web application vulnerability categories (injection,
  broken authentication, sensitive data exposure, and others) — not
  something to memorize line by line, but worth knowing as the
  checklist-of-checklists a security-testing effort is usually measured
  against.
- Concretely, security testing means things like: trying to submit
  `' OR '1'='1` into every input field, attempting to access another
  user's data by changing an ID in a URL (**broken access control** —
  consistently one of the most common real findings), checking whether
  sensitive data appears unencrypted in a network request, and
  confirming a session token is actually invalidated after logout rather
  than remaining usable.
- Automated scanners (OWASP ZAP, Burp Suite) catch a real, broad class
  of these mechanically — but they don't replace a human adversarial
  tester for business-logic-specific vulnerabilities (a discount code
  that can be reused by manipulating a hidden field) that a generic
  scanner has no way to know to look for.

## 3. "What does accessibility testing actually check, and why can't it be fully automated?"

**Answer:**

- Accessibility testing verifies the application is actually usable by
  people with disabilities — screen reader users, users who navigate
  entirely by keyboard (no mouse), users with low vision relying on
  high contrast or zoomed text, and others.
- **WCAG (Web Content Accessibility Guidelines)** is the standard
  reference — organized around four principles worth knowing by name:
  content must be **Perceivable** (alt text for images, sufficient color
  contrast), **Operable** (every interactive element reachable and usable
  by keyboard alone, not just mouse/touch), **Understandable** (clear
  labels, predictable navigation), and **Robust** (works correctly with
  assistive technology like a screen reader).
- **Automated scanners** (axe, Lighthouse) catch the mechanically
  detectable subset well — missing alt text, insufficient color
  contrast, missing form labels — genuinely useful as a fast, cheap
  first pass.
- What automated tools **structurally can't** catch: whether the actual
  experience of using the page with a screen reader makes sense, whether
  keyboard focus moves in a logical, usable order through a complex
  interaction, whether an alt text that technically exists actually
  describes the image meaningfully. These require manual testing — often
  literally navigating the application with a screen reader and no
  mouse — the same "automation catches the mechanical subset, a human
  catches what requires actual judgment" pattern that shows up across
  every non-functional testing category on this page.

| Pros | Cons / Trade-offs |
|---|---|
| Load/stress/soak testing finds capacity limits and degradation patterns before real users do | Realistic virtual-user scripting is genuinely hard to get right — unrealistic load patterns give false confidence |
| Automated security scanners catch a broad class of common vulnerabilities fast and cheaply | Can't find business-logic-specific vulnerabilities a generic scanner has no way to anticipate |
| Automated accessibility scanners catch mechanically detectable issues (alt text, contrast) instantly | Can't judge actual usability with a screen reader or real keyboard-only navigation |
| k6/Locust integrate cleanly into CI for repeatable, scripted load tests | JMeter's GUI-first workflow is less naturally CI-friendly without extra tooling |

---

## Code Samples

No dedicated code samples for this page.
