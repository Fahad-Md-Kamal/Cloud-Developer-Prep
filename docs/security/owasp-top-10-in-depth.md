---
title: "The OWASP Top 10, In Depth"
---

# The OWASP Top 10, In Depth

Several categories on this list are already covered elsewhere on this
site in real depth — this page is the canonical map tying all ten
together, cross-linking to existing coverage where it exists and
filling in the categories that haven't had dedicated treatment yet:
insecure design, vulnerable components, software supply chain
integrity, and SSRF.

## The Ten Categories, at a Glance

| # | Category | Where it's covered |
|---|---|---|
| A01 | Broken Access Control | [Authorization Patterns §3](../architecture/authorization-patterns.md#3-resource-level-authorization) |
| A02 | Cryptographic Failures | [Cryptography Fundamentals](cryptography-fundamentals.md) |
| A03 | Injection | [Security Hardening §1](../architecture/security-hardening.md#1-input-validation-and-injection-prevention) |
| A04 | Insecure Design | This page, §1 |
| A05 | Security Misconfiguration | [AWS Organizations & Control Tower](../cloud-devops/aws-organizations-and-control-tower.md) |
| A06 | Vulnerable & Outdated Components | This page, §2 |
| A07 | Identification & Authentication Failures | [Authentication Patterns](../architecture/authentication-patterns.md) |
| A08 | Software & Data Integrity Failures | This page, §3 |
| A09 | Security Logging & Monitoring Failures | [Threat Detection & Monitoring §1](threat-detection-and-monitoring.md#1-security-audit-logging) |
| A10 | Server-Side Request Forgery (SSRF) | This page, §4 |

## 1. "What's 'insecure design,' and how is it different from a specific implementation bug like injection?"

**Answer:**

- Every other category on this list describes a **flaw in how something
  was built** — a missing input check, a weak hash. Insecure design
  describes a flaw in **what was decided to build in the first place** —
  the feature works exactly as designed, and the design itself is the
  vulnerability.
- Concrete example: a password-reset flow that emails a reset link with
  no expiration and no single-use enforcement isn't a coding bug — every
  line of code does exactly what it was designed to do. The design
  itself — a permanently valid, reusable reset link — is the actual
  flaw.
- The fix for a design flaw is architectural, not a patch — threat
  modeling *before* building a sensitive feature (walking through "how
  would someone misuse this, specifically," not just "does this do what
  we want") catches this category before it ships, in a way that code
  review of the finished implementation often can't.

## 2. "What does 'vulnerable and outdated components' actually mean as a practical risk, not just 'update your dependencies'?"

**Answer:**

- Modern applications are built on a large tree of third-party
  dependencies, each with its own dependencies — a known vulnerability
  in any package anywhere in that tree, even one your own code never
  directly imports, is a real attack surface the moment it's reachable
  from your running application.
- The practical mechanism: a **Software Bill of Materials (SBOM)** — an
  explicit, generated inventory of every component and version actually
  in a build — is what makes it possible to even ask "are we affected by
  this newly disclosed CVE" quickly, instead of manually auditing a deep
  dependency tree by hand when a new vulnerability is announced.
- Automated dependency scanning (Dependabot, Snyk, and similar) in CI is
  the operational answer — flagging known-vulnerable versions
  automatically on every build, rather than relying on someone
  remembering to check.

## 3. "What's a 'software and data integrity failure,' and how does this connect to supply chain attacks?"

**Answer:**

- This category covers trusting something — code, a CI/CD pipeline step,
  a software update — **without verifying its integrity**, leaving an
  opening for it to be tampered with between where it was built and
  where it actually runs.
- A **supply chain attack** is the real-world consequence: compromising
  a trusted upstream component (a popular open-source package, a build
  tool, a CI pipeline's own dependencies) so that malicious code rides
  along inside something thousands of downstream applications pull in
  and trust automatically.
- This is the exact mechanism [digital signatures](cryptography-fundamentals.md#4-whats-a-digital-signature-and-how-is-it-different-from-encryption)
  defend against when applied to software distribution: verifying a
  package or update is signed by its genuine publisher, and that
  signature hasn't been tampered with, before trusting and running it —
  the same integrity+authenticity guarantee covered there, applied here
  to code instead of a network connection.

## 4. "What's SSRF, and why does it specifically matter more in cloud environments?"

```python
# Vulnerable: the app fetches whatever URL the user supplies
@app.post("/fetch-preview")
def fetch_preview(url: str):
    return requests.get(url).text  # user controls the destination entirely
```

**Answer:**

- **Server-Side Request Forgery** — an attacker gets the *server* to
  make a request on their behalf to a destination the attacker chose,
  not the application developer. In the snippet above, nothing stops a
  user from supplying an internal URL instead of a real external one.
- This matters disproportionately in cloud environments because of
  **instance metadata endpoints** — a fixed, internal-only address
  (169.254.169.254, already covered in
  [Instance Profiles and IMDSv2](../cloud-devops/aws-accounts-and-iam.md#instance-profiles-and-imdsv2))
  that often returns temporary credentials for whatever role the
  instance is running as. A server vulnerable to SSRF can be tricked
  into fetching that internal URL on the attacker's behalf, handing over
  real, live cloud credentials the attacker was never supposed to reach
  — one of the most consequential real-world SSRF outcomes seen in
  actual breaches.
- Mitigation: never let user input directly determine a server-side
  request's destination without a strict allowlist, and specifically
  block the ability for an application server to reach internal/metadata
  addresses at all from a code path that handles user-supplied URLs.

---

## Code Samples

No dedicated code samples for this page.
