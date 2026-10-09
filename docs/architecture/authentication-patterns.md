---
title: "Authentication Patterns"
---

# Authentication Patterns

JWT design, OAuth2 flow selection, MFA, and enterprise SSO — proving
*who* is making the request. For *what they're allowed to do* once
authenticated, see [Authorization Patterns](authorization-patterns.md).

## 1. JWT Design and Security

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

## 2. OAuth2 Flow Selection

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

## 3. Multi-Factor Authentication

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

## 4. Enterprise SSO Integration

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
