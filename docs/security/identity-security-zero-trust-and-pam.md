---
title: "Identity Security: Zero Trust & Privileged Access"
---

# Identity Security: Zero Trust & Privileged Access

[Authentication Patterns](../architecture/authentication-patterns.md)
already covers JWT, OAuth2, MFA, and SSO mechanics —
[Network Security Fundamentals §2](network-security-fundamentals.md#2-why-is-trust-the-internal-network-considered-a-broken-security-model-today-what-does-zero-trust-actually-mean-mechanically)
already covers zero trust's network-level architecture. This page
covers what sits on top of both: identity as the thing zero trust
actually verifies, and the specific discipline of protecting the
accounts that matter most — the privileged ones.

## 1. "Zero trust is usually explained as a network architecture — what does it actually mean at the identity layer specifically?"

**Answer:**

- Network-level zero trust (already covered) removes implicit trust
  based on *location* — being on the internal network no longer proves
  anything. Identity-level zero trust removes implicit trust based on
  *session* — successfully authenticating once no longer proves
  continued legitimacy for everything that follows.
- Concretely: **continuous verification** means re-checking identity and
  context signals on an ongoing basis (an unusual new device, a login
  from a geographically improbable location right after a previous one,
  a request to an unusually sensitive resource) rather than trusting a
  session token as permanent proof once issued at login.
- This reframes identity as effectively **the real perimeter** in a
  zero-trust architecture — once network location stops being a trust
  signal, verifying *who* is making a request, continuously, is what's
  actually left to secure the system on.

## 2. "MFA exists, but not all MFA is equally strong — what's actually different between the common methods?"

**Answer:**

- **SMS-based MFA** — a one-time code sent by text. The weakest common
  option: vulnerable to **SIM swapping** (an attacker social-engineers a
  mobile carrier into porting the victim's phone number to a new SIM
  card they control, intercepting the code), and SMS itself isn't
  encrypted end-to-end.
- **TOTP (Time-based One-Time Password)** apps (Google Authenticator,
  Authy) — generate a code from a shared secret and the current time,
  entirely offline, with no network transmission (and no SIM) to
  intercept at all. A meaningfully stronger default than SMS for the
  same "something you have" factor.
- **Hardware security keys** (YubiKey, and similar, using the FIDO2/WebAuthn
  standard) — the strongest common option: the private key material
  never leaves the physical device, and the protocol is specifically
  designed to resist phishing — a key cryptographically verifies it's
  talking to the genuine site's actual domain, so even a perfect
  look-alike phishing page can't successfully complete the
  authentication the way it could trick a human into typing in a TOTP
  code.
- The practical takeaway for a security-conscious design: MFA isn't a
  single checkbox — which factor is required matters, and SMS alone is
  increasingly treated as better-than-nothing rather than genuinely
  strong.

## 3. "What is Privileged Access Management (PAM), and why does it need to be a distinct discipline from regular access control?"

**Answer:**

- [Authorization Patterns](../architecture/authorization-patterns.md)
  already covers RBAC/ABAC for ordinary, everyday access control. PAM is
  specifically about the smaller set of **highly privileged** accounts —
  domain admins, database root, cloud account root/admin roles — where
  the consequence of compromise is disproportionately severe compared to
  an ordinary user account.
- **Just-in-time (JIT) access** — instead of a privileged account
  holding standing, always-on elevated permissions, access is granted
  temporarily, on request, for a specific task, and automatically
  revoked afterward. This shrinks the window during which a compromised
  privileged credential is actually useful to an attacker, compared to a
  permanently elevated account that's valuable to compromise at any
  moment.
- **Session recording and monitoring** for privileged sessions
  specifically (not applied uniformly to every account) — because the
  blast radius of a privileged session going wrong, maliciously or
  accidentally, justifies a level of scrutiny that would be excessive
  overhead applied to every ordinary user session.
- **Credential vaulting** — privileged credentials are stored in a
  dedicated secrets vault (see
  [Secrets Manager vs. Parameter Store](../cloud-devops/kms-secrets-and-cognito.md#secrets-manager-vs-parameter-store)
  for the general secrets-management mechanism) rather than known
  directly to any human, often with automatic rotation after each
  privileged session — so a privileged credential a human once typed in
  manually isn't a long-lived, memorized secret at all.

| Pros | Cons / Trade-offs |
|---|---|
| Continuous identity verification catches a hijacked session, not just a bad initial login | Meaningfully more overhead than trusting a session token for its full lifetime |
| Hardware security keys resist phishing in a way SMS/TOTP structurally can't | Physical device requirement — lost key means a real account-recovery process |
| Just-in-time privileged access shrinks the window a stolen credential is actually useful | Adds real friction/latency to legitimate privileged tasks that need to happen quickly |
| Credential vaulting removes long-lived, human-memorized privileged secrets entirely | Introduces a new, high-value target — the vault itself becomes critical infrastructure to protect |

---

## Code Samples

No dedicated code samples for this page.
