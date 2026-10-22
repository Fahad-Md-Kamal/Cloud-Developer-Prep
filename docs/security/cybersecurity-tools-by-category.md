---
title: "Cybersecurity Tools by Category"
---

# Cybersecurity Tools by Category

The rest of this track covers concepts and methodology. This page is
the practical map on top of that — which concrete tool actually
performs a given kind of security check, organized by what each one
mechanically does, the same way
[Testing Tools & Frameworks by Type](../testing/testing-tools-and-frameworks.md)
maps testing concepts to concrete tools.

## 1. "Vulnerability scanners (Nessus, OpenVAS, Qualys) — what are they actually checking, mechanically?"

**Answer:**

- A vulnerability scanner probes a target system (a host, a network
  range) and compares what it finds — open ports, running service
  versions, OS fingerprints — against a continuously updated database of
  **known vulnerability signatures** (CVEs), flagging matches.
- This is the automated, signature-matching half of the distinction
  already drawn in
  [Offensive Security §1](offensive-security-and-pentesting.md#1-whats-the-actual-difference-between-a-vulnerability-scan-and-a-real-penetration-test) —
  fast and broad, but only as good as its signature database; it can't
  find a vulnerability nobody has cataloged yet, or chain several minor
  findings into something seriously exploitable the way a human
  penetration tester does.
- **Nessus** (commercial) and **OpenVAS** (open-source) are the common
  general-purpose options; **Qualys** operates as a cloud-based platform
  for continuous scanning across a large, dynamic infrastructure
  footprint rather than a one-off scan of a fixed target list.

## 2. "Network analysis tools — nmap and Wireshark are already covered; what's new here?"

**Answer:**

- [Network Security Fundamentals §4](network-security-fundamentals.md#4-what-do-nmap-and-wireshark-actually-do-and-when-would-you-reach-for-each)
  already covers nmap (port scanning) and Wireshark (packet capture and
  analysis) in full.
- The **Nmap Scripting Engine (NSE)** extends plain port scanning with
  Lua scripts that perform deeper checks once a port is found open —
  detecting a specific known vulnerability in the service behind that
  port, not just confirming the port is open — the bridge between a
  basic port scan and a lightweight vulnerability check, without a full
  separate scanner.
- **tcpdump** is Wireshark's command-line cousin — same underlying
  packet-capture mechanism, no GUI, built for capturing traffic on a
  remote server over SSH or scripting a capture as part of an automated
  process, where Wireshark's graphical analysis isn't practical to run
  directly.

## 3. "Burp Suite / OWASP ZAP — what's the actual mechanism behind a web app security testing proxy?"

**Answer:**

- Both work as an **intercepting proxy** — they sit directly between the
  browser and the target web application, so every single request and
  response actually passes through the tool before reaching its
  destination.
- This is a genuinely different mechanism from a vulnerability scanner
  crawling a site externally: a tester using an intercepting proxy can
  **pause, inspect, and modify** any request by hand before it's
  actually sent — changing a parameter, replaying a request with a
  different value, probing exactly the kind of business-logic edge case
  an automated scan has no way to know to try (the same manual,
  judgment-driven testing distinction already drawn throughout this
  track).
- **Burp Suite** is the industry-standard commercial option, with a
  large extension ecosystem; **OWASP ZAP** is the free, open-source
  alternative with substantially overlapping core functionality — both
  also include their own automated scanning modes on top of the manual
  proxy capability, blending the two approaches in one tool.

## 4. "Metasploit — what does an 'exploitation framework' actually provide that a scanner doesn't?"

**Answer:**

- A vulnerability scanner only tells you a weakness likely exists.
  Metasploit is built for the **exploitation** phase of
  [a penetration test](offensive-security-and-pentesting.md#2-walk-through-the-actual-phases-of-a-penetration-test) —
  actually proving a vulnerability is real and exploitable.
- The core architecture is a clean separation between **exploits**
  (code that takes advantage of a specific known vulnerability to gain
  execution) and **payloads** (what actually runs once that execution is
  gained — a reverse shell, a command execution). This separation means
  a tester doesn't need to write custom exploit code from scratch for
  every engagement — Metasploit's large, maintained module library
  already covers a huge number of known vulnerabilities, each pairable
  with whatever payload the engagement actually needs.
- This is exactly why Metasploit is a dual-use tool in the sharpest
  sense — the same module library that makes legitimate, authorized
  penetration testing dramatically faster is equally usable by an actual
  attacker; it's a tool, not inherently an attack, and its ethical use
  depends entirely on authorization (see
  [Offensive Security & Penetration Testing](offensive-security-and-pentesting.md)
  for the authorized-engagement framing this tool is meant to operate
  within).

## 5. "Hashcat / John the Ripper — how does password cracking actually work, and why does it matter beyond breaking into something?"

**Answer:**

- Both tools take a **captured password hash** (from a breached
  database, or a legitimately authorized security assessment) and
  attempt to find the plaintext that produces it — via a **dictionary
  attack** (trying known common passwords and variations first, since
  real-world passwords cluster heavily around predictable patterns), a
  **brute-force attack** (trying every possible combination, the slowest
  but most exhaustive approach), or a **rainbow table** lookup (already
  covered in
  [Cryptography Fundamentals §5](cryptography-fundamentals.md#5-why-is-hashing-a-password-with-plain-sha-256-the-wrong-approach-even-though-sha-256-itself-is-a-secure-hash-function)).
- This is the direct, practical reason that same page's explanation of
  **why bcrypt/Argon2's deliberate slowness matters** isn't abstract —
  these are the literal tools that slowness is specifically designed to
  defeat. A fast hash (plain SHA-256) lets Hashcat try billions of
  guesses per second against a stolen hash database; a deliberately slow
  one cuts that rate by orders of magnitude, making the same attack
  take impractically long.
- Legitimately, these tools are used in authorized assessments to
  **audit real password strength** — running an organization's own
  hashed password database against these tools (with authorization)
  reveals how many accounts would actually fall to a realistic
  cracking attempt, a concrete, measurable signal rather than a policy
  assumption about "strong password requirements" actually working in
  practice.

## 6. "SIEM platforms — Splunk, the ELK Stack, Microsoft Sentinel — how do these differ as products?"

**Answer:**

- [Security Operations §1](security-operations-and-incident-response.md#1-what-does-a-siem-actually-do-that-individual-service-logs-on-their-own-dont)
  already covers what a SIEM does mechanically — log correlation across
  every source at once. These are the concrete products implementing
  that pattern.
- **Splunk** — a mature, powerful commercial platform with its own
  query language (SPL) for searching and correlating ingested log data;
  widely used in enterprise SOCs, priced by data ingestion volume.
- **ELK Stack (Elasticsearch, Logstash, Kibana)** — the open-source
  alternative: Elasticsearch for storage and search, Logstash for
  ingestion/parsing, Kibana for visualization — more setup and
  operational ownership, no per-GB licensing cost.
- **Microsoft Sentinel** — a cloud-native SIEM built into Azure,
  integrating tightly with Microsoft's own ecosystem (Entra ID,
  Microsoft 365) specifically, relevant disproportionately for
  organizations already standardized on that stack.

## 7. "Digital forensics tools — Autopsy, FTK, Volatility — what problem are these actually solving?"

**Answer:**

- Forensics tools exist to analyze a compromised system **after the
  fact**, specifically in a way that preserves evidence integrity for
  potential legal or formal incident purposes — directly feeding the
  eradication and lessons-learned phases of
  [the incident response lifecycle](security-operations-and-incident-response.md#2-a-siem-fires-an-alert-whats-the-actual-structured-process-that-follows-and-why-does-it-need-to-be-structured-at-all).
- **Chain of custody** is the core discipline underneath all of them: a
  forensic **disk image** (a bit-for-bit copy of storage, taken through
  a write-blocker that physically prevents any accidental modification
  during imaging) is hashed immediately after creation, so its integrity
  — that it genuinely wasn't altered during analysis — can be
  cryptographically proven later, the same hash-verification mechanism
  already covered in
  [Cryptography Fundamentals](cryptography-fundamentals.md), applied here
  to evidence integrity instead of password storage.
- **Autopsy / FTK** analyze that disk image — recovering deleted files,
  examining file system metadata, reconstructing a timeline of activity.
- **Volatility** specifically analyzes a **memory dump** (RAM captured
  from a running or recently-running system) rather than disk — catching
  evidence that only ever existed in memory and was never written to
  disk at all, such as a process actively running at the moment of
  compromise or an encryption key only ever held in RAM.

## Summary: Security Check → Tooling

| Check type | Tools | Deeper coverage |
|---|---|---|
| Known-vulnerability scanning | Nessus, OpenVAS, Qualys | [Offensive Security §1](offensive-security-and-pentesting.md#1-whats-the-actual-difference-between-a-vulnerability-scan-and-a-real-penetration-test) |
| Network/packet analysis | nmap (+ NSE), Wireshark, tcpdump | [Network Security Fundamentals §4](network-security-fundamentals.md#4-what-do-nmap-and-wireshark-actually-do-and-when-would-you-reach-for-each) |
| Web app security (manual + automated) | Burp Suite, OWASP ZAP | [The OWASP Top 10, In Depth](owasp-top-10-in-depth.md) |
| Exploitation | Metasploit | [Offensive Security & Penetration Testing](offensive-security-and-pentesting.md) |
| Password strength auditing | Hashcat, John the Ripper | [Cryptography Fundamentals §5](cryptography-fundamentals.md#5-why-is-hashing-a-password-with-plain-sha-256-the-wrong-approach-even-though-sha-256-itself-is-a-secure-hash-function) |
| Log correlation / SIEM | Splunk, ELK Stack, Microsoft Sentinel | [Security Operations & Incident Response](security-operations-and-incident-response.md) |
| Cloud posture (CSPM) | AWS Config, Wiz, Prisma Cloud | [Cloud Security Fundamentals §2](cloud-security-fundamentals.md#2-what-does-cloud-security-posture-management-cspm-actually-do-as-a-category-of-tool) |
| Disk/memory forensics | Autopsy, FTK, Volatility | — |
| Dependency/supply chain scanning | Snyk, Dependabot | [The OWASP Top 10 §2](owasp-top-10-in-depth.md#2-what-does-vulnerable-and-outdated-components-actually-mean-as-a-practical-risk-not-just-update-your-dependencies) |

---

## Code Samples

No dedicated code samples for this page.
