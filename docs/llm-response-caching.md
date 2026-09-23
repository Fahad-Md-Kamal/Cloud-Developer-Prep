---
title: "LLM Response Caching: Semantic & Hybrid Caching"
---

# LLM Response Caching: Semantic & Hybrid Caching

Why exact-match caching mostly fails for LLM traffic, and the semantic/
hybrid caching patterns that actually work — plus what "hybrid caching"
means in this context. For a concrete named product implementing this
pattern, see [LangCache](langchain-ecosystem.md#4-langcache-the-named-product-behind-semantic-caching-for-llms).

## 1. "Why doesn't a normal Redis key-value cache work well for caching LLM responses?"

```python
# Exact-match caching -- misses constantly for LLM traffic
cache_key = hashlib.sha256(prompt.encode()).hexdigest()
cached = redis_client.get(cache_key)
```

**Answer:** Exact-match caching only hits when the *literal string* of
a new prompt matches a previously-cached one, byte for byte. LLM inputs
are natural language — "summarize this email" and "please summarize
this email for me" express the same intent but hash to completely
different keys, so the cache hit rate on real traffic is far lower than
the actual amount of redundant, cacheable intent flowing through the
system.

## 2. "Explain semantic caching — how is it different from exact-match caching?"

```python
def semantic_cache_lookup(prompt: str, threshold: float = 0.92):
    query_embedding = embed(prompt)
    candidates = vector_store.search(query_embedding, top_k=1)
    if candidates and candidates[0].score >= threshold:
        return candidates[0].cached_response  # cache hit -- similar enough
    return None  # cache miss -- call the LLM, then store this prompt+response
```

**Answer:** Instead of hashing the literal prompt, semantic caching
embeds it and searches for a *previously cached prompt with a similar
enough embedding* (cosine similarity above a threshold) — "summarize
this email" and "please summarize this email for me" land close enough
in embedding space to hit the same cache entry, even though their exact
text differs.

**Likely follow-up — "what's the risk of setting the similarity
threshold too low?"** A false cache hit — returning a cached response
for a prompt that's *similar* but not actually asking the same thing,
which silently returns a wrong answer instead of a fresh one. The
threshold is a real precision/recall trade-off, not a free efficiency
win — tune it against real traffic, and consider excluding
high-stakes/factual queries from semantic caching entirely if a stale
or mismatched answer would be costly.

## 3. "What's 'hybrid caching' in this context?"

**Answer:** Layering exact-match caching (fast, free of false positives,
catches genuinely repeated queries) with semantic caching (catches
paraphrased/similar queries the exact-match layer would miss) — check
exact-match first since it's cheaper and has no risk of a wrong
semantic match, then fall back to semantic search only on an exact-match
miss. This gets the speed and safety of exact matching for literal
repeats, plus the higher hit rate of semantic matching for the much
larger volume of paraphrased-but-equivalent traffic.

```python
def hybrid_cache_lookup(prompt: str):
    exact_hit = redis_client.get(exact_key(prompt))
    if exact_hit:
        return exact_hit  # cheap, zero false-positive risk

    return semantic_cache_lookup(prompt)  # broader net, tunable risk
```

**Likely follow-up — "how do you invalidate a semantic cache when the
underlying data changes?"** Harder than exact-match invalidation, since
there's no single key to delete — common approaches are a short TTL on
cache entries (accept some staleness, bounded), or tagging cached
entries with the data version/source they depended on and invalidating
by tag when that source changes, rather than trying to invalidate by
prompt content.

| Pros | Cons / Trade-offs |
|---|---|
| Meaningfully higher hit rate than exact-match alone on natural-language traffic | Semantic matches can be wrong — a similarity threshold is a tuned trade-off, not a guarantee |
| Cuts LLM API cost and latency for genuinely repeated intent | Adds an embedding call + vector search to the cache-lookup path itself |
| Hybrid approach keeps exact-match's safety for literal repeats | Invalidation is harder than a simple key delete — needs a TTL or tagging strategy |

## 4. "Is every LLM response worth caching, and how do you pick a TTL?"

```python
def cache_ttl_seconds(request_cost: float, content_volatility: str) -> int:
    # Expensive requests earn a longer TTL -- a cache miss on them is costly.
    # Volatile content (news, prices, anything time-sensitive) earns a
    # shorter one regardless of cost, since a stale answer is actively wrong.
    base_ttl = {"static": 86400, "moderate": 3600, "volatile": 60}[content_volatility]
    if request_cost > 0.10:  # dollars per request
        return base_ttl * 4
    return base_ttl
```

**Answer:** Not automatically — caching is a cost/staleness trade-off,
not a free win. Two independent factors decide the TTL: **request
cost** (an expensive request, e.g. a large-context call against a
premium model, is worth caching longer because a miss is expensive to
recompute) and **content volatility** (a summary of a static
legal-clause template can be cached for days; anything referencing
current events, prices, or user-specific state shouldn't be cached long
regardless of how expensive it was to generate, because a stale
answer isn't just slower — it's wrong). The two factors can conflict —
an expensive *and* volatile request is exactly the case that needs the
most judgment, not just "cache everything expensive."

**Likely follow-up — "what's cache warming, and when is it worth
doing?"** Proactively populating the cache with responses for known
high-frequency queries (common FAQ-style prompts, a fixed set of
report templates run on a schedule) *before* traffic hits them, instead
of waiting for the first real request to pay the cache-miss cost. Worth
doing when a query pattern is predictable and high-volume enough that
the first-request latency/cost hit matters (e.g. right after a deploy
or cache flush) — not worth building for genuinely long-tail,
unpredictable traffic where warming would just be guessing.

| Pros | Cons / Trade-offs |
|---|---|
| Cost-based TTL keeps expensive responses cached longer, cutting spend where it matters most | Requires tracking per-request cost, not just a flat TTL config |
| Volatility-aware TTL avoids serving confidently-wrong stale answers | Volatility classification is often a manual/heuristic judgment call per request type |
| Cache warming eliminates cold-start latency for known-common queries | Warming is only worth building for predictable, high-volume patterns — wasted effort on long-tail traffic |

---

## Code Samples

- `code_samples/chapter-21/intelligent_caching.py` — multi-layer
  (memory + Redis) caching, semantic similarity matching, cost-aware
  eviction, cache warming
