---
title: "Cryptography Fundamentals"
---

# Cryptography Fundamentals

Every other security page on this site uses encryption, hashing, and
TLS as a given — "store it encrypted," "the connection is TLS-secured."
This page is the mechanism underneath all of those claims. Getting the
vocabulary precise here (encryption vs. hashing, symmetric vs.
asymmetric) is the single most common gap in an otherwise strong
security answer.

## 1. "Encryption vs. hashing — these get used interchangeably, what's actually different?"

**Answer:**

- **Encryption is reversible** — given the right key, ciphertext
  converts back to the original plaintext. It's for data you need to
  read again later: a file at rest, a value in a database, a network
  payload in transit.
- **Hashing is one-way by design** — a hash function converts input of
  any size into a fixed-size output, and there's no key or process that
  converts the hash back to the original input. It's for *verifying*
  something matches, not for recovering it — a password's stored hash,
  a file's checksum, a block in a blockchain.
- Mixing these up is a real, recurring bug class: "encrypting" a
  password (reversible, meaning anyone with the key, including an
  attacker who steals the database and the key, can recover every
  plaintext password) instead of hashing it (irreversible — even the
  application itself can't recover the original password, only verify a
  login attempt against the stored hash).

## 2. "Symmetric vs. asymmetric encryption — what's the actual trade-off, and why do real systems use both together?"

**Answer:**

- **Symmetric encryption** — the same single key both encrypts and
  decrypts (AES is the standard today). Fast, computationally cheap, but
  requires both parties to already share that key securely — which is
  exactly the hard problem it doesn't solve on its own.
- **Asymmetric encryption** — a mathematically linked **key pair**: a
  public key (safe to share with anyone) encrypts, and only the matching
  private key (kept secret) can decrypt — or the reverse, for signing
  (see §4). This solves the key-distribution problem symmetric
  encryption has, since the public key never needs to be kept secret at
  all.
- The trade-off that makes both necessary: asymmetric encryption is
  **far more computationally expensive** than symmetric — using it to
  encrypt an entire data stream would be slow at real scale. The
  standard solution, used by TLS (§3) and most real systems: use
  asymmetric encryption just once, briefly, to securely exchange a
  symmetric key — then switch to fast symmetric encryption for the
  actual bulk of the data.

## How TLS Actually Establishes a Secure Connection

<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of a TLS handshake: the client and server exchange certificates and use asymmetric encryption to agree on a shared symmetric session key, then switch to fast symmetric encryption for the actual data" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="40" y="40" width="180" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="130" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Client</text>
<rect x="680" y="40" width="180" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="770" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Server</text>
<line x1="220" y1="70" x2="680" y2="70" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.06;0.1;0.3;0.34;1" dur="17s" repeatCount="indefinite"></animate></line>
<circle r="8" fill="#2f6fb3"><animate attributeName="cx" values="220;680" keyTimes="0;1" dur="2.5s" begin="0.5s;19.5s" repeatCount="indefinite"></animate><animate attributeName="cy" values="70;70" dur="2.5s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" dur="2.5s" begin="0.5s;19.5s" repeatCount="indefinite"></animate></circle>
<rect x="340" y="140" width="220" height="60" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.3;0.34;1" dur="17s" repeatCount="indefinite"></animate></rect>
<text x="450" y="166" font-size="13" font-weight="600" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.3;0.34;1" dur="17s" repeatCount="indefinite"></animate>Server sends its certificate</text>
<text x="450" y="184" font-size="12" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.1;0.14;0.3;0.34;1" dur="17s" repeatCount="indefinite"></animate>(its public key, signed)</text>
<rect x="340" y="240" width="220" height="60" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.34;0.38;0.6;0.64;1" dur="17s" repeatCount="indefinite"></animate></rect>
<text x="450" y="266" font-size="13" font-weight="600" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.34;0.38;0.6;0.64;1" dur="17s" repeatCount="indefinite"></animate>Client encrypts a session key</text>
<text x="450" y="284" font-size="12" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.34;0.38;0.6;0.64;1" dur="17s" repeatCount="indefinite"></animate>using the server's public key (asymmetric)</text>
<rect x="340" y="340" width="220" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="17s" repeatCount="indefinite"></animate></rect>
<text x="450" y="366" font-size="13" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="17s" repeatCount="indefinite"></animate>Both switch to the shared key</text>
<text x="450" y="384" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="17s" repeatCount="indefinite"></animate>fast symmetric encryption for all real data</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.3;0.34;1" dur="17s" repeatCount="indefinite"></animate>The server proves its identity with a certificate, signed by a trusted authority.</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.34;0.38;0.6;0.64;1" dur="17s" repeatCount="indefinite"></animate>Asymmetric encryption is used ONCE, just to exchange a symmetric key safely.</text>
<text x="450" y="425" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="17s" repeatCount="indefinite"></animate>From here on, fast symmetric encryption protects the actual session.</text>
</svg>

