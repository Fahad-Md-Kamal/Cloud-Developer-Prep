---
title: "Legacy Signaling: SS7 & Diameter"
---

# Legacy Signaling: SS7 & Diameter

The direct telecom parallel to
[HL7 v2.x & C-CDA](../healthcare/hl7-ccda.md) and
[ISO 8583/SWIFT MT](../fintech/iso8583-and-swift-mt-mx.md) — a
decades-old protocol that predates every modern alternative, still
carrying the overwhelming majority of real traffic today. What's
genuinely different here: this isn't just old, it's a real, actively
exploited security weak point baked into global telecom infrastructure.

## 1. "What is SS7, and what's it actually doing every time a call connects or an SMS arrives?"

**Answer:**

- **SS7 (Signaling System No. 7)**, standardized in the 1970s-80s, is
  the protocol carriers use to set up calls, route SMS messages, and
  manage roaming **between each other's networks** — not the voice/data
  path itself, the control-plane messaging that decides how to route
  it.
- When a subscriber roams onto another carrier's network, or a call
  needs to reach a number on a different carrier entirely, SS7 is the
  signaling exchange that locates the subscriber and sets up the actual
  connection — a real-time, multi-network message exchange happening
  behind every cross-carrier call or text.

## How a Call Actually Gets Routed Across Carriers via SS7

<svg viewBox="0 0 900 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of SS7 call routing: the originating carrier queries the destination number's home network registry to locate the subscriber, then routes the call through the carrier currently serving that subscriber" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="40" y="40" width="180" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="130" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Caller's Carrier</text>
<rect x="680" y="40" width="180" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="770" y="65" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">Home Network</text>
<text x="770" y="83" font-size="12" text-anchor="middle" fill="#5b6472">Subscriber Registry</text>
<rect x="360" y="260" width="200" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.5;0.54;1" dur="15s" repeatCount="indefinite"></animate></rect>
<text x="460" y="286" font-size="14" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.5;0.54;1" dur="15s" repeatCount="indefinite"></animate>Serving Carrier</text>
<text x="460" y="304" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.5;0.54;1" dur="15s" repeatCount="indefinite"></animate>wherever the subscriber actually is</text>
<line x1="220" y1="70" x2="680" y2="70" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.06;0.1;0.3;0.34;1" dur="15s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#2f6fb3" cy="70"><animate attributeName="cx" values="220;680" keyTimes="0;1" dur="1.8s" begin="0.9s;15.9s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.9;1" dur="1.8s" begin="0.9s;15.9s" repeatCount="indefinite"></animate></circle>
<line x1="680" y1="90" x2="220" y2="90" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.32;0.36;0.5;0.54;1" dur="15s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#b5831f" cy="90"><animate attributeName="cx" values="680;220" keyTimes="0;1" dur="1.8s" begin="4.8s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.9;1" dur="1.8s" begin="4.8s" repeatCount="indefinite"></animate></circle>
<line x1="220" y1="100" x2="360" y2="280" stroke="#1f9d6b" stroke-width="2" stroke-dasharray="5,5"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.56;0.6;1" dur="15s" repeatCount="indefinite"></animate></line>
<text x="450" y="370" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.28;0.32;1" dur="15s" repeatCount="indefinite"></animate>The caller's carrier queries the dialed number's home registry: where is this subscriber right now?</text>
<text x="450" y="370" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.32;0.36;0.48;0.52;1" dur="15s" repeatCount="indefinite"></animate>The home registry responds with the serving carrier currently handling that subscriber.</text>
<text x="450" y="370" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.6;0.64;1" dur="15s" repeatCount="indefinite"></animate>The call is routed directly to wherever the subscriber actually is — even on another network.</text>
</svg>

## 2. "Why is SS7 specifically known as a real, exploited security weak point, not just old technology?"

**Answer:**

- SS7 was designed in an era when the **set of networks allowed to
  exchange signaling messages was small and implicitly trusted** — there
  was no serious expectation that an unauthorized party could ever gain
  access to the signaling network at all, so the protocol has
  essentially **no built-in authentication** of who's allowed to send
  which message.
