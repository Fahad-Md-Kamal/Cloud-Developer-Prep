---
title: "FAPI & Consent Authorization Flows"
---

# FAPI & Consent Authorization Flows

[Open Banking & Financial Data APIs](open-banking-and-financial-apis.md)
covers the data model — this page covers how an app actually gets
authorized to touch it, the direct fintech parallel to
[SMART on FHIR](../healthcare/smart-on-fhir-and-bulk-data.md). The
pattern is the same shape (OAuth2, hardened for one specific high-stakes
context); the stakes and the specific hardening are what's different.

## 1. "Why does Open Banking need a stricter OAuth2 profile instead of plain OAuth2?"

**Answer:**

- Financial account data is higher-stakes than most OAuth2 use cases —
  a leaked read-only social feed token and a leaked bank-transaction-read
  token are not remotely comparable in consequence.
- **FAPI (Financial-grade API)** is a specific security profile built on
  top of OAuth2/OIDC — the same "constrain a general standard for one
  high-stakes context" pattern as
  [SMART on FHIR §1](../healthcare/smart-on-fhir-and-bulk-data.md#1-why-does-a-fhir-server-need-a-separate-authorization-standard-at-all-isnt-oauth2-already-enough),
  mandating things plain OAuth2 only leaves optional: PKCE always
  required (not optional), short-lived access tokens, and the
  **implicit flow banned outright** — implicit flow returns the token
  directly in the browser's URL fragment, which ends up in browser
  history and can leak via a referrer header, a long-known OAuth2 weak
  point FAPI closes by forbidding the flow entirely rather than just
  discouraging it.

## The Consent Authorization Flow

<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of an Open Banking consent flow: a fintech app redirects the user to their own bank's login page, the user approves a scoped, time-limited request, the bank returns an authorization code, and the app exchanges it for an access token bound to that consent" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="440" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<rect x="40" y="40" width="190" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="135" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Fintech App</text>
<rect x="670" y="40" width="190" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="765" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Customer's Own Bank</text>
<line x1="230" y1="70" x2="670" y2="70" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.04;0.08;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#2f6fb3" cy="70"><animate attributeName="cx" values="230;670" keyTimes="0;1" dur="2.2s" begin="0.4s;18.4s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" dur="2.2s" begin="0.4s;18.4s" repeatCount="indefinite"></animate></circle>
<rect x="340" y="140" width="220" height="60" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="450" y="166" font-size="13" font-weight="600" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate>Customer logs in AT THE BANK</text>
<text x="450" y="184" font-size="12" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.26;0.3;1" dur="18s" repeatCount="indefinite"></animate>approves a scoped, time-limited request</text>
<line x1="670" y1="90" x2="230" y2="90" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.3;0.34;0.5;0.54;1" dur="18s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#b5831f" cy="90"><animate attributeName="cx" values="670;230" keyTimes="0;1" dur="2.2s" begin="6.3s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" dur="2.2s" begin="6.3s" repeatCount="indefinite"></animate></circle>
<rect x="340" y="240" width="220" height="60" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.52;0.56;0.74;0.78;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="450" y="266" font-size="13" font-weight="600" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.52;0.56;0.74;0.78;1" dur="18s" repeatCount="indefinite"></animate>App exchanges the code</text>
<text x="450" y="284" font-size="12" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.52;0.56;0.74;0.78;1" dur="18s" repeatCount="indefinite"></animate>for a token bound to this consent</text>
<rect x="340" y="340" width="220" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.78;0.82;1" dur="18s" repeatCount="indefinite"></animate></rect>
<text x="450" y="366" font-size="13" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.78;0.82;1" dur="18s" repeatCount="indefinite"></animate>App reads account data</text>
<text x="450" y="384" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.78;0.82;1" dur="18s" repeatCount="indefinite"></animate>until the consent expires or is revoked</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.22;0.26;1" dur="18s" repeatCount="indefinite"></animate>The app redirects to the BANK's own login page — never sees the password.</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.26;0.3;0.48;0.52;1" dur="18s" repeatCount="indefinite"></animate>The bank returns an authorization code — not a usable token yet.</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.82;0.86;1" dur="18s" repeatCount="indefinite"></animate>The bank remains the source of truth — it can revoke access at any time.</text>
</svg>

## 2. "Walk through what actually makes this redirect flow secure — why can't the app just ask the customer for their bank password directly?"

**Answer:**

- The entire point of the flow is that the customer **authenticates on
  the bank's own domain**, never inside the third-party app at all — the
  app only ever receives a short-lived authorization code, then
  exchanges it (server-to-server, not visible to the browser) for an
  access token scoped to exactly what the customer approved.
- This is the same core property already covered generally for OAuth2 in
  [Authentication Patterns](../../architecture/authentication-patterns.md) —
  the app never holds a credential capable of broader access than the
  token itself grants, so a compromised app leaks only a scoped,
  revocable token, never the customer's actual bank login.

## 3. "What's token binding / mutual TLS in FAPI, and why does it matter beyond a normal bearer token?"

**Answer:**

- A plain bearer token works for whoever **possesses** it — if stolen,
  pure impersonation, no further proof required.
- FAPI's higher security tier requires binding the token to a specific
  TLS client certificate (or an equivalent signed proof-of-possession)
  — a stolen token alone is no longer enough to use it; the attacker
  would also need the private key tied to that specific certificate.
- This is a direct, practical application of
  [digital signatures](../../security/cryptography-fundamentals.md#4-whats-a-digital-signature-and-how-is-it-different-from-encryption) —
  proving possession of a private key is what turns a merely-stolen
  token from immediately usable into useless without also compromising
  the key material backing it.

## 4. "What's consent expiry and revocation, and why is this a harder UX problem in finance than in most OAuth2 contexts?"

**Answer:**

- Regulation typically mandates a **maximum consent duration** (commonly
  90 days under UK Open Banking) — after which access must be explicitly
  re-confirmed by the customer, not silently renewed.
- The customer must be able to **revoke consent at any time, from their
  own bank's interface**, independent of whatever the third-party app
  shows — the bank, not the app, is the actual source of truth for
  whether access is still valid.
- The practical engineering consequence: a sudden `401`/`403` on an
  established integration isn't automatically a bug — it can be
  revocation working exactly as intended, and the app needs to handle
  that gracefully (re-prompt for consent, not retry blindly or treat it
  as an outage) rather than assuming a token, once issued, stays valid
  indefinitely.

| Pros | Cons / Trade-offs |
|---|---|
| Redirect-based consent means the app never touches the real bank credential | More integration complexity than a simple username/password form |
| FAPI's mandatory PKCE and banned implicit flow close known OAuth2 weak points | A stricter profile to implement correctly than generic OAuth2 |
| Token binding via mutual TLS defeats pure token theft | Real operational overhead — client certificate management at scale |
| Bank-controlled revocation keeps the customer genuinely in control | Apps must handle sudden, legitimate access loss gracefully, not as an error |

---

## Code Samples

No dedicated code samples yet for this section.
