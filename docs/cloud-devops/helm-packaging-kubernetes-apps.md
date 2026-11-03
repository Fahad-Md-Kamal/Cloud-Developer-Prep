---
title: "Helm: Packaging Kubernetes Applications"
---

# Helm: Packaging Kubernetes Applications

**Helm** packages a Kubernetes application's manifests — a Deployment,
Service, ConfigMap, Secret, Ingress, all needing to stay consistent
with each other — so the same definition can be reused across
environments instead of hand-maintaining near-duplicate YAML per
environment. For *when* and *how* a packaged application actually gets
deployed, see
[GitOps: Git as the Source of Truth for Deployments](gitops-with-argocd-and-flux.md)
— Helm and GitOps solve different problems and compose directly,
covered there in
[§7](gitops-with-argocd-and-flux.md#7-how-does-gitops-compose-with-helm).

## The Problem It Solves

A real application isn't one Kubernetes object — it's a Deployment, a
Service, a ConfigMap, a Secret, maybe an Ingress, all needing to stay
consistent with each other. Deploying it to dev, staging, and
production means either hand-maintaining near-duplicate copies of all
of that YAML per environment, or building your own templating by hand
— both error-prone, and both get worse as the number of environments
and services grows.

## A Chart: Templates Plus Values

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

---

## Code Samples

No dedicated code samples for this page — see
[EKS Fundamentals](container-orchestration-ecs-eks.md#eks-fundamentals)
for the underlying Kubernetes mechanics Helm templates target.
