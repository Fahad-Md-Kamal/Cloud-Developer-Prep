---
title: "Chapter 4: Authentication, Authorization, and Security Best Practices"
---

# Chapter 4: Authentication, Authorization, and Security Best Practices

Authentication, authorization, and the hardening/monitoring that sits around
both — each as a question you should be able to answer cold, with the
trade-offs named explicitly, not just the upside.

---

## Part 1: Authentication

### 1. JWT Design and Security

**"How do you design JWTs so they're actually safe to use for stateless auth?"**

```python
import jwt
from datetime import datetime, timedelta

def create_access_token(user_id: str, roles: list[str], minutes: int = 15) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=minutes),
        "iss": "api-service",
        "aud": ["api"],
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
```

**Answer:** Use RS256 (asymmetric) over HS256 for anything beyond a single
trusted service — verifying a token only needs the public key, so services
that never issue tokens also never hold the signing key. Keep access tokens
short-lived (5–15 minutes) paired with a rotating refresh token, so a stolen
access token has a small blast-radius window. Always pin acceptable
algorithms and reject `alg=none` — a real, well-documented vulnerability
class comes from attackers re-signing with `none` or downgrading an RS256
check to HS256 using the public key as an HMAC secret. Validate `iss`,
`aud`, `exp`, and `nbf` on every verify, not just on decode.

**Likely follow-up — "you can't revoke a JWT once it's issued — how do you
handle a compromised token before it expires?"** Short expirations shrink
the window by design. For anything that needs true revocation, keep a
denylist keyed by `jti` checked at verify time, or track a per-user "token
version" that invalidates every previously issued token on password change
or logout-all.

| Pros | Cons / Trade-offs |
|---|---|
| No DB round trip to verify — scales horizontally with no shared session store | Can't be revoked before expiry without extra infra (denylist or version check) |
| Any service holding the public key can verify independently | Payload is base64, not encrypted — never put secrets in claims |
| Claims (roles, tenant) travel with the token, no extra lookup | Token size grows with claims — larger than a session ID on every request |

### 2. OAuth2 Flow Selection

**"Which OAuth2 flow do you pick for a SPA, a backend service, and a CLI tool — and why does it matter?"**

```python
# Authorization Code + PKCE -- the only flow a public client (SPA/mobile) should use
code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip("=")
# code_challenge goes out with the initial redirect; code_verifier is only
# sent on the final token exchange, so a stolen auth code alone is useless
```

**Answer:** The right flow depends on who's asking and whether they can
keep a secret.

| Flow | Use it for | Why |
|---|---|---|
| Authorization Code + PKCE | SPA, mobile app | Public client, can't safely store a client secret; PKCE binds the code exchange to the party that started it |
| Client Credentials | Service-to-service | No user in the loop; narrow scopes + IP allowlisting replace user consent |
| Device Code | CLI tools, TVs, headless devices | No browser on the device itself; user authorizes from a second device |
| Implicit | Nothing — deprecated | Token exposed directly in the URL fragment; migrate any legacy use to PKCE |

**Likely follow-up — "what stops a malicious app from registering a
redirect URI and stealing the code?"** Exact `redirect_uri` matching (no
wildcards), plus PKCE — so even an intercepted authorization code can't be
exchanged for a token without the original verifier.

### 3. Multi-Factor Authentication

**"How would you roll out MFA, and what are the real trade-offs between TOTP, SMS, and WebAuthn?"**

```python
import pyotp

def setup_totp(user_id: str, issuer: str) -> tuple[str, str]:
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user_id, issuer_name=issuer)
    return secret, uri  # secret stored encrypted; uri renders as a QR code

def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)
```

**Answer:** TOTP is the practical default — free, works offline, no
carrier dependency. SMS is the weakest option (SIM-swap and SS7
interception are real, not theoretical) — keep it only as a rate-limited
fallback, never the only factor offered. WebAuthn/FIDO2 hardware keys are
strongest — phishing-resistant because the credential is bound to the
origin — but carry real cost and onboarding friction. Ship backup codes and
an audited break-glass path regardless of which factors you support; "lost
my phone" is a support-ticket certainty at scale.

