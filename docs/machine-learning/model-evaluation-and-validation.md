---
title: "Model Evaluation & Validation"
---

# Model Evaluation & Validation

A model's accuracy on the data it trained on tells you almost
nothing about whether it actually works — this page covers how to
measure a model honestly, and the metrics that come up in nearly
every ML interview. See
[Evaluating LLM Output at Scale](../ai-llm/evaluating-llm-output.md) for the
LLM-specific version of this question (benchmarks, golden sets,
LLM-as-judge) — this page is the classical-ML foundation underneath
it.

## 1. "Why does a model need a separate training, validation, and test split?"

**Answer:**

- **Training set** — what the model actually learns from.
- **Validation set** — held out from training, used to compare
  different models or hyperparameter settings and pick the best one
  (see
  [Regularization & Hyperparameter Tuning](regularization-and-hyperparameter-tuning.md)).
- **Test set** — touched exactly once, at the very end, to report the
  final, honest performance number — never used to make *any* decision
  about the model along the way.
- **The mistake this structure exists to prevent:** if you tune
  hyperparameters by repeatedly checking performance on the same
  "test" set, you're implicitly fitting to that set's quirks over many
  iterations — the reported number stops being an honest estimate of
  real-world performance, even though no single step looks like
  cheating. A true test set, touched once, is what keeps the final
  number trustworthy.
- A common split is 70/15/15 or 80/10/10, but the real rule is
  **enough validation/test data to get a stable estimate** — on a
  small dataset, use **k-fold cross-validation** instead (split into
  `k` folds, train on `k-1`, validate on the remaining one, rotate
  through all `k`, average the results) to get a more stable estimate
  without sacrificing a large fixed chunk of scarce data.

## 2. "For classification, what does a confusion matrix actually tell you that accuracy doesn't?"

**Answer:**

|  | Predicted positive | Predicted negative |
|---|---|---|
| **Actual positive** | True Positive (TP) | False Negative (FN) |
| **Actual negative** | False Positive (FP) | True Negative (TN) |

- Accuracy (`(TP + TN) / total`) collapses all four numbers into one,
  which hides exactly the thing that usually matters most: **what
  kind** of mistake the model is making, and how often.
- The classic trap: a fraud model that always predicts "not fraud" on
  a dataset where only 0.5% of transactions are actually fraud scores
  **99.5% accuracy** while catching zero fraud — accuracy looks great
  specifically because the classes are imbalanced, which is the normal
  case for fraud, disease screening, and most rare-event detection.
- This is exactly why **precision, recall, and F1** (next) exist —
  they're built directly from the confusion matrix's four numbers, and
  none of them can be gamed by a model that just always predicts the
  majority class the way accuracy can.

## 3. "What do precision, recall, and F1 actually measure, and when do you optimize for one over the other?"

**Answer:**

- **Precision** = `TP / (TP + FP)` — of everything the model flagged
  positive, how much was actually positive? High precision means few
  false alarms.
- **Recall** = `TP / (TP + FN)` — of everything that was actually
  positive, how much did the model catch? High recall means few missed
  cases.
- **F1** = the harmonic mean of precision and recall — a single number
  that stays low unless *both* are reasonably high, used when there's
  no clear reason to favor one over the other.
- **These trade off against each other** — a model can trivially get
  100% recall by flagging everything positive (catches every real
  case, buried in false alarms), or near-100% precision by only
  flagging the single most obvious case (misses almost everything
  else). The threshold used to turn a predicted probability into a
  final yes/no decision is what's actually being tuned here.
- **Which to optimize for is a business decision, not a math
  decision:** cancer screening wants high recall (a missed case is far
  worse than a false alarm that gets ruled out by a follow-up test);
  spam filtering wants high precision (a real email wrongly marked
  spam is worse than one spam message slipping through). Naming this
  trade-off explicitly, with a concrete reason, is what a strong
  interview answer sounds like — not just defining the two terms.

## 4. "What's ROC-AUC, and how is it different from F1?"

**Answer:**

- **ROC-AUC** plots the true positive rate against the false positive
  rate across *every possible threshold*, then measures the area under
  that curve — a single number from 0.5 (no better than random) to 1.0
  (perfect), summarizing how well the model separates the two classes
  **independent of any one chosen threshold**.
- This is the key difference from F1: F1 is computed at one specific
  threshold (usually 0.5); ROC-AUC asks "across every possible
  threshold, how good is this model's ranking?" — useful for comparing
  models *before* a specific threshold/business trade-off has been
  decided.
- **Interview point:** ROC-AUC can be misleadingly optimistic on
  heavily imbalanced data, because the false-positive-rate denominator
  (all true negatives) is huge, so even a meaningfully high number of
  false positives barely moves the rate. **Precision-Recall AUC** is
  the standard fix — it's built from precision, which is directly
  sensitive to false positives relative to the much smaller positive
  class, making it the better choice specifically for rare-event
  problems like fraud or disease detection.

## 5. "For regression, which metric should you actually report?"

**Answer:**

- **MAE (Mean Absolute Error)** — the average absolute difference
  between predicted and actual values, in the original units. Easy to
  explain to a non-technical stakeholder ("off by $8,200 on average").
- **RMSE (Root Mean Squared Error)** — squares errors before
  averaging, then takes the square root — this means large errors are
  penalized disproportionately more than small ones, so RMSE is the
  right choice when a few big misses matter more than many small ones.
- **R² (R-squared)** — the proportion of variance in the target the
  model explains, from 0 (no better than always predicting the mean)
  to 1 (perfect). Useful for a quick "how much better than a naive
  baseline is this," but says nothing about the error's actual size in
  real units the way MAE/RMSE do.
- **Interview point:** "MAE vs. RMSE — which do you pick?" expects
  naming the actual reason, not just the formula difference — RMSE
  when large errors are disproportionately costly (badly
  underestimating one high-value customer's churn risk), MAE when
  errors should just be judged by their average real-world size.

---

## Code Samples

No dedicated code samples for this page — `sklearn.metrics` implements
every metric above directly:
`from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, mean_absolute_error`.
