---
title: "Fine-Tuning & the Model Training Lifecycle"
---

# Fine-Tuning & the Model Training Lifecycle

Every other page in this section treats a model as a finished artifact
you call through an API. This page covers how it got that way — the
stages between "a pile of text" and "a model that follows instructions
and refuses to help with a bomb" — and the practical question that
actually comes up in interviews: when do you fine-tune at all, instead
of just prompting or retrieving?

## 1. "What are the actual stages a model goes through before it's the thing you call via an API?"

**Answer:**

- **Pretraining** — the model learns to predict the next token over a
  huge, broad corpus of text, with no human-written labels at all (see
  §2). This is where the vast majority of compute and cost goes, and
  where general language ability and world knowledge come from.
- **Supervised fine-tuning (SFT)** — the pretrained model is further
  trained on a much smaller set of human-written example conversations
  (a prompt and a high-quality response), teaching it to behave like an
  assistant that follows instructions, instead of just completing text
  the way pretraining alone would.
- **Preference alignment (RLHF/DPO)** — a further pass that tunes the
  model toward responses humans actually *prefer*, not just responses
  that look like the SFT examples (see §4) — this is where behaviors
  like refusing harmful requests or being appropriately concise get
  reinforced.
- **(Optional) task-specific fine-tuning** — what most people mean by
  "fine-tuning" in a product context: taking that already-aligned model
  and adapting it further on your own narrow data (§3-5).

!!! success "The exam/interview framing"

    A model you call via an API has already been through the first
    three stages by the provider. "Fine-tuning" in a job description
    almost always means the fourth stage — adapting an already-capable
    model to a narrower task, not training one from scratch.

## 2. "What is pretraining actually learning, and why does it need so much data and compute?"

**Answer:**

