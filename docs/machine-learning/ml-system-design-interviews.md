---
title: "ML System Design Interviews"
---

# ML System Design Interviews

"Design a recommendation system," "design a fraud detection pipeline,"
"design a search ranking system" — these look like regular system
design questions wearing an ML costume, but they're actually testing a
different skill: knowing where the *model* fits into the system, and
the ML-specific failure modes a generic system design framework never
covers. See
[System Design Methodology](../architecture/system-design-methodology.md)
for the general interview framework this builds directly on top of.

## 1. "How is an ML system design question actually different from a regular one?"

**Answer:**

- A regular system design question is almost entirely about data flow,
  storage, and scale — get those right and you're done.
- An ML system design question adds a second axis most candidates
  under-practice: **where does the model fit, how is it trained, how
  is it evaluated, and what happens when its real-world performance
  degrades** — covered throughout
  [MLOps](mlops-experiment-tracking-and-deployment.md) and
  [Model Monitoring & Drift Detection](model-monitoring-and-drift-detection.md).
  A design that nails the infrastructure but never mentions how the
  model gets retrained, or how you'd know it's working, is incomplete
  by ML-interview standards even if it would pass a regular system
  design interview.
- **The strongest answers explicitly walk both axes**: the regular
  system design framework (requirements → data flow → storage →
  scale), *and* the ML-specific one below — not just bolting "and then
  we train a model" onto an otherwise generic design.

## 2. The ML-Specific Framework to Walk Through

**Answer:**

- **Problem framing** — is this actually a supervised, unsupervised,
  or ranking problem? What's the target variable, concretely, and
  where does its label come from (explicit user feedback, implicit
  signal like a click, a delayed outcome like a 30-day default)? Get
  this wrong and everything downstream is solving the wrong problem —
  see
  [Supervised, Unsupervised & Reinforcement Learning §1](supervised-unsupervised-and-reinforcement-learning.md#1-whats-the-actual-difference-between-supervised-unsupervised-and-reinforcement-learning).
- **Data** — what data exists, how is it labeled (and how expensive/
  slow is getting more labels), and what's the realistic training
  volume? A design that assumes abundant clean labeled data for a
  problem where labels are actually scarce and expensive (fraud,
  medical diagnosis) needs to address that gap directly, not assume it
  away.
- **Model choice** — start simple and justify complexity, don't default
  to the fanciest option. "Why not deep learning here?" is a
  legitimate, common follow-up when a simpler model (logistic
  regression, gradient-boosted trees — see
  [Classical ML: Regression, Trees & Ensembles](classical-ml-regression-trees-and-ensembles.md))
  would plausibly work; a strong answer names the actual trade-off
  (interpretability, training data volume needed, latency budget, team
  ability to maintain it) rather than picking the impressive-sounding
  option by reflex.
- **Evaluation** — what offline metric (from
  [Model Evaluation & Validation](model-evaluation-and-validation.md))
  predicts the real business outcome, and what online metric (A/B test
  result, not just offline F1) actually confirms it worked once
  deployed? These are routinely different numbers, and conflating them
  is a common, flagged mistake — an offline metric can improve while
  the real online business metric doesn't move, or moves the wrong
  way.
- **Serving and scale** — batch vs. real-time
  ([MLOps §5](mlops-experiment-tracking-and-deployment.md#5-serving-patterns)),
  and the latency budget the model has to fit inside.
- **Monitoring and iteration** — how is drift detected
  ([Model Monitoring & Drift Detection](model-monitoring-and-drift-detection.md)),
  and what triggers retraining
  ([MLOps §4](mlops-experiment-tracking-and-deployment.md#4-cicd-for-ml))?
  A design that stops at "and then it's deployed" with no mention of
  what happens after is treated as unfinished.

## 3. Worked Example: "Design a Recommendation System"

**Answer:**

- **Problem framing:** implicit feedback (clicks, watch time,
  purchases) almost always stands in for an explicit "did the user
  like this" label, since asking users to rate everything doesn't
  scale — worth naming explicitly, since it changes what the target
  variable actually is.
- **Two-stage architecture is the standard answer, and naming it
  directly is a strong signal:** a cheap **candidate generation** stage
  narrows millions of items down to a few hundred plausible candidates
  (often via embeddings and approximate nearest-neighbor search — see
  [Embeddings & Semantic Search](../ai-llm/embeddings-semantic-search.md)),
  followed by a more expensive, more accurate **ranking** model that
  scores just those few hundred precisely. Running the expensive
  ranking model over the *entire* catalog for every request is the
  common naive mistake this two-stage split exists to avoid.
- **The cold-start problem** — new users and new items have no
  interaction history to learn from — is close to a guaranteed
  follow-up. Content-based features (item metadata, user profile
  attributes) as a fallback when collaborative signal doesn't exist
  yet is the expected answer.
- **Evaluation:** offline, ranking-specific metrics (precision@k,
  NDCG) rather than plain accuracy, since the whole point is the
  *order* of recommendations, not a single yes/no prediction per item
  — then an online A/B test on actual engagement/conversion to confirm
  the offline improvement translates to real behavior.

## 4. Common Mistakes Interviewers Flag

**Answer:**

- Jumping straight to "we'll use deep learning" without naming what
  problem that complexity actually solves, or considering a simpler
  baseline first.
- Designing the training pipeline in detail while never mentioning how
  the model gets served, monitored, or retrained — treating "train a
  good model" as the entire problem instead of one stage in an
  ongoing system.
- Picking an offline metric and never connecting it back to the actual
  business/product goal, or never distinguishing offline evaluation
  from an online experiment's result.
- Ignoring label availability and cost — assuming a clean, large
  labeled dataset exists for a problem where real labels are actually
  scarce, delayed, or expensive to collect.

---

## Code Samples

No dedicated code samples for this page — it's an interview framework,
not a runnable system.
