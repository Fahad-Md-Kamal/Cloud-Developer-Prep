---
title: "GitOps: Git as the Source of Truth for Deployments"
---

# GitOps: Git as the Source of Truth for Deployments

**GitOps** is a way of deploying software where a Git repository — not
a human running commands, not a CI pipeline pushing changes directly —
is the single source of truth for what should currently be running. A
controller inside the cluster continuously compares the cluster's
actual state against whatever is committed in Git, and acts to close
any gap it finds. For Kubernetes packaging specifically, see
[Helm: Packaging Kubernetes Applications](helm-packaging-kubernetes-apps.md) — GitOps
and Helm solve different problems and compose directly, covered in
[§7](#7-how-does-gitops-compose-with-helm).

## 1. "What is GitOps, and how is it actually different from a normal CI/CD pipeline?"

**Answer:**

- [EKS Fundamentals](container-orchestration-ecs-eks.md#what-kubectl-apply-actually-does)
  already covers the core loop every Kubernetes controller runs:
  observe actual state, compare to desired state, act to close the
  gap, repeat forever. **GitOps applies that exact same loop to your
  own application deployments** — except the "desired state" isn't
  something a human typed into `kubectl` by hand, it's whatever is
  currently committed to a Git repository.
- The real, structural difference from a traditional pipeline is
  **who initiates the change**:

| | Traditional CI/CD ("push") | GitOps ("pull") |
|---|---|---|
| Who changes the cluster | The CI pipeline, using credentials to `kubectl apply`/`helm upgrade` directly | A controller running *inside* the cluster, watching Git |
| Where cluster credentials live | In the CI system — a real, wide attack surface | Nowhere outside the cluster — the controller already has in-cluster access |
| What happens on a manual `kubectl edit` | Nothing catches it — cluster and "source of truth" silently drift apart | The controller sees the drift (actual ≠ Git) and flags or reverts it |
| Rolling back | Re-run a deploy with the old version, or `kubectl rollout undo` | `git revert` the commit — the controller reconciles the cluster to match |

- **The security win is usually the actual point, not a side benefit**
  — the CI system never needs direct write access to the cluster at
  all; it only needs permission to push a commit to the Git repo the
  GitOps controller is already watching.
- **Git becomes the real audit log** of every change ever deployed —
  not a separate deployment-history system, just `git log` on a repo
  that describes desired state.

## 2. "How does ArgoCD actually work?"

**Answer:**

- An **`Application`** is ArgoCD's own custom resource — it maps a Git
  repo + path + target revision to a destination cluster and
  namespace. ArgoCD's controller continuously renders what that path
  in Git *should* produce (plain manifests, a Helm chart +
  `values.yaml`, a Kustomize overlay) and diffs it against the live
  cluster state.
- **Sync** is the act of applying that diff. **Manual sync** waits for
  someone to click "Sync" or run `argocd app sync` once they're ready;
  **automated sync** applies a change the moment it lands in Git, no
  human step at all.
- **Drift detection** — when the live cluster doesn't match Git (most
  often: someone ran `kubectl edit` directly against a resource),
  ArgoCD's UI shows that resource as `OutOfSync`. With **self-healing**
  enabled, the controller doesn't just flag it — it automatically
  reverts the manual change back to match Git on its own.
- **App of Apps** — an `Application` whose own Git path contains the
  manifests for *other* `Application` resources. This is the standard
  pattern for managing many applications (or the same application
  across many clusters) from one root: one `git push` to the parent
  repo can add, remove, or reconfigure an entire fleet of
  applications, not just one.
- **ApplicationSets** generate `Application` resources from a
  template plus a generator (a list of clusters, a Git directory
  structure, a pull request) — the practical tool for "the same app,
  deployed identically across 40 clusters" without hand-writing 40
  `Application` manifests.

## 3. "How does Flux differ from ArgoCD, and which do you actually pick?"

**Answer:**

- Same core idea as ArgoCD (§2) — a controller reconciling cluster
  state against Git — but Flux is built as **a set of Kubernetes
  controllers with no UI by default**, meant to feel like a native
  extension of Kubernetes itself rather than a separate platform with
  its own interface.
- Flux's **GitOps Toolkit** splits the job into focused controllers:
  a **source-controller** (watches Git/Helm/OCI repositories for
  changes), a **kustomize-controller** (applies Kustomize overlays),
  and a **helm-controller** (reconciles `HelmRelease` resources
  directly — watching a Git repo for chart version and `values.yaml`
  changes and running the equivalent of `helm upgrade` itself).
- **Picking between them** is mostly an organizational question, not
  a capability one: ArgoCD's built-in UI and more explicit
  `Application`/App-of-Apps model tend to win when multiple teams need
  a shared visual view of what's deployed where; Flux's
  controller-only, more composable design tends to win for teams that
  want GitOps to feel like "just another set of Kubernetes
  controllers" integrated into existing tooling, with observability
  handled by whatever the team already uses for the rest of the
  cluster.
- Both are CNCF graduated projects — neither is the "more official"
  choice; the decision comes down to team workflow and existing
  tooling, not maturity.

## 4. "Secrets can't live in Git in plaintext — so how does GitOps actually handle them?"

**Answer:**

- This is the first real objection anyone raises about GitOps, and
  there isn't one single standard answer — three genuinely different
  approaches are all in common use:
- **Sealed Secrets** (Bitnami) — a controller in the cluster holds a
  private key; a `kubectl` plugin encrypts a Secret *against that
  specific cluster's public key* into a `SealedSecret` custom
  resource, which **is safe to commit to Git** — it can only be
  decrypted by the controller that holds the matching private key,
  so a leaked Git repo alone doesn't leak the actual secret value.
- **External Secrets Operator** — Git holds only a *reference*
  (`ExternalSecret` naming a key in AWS Secrets Manager, Vault, or
  similar), never the secret value itself. The operator fetches the
  real value from that external store at reconcile time and creates a
  normal Kubernetes `Secret` from it — Git never touches the secret
  at all, at the cost of needing a separate secrets store as a real
  runtime dependency.
- **SOPS** (Mozilla) — encrypts just the *values* inside a YAML/JSON
  file in place (keys stay readable, so diffs in Git stay meaningful),
  decryptable via a KMS key, PGP, or age — Flux's kustomize-controller
  and ArgoCD both support decrypting SOPS-encrypted files natively
  during reconciliation.
- **Interview point**: "doesn't GitOps mean your secrets are in Git?"
  is a common trap question — the honest answer names a specific
  mechanism (sealed values, or a reference-only pointer to an external
  store) rather than either "yes, that's a real problem" or a vague
  "there are tools for that."

## 5. "How do you do progressive delivery (canary/blue-green) the GitOps way?"

**Answer:**

- [CI/CD & Progressive Delivery](cicd-and-progressive-delivery.md#progressive-delivery-runbook-readiness-review)
  already covers *why* canary/blue-green matter and what makes a
  canary real (a deliberate pause, a metrics-gated decision) — that
  page's version is driven by a push-based pipeline (ECS/CodeDeploy,
  weighted ALB target groups). This section covers the GitOps-native
  equivalent: the rollout itself is a Kubernetes custom resource
  reconciled by a controller, not a pipeline script.
- **Argo Rollouts** replaces a plain Kubernetes `Deployment` with a
  `Rollout` resource supporting canary and blue-green strategies
  natively — traffic shifting via a service mesh or ingress
  controller, an automated **AnalysisTemplate** that queries a metrics
  backend (Prometheus, Datadog) at each step and **automatically
  rolls back** if the new version's error rate/latency looks worse
  than the baseline, no human watching a dashboard required.
- **Flagger** is Flux's equivalent — same core idea (a custom resource
  driving a metrics-gated canary), integrated with Flux's own
  reconciliation model instead of ArgoCD's.