| Pros | Cons / Trade-offs |
|---|---|
| TOTP: free, offline, no telecom dependency | Still phishable — a fake login page can relay the code to the real one in real time |
| SMS: zero setup friction for users | SIM-swap/SS7 interception make it the weakest factor; fallback only |
| WebAuthn/FIDO2: phishing-resistant, bound to the origin | Hardware cost and onboarding friction; still needs a non-hardware fallback path |

### 4. Enterprise SSO Integration

**"Walk me through validating an incoming SAML/OIDC assertion — what goes wrong if Just-in-Time provisioning is sloppy?"**

```python
def validate_assertion(assertion, expected_issuer: str, expected_audience: str) -> bool:
    return (
        assertion.issuer == expected_issuer
        and expected_audience in assertion.audiences
        and assertion.not_before <= now() <= assertion.not_on_or_after
        and assertion.signature_is_valid()
    )
```

**Answer:** Validate signature, issuer, audience, and expiry on every
assertion, and enforce HTTPS on the ACS/callback endpoint. Map external
attributes through an explicit allowlist — never trust arbitrary claims
from the identity provider as-is. Just-in-Time provisioning (auto-creating
an account on first login) is convenient but dangerous the moment it
defaults to anything above least privilege: a misconfigured IdP or a bug in
attribute mapping can hand an elevated role to every one of the identity
provider's users the first time they log in.

**Likely follow-up — "what about logout?"** Configure SLO (SAML) or
OIDC RP-initiated logout and clean up the session server-side — a
client-side-only logout leaves the session valid at the identity provider.

---

## Part 2: Authorization

### 5. Role-Based Access Control (RBAC)

**"How do you design a role hierarchy that doesn't turn into permission sprawl?"**

```python
class Role:
    def __init__(self, name: str, permissions: set[str], parent: "Role | None" = None):
        self.name = name
        self.permissions = permissions
        self.parent = parent

    def all_permissions(self) -> set[str]:
        perms = self.permissions.copy()
        return perms | self.parent.all_permissions() if self.parent else perms
```

**Answer:** Keep a small, actively owned role catalog rather than a role
per team's ad hoc request. Default deny when a check is ambiguous, enforce
least privilege, and separate duties so no single role holds two
permissions that should require two people (e.g. "approve payment" and
"create vendor"). Run periodic access reviews on high-risk roles instead of
assuming grants stay correct forever — they don't.

| Pros | Cons / Trade-offs |
|---|---|
| Simple mental model — one role, one fixed permission set | Coarse-grained; can't express "only during business hours" or "only for this tenant" |
| Easy to audit — a role's permissions are a readable list | Role explosion if every edge case becomes a new role instead of composition |
| Fast authorization checks — one lookup | Permission sprawl over time without an active owner pruning the catalog |

### 6. Attribute-Based Access Control (ABAC)

**"When does RBAC stop being enough, and what does ABAC give you that RBAC can't?"**

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class ABACPolicy:
    name: str
    condition: Callable[[dict], bool]  # never eval() a raw policy string
    effect: str  # "ALLOW" or "DENY"

def is_authorized(policies: list[ABACPolicy], context: dict) -> bool:
    for policy in policies:
        if policy.condition(context):
            return policy.effect == "ALLOW"
    return False  # default deny
