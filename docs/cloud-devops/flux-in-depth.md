---
title: "Flux In Depth"
---

# Flux In Depth

**Flux** is a GitOps controller for Kubernetes, built as a set of
small, focused controllers (the **GitOps Toolkit**) rather than one
platform with a UI — each controller owns one job, and they compose
through Kubernetes custom resources that reference each other. See
[GitOps Fundamentals](gitops-fundamentals.md) for the pull-based
reconciliation idea this implements, and
[ArgoCD In Depth](argocd-in-depth.md) for the alternative.

!!! note "Version"
    Written for Flux v2 (the GitOps Toolkit architecture — a full
    rewrite from the original Flux v1, which is end-of-life and not
    covered here).

## 1. The GitOps Toolkit: One Controller, One Job

**Answer:**

- **`source-controller`** — the only component that actually talks to
  Git/Helm repos/OCI registries/S3-compatible buckets. It watches a
  **`GitRepository`** (or `HelmRepository`, `OCIRepository`, `Bucket`)
  resource, pulls the content, and exposes it as an internal artifact
  other controllers can consume — no other controller fetches
  anything from outside the cluster directly.
- **`kustomize-controller`** — watches **`Kustomization`** resources,
  takes the artifact a `GitRepository` produced, runs `kustomize
  build` against a path inside it, and applies the result to the
  cluster — the component implementing the actual reconciliation loop
  for plain manifests.
- **`helm-controller`** — watches **`HelmRelease`** resources,
  combines a chart artifact (from a `HelmRepository` or `OCIRepository`)
  with values, and performs the equivalent of `helm upgrade`
  automatically — the natural pairing with
  [Helm](helm-packaging-kubernetes-apps.md) named in
  [GitOps Fundamentals §5](gitops-fundamentals.md#5-how-does-gitops-compose-with-helm).
- **`notification-controller`** and the **image-reflector/
  image-automation-controllers** are covered in §4-5 below — all of
  these are separate, independently-deployable controllers, which is
  the actual meaning of "GitOps Toolkit" rather than "Flux" being one
  monolithic binary.

## 2. Source Resources: Where Flux Gets Its Content

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app-deploy
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/org/my-app-deploy.git
  ref:
    branch: main
```

**Answer:**

- **`interval`** is how often `source-controller` polls for new
  commits — Flux is fundamentally a **polling** system by default
  (not instant-on-push), though a webhook receiver can trigger an
  immediate reconcile without waiting for the next poll.
- **`ref`** pins to a branch, a tag, a specific commit SHA, or a
  semver range (`tag: ">=1.0.0 <2.0.0"`) — useful for tracking a
  specific release line of a shared deploy repo rather than always
  `main`.
- `HelmRepository` and `OCIRepository` are the same idea applied to a
  Helm chart repository or an OCI registry holding charts/artifacts
  directly — Flux treats "where do I get content from" as one
  consistent abstraction regardless of whether the content is plain
  YAML, a Helm chart, or an OCI artifact.

## 3. The `Kustomization` Resource

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app-prod
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: my-app-deploy
  path: ./overlays/prod
  prune: true
  dependsOn:
    - name: shared-infra
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: my-app
      namespace: my-app
  postBuild:
    substitute:
      cluster_name: "prod-use1"
```

**Answer:**

- `sourceRef` + `path` is the Flux equivalent of ArgoCD's
  `source.repoURL` + `source.path` — which `GitRepository` to read
  from, and which directory inside it to build with Kustomize.
- **`prune: true`** — same meaning as ArgoCD's `syncPolicy.automated.prune`
  (§2 on the ArgoCD page): resources removed from Git get deleted from
  the cluster too, not just left orphaned.
- **`dependsOn`** — this `Kustomization` won't reconcile until the
  named one has successfully reconciled first, Flux's answer to
  ArgoCD's sync waves/hooks (ordering "shared infra" before an app
  that needs it) — expressed as a dependency between `Kustomization`
  resources rather than an annotation on individual objects.
- **`healthChecks`** — explicit resources Flux waits on to be `Ready`
  before considering this `Kustomization` itself healthy, which other
  `Kustomization`s can then depend on.
- **`postBuild.substitute`** — variable substitution applied to the
  rendered manifests *after* `kustomize build` runs, for values that
  genuinely differ per cluster/environment (a cluster name, a region)
  without needing a separate Kustomize overlay just for one string.

## 4. The `HelmRelease` Resource

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: my-app
  namespace: my-app
spec:
  interval: 5m
  chart:
    spec:
      chart: my-app
      version: "1.4.x"
      sourceRef:
        kind: HelmRepository
        name: my-app-charts
  values:
    replicaCount: 3
  upgrade:
    remediation:
      retries: 3
```

**Answer:**

- A `HelmRelease` is Flux's equivalent of running `helm upgrade`
  directly — `chart.spec` names which chart and version (supporting a
  semver range like `1.4.x`, so a new patch release can roll out
  automatically on the next reconcile without a Git change at all,
  *if* that's actually the desired behavior), and `values` is the
  same `values.yaml` content Helm itself would take.
- **`upgrade.remediation.retries`** — if a `helm upgrade` fails (a
  failed hook, a timeout), `helm-controller` can automatically retry,
  and (with `remediateLastFailure: true`) roll back to the last known
  good release — turning Helm's own manual `helm rollback` into an
  automated reconciliation behavior instead of a human running a
  command after noticing a problem.
- **Interview point**: "how does Flux handle a failed Helm upgrade
  without a human intervening?" — expects naming
  `upgrade.remediation` and its automatic retry/rollback behavior,
  not just "someone would run `helm rollback`."

## 5. Image Automation: Flux's Distinctive Feature

```yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: my-app
spec:
  imageRepositoryRef:
    name: my-app-repo
  policy:
    semver:
      range: ">=1.0.0"
