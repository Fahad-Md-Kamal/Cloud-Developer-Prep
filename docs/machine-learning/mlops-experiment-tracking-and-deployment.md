---
title: "MLOps: Experiment Tracking, Model Registry & CI/CD for Models"
---

# MLOps: Experiment Tracking, Model Registry & CI/CD for Models

A trained model sitting in a Jupyter notebook isn't a production
system — MLOps is the set of practices for getting a model from
"it worked in my experiment" to "it's serving real traffic reliably,
and we know when it stops working." For the LLM-specific side of
shipping a model-backed feature, see
[LLM APIs & Providers](../ai-llm/llm-apis-and-providers.md) and
[LLM Response Caching](../ai-llm/llm-response-caching.md); this page covers the
classical-ML training-to-production pipeline underneath both.

## 1. "Why can't you just save a `.pkl` file and call it done?"

**Answer:**

- A single pickled model file answers "what does the model predict,"
  but none of the questions that actually matter in production: which
  exact data and code produced this model, can it be reproduced, is
  this the version currently serving traffic, and what happens when a
  better version needs to replace it safely.
- **MLOps exists to answer those systematically** — it's the ML
  analogue of DevOps (see
  [DevOps Principles & Delivery](../cloud-devops/devops-principles-and-delivery.md)):
  the same instinct to make a process repeatable, observable, and
  safe to change, applied to the specific lifecycle of a trained model
  instead of a deployed service's code.
- The three practices below (experiment tracking, model registry,
  CI/CD for models) map directly onto DevOps's own version
  control → build → deploy pipeline, just with a model artifact (and
  the data it was trained on) as the thing being versioned and
  promoted, not just source code.

## 2. Experiment Tracking

```python
import mlflow

with mlflow.start_run():
    mlflow.log_param("max_depth", 7)
    mlflow.log_param("n_estimators", 200)
    model.fit(X_train, y_train)
    mlflow.log_metric("f1", f1_score(y_test, model.predict(X_test)))
    mlflow.sklearn.log_model(model, "model")
```

- A real ML project runs dozens to hundreds of training experiments —
  different features, hyperparameters (see
  [Regularization & Hyperparameter Tuning §4](regularization-and-hyperparameter-tuning.md#4-hyperparameter-search)),
  algorithms. Without tracking, "which exact settings produced the
  model that scored 0.89 F1 last Tuesday" becomes genuinely
  unanswerable within a week.
- Tools like **MLflow** and **Weights & Biases** log every run's
  parameters, metrics, and the resulting model artifact automatically,
  making every experiment comparable and reproducible after the fact —
  the ML equivalent of a commit history, but for training runs instead
  of code changes.
- **Interview point:** tracking the *code version* and *exact training
  data version* alongside parameters/metrics is what makes an
  experiment genuinely reproducible — logging only hyperparameters and
  the final score, with no link back to the data snapshot or code
  commit that produced it, means "reproduce this result" is still
  impossible months later even with perfect metric logs.

## 3. Model Registry and Versioning

```python
mlflow.register_model("runs:/<run_id>/model", "fraud-detector")
client.transition_model_version_stage("fraud-detector", version=3, stage="Production")
```

- A **model registry** is a central store of trained model versions,
  each tagged with a **stage** (commonly Staging → Production →
  Archived) — the explicit, auditable answer to "which model is
  actually serving traffic right now," separate from the much larger
  pile of experiments tracked in §2.
- This separation matters: not every tracked experiment becomes a
  registered model, and not every registered model version is
  currently in Production — the registry is specifically the curated,
  promotion-gated subset that's actually deployment-relevant.
- Versioning a model also means versioning **the data it was trained
  on**, not just the code and weights — a model retrained on updated
  data is a genuinely different artifact even with identical code and
  hyperparameters, and "which data snapshot trained this version" is a
  real, recurring debugging question when a new model version behaves
  unexpectedly.

## 4. CI/CD for ML

**Answer:**

- Standard CI/CD (see
  [CI/CD & Progressive Delivery](../cloud-devops/cicd-and-progressive-delivery.md))
  tests and deploys *code*. ML pipelines add a parallel concern: a
  model can pass every code test and still be a bad model to deploy,
  because its *quality* depends on data, not just logic correctness.
- **A model-specific CI pipeline typically adds:** data validation (is
  the incoming training data within expected ranges/schema — a
  malformed data feed should fail the pipeline before it trains a
  model on garbage), automated retraining on a schedule or data-drift
  trigger (see
  [Model Monitoring & Drift Detection](model-monitoring-and-drift-detection.md)),
  and a gate that compares the newly trained model's validation metrics
  against the currently deployed one **before** promoting it — a new
  model doesn't get deployed just because training succeeded, only if
  it's measurably at least as good.
- **Deployment patterns borrow directly from regular service
  deployment** (see
  [DevOps Principles & Delivery](../cloud-devops/devops-principles-and-delivery.md)):
  **shadow deployment** runs the new model alongside the current one
  on live traffic without its predictions actually being used, purely
  to compare behavior safely; **canary deployment** routes a small
  percentage of real traffic to the new model first, watching metrics
  before a full rollout — the same risk-reduction idea as canary code
  deploys, applied to model versions instead of code versions.

## 5. Serving Patterns

**Answer:**

- **Batch inference** — run predictions on a large set of inputs
  periodically (nightly, hourly), store the results, serve them from a
  fast lookup later. Right for use cases where predictions don't need
  to reflect the very latest input instantly (tomorrow's demand
  forecast, this week's churn-risk scores).
- **Real-time inference** — a live API endpoint that takes one input
  and returns a prediction on demand (see
  [FastAPI: Performance & Production Patterns](../backend/python/fastapi-performance-patterns.md)
  for the serving-infrastructure side of this). Needed when the
  prediction depends on input only available at request time (fraud
  scoring a transaction as it happens).
- **The real trade-off is cost and latency, not just "real-time is
  better":** real-time serving needs the model (and its dependencies)
  loaded and ready continuously, with latency budgets to meet; batch
  inference can use cheaper, scheduled compute and amortize cost
  across a large volume — reaching for real-time serving when batch
  would genuinely satisfy the actual product need is a common,
  avoidable cost mistake.

---

## Code Samples

No dedicated code samples for this page — the snippets above are
standard `mlflow` usage, runnable with `pip install mlflow`.
