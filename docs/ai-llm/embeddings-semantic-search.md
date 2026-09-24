---
title: Embeddings & Semantic Search
---

# Embeddings & Semantic Search

What an embedding actually is, how similarity search works on top of
them, and where embedding-focused models (Sentence-Transformers, MiniLM)
fit next to generative models (Mistral, LLaMA, Gemma, T5) in a
pre-trained-model landscape. For the retrieval/vector-database side of
this, see [RAG & Vector Databases](rag-and-vector-databases.md).

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
[RAG & Vector Databases](rag-and-vector-databases.md#4-how-do-you-choose-a-vector-database-and-what-actually-differs-between-them))
rather than a brute-force loop over every stored vector.

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

## 4. "General-purpose embeddings aren't retrieving well for a specialized domain (legal, medical, internal jargon) — what do you do before reaching for a bigger model?"

```python
class EmbeddingStrategy:
    def __init__(self, model_name: str, batch_size: int = 32):
        self.model = SentenceTransformer(model_name)
        self.batch_size = batch_size

    def embed_documents(self, documents: list[str]) -> np.ndarray:
        embeddings = []
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            embeddings.extend(self.model.encode(batch, show_progress_bar=False))
        return np.array(embeddings)
```

**Answer:** A general-purpose model like MiniLM is trained on broad,
generic text, so it can genuinely under-perform on vocabulary it rarely
saw in training — legal citation formats, medical terminology, a
company's internal product/acronym jargon — because words that are
semantically distinct in that domain may not have been pushed apart in
the model's training data. Two options, in order of how much effort
they cost: first, try a domain-specific *pre-trained* model if one
exists (Legal-BERT-derived sentence encoders for legal text, PubMedBERT-based
encoders for biomedical text) — someone already did the domain adaptation
work. If nothing suitable exists for your domain, fine-tune a
general-purpose sentence-embedding model on domain pairs (contrastive
fine-tuning on "these two chunks mean the same thing in our domain"
examples) — meaningfully more effort than swapping models, but it directly
teaches the embedding space your domain's actual semantic distinctions
instead of hoping a bigger general model happens to have learned them.
The batching in the snippet above is a separate, purely operational
concern from model choice — encoding documents in batches instead of one
at a time is what makes embedding a large corpus computationally
practical, regardless of which model you're running.

**Likely follow-up — "you fine-tuned or swapped the embedding model in
production — what breaks if you're not careful?"** Every vector already
in the index was produced by the *old* model's embedding space, and a
new model's vectors are not comparable to the old ones — mixing them in
one index silently corrupts similarity search, because "close" in the
new model's space has no defined relationship to "close" in the old
one's. Migrating requires re-embedding the entire corpus with the new
model and treating the switch as a full reindex, not an incremental
update — this is the same blue-green reindexing concern covered in
[RAG & Vector Databases](rag-and-vector-databases.md#8-the-knowledge-base-needs-to-reflect-new-documents-within-minutes-not-after-a-nightly-batch-job-how-do-you-support-that-without-downtime),
and it's why production systems track which model version produced a
given set of vectors rather than assuming the index is always
homogeneous.

| Pros | Cons / Trade-offs |
|---|---|
| A domain-specific pre-trained model is a drop-in swap if one already exists for your domain | Rarely exists for narrow/internal jargon — most teams end up fine-tuning instead |
| Fine-tuning on domain pairs directly teaches the semantic distinctions that matter for your data | Needs labeled/contrastive training pairs and real ML iteration, not just a config change |
| Batched encoding makes embedding large corpora computationally practical regardless of model choice | Batch size is a memory/throughput trade-off that needs tuning per model and hardware |
| — | Swapping or fine-tuning the embedding model invalidates the existing index — requires a full re-embed, not an incremental update |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Sentence-Transformers + similarity-search example added under
`code_samples/`.
