---
title: Kong API Gateway
---

# Kong API Gateway

The specific gateway product interviewers mean when a JD says "API
Gateway (Kong)" — what it adds over a plain reverse proxy, and the
plugins that cover auth/rate limiting/multi-tenancy. For the general
API gateway concepts (not tied to one product) — including the
single-point-of-failure and added-latency trade-offs any gateway
carries — see
[API Gateway Architecture](api-gateway-architecture.md),
[Rate Limiting Strategies](rate-limiting-strategies.md), and
[Circuit Breakers, Retries & Bulkheads](circuit-breakers-retries-and-bulkheads.md).

## Overview

**What it is:**

- An API gateway — a reverse proxy purpose-built for API traffic,
  built on nginx/OpenResty — sitting in front of your backend services
  as the single entry point for external requests.
- Config is **declarative**: enable a capability (auth, rate limiting,
  logging) per route/service via a plugin, not custom proxy code.

**Why it's used:**

- Centralizes cross-cutting concerns in one place instead of
  duplicating auth/rate-limiting/logging logic in every service.
- One policy change (new rate limit, revoke a key) takes effect
  immediately, with no redeploy of any backend service.

**What Kong specifically adds, beyond what any gateway gives you:**

- Consistent enforcement — no individual service can forget to check
  auth, since the check never happens in the service at all.
- A large plugin ecosystem covering most needs out of the box, instead
  of hand-rolling auth/rate-limiting per service.
- One place to monitor and debug all external traffic.
- What this *doesn't* cover — the general gateway trade-offs (new
  single point of failure, one extra network hop, risk of becoming a
  dumping ground for logic that doesn't belong there) apply here the
  same way they apply to any gateway; see
  [API Gateway Architecture §1](api-gateway-architecture.md#1-what-does-an-api-gateway-actually-do-that-a-plain-load-balancer-doesnt)
  for that table rather than repeating it here.
- One thing worth calling out that's easy to forget: Kong only sees
  "is this a valid key" — business-level authorization ("can *this*
  user edit *this* order") still belongs in the service, same as for
  any gateway.

**Additional things worth knowing:**

- **Editions**: Kong Gateway (open-source, self-hosted) vs. Kong
  Enterprise (extra plugins, a dev portal, vendor support) vs. Kong
  Konnect (Kong's own managed/hosted control plane) — a JD may
  reference any of the three.
- **Two ways to configure it**: declarative config (a `kong.yml` file
  — the GitOps-friendly, version-controllable approach) vs. the Admin
  API (imperative REST calls that configure Kong itself at runtime).
- **DB-less mode**: Kong can run without its own Postgres/Cassandra
  backing store, reading all config from a YAML file instead — simpler
  operationally for smaller deployments.
- **Where it sits among alternatives**: AWS API Gateway (managed,
  AWS-native, less flexible), Apigee (enterprise-heavy, Google-owned),
  Envoy/Traefik (general-purpose proxies that *can* do gateway-like
  work but aren't API-gateway-first products the way Kong is).

## 1. "What does Kong actually add on top of a plain reverse proxy like nginx?"

**Answer:**

- Nginx routes and proxies requests — nothing more.
- Kong does that, plus a plugin architecture for cross-cutting
  concerns — authentication, rate limiting, request/response
  transformation, logging — configured declaratively per route or
  service, with no custom proxy code to write.
- Kong is itself built on nginx/OpenResty, so it's not a replacement
  for understanding nginx — it's a management/plugin layer on top of
  it, aimed specifically at API traffic.

**Where this actually shows up:** a team choosing Kong over "just
nginx" is usually choosing it *because* they need several of auth,
rate limiting, and multi-tenant routing together, declaratively
configured, rather than hand-rolling each one in nginx config or
application middleware.

## 2. "How would you implement API key authentication and per-tenant rate limiting in Kong?"

```yaml
# kong.yml -- declarative config
services:
  - name: orders-service
    url: http://orders-backend:8000
    routes:
      - name: orders-route
        paths: ["/api/v1/orders"]
    plugins:
      - name: key-auth
        config:
          key_names: ["apikey"]
      - name: rate-limiting
        config:
          minute: 100
          policy: redis
          redis_host: redis
```

**Answer:**

- The `key-auth` plugin validates an API key on the request **before**
  it ever reaches the backend — the service never sees an
  unauthenticated request at all.
- `rate-limiting` with `policy: redis` shares the rate-limit counter
  across every Kong node, not just the one that happened to handle
  this particular request.
- That sharing matters the moment there's more than one Kong instance
  — an in-memory-only policy would let each node enforce its own
  separate limit, which effectively multiplies the real limit by the
  number of nodes.

**Likely follow-up — "how do you scope the rate limit per tenant, not
globally?"**

- Kong's **consumers** map each API key to an identity.
- A per-consumer rate-limiting config (instead of per-route) applies
  the limit individually to each authenticated tenant, instead of one
  shared bucket for everyone hitting the route.

## 3. "What's the practical difference between doing auth/rate-limiting at the gateway vs. in each service?"

**Answer:**

- **Centralizing at the gateway:** every service gets the same
  enforcement without reimplementing it, and a policy change (a new
  rate limit, revoking a key) takes effect in one place instead of a
  redeploy of every affected service.
- **The trade-off:** the gateway becomes a single place every request
  now depends on, and anything it can't see — business-logic-level
  authorization, not just "is this a valid key" — still has to live in
  the service itself.

| Pros | Cons / Trade-offs |
|---|---|
| Declarative plugin config instead of custom proxy/middleware code per service | Another piece of infrastructure to run, monitor, and keep available |
| Consistent auth/rate-limiting enforcement across every service behind it | Distributed policy (Redis-backed) adds a dependency the gateway itself now relies on |
| Plugin ecosystem covers most cross-cutting concerns out of the box | Business-level authorization still belongs in the service — the gateway only sees "valid key or not" |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Kong declarative-config example added under `code_samples/`.
