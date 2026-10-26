---
title: "Feature Engineering for ML"
---

# Feature Engineering for ML

Most of the real, day-to-day work in a classical ML project isn't
choosing or tuning an algorithm — it's getting raw data into a shape
a model can actually learn from. For the data-wrangling tools
themselves (Pandas/NumPy mechanics), see
[Data Preprocessing: Pandas & NumPy](../database/data-preprocessing-pandas-numpy.md);
this page covers the ML-specific *decisions* made while using them.

## 1. Handling Missing Data

```python
df["income"].fillna(df["income"].median(), inplace=True)
df["is_income_missing"] = df["income"].isna().astype(int)  # before filling
```

- **Dropping rows** with missing values is simplest, but only safe
  when the missing rows are a small, genuinely random fraction of the
  data — dropping a large or non-random chunk silently biases what the
  model learns from.
- **Imputation** (filling in a value) is the usual alternative: median
  for numeric columns with outliers (mean is pulled by them), mode for
  categorical columns, or a model-based prediction of the missing
  value from other columns for a more careful fill.
- **Interview point:** *why* data is missing matters more than how to
  fill it. Data **missing completely at random** is safe to drop or
  simple-impute. Data missing *because of its own value* (high earners
  skip the income question) is **informative** — filling it blindly
  erases a real signal. Adding a separate `is_X_missing` indicator
  column (as above) is the standard way to preserve that signal instead
  of just filling and hoping it didn't matter.

## 2. Encoding Categorical Variables

```python
pd.get_dummies(df, columns=["city"])          # one-hot
df["city_encoded"] = df["city"].map(df.groupby("city")["target"].mean())  # target encoding
```

- **One-hot encoding** turns a category into one binary column per
  possible value — safe, interpretable, but explodes column count for
  a high-cardinality feature (thousands of unique city/product IDs
  becomes thousands of sparse columns).
- **Ordinal encoding** (mapping each category to an integer) is only
  valid when the categories have a real order (`small < medium <
  large`) — using it on an unordered category (city names) invents a
  fake numeric relationship ("Chicago < Denver") the model will
  wrongly try to learn from.
- **Target encoding** replaces a category with the average target
  value for that category — handles high cardinality well, but leaks
  target information into the feature if computed on the full dataset
  before splitting, which is exactly the kind of subtle data leakage
  covered in [§3](#3-the-data-leakage-trap). It needs to be computed
  **only on the training fold**, not the full dataset.

## 3. The Data Leakage Trap

**Answer:**

- **Data leakage** is information from outside the legitimate training
  data — often, indirectly, information from the future, or from the
  target itself — sneaking into the features a model trains on,
  producing performance that looks great in validation and then falls
  apart in production.
- **Classic examples:** scaling/normalizing the *entire* dataset
  (including test data) before splitting, so the training process
  implicitly "sees" statistics from data it's supposed to be evaluated
  against later; including a feature that's only known *after* the
  outcome happens (a "cancellation reason" column when predicting
  whether an order will cancel); target encoding (§2) computed before
  splitting, baking the actual target value into a feature.
- **The single rule that prevents most of it:** any computation that
  uses statistics from the data (a mean, a scaling factor, a target
  encoding) must be **fit only on the training split**, then applied
  unchanged to validation/test — never fit on the full dataset first.
- **Interview point:** "your model got 98% validation accuracy but
  does poorly in production — what's your first suspicion?" is a real,
  common question, and data leakage is almost always the right first
  answer to reach for before questioning the algorithm itself.

## 4. Feature Selection

```python
from sklearn.feature_selection import SelectKBest, f_classif

selector = SelectKBest(f_classif, k=20).fit(X_train, y_train)
X_selected = selector.transform(X_train)
```

- **Filter methods** (like `SelectKBest` above) score each feature's
  individual statistical relationship with the target, independent of
  any model — fast, but misses interactions between features.
- **Wrapper methods** (like recursive feature elimination) actually
  train a model repeatedly, each time with a different feature subset,
  and keep whichever subset performs best — slower but accounts for
  how features interact, since it's judged by real downstream model
  performance.
- **Embedded methods** get feature importance as a side effect of
  training a single model that does its own selection internally — L1
  regularization zeroing out a feature's weight entirely (see
  [Regularization & Hyperparameter Tuning §1](regularization-and-hyperparameter-tuning.md#1-l1-vs-l2-regularization)),
  or a tree ensemble's feature importances
  ([Classical ML §4](classical-ml-regression-trees-and-ensembles.md#4-feature-importance)).
- **Why bother, instead of just feeding a model everything?**
  Irrelevant/noisy features add variance without adding signal — more
  columns the model can latch onto spuriously, worse generalization —
  plus a real, practical cost to training/inference time and, for a
  production system, to the surface area that needs monitoring for
  drift (see
  [Model Monitoring & Drift Detection](model-monitoring-and-drift-detection.md)).

## 5. Feature Scaling

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler

scaler = StandardScaler().fit(X_train)  # fit on train only — see §3
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

- **Standardization** (zero mean, unit variance) and **normalization**
  (scaling to a fixed range, usually 0–1) put features with very
  different natural ranges (age: 0–100, income: 0–500,000) on
  comparable footing.
- **Which algorithms actually need it:** distance-based methods (SVM,
  k-means, k-NN) and gradient-descent-trained models (linear/logistic
  regression, neural networks) are genuinely sensitive to feature
  scale — an unscaled large-range feature dominates a distance
  calculation or a gradient step purely because of its units, not its
  real importance. Tree-based methods
  ([Classical ML §2–3](classical-ml-regression-trees-and-ensembles.md#2-decision-trees))
  split on one feature's threshold at a time and are **scale-invariant**
  — scaling is wasted effort (though harmless) for a pure tree/forest/
  boosting model.
- **Interview point:** knowing *which* model families actually need
  scaling, rather than scaling everything reflexively "because that's
  the standard preprocessing step," is a real signal of understanding
  why the technique exists rather than just following a checklist.

---

## Code Samples

No dedicated code samples for this page — the snippets above are
standard `scikit-learn`/`pandas` usage, runnable directly with
`pip install scikit-learn pandas`.
