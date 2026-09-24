---
title: "Collections & Itertools"
---

# Collections & Itertools

Specialized data structures and iterator-based processing — the
standard-library building blocks that solve specific performance
problems without reaching for an external dependency.

## 1. "`Counter`, `defaultdict`, `deque` — what problem does each actually solve that a plain `dict`/`list` doesn't?"

```python
from collections import Counter, defaultdict, deque

word_counts = Counter()          # frequency counting
groups = defaultdict(list)       # auto-initializing values
recent_events = deque(maxlen=100)  # bounded FIFO
```

**Answer:**

- **`Counter`** — frequency counting without manual "does this key
  exist yet" checks; `.most_common(n)` returns ranked results in one
  call instead of a manual sort.
- **`defaultdict`** — eliminates "check if key exists, initialize if
  not" boilerplate in hot paths; the default value is created
  automatically on first access to a missing key.
- **`deque`** — O(1) append/pop from *both* ends. A plain
  `list.pop(0)` is O(n) because every remaining element shifts —
  `deque` is the correct structure for a FIFO queue or a bounded
  sliding window (`maxlen=`).
- **`ChainMap`** — layers multiple dicts (e.g. defaults + overrides)
  for lookup without physically merging them into a new dict.

| Pros | Cons / Trade-offs |
|---|---|
| `Counter`/`defaultdict` remove boilerplate and reduce off-by-one/KeyError bugs | Slightly less obvious to a reader unfamiliar with these specific types |
| `deque` gives O(1) operations at both ends, unlike a list | `deque` doesn't support O(1) random access by index — it's not a list replacement everywhere |
| `ChainMap` avoids the cost of merging dicts just to do a lookup | Mutations write to the first mapping only — surprising if not understood upfront |

## 2. "How do you process a dataset larger than available memory?"

```python
from itertools import islice

def batch_processor(iterable, batch_size=1000):
    iterator = iter(iterable)
    while batch := list(islice(iterator, batch_size)):
        yield batch
```

**Answer:**

- Treat the data source as an iterator, not a list — never materialize
  the whole thing at once.
- `itertools.islice` pulls a fixed-size batch from an iterator without
  needing to know its total length upfront, and without consuming
  more than that batch.
- `itertools.chain` composes multiple iterables into one logical
  stream without concatenating them into a new list in memory.
- `itertools.groupby` groups *consecutive* matching items in a single
  pass — genuinely useful, but only correct if the input is already
  sorted/grouped by that key.

**Likely follow-up — "what's the `groupby` gotcha people miss?"**

- `itertools.groupby` only groups consecutive equal keys.
- If the input isn't pre-sorted by that key, elements sharing a key
  but separated by a different one silently form *separate* groups —
  no error is raised, the output is just quietly wrong.
- The fix is always the same: sort by the grouping key immediately
  before calling `groupby`, don't assume the input arrives pre-grouped.

| Pros | Cons / Trade-offs |
|---|---|
| Constant memory regardless of total dataset size | Iterators are single-pass — no re-reading without re-creating the source |
| Composable — `chain`, `islice`, `groupby` combine into readable pipelines | `groupby` silently produces wrong results on unsorted input |
| No external dependency needed for streaming-style processing | Debugging a lazy pipeline is less direct than inspecting a materialized list |

---

## Code Samples

- `code_samples/chapter-38/data_processing_optimization.py` —
  memory-efficient processing, streaming algorithms, batch tuning