- That assumption has not held for a long time — SS7 network access has
  been obtained by parties well beyond the small trusted circle it was
  designed for, and an attacker with that access can send legitimate-
  looking SS7 messages to **intercept SMS messages or calls intended for
  a different subscriber**, including SMS-based one-time passcodes.
- This is a direct, real-world mechanism behind
  [SMS MFA's weakness](../../security/identity-security-zero-trust-and-pam.md#2-mfa-exists-but-not-all-mfa-is-equally-strong-whats-actually-different-between-the-common-methods) —
  SIM swapping is one way to defeat SMS OTP; a direct SS7-level
  interception attack is another, structurally different way to reach
  the same outcome, exploiting the **network** rather than the
  **carrier's customer-service process**. Both land on the same lesson:
  SMS OTP has more than one real, documented attack path.

## 3. "What's Diameter, and how does it relate to SS7?"

**Answer:**

- **Diameter** is the signaling protocol for authentication,
  authorization, and accounting (AAA) in later-generation (4G/LTE and
  beyond) networks — a structurally more modern protocol than SS7,
  but still a legacy, carrier-grade signaling protocol relative to a
  REST API, and still the thing actually running in core network
  infrastructure today, not a historical footnote.
- Diameter improved on SS7 specifically around security (it supports
  proper transport-layer security and stronger peer authentication
  between network elements), but **interworking between SS7-based 2G/3G
  networks and Diameter-based 4G/5G networks** is still a real
  operational reality for any carrier supporting older devices or
  roaming partners still running legacy infrastructure — the legacy
  protocol doesn't disappear just because a newer one exists alongside
  it, the same "far from retired" pattern already established for
  [HL7 v2](../healthcare/hl7-ccda.md#1-what-does-an-hl7-v2-message-actually-look-like-structurally)
  and [ISO 8583](../fintech/iso8583-and-swift-mt-mx.md#2-why-is-iso-8583-still-the-dominant-standard-for-card-transactions-when-far-more-modern-alternatives-exist).

## 4. "How does a modern network actually defend against SS7-level attacks, given the protocol itself can't just be replaced overnight?"

**Answer:**

- **SS7 firewalls** — purpose-built filtering systems sitting at the
  edge of a carrier's network, inspecting incoming SS7 messages for
  patterns that look like an unauthorized location-tracking or
  message-interception attempt, and blocking them before they reach
  internal network elements — the same filtering-at-the-boundary
  principle as
  [a stateful firewall](../../security/network-security-fundamentals.md#1-stateless-vs-stateful-firewall-whats-the-actual-mechanism-difference),
  applied to telecom-specific signaling traffic instead of generic
  IP traffic.
- At the application level, the practical mitigation isn't fixing SS7
  itself — it's **not relying on SMS as a sole authentication factor**
  for anything genuinely high-stakes, shifting toward the stronger MFA
  methods (authenticator apps, hardware keys) already covered in
  [Identity Security §2](../../security/identity-security-zero-trust-and-pam.md#2-mfa-exists-but-not-all-mfa-is-equally-strong-whats-actually-different-between-the-common-methods),
  or toward network-level verification approaches like
  [CAMARA number verification](telecom-api-authorization.md#3-whats-number-verification-mechanically-and-why-is-it-considered-a-stronger-signal-than-sms-otp)
  that don't depend on an SMS actually reaching the right device at all.

| Pros | Cons / Trade-offs |
|---|---|
| SS7/Diameter remain the actual backbone of real-time cross-carrier call/SMS routing globally | No realistic full replacement in the near term — decades of embedded infrastructure |
| SS7 firewalls can filter out a real share of known attack patterns at the network edge | Doesn't fix the protocol's fundamental lack of built-in authentication |
| Diameter's stronger security model is a real improvement over SS7 | Still has to interwork with SS7-based legacy networks, inheriting some of the same exposure |
| Shifting away from SMS-only MFA sidesteps the risk at the application layer | Requires real product/UX change, not just a backend security fix |

---

## Code Samples

No dedicated code samples yet for this section.
