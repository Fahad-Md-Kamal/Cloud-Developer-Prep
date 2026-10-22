---
title: "Network Security Fundamentals"
---

# Network Security Fundamentals

[VPC Connectivity & Hybrid Networking](../cloud-devops/vpc-connectivity-and-hybrid-networking.md)
already covers Site-to-Site VPN and Direct Connect from AWS's specific
service angle. This page covers the vendor-agnostic mechanisms
underneath network security generally — how a firewall actually decides
what to block, why "trust the internal network" is a broken model, and
the two classic attacks that exploit protocols never designed with
security in mind.

## 1. "Stateless vs. stateful firewall — what's the actual mechanism difference?"

**Answer:**

- A **stateless firewall** (packet filter) evaluates every packet
  independently against a fixed rule set — source/destination IP, port,
  protocol — with no memory of any packet that came before it. It has to
  explicitly allow both the outbound request *and* the inbound response
  as separate rules, since it has no concept of "this response belongs
  to that earlier request."
- A **stateful firewall** tracks active connections — once it sees an
  outbound request it permitted, it automatically allows the
  corresponding inbound response without needing a separate explicit
  rule, because it remembers the connection's state.
- This is the exact mechanism behind the asymmetric behavior already
  named (without being explained) for AWS security groups, which are
  stateful: an inbound rule allowing traffic in doesn't need a matching
  outbound rule for the response to leave — the firewall already knows
  that response belongs to an already-permitted connection.
- **Network ACLs** (the stateless counterpart in AWS, operating at the
  subnet level) require exactly the explicit both-directions rule
  management a stateless firewall always has — this is a real, common
  point of confusion: a security group and an NACL look similar on the
  surface but follow genuinely different underlying logic.

## 2. "Why is 'trust the internal network' considered a broken security model today — what does zero trust actually mean, mechanically?"

**Answer:**

- The traditional model — a hardened perimeter (firewall at the edge),
  with broad trust for anything already inside the network — fails the
  moment **any** single internal device is compromised (a phished
  employee's laptop, a vulnerable IoT device). Once an attacker is
  inside that perimeter, internal systems that trusted "already on the
  network" as sufficient proof of legitimacy become easy lateral-movement
  targets.
- **Zero trust** removes that implicit trust entirely: every request is
  verified — identity, device posture, and authorization — **regardless
  of where it originates**, including from inside what used to be
  considered the trusted perimeter. "Never trust, always verify" is the
  actual operating principle, not a marketing phrase.
- Mechanically, this means authentication and authorization checks move
  from "once, at the network edge" to **enforced on every single
  request**, often per-service rather than per-network-segment — the
  same principle behind requiring a valid token on every API call
  (see [Authentication Patterns](../architecture/authentication-patterns.md))
  applied at the network architecture level, not just the application
  layer.
- The practical cost: meaningfully more overhead per request (every call
  verified, not just the initial network entry point) and real
  architectural complexity — zero trust isn't a product you buy, it's an
  architecture you build toward incrementally.

## 3. "What's actually happening in ARP spoofing and DNS spoofing — why do these attacks work at all?"

**Answer:**

- Both exploit the same root cause: **protocols designed without
  built-in verification**, trusting that a response claiming to come
  from a given source actually did.
- **ARP spoofing** — ARP (Address Resolution Protocol) maps an IP
  address to a physical (MAC) address on a local network, with no
  authentication of who's allowed to answer an ARP request. An attacker
  on the same local network sends forged ARP responses claiming "I am
  the router" (or "I am this other host"), and other devices simply
  believe it — redirecting their traffic through the attacker, a classic
  **man-in-the-middle** setup.
- **DNS spoofing / cache poisoning** — see
  [How DNS Resolution Actually Works](../cloud-devops/load-balancing-and-dns.md#how-dns-resolution-actually-works)
  for the legitimate resolution chain this attack corrupts. An attacker
  injects a forged DNS response (or poisons a resolver's cache) mapping
  a legitimate domain name to an attacker-controlled IP — a victim
  looking up a real domain gets sent to a fake server, with nothing in
  the basic DNS protocol itself to detect the forgery.
- **DNSSEC** (DNS Security Extensions) is the direct mitigation for the
  second attack — it adds cryptographic signatures (the same
  digital-signature mechanism covered in
  [Cryptography Fundamentals §4](cryptography-fundamentals.md#4-whats-a-digital-signature-and-how-is-it-different-from-encryption))
  to DNS responses, so a resolver can verify a response genuinely came
  from the authoritative source rather than blindly trusting whatever
  arrived first.

## 4. "What do nmap and Wireshark actually do, and when would you reach for each?"

**Answer:**

- **nmap** answers "what's actually running on this network" —
  **port scanning**: sending probes across a range of ports on a target
  host (or many hosts) and interpreting the responses (open, closed,
  filtered) to map out what services are listening and, often, what
  software/version is behind each one. The first tool reached for in
  both legitimate network auditing and the reconnaissance phase of a
  penetration test (see
  [Offensive Security & Penetration Testing](offensive-security-and-pentesting.md)).
- **Wireshark** answers a different question — "what's actually in the
  traffic" — a packet capture and analysis tool that shows the real
  contents of network traffic, protocol by protocol, down to individual
  fields in a TCP/IP packet. Used for debugging a network issue by
  actually observing what's being sent, or for verifying traffic is
  genuinely encrypted (confirming no plaintext credentials are visible
  on the wire) rather than assuming it from configuration alone.
- The practical distinction: nmap tells you what's **reachable**;
  Wireshark tells you what's **actually happening** on a connection once
  you're looking at it directly.

| Pros | Cons / Trade-offs |
|---|---|
| Stateful firewalls need far less rule management than stateless ones | Track more state, costing more memory/resources per active connection |
| Zero trust removes the single-perimeter-breach failure mode entirely | Real added overhead and complexity — not a drop-in replacement for perimeter security |
| DNSSEC cryptographically prevents DNS spoofing from succeeding | Not universally deployed — a domain without it is still exposed to the attack |
| nmap and Wireshark together cover both "what's reachable" and "what's actually on the wire" | Both are dual-use tools — the same reconnaissance power serves legitimate audits and real attackers |

---

## Code Samples

No dedicated code samples for this page.
