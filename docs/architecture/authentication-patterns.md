---
title: "Authentication Patterns"
---

# Authentication Patterns

JWT is one mechanism among many for proving *who* is making a
request, not the whole topic — this page opens with the full
landscape, then goes deep on the four mechanisms that come up most in
practice: JWT design, OAuth2 flow selection, MFA, and enterprise SSO.
For *what they're allowed to do* once authenticated, see
[Authorization Patterns](authorization-patterns.md).

## 1. The Authentication Mechanism Landscape

**"JWT can't be the only way to authenticate a request — what else is actually out there?"**

| Mechanism | How it works | Best for | Key benefit | Key drawback |
|---|---|---|---|---|
| Session + cookie | Server stores session state; browser holds an opaque session ID cookie | Traditional server-rendered web apps, one backend | Instant server-side revocation; the cookie itself carries no data to leak | Needs a shared session store to scale across servers; CSRF needs its own defenses |
| JWT | Signed, stateless token carrying claims; verified with a key, no DB lookup | Stateless APIs, microservices, mobile backends | Scales with zero shared state — any service holding the public key verifies independently | Can't revoke before expiry without extra infrastructure ([§2](#2-jwt-design-and-security)) |
| OAuth2 + OIDC | Delegated authorization (OAuth2) plus an identity layer on top (OIDC) issuing an ID token | "Log in with Google," third-party API access without sharing a password | The app never sees or stores the user's real password; scopes are fine-grained and revocable | Genuinely complex to implement correctly; the wrong flow choice is a real vulnerability ([§5](#5-oauth2-flow-selection)) |
| SAML | XML-based assertion exchanged between an Identity Provider and Service Provider | Enterprise SSO into legacy/internal systems | Mature and battle-tested at large-enterprise scale; not limited to browser-based apps | Verbose XML, harder to debug than OIDC's JSON |
| API keys | A long-lived static secret sent with every request, checked against a stored value | Service-to-service calls, third-party integrations, internal tooling | Trivial to implement and understand | No real user identity, no built-in expiry — a leaked key is valid until someone manually revokes it |
| HTTP Basic Auth | Username:password base64-encoded in every request's header | Quick internal tools, scripts, or layered behind something like mTLS | Zero setup, supported everywhere | Credentials sent on every single request; only ever safe over TLS, no revocation without changing the password |
| mTLS (mutual TLS) | Client and server each present and verify an X.509 certificate during the TLS handshake | Service-to-service in a zero-trust mesh, high-assurance device auth | Authenticates at the transport layer before any application code runs | Certificate issuance and rotation is real, ongoing operational overhead |
| HMAC request signing | Client signs each request with a shared secret; server recomputes the signature and compares | Public APIs needing tamper-proof requests (AWS SigV4, webhooks) | Proves identity *and* that the request body wasn't altered in transit | Clock-skew/replay handling adds complexity; the shared secret still needs protecting |
| Kerberos | Ticket-based mutual authentication via a trusted third-party Key Distribution Center | Internal enterprise networks, Windows Active Directory domains | No password crosses the network after the initial ticket is issued | Needs tight clock sync; the KDC is a single point of failure if it's down |
| WebAuthn / passkeys | Public-key cryptography bound to the site's real origin; the private key never leaves the device | Passwordless primary login, phishing-resistant consumer and enterprise auth | Nothing reusable to steal in a server breach; cryptographically can't be phished | Hardware/platform support is still uneven on older devices |
| Magic links / email OTP | A one-time link or code sent to a verified channel (email/SMS), no password at all | Low-friction consumer signup, infrequent-login apps | Nothing to forget, reuse across sites, or leak in a password-database breach | Only as secure as the delivery channel — a compromised inbox or SIM is a full account takeover |

**The question underneath "why not just sessions?" — Session vs. JWT:**

- Both solve the same problem (prove who's making a *later* request
  after they already proved who they are once) with opposite
  trade-offs: a session keeps the truth on the server and hands the
  client a meaningless pointer to it; a JWT puts the truth *inside*
  the token itself, so no server-side lookup is needed to trust it.
- **Session wins** when instant revocation genuinely matters (ban a
  user, force logout everywhere right now) and there's a reasonably
  small number of backends that can share one session store.
- **JWT wins** once there are multiple independent services that each
  need to verify a request without all sharing access to the same
  session store — the standard shape of a microservices backend or a
  mobile app talking to several APIs.