- The real shift from the pipeline-driven version: the *rollout
  strategy itself* now lives in Git as a resource definition, so
  "what does our canary process look like" is reviewable in a pull
  request and version-controlled exactly like everything else —
  instead of being pipeline-script logic living outside the GitOps
  loop entirely.

## 6. "How do you promote a change from dev to staging to production with GitOps?"

**Answer:**

- The actual "deploy to production" action in a mature GitOps setup
  is a **pull request** — typically one that bumps an image tag or a
  Helm `values.yaml` value in a production-specific path — merged
  and reviewed like any other code change, not a separate deployment
  tool or button.
- **Directory-per-environment** (Kustomize overlays: `base/` plus
  `overlays/dev/`, `overlays/staging/`, `overlays/prod/`, each
  patching the shared base) is the common layout — promoting a change
  means copying the already-proven staging config forward into the
  prod overlay, usually via an automated PR a CI job opens once
  staging has been stable for a defined period.
- **Branch-per-environment** (a `staging` branch auto-deploys, merging
  `staging` → `main` deploys to prod) is the alternative, simpler to
  reason about but less flexible when environments need genuinely
  different configuration shapes, not just different values.
- **ApplicationSets** (§2) extend this to many clusters: a generator
  that reads the directory structure or a list of clusters can turn
  "add a new environment" into "add a new overlay directory," with no
  change to the GitOps tooling itself.

