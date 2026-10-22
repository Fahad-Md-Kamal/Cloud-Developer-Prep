---
title: "How LLMs Actually Work: Tokens, Attention & Generation"
---

# How LLMs Actually Work: Tokens, Attention & Generation

Every other page in this section — prompting, caching, RAG, agents,
tool-calling — treats the LLM as a box you send text into and get text
back from. That's fine for building with one, but several facts
everywhere else on this site get asserted without being explained:
why token count isn't word count, why "lost in the middle" happens, what
temperature actually changes, why a context window is a hard wall and
not just a setting. This page is the mechanism underneath all of that.

## 1. "What actually happens between sending a prompt and getting a response back?"

**Answer — the pipeline, at a high level:**

- **Tokenize** — the input text is split into tokens (see §2), each
  mapped to an integer ID from the model's fixed vocabulary.
- **Embed** — each token ID is looked up in an embedding table,
  producing a vector that represents that token, plus a positional
  signal added so the model knows *where* in the sequence each token
  sits (without it, "dog bites man" and "man bites dog" would look
  identical to the model).
- **Transform** — those vectors pass through many stacked layers, each
  combining **self-attention** (§3) with a small feedforward network —
  this is where the actual "understanding" happens, as each token's
  representation gets updated based on every other token's.
- **Predict** — the final layer produces a probability distribution
  over the entire vocabulary for "what token comes next."
- **Sample** — one token is chosen from that distribution (§4), appended
  to the sequence, and the whole process repeats to generate the next
  one — this is why generation happens one token at a time, not all at
  once.
- **Detokenize** — once generation stops, the chosen token IDs are
  converted back into text.

!!! success "The one-sentence version"

    An LLM doesn't "think up" a reply and then write it down — it
    repeatedly answers one narrow question, "given everything so far,
    what's the single most probable next token," and the illusion of a
    coherent, reasoned answer emerges from doing that thousands of times
    in a row.

## 2. "What is a token, really, and why doesn't token count match word count?"

```text
"unbelievable"      -> ["un", "believ", "able"]        (3 tokens)
"The cat sat."       -> ["The", " cat", " sat", "."]    (4 tokens)
"অবিশ্বাস্য"          -> many more tokens than its English gloss
```

**Answer:**

- Tokens are **subword units**, not whole words — produced by an
  algorithm like Byte-Pair Encoding (BPE) that starts from individual
  characters and repeatedly merges the most frequent adjacent pair,
  trained once on a huge text corpus until it reaches a fixed vocabulary
  size (commonly 50K-100K+ entries).
- Subword splitting solves a real problem whole-word tokenization can't:
  a fixed vocabulary of whole words either explodes in size or can't
  represent a word it's never seen. Subwords let the model represent
  *any* string — a rare word, a typo, a made-up word — by breaking it
  into pieces it has seen, instead of hitting a hard "unknown word"
  wall.
