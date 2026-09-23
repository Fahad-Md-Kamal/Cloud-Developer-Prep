---
title: "RAG & Vector Databases"
---

# RAG & Vector Databases

Retrieval-Augmented Generation architecture end to end: chunking and
preprocessing documents, assembling context within a token budget,
choosing and scaling a vector database, and the advanced retrieval
patterns (multi-step retrieval, query expansion, hybrid search,
real-time index updates) that go beyond a single similarity-search call.
For embedding *model* selection specifically — Sentence-Transformers vs.
generative models, self-hosting trade-offs — see
[Embeddings & Semantic Search](embeddings-semantic-search.md#3-sentence-transformersminilm-vs-a-full-llm-like-mistralllama-for-generating-embeddings-whats-the-difference).

## 1. "Walk me through a RAG pipeline end to end — what actually happens between a user's question and the final answer?"

```python
async def rag_pipeline(query: str) -> str:
    # 1. Embed the query with the same model used to embed the corpus
    query_embedding = await embed_query(query)

    # 2. Vector similarity search for candidate chunks
    candidates = await vector_db.similarity_search(query_embedding, k=20)

    # 3. Re-rank/filter down to the most relevant subset
    relevant_docs = await rerank_documents(query, candidates)

    # 4. Assemble a context block within the model's token budget
    context = assemble_context(relevant_docs, max_tokens=4000)

    # 5. Generate the answer grounded in that context
    return await generate_response(query, context)
```

**Answer:** Five stages, and the failure mode at each stage is
different, which is why "the RAG system is wrong" is rarely one bug.
Query embedding uses the *same* embedding model the corpus was indexed
with — a mismatch there silently tanks recall because the two vector
spaces aren't comparable. The similarity search over-fetches (`k=20`
when you only need ~5) because raw vector similarity is a noisy
relevance signal on its own. Re-ranking narrows that noisy candidate set
down using a stronger, more expensive signal — a cross-encoder, an LLM
call, or metadata rules. Context assembly fits the *survivors* into the
generation model's context window, in priority order, and the
generation step is a normal LLM call with an explicit instruction to
answer from the provided context. The whole point of separating
retrieval from generation is that each stage is independently
debuggable: a bad answer with the right sources in context is a
generation/prompting bug, a bad answer with the wrong sources in context
is a retrieval bug.

**Likely follow-up — "why retrieve 20 candidates and re-rank down to 5
instead of just retrieving 5 directly?"** Vector similarity search
optimizes for *recall* at low latency — cheap, approximate, and prone to
returning near-misses that are lexically or topically related but not
actually the best answer. A re-ranker (typically a cross-encoder that
scores the query and each candidate jointly, which is more accurate but
too slow to run over the whole corpus) trades a small amount of extra
latency on a small candidate set for a large precision gain on the
handful of chunks that actually make it into the prompt.

| Pros | Cons / Trade-offs |
|---|---|
| Grounds generation in retrieved facts, cutting hallucination vs. relying on parametric knowledge alone | Answer quality is bounded by retrieval quality — a perfect generator can't fix a bad retrieval set |
| Retrieve-then-rerank separates a cheap recall step from an expensive precision step | Extra re-ranking hop adds latency the naive "just embed and search" pipeline doesn't have |
| Each stage (embed, retrieve, rerank, assemble, generate) is independently testable | More moving parts than a single LLM call — more places for something to silently degrade |

## 2. "How do you chunk documents for RAG, and what breaks if you get chunk size wrong?"

```python
def semantic_chunking(document: str, max_chunk_size: int = 512) -> list[str]:
    sentences = split_into_sentences(document)
    chunks, current = [], []

    for sentence in sentences:
        if len(" ".join(current + [sentence])) <= max_chunk_size:
            current.append(sentence)
        else:
            if current:
                chunks.append(" ".join(current))
            current = [sentence]

    if current:
        chunks.append(" ".join(current))
    return chunks
```