## 7. "How does GitOps compose with Helm?"

**Answer:**

- These aren't competing choices — a common real setup uses both
  together: a **Helm chart** defines *what* the application looks like
  (the templated manifests, see
  [Helm §2](helm-packaging-kubernetes-apps.md#a-chart-templates-plus-values)); a
  **Git repo** holds *which* chart version and *which* `values.yaml`
  should currently be running in each environment; **ArgoCD or Flux**
  is the controller continuously making sure the cluster actually
  matches what that repo says.
- Change an image tag in `values-prod.yaml`, commit it, and the
  controller performs the equivalent of `helm upgrade` automatically —
  no one runs `helm upgrade` by hand against production again, which
  is exactly how the credential/audit-trail benefits from
  [§1](#1-what-is-gitops-and-how-is-it-actually-different-from-a-normal-cicd-pipeline)
  actually get enforced in practice, not just stated as a goal.

## 8. Interview Questions You're Likely to Get Asked

**Core concept**

- "What's the actual structural difference between GitOps and a
  traditional CI/CD pipeline?" — expects naming *who* changes the
  cluster (a controller pulling, vs. a pipeline pushing) and the
  credential-location consequence,
  [§1](#1-what-is-gitops-and-how-is-it-actually-different-from-a-normal-cicd-pipeline).
- "Someone runs `kubectl edit` directly against a GitOps-managed
  resource — what happens?" — expects drift detection, and
  self-healing if enabled,
  [§2](#2-how-does-argocd-actually-work).

**Depth**

- "Doesn't GitOps mean secrets are sitting in Git?" — expects naming a
  specific real mechanism (Sealed Secrets, External Secrets Operator,
  or SOPS), not a vague "there are tools for that,"
  [§4](#4-secrets-cant-live-in-git-in-plaintext-so-how-does-gitops-actually-handle-them).
- "How would you run a metrics-gated canary rollout natively in a
  GitOps-managed cluster?" — expects Argo Rollouts or Flagger, and
  that the rollout strategy itself is a Git-tracked resource,
  [§5](#5-how-do-you-do-progressive-delivery-canaryblue-green-the-gitops-way).
- "What's an App of Apps, and what real problem does it solve?" —
  expects managing many applications/clusters from one root
  Application, one commit affecting a whole fleet,
  [§2](#2-how-does-argocd-actually-work).

**Design**

- "How do you actually promote a build from staging to production in
  a GitOps workflow?" — expects a pull request against a
  production-specific path/overlay, not a separate deploy tool,
  [§6](#6-how-do-you-promote-a-change-from-dev-to-staging-to-production-with-gitops).
- "ArgoCD or Flux — how do you actually choose?" — expects naming it
  as a team-workflow/tooling decision, not a maturity difference,
  [§3](#3-how-does-flux-differ-from-argocd-and-which-do-you-actually-pick).

---

## Code Samples

No dedicated code samples for this page — see
[EKS Fundamentals](container-orchestration-ecs-eks.md#eks-fundamentals)
for the underlying Kubernetes reconciliation mechanics this page
builds on.