```

**Answer:** RBAC answers "what role does this user have." ABAC answers
"given this user's attributes, this resource's attributes, and the current
context (time, location, device), is this specific action allowed" — needed
once rules genuinely depend on more than role, e.g. "marketing can read
customer data during business hours from a corporate device, but not from
a personal device at 2am." Normalize attribute names and types and document
their sources, prefer deny-overrides when policies conflict, and cache
low-volatility attributes while keeping short TTLs on ones that shift (IP
reputation, device risk).

**Likely follow-up — "what's wrong with literally `eval()`-ing a policy
condition string, the way a naive implementation does it?"** Arbitrary
code execution the moment the policy source isn't fully trusted — a config
file or a database row someone else can edit is enough. Use a restricted
expression evaluator or an established policy engine (Cedar, OPA/Rego,
XACML) instead of `eval`.

### 7. Resource-Level Authorization

**"How do you authorize access to one specific resource — not just a role — without hitting the database on every check?"**

```python
def can_access(db, user_id: str, document_id: str, action: str) -> bool:
    doc = db.get_document(document_id)
    if doc is None:
        return False
    if doc.owner_id == user_id:
        return True
    return db.has_permission(document_id, user_id, action)  # explicit grant/ACL
```

**Answer:** Check ownership first — cheapest and most common case — then
fall back to an explicit grant/ACL table for shared access. Cache the
resulting allow/deny decision with a short TTL, invalidated on ACL change
rather than re-derived on every read, and expose a bulk/batch decision
endpoint for list views so a 50-row list doesn't mean 50 authorization
round-trips.

**Likely follow-up — "what happens if the permission changes mid-TTL?"**
A stale-cache window — keep the TTL short and invalidate on write rather
than relying purely on expiry, and log every allow/deny with actor,
resource, and action so a stale decision is at least auditable after the
fact.

### 8. API Key Management and Scoping

**"How do you design an API key system so one leaked key doesn't hand out the keys to the kingdom?"**

```python
import secrets, hashlib

def create_api_key(scopes: list[str]) -> tuple[str, str]:
    key_id = secrets.token_urlsafe(16)
    secret = secrets.token_urlsafe(32)
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    store_api_key(key_id, secret_hash, scopes)  # only the hash is persisted
    return key_id, secret  # plaintext returned exactly once
```

**Answer:** Store only a hash of the secret — never the plaintext — and
show the plaintext exactly once, at creation. Scope every key narrowly
(default read-only, explicit expiration) rather than issuing an all-access
key. Bind to IP ranges or service accounts where practical, and monitor
usage for anomalies (sudden volume or geography change). Automate rotation
and have a fast revoke-on-compromise path with blast-radius analysis — know
which systems a key can touch before you need that answer under pressure.

---

## Part 3: Security Hardening

### 9. Input Validation and Injection Prevention

**"Design input validation for an API that accepts user content, and explain how parameterized queries actually stop SQL injection."**

```python
from pydantic import BaseModel, validator
import bleach

class DocumentUpload(BaseModel):
    title: str
    content: str

    @validator("content")
    def sanitize(cls, v):
        return bleach.clean(v, tags=["p", "br", "strong", "em"], strip=True)
```

```python
from sqlalchemy import text

query = text("SELECT id, title FROM documents WHERE owner_id = :uid AND type = :t")
db.execute(query, {"uid": user_id, "t": doc_type})  # bound params, not string-built SQL
```

**Answer:** Validate at the API boundary before business logic ever sees
the input — whitelist allowed values/formats, reject unknown fields,
enforce size limits on payloads/arrays/uploads, and don't echo raw rejected
input back into logs or error messages. For injection specifically:
parameterized queries work because the query structure and the data are
sent to the database as two separate things — user input can never be
reinterpreted as SQL syntax no matter what characters it contains. An ORM
handles this by default for normal queries, but the risk returns the
moment you concatenate user input into a raw fragment — most commonly
`ORDER BY`/`LIMIT`, which many ORMs don't parameterize the same way; check
those against an explicit whitelist of allowed columns. Least-privilege
database accounts (no DDL at runtime) limit the damage if something still
gets through.

**Likely follow-up — "what about NoSQL?"** Same idea: validate document
structure and types before insertion, and whitelist which operators callers
may send. MongoDB injection usually comes from passing a raw user-supplied
dict straight into a query filter, letting the caller sneak in an operator
like `$where` or `$ne` where a plain value was expected.

### 10. Cross-Site Scripting (XSS) Protection

**"Should you sanitize on input or escape on output — and why does it matter which one you pick?"**

```python
import bleach

