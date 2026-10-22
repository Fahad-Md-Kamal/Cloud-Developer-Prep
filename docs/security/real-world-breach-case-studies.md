---
title: "Real-World Breach Case Studies (2023–2025)"
---

# Real-World Breach Case Studies (2023–2025)

Every mechanism covered elsewhere in this track is abstract until it's
the reason a real organization lost real money and real trust. These
five incidents are recent (within the last 2-3 years), extensively
publicly documented, and each one maps cleanly onto a specific
mechanism covered earlier in this track — not random trivia, but
evidence that these failure modes are exactly what actually happens at
scale.

!!! note "On the numbers below"

    Breach costs and affected-user counts routinely get revised as
    litigation, regulatory filings, and follow-up investigation
    progress — treat every figure below as "as publicly reported," not
    a final, uncontested number, and verify current figures before
    citing them as precise facts in anything beyond general discussion.

## 1. MOVEit Transfer — One Zero-Day, Thousands of Downstream Breaches (2023)

**What happened:** The Clop ransomware group exploited a previously
unknown SQL injection vulnerability (CVE-2023-34362) in Progress
Software's MOVEit Transfer — a widely used file-transfer product — in
May-June 2023, extracting data directly from any organization running
the vulnerable version.

**The numbers:** Tracking organizations reported over 2,500
organizations and more than 60 million individuals affected across the
full campaign — among them British Airways, the BBC, Shell, the UK's
and US's largest payroll providers, and numerous US state government
agencies. Progress Software itself faced significant shareholder and
customer litigation in the aftermath.

