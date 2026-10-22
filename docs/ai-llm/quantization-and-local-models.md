---
title: "Quantization & Running Models Locally"
---

# Quantization & Running Models Locally

"Download a model and run it on your laptop" is possible today largely
because of one technique: quantization. Before getting to the actual
tools (GGUF, llama.cpp, Ollama), this page covers what quantization is
actually doing to a model's weights and why that trade-off works as well
as it does — the "depth before tools" the rest of this topic deserves.

## 1. "What does 'quantization' actually mean for a model, mechanically?"

**Answer:**

- A model's weights are just a huge number of floating-point numbers —
  commonly stored at 16-bit precision (FP16/BF16) after training.
- **Quantization** reduces the numerical precision used to store (and
  often compute with) those weights — down to 8-bit integers, or even
  4-bit, instead of 16-bit floats.
- This shrinks memory footprint roughly in proportion to the precision
  drop (a 4-bit quantized model takes roughly a quarter of the memory of
  its 16-bit original) and speeds up computation, since moving and
  multiplying smaller numbers is cheaper on real hardware.
- **Why this doesn't just break the model:** neural network weights are
  surprisingly tolerant of small numerical perturbation — a weight's
  exact value to many decimal places usually matters far less than its
  approximate magnitude and sign relative to its neighbors. Quantization
  exploits exactly that tolerance, rounding each weight to the nearest
  representable value in a much smaller numeric range, which measurably
  degrades precision but rarely breaks the model's behavior outright.
- The trade-off is real, not free: more aggressive quantization (4-bit
  and below) does cost some output quality, and that cost is uneven —
  it tends to show up more on tasks requiring precise reasoning or rare
  knowledge than on fluent conversational text.

## 2. "Why does a larger quantized model often outperform a smaller full-precision one at the same memory budget?"

**Answer:**

- Model capability scales with the number of parameters more reliably
  than it scales with numeric precision — a model with more parameters
  generally "knows" and can do more, even if each individual weight is
  stored less precisely.
- At a fixed memory budget, you're choosing between "fewer parameters,
  stored precisely" and "more parameters, stored approximately" — and in
  practice, the larger-but-quantized option usually wins, because the
  quality lost to quantization's rounding is smaller than the quality
  gained from the extra parameters.
- This is why "download the biggest model you can fit, quantized" is
  the practical rule of thumb for running something locally, rather than
  "download the most precisely-stored model that fits."

## 3. "What is GGUF, and what problem does it actually solve?"

**Answer:**

- **GGUF** is a file format (the successor to the earlier GGML format)
  that packages a quantized model's weights, its metadata (architecture,
  tokenizer, quantization scheme used), and everything needed to load
  and run it into a single portable file.
- Before a standard format like this, every quantization effort was its
  own bespoke setup — GGUF makes a quantized model a single file that
  "just works" across any inference tool built to read the format,
  similar in spirit to how a `.docx` file works across different word
  processors without each one needing its own conversion step.
- A single model is typically published in several GGUF variants at
  different quantization levels (commonly named like `Q4_K_M`, `Q5_K_M`,
  `Q8_0`) — the letter/number naming encodes the bit-width and the
  specific quantization method used, trading file size and speed against
  output quality, so you pick the variant that fits your actual
  hardware and quality bar rather than there being one "correct" choice.

## 4. "llama.cpp vs. Ollama — what's actually different between them?"

**Answer:**

- **llama.cpp** is the underlying inference engine — C/C++ code that
  loads a GGUF model and actually runs the forward pass (the same
  mechanism covered in
  [How LLMs Actually Work](how-llms-actually-work.md#1-what-actually-happens-between-sending-a-prompt-and-getting-a-response-back)),
  optimized to run efficiently on ordinary CPUs and consumer GPUs rather
  than requiring the kind of data-center hardware the original
  full-precision model was trained and served on.
- **Ollama** is a higher-level wrapper built on top of an engine like
  this — it adds a simple CLI and local API (`ollama pull llama3`,
  `ollama run llama3`), model management that feels like pulling a
  Docker image, and automatic handling of which quantization/hardware
  configuration to use, so the end user doesn't need to hand-pick a
  specific GGUF file or compile anything themselves.
- The relationship is the mechanism-then-tool pattern this whole page is
  built around: llama.cpp is what makes running a quantized model on a
  laptop possible at all; Ollama is what makes doing so convenient.

## 5. "When would you actually self-host a local/open-weight model instead of calling a hosted API?"

**Answer:**

- This is the same underlying trade-off already covered for embedding
  models specifically in
  [Embeddings & Semantic Search §3](embeddings-semantic-search.md#3-sentence-transformersminilm-vs-a-full-llm-like-mistralllama-for-generating-embeddings-whats-the-difference),
  generalized to full generative models.
- **Cost at volume** — a self-hosted model running on owned or rented
  hardware can beat per-token API pricing once request volume is high
  enough to amortize the hardware cost.
- **Data residency/privacy** — some data genuinely can't leave your own
  infrastructure, ruling out a third-party API regardless of its
  capability.
- **Offline/air-gapped requirements** — a system that needs to function
  with no network access at all has no other option.
- **Latency-sensitive paths** — a local call avoids the network
  round-trip a hosted API always pays.
- Against all of that: a hosted frontier model is almost always more
  capable than what you can practically run locally, and self-hosting
  means owning the serving infrastructure, scaling, and updates yourself
  instead of a vendor handling it — the same ownership trade-off that
  shows up anywhere "managed service vs. self-hosted" comes up.

| Pros | Cons / Trade-offs |
|---|---|
| Quantization makes running a capable model on consumer hardware possible at all | Output quality degrades, more at aggressive (4-bit and below) quantization levels |
| GGUF's single-file packaging makes a quantized model portable across tools | Picking the right quantization variant for your hardware/quality bar takes some trial and error |
| Self-hosting avoids per-token API cost at volume and keeps data in your own infrastructure | Hosted frontier models are usually more capable than anything practical to self-host locally |
| Ollama removes the setup friction of llama.cpp for everyday use | Less fine-grained control than configuring the underlying engine directly |

---

## Code Samples

No dedicated code samples for this page — the tools above are meant to
be run directly (`ollama run <model>`), not wrapped in application code.
