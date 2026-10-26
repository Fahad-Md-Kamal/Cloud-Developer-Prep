---
title: "Regularization & Hyperparameter Tuning"
---

# Regularization & Hyperparameter Tuning

Two closely related practical skills: deliberately constraining a
model so it generalizes better, and systematically searching for the
settings that make it perform best — both built directly on the
bias-variance idea from
[Supervised, Unsupervised & Reinforcement Learning §5](supervised-unsupervised-and-reinforcement-learning.md#5-whats-the-bias-variance-tradeoff-and-why-does-every-model-eventually-run-into-it).

## 1. L1 vs. L2 Regularization

```python
from sklearn.linear_model import Lasso, Ridge

lasso = Lasso(alpha=0.1).fit(X_train, y_train)  # L1
ridge = Ridge(alpha=0.1).fit(X_train, y_train)  # L2
```

- Both add a penalty term to the training loss based on the size of
  the model's weights, so the model is rewarded not just for fitting
  the data but for keeping its weights small — a direct, deliberate
  way to trade a little bias for a lot less variance when a model is
  overfitting.
- **L2 (Ridge)** penalizes the *squared* size of each weight — shrinks
  every weight toward zero smoothly, but essentially never all the way
  to exactly zero.
- **L1 (Lasso)** penalizes the *absolute* size of each weight — this
  geometric difference means L1 can push weights to **exactly zero**,
  effectively removing those features from the model entirely. This is
  why L1 is also a feature-selection technique (see
  [Feature Engineering for ML §4](feature-engineering-for-ml.md#4-feature-selection)),
  not just a regularizer.
- **Elastic Net** combines both penalties, for when you want some
  automatic feature elimination (L1) alongside the smoother, more
  stable shrinkage L2 provides on the features that remain.
- `alpha` controls penalty strength — too high and the model
  underfits (pushed toward predicting near-zero/the mean for
  everything); too low and it barely regularizes at all. Picked via
  the validation process in [§3](#3-cross-validation-for-model-selection),
  not guessed.

## 2. Regularization Beyond Linear Models

**Answer:**

- **Dropout** (neural networks) — randomly zeroes out a fraction of
  neurons during each training step, forcing the network to not rely
  too heavily on any single neuron or co-adapted group of neurons.
  Covered in context in
  [Deep Learning Fundamentals §4](deep-learning-fundamentals.md#4-overfitting-controls-dropout-and-batch-normalization).
- **Early stopping** — stop training once validation performance
  stops improving (or starts getting worse), even though training loss
  would keep dropping if you kept going. A free, almost-always-applied
  regularizer: it directly prevents the model from continuing to fit
  the training data's noise past the point of genuine improvement.
- **Tree pruning / `max_depth` / `min_samples_leaf`** — the tree-based
  equivalent, covered in
  [Classical ML §2](classical-ml-regression-trees-and-ensembles.md#2-decision-trees)
  — limiting how far a tree is allowed to split is regularization by a
  different mechanism (constraining model complexity directly, instead
  of penalizing weight size).
- **The unifying idea across all of these:** every regularization
  technique trades a little training-data fit (bias) for a lot more
  stability on new data (variance) — naming that trade-off explicitly
  is what separates a strong answer from a list of unrelated-sounding
  techniques.

## 3. Cross-Validation for Model Selection

```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5, scoring="f1")
print(scores.mean(), scores.std())
```

- **K-fold cross-validation** (introduced in
  [Model Evaluation & Validation §1](model-evaluation-and-validation.md#1-why-does-a-model-need-a-separate-training-validation-and-test-split))
  is the standard way to choose between models or hyperparameter
  settings without burning a large, separate validation set — every
  fold gets a turn as the held-out set, and the average score across
  folds is a more stable estimate than any single train/validation
  split.
- The **standard deviation across folds** matters as much as the mean
  — two models with the same average F1 but very different fold-to-fold
  variance are not equally trustworthy; the high-variance one is more
  likely to perform unpredictably on genuinely new data.
- **Interview point:** cross-validation on **time-series or any
  temporally ordered data needs a special variant** (`TimeSeriesSplit`)
  that always trains on past data and validates on future data within
  each fold — ordinary random k-fold would let the model "see the
  future" during training, a direct, easy-to-miss form of the data
  leakage covered in
  [Feature Engineering for ML §3](feature-engineering-for-ml.md#3-the-data-leakage-trap).

## 4. Hyperparameter Search

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

grid = GridSearchCV(model, param_grid={"max_depth": [3, 5, 7], "n_estimators": [100, 200]}, cv=5)
grid.fit(X_train, y_train)
```

- **Grid search** tries every combination of specified hyperparameter
  values exhaustively — guaranteed to find the best combination *within
  the grid*, but the number of combinations (and therefore training
  runs) grows multiplicatively with every added parameter, making it
  impractical for more than a few parameters.
- **Random search** samples a fixed number of random combinations from
  the specified ranges instead of trying all of them. Counterintuitively,
  this usually finds a comparably good result with far fewer runs,
  because most hyperparameters only weakly affect performance — random
  search naturally spends more of its budget exploring the few
  parameters that actually matter, instead of exhaustively covering
  combinations of ones that don't.
- **Bayesian optimization** (e.g. Optuna, Hyperopt) goes a step
  further: it uses the results of previous trials to intelligently
  choose the next combination to try, instead of searching the grid
  blindly or randomly — converges to a good setting in meaningfully
  fewer trials than random search, at the cost of being sequential
  (each trial depends on prior results) rather than trivially
  parallelizable the way grid/random search are.
- **Interview point:** "grid search vs. random search — which do you
  pick, and why?" expects naming the actual mechanism (random search's
  budget concentrates on parameters that matter, since most don't),
  not just "random search is faster."

| Method | Guarantees best-in-search-space? | Scales to many hyperparameters? | Parallelizable? |
|---|---|---|---|
| Grid search | Yes, within the grid | No — combinatorial explosion | Yes |
| Random search | No, but usually close | Yes | Yes |
| Bayesian optimization | No, but typically fewer trials needed | Yes | Limited — sequential |

---

## Code Samples

No dedicated code samples for this page — the snippets above are
standard `scikit-learn` usage, runnable directly with
`pip install scikit-learn`.
