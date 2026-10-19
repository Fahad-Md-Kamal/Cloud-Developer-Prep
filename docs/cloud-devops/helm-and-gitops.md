---
title: "Helm & GitOps: Packaging and Deploying to Kubernetes"
---

# Helm & GitOps: Packaging and Deploying to Kubernetes

Two practices that show up constantly in a real Kubernetes setup but
rarely get explained together, even though they compose directly:
**Helm** packages an application's Kubernetes manifests so the same
definition can be reused across environments, and **GitOps** controls
*when* and *how* that package actually gets deployed — by applying the
same reconciliation-loop idea already covered in
[EKS Fundamentals](container-orchestration-ecs-eks.md#what-kubectl-apply-actually-does)
to your own application, not just to Kubernetes' own built-in objects.

## Helm: Packaging Kubernetes Manifests

### The Problem It Solves

A real application isn't one Kubernetes object — it's a Deployment, a
Service, a ConfigMap, a Secret, maybe an Ingress, all needing to stay
consistent with each other. Deploying it to dev, staging, and
production means either hand-maintaining near-duplicate copies of all
of that YAML per environment, or building your own templating by hand
— both error-prone, and both get worse as the number of environments
and services grows.

### A Chart: Templates Plus Values

A **Helm chart** is a packaged bundle that separates the *shape* of the
manifests from the *values* that differ per environment.

```
my-app/
├── Chart.yaml          # name, version, metadata
├── values.yaml          # default values (replica count, image tag, ...)
├── templates/
│   ├── deployment.yaml  # a Kubernetes Deployment, with {{ .Values.X }} placeholders
│   ├── service.yaml
│   └── ingress.yaml
└── charts/               # dependency sub-charts (e.g. a bundled Postgres chart)
```

```yaml
# templates/deployment.yaml (excerpt)
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
        - name: my-app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

```bash
helm install my-app ./my-app -f values-prod.yaml
helm upgrade my-app ./my-app -f values-prod.yaml --set image.tag=v1.4.2
helm rollback my-app 3   # back to revision 3
```

- The **same chart** gets installed into dev, staging, and production —
  only the `values.yaml` passed in differs (replica count, image tag,
  resource limits, domain name), instead of maintaining separate full
  copies of the manifests per environment.
- A **release** is a named, tracked instance of a chart installed into
  a cluster — this is Helm's actual value-add over "just template the
  YAML yourself with some other tool": every `helm upgrade` is recorded
  as a new revision, and `helm rollback` reverts the release to any
  earlier recorded revision, not just "undo the last change."
- **Chart repositories** (Artifact Hub, or a private one) work like a
  package registry for charts — `helm repo add`, then
  `helm install` a published chart instead of writing one from scratch
  for common software (Postgres, Redis, nginx-ingress all have
  well-maintained public charts already).
- **Dependencies**: a chart can declare other charts as dependencies in
  `Chart.yaml` — an application chart depending on a bundled Postgres
  chart, for example — so installing the app chart can also stand up
  everything it needs.

!!! success "The exam/interview-style signal"

    "Deploy the same application consistently across multiple
    environments with different configuration" → Helm. "Need versioned
    rollback of a deployment, not just `kubectl rollout undo` on one
    object at a time" → Helm releases track the whole bundle together,
    not one resource at a time.

## GitOps: Git as the Source of Truth for What's Deployed

### The Core Idea

[EKS Fundamentals](container-orchestration-ecs-eks.md#what-kubectl-apply-actually-does)
already covers how every Kubernetes controller runs the same loop:
observe actual state, compare to desired state, act to close the gap,
repeat forever. **GitOps applies that exact same idea to your own
application deployments** — except the "desired state" a GitOps
controller compares against isn't something a human typed into
`kubectl` by hand, it's **whatever's currently committed in a Git
repository**.

### GitOps vs. a Traditional "Push" Pipeline

| | Traditional CI/CD ("push") | GitOps ("pull") |
|---|---|---|
| Who changes the cluster | The CI pipeline, using credentials to `kubectl apply`/`helm upgrade` directly | A controller running *inside* the cluster, watching Git |
| Where cluster credentials live | In the CI system — a real, wide attack surface | Nowhere outside the cluster — the controller already has in-cluster access |
| What happens on a manual `kubectl edit` | Nothing catches it — the cluster and the "source of truth" can silently drift apart | The controller sees the drift (actual ≠ what's in Git) and can flag it, or revert it automatically |
| Rolling back | Re-run a deploy with the old version, or `kubectl rollout undo` | `git revert` the commit — the controller reconciles the cluster back to match |

- **The security win isn't incidental** — it's the main point for a lot
  of adopters. The CI system never needs direct write access to the
  cluster at all; it only needs to be able to push a commit to the Git
  repo the GitOps controller is watching.
- **Git becomes the actual audit log** of every change that was ever
  deployed — not a separate deployment history system, just normal
  `git log` on the repo describing desired state.

### ArgoCD and Flux

`ArgoCD`
:   Defines an **Application** custom resource mapping a Git
    repo/path to a target cluster and namespace. Supports **manual
    sync** (someone clicks "sync" or runs a command once they're ready)
    or **automated sync** (deploys the moment a change lands in Git,
    no human step). Its UI directly shows **drift** — a resource that's
    "out of sync" because someone changed it by hand instead of through
    Git — and can be configured for **self-healing**, automatically
    reverting manual changes back to match Git.

`Flux`
:   The same core idea, built to feel more like a native extension of
    Kubernetes itself (a set of controllers, no separate UI by
    default). Its Helm Controller specifically watches a Git repo for
    Helm chart + values changes and reconciles Helm releases directly —
    the natural pairing with everything covered above.

!!! danger "GitOps doesn't replace Helm — it usually deploys it"

    These aren't competing choices. A common real setup: a Helm chart
    defines *what* the application looks like (the templated
    manifests); a Git repo holds *which* chart version and *which*
    `values.yaml` should currently be running in each environment; and
    ArgoCD or Flux is the controller continuously making sure the
    cluster actually matches what that repo says. Change an image tag
    in `values-prod.yaml`, commit it, and the controller does the
    `helm upgrade` for you — no one ever runs `helm upgrade` by hand
    against production again.

!!! success "The exam/interview-style signal"

    "Reduce the attack surface of giving a CI pipeline direct
    cluster-admin credentials" → GitOps (pull-based), not a traditional
    push pipeline. "Detect and correct configuration drift from manual
    changes automatically" → ArgoCD/Flux's reconciliation loop, the
    same mechanism — just pointed at your own application instead of
    Kubernetes' own built-in controllers.