def sanitize_rich_text(html: str) -> str:
    return bleach.clean(html, tags=["p", "b", "i", "a"], attributes={"a": ["href"]}, strip=True)
```

**Answer:** Escape on output, by default, per sink (HTML, JS, CSS, URL
context) — this is what template engines with auto-escaping already do,
and it's safe because it happens right before the data reaches a place
that could interpret it as code. Sanitize on input only for the narrow
case where you must store and later render actual rich-text HTML (a
comment box with bold/italic) — allowlist sanitization, never a blocklist.
A Content Security Policy is the backstop for anything that slips through:
disallow inline scripts, prefer nonce-based CSP when inline is
unavoidable, and strip dangerous URL schemes (`javascript:`, `data:`) from
user-supplied links.

| Pros | Cons / Trade-offs |
|---|---|
| Output encoding: safe by default, applied automatically by most template engines | Wrong for content that's genuinely meant to render as HTML |
| Input sanitization: lets you store/render limited rich text at all | Easy to get the allowlist wrong — strip too little and you've built an XSS vector |
| CSP as a backstop: blocks exploitation even if a sanitizer has a bug | Real maintenance cost — a strict CSP breaks the first unreviewed third-party script |

### 11. Security Headers and HTTPS Enforcement

**"What does a solid security-headers baseline look like, and what does each header actually stop?"**

```python
response.headers.update({
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": f"default-src 'self'; frame-ancestors 'none'; script-src 'self' 'nonce-{request_nonce}'",
})
```

**Answer:** Each header stops a specific, named attack. HSTS stops
protocol-downgrade/SSL-stripping by forcing HTTPS at the browser level.
`frame-ancestors 'none'` (or `X-Frame-Options: DENY`) stops clickjacking.
`X-Content-Type-Options: nosniff` stops the browser from executing a file
as a different content type than declared. A strict CSP is the main XSS
backstop — but only if you avoid `unsafe-inline`, which defeats most of
CSP's purpose since it's exactly what lets an injected `<script>` execute.
Use a per-request nonce for the rare legitimate inline script instead.

**Likely follow-up — "why would you ever exclude a subdomain from HSTS
preload?"** If any subdomain still serves plain HTTP, preload breaks it
for every visitor, permanently — removal from browsers' preload lists is
slow and not guaranteed.

---

## Part 4: Threat Detection and Monitoring

### 12. Rate Limiting and DDoS Protection

**"Design rate limiting that's fair to real users but stops brute-force and scraping."**

```python
async def is_allowed(redis, key: str, limit: int, window_seconds: int) -> bool:
    pipe = redis.pipeline()
    now = time.time()
    pipe.zremrangebyscore(key, 0, now - window_seconds)  # drop entries outside window
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds)
    _, count, *_ = await pipe.execute()
    return count <= limit
```

**Answer:** Layer limits — per IP, per authenticated user/key, and per
endpoint class (auth endpoints much tighter than read endpoints) — because
one global limit either blocks legitimate bursts or lets a distributed
attacker through. Sliding-window or token-bucket algorithms are fairer than
fixed windows, which allow a full quota again right at the window boundary.
Return `429` with `Retry-After` so well-behaved clients back off correctly.
Heuristics like "block `curl`/`python-requests` user agents" are weak —
trivially spoofed — treat them as a signal to tighten, never as the sole
gate.

| Approach | Pros | Cons |
|---|---|---|
| Fixed window | Simple, cheap to implement | Allows up to a 2x burst right at the window boundary |
| Sliding window (log) | Accurate, no boundary burst | More storage — tracks individual request timestamps |
| Token bucket | Allows legitimate bursts while capping average rate | Needs tuning (bucket size + refill rate) to feel right |

### 13. Security Audit Logging

**"What must a security audit log capture, and what must it never contain?"**

```python
def log_security_event(event_type, user_id, ip, resource, outcome, correlation_id):
    logger.info(
        "security_event", event_type=event_type, actor=user_id, ip=ip,
        resource=resource, outcome=outcome, correlation_id=correlation_id,
    )  # never log passwords, tokens, or raw PII
