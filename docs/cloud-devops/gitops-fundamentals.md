---
title: "GitOps Fundamentals"
---

# GitOps Fundamentals

**GitOps** is a way of deploying software where a Git repository — not
a human running commands, not a CI pipeline pushing changes directly —
is the single source of truth for what should currently be running. A
controller inside the cluster continuously compares the cluster's
actual state against whatever is committed in Git, and acts to close
any gap it finds. This page covers the ideas common to any GitOps
setup; for the two controllers that actually implement them, see
[ArgoCD In Depth](argocd-in-depth.md) and [Flux In Depth](flux-in-depth.md).
For Kubernetes packaging specifically, see
[Helm: Packaging Kubernetes Applications](helm-packaging-kubernetes-apps.md) —
covered together in [§5](#5-how-does-gitops-compose-with-helm).

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

## 2. "ArgoCD or Flux — how do you actually choose?"

**Answer:**

- Both implement the exact same core loop from [§1](#1-what-is-gitops-and-how-is-it-actually-different-from-a-normal-cicd-pipeline)
  — a controller reconciling cluster state against Git — and both are
  CNCF graduated projects, so neither is the "more official" choice.
- **ArgoCD** ships as a platform with its own UI and an explicit
  `Application` resource model — see [ArgoCD In Depth](argocd-in-depth.md).
  Tends to win when multiple teams need a shared visual view of what's
  deployed where.
- **Flux** ships as a set of focused Kubernetes controllers with no UI
  by default, meant to feel like a native extension of Kubernetes
  itself — see [Flux In Depth](flux-in-depth.md). Tends to win for
  teams that want GitOps to feel like "just another set of controllers"
  integrated into existing tooling and observability.
- The decision comes down to team workflow and existing tooling, not
  capability or maturity — either can do everything described on this
  page.

## 3. "Secrets can't live in Git in plaintext — so how does GitOps actually handle them?"

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
  decryptable via a KMS key, PGP, or age — both Flux's
  kustomize-controller and ArgoCD support decrypting SOPS-encrypted
  files natively during reconciliation.
- **Interview point**: "doesn't GitOps mean your secrets are in Git?"
  is a common trap question — the honest answer names a specific
  mechanism (sealed values, or a reference-only pointer to an external
  store) rather than either "yes, that's a real problem" or a vague
  "there are tools for that."

## 4. "How do you promote a change from dev to staging to production with GitOps?"

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
- Fanning this out to many clusters at once is exactly what ArgoCD's
  ApplicationSets or Flux's multi-cluster patterns are for — see the
  dedicated pages for the mechanism each uses.

## 5. "How does GitOps compose with Helm?"

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

## 6. "How does progressive delivery (canary/blue-green) work the GitOps way?"

**Answer:**

- [CI/CD & Progressive Delivery](cicd-and-progressive-delivery.md#progressive-delivery-runbook-readiness-review)
  already covers *why* canary/blue-green matter and what makes a
  canary real (a deliberate pause, a metrics-gated decision) — that
  page's version is driven by a push-based pipeline (ECS/CodeDeploy,
  weighted ALB target groups). The GitOps-native equivalent makes the
  rollout itself a Kubernetes custom resource reconciled by a
  controller, not a pipeline script — **Argo Rollouts** for ArgoCD,
  **Flagger** for Flux, both covered on their dedicated pages.
- The real shift from the pipeline-driven version: the *rollout
  strategy itself* now lives in Git as a resource definition, so
  "what does our canary process look like" is reviewable in a pull
  request and version-controlled exactly like everything else —
  instead of being pipeline-script logic living outside the GitOps
  loop entirely.

## 7. Interview Questions You're Likely to Get Asked

**Core concept**

- "What's the actual structural difference between GitOps and a
  traditional CI/CD pipeline?" — expects naming *who* changes the
  cluster (a controller pulling, vs. a pipeline pushing) and the
  credential-location consequence,
  [§1](#1-what-is-gitops-and-how-is-it-actually-different-from-a-normal-cicd-pipeline).
- "ArgoCD or Flux — how do you actually choose?" — expects naming it
  as a team-workflow/tooling decision, not a maturity difference,
  [§2](#2-argocd-or-flux-how-do-you-actually-choose).

**Depth**

- "Doesn't GitOps mean secrets are sitting in Git?" — expects naming a
  specific real mechanism (Sealed Secrets, External Secrets Operator,
  or SOPS), not a vague "there are tools for that,"
  [§3](#3-secrets-cant-live-in-git-in-plaintext-so-how-does-gitops-actually-handle-them).

**Design**

- "How do you actually promote a build from staging to production in
  a GitOps workflow?" — expects a pull request against a
  production-specific path/overlay, not a separate deploy tool,
  [§4](#4-how-do-you-promote-a-change-from-dev-to-staging-to-production-with-gitops).

---

## Code Samples

No dedicated code samples for this page — see
[ArgoCD In Depth](argocd-in-depth.md#code-samples) and
[Flux In Depth](flux-in-depth.md#code-samples) for runnable manifests.