- **Most real production systems use both, for different layers**: a
  session cookie for the browser-facing web app's own login, and a
  JWT for the backend APIs/microservices behind it — picking one
  doesn't mean abandoning the other everywhere.

**Interview point:** naming the actual trade-off (revocation vs.
statelessness) is what separates a strong answer from reciting "JWT is
stateless, sessions are stateful" as an unexplained fact — the
follow-up "so why would anyone still use sessions" is exactly testing
whether that trade-off was understood or just memorized.

## 2. JWT Design and Security

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

**Answer:**

- RS256 (asymmetric) over HS256 beyond a single trusted service —
  verifying only needs the public key, so a verifying service never
  holds the signing key.
- Short-lived access tokens (5-15 min) + rotating refresh token —
  shrinks a stolen token's usable window.
- Pin acceptable algorithms, reject `alg=none` — attackers re-sign
  with `none`, or downgrade RS256 to HS256 using the public key as an
  HMAC secret.
- Validate `iss`/`aud`/`exp`/`nbf` on every verify, not just decode.

**Follow-up — "you can't revoke a JWT before it expires — then what?"**
Short expirations shrink the window by design. For true revocation: a
denylist keyed by `jti`, or a per-user "token version" that
invalidates every prior token on password change/logout-all.

| Pros | Cons / Trade-offs |
|---|---|
| No DB round trip to verify — scales with no shared session store | Can't revoke before expiry without extra infra |
| Any service holding the public key verifies independently | Payload is base64, not encrypted — never put secrets in claims |
| Claims travel with the token, no extra lookup | Token size grows with claims — bigger than a session ID |

## 3. Defending Against Token Theft

**"A hacker steals a valid JWT from the browser and replays it — the server has no way to tell it apart from the real user's request. How do you actually defend against that?"**

```python
# Store the token where JS (and therefore XSS) can't read it at all
response.set_cookie(
    "access_token", token,
    httponly=True,    # unreadable by JavaScript
    secure=True,       # HTTPS only
    samesite="strict", # not sent on cross-site requests
)
```

**Answer:**

- A valid signature only proves the token wasn't forged and hasn't
  expired — it says nothing about whether whoever is presenting it is
  actually who it was issued to. That's the real gap a stolen token
  walks through: JWT auth is **bearer** auth by default, whoever holds
  the token is trusted.
- **Fix the theft vector first.** A token "stolen from the browser"
  was almost always readable by JavaScript — sitting in `localStorage`
  or a non-`httponly` cookie, exactly the kind of value an XSS payload
  can exfiltrate. An `httponly`/`secure`/`samesite=strict` cookie (as
  above) can't be read by injected JS at all, closing the most common
  real-world theft path before any of the following even matters.
- **`samesite` is a separate, related defense — CSRF, not theft.**
  `httponly`/`secure` stop the token from being *read*; `samesite`
  controls when the browser is willing to *send* it automatically.
- Without it, a malicious page on another site could make the
  victim's browser silently attach their real cookie to a request that
  page itself triggered.
- `strict` refuses to send the cookie on any request that didn't
  originate from your own site, closing that gap.
- **Bind the token to the client, not just the bearer** — the direct
  fix for "what if it still leaks anyway":
    - **DPoP** (Demonstrating Proof-of-Possession) — the client signs
      each request with a private key it holds; the server checks that
      signature against the key bound to the token at issuance. A
      copied token is useless without that key.
    - **mTLS-bound tokens (RFC 8705)** — the access token is
      cryptographically tied to the TLS client certificate used to
      obtain it; replaying the token from a different client fails the
      binding check.
- **Shorten the window, then detect reuse on the refresh token.**
  Short-lived access tokens (above) already limit how long a stolen
  token works. Pairing that with **refresh token rotation + reuse
  detection** — if a refresh token is ever presented twice, the server
  assumes theft and revokes the *entire* token family immediately, not
  just that one token — turns "stolen once" into "caught on the very
  next use."
- **Anomaly detection as a backstop.** The same token suddenly hitting
  from a different country, device, or IP pattern than its normal
  usage is a cheap, real signal — forcing step-up re-authentication
  there catches theft that binding/rotation alone wouldn't.
- **Narrow scopes limit the damage**, not the theft itself — a stolen
  token that can only read one resource is a smaller incident than one
  with full account access, which is why minimal scope-per-token is
  worth doing even with the defenses above already in place.

