---
title: "Multimodal Models"
---

# Multimodal Models

A model built entirely around "predict the next text token" somehow
also looks at a photo and describes what's in it. This page covers how
that actually works — it turns out to need surprisingly little new
machinery on top of
[everything already covered about how LLMs work](how-llms-actually-work.md)
— before the practical question of when a multimodal model is actually
the right tool versus a simpler pipeline.

## 1. "How does a model that only predicts 'the next token' understand an image at all?"

**Answer:**

- The image is first split into a grid of small patches (a common
  approach, used by Vision Transformers), and each patch is run through
  a vision encoder that converts it into a vector embedding — the same
  kind of fixed-length numeric vector covered in
  [Embeddings & Semantic Search](embeddings-semantic-search.md), just
  produced from image data instead of text.
- Critically, that vision encoder is trained (or aligned via further
  training) so its output embeddings land in the **same vector space**
  the text transformer already operates in — an image patch's embedding
  and a text token's embedding are dimensionally compatible and
  meaningfully comparable, not two separate, unrelated kinds of data.
- Once that's true, the image-patch embeddings are simply interleaved
  into the sequence alongside the text token embeddings, and the rest of
  the transformer proceeds exactly as described in
  [How LLMs Actually Work §3](how-llms-actually-work.md#3-what-is-self-attention-and-why-is-it-the-mechanism-that-made-transformers-work) —
  self-attention lets every token, whether it came from text or an image
  patch, attend to every other token, regardless of which modality it
  originated from.
- The practical upshot: there's no separate "image understanding module"
  bolted onto a text model — the same attention mechanism that relates
  words to each other is relating image patches to words and to each
  other, once both are embedded into one shared space.

## 2. "Is audio input the same idea?"

**Answer:**

- Conceptually, yes — the specific encoding step differs (audio is
  typically processed into a spectrogram or passed through an audio
  encoder that produces a sequence of discrete tokens or embeddings),
  but the pattern is identical: encode the raw modality into the shared
  embedding space, then hand it to the same transformer alongside text.
- This is why adding a new modality to a model is fundamentally an
  encoding problem, not a generation-mechanism problem — once something
  can be reliably turned into embeddings that live in the same space as
  everything else, the self-attention machinery that already exists
  doesn't need to change to make use of it.

## 3. "Native multimodal input vs. a pipeline of separate models (OCR, then a text LLM) — when does each make sense?"

**Answer:**

- A **native multimodal model** processes the actual image directly —
  it sees layout, visual structure, and non-text elements (a chart's
  shape, a diagram's arrows, a table's grid) in one pass, because
  nothing about the image was thrown away before the model ever saw it.
- An **OCR-then-text pipeline** (extract text from the image first, then
  feed that extracted text to a normal text-only LLM) is cheaper and
  simpler, and works fine when the image genuinely only contains text
  worth extracting — a scanned paragraph, a simple label.
- It breaks down for anything where the *visual* structure carries
  meaning OCR discards: a bar chart's actual shape, a flowchart's
  arrows and layout, a form's spatial relationship between a label and
  its filled-in value — OCR hands back flat text with that structure
  gone, and no downstream text model can recover information that was
  never captured to begin with.
- It also compounds errors in a way native multimodal input doesn't: an
  OCR misread becomes the LLM's input, with the LLM having no way to
  notice or correct a transcription mistake it never saw the original
  image to check against.

## 4. "What's a practical, interview-relevant use case for multimodal input?"

**Answer:**

- **Document/invoice/receipt extraction** — reading a scanned invoice
  and extracting structured fields (vendor, amount, date) in one pass,
  using the same
  [structured-output pattern](prompt-engineering.md#3-downstream-code-needs-to-parse-the-models-output-programmatically-how-do-you-get-reliable-structured-output-instead-of-prose-the-code-has-to-regex-out)
  already covered for text, just with an image as part of the input.
- **UI screenshot understanding** — an agent that needs to act on what's
  visually on screen (a specific button's location, a form's current
  state) rather than working from a text description of the UI — the
  visual/"computer-use" extension of the
  [agent loop](agentic-ai-fundamentals.md#1-what-is-agentic-ai-in-plain-terms)
  covered elsewhere in this section.
- **Chart/graph question-answering** — answering a question about a
  chart's actual shape or trend, which genuinely requires seeing the
  image rather than a flattened textual description of its data.

| Pros | Cons / Trade-offs |
|---|---|
| Native multimodal input preserves visual structure OCR-then-text discards | Costs more per call than a pure text model, and image tokens eat into context budget |
| One model call handles both reading and reasoning about an image | Harder to debug than a text pipeline — there's no intermediate "extracted text" to inspect |
| Compounds fewer errors than a two-stage OCR-then-LLM pipeline | Still only as good as the vision encoder's training — unusual image types can degrade quality |
| An OCR-then-text pipeline is cheaper and simpler when the image is purely text | Throws away any non-text visual structure the image actually carried |

---

## Code Samples

No dedicated code samples for this page — multimodal input is typically
a parameter on an existing provider SDK call (passing an image alongside
text) rather than a standalone system.
