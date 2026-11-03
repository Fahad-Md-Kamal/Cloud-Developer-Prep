---
title: "ArgoCD In Depth"
---

# ArgoCD In Depth

**ArgoCD** is a GitOps controller for Kubernetes, packaged as a full
platform — a set of in-cluster services plus a web UI and CLI — built
around one custom resource, the **`Application`**, that maps a Git
repo/path to a destination cluster and namespace. See
[GitOps Fundamentals](gitops-fundamentals.md) for the pull-based
reconciliation idea this implements, and
[Flux In Depth](flux-in-depth.md) for the alternative.

!!! note "Version"
    Written for ArgoCD 2.x (the stable major version in common
    production use at the time of writing). Core resource shapes
    (`Application`, `AppProject`, `ApplicationSet`) have been stable
    across the 2.x line.

## 1. Architecture: What's Actually Running in the Cluster

**Answer:**

- **`argocd-server`** — the API server and the backend for the web UI
  and CLI; the only component that needs to be reachable from outside
  the cluster.
- **`argocd-repo-server`** — clones the Git repo (or pulls the Helm
  chart/OCI artifact) and renders the manifests that *should* exist
  (running `helm template`, `kustomize build`, or just reading plain
  YAML, depending on what the `Application` points at). It never talks
  to the Kubernetes API directly — it only produces rendered manifests.