| Defense | Stops theft, or just limits damage after? | Cost |
|---|---|---|
| `httponly`/`secure` cookies | Stops the most common theft vector (XSS reading the token) | Free — a storage choice |
| DPoP / mTLS-bound tokens | Makes a stolen token unusable without the bound key/cert | Real client + server implementation work |
| Short expiry + refresh rotation | Limits the window; reuse detection catches theft fast | Low — standard OAuth2 practice |
| Anomaly detection | Limits damage after the fact | Needs usage-pattern infrastructure |
| Narrow scopes | Limits damage, doesn't prevent theft | Free — a design discipline |

**Interview point:** "can you fully prevent JWT theft?" is a bit of a
trick question — bearer tokens are inherently stealable by definition;
the honest answer is **layered defense**: make theft harder (secure
storage), make a stolen token less useful (binding), and catch it fast
when it happens anyway (rotation + reuse detection, anomaly detection)
— not any single mechanism claiming to solve it outright.

## 4. Other JWT Attack Scenarios Beyond Theft

**"Theft-and-replay assumes the attacker gets hold of an intact,
legitimate token. What if they never steal one at all?"**

**Algorithm/signature forgery — the attacker makes their own token:**

- The `alg=none` attack — some libraries trust the `alg` field *inside
  the token itself* to decide how to verify it. Strip the signature,
  set `alg: none`, and a naive verifier skips verification entirely.
- RS256→HS256 confusion — if a server accepts both algorithms without
  pinning which one a given token must use, an attacker who knows the
  RS256 public key (often published openly via a **JWKS** endpoint —
  a JSON Web Key Set, the standard JSON document of public keys an
  issuer hosts so others can verify its tokens, typically at
  `/.well-known/jwks.json`) can sign a forged token with HS256, using
  that public key as the HMAC secret. The server's own public key
  becomes the attacker's signing key.
- `kid`/`jku` header injection — some implementations let the token
  itself specify which key to verify against via its `kid` (which key
  *in* the JWKS) or `jku` (a URL to a JWKS document entirely). A
  server that blindly fetches whatever key a token's `jku` header
  points to will happily "verify" a token against a key the attacker
  controls.
- **Defense:** pin the expected algorithm server-side — never let the
  token's own header pick its verification method — and never fetch a
  verification key from a URL the token itself supplies.

**Silent leakage through your own infrastructure — nobody "stole" anything:**

- A token passed as a URL query parameter ends up in browser history,
  server access logs, and the `Referer` header sent to any third-party
  script or image loaded on that page.
- A token in the `Authorization` header gets captured whole by error
  trackers (Sentry, Datadog) or API gateway logs that record full
  request headers by default.
- **Defense:** never put a token in a URL; explicitly configure
  logging/error-tracking tools to redact `Authorization`/`Cookie`
  headers — treat the logging pipeline as part of the threat model,
  not just the browser.

**Cross-service audience confusion — a legitimate token, used somewhere it shouldn't be:**

- Microservices sharing one signing key is common — a token minted
  for Service A (`aud: "service-a"`) gets presented to Service B. If B
  only checks the signature and skips `aud`, it accepts a token that
  was never meant for it.
- **Defense:** every service validates `aud`/`iss` itself — a valid
  signature proves the token came from the trusted issuer, not that
  it was meant for *this particular* service.

**Man-in-the-browser — defeats storage protections entirely:**

- A malicious or compromised browser extension runs with access to
  the page's network traffic and DOM directly, bypassing the
  same-origin restrictions that protect against a page's own injected
  script — `httponly` stops `document.cookie` from reading the token,
  but doesn't stop an extension intercepting the request that carries
  it.
