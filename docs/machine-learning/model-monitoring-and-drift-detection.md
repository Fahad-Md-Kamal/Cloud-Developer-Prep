---
title: "Model Monitoring & Drift Detection in Production"
---

# Model Monitoring & Drift Detection in Production

A model's validation score on the day it shipped is a snapshot, not a
guarantee — the real world it's making predictions about keeps
changing after deployment, and nothing alerts you to that on its own.
This page covers what to actually monitor, and why a model can fail
silently with no error, no exception, and no crash anywhere in the
stack.

## 1. "A model's accuracy quietly drops over time with no code changes — what's actually happening?"

**Answer:**

- This is **model drift**, and it's the single most important
  production-ML concept beyond the model itself — a model that was
  genuinely good at launch can become quietly, silently wrong months
  later, with every system around it reporting healthy (no errors, no
  crashed requests, normal latency).
- It happens because a model encodes a **snapshot** of the
  relationship between features and target at training time — if that
  relationship, or the data feeding it, shifts in the real world after
  deployment, the model keeps confidently applying its now-outdated
  snapshot.
- There are two genuinely different ways this happens, covered next —
  distinguishing them is the actual interview-relevant skill, since
  the fix for each is different.

## 2. Data Drift vs. Concept Drift

**Answer:**

- **Data drift (covariate shift)** — the distribution of the *input
  features* changes, while the real relationship between features and
  target stays the same. A fraud model trained mostly on card-present
  transactions suddenly sees a surge of card-not-present transactions
  after a product change — the input distribution shifted, but "what
  fraud looks like" for any given transaction type hasn't.
- **Concept drift** — the actual relationship between features and
  target changes, even if the input distribution looks the same. A
  spam filter trained on 2020-era spam patterns faces genuinely new
  spam tactics in 2024 — the same kind of email now means something
  different.
- **Why the distinction matters practically:** data drift is often
  detectable just by monitoring input feature statistics (§3), without
  needing new labels at all. Concept drift is only directly detectable
  by comparing predictions to *actual outcomes* once they're known —
  which is why label availability (and the lag before labels arrive)
  is a core design constraint for any monitoring system, covered next.

## 3. What to Actually Monitor

```python
from scipy.stats import ks_2samp

stat, p_value = ks_2samp(training_feature_distribution, live_feature_distribution)
# low p-value => distributions are meaningfully different => data drift
```

- **Input/feature monitoring** — track each feature's distribution
  (mean, variance, or a full statistical test like the
  Kolmogorov-Smirnov test above) in live traffic against its training-
  time distribution. This works *without waiting for labels*, which is
  exactly why it's usually the first layer of defense.
- **Prediction monitoring** — track the distribution of the model's
  *outputs* over time (e.g., the fraction of transactions scored as
  fraud). A sudden shift here, even with no clear single feature
  cause, is often the earliest visible symptom of a problem.
- **Outcome/label monitoring** — once the real outcome is eventually
  known (did the transaction turn out to be fraud, did the customer
  actually churn), compare it against the prediction, recomputing the
  real metrics from
  [Model Evaluation & Validation](model-evaluation-and-validation.md)
  on a rolling window of live data, not just at training time.
- **Interview point:** "how would you monitor a model where the real
  label only becomes available 30 days after the prediction (like loan
  default)?" is a genuinely common, realistic question — the expected
  answer leans on input/prediction drift monitoring as an early-warning
  signal precisely *because* outcome monitoring has an unavoidable
  30-day lag, not as a nice-to-have extra layer.

## 4. Responding to Drift

**Answer:**

- **Scheduled retraining** — simplest approach: retrain on a fixed
  cadence (weekly, monthly) regardless of whether drift was actually
  detected. Easy to operate, but wastes compute when nothing's
  drifted, and reacts too slowly if drift happens suddenly.
- **Triggered retraining** — retrain automatically when a monitored
  drift metric crosses a defined threshold, feeding directly into the
  CI/CD pipeline from
  [MLOps §4](mlops-experiment-tracking-and-deployment.md#4-cicd-for-ml)
  — the model only gets rebuilt when there's actual evidence it's
  needed.
- **Before retraining fixes anything, confirm the pipeline itself
  isn't the real problem** — a schema change in an upstream data
  source, a broken feature-computation job, or a silently-changed
  units/scale on one input can look exactly like drift in monitoring
  dashboards while actually being a data *pipeline* bug. Retraining a
  model to "adapt" to a bug just teaches it the bug.
- **Interview point:** "would you always just retrain when drift is
  detected?" — expects the nuance above: drift detection should
  trigger investigation first, not blind automatic retraining, since
  some of what looks like drift is actually a broken upstream pipeline
  that retraining would paper over rather than fix.

---

## Code Samples

No dedicated code samples for this page — the snippet above uses
`scipy.stats`, runnable with `pip install scipy`.
