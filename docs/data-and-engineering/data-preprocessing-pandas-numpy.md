---
title: "Data Preprocessing: Pandas & NumPy"
---

# Data Preprocessing: Pandas & NumPy

The general-purpose data-handling foundation underneath most ML/NLP
pipelines — vectorized operations, and the missing-data/feature-prep
work that happens before anything reaches a model.

## 1. "Why is a vectorized NumPy operation faster than a Python for-loop over the same data?"

```python
import numpy as np

prices = np.array([19.99, 5.50, 100.00, 42.75])

# Slow: a Python-level loop, one interpreted operation per element
discounted = [p * 0.9 for p in prices]

# Fast: one vectorized operation, executed in compiled C, no per-element
# Python bytecode overhead
discounted = prices * 0.9
```

**Answer:** A Python `for` loop executes interpreted bytecode once per
element — real overhead at scale. NumPy's vectorized operations push the
loop down into compiled C code operating on a contiguous block of
memory, avoiding Python's per-element interpreter overhead entirely.
The speedup compounds with array size — for a few elements it barely
matters, for millions of rows it's often a 10-100x difference.

## 2. "How do you handle missing data in a Pandas DataFrame, and what's the actual decision behind each option?"

```python
import pandas as pd

df = pd.DataFrame({"price": [19.99, None, 100.00], "category": ["A", "B", None]})

df.dropna()                          # drop any row with a missing value
df.fillna({"price": df["price"].mean(), "category": "unknown"})  # impute
df["price"].isna().sum()             # count missing values before deciding
```

**Answer:** `dropna()` is safe when missing rows are rare and dropping
them doesn't bias the dataset — but silently shrinks your data, which
matters if missingness itself correlates with something (e.g. a survey
question people skip more often when the answer is embarrassing —
dropping those rows systematically removes a pattern, not just noise).
`fillna()` with a mean/median/mode keeps every row but introduces an
assumption about what the missing value "should" be — reasonable for
data missing at random, misleading if it isn't. Always check *how much*
is missing (`isna().sum()`) and *why* before picking a strategy —
"just drop nulls" is a default, not a universal answer.

## 3. "Walk through a typical feature-preparation step before feeding data to a model."

```python
import pandas as pd

df = pd.read_csv("orders.csv")

# Type coercion -- catch bad data early, not deep inside a model call
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

# Feature engineering -- derive signal the raw column doesn't expose directly
df["days_since_order"] = (pd.Timestamp.now() - df["order_date"]).dt.days

# Categorical encoding -- most models need numeric input, not raw strings
df = pd.get_dummies(df, columns=["region"])

# Normalization -- keep feature scales comparable for distance-based models
df["amount_normalized"] = (df["amount"] - df["amount"].mean()) / df["amount"].std()
```

**Answer:** Type coercion first (`errors="coerce"` turns unparseable
values into `NaN` instead of crashing, making bad rows visible and
handleable rather than silently corrupting downstream math). Feature
engineering derives signal a raw column doesn't expose on its own (a
raw timestamp is less useful to most models than "days since
purchase"). Categorical encoding (`get_dummies` for one-hot, or a
label/ordinal encoder) because most models expect numeric input.
Normalization matters specifically for distance-based methods (cosine
similarity, k-NN, gradient-descent-trained models) where features on
wildly different scales otherwise dominate the result — a tree-based
model is far less sensitive to this.

| Pros | Cons / Trade-offs |
|---|---|
| Vectorized operations scale to real data volumes without custom optimization | Vectorized code can be less readable than an equivalent explicit loop for complex logic |
| Pandas gives a consistent, well-documented API for the whole cleaning/prep pipeline | Easy to silently introduce bias (via `fillna`, `dropna`) without checking the data first |
| NumPy underlies most of the Python data/ML ecosystem — one skill, broad applicability | Large in-memory DataFrames don't scale indefinitely — a genuinely big dataset needs Spark/Dask instead |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Pandas/NumPy preprocessing example added under `code_samples/`.