- The training objective is deceptively simple: given a huge amount of
  real text, predict the next token at every position (see
  [How LLMs Actually Work §1](how-llms-actually-work.md#1-what-actually-happens-between-sending-a-prompt-and-getting-a-response-back)
  for the mechanism this is actually running).
- It's **self-supervised** — the "label" for every training example is
  just the next word in text that already exists, so no human has to
  hand-label anything. That's exactly why it can scale to a huge corpus:
  the entire readable internet and more becomes usable training data
  with zero manual annotation.
- To get good at this one narrow-sounding task at genuinely massive
  scale, the model has to implicitly absorb grammar, facts, reasoning
  patterns, and style — predicting the next word of a physics textbook
  well enough to be consistently right requires something that behaves
  a lot like understanding physics, even though "understand physics"
  was never the stated goal.
- This is also why pretraining has a **knowledge cutoff**: whatever
  happened after the training corpus was collected simply isn't in
  there to learn from — a fact covered in the hallucination page.

## 3. "What's the actual difference between prompting, RAG, and fine-tuning — when do you really need to fine-tune?"

**Answer:**

- These solve three genuinely different problems, and the single most
  common mistake is reaching for fine-tuning to fix something prompting
  or retrieval would fix more cheaply.
- **Prompting** changes *instructions* for one call — use it for
  anything expressible as "here's what I want you to do," which is most
  tasks.
- **RAG** changes what *facts/knowledge* the model has access to for one
  call (see [RAG & Vector Databases](rag-and-vector-databases.md)) — use
  it when the model needs information it wasn't trained on, or
  information that changes over time.
- **Fine-tuning** changes the model's *underlying behavior* — its
  default tone, its output format, a narrow skill it doesn't reliably
  do out of the box — use it when that behavior needs to be consistent
  across every call without re-stating a long instruction every time, or
  when the task is too subtle to fully specify in a prompt (matching a
  very particular writing style from hundreds of examples, rather than a
  describable rule).
- The misconception worth correcting explicitly: fine-tuning is a poor,
  expensive way to teach a model new *facts* — those facts get baked
  into weights in a way that's hard to verify, hard to update, and
  doesn't give you a citation back to a source. RAG is almost always the
  right tool for "the model needs to know X," and fine-tuning is the
  right tool for "the model needs to consistently behave like Y."

| | Changes | Good for | Cost to maintain |
|---|---|---|---|
| Prompting | Instructions, per call | Most tasks — the default starting point | Free to iterate, but repeated on every call |
| RAG | Available facts, per call | Knowledge that's large, changes over time, or needs citations | Needs a retrieval pipeline, but facts stay current and verifiable |
| Fine-tuning | The model's default behavior | Consistent tone/format/narrow skill, compressing a long repeated prompt | Needs training data and a retraining pass to update |

## 4. "What is RLHF, mechanically, and why not just supervised fine-tune on only the best examples?"

**Answer:**

- Supervised fine-tuning alone only teaches the model to imitate the
  *specific examples* it was shown — it has no signal about *why* one
  plausible response is better than another similarly plausible one.
- **RLHF (Reinforcement Learning from Human Feedback)** adds that
  signal in two steps: first, train a separate **reward model** on human
  preference data — pairs of responses where a person judged "A is
  better than B" — so the reward model learns to score any response's
  quality. Then, use that reward model to further train the main model
  via reinforcement learning (commonly PPO), nudging it to produce
  outputs the reward model scores highly.
- The reason this works better than collecting more labeled "ideal"
  answers directly: humans are much more reliable at *relative*
  judgments ("which of these two is better") than at producing or
  scoring an absolute "ideal" response from scratch — comparison is an
  easier, more consistent task to crowdsource at scale.
- **DPO (Direct Preference Optimization)** is a newer, simpler
  alternative that skips training a separate reward model and the RL
  loop entirely — it optimizes the model directly on the same
  preference pairs using a more direct loss function, reaching a similar
  effect with meaningfully less infrastructure and instability than
  full RLHF.

## 5. "What is LoRA, and why does it matter practically for fine-tuning?"

**Answer:**

- **Full fine-tuning** updates every single weight in the model — for a
  model with tens of billions of parameters, that means enough GPU
  memory to hold the full model, its gradients, and optimizer state all
  at once, and a full new copy of the model's weights for every separate
  task you fine-tune for.
- **LoRA (Low-Rank Adaptation)** freezes the original model's weights
  entirely and instead trains a small pair of additional low-rank
  matrices injected alongside each frozen weight matrix — the frozen
  weights never change; only this small add-on does.
- This cuts the number of trainable parameters by orders of magnitude
  (often under 1% of the full model), which means fine-tuning that
  would otherwise need a multi-GPU cluster can run on a single GPU, and
  storing a fine-tuned "version" per task means storing just the small
  LoRA adapter, not a full duplicate copy of the entire model.
- The practical consequence: a team can maintain many narrow,
  task-specific adapters cheaply, swapping which one sits on top of the
  same shared frozen base model at inference time, instead of hosting a
  full separate fine-tuned model per task.

**Likely follow-up — "what's the risk of fine-tuning at all?"**

- **Catastrophic forgetting** — fine-tuning hard on a narrow dataset can
  degrade the model's broader general ability, since the weights are
  being pulled toward the new, narrow distribution of examples.
- This is one more reason LoRA's lighter touch (and techniques like
  mixing in some general-purpose data during fine-tuning) matter in
  practice — a full, aggressive fine-tune is the fastest way to end up
  with a model that's great at the one task and worse at everything
  else than the base model was.

| Pros | Cons / Trade-offs |
|---|---|
| LoRA cuts fine-tuning cost and GPU requirements by orders of magnitude | A slightly weaker fit than full fine-tuning on the hardest adaptation tasks |
| Small adapters mean many task-specific variants without duplicating the full model | Still needs real, well-curated training data — not a free lunch over prompting |
| DPO skips the reward-model + RL infrastructure RLHF needs | Fine-tuning any kind risks catastrophic forgetting if not managed carefully |

---

## Code Samples

No dedicated code samples for this page — it's training-process
background, not a runnable system.
