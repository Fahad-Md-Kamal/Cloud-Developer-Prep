---
title: "Why LLMs Hallucinate"
---

# Why LLMs Hallucinate

"The model made something up" is the single most common complaint about
LLMs in production — and the most common wrong mental model for it is
"the model lied" or "the model got confused." Neither framing is quite
right. This page covers why hallucination happens as a direct
consequence of how generation works (see
[How LLMs Actually Work](how-llms-actually-work.md) first if you haven't),
not as a malfunction of it.

## 1. "What is a hallucination, precisely, and why does it happen at all?"

**Answer:**

- A hallucination is fluent, confident, structurally correct output
  that is factually wrong — a citation that doesn't exist, a function
  that was never in the library, a statistic that was never published.
- The root cause is the training objective itself: a model is trained
  to predict the **most plausible next token**, not to verify a claim
  against ground truth before producing it. There is no step in
  generation that checks "is this actually true" — plausibility and
  truth are correlated most of the time, which is exactly why the model
  is usually right, but they are not the same thing.
- A hallucinated sentence and a correct sentence are produced by the
  *exact same mechanism* — the model has no internal flag that lights
  up differently for one versus the other. That's what makes
  hallucination hard to catch from the output alone: it reads exactly as
  confidently as a correct answer, because confidence of phrasing was
  never what the model was optimizing for truth with.

!!! success "The one-line interview answer"

    A model hallucinates because it was trained to produce the most
    probable next word, not to check facts — confident and correct are
    two separate things it never learned to distinguish between.

## 2. "Why can't a bigger, more capable model just fix this?"

**Answer:**

- Bigger, better-trained models do hallucinate less often on average —
  but "less often" isn't "never," because the underlying mechanism
  (predict the plausible next token) hasn't changed, only how good the
  model is at it.
- Specific, structural reasons hallucination doesn't go to zero with
  scale:
    - **Knowledge cutoff** — anything after the training data was
      collected simply isn't known, and a model asked about it will
      often produce something plausible-sounding rather than cleanly
      admitting it has no idea.
    - **Long-tail facts** — a fact mentioned once, in one obscure
      source, is far less reliably "learned" than a fact repeated across
      thousands of training documents — the model's confidence in its
      own output doesn't reliably track how well-represented that fact
      actually was in training.
    - **No access to ground truth at inference time** — without
      retrieval (RAG) or a tool call, the model is answering purely from
      what got compressed into its weights during training, with no way
      to look anything up and check.

## 3. "Is there a difference between a hallucinated fact and a confidently wrong chain of reasoning?"

**Answer:**

- Same underlying cause, different surface — both are the model
  producing the most plausible-*looking* continuation, whether that's a
  fact or a line of reasoning.
- A fluent, well-structured chain-of-thought trace (see
  [Prompt Engineering & Context Management §2](prompt-engineering.md#2-a-multi-step-reasoning-task-a-word-problem-a-multi-part-policy-question-keeps-getting-the-wrong-final-answer-what-do-you-try-before-assuming-the-model-cant-do-it))
  can reach a wrong conclusion while reading exactly as convincingly as
  one that reaches a correct one — the trace is itself generated text,
  subject to the same plausible-not-necessarily-true dynamic as any
  other output.
- Practical implication: treating a model's own explanation of its
  reasoning as proof of correctness is the same mistake as treating
  confident phrasing as proof of a correct fact — neither is a reliable
  signal on its own.

## 4. "How do you actually reduce hallucination in a real product?"

**Answer — there's no single fix, so layer several:**

- **Ground answers in retrieval** — [RAG](rag-and-vector-databases.md)
  gives the model actual source text to work from instead of relying
  purely on what's compressed into its weights, and lets you require
  citations back to that source — a claim with no matching retrieved
  passage is a strong hallucination signal on its own.
- **Make "I don't know" an acceptable answer** — a system prompt that
  explicitly permits and rewards admitting uncertainty reduces the
  pressure toward confidently guessing; a model implicitly trained to
  always produce *some* answer will often produce a plausible-sounding
  wrong one rather than decline.
- **Constrain the output where possible** — [structured
  output](prompt-engineering.md#3-downstream-code-needs-to-parse-the-models-output-programmatically-how-do-you-get-reliable-structured-output-instead-of-prose-the-code-has-to-regex-out)
  that requires a source field alongside a claim makes "no source" a
  visible, checkable gap, rather than letting an unsupported claim blend
  invisibly into fluent prose.
- **Add an independent verification pass** — a second model call (or a
  deterministic check against a database/API) that specifically checks
  claims in the first response, for anything where a wrong answer has
  real consequences.
- **Human-in-the-loop for high-stakes output** — the same architectural
  principle as defending against
  [prompt injection](prompt-engineering.md#4-your-application-takes-untrusted-user-input-and-feeds-it-into-a-prompt-that-also-has-system-instructions-and-possibly-tool-access-whats-the-actual-attack-and-how-do-you-defend-against-it):
  treat this as defense in depth, not a single setting to toggle on.

## 5. "Can you detect a hallucination automatically, without a human reading every response?"

**Answer:**

- **Self-consistency sampling** — generate the same answer multiple
  times (with some temperature) and check agreement; a fact the model is
  genuinely confident about tends to come out the same way repeatedly,
  while a hallucinated detail is more likely to vary across samples,
  since it isn't anchored to anything real.
- **Retrieval-grounded verification** — check whether the claim is
  actually supported by a retrieved source passage, rather than trusting
  the model's own citation; a model can hallucinate a citation that
  looks real but doesn't actually say what's claimed.
- **LLM-as-judge fact-checking** — a second model call scoring whether a
  claim is supported — useful, but inherits the same blind spots
  flagged in
  [Designing Adaptive AI Interview Systems §3](adaptive-ai-interview-systems.md#3-how-do-you-actually-score-a-candidates-answer-in-real-time-to-drive-that-adaptation):
  a judge model can be fooled by the same fluent confidence a human
  reviewer would be.
- None of these reach 100% — they reduce the rate and catch more cases,
  which is why production systems combine several rather than relying on
  any single detector.

| Pros | Cons / Trade-offs |
|---|---|
| Grounding in retrieval with required citations catches most unsupported claims | Still relies on retrieval quality — a bad retrieval set can "ground" a wrong answer in the wrong source |
| Self-consistency sampling needs no external data, just repeated calls | Extra cost/latency — multiple generations per answer instead of one |
| LLM-as-judge verification scales far better than human review | Inherits the same blind spots and confident-wrong failure mode as any other LLM output |

---

## Code Samples

No dedicated code samples for this page — it's conceptual, not a
runnable system.
