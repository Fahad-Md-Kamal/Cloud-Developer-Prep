---
title: "Evaluating LLM Output at Scale"
---

# Evaluating LLM Output at Scale

"It feels smart when I try it" doesn't scale into "it's safe to ship."
This page covers how evaluation actually works for LLM systems — the
public benchmarks everyone cites, how to build an eval for a task that
doesn't look like a benchmark, and the real failure modes of
LLM-as-judge, which shows up throughout this site (scoring interview
answers, gating a prompt change) without being explained on its own
until now.

## 1. "How do you know if a model is actually good, beyond 'it feels smart'?"

**Answer:**

- Public **benchmarks** give a standardized, comparable number — but
  each one measures something narrow, not "intelligence" in general.
- **MMLU** (Massive Multitask Language Understanding) — multiple-choice
  questions across dozens of academic subjects; measures broad knowledge
  recall, not reasoning or real-world task performance.
- **HumanEval** — a set of programming problems scored by whether
  generated code actually passes real unit tests; a genuinely objective,
  executable measure, but narrow to code-generation-style tasks.
- **Perplexity** — a measure of how "surprised" the model is by real
  held-out text, computed from the probability it assigned to the actual
  next token at each position. Lower perplexity means the model
  consistently assigned higher probability to what actually came next —
  a fluency measure, not a correctness or usefulness measure.
- **Benchmark contamination** is the sharp edge worth knowing: if a
  benchmark's actual questions leaked into a model's training data, it
  can score well by having memorized the answer, not by having the
  underlying skill — a real, recurring credibility problem across the
  industry's published leaderboards, which is why a high benchmark score
  is a weak signal on its own for *your* specific task.

## 2. "Your product's task doesn't look like a benchmark question — how do you evaluate it?"

**Answer:**

- Build a **golden set** — a curated collection of real (or
  realistic) inputs for your actual task, each paired with a known-good
  expected output or a rubric for judging the output.
- Score it with whichever method fits the task:
    - **Exact match** — only works when there's one genuinely correct
      answer (a classification label, an extracted number) — cheap,
      unambiguous, but useless for open-ended text.
    - **Semantic similarity** — embed the generated answer and the
      reference answer (see
      [Embeddings & Semantic Search](embeddings-semantic-search.md)) and
      score by how close they land — tolerant of valid paraphrasing that
      exact match would wrongly fail.
    - **LLM-as-judge** — a model scores the output against a rubric (see
      §3) — the most flexible option, and the only practical one for
      genuinely open-ended output, at the cost of inheriting an LLM's
      own blind spots.
- Run the golden set as a **CI gate** on every prompt or model change —
  the same regression-testing instinct as any other software change,
  applied to prompt/model behavior instead of code behavior. See
  [LangChain Agents §5](langchain-agents.md#5-guardrails-evaluation-and-safety-how-do-you-stop-an-agent-from-hallucinating-a-tool-call-or-leaking-sensitive-data-before-it-ships)
  for where this fits operationally as an actual pipeline gate.

## 3. "What's LLM-as-judge, and what are its real failure modes?"

**Answer:**

- The pattern itself — a model scoring another model's output against a
  rubric — already shows up in
  [Designing Adaptive AI Interview Systems §3](adaptive-ai-interview-systems.md#3-how-do-you-actually-score-a-candidates-answer-in-real-time-to-drive-that-adaptation).
  The failure modes below are what make it a genuinely imperfect
  substitute for human judgment, not just a faster version of it.
- **Position bias** — a judge comparing two answers side by side tends
  to favor whichever is shown first, independent of actual quality.
  Mitigate by randomizing order across judged pairs, or scoring each
  answer independently rather than comparatively.
- **Verbosity bias** — judges systematically rate longer answers higher,
  even when the extra length adds no real information. A rubric that
  explicitly penalizes unnecessary length, rather than one that's silent
  on length, counters this.
- **Self-preference bias** — a model used to judge its own family's
  output tends to rate it more favorably than an equally good answer
  from a different model. Mitigate by using a different model (or
  provider) as the judge than the one being evaluated, where the
  evaluation's stakes justify the extra cost.
- The common thread across all three: a judge model inherits the exact
  same "plausible, not necessarily correct" dynamic covered in
  [Why LLMs Hallucinate](why-llms-hallucinate.md) — it can be
  confidently wrong about a *score* the same way a model can be
  confidently wrong about a *fact*.

| Pros | Cons / Trade-offs |
|---|---|
| Scales to far more evaluations than a human panel ever could | Inherits judge-model biases — position, verbosity, self-preference |
| Works on genuinely open-ended output exact-match/similarity can't score | A specific, detailed rubric is required — a vague one produces inconsistent scores |
| Fast enough to run as a CI gate on every change | Not a substitute for human review on the highest-stakes decisions |

## 4. "What's the difference between offline and online evaluation, and why do you need both?"

**Answer:**

- **Offline evaluation** runs the golden set against a candidate
  change before it ships — catches known regressions fast, cheaply, and
  before any real user sees a bad output.
- **Online evaluation** compares variants against real, live traffic —
  shadowing a new version alongside the current one, or a canary/A/B
  split (see
  [LLM Gateway & Multi-Provider Integration §5](llm-gateway-multi-provider.md#5-how-would-you-ab-test-two-models-or-providers-against-each-other-in-production)
  for the statistical-significance mechanics of running this properly).
- The reason you need both: a golden set only covers the failure modes
  someone already thought to put in it — online evaluation is what
  catches the regression nobody anticipated, because real traffic always
  includes inputs a hand-built golden set didn't.
- The failure mode of skipping the offline gate specifically: a change
  that fixes one reported complaint quietly regresses three other cases
  that weren't being watched, and the first anyone hears about it is a
  user complaint in production — not a CI failure before it ever shipped.

---

## Code Samples

No dedicated code samples for this page — see
[LangChain Agents](langchain-agents.md#code-samples) for related
testing-harness patterns this evaluation approach plugs into.