```

**Answer:** Standardize fields across every event — actor, subject,
action, resource, outcome, timestamp, correlation ID — so events are
queryable across services, not just readable one at a time. Never log
passwords, tokens, or raw PII; hash or tokenize identifiers where the raw
value isn't actually needed. Ship logs to a centralized, access-restricted
store with integrity protection, since the audit log is itself a target
once an attacker is inside. Predefine alert rules — repeated auth
failures, privilege escalation, key rotation, policy denials — a log
nobody's alerting on is just storage.

### 14. Anomaly Detection and Behavior Analytics

**"How would you detect account-takeover-style behavior without drowning the security team in false positives?"**

```python
def risk_score(activity, baseline) -> float:
    score = 0.0
    if activity.ip not in baseline.known_ips: score += 0.25       # geographic anomaly
    if is_impossible_travel(activity, baseline): score += 0.30
    if is_off_hours(activity.timestamp, baseline): score += 0.15
    if activity.device_id not in baseline.known_devices: score += 0.20
    return min(score, 1.0)
```

**Answer:** Build a baseline per user (typical login times, locations,
devices) rather than one global threshold — "normal" varies hugely by role
and person. Correlate multiple weak signals instead of triggering on any
single one — impossible travel plus a new device plus an off-hours login
is a strong signal; any one alone usually isn't. Route medium-risk activity
to step-up authentication rather than an outright block, and reserve hard
blocks or session quarantine for high-confidence cases. Tune thresholds
against precision/recall with actual security-operations feedback, not a
model's default sensitivity — a detector nobody trusts gets its alerts
ignored within a month.

**Likely follow-up — "isn't machine learning overkill here?"** Often, yes,
to start — a handful of correlated rule-based signals (new device + new
country + off-hours) catches most real cases and is far easier to explain
and debug than an opaque model. Reach for ML once you have enough labeled
incident data to validate that it's actually doing better.

### 15. Vulnerability Management and Security Testing

**"How do you keep dependency and code vulnerabilities from piling up silently?"**

```bash
bandit -r src/ -f json          # SAST: code-level issues
safety check -r requirements.txt --json   # dependency vulnerabilities
```

**Answer:** Automate SAST, dependency scanning, and container image
scanning in CI so they run on every change, not as an occasional manual
exercise. Prioritize by actual risk — a critical CVE in an internet-facing
service beats a medium finding in an internal batch job — and track
remediation to closure, not just detection. A scanner that only produces
reports nobody acts on adds process without adding security.

---

## Code Samples

Runnable examples in `code_samples/chapter-4/`:

- `jwt_authentication_system.py` — RS256 JWT issuing/verification, refresh token rotation, key rotation, token blacklisting
- `oauth2_provider.py` — Authorization Code + PKCE and Client Credentials flows as a FastAPI app, scope validation, token introspection

```bash
pip install pyjwt cryptography redis fastapi uvicorn pydantic
python code_samples/chapter-4/jwt_authentication_system.py
uvicorn code_samples.chapter-4.oauth2_provider:app --reload --port 8001
```

---

## Summary

1. **Authentication** — JWT, OAuth2, MFA, and SSO each solve a different
   piece of "who is this"; the recurring theme is short-lived credentials,
   strict validation of every claim/assertion, and least-privilege
   defaults for anything auto-provisioned.
2. **Authorization** — RBAC for coarse role-based access, ABAC when
   decisions genuinely depend on context, resource-level checks for
   per-object sharing, and API keys scoped narrowly enough that a leak
   isn't catastrophic.
3. **Hardening** — input validation at the edge, parameterized queries,
   output encoding over blocklist sanitization, and a security-headers
   baseline are cheap, high-leverage defenses against the most common
   attack classes.
4. **Detection** — rate limiting, audit logging, anomaly detection, and
   vulnerability scanning are what turn "we got breached and found out
   three months later" into "we caught it within the hour."