- **Defense:** there's no pure storage fix here — this is exactly
  where client-binding (DPoP/mTLS from [§3](#3-defending-against-token-theft))
  earns its cost: even an intercepted request is useless without the
  private key the extension can't extract, plus a tighter CSP and
  fewer trusted third-party scripts as defense-in-depth.

| Scenario | Attacker needs | Real defense |
|---|---|---|
| Algorithm forgery | No stolen token at all — just a weak verifier | Pin the algorithm server-side; never trust the token's own header to pick it |
| Infrastructure leakage | Access to logs/analytics, not the user's browser | Redact tokens from logs; never put them in a URL |
| Audience confusion | A token meant for a different service | Validate `aud`/`iss` on every single service, not just the signature |
| Man-in-the-browser | A malicious extension or compromised device | Client-binding (DPoP/mTLS) — storage hygiene alone can't fix this one |

**Interview point:** this is the real contrast with §3 — theft-and-replay
is about protecting an *intact* token from being copied; these four are
about a token that was never copied at all, either forged outright,
leaked by your own systems, or valid but misused outside its intended
scope. A strong answer names which category a given scenario actually
falls into before reaching for a fix, since "use `httponly` cookies"
answers none of these four.

## 5. OAuth2 Flow Selection

**"Which OAuth2 flow for a SPA, a backend service, and a CLI tool — and why?"**

```python
# Authorization Code + PKCE -- the only flow a public client (SPA/mobile) should use
code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip("=")
# code_challenge goes out with the initial redirect; code_verifier is only
# sent on the final token exchange, so a stolen auth code alone is useless
```

**Answer:** Depends on who's asking and whether they can keep a secret.

| Flow | Use for | Why |
|---|---|---|
| Authorization Code + PKCE | SPA, mobile | Public client, can't store a secret; PKCE binds the exchange to who started it |
| Client Credentials | Service-to-service | No user in the loop; narrow scopes + IP allowlisting replace consent |
| Device Code | CLI, TVs, headless | No browser on-device; user authorizes from a second device |
| Implicit | Nothing — deprecated | Token exposed in the URL fragment; migrate to PKCE |

**Follow-up — "what stops a malicious app stealing the code via a
registered redirect URI?"** Exact `redirect_uri` matching (no
wildcards) + PKCE, so an intercepted code can't be exchanged without
the original verifier.

## 6. Multi-Factor Authentication

**"TOTP vs. SMS vs. WebAuthn — what's the real trade-off, and how would you roll out MFA?"**

```python
import pyotp

def setup_totp(user_id: str, issuer: str) -> tuple[str, str]:
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user_id, issuer_name=issuer)
    return secret, uri  # secret stored encrypted; uri renders as a QR code
```

**Answer:**

- **TOTP** — free, offline, the practical default.
- **SMS** — weakest; SIM-swap/SS7 interception are real. Rate-limited
  fallback only, never the sole factor.
- **WebAuthn/FIDO2** — strongest, phishing-resistant (credential bound
  to origin), at real hardware/onboarding cost.
- Ship backup codes and an audited break-glass path regardless — "lost
  my phone" is a certainty at scale.

| Pros | Cons / Trade-offs |
|---|---|
| TOTP: free, offline, no telecom dependency | Still phishable via real-time relay |
| SMS: zero setup friction | SIM-swap/SS7 make it the weakest factor |
| WebAuthn: phishing-resistant, origin-bound | Hardware cost; still needs a fallback |

## 7. Enterprise SSO Integration

**"Validating an incoming SAML/OIDC assertion — what goes wrong with sloppy Just-in-Time provisioning?"**

```python
def validate_assertion(assertion, expected_issuer: str, expected_audience: str) -> bool:
    return (
        assertion.issuer == expected_issuer
        and expected_audience in assertion.audiences
        and assertion.not_before <= now() <= assertion.not_on_or_after
        and assertion.signature_is_valid()
    )
```

**Answer:**

- Validate signature, issuer, audience, and expiry on every assertion;
  enforce HTTPS on the ACS/callback endpoint.
- Map external attributes through an explicit allowlist — never trust
  raw IdP claims.
- Just-in-Time provisioning (auto-create on first login) is dangerous
  the moment its default is above least privilege — a misconfigured
  IdP can hand an elevated role to every one of its users at once.

**Follow-up — "what about logout?"** Configure SAML SLO or OIDC
RP-initiated logout and clean up server-side — client-side-only logout
leaves the session valid at the IdP.

---

## Code Samples

- `code_samples/chapter-4/jwt_authentication_system.py` — RS256 JWT
  issuing/verification, refresh token rotation, key rotation, token
  blacklisting
- `code_samples/chapter-4/oauth2_provider.py` — Authorization Code +
  PKCE and Client Credentials flows as a FastAPI app, scope
  validation, token introspection

```bash
pip install pyjwt cryptography redis fastapi uvicorn pydantic
python code_samples/chapter-4/jwt_authentication_system.py
uvicorn code_samples.chapter-4.oauth2_provider:app --reload --port 8001
```
