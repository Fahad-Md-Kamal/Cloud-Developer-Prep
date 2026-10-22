---
title: "Data Cleaning, Normalization & Deduplication at Scale"
---

# Data Cleaning, Normalization & Deduplication at Scale

Finding exact duplicates is a solved problem — hash the record, compare
hashes. The actual hard problem at scale is **near-duplicates**: the same
underlying article mirrored with a different byline, the same product
listed by two sellers with slightly different descriptions. Catching
those without comparing every record to every other record (which stops
being possible well before you reach millions of records) is what
MinHash and LSH actually solve.

## 1. "Why does normalization have to happen before deduplication, not after?"

**Answer:**

- Two records can be the *same underlying thing* and still fail any
  direct comparison simply because they're formatted differently —
  `"Jan 5, 2026"` vs. `"2026-01-05"`, `"  Acme Corp  "` vs. `"Acme
  Corp"`, different Unicode representations of a visually identical
  character.
- Normalization standardizes all of that first — consistent date format,
  trimmed whitespace, consistent case, consistent Unicode normal form —
  specifically so that comparison afterward is actually comparing
  meaning, not formatting noise.
- Skipping this step doesn't just lose some duplicates — it makes
  whatever similarity scores a dedup algorithm computes systematically
  unreliable, since two formatting variants of the same real value look
  artificially dissimilar to any string- or hash-based comparison.

## 2. "Exact duplicates are easy — hash and compare. What actually makes near-duplicate detection hard at scale?"

**Answer:**

- The naive approach — compare every record against every other record
  for similarity — is O(n²) comparisons. At a million records, that's
  roughly 500 billion pairwise comparisons; the approach simply stops
  being computationally possible long before reaching real production
  data volumes.
- The real problem isn't *measuring* similarity between two known
  records (that part's comparatively easy) — it's narrowing down, out of
  millions of candidates, which *pairs* are even worth measuring in the
  first place.

## 3. "What is MinHash, and what problem does it actually solve?"

**Answer:**

- MinHash estimates the **Jaccard similarity** between two sets (how
  much they overlap, as a fraction of their combined content) *without*
  ever comparing the sets directly, element by element.
- The mechanism: apply several different hash functions to every element
  of a set, and for each hash function, keep only the *minimum* hash
  value produced — that small handful of minimum values becomes the
  set's **signature**.
- The key mathematical property that makes this work: two sets that
  share a large fraction of their elements will, with a provable
  probability tied directly to their actual Jaccard similarity, produce
  the *same* minimum value for a given hash function. Comparing two
  signatures (a few numbers each) instead of two full sets (potentially
  thousands of elements each) is what turns an expensive full comparison
  into a cheap one, while still estimating the real similarity reliably.
- Applied to near-duplicate text: represent each document as a set of
  overlapping word or character n-grams first, then MinHash that set —
  two documents that share most of their phrasing produce highly similar
  MinHash signatures, even if their exact wording differs here and
  there.

## 4. "MinHash gives cheap signatures — how does that avoid the O(n²) comparison problem entirely?"

**Answer:**

- MinHash alone still leaves you comparing every signature against every
  other signature — cheaper per comparison, but still O(n²) in the
  number of comparisons made.
- **Locality-Sensitive Hashing (LSH)** is what actually removes the
  pairwise step: it buckets signatures such that similar signatures are,
  with high probability, hashed into the *same* bucket, while dissimilar
  ones land in different buckets.
- Instead of comparing every pair, you only need to compare items that
  landed in the same bucket — a group that's typically a tiny fraction
  of the full dataset, turning an intractable O(n²) problem into
  something close to linear in practice.
- The trade-off is the same shape as approximate nearest-neighbor search
  covered in
  [RAG & Vector Databases §4](../ai-llm/rag-and-vector-databases.md#4-how-do-you-choose-a-vector-database-and-what-actually-differs-between-them) —
  LSH can miss a genuine near-duplicate pair that happened to land in
  different buckets (a false negative), trading a small, tunable amount
  of recall for making the whole approach computationally possible at
  scale at all.

## 5. "How does this actually run at the scale of a real crawl's output — batch or streaming?"

**Answer:**

- **Batch** — compute MinHash signatures and LSH buckets over an entire
  accumulated dataset at once, typically with
  [Spark](spark-pyspark.md#1-explain-how-spark-achieves-parallelism-whats-a-partition),
  partitioning the work across a cluster the same way any other
  large-scale transformation would be distributed.
- **Streaming** — for deduplication that needs to happen as records
  arrive rather than in a periodic batch job, each new record's
  signature gets computed and checked against the existing LSH buckets
  incrementally, flagging a likely duplicate immediately instead of
  waiting for the next batch run.
- The deciding question is the same one that comes up anywhere batch vs.
  streaming is a choice: does a duplicate need to be caught within
  seconds of arriving (streaming), or is catching it within the next
  scheduled run genuinely fine (batch, simpler to build and operate)?

| Pros | Cons / Trade-offs |
|---|---|
| MinHash turns expensive full-set comparison into cheap signature comparison | A probabilistic estimate, not an exact similarity score |
| LSH avoids O(n²) comparisons by only comparing items in the same bucket | Can miss a genuine near-duplicate that lands in a different bucket (a tunable false-negative rate) |
| Batch processing (Spark) scales cleanly to very large accumulated datasets | Not real-time — duplicates aren't caught until the next run |
| Streaming catches duplicates immediately as records arrive | More operationally complex than a periodic batch job |

---

## Code Samples

No dedicated code samples for this page.
