---
title: "Supervised, Unsupervised & Reinforcement Learning"
---

# Supervised, Unsupervised & Reinforcement Learning

[Types of AI Models & What They Actually Cost](../ai-llm/types-of-ai-models-and-their-cost.md)
covers what a model and training are, in the most basic terms, and
what makes an LLM's output expensive. This page covers the other
split that actually matters in an interview: the three fundamentally
different ways a model can learn, and the classical (non-LLM)
algorithms built on top of them — the body of knowledge most "ML
Engineer" roles are actually testing, distinct from the LLM/agent
material in the rest of this section.

## 1. "What's the actual difference between supervised, unsupervised, and reinforcement learning?"

**Answer:**

- **Supervised learning** — the training data comes with the correct
  answer already attached ("this email is spam," "this house sold for
  $420,000"). The model's whole job is learning the mapping from input
  to that known answer, then applying it to new, unlabeled input.
- **Unsupervised learning** — the training data has no correct answer
  attached at all. The model's job is finding structure that's
  already there — groups of similar items, a simpler way to represent
  the same data — without anyone telling it what the "right" groups or
  representation are.
- **Reinforcement learning (RL)** — there's no labeled dataset at
  all; instead, an **agent** takes actions in an **environment** and
  gets a **reward** signal back, learning which actions lead to more
  reward over time through trial and error, not from being shown
  correct answers up front.
- The question that actually separates them in practice: **does a
  "right answer" exist in the training data before the model ever
  sees it?** Yes → supervised. No, but structure still exists to find
  → unsupervised. No, and the only feedback is a reward after acting →
  reinforcement learning.

## 2. "Within supervised learning, what's the difference between regression and classification?"

**Answer:**

- **Regression** predicts a continuous number — a house price, a
  delivery time, tomorrow's temperature. The output can be any value
  on a scale, and "close" is meaningfully better than "far."
- **Classification** predicts one label from a fixed, discrete set —
  spam/not-spam, which of 5 product categories, fraud/not-fraud.
  There's no "closer" or "farther" between labels the way there is
  between numbers.
- The same underlying algorithm family often supports both — linear
  regression predicts a number directly; logistic regression (despite
  the name) is a *classification* algorithm, predicting a probability
  that gets thresholded into a label (see
  [Classical ML: Regression, Trees & Ensembles §1](classical-ml-regression-trees-and-ensembles.md#1-linear-and-logistic-regression)).
- **Interview point:** picking the wrong one is a real, common mistake
  — predicting a *price range bucket* (0-10k, 10-50k, 50k+) as a
  classification problem throws away the ordering information a
  regression model would naturally use; predicting an exact price as a
  classification problem (one class per possible dollar amount) is
  nonsensical. Match the problem's actual shape to the method.

## 3. "What does unsupervised learning actually get used for, concretely?"

**Answer:**

- **Clustering** — grouping similar items without being told the
  groups in advance: customer segmentation, grouping similar support
  tickets, finding anomalous transactions that don't fit any normal
  cluster. Covered in depth in
  [Classical ML: Clustering, SVM & Dimensionality Reduction §1](classical-ml-clustering-svm-and-dimensionality-reduction.md#1-k-means-and-hierarchical-clustering).
- **Dimensionality reduction** — compressing data with many columns
  into fewer, more informative ones, for visualization or to feed into
  a downstream model more efficiently. See
  [§4](classical-ml-clustering-svm-and-dimensionality-reduction.md#4-pca-and-dimensionality-reduction)
  of the same page.
- **Anomaly detection** — flagging data points that don't resemble the
  rest of the dataset, used directly for fraud detection, equipment
  failure prediction, and intrusion detection — unsupervised because
  genuinely new fraud patterns, by definition, weren't in any labeled
  training set yet.
- Embeddings (see
  [Embeddings & Semantic Search](../ai-llm/embeddings-semantic-search.md)) are
  also fundamentally an unsupervised/self-supervised technique — no
  human labeled "these two sentences are similar," the structure is
  learned from co-occurrence in the data itself.

## 4. "How does reinforcement learning actually connect to LLMs?"

**Answer:**

- RLHF — the alignment step covered in
  [Fine-Tuning & the Model Training Lifecycle §4](../ai-llm/fine-tuning-and-training-lifecycle.md#4-what-is-rlhf-mechanically-and-why-not-just-supervised-fine-tune-on-only-the-best-examples)
  — is literally reinforcement learning applied to an LLM: the
  "environment" is a conversation, the "action" is the next token or
  full response generated, and the "reward" comes from a model trained
  on human preference judgments instead of a hand-coded game score.
- This is the clearest bridge between classical RL (originally
  developed for games and robotics — an agent moving through a maze,
  balancing a pole) and the LLM material in the rest of this section:
  same core learning mechanism (trial, reward signal, adjust), applied
  to a completely different kind of "environment."
- **Interview point:** "is ChatGPT reinforcement learning?" is a
  common confused question — the base model itself is trained by
  supervised next-token prediction (pretraining, see
  [Fine-Tuning §2](../ai-llm/fine-tuning-and-training-lifecycle.md#2-what-is-pretraining-actually-learning-and-why-does-it-need-so-much-data-and-compute)),
  and only the *alignment* stage on top of that is RL. The honest
  answer names both stages, not just one.

## 5. "What's the bias-variance tradeoff, and why does every model eventually run into it?"

**Answer:**

- **Bias** is error from a model being too simple to capture the real
  pattern — it makes the same kind of mistake consistently, regardless
  of which specific training data it saw (underfitting).
- **Variance** is error from a model being too sensitive to the
  specific training data it happened to see — it fits that data's
  noise, not just its real pattern, so its predictions swing wildly if
  trained on a slightly different sample (overfitting).
- These trade off against each other as a model gets more complex: a
  straight line fit to curved data has high bias, low variance (stable
  but wrong); a model that memorizes every training point has low
  bias, high variance (fits training data perfectly, generalizes
  badly). The goal is the sweet spot in between, measured by
  performance on *held-out* data the model never trained on — see
  [Model Evaluation & Validation §1](model-evaluation-and-validation.md#1-why-does-a-model-need-a-separate-training-validation-and-test-split).
- This single idea is the reason almost every technique in this
  section exists: regularization
  ([Regularization & Hyperparameter Tuning](regularization-and-hyperparameter-tuning.md))
  deliberately adds bias to reduce variance; ensemble methods
  ([Classical ML §3](classical-ml-regression-trees-and-ensembles.md#3-ensemble-methods-random-forests-and-gradient-boosting))
  average multiple high-variance models together to cancel out their
  individual noise; more training data reduces variance without
  touching bias at all.

| Symptom | Likely cause | Typical fix |
|---|---|---|
| High error on both training and test data | High bias (underfitting) | More complex model, more/better features |
| Low training error, high test error | High variance (overfitting) | More data, regularization, a simpler model |
| Both errors low and close together | Good fit | Ship it, keep monitoring (see [Model Monitoring & Drift Detection](model-monitoring-and-drift-detection.md)) |

---

## Code Samples

No dedicated code samples for this page — it's conceptual framing for
the classical ML pages that follow.
