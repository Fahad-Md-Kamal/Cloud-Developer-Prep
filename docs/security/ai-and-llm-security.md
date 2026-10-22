---
title: "AI & LLM Security"
---

# AI & LLM Security

[Testing AI & LLM Applications](../testing/testing-ai-and-llm-applications.md)
covers how to find these problems through testing. This page covers the
same attack surface from the defender's side — what's actually being
exploited, and the architectural mitigations — organized around the
**OWASP Top 10 for LLM Applications**, the field's own emerging
equivalent of the classic web OWASP Top 10 already covered in
[The OWASP Top 10, In Depth](owasp-top-10-in-depth.md).

## 1. "Is there really an OWASP-style list for LLM-specific vulnerabilities?"

**Answer:**

- Yes — OWASP maintains a dedicated Top 10 for LLM Applications, mirroring
  the structure of the classic web list but for failure modes specific
  to language models: prompt injection, insecure output handling,
  training data poisoning, model denial of service, supply chain
  vulnerabilities, sensitive information disclosure, insecure plugin
  design, excessive agency, overreliance, and model theft.
- Several of these map directly onto mechanisms already covered
  elsewhere on this site — this page's job is connecting that existing
  coverage to the security framing specifically, plus the categories
  that haven't had dedicated treatment yet: training data poisoning,
  excessive agency, and model theft.

## 2. "Prompt injection is already covered as a testing concern — what does 'excessive agency' add to that, specifically?"

**Answer:**

- [Prompt Engineering §4](../ai-llm/prompt-engineering.md#4-your-application-takes-untrusted-user-input-and-feeds-it-into-a-prompt-that-also-has-system-instructions-and-possibly-tool-access-whats-the-actual-attack-and-how-do-you-defend-against-it)
  already covers the injection mechanism and its layered mitigations in
  full — nothing to re-derive here.
- **Excessive agency** is the amplifier that turns a successful
  injection from annoying into genuinely dangerous: an agent with broad
  tool permissions (database write access, the ability to send emails,
  payment capability) gives a successful injection a much larger blast
  radius than one against a read-only chatbot with no tool access at all.
- This is the direct LLM-specific application of **least privilege** —
  the same principle already load-bearing in
  [Identity Security §3](identity-security-zero-trust-and-pam.md#3-what-is-privileged-access-management-pam-and-why-does-it-need-to-be-a-distinct-discipline-from-regular-access-control)
  and [Cloud Security §3](cloud-security-fundamentals.md#3-whats-the-actual-mechanism-behind-a-publicly-exposed-s3-bucket-or-database-how-does-this-keep-happening-despite-how-well-known-the-risk-is):
  scope an agent's actual tool access to exactly what the task needs,
  never broader "just in case" — because the
  [tool-calling mechanism itself](../ai-llm/how-llms-actually-work.md#6-when-an-agent-decides-to-call-a-tool-is-it-actually-reasoning-about-that-decision)
  has no built-in verification that a given call is actually
  appropriate; that check has to live in how much capability the agent
  was ever handed in the first place.

## 3. "What is training data poisoning, mechanically, and is it a realistic risk for a RAG-based application specifically?"

**Answer:**

- For a model's actual training/fine-tuning data, poisoning means an
  attacker manages to get malicious or biased examples included in the
  data a model learns from (see
  [Fine-Tuning & the Model Training Lifecycle](../ai-llm/fine-tuning-and-training-lifecycle.md)
  for how that data actually shapes the model) — implanting a backdoor
  behavior or a specific bias that only activates under a particular
  trigger input, invisible under normal use.
- For a **RAG** application specifically, the more realistic version of
  this risk doesn't require touching model training at all — it targets
  the **retrieval corpus** instead. If an attacker can get a document
  into the index a RAG pipeline retrieves from (a public wiki anyone can
  edit, a support ticket system feeding
  [incremental indexing](../ai-llm/rag-and-vector-databases.md#8-the-knowledge-base-needs-to-reflect-new-documents-within-minutes-not-after-a-nightly-batch-job-how-do-you-support-that-without-downtime)),
  the model will confidently retrieve and repeat whatever that document
  says, with the same fluent confidence as any legitimate source —
  because retrieval has no built-in concept of "trustworthy" vs.
  "attacker-controlled," only "similar to the query."
- The mitigation is the same access-control discipline as any other
  ingestion pipeline: validate and restrict who/what can actually write
  into a corpus a production RAG system retrieves from, rather than
  treating retrieval ingestion as a lower-trust-bar operation than it
  actually is.

## 4. "What's model theft/extraction, and is it a genuinely distinct risk from a normal data breach?"

**Answer:**

- **Model extraction** — systematically querying a model (often a
  hosted, paid API) to approximate its behavior closely enough to
  effectively clone its capability without ever accessing its actual
  weights — a real, distinct form of IP theft that doesn't require
  breaching any infrastructure at all, just paying for enough API calls.
- **Training data extraction** — a different, adjacent risk: carefully
  crafted prompts can sometimes cause a model to regurgitate specific
  memorized sequences from its own training data, which is a genuine
  problem when that training data included anything sensitive or
  proprietary.
- Both are distinct from a classic data breach in a meaningful way: no
  database was ever compromised, no credential stolen — the model's own
  completely normal, intended query interface is the entire attack
  surface, which is exactly why rate limiting and usage-pattern
  monitoring on API access (see
  [LLM APIs & Providers §6](../ai-llm/llm-apis-and-providers.md#6-how-do-you-rate-limit-your-own-outgoing-requests-to-a-provider-instead-of-just-reacting-to-429s)
  for the general rate-limiting mechanism, applied here defensively
  rather than for cost control) is a real mitigation layer specifically
  against this category, not just an API-cost concern.

## 5. "Sensitive information disclosure — how is this different from a normal AppSec data leak?"

**Answer:**

- Beyond training-data regurgitation (§4), the LLM-specific version of
  this risk is a **context-isolation** failure, not a classic access-control
  bug: if a system doesn't properly separate conversation context
  between users or sessions, a model can end up with another user's data
  in its context window and — having no inherent concept of "whose data
  is this" — reveal it just as fluently as its own legitimate context.
- This is why the outbound PII scanning already covered in
  [LLM APIs & Providers §9](../ai-llm/llm-apis-and-providers.md#9-what-security-and-compliance-monitoring-is-specific-to-llm-apis-as-opposed-to-a-typical-api)
  matters on **both sides** of the call — not just what leaves the
  network boundary toward a third-party provider, but what the model
  might include in a *response* back to the wrong user, if session/context
  isolation anywhere in the pipeline is ever broken.

| Pros | Cons / Trade-offs |
|---|---|
| Least-privilege tool scoping bounds excessive agency even if injection succeeds | Cuts against giving an agent the broad capability that often makes it genuinely useful |
| Restricting who can write into a RAG corpus closes the realistic poisoning vector | Adds real friction to open, crowdsourced, or rapidly-updated knowledge sources |
| Rate limiting and usage monitoring catch extraction attempts in progress | A determined, patient attacker can stay under naive rate-limiting thresholds |
| Context-isolation discipline prevents cross-user data leakage through the model's response | Easy to get subtly wrong in a multi-tenant system without deliberate, explicit design |

---

## Code Samples

No dedicated code samples for this page.
