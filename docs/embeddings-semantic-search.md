---
title: Embeddings & Semantic Search
---

# Embeddings & Semantic Search

What an embedding actually is, how similarity search works on top of
them, and where embedding-focused models (Sentence-Transformers, MiniLM)
fit next to generative models (Mistral, LLaMA, Gemma, T5) in a
pre-trained-model landscape. For the retrieval/vector-database side of
this, see [Chapter 23: RAG & Vector Databases](chapter-23.md).

## 1. "What is an embedding, concretely?"

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
embedding = model.encode("The quick brown fox jumps over the lazy dog")
# embedding.shape == (384,) -- a fixed-length vector of floats
```

**Answer:** A fixed-length vector of numbers that represents the
*meaning* of a piece of text (or image, or audio), produced by a model
trained so that semantically similar inputs end up close together in
that vector space, and dissimilar inputs end up far apart. "A dog is
running" and "A canine is sprinting" produce embeddings close to each
other despite sharing almost no words in common — the model captured
meaning, not just surface text.

## 2. "How do you measure similarity between two embeddings?"

```python
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

similarity = cosine_similarity(embedding_1, embedding_2)  # -1 to 1, higher = more similar
```

**Answer:** Cosine similarity is the standard metric — it measures the
angle between two vectors, not their magnitude, which matters because
embedding magnitude often reflects something incidental (like text
length) rather than meaning. A cosine similarity near 1 means "nearly
the same meaning," near 0 means "unrelated," negative means "opposite."
At scale, this comparison runs inside a vector database's approximate
nearest-neighbor index (see
[Chapter 23](chapter-23.md)) rather than a brute-force loop over every
stored vector.

## 3. "Sentence-Transformers/MiniLM vs. a full LLM like Mistral/LLaMA for generating embeddings — what's the difference?"

**Answer:** Sentence-Transformers and MiniLM are trained *specifically*
to produce good embeddings — small, fast, and optimized so that
semantic similarity in the output vector space actually reflects
semantic similarity in the input text. Mistral, LLaMA, Gemma, and T5 are
primarily *generative* models (trained to produce fluent text
continuations); they *can* be used to derive embeddings from their
internal representations, but a purpose-built embedding model is
usually smaller, faster, and more accurate for retrieval/similarity
tasks specifically, since that's the only thing it was optimized for.

**Likely follow-up — "when would you self-host one of these models
instead of calling a hosted API (OpenAI embeddings, etc.)?"** Cost at
volume (a self-hosted MiniLM running on your own GPU/CPU can be far
cheaper than per-call API pricing once volume is high enough), data
residency/privacy requirements that rule out sending text to a
third-party API, and latency-sensitive paths where a local model call
beats a network round trip. The trade-off is owning the
serving infrastructure, model updates, and scaling yourself instead of
a vendor handling it.

| Pros | Cons / Trade-offs |
|---|---|
| Purpose-built embedding models (MiniLM, Sentence-Transformers) are small, fast, and cheap to self-host | Smaller models can lag larger/hosted models on nuanced or domain-specific semantic tasks |
| Self-hosting avoids per-call API cost and keeps data in your own infrastructure | You own serving, scaling, and model-update work a hosted API would otherwise handle |
| Cosine similarity search is cheap and well-supported by every vector database | Embedding quality is only as good as the model's training data — domain mismatch degrades results silently |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Sentence-Transformers + similarity-search example added under
`code_samples/`.
