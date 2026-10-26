---
title: "Classical ML: Regression, Trees & Ensemble Methods"
---

# Classical ML: Regression, Trees & Ensemble Methods

The supervised-learning algorithm family most "ML Engineer" and "Data
Scientist" interviews actually probe — not because they're
cutting-edge (they're decades old), but because they're still what
runs in production for tabular data (pricing, churn, fraud, credit
risk) where a transformer is overkill. See
[Supervised, Unsupervised & Reinforcement Learning](supervised-unsupervised-and-reinforcement-learning.md)
for the paradigm these all sit inside.

## 1. Linear and Logistic Regression

```python
from sklearn.linear_model import LinearRegression, LogisticRegression

reg = LinearRegression().fit(X_train, y_train)          # predicts a number
clf = LogisticRegression().fit(X_train, y_train)         # predicts a class
```

- **Linear regression** fits a straight line (or hyperplane, with
  multiple features): `y = w1*x1 + w2*x2 + ... + b`. Training means
  finding the weights that minimize the squared difference between
  predicted and actual values — simple, fast, and the weights
  themselves are directly interpretable ("a 100 sq ft increase adds
  $X to predicted price").
- **Logistic regression** runs that same linear combination through a
  **sigmoid function**, squashing the output into a 0–1 probability,
  then thresholds it (commonly at 0.5) into a class. Despite the name,
  it's a classification algorithm, not a regression one.
- **Interview point:** both assume a roughly linear relationship
  between features and the target — if the real relationship is
  curved or has interactions between features, a linear model
  systematically underfits (high bias) no matter how much data you
  add, which is exactly when a tree-based model below becomes the
  better default.

## 2. Decision Trees

```python
from sklearn.tree import DecisionTreeClassifier

tree = DecisionTreeClassifier(max_depth=5).fit(X_train, y_train)
```

- A decision tree repeatedly splits the data on the single feature
  (and threshold) that best separates it into purer groups — "is
  income > $50k? if yes, is age > 30?" — until each final group (a
  **leaf**) is mostly one class, or a stopping rule is hit.
- "Purer" is measured by **Gini impurity** or **entropy** — both just
  different formulas for "how mixed are the classes in this group,"
  minimized by the split the tree picks at each step.
- A single tree with no depth limit can split all the way down to
  leaves containing one training example each — perfect training
  accuracy, and a textbook case of high-variance overfitting (see
  [Supervised, Unsupervised & Reinforcement Learning §5](supervised-unsupervised-and-reinforcement-learning.md#5-whats-the-bias-variance-tradeoff-and-why-does-every-model-eventually-run-into-it)).
  `max_depth`, `min_samples_leaf`, and pruning all exist specifically
  to stop that.
- **Why trees matter beyond accuracy:** unlike linear regression's
  single global equation, a tree naturally captures interactions and
  non-linear relationships without any manual feature engineering —
  the trade-off is that a single tree is still a weak, unstable
  predictor on its own, which is exactly the gap ensembles close.

## 3. Ensemble Methods: Random Forests and Gradient Boosting

```python
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

rf = RandomForestClassifier(n_estimators=200).fit(X_train, y_train)
gb = GradientBoostingClassifier(n_estimators=200).fit(X_train, y_train)
```

- **Random forest — bagging:** train many trees independently, each
  on a random subset of the training data *and* a random subset of
  features at each split, then average their predictions (or vote, for
  classification). Each individual tree is still high-variance and
  overfit to its own random slice of data, but their errors are
  uncorrelated — averaging many uncorrelated, noisy predictors cancels
  out the noise, driving variance down without adding bias.
- **Gradient boosting — boosting, a genuinely different idea:** train
  trees *sequentially*, where each new tree is trained specifically to
  predict the previous ensemble's *errors* (residuals), then added in
  to correct them. Bagging reduces variance from already-decent trees
  trained in parallel; boosting reduces bias by deliberately,
  iteratively fixing mistakes, trained one tree at a time.
- **XGBoost / LightGBM / CatBoost** are production-grade, heavily
  optimized implementations of gradient boosting — the default
  winning approach on tabular-data competitions and a huge share of
  real production tabular-data systems, for the same reason: boosted
  trees usually beat both a single tree and a random forest on
  structured, spreadsheet-shaped data.

| Method | Trains trees | Fixes | Trade-off |
|---|---|---|---|
| Single tree | One, to full depth | Nothing — the baseline | Fast, interpretable, but high variance |
| Random forest | Many, in parallel, on random subsets | Variance (overfitting) | Slower, less interpretable, but much more stable |
| Gradient boosting | Many, sequentially, on prior errors | Bias (underfitting) | Best raw accuracy on tabular data; more prone to overfitting if not tuned, slower to train |

**Interview point:** "Why would a deep learning model lose to XGBoost
on this dataset?" is a real, recurring question — neural networks need
large amounts of data and benefit from spatial/sequential structure
(images, text, audio) to outperform trees; on a modest-sized,
genuinely tabular dataset (rows and independent columns, no spatial
structure), gradient-boosted trees routinely beat a neural network
both on accuracy and on training/inference cost. "Use deep learning by
default" is the wrong instinct for this exact, very common case.

## 4. Feature Importance

```python
import pandas as pd
importances = pd.Series(rf.feature_importances_, index=X_train.columns).sort_values(ascending=False)
```

- Tree-based models give feature importance almost for free — how much
  each feature reduced impurity across every split it was used in,
  summed across the whole forest/ensemble.
- This is a real practical advantage over a plain linear model's
  coefficients when features are on different scales or correlated —
  tree importance is naturally scale-invariant and handles some
  correlation gracefully, though **correlated features can still split
  importance between them artificially**, understating how important
  that *group* of features actually is.
- Where this actually shows up: explaining a fraud model's decision to
  a compliance team, or a quick first pass at which columns are even
  worth keeping before more rigorous feature selection — see
  [Feature Engineering for ML §4](feature-engineering-for-ml.md#4-feature-selection).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
standard `scikit-learn` usage, runnable directly against any tabular
dataset with `pip install scikit-learn pandas`.