- **`argocd-application-controller`** — the actual reconciliation
  loop: takes what `repo-server` rendered, diffs it against live
  cluster state, and applies the diff when a sync is triggered. This
  is the component implementing the core loop from
  [GitOps Fundamentals §1](gitops-fundamentals.md#1-what-is-gitops-and-how-is-it-actually-different-from-a-normal-cicd-pipeline).
- **Redis** — caches rendered manifests and live cluster state so the
  controller doesn't re-render/re-list on every reconcile tick.
- **Dex** (optional) — an identity broker for SSO, letting ArgoCD
  delegate login to an existing OIDC/SAML/LDAP provider instead of
  managing its own user database.

## 2. The `Application` Resource

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/my-app-deploy.git
    targetRevision: main
    path: overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

**Answer:**

- **`source`** names the Git repo, the revision (a branch, tag, or
  commit SHA — not just always `HEAD` of a branch), and the path
  within it. ArgoCD supports plain manifests, a Kustomize overlay, or
  a Helm chart (with `source.helm.valueFiles`) in that same field —
  the repo-server (§1) figures out which based on what it finds at
  that path.
- **`destination`** is the target cluster (ArgoCD can manage clusters
  other than its own) and namespace.
- **`syncPolicy.automated`** turns on auto-sync — `prune: true` means
  ArgoCD also **deletes** resources that exist in the cluster but are
  no longer in Git (without it, removing a resource from Git leaves
  the orphaned object running forever); `selfHeal: true` is what
  actually reverts a manual `kubectl edit` back to match Git, not just
  flag it as drifted.
- Leaving `syncPolicy` empty means **manual sync** — the
  `Application` still shows drift/health status, but nothing is
  applied until someone runs `argocd app sync my-app-prod` or clicks
  Sync in the UI.
- **Sync windows** (configured on the `AppProject`, §5) restrict
  *when* automated sync is allowed to run at all — a real production
  need: "never auto-deploy during the Friday afternoon change freeze"
  without disabling automation entirely.

## 3. Sync Waves and Hooks: Controlling Apply Order

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "1"
```

**Answer:**

- By default, ArgoCD applies every resource in an `Application`
  together, in one pass — fine until something genuinely needs to
  happen **before** something else (a database migration before the
  new app version starts expecting the new schema).
- **`argocd.argoproj.io/sync-wave`** orders plain resources —
  lower numbers apply first, ArgoCD waits for each wave's resources to
  be healthy before starting the next wave.
- **Hooks** (`PreSync`, `Sync`, `PostSync`, `SyncFail`) are a separate
  mechanism specifically for one-shot operations like a migration
  `Job` — a `PreSync` hook resource runs and must complete
  successfully *before* the main sync proceeds at all; `PostSync` runs
  after everything else is healthy (smoke tests, a Slack notification);
  `SyncFail` runs cleanup if the sync failed partway through.
- **Interview point**: "how do you make sure a DB migration runs
  before the new app version starts, in a GitOps-managed deploy?" —
  expects naming a `PreSync` hook specifically, not just "add it to
  the same manifests and hope for the best."

## 4. App of Apps and ApplicationSets

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-app-all-clusters
spec:
  generators:
    - clusters: {}   # one Application per registered cluster
  template:
    metadata:
      name: '{{name}}-my-app'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/my-app-deploy.git
        targetRevision: main
        path: overlays/{{name}}
      destination:
        server: '{{server}}'
        namespace: my-app
```

**Answer:**

- **App of Apps** — an `Application` whose own Git path contains the
  manifests for *other* `Application` resources, not a workload
  directly. This is the original pattern for managing many
  applications from one root: one `git push` to the parent repo can
  add, remove, or reconfigure an entire set of child applications.
- **ApplicationSets** generate `Application` resources from a
  **template** plus a **generator** — the more modern, more flexible
  evolution of the same idea:
    - **List generator** — a fixed, hand-written list of parameter
      sets (e.g. one entry per environment).
    - **Cluster generator** — one `Application` per cluster ArgoCD
      already knows about, automatically, as shown above — adding a
      new cluster to ArgoCD is enough to deploy this app to it, no
      `ApplicationSet` edit needed.
    - **Git generator** — one `Application` per directory (or per file
      matching a glob) found in a Git repo — the mechanism behind
      "add a new overlay directory to add a new environment," named in
      [GitOps Fundamentals §4](gitops-fundamentals.md#4-how-do-you-promote-a-change-from-dev-to-staging-to-production-with-gitops).
    - **Matrix generator** — combines two other generators (e.g.
      clusters × Git directories) for "every app, on every cluster."
    - **Pull Request generator** — one `Application` per *open* PR
      against a repo, the mechanism behind automatic per-PR preview
      environments.
- **Interview point**: "the same app needs to deploy identically
  across 40 clusters — how?" — expects an `ApplicationSet` with a
  cluster generator, not 40 hand-written `Application` manifests.

## 5. Projects: Multi-Tenancy and RBAC

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-payments
  namespace: argocd
spec:
  sourceRepos:
    - https://github.com/org/payments-*
  destinations:
    - server: https://kubernetes.default.svc
      namespace: payments-*
  clusterResourceWhitelist: []   # no cluster-scoped resources allowed
```

**Answer:**

- By default every `Application` lives in the `default` `AppProject`,
  which places no real restriction on what it can do. A real
  multi-team ArgoCD installation creates one **`AppProject`** per
  team, restricting:
    - **`sourceRepos`** — which Git repos this project's applications
      are even allowed to point at.
    - **`destinations`** — which clusters/namespaces this project's
      applications are allowed to deploy into.
    - **`clusterResourceWhitelist`** — whether cluster-scoped
      resources (a `ClusterRole`, a `CustomResourceDefinition`) can be
      managed at all, separate from namespaced ones — the real control
      stopping one team's `Application` from quietly granting itself
      cluster-admin-adjacent permissions.
- RBAC on top of this (ArgoCD's own `argocd-rbac-cm` policy, usually
  tied to the SSO groups Dex provides, §1) controls which **users**
  can create/sync/delete `Application`s inside a given project — the
  combination of project restrictions (what an app *can* do) and RBAC
  (who can *act* on it) is ArgoCD's actual multi-tenancy model.

## 6. Keeping Images Current and Getting Notified

**Answer:**

- **ArgoCD Image Updater** watches configured container registries
  for new tags matching a policy (semver constraint, a `latest`-style
  tag, or a digest), and writes the new tag back — either as a direct
  Git commit to the deploy repo, or as an ArgoCD-internal parameter
  override — closing the loop from "new image built" to "deployed"
  without a human editing `values.yaml` by hand.
- **Notifications** (the `argocd-notifications` controller) fire on
  `Application` state changes — defining a trigger (`on-sync-failed`,
  `on-deployed`) plus a template and a destination (Slack, a generic
  webhook, email) — the standard way a team actually finds out a sync
  failed without someone having to keep the UI open.
- **CLI vs. UI vs. declarative**: `argocd app create`/`argocd app
  sync` from the CLI, clicking through the UI, and committing an
  `Application` YAML directly (as shown throughout this page) are
  three ways to reach the same API — in a real GitOps-mature setup,
  even the `Application` resources themselves are usually managed
  declaratively (an "app of `Application`s"), so the CLI/UI stay
  read-mostly, used for day-to-day visibility and manual sync
  triggers rather than as the primary way applications get defined.

## 7. Interview Questions You're Likely to Get Asked

**Architecture**

- "Which ArgoCD component actually talks to the Kubernetes API to
  apply changes?" — expects `argocd-application-controller`, not
  `repo-server` (which only renders manifests),
  [§1](#1-architecture-whats-actually-running-in-the-cluster).
- "What does `prune: true` actually do that a plain automated sync
  doesn't?" — expects deleting resources removed from Git, not just
  applying additions/changes,
  [§2](#2-the-application-resource).

**Depth**

- "How do you guarantee a database migration runs before the new app
  version is deployed, in ArgoCD?" — expects a `PreSync` hook,
  [§3](#3-sync-waves-and-hooks-controlling-apply-order).
- "How would you deploy the same application to 40 clusters without
  writing 40 manifests?" — expects an `ApplicationSet` with a cluster
  generator, [§4](#4-app-of-apps-and-applicationsets).

**Design**

- "How do you stop one team's ArgoCD `Application` from deploying into
  another team's namespace?" — expects an `AppProject` restricting
  `destinations`, not relying on convention,
  [§5](#5-projects-multi-tenancy-and-rbac).

---

## Code Samples

No dedicated code samples for this page — the YAML throughout is
complete and intended to be adapted directly; see
[EKS Fundamentals](container-orchestration-ecs-eks.md#eks-fundamentals)
for the underlying Kubernetes reconciliation mechanics ArgoCD itself
builds on.
