---
title: "Types of AI Models & What They Actually Cost"
---

# Types of AI Models & What They Actually Cost

If you've never worked with AI models before, this page genuinely
starts from zero — before types, before cost, before anything else:
what an AI model actually *is*.

## 1. "What even is an 'AI model,' in the most basic possible terms?"

**Answer:**

- Ordinary software runs on rules a person wrote by hand — "if the
  password matches, let them in." Every case was thought through and
  explicitly coded by someone.
- An AI model is built differently: instead of a person writing the
  rules, the model is shown a huge number of examples with known
  correct answers, and it works out its *own* rules by adjusting itself
  to get more of those examples right. That process is called
  **training** — covered next.
- What the finished model actually *is*, once trained, is a large
  collection of numbers — often millions or billions of them, called
  **parameters** (or **weights**). There's no human-readable rulebook
  hiding inside it anywhere — just these numbers, tuned during training
  to produce good answers.
- "Using" the model afterward means feeding it new input and letting
  those already-tuned numbers produce an output — the exact same basic
  mechanism whether that output ends up being "yes," "no," or a full
  working program.

## 2. "What does 'training' actually involve, step by step?"

**Answer:**

- Gather a large set of examples with known correct answers — this is
  the **training data** ("here are 50,000 emails, each already labeled
  spam or not spam").
- Let the model guess on each example, compare its guess to the real
  answer, and nudge its internal numbers slightly toward getting it
  right next time — repeated across every example, many times over.
- Once training finishes, the model's numbers stop changing — it's
  "frozen" and ready to be used on brand-new input it's never seen
  before, ideally still getting it right because it learned the actual
  pattern, not just memorized the training examples themselves.
- A trained model only ever knows what showed up in its training data —
  this is also the root cause behind
  [why LLMs hallucinate](why-llms-hallucinate.md), covered in full
  later in this section, once the generation-specific mechanism is
  built up.

## 3. "Given that, what actually makes different AI models different from each other?"

**Answer:**

- Mainly **what kind of examples a model was trained on, and what kind
  of answer it was trained to produce.** This is the real source of
  every "type" distinction that follows.
- A model trained on emails already labeled spam/not-spam learns to
  output one of two labels — a **classification** model.
- A model trained on enormous amounts of ordinary written text learns
  to predict "what word plausibly comes next" — and doing that over and
  over, one word at a time, is what lets it write entire new sentences,
  paragraphs, or code.
- Different training purpose → different kind of output → (covered
  next) different cost to actually run.

## 4. "What's actually different between a 'yes/no' model and a 'code generating' model?"

**Answer:**

- Often, nothing about the model itself — the same underlying AI model
  can answer a yes/no question *and* write a program. What changes is
  how much it has to **output** to do each task.
- A yes/no question ("is this email spam?") only needs the model to
  write back one or two words. A code-generation request needs the
  model to write back dozens or hundreds of lines.
- Since you're charged for how much text goes in **and** how much
  comes out — and the text that comes *out* costs noticeably more per
  word than the text that goes *in* — a task that barely outputs
  anything costs barely anything, and a task that outputs a lot costs a
  lot. Same model, wildly different bill, purely because of how much it
  had to write.

## 5. "Beyond just 'cheap vs. expensive,' what are the actual categories of AI models?"

**Answer — the shapes you'll actually run into:**

- **Classification models** — pick one answer from a small, fixed list:
  yes/no, spam/not-spam, positive/negative/neutral. The output is
  always tiny — one word or a short label — so these are consistently
  the cheapest kind of task to run.
- **Text generation models** — write open-ended text: a chat reply, a
  summary, an email draft. The output can be short or long depending on
  what you ask for.
- **Code generation models** — write programs. Functionally a text
  generation model, just asked to write code instead of prose — and
  code output tends to run long, which is exactly why this category
  shows up as "expensive" in practice.
- **Embedding models** — don't write any text back at all. They turn
  your input into a list of numbers representing its meaning, used for
  search and matching rather than conversation. See
  [Embeddings & Semantic Search](embeddings-semantic-search.md) for
  what that's actually for — worth knowing here mainly because this
  category is usually the *cheapest* of all, since there's no text
  output to pay for at all, just a small, fixed-size number list.
- **Image/audio generation models** — produce an image, a sound clip, or
  a video instead of text. Covered separately below, because they're
  priced in a genuinely different way.

## 6. "Why exactly does a 'yes/no' question cost almost nothing — walk through the actual math?"

**Answer:**

- [LLM APIs & Providers §3](llm-apis-and-providers.md#3-what-actually-drives-llm-api-cost-and-how-do-you-estimate-it-before-shipping-a-feature)
  already covers the real formula: cost = (text you send in × its
  price) + (text you get back × its price) — and the price per word
  for what comes *back* is typically 2-4x higher than for what goes
  *in*.
- A classification call might send in 500 words of text to classify,
  but get back just one word ("spam"). Even though the output word is
  priced higher per-word, there's so little of it that the bill is
  almost entirely just the cost of the 500 words you sent in — and
  that's already a small number.
- A code-generation call might send in only 50 words (your request),
  but get back 1,500 words of actual code. Now the *expensive* output
  side completely dominates the bill — this is the entire reason code
  generation costs noticeably more than a quick yes/no check, even
  though the request itself was shorter.

## 7. "Does a yes/no task actually need the same, expensive AI model as code generation?"

**Answer:**

- Usually not, and this is the second real cost lever, on top of
  output length: simple tasks like classification often don't need a
  large, expensive model at all — a small, fast, cheap model is
  frequently just as accurate for "is this spam," while code generation
  genuinely benefits from a larger, more capable one.
- This is exactly the idea behind
  [routing simple queries to a cheap model and only using an expensive
  one when the task actually needs it](llm-gateway-multi-provider.md#6-beyond-routing-by-provider-health-or-cost-how-do-you-cut-spend-on-queries-that-dont-need-your-best-model) —
  picking the cheapest model that can reliably do a given job is one of
  the single biggest cost-saving decisions in working with AI at all,
  bigger than almost any other optimization.

## 8. "What about models that generate images, audio, or video — priced the same way?"

**Answer:**

- No — this is a genuinely different pricing model, not just "more
  text." Image, audio, and video generation models are usually priced
  **per image generated**, or **per second of audio/video produced**,
  not per word, because there's no natural "word" unit for a picture or
  a sound the way there is for text.
- Worth knowing as its own fact rather than assuming it follows the
  same per-word math as everything else above — a single generated
  image can cost noticeably more than an entire page of generated text,
  simply because it's priced on a completely different unit.

## 9. "So what's the one thing actually worth remembering about AI model costs?"

**Answer:**

- Cost comes down to two decisions, and almost everything else is
  detail: **how much output the task actually needs** (a short answer
  costs little, a long one costs a lot), and **how big/capable a model
  the task actually needs** (don't reach for the most expensive model
  by default — reach for the cheapest one that can still do the job
  reliably).
- Every other page on this site about AI cost — from
  [token counting](llm-apis-and-providers.md#5-how-do-you-count-and-manage-tokens-before-sending-a-request-and-why-does-it-matter)
  to [caching repeated queries](llm-response-caching.md) to
  [model routing by complexity](llm-gateway-multi-provider.md#6-beyond-routing-by-provider-health-or-cost-how-do-you-cut-spend-on-queries-that-dont-need-your-best-model) —
  is really a more detailed version of one of those two levers.

| Model type | What it outputs | Typical cost | Why |
|---|---|---|---|
| Classification (yes/no, labels) | One word or short label | Lowest | Almost nothing to write back |
| Embeddings | A fixed-size list of numbers | Very low | No text output at all |
| Text generation (chat, summaries) | A sentence to a few paragraphs | Moderate | Output length varies with the ask |
| Code generation | Dozens to hundreds of lines | High | Output is usually long by nature |
| Image/audio/video generation | A picture, clip, or video | Priced per item, not per word | A genuinely different pricing unit |

---

## Code Samples

No dedicated code samples for this page — see
[LLM APIs & Providers](llm-apis-and-providers.md#code-samples) for a
real, runnable cost-tracking example.