**Answer:** Chunking is a trade-off between semantic coherence and
retrieval granularity, and getting it wrong shows up as a specific,
recognizable symptom. Chunks too large (a whole document section)
dilute the embedding — a chunk covering five different sub-topics
produces a vector that's mediocre-similar to queries about any one of
them, so it under-ranks even when it contains the answer. Chunks too
small (a single sentence) lose the surrounding context needed to make
sense of the sentence on its own — "it must be filed within 30 days"
retrieved without the paragraph that says what "it" refers to is
useless. The common middle ground is sentence- or paragraph-boundary
chunking with a target size (a few hundred tokens) and a small overlap
between consecutive chunks, so a sentence that would otherwise sit right
at a chunk boundary still has its immediate context in at least one of
the neighboring chunks.

**Likely follow-up — "would you use the same chunking strategy for every
document type?"** No — structure should drive the split where it's
available. Headings-and-sections documents (docs, wikis) chunk cleanly
along their own structure (recursive chunking by heading, falling back
to sentence-boundary within a section). Loosely structured text falls
back to sentence-boundary chunking with overlap. Short, already-atomic
content (a product title, an FAQ answer) often shouldn't be chunked at
all — chunking a single sentence just to hit a target size adds no
value. The one thing that should carry through every strategy is
metadata: source, section heading, position in the parent document —
because you need it later both to reconstruct context around a
retrieved chunk and to attribute the answer back to its source.

| Pros | Cons / Trade-offs |
|---|---|
| Structure-aware (heading/section) chunking preserves semantic coherence better than fixed-size splitting | Requires the document to actually have usable structure — plain text or scanned PDFs don't |
| Overlap between chunks protects against losing context at a boundary | Overlap means the same content is stored (and embedded) more than once — more index size and cost |
| Smaller chunks improve retrieval precision (less dilution per chunk) | Smaller chunks lose surrounding context and multiply the total chunk count, both of which can hurt |

## 3. "How do you decide what to include in the context window, and what happens when everything relevant doesn't fit?"

```python
def assemble_context(documents: list[Document], max_tokens: int = 4000) -> str:
    parts, used = [], 0
    for doc in sorted(documents, key=lambda d: d.score, reverse=True):
        doc_tokens = estimate_tokens(doc.content)
        if used + doc_tokens > max_tokens:
            break
        parts.append(f"Source: {doc.metadata['source']}\n{doc.content}")
        used += doc_tokens
    return "\n\n---\n\n".join(parts)
```

**Answer:** Context assembly is a budgeting problem: rank retrieved
chunks by relevance score, then greedily add them to the prompt until
the token budget for context is exhausted, leaving separate budget for
the system prompt, the conversation history, and the generation itself.
The chunks that don't fit are simply dropped — which is why over-fetch
and re-rank (question 1) matters so much: if re-ranking put the actually
useful chunk in position 3, it survives a budget that only fits 5; if
it's in position 15 out of 20 raw candidates, it doesn't. Ordering
inside the assembled context also matters for generation quality, not
just which chunks make the cut — putting the single most relevant chunk
first (or, for some models, last, immediately before the question) tends
to get it attended to more reliably than burying it in the middle of a
long context block, an effect sometimes called "lost in the middle."

