---
title: "Testing AI & LLM Applications"
---

# Testing AI & LLM Applications

Every technique on this page so far quietly assumes the system under
test is **deterministic** — same input, same expected output, every
time. An LLM-powered feature breaks that assumption on purpose. This
page covers what actually changes about testing once the system you're
testing can legitimately give a different, still-correct answer to the
same input twice in a row.

## 1. "A traditional test asserts one exact expected output — how do you even write a test for something non-deterministic?"

**Answer:**

- The honest first move: not every part of an AI feature is actually
  non-deterministic. A feature that extracts a structured field from
  text (an invoice total, a classification label) via
  [schema-constrained output](../ai-llm/prompt-engineering.md#3-downstream-code-needs-to-parse-the-models-output-programmatically-how-do-you-get-reliable-structured-output-instead-of-prose-the-code-has-to-regex-out)
  genuinely does have one correct answer, and an exact-match assertion
  is still the right tool for that slice of the feature.
- For genuinely open-ended generation (a summary, a conversational
  reply), the fix is the same reframing
  [Property-Based Testing](property-based-testing.md) already teaches
  for a completely different reason: stop asserting an exact output, and
  assert a **property** the output must satisfy instead — does the
  summary mention the three key facts the source document actually
  contains, does the reply avoid a list of banned terms, is the response
  under a length limit.
- Scoring those properties at scale is exactly what
  [Evaluating LLM Output at Scale](../ai-llm/evaluating-llm-output.md)
  already covers in depth — semantic similarity against a reference
  answer, and LLM-as-judge scoring against an explicit rubric, both of
  which exist specifically because exact-match assertions don't work
  here. This page assumes that mechanism and focuses on how it fits into
  a *testing* workflow specifically, not how the scoring itself works.

## 2. "Is a hallucination a 'bug' — and if so, how do you even track something that doesn't fail the same way every time?"

**Answer:**

- Treat it as a real defect class, but a **probabilistic** one — the
  mechanism behind why it happens at all is covered in
  [Why LLMs Hallucinate](../ai-llm/why-llms-hallucinate.md); the testing
  question is how to track something that doesn't reliably reproduce on
  demand the way a traditional bug does.
- The practical shift: track **failure rate across a test set**, not
  pass/fail on a single run. "This prompt hallucinates a citation on
  roughly 8% of golden-set questions" is an actionable, trackable defect
  report; "it hallucinated once when I tried it" isn't reproducible
  enough to act on the way a traditional bug report needs to be.
- This changes what "fixed" means too — a prompt or retrieval change
  that drops the hallucination rate from 8% to 2% is a real, measurable
  fix, even though it didn't make the failure mode impossible. Expecting
  0% the way you'd expect a deterministic bug to be fully fixed sets the
  wrong bar for this category of defect entirely.

## 3. "How do you regression-test a prompt, the same way you'd regression-test code?"

**Answer:**

- This is [Testing Types & Levels](testing-types-and-levels.md#2-what-does-regression-testing-actually-mean-and-how-do-you-decide-what-to-re-run)'s
  regression-testing discipline, applied to something that isn't code at
  all — a prompt change, a model version bump, or a retrieval-pipeline
  change can all silently break behavior that used to work, the exact
  same risk a code change carries.
- The mechanism is the golden-set-as-CI-gate pattern already covered in
  [Evaluating LLM Output at Scale §2](../ai-llm/evaluating-llm-output.md#2-your-products-task-doesnt-look-like-a-benchmark-question-how-do-you-evaluate-it)
  and
  [LangChain Agents §5](../ai-llm/langchain-agents.md#5-guardrails-evaluation-and-safety-how-do-you-stop-an-agent-from-hallucinating-a-tool-call-or-leaking-sensitive-data-before-it-ships):
  a curated set of real inputs with known-good expected behavior, run
  automatically against every prompt/model/pipeline change, failing the
  build if scores regress past a threshold.
- The failure mode of skipping this is the same one named there too — a
  prompt tweak that fixes one reported complaint quietly regresses three
  other cases nobody was watching, discovered by a user complaint in
  production instead of a CI failure before it ever shipped.

## 4. "What's adversarial/red-team testing for an AI feature, specifically?"

**Answer:**

- The same adversarial mindset [Non-Functional
  Testing](non-functional-testing.md#2-what-does-testing-for-security-actually-mean-for-a-qa-engineer-as-opposed-to-a-developer-preventing-vulnerabilities-in-the-code)
  already applies to SQL injection and broken access control, aimed at
  a new target: deliberately trying to make the model say or do
  something it shouldn't, rather than trying to break application code.
- Concrete things to actually try: **prompt injection** — feeding input
  designed to override the system's instructions (see
  [Prompt Engineering §4](../ai-llm/prompt-engineering.md#4-your-application-takes-untrusted-user-input-and-feeds-it-into-a-prompt-that-also-has-system-instructions-and-possibly-tool-access-whats-the-actual-attack-and-how-do-you-defend-against-it)
  for the attack mechanism this is testing against); attempting to
  extract the system prompt verbatim; trying known **jailbreak**
  phrasings to get the model to ignore its safety guidelines; and
  testing whether a tool-using agent can be tricked into calling a tool
  it shouldn't via injected instructions in tool *output*, not just user
  input.
- The deliverable from a red-team session is the same as any other
  testing effort — a tracked, reproducible set of inputs that currently
  succeed at breaking the system, feeding back into the golden set from
  §3 so a fix for one jailbreak phrasing can be regression-tested against
  all the others, not just re-verified by hand once and forgotten.

## 5. "How do you test an AI feature for bias, not just correctness?"

**Answer:**

- Run the **same underlying question or task** through the system
  multiple times, varying only a dimension that *shouldn't* affect the
  outcome — a name that implies a different gender or ethnicity, a
  neighborhood associated with a different socioeconomic group — and
  check whether the output's substance (a sentiment score, a
  recommendation, an approval decision) changes anyway.
- This is equivalence partitioning from
  [Manual Testing Fundamentals](manual-testing-fundamentals.md#1-you-cant-test-every-possible-input-how-do-you-systematically-pick-which-ones-actually-matter)
  applied with a specific purpose: the test classes here are defined by
  a protected characteristic, and the expected result is explicitly "no
  difference," rather than the usual "correct behavior within this
  class."
- Like hallucination testing in §2, this produces a rate, not a binary
  pass/fail — "outcomes differed on 3% of paired test cases across this
  dimension" is the actionable signal, tracked and trended over time
  the same way a hallucination rate is.

**Likely follow-up — "can an AI tool help generate test cases for this, not just be the thing under test?"**

- Yes, and it's a genuinely current, real practice — an LLM can generate
  a broad first draft of equivalence classes, boundary cases, and
  adversarial phrasings far faster than writing them by hand, which a
  tester then reviews, prunes, and curates rather than accepting
  verbatim. Treat generated test cases with the same scrutiny as any
  other AI output on this page — useful as a starting point, not
  something to trust blindly without a human actually checking the
  cases make sense.

| Pros | Cons / Trade-offs |
|---|---|
| Property-based assertions test what actually matters, not one brittle exact string | Needs real judgment to define the right property — a vague one misses real regressions |
| Tracking failure rate over a golden set gives an actionable, trackable signal for a probabilistic defect | Expecting 0% the way you would for a deterministic bug sets an unrealistic bar |
| Golden-set regression testing catches a prompt/model change silently breaking prior behavior | Needs real upkeep — a stale golden set stops reflecting what the feature actually needs to handle |
| Adversarial/red-team testing finds real jailbreak and injection gaps before users do | No fix is ever complete — new phrasings and attacks keep appearing, same as any security testing |

---

## Code Samples

No dedicated code samples for this page.