- This is exactly why [token-counting before sending a
  request](llm-apis-and-providers.md#5-how-do-you-count-and-manage-tokens-before-sending-a-request-and-why-does-it-matter)
  matters, and why it isn't just "count the words": common English
  words are often one token, but rarer words, code, and — notably —
  most non-English languages split into *several* tokens per word,
  since the vocabulary was trained on a corpus dominated by English
  text. The practical consequence: the same sentence meaning costs more
  tokens (more money, more context-window budget) in a language the
  tokenizer saw less of during training.

## 3. "What is self-attention, and why is it the mechanism that made transformers work?"

**Answer:**

- The core idea: for every token, self-attention lets it "look at"
  every other token in the sequence and decide how much each one
  matters for understanding *this* token, before updating its own
  representation accordingly.
- Mechanically, each token produces three vectors — a **Query** (what
  am I looking for), a **Key** (what do I offer), and a **Value** (what
  information do I actually carry). A token's updated representation is
  a weighted sum of every other token's Value, where the weights come
  from how well this token's Query matches each other token's Key.
- Concretely: in "the trophy didn't fit in the suitcase because **it**
  was too big," resolving what "it" refers to requires attention to
  weigh "trophy" far more heavily than "suitcase" (or vice versa, in
  the "because it was too small" version) — one word's meaning depends
  on a specific other word, regardless of how far apart they sit in the
  sentence.
- This is the real reason transformers replaced the previous generation
  of sequence models (RNNs): an RNN processes tokens one at a time *in
  order*, so token 500 only learns about token 1 after passing through
  499 intermediate steps, and that signal degrades over distance.
  Self-attention lets every token connect to every other token
  directly, in one step, regardless of distance — and because there's
  no inherent sequential dependency, the whole computation parallelizes
  across a GPU instead of being forced to run step-by-step.
- The direct payoff elsewhere on this site:
  ["lost in the middle"](rag-and-vector-databases.md#3-how-do-you-decide-what-to-include-in-the-context-window-and-what-happens-when-everything-relevant-doesnt-fit)
  — content buried in the middle of a long context getting attended to
  less reliably than content at the start or end — is an empirical
  attention-pattern phenomenon, not a bug; attention weights aren't
  perfectly uniform across position in practice, and models show a
  measurable bias toward the sequence's edges.

## 4. "Why does an LLM generate one token at a time, and what does 'temperature' actually control?"

```python
import math

def softmax_with_temperature(logits: list[float], temperature: float) -> list[float]:
    scaled = [x / temperature for x in logits]
    exp_vals = [math.exp(x) for x in scaled]
    total = sum(exp_vals)
    return [v / total for v in exp_vals]

# temperature < 1 sharpens the distribution (more confident, more deterministic)
# temperature > 1 flattens it (more randomness, more varied output)
```

**Answer:**

- This is called **autoregressive generation**: the model predicts a
  probability distribution over its entire vocabulary for "what's the
  next token," one token gets chosen, it's appended to the input, and
  the model runs again on the new, longer sequence — repeated until it
  emits a stop token or hits a length limit.
- **Temperature** scales the raw output scores (logits) before they're
  turned into probabilities via softmax. Dividing by a temperature
  below 1 makes the highest-scoring tokens even more dominant (closer
  to always picking the single most likely token — more deterministic,
  more repetitive). Dividing by a temperature above 1 flattens the
  distribution, giving lower-probability tokens a real chance of being
  picked — more varied, but also more likely to wander off-topic.
- **Greedy decoding** (always pick the single highest-probability
  token, equivalent to temperature → 0) sounds like it should be best,
  but in practice tends to produce flatter, more repetitive, sometimes
  factually worse text than sampling with modest randomness — always
  taking the locally-best next token isn't the same as producing the
  best overall sequence.
- **Top-k** (only sample from the k highest-probability tokens) and
  **top-p/nucleus sampling** (sample from the smallest set of tokens
  whose probabilities sum past p) are both ways to bound *how much*
  randomness temperature is allowed to reach into, cutting off the long
  tail of implausible tokens rather than letting temperature alone
  decide.
- Practical consequence worth knowing: "temperature 0" is not
  perfectly deterministic in production on most hosted APIs — batching,
  floating-point non-associativity, and hardware-level parallelism can
  still produce tiny numerical differences run to run, even with
  identical input and temperature=0.

## 5. "Why is the context window a hard architectural limit, not just a configuration setting?"

**Answer:**

- Self-attention's actual cost comes from every token needing to be
  compared against every other token — that's a number of comparisons
  that grows roughly with the *square* of the sequence length, not
  linearly with it.
- Doubling the context length doesn't double the compute and memory
  cost of attention — it roughly quadruples it. This is the real reason
  large context windows were historically expensive and rare, and why
  "just make the context window bigger" isn't a free knob to turn —
  it's a direct, steep cost trade-off baked into the architecture
  itself.
- This is also why context-window size varies so much between models
  and keeps improving over time: newer models use engineering
  workarounds (sparse/local attention patterns, memory-efficient
  attention implementations, architectural changes) specifically to
  push this cost curve down, not because the fundamental quadratic
  relationship went away.
- This is the mechanism underneath the practical token-budgeting advice
  in
  [Prompt Engineering & Context Management](prompt-engineering.md#5-a-long-running-chat-conversation-eventually-blows-past-the-models-context-window-how-do-you-keep-it-going-without-just-truncating-history-and-losing-earlier-context)
  and the RAG-vs-long-context trade-off in
  [RAG & Vector Databases](rag-and-vector-databases.md#3-how-do-you-decide-what-to-include-in-the-context-window-and-what-happens-when-everything-relevant-doesnt-fit) —
  a bigger context window is never free, even when it technically fits
  what you want to put in it.

## 6. "When an agent 'decides' to call a tool, is it actually reasoning about that decision?"

**Answer:**

- Not in the sense of a separate decision-making module — tool-calling
  is the *same* next-token-prediction mechanism as everything else,
  applied to a model that's been specifically fine-tuned to recognize
  when a specially-formatted output (a structured call to a named
  function, with arguments) is the right thing to generate next.
- Concretely: instead of generating prose, the model generates tokens
  that happen to form valid, schema-matching structured output (the
  same mechanism behind
  [schema-constrained structured output](prompt-engineering.md#3-downstream-code-needs-to-parse-the-models-output-programmatically-how-do-you-get-reliable-structured-output-instead-of-prose-the-code-has-to-regex-out)
  generally) — the calling application recognizes that shape, actually
  executes the function, and feeds the result back into the model's
  context as if it were just more conversation text.
- This explains why tool descriptions matter so much in practice (see
  [LangChain Agents §2](langchain-agents.md#2-tool-integration-and-custom-tool-creation-how-do-you-build-a-custom-tool-and-what-actually-makes-an-agent-pick-the-right-one)):
  the model isn't consulting a real decision tree over your actual
  available tools — it's pattern-matching the current context against
  what it learned, during fine-tuning, tends to precede a
  tool-call-shaped output. A vague or overlapping tool description
  genuinely confuses that pattern match, the same way an ambiguous
  prompt confuses any other generation.
- It also explains why an agent can confidently call a tool that
  doesn't exist, or call the right tool with plausible-looking but
  wrong arguments — there's no built-in verification step inside
  generation itself that checks "does this tool actually exist" before
  the tokens are produced; that check has to happen in the calling
  code, after the fact.

---

## Code Samples

No dedicated code samples for this page — it's architectural
background, not a runnable system. See
[Embeddings & Semantic Search](embeddings-semantic-search.md) for how
this same transformer machinery gets adapted to produce similarity
vectors instead of generated text.
