---
title: "Classical ML: Clustering, SVM & Dimensionality Reduction"
---

# Classical ML: Clustering, SVM & Dimensionality Reduction

Unsupervised learning's main algorithm families, plus Support Vector
Machines — a supervised classifier with a genuinely different
mechanism from the tree-based methods in
[Classical ML: Regression, Trees & Ensembles](classical-ml-regression-trees-and-ensembles.md).
See
[Supervised, Unsupervised & Reinforcement Learning §3](supervised-unsupervised-and-reinforcement-learning.md#3-what-does-unsupervised-learning-actually-get-used-for-concretely)
for what these get used for before the mechanics below.

## 1. K-Means and Hierarchical Clustering

```python
from sklearn.cluster import KMeans

kmeans = KMeans(n_clusters=4, n_init=10).fit(X)
labels = kmeans.labels_
```

- **K-means** picks `k` random starting points (centroids), assigns
  every data point to its nearest centroid, recomputes each centroid
  as the mean of its assigned points, and repeats until the
  assignments stop changing. Simple, fast, and the standard first
  thing to try for clustering.
- **`k` has to be chosen up front** — it's not learned from the data.
  The **elbow method** (plotting within-cluster variance against `k`
  and looking for where adding more clusters stops helping much) is
  the common heuristic for picking it.
- **Interview point:** k-means assumes clusters are roughly round and
  similarly sized, because it's literally built on distance-to-a-single-
  centroid — it does badly on elongated, nested, or very
  differently-sized clusters. That's the direct opening for
  **hierarchical clustering** (build a tree of nested clusters by
  repeatedly merging the closest pair, no need to pick `k` up front —
  cut the resulting tree, called a **dendrogram**, at whatever level
  gives the number of clusters you want) or **DBSCAN** (groups points
  by density, naturally handles irregular shapes and automatically
  marks sparse points as noise/outliers instead of forcing them into a
  cluster).

| Algorithm | Needs `k` up front? | Handles irregular shapes? | Handles outliers? |
|---|---|---|---|
| K-means | Yes | No — assumes round clusters | No — every point forced into a cluster |
| Hierarchical | No (cut the tree later) | Better than k-means | No |
| DBSCAN | No | Yes — density-based | Yes — labels sparse points as noise |

## 2. Support Vector Machines (SVM)

```python
from sklearn.svm import SVC

svm = SVC(kernel="rbf", C=1.0).fit(X_train, y_train)
```

- SVM finds the **decision boundary that maximizes the margin** —
  the distance between the boundary and the nearest point of each
  class (the **support vectors**) — rather than just any boundary
  that separates the classes, which tends to generalize better to new
  points near the edge of the training distribution.
- **The kernel trick** is SVM's genuinely distinctive idea: data that
  isn't linearly separable in its original space (think two concentric
  circles of different classes — no straight line separates them) can
  become linearly separable after being mapped into a higher-dimensional
  space. The kernel trick computes the *effect* of that mapping
  directly, without ever actually constructing the (potentially
  infinite-dimensional) transformed space — `kernel="rbf"` above is
  the most common choice for this.
- `C` controls the margin/misclassification trade-off: a high `C`
  penalizes misclassified training points heavily (a tighter fit,
  more prone to overfitting); a low `C` allows more margin violations
  for a wider, more generalizable margin — the SVM-specific version of
  the bias-variance knob.
- **Interview point:** SVMs scale poorly to large datasets (training
  cost grows roughly quadratically to cubically with the number of
  samples) and need feature scaling to work correctly, since they're
  explicitly distance-based — this is the real reason gradient-boosted
  trees displaced SVMs as the default choice for most tabular problems
  over the last decade, despite SVM's strong theoretical properties.

## 3. Naive Bayes

```python
from sklearn.naive_bayes import MultinomialNB

nb = MultinomialNB().fit(X_train_counts, y_train)
```

- Applies Bayes' theorem with one deliberately simplifying ("naive")
  assumption: every feature is independent of every other feature,
  given the class. That assumption is almost never literally true, but
  the algorithm still works well in practice, especially for text
  classification (spam filtering, sentiment) where features are word
  counts.
- **Why it still works despite a false assumption:** Naive Bayes only
  needs to rank classes correctly relative to each other, not produce
  perfectly calibrated probabilities — the independence assumption
  distorts the exact probabilities but often still preserves which
  class scores highest, which is all a classifier needs.
- Extremely cheap to train (a single pass counting feature/class
  co-occurrences) and a reasonable fast baseline to compare a heavier
  model against before concluding the heavier model's complexity is
  actually earning its keep.

## 4. PCA and Dimensionality Reduction

```python
from sklearn.decomposition import PCA

pca = PCA(n_components=2)
X_reduced = pca.fit_transform(X)
print(pca.explained_variance_ratio_)
```

- **PCA (Principal Component Analysis)** finds new axes (**principal
  components**) that are linear combinations of the original
  features, ordered so the first axis captures the most variance in
  the data, the second captures the most *remaining* variance while
  staying perpendicular to the first, and so on.
- Keeping only the first few components compresses a dataset with many
  correlated columns down to a handful of columns that still capture
  most of the real signal — used both for visualizing high-dimensional
  data in 2D/3D and for speeding up/denoising a downstream model by
  feeding it fewer, less redundant inputs.
- `explained_variance_ratio_` tells you exactly how much information
  each kept component preserves — the honest way to answer "how much
  did we lose by compressing," rather than assuming compression is
  free.
- **t-SNE and UMAP** are non-linear alternatives, strictly for
  *visualization* (never as model input) — they preserve local
  neighborhood structure (points close together in high dimensions
  stay close in the 2D plot) much better than PCA's linear projection,
  at the cost of distances in the plot not being globally meaningful —
  two clusters that look far apart in a t-SNE plot aren't necessarily
  more different than two that look close.

**Interview point:** "Does PCA remove features?" — no, and this trips
people up: PCA doesn't select a subset of the *original* columns, it
creates entirely new ones that are combinations of all of them.
Removing/selecting from the original features is **feature
selection**, covered in
[Feature Engineering for ML §4](feature-engineering-for-ml.md#4-feature-selection)
— a genuinely different technique with a different goal (interpretable
features kept) than PCA's (maximum variance preserved, in new,
less-interpretable axes).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
standard `scikit-learn` usage, runnable directly against any dataset
with `pip install scikit-learn`.