## 3. "Walk through what's actually happening during a TLS handshake."

**Answer:**

- The server presents a **certificate** — containing its public key,
  signed by a trusted **Certificate Authority (CA)**. The client verifies
  that signature against a CA it already trusts (bundled with the OS or
  browser), confirming the server is who it claims to be before trusting
  anything else it sends.
- The client generates a symmetric session key and encrypts it using the
  server's public key (asymmetric encryption, used exactly once, for
  exactly this exchange) — only the server's matching private key can
  decrypt it, so the session key reaches the server without ever being
  exposed in transit.
- From that point on, both sides switch to fast **symmetric encryption**
  using the now-shared session key for the entire rest of the
  connection — this is the direct, practical application of the
  trade-off from §2: asymmetric encryption solves the key-exchange
  problem once, then gets out of the way for performance.
- This is why a certificate expiring or being issued by an untrusted CA
  breaks a connection before any actual data exchange happens at all —
  the identity verification step is a hard gate, not an optional nicety.

## 4. "What's a digital signature, and how is it different from encryption?"

**Answer:**

- A digital signature proves two things at once: **integrity** (the data
  hasn't been altered since signing) and **authenticity** (it genuinely
  came from the claimed signer) — not confidentiality, which is
  encryption's job.
- Mechanically: the signer hashes the data, then encrypts *that hash*
  with their own **private** key (the reverse direction from normal
  asymmetric encryption, which encrypts with a public key). Anyone with
  the signer's public key can decrypt the signature back to the
  original hash, re-hash the actual data themselves, and compare the
  two — a match proves both that the signer's private key produced it
  and that the data hasn't changed since.
- This is the exact mechanism underneath a TLS certificate's "signed by
  a trusted CA" claim in §3 — the CA signed the certificate with its own
  private key, and every client's trust store already holds the CA's
  public key to verify it.

## 5. "Why is hashing a password with plain SHA-256 the wrong approach, even though SHA-256 itself is a secure hash function?"

**Answer:**

- A general-purpose hash function like SHA-256 is designed to be **fast**
  — a property that's actively harmful for password storage specifically,
  because it means an attacker with a stolen password-hash database can
  try billions of guesses per second against it.
- **Rainbow tables** — precomputed tables mapping common passwords to
  their hashes — make an unsalted hash even weaker: a match is instant
  lookup, no guessing required at all.
- **Salting** — a unique, random value added to each password before
  hashing — defeats rainbow tables entirely, since a precomputed table
  for one salt value doesn't apply to any other.
- **Password-specific hash functions** (bcrypt, Argon2) solve the speed
  problem directly: they're deliberately, tunably **slow** (a
  configurable "work factor"), making large-scale guessing
  computationally expensive even with modern hardware — the opposite
  design goal from a general-purpose hash function like SHA-256, which
  is built to be fast specifically because most of its *other* use cases
  (file checksums, digital signatures) want speed, not slowness.

| Pros | Cons / Trade-offs |
|---|---|
| Symmetric encryption is fast enough for real bulk data transfer | Requires a securely shared key — doesn't solve key distribution on its own |
| Asymmetric encryption solves key distribution without a pre-shared secret | Too computationally expensive to use for an entire data stream |
| TLS's hybrid approach gets both: safe key exchange and fast bulk encryption | A single broken/untrusted CA in the chain undermines the entire trust model |
| bcrypt/Argon2's deliberate slowness makes mass password-guessing impractical | Slower by design — a real, intentional performance cost on every login |

---

## Code Samples

No dedicated code samples for this page.