**The mechanism:** A single injection vulnerability (see
[The OWASP Top 10 §A03](owasp-top-10-in-depth.md) and
[Security Hardening §1](../architecture/security-hardening.md#1-input-validation-and-injection-prevention))
in one widely-deployed third-party product became thousands of separate
breaches simultaneously — the real-world scale of
[vulnerable and outdated components §2](owasp-top-10-in-depth.md#2-what-does-vulnerable-and-outdated-components-actually-mean-as-a-practical-risk-not-just-update-your-dependencies)
as a supply chain risk, not a single-organization failure.

## 2. Change Healthcare — Missing MFA, National Healthcare Disruption (2024)

**What happened:** A ransomware affiliate (linked to ALPHV/BlackCat)
gained initial access to Change Healthcare — a UnitedHealth subsidiary
that processes a large share of US healthcare billing and insurance
claims — reportedly through a system that lacked multi-factor
authentication, then deployed ransomware across the environment in
February 2024.

**The numbers:** The attack disrupted pharmacy and claims processing
across the US healthcare system for weeks. UnitedHealth disclosed
paying a reported $22 million ransom, with total company-reported
financial impact (response costs, system restoration, business
disruption) running into the billions of dollars. UnitedHealth's own
later disclosures put the number of individuals whose data was affected
at well over 100 million — among the largest healthcare data breaches
in US history.

**The mechanism:** The entry point traces back to one missing control —
multi-factor authentication — on a single system, the exact gap covered
in [Identity Security §2](identity-security-zero-trust-and-pam.md#2-mfa-exists-but-not-all-mfa-is-equally-strong-whats-actually-different-between-the-common-methods).
The scale of downstream disruption is also a direct illustration of why
[the incident response lifecycle](security-operations-and-incident-response.md#2-a-siem-fires-an-alert-whats-the-actual-structured-process-that-follows-and-why-does-it-need-to-be-structured-at-all)
matters at critical-infrastructure scale, not just for one company.

## 3. The Snowflake Customer Campaign — AT&T, Ticketmaster & Shared Responsibility (2024)

**What happened:** Attackers used credentials stolen via infostealer
malware — not any vulnerability in Snowflake's own platform — to log
into customer accounts on the Snowflake data platform that had **no MFA
enabled**, then exfiltrated data directly from those customers' own data
warehouses. Reporting attributed this to well over 100 affected
Snowflake customer organizations.

**The numbers:** AT&T disclosed theft of call and text metadata (who
contacted whom, and when — not message content) for nearly all of its
roughly 110 million wireless customers, covering a period in 2022.
Ticketmaster/Live Nation had data reportedly covering 560 million
customer records offered for sale. AT&T was separately reported to have
paid an extortion payment in the low hundreds of thousands of dollars
in an attempt to have the stolen data deleted.

**The mechanism:** This is the single clearest real-world illustration
of [the shared responsibility model](cloud-security-fundamentals.md#1-what-does-the-shared-responsibility-model-actually-mean-in-practice-beyond-the-diagram-every-provider-shows)
available: Snowflake's own infrastructure was never compromised — every
single one of these breaches traces back to the *customer's* side of
the line, specifically the absence of MFA covered in
[Identity Security §2](identity-security-zero-trust-and-pam.md#2-mfa-exists-but-not-all-mfa-is-equally-strong-whats-actually-different-between-the-common-methods).
A secure platform does not make an insecurely configured customer
account safe.

## 4. Microsoft Storm-0558 — A Stolen Signing Key (2023)

**What happened:** A China-linked threat actor (tracked as Storm-0558)
obtained a Microsoft cryptographic signing key and exploited a token
validation flaw to forge authentication tokens, gaining access to
Exchange Online and Outlook Web Access email accounts — including those
of senior US government officials — across roughly 25 organizations,
discovered in mid-2023.

**The numbers:** The direct financial cost was never the headline here
— the impact was access to sensitive US government communications,
including the US Secretary of Commerce's email. The US Cyber Safety
Review Board (CSRB) conducted a formal investigation and concluded the
intrusion was preventable, citing a cascade of Microsoft security
failures including inadequate logging that delayed detection.

**The mechanism:** This is a direct, real-world consequence of
[digital signatures](cryptography-fundamentals.md#4-whats-a-digital-signature-and-how-is-it-different-from-encryption)
as a trust anchor — the entire authentication system's integrity rested
on that one signing key never being compromised or usable beyond its
intended scope, and once it was, forged tokens were indistinguishable
from genuine ones. The CSRB's specific finding on logging gaps is also
a direct, real consequence of
[Security Operations §1](security-operations-and-incident-response.md#1-what-does-a-siem-actually-do-that-individual-service-logs-on-their-own-dont)'s
core point — detection depends entirely on actually having the right
logs to correlate in the first place.

## 5. 23andMe — 14,000 Compromised Accounts, 6.9 Million Exposed Profiles (2023)

**What happened:** Attackers used **credential stuffing** — login/password
combinations leaked from *other, unrelated* past breaches, tried against
23andMe's login — to directly access roughly 14,000 accounts whose
owners had reused a previously leaked password. Because of 23andMe's
opt-in "DNA Relatives" feature connecting genetic relatives' profiles to
each other, the attacker was able to scrape data belonging to
approximately 6.9 million users total, far beyond the accounts actually
broken into directly.

**The numbers:** The breach led to dozens of lawsuits and a roughly $30
million class-action settlement, and the resulting reputational and
legal damage was a significant factor in 23andMe's subsequent financial
collapse, culminating in a Chapter 11 bankruptcy filing in March 2025.

**The mechanism:** Not a hack of 23andMe's systems in the traditional
sense — no vulnerability was exploited — just weak account-level
credential hygiene at scale, exactly the risk MFA exists to close (see
[Identity Security §2](identity-security-zero-trust-and-pam.md#2-mfa-exists-but-not-all-mfa-is-equally-strong-whats-actually-different-between-the-common-methods)).
The roughly 500x gap between accounts directly compromised (14,000) and
profiles ultimately exposed (6.9 million) is the real lesson: a feature
that connects users' data together multiplies the blast radius of even
a comparatively small initial compromise — a design-level risk worth
weighing explicitly, the same
[insecure design](owasp-top-10-in-depth.md#1-whats-insecure-design-and-how-is-it-different-from-a-specific-implementation-bug-like-injection)
category covered earlier in this track.

## Summary: Mechanism → Real-World Incident

| Mechanism | Incident | Where it's covered |
|---|---|---|
| Injection / vulnerable components | MOVEit Transfer (2023) | [OWASP Top 10](owasp-top-10-in-depth.md) |
| Missing MFA, ransomware | Change Healthcare (2024) | [Identity Security](identity-security-zero-trust-and-pam.md) |
| Missing MFA, shared responsibility | Snowflake customer campaign (2024) | [Cloud Security Fundamentals](cloud-security-fundamentals.md) |
| Compromised signing key | Microsoft Storm-0558 (2023) | [Cryptography Fundamentals](cryptography-fundamentals.md) |
| Credential stuffing, blast-radius design | 23andMe (2023) | [Identity Security](identity-security-zero-trust-and-pam.md) |

---

## Code Samples

No dedicated code samples for this page.
