---
title: "CloudFront: Content Delivery & Edge Caching"
---

# CloudFront: Content Delivery & Edge Caching

CloudFront shows up constantly elsewhere in this project as a detail —
[WAF attaches to it](aws-security-and-compliance-services.md#waf-web-application-firewall),
[ACM certs for it must be in `us-east-1`](load-balancing-and-dns.md#tls-termination-with-acm),
a deployment can invalidate its cache — without ever being explained on
its own. This page is that explanation.

## What It Actually Does

CloudFront is AWS's CDN: a global network of edge locations that cache
content close to the end user, so a request from Dhaka doesn't have to
round-trip to an origin server in `us-east-1` every time.

- First request for an object at a given edge location: a cache
  **miss** — CloudFront fetches it from the origin, serves it, and
  caches a copy at that edge location.
- Every subsequent request from a nearby user: a cache **hit** — served
  straight from the edge, no trip back to the origin at all.
- This cuts both **latency** (physically closer server) and **origin
  load** (the origin only sees cache misses, not every request).

## Origins: What CloudFront Fetches From

`S3 bucket`
:   The classic case — static assets, a single-page app's build output.
    Use **Origin Access Control (OAC)** so the bucket stays fully
    private and only CloudFront can read from it — the bucket itself
    should never be publicly readable.

`ALB / custom origin (any HTTP server)`
:   CloudFront in front of dynamic content too — an ALB, or any
    origin server reachable over HTTP(S). Lets you cache cacheable
    responses while still letting genuinely dynamic requests reach the
    actual application.

One distribution can route to **multiple origins** based on path pattern
— `/api/*` to the ALB, everything else to the S3 bucket holding the
frontend build, both behind the same domain and the same certificate.

## Cache Behaviors: Controlling What Gets Cached, and for How Long

A **cache behavior** is a path-pattern rule (`/images/*`, `/api/*`,
default `*`) that decides, for requests matching it:

- Which origin to route to.
- Whether to forward query strings, headers, and cookies to the origin
  — forwarding more means more cache misses (each unique combination is
  cached separately), forwarding less means a simpler, more effective
  cache but risks serving the wrong cached response to the wrong user.
- TTL — how long an object is served from cache before CloudFront checks
  the origin again, the same latency-vs-freshness trade-off already
  covered for
  [Route 53 TTLs](load-balancing-and-dns.md#ttl-the-trade-off-youre-actually-making).

## Invalidating a Cache

Deploying a new version of a static asset under the *same* path doesn't
automatically reach users already holding a cached copy — an
invalidation request tells CloudFront to stop serving the cached version
immediately.

``` bash
aws cloudfront create-invalidation \
  --distribution-id E1234EXAMPLE \
  --paths "/*"
```

!!! note "The cheaper alternative most pipelines actually use"

    Invalidation requests cost money past a free monthly allowance, and
    take time to propagate to every edge location. The common production
    pattern instead: give every build a unique path (a content hash or
    version in the filename, e.g. `app.a1b2c3.js`), so a new deploy is
    simply a *new* object CloudFront has never cached, served instantly
    with no invalidation needed at all — only `index.html` itself
    (which references the hashed filenames) needs a short TTL or an
    invalidation on deploy.

## Signed URLs & Signed Cookies — Restricting Access

For content that shouldn't be freely downloadable (paid video, private
documents) without exposing the origin publicly:

- **Signed URL** — a single URL with an expiry and a signature baked
  in, works for one object at a time. Good for a single file link sent
  to one user.
- **Signed Cookie** — the signature lives in a cookie instead, so it
  applies to every request matching a path pattern without rewriting
  every URL. Good for granting access to a whole section of a site (an
  entire video course) after a single sign-in.

!!! success "The exam signal"

    "Restrict access to premium content for authenticated users,
    multiple files" → signed cookies. "Share a single file with a
    time-limited link" → signed URL, or the equivalent
    [S3 presigned URL](load-balancing-and-dns.md) if CloudFront isn't
    already in front of that bucket.
