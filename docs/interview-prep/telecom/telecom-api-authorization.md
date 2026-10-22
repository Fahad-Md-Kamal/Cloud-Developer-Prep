---
title: "Authorization for Telecom APIs: CIBA & Number Verification"
---

# Authorization for Telecom APIs: CIBA & Number Verification

[TM Forum Open APIs](tm-forum-open-apis.md) covers the data/resource
shape — this page covers how an app actually gets authorized to call a
network-capability API on a customer's behalf. The underlying pattern
is the same redirect-based consent flow already covered in depth for
[FAPI & Consent Authorization Flows](../fintech/fapi-and-consent-flows.md) —
this page focuses on where telecom's specific flow genuinely diverges.

## 1. "Does a telecom network API use the same consent-redirect flow already covered for Open Banking?"

**Answer:**

- For APIs acting on behalf of a logged-in user in an app they're
  actively using, yes — the same OAuth2 authorization-code redirect
  flow already diagrammed in
  [FAPI & Consent Authorization Flows](../fintech/fapi-and-consent-flows.md) —
  the app redirects to the carrier's own authorization endpoint, the
  user approves, a code comes back, the app exchanges it for a scoped
  token. Nothing new to re-derive here.
- The genuine divergence is a flow most financial or healthcare apps
  never need at all: **CIBA**.

## 2. "What's CIBA (Client-Initiated Backchannel Authentication), and why does telecom specifically need it when the redirect flow already exists?"

**Answer:**

- The standard redirect flow assumes the user is actively present in a
  browser or app *right now*, able to be redirected to a login page
  and back. **CIBA** handles a genuinely different case: the
  authorization request is initiated **out-of-band**, by a backend
  system, for a user who isn't necessarily looking at the requesting
  app's screen at that moment at all.
- Concrete example: a carrier-network fraud check triggered server-side
  during a high-value transaction elsewhere (a bank's own fraud
  system calling out to verify the user's phone is genuinely present
  and hasn't been SIM-swapped) — there's no app screen to redirect the
  user through; instead, the carrier pushes an approval prompt directly
  to the user's registered device (a push notification, an SMS), and
  the backend system polls for the result.
- This matters specifically because many of the highest-value telecom
  network APIs (fraud/risk checks, SIM-swap verification) are called
  by a **different** company's backend (a bank, a fintech app) during
  a flow where the actual end user isn't inside *that calling
  company's* app at the moment the check needs to happen — CIBA is
  built for exactly that decoupled, backend-initiated case.

## 3. "What's number verification, mechanically, and why is it considered a stronger signal than SMS OTP?"

**Answer:**

- **Number verification** confirms a phone number is genuinely active
  on the device currently making the request — not by sending an SMS
  code the user types back in (which, see
  [Identity Security §2](../../security/identity-security-zero-trust-and-pam.md#2-mfa-exists-but-not-all-mfa-is-equally-strong-whats-actually-different-between-the-common-methods),
  is vulnerable to SIM swapping and interception), but by checking
  directly, at the **network level**, whether the device currently
  holding this active mobile data session is actually associated with
  the claimed number.
- Because this check happens inside the carrier's own network
  infrastructure rather than relying on a message the user has to
  receive and relay back, it closes the exact interception/SIM-swap gap
  that makes SMS-based OTP the weakest common MFA method — the
  verification doesn't depend on a message reaching the right device at
  all, it depends on which device's live network session is actually
  making the request.

## 4. "What's the practical trade-off of network-level verification like this, compared to standard app-based MFA?"

**Answer:**

- It only works while the device is actually on **mobile data from that
  carrier** — a device on Wi-Fi, or roaming onto a different carrier's
  network, can't be verified this way, since the check depends on the
  home carrier's own network session.
- It requires a direct technical integration with carrier network APIs
  (via CAMARA or an aggregator), real infrastructure most apps don't
  already have, compared to SMS OTP's near-zero integration cost — the
  classic security-vs-convenience trade-off, just shifted here toward
  "stronger but requires real carrier integration work" rather than
  "weaker but universally available."

| Pros | Cons / Trade-offs |
|---|---|
| The standard redirect flow reuses everything already covered for Open Banking/FAPI | Doesn't cover the backend-initiated, no-active-screen case at all |
| CIBA enables fraud/risk checks initiated by a completely different company's backend | Genuinely more complex than the simple redirect flow — polling, device-side approval prompts |
| Network-level number verification closes the SIM-swap/interception gap SMS OTP can't | Only works on the carrier's own mobile data session — unavailable on Wi-Fi or roaming |

---

## Code Samples

No dedicated code samples yet for this section.