```

**Answer:**

- This is the one capability that genuinely has no equivalent built
  into core ArgoCD (ArgoCD's version is the separate Image Updater
  add-on, §6 on the ArgoCD page) — Flux ships it as part of the core
  toolkit: **`ImageRepository`** scans a registry for available tags;
  **`ImagePolicy`** picks the "best" one by a policy (semver range, as
  above, or a regex/alphabetical ordering); **`ImageUpdateAutomation`**
  actually **commits** the new tag back into the Git repo's manifests
  automatically.
- The real consequence worth naming explicitly: this means Git isn't
  always purely human-authored — a bot can open (or directly push) a
  commit bumping an image tag, which is *also* a legitimate part of
  "Git is the source of truth," since that commit is still reviewable
  history, just authored by automation instead of a person.
- **Interview point**: "can Flux automatically deploy a new image the
  moment it's pushed to a registry, with no human editing a YAML
  file?" — expects yes, via `ImageRepository`/`ImagePolicy`/
  `ImageUpdateAutomation` together, and that this writes an actual Git
  commit (preserving the audit trail from
  [GitOps Fundamentals §1](gitops-fundamentals.md#1-what-is-gitops-and-how-is-it-actually-different-from-a-normal-cicd-pipeline)),
  not a side-channel deploy that bypasses Git.

## 6. Multi-Tenancy and Notifications

**Answer:**

- Flux's multi-tenancy model is built on **Kubernetes RBAC and
  namespaces directly**, rather than a separate project concept like
  ArgoCD's `AppProject`: a `Kustomization`/`HelmRelease` can specify a
  `serviceAccountName` it reconciles **as**, and that service
  account's own RBAC permissions (scoped to one namespace, typically)
  become the real ceiling on what that `Kustomization` is allowed to
  touch — "impersonation," enforced by Kubernetes' own RBAC instead
  of a Flux-specific policy engine.
- **`notification-controller`** fires on reconciliation events the
  same way ArgoCD's notifications do — an `Alert` resource names which
  events to watch and a `Provider` resource (Slack, a generic webhook,
  Microsoft Teams) names where to send them, kept as two separate
  resources so one `Provider` can be reused by multiple `Alert` rules.

## 7. The Flux CLI and Bootstrap

```bash
flux bootstrap github \
  --owner=my-org \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/prod
```

**Answer:**

- **`flux bootstrap`** is the standard way to install Flux at all — it
  installs the controllers into the cluster **and** commits Flux's own
  manifests into the target Git repo/path, so from the very first
  install, Flux is already managing itself via GitOps, not just the
  applications it's pointed at afterward.
- This is a genuine structural difference worth naming against ArgoCD,
  which is typically installed via a plain Helm chart or manifest
  apply first, with GitOps self-management as something set up
  afterward rather than the default install path itself.
- `flux get kustomizations`, `flux get helmreleases`, and `flux logs`
  are the day-to-day CLI equivalent of ArgoCD's UI — since there's no
  UI by default (§1 on this page, and
  [GitOps Fundamentals §2](gitops-fundamentals.md#2-argocd-or-flux-how-do-you-actually-choose)),
  the CLI (or a separate dashboard like Weave GitOps/Capacitor) is how
  a team actually watches reconciliation status day to day.

## 8. Interview Questions You're Likely to Get Asked

**Architecture**

- "Name the Flux controller responsible for actually applying
  manifests to the cluster." — expects `kustomize-controller` (for
  plain/Kustomize manifests) or `helm-controller` (for `HelmRelease`
  resources) — not `source-controller`, which only fetches content,
  [§1](#1-the-gitops-toolkit-one-controller-one-job).
- "How does Flux order a dependency between two applications?" —
  expects `dependsOn` between `Kustomization` resources,
  [§3](#3-the-kustomization-resource).

**Depth**

- "Can Flux automatically deploy a newly-pushed image with no human
  editing a manifest?" — expects `ImageRepository`/`ImagePolicy`/
  `ImageUpdateAutomation`, and that it commits back to Git,
  [§5](#5-image-automation-fluxs-distinctive-feature).
- "How does Flux recover from a failed Helm upgrade automatically?" —
  expects `HelmRelease`'s `upgrade.remediation` retry/rollback
  behavior, [§4](#4-the-helmrelease-resource).

**Design**

- "How does Flux restrict what one team's `Kustomization` is allowed
  to touch, without a separate project resource like ArgoCD has?" —
  expects Kubernetes RBAC via `serviceAccountName` impersonation,
  [§6](#6-multi-tenancy-and-notifications).
- "What does `flux bootstrap` actually do, beyond installing the
  controllers?" — expects that it also commits Flux's own manifests
  into Git, making Flux self-managing from the first install,
  [§7](#7-the-flux-cli-and-bootstrap).

---

## Code Samples

No dedicated code samples for this page — the YAML throughout is
complete and intended to be adapted directly; see
[EKS Fundamentals](container-orchestration-ecs-eks.md#eks-fundamentals)
for the underlying Kubernetes reconciliation mechanics Flux itself
builds on.