**Likely follow-up — "when do you stuff more into the context window
instead of retrieving more precisely?"** This is really the RAG-vs-long-context
question. Larger context windows on modern models make "just include
everything" tempting, but it doesn't remove the trade-off: bigger
context means higher latency and cost per call (you pay per token
whether or not the model uses it), and retrieval quality still matters
because a large but poorly-ranked context has the same "lost in the
middle" problem, just with a bigger haystack. RAG earns its cost when
the corpus is far larger than any context window (a legal corpus,
company-wide documentation) or when the answer needs to be grounded and
attributable to specific sources — retrieval keeps both the prompt and
the citation trail small and precise. Stuffing more into context is
reasonable for corpora that genuinely fit (a single document, a small
codebase) where the retrieval step would only add latency without
improving on "the model can just read all of it." See
[Prompt Engineering & Context Management](prompt-engineering.md#6-when-do-you-reach-for-rag-retrieval-vs-just-putting-more-into-the-context-window)
for the budgeting side of this same question.

| Pros | Cons / Trade-offs |
|---|---|
| Relevance-ordered greedy assembly is simple and keeps the most useful chunks even under a tight budget | Chunks that don't fit are silently dropped — a real answer can be in the corpus and never reach the prompt |
| Source attribution per chunk enables citations and audit trails | Formatting overhead (source labels, separators) eats into the same token budget as the content |
| Placing the top-ranked chunk first/last mitigates "lost in the middle" | Requires re-testing prompt layout per model — attention-to-position behavior isn't identical across models |

## 4. "How do you choose a vector database, and what actually differs between them?"

```python
class VectorDatabase:
    def __init__(self, provider: str, config: dict):
        self.provider = provider
        self.client = self._init_client(provider, config)

    async def similarity_search(self, query_embedding, k: int, filters: dict | None = None):
        # Provider-specific call — the interface stays the same either way
        ...
```

**Answer:** The practical differences are managed-vs-self-hosted,
filtering/hybrid-search capability, and operational maturity — not raw
similarity-search correctness, which is table stakes across all of
them. Pinecone is a fully managed service — good when you want scaling
and ops handled for you and are fine with the vendor lock-in and
per-vector cost. Qdrant and Weaviate are strong self-hosted options —
Qdrant for a fast, filter-heavy workload with a smaller resource
footprint, Weaviate for built-in hybrid (vector + keyword) search and a
GraphQL API. Milvus targets distributed, very-large-scale deployments
where sharding is a first-class concern. Chroma is the easiest to get
running locally for prototyping but is the least battle-tested at
production scale. The selection criteria that actually matter for a
production system are query latency at your real vector count,
horizontal scaling story, metadata-filtering expressiveness (can it
combine "similar to this vector" with "where tenant_id = X" efficiently,
not as a post-filter), and how it fits your existing ops footprint — a
team already running Kubernetes will operate a self-hosted Qdrant
cluster very differently than a team that wants zero infra to manage.

**Likely follow-up — "what index type would you pick, and does that
choice change with scale?"** Yes — index choice is a function of corpus
size and the latency/accuracy trade-off you're willing to make, not a
one-time decision. Flat (brute-force exact search) is fine and actually
preferable under roughly 100K vectors — it's exact and there's no index
to tune. HNSW (graph-based approximate nearest neighbor) is the default
for the 100K–10M range — very good recall at low latency, at the cost of
memory (the graph structure lives in RAM). Beyond that, IVF combined
with product quantization trades some accuracy for dramatically lower
memory by compressing vectors, which matters once the raw vectors
themselves no longer fit affordably in memory. This mirrors an ordinary
database indexing decision: a full scan is fine on a small table, and
you reach for a more complex index only once scale demands it.

| Pros | Cons / Trade-offs |
|---|---|
| Managed services (Pinecone) remove index tuning and scaling ops entirely | Managed services cost more per vector at volume and add a hard external dependency |
| Self-hosted options (Qdrant, Weaviate, Milvus) give full control over indexing, filtering, and cost | You own uptime, backups, upgrades, and capacity planning yourself |
| HNSW gives near-exact recall at low latency for the common mid-size range | HNSW's graph lives in memory — cost scales with vector count long before disk would be the bottleneck |
| Metadata filtering combined with vector search enables precise, access-controlled retrieval | Filter expressiveness and performance vary a lot between providers — verify it isn't just a slow post-filter |

## 5. "Pure vector similarity missed an obviously-relevant document that shares exact keywords with the query — how do you fix that class of problem?"

```python
async def hybrid_search(query: str, filters: dict, k: int = 10) -> list[Document]:
    dense = await vector_search(embed_query(query), k=k * 2)
    sparse = await keyword_search(query, k=k * 2)          # BM25 / TF-IDF
    combined = combine_results(dense, sparse)               # e.g. reciprocal rank fusion
    filtered = apply_filters(combined, filters)
    return rerank_final_results(query, filtered, k=k)
```

**Answer:** This is the known weak spot of pure embedding similarity —
it captures semantic meaning well but can under-rank a document that's
an exact keyword/ID/code match if the surrounding phrasing differs
enough that the embeddings drift apart. Hybrid search runs both a dense
retriever (vector similarity, good at "these mean the same thing") and a
sparse retriever (BM25/TF-IDF, good at "these share the exact terms")
in parallel, then fuses the two ranked lists — commonly with reciprocal
rank fusion, which combines rank positions rather than trying to
normalize two differently-scaled similarity scores directly. Metadata
filters (date range, category, access permissions) are then applied as
a genuine filter on top, not another scored signal to blend in.

**Likely follow-up — "why not just always use hybrid search — is there a
downside?"** Extra cost and complexity for a gain that's workload-dependent.
Running two retrieval paths means maintaining two indexes (or one index
that supports both), and merging their results is an extra step with its
own tuning (the fusion weighting between dense and sparse). For
workloads that are inherently conceptual — "find documents about this
general topic" — vector search alone usually already covers it well and
sparse search adds little. Hybrid search earns its cost specifically
where users query with exact terms that matter — product SKUs, legal
citations, error codes, proper nouns — where a pure semantic match can
plausibly rank the literal match below a merely-related document.

| Pros | Cons / Trade-offs |
|---|---|
| Catches exact-term/keyword matches that pure vector similarity can under-rank | Two retrieval paths to run, tune, and keep in sync instead of one |
| Reciprocal rank fusion avoids the pitfall of blending two differently-scaled similarity scores | Fusion weighting is itself a tunable that needs real query data to get right |
| Metadata filters compose cleanly on top for access control and structured constraints | Adds latency (two searches + a fusion + re-rank) versus a single vector search |

## 6. "A query needs information that no single retrieved chunk contains on its own — how do you handle multi-hop questions?"

```python
async def multi_step_retrieval(query: str) -> str:
    sub_queries = await decompose_query(query)

    context = []
    for sub_query in sub_queries:
        results = await retrieve_documents(sub_query, context)
        context.extend(results)
        if not validate_retrieval_quality(sub_query, results):
            refined = await refine_query(sub_query, context)
            context.extend(await retrieve_documents(refined, context))

    return await generate_final_response(query, context)
```

**Answer:** Single-shot retrieval assumes one query embedding can find
everything the answer needs, which breaks down for questions that
genuinely require chaining facts together — "what's the liability
exposure of a policy that didn't exist when the underlying regulation
was written" needs the regulation, a separate lookup on how it's been
applied since, and a synthesis step, not one similarity search. Multi-step
retrieval decomposes the query into sub-questions, retrieves for each one
in sequence (feeding prior results in as context so later sub-queries can
build on earlier findings), optionally validates and refines a sub-query
that came back with weak results, and only then generates a final answer
over the accumulated context. It's strictly more expensive — each
sub-query is its own retrieval round, and decomposition itself is
typically an LLM call — so it's worth reaching for only when single-shot
retrieval is demonstrably insufficient, not as a default.

**Likely follow-up — "how do you know when a query actually needs this
instead of a normal single retrieval pass?"** In practice, either the
query itself signals it (explicit multi-part questions, comparisons
across sources, "how has X changed since Y") or you find out empirically
— single-shot retrieval quality metrics (see the RAG-evaluation
follow-up below) are consistently poor on a cluster of queries even
though the corpus clearly contains the relevant information split across
multiple documents. A cheap middle ground before committing to full
decomposition: query expansion (below) or simply raising `k` and letting
re-ranking do more work — multi-step retrieval is the heavier answer for
when those don't close the gap.

| Pros | Cons / Trade-offs |
|---|---|
| Handles genuinely compositional questions a single similarity search can't answer | Multiple sequential retrieval rounds — meaningfully higher latency and LLM-call cost per query |
| Feeding earlier results into later sub-queries lets retrieval build on itself | Query decomposition quality is itself an LLM call that can decompose badly |
| Refinement step catches and retries a sub-query that came back weak | Harder to reason about and test than a deterministic single-pass pipeline |

## 7. "Users search with different vocabulary than the corpus uses — how do you improve recall for that?"

**Answer:** Query expansion — generate related terms, synonyms, and
contextual variations of the original query and search on the expanded
set, not just the literal query text. This matters most in domains with
jargon, acronyms, or multiple valid ways to say the same thing: a search
for "conversion optimization" should also surface documents about "CRO,"
"funnel optimization," or "A/B testing" even if the query never used
those exact words. Expansion sources range from a domain-specific
synonym list (cheap, deterministic, good for known acronyms and
terminology) to an LLM call that generates plausible related phrasings
of the query (more flexible, catches cases a static list wouldn't, but
non-deterministic and adds latency). Expanded queries are typically
searched in parallel and their results merged, similar to hybrid search
above, rather than concatenated into one giant query string.

**Likely follow-up — "can query expansion hurt more than it helps?"**
Yes — over-expansion drags in tangentially related results that dilute
precision, especially with an LLM-generated expansion that drifts from
the original intent. The mitigation is the same re-ranking step used
everywhere else in the pipeline: expand generously for recall, then
re-rank the combined candidate pool against the *original* query (not
the expanded ones) so precision is restored before anything reaches the
context window.

## 8. "The knowledge base needs to reflect new documents within minutes, not after a nightly batch job — how do you support that without downtime?"

**Answer:** Incremental indexing rather than full reindexing — new or
changed documents are embedded and upserted into the vector database as
they arrive (via a queue/background worker), while deletions and updates
apply to just the affected vectors rather than rebuilding the whole
index. The operational risk is a partially-applied update leaving the
index in an inconsistent state, which is why production systems wrap
updates in a version/transaction concept — track a version id, apply the
batch, and roll back cleanly if any part fails, rather than leaving some
new documents indexed and others not. For a change large enough to alter
retrieval behavior broadly (switching embedding models, a major
re-chunking pass), a blue-green approach — build the new index
completely alongside the old one, then cut traffic over — avoids
degrading live search quality mid-rebuild the way an in-place full
reindex would.

**Likely follow-up — "how do you know an update actually helped instead
of quietly hurting retrieval quality?"** The same way you'd validate any
production change: a held-out set of query/expected-document pairs run
against both the old and new index, comparing standard retrieval metrics
(precision@k, recall@k, Mean Reciprocal Rank), plus canarying the update
to a fraction of traffic before a full cutover rather than trusting the
offline metrics alone. Without that check, "we updated the embedding
model" and "retrieval quality quietly dropped" are indistinguishable
until users notice.

---

## Code Samples

- `code_samples/chapter-23/rag_pipeline.py` — a complete end-to-end RAG
  pipeline: query embedding, vector similarity search, context assembly,
  and generation, wired together with mocked embedding/LLM clients so it
  runs standalone.
- `code_samples/chapter-23/vector_databases.py` — a provider-abstraction
  layer over multiple vector databases (mocked Pinecone/Qdrant-style
  clients) covering upsert, similarity search, metadata filtering, and
  index-configuration selection by dataset size.
- `code_samples/chapter-23/advanced_rag_patterns.py` — multi-step
  (decompose-and-refine) retrieval, query expansion, hybrid dense/sparse
  search, and document-relationship-graph-based retrieval expansion.
- `code_samples/chapter-23/document_processing.py` — multi-format
  document parsing (PDF/DOCX/HTML/Markdown, mocked) with semantic
  chunking, overlap handling, and metadata extraction.
- `code_samples/chapter-23/production_rag_system.py` — a production-shaped
  RAG service: caching (mocked Redis), monitoring/metrics hooks, and
  access-control filtering layered around the core pipeline.
