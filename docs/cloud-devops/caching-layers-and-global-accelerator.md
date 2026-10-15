---
title: "Caching Layers & Global Accelerator"
---

# Caching Layers & Global Accelerator

This project already covers three of the four caching layers the exam
asks about in depth — this page fills the fourth (API Gateway caching),
adds Global Accelerator, and ties all four together with the one
question the exam actually cares about: **which layer is this cache
actually sitting in front of.**

## The Four Caching Layers, at a Glance

| Layer | Caches | Covered in |
|---|---|---|
| CloudFront | Static/dynamic HTTP responses, at edge locations near the user | [CloudFront: Content Delivery & Edge Caching](cloudfront-cdn.md) |
| API Gateway caching | A specific API's responses, keyed by endpoint + parameters | Below |
| ElastiCache | Arbitrary application data (sessions, query results, leaderboards) | [ElastiCache: Redis vs Memcached](dynamodb-and-elasticache.md#elasticache-redis-vs-memcached) |
| DAX | DynamoDB reads specifically | [DAX — DynamoDB Accelerator](dynamodb-and-elasticache.md#dax-dynamodb-accelerator) |

- Moving **down** this table moves the cache **closer to the actual data
  source** and **narrower in scope** — CloudFront caches whole HTTP
  responses globally, DAX caches only DynamoDB item/query results,
  right next to DynamoDB itself.
- A real production stack often runs more than one of these
  simultaneously, each solving a different hop: CloudFront in front of
  the whole app, DAX in front of just the DynamoDB calls a Lambda
  function makes.

## API Gateway Caching

Caches a REST API's responses directly in API Gateway, keyed by endpoint
path and request parameters — so an identical request within the TTL
window never reaches the backend integration (Lambda, HTTP endpoint) at
all.

- Enabled per **stage**, with a configurable TTL (up to 1 hour) and
  cache size (0.5 GB – 237 GB).
- Can be **encrypted** at rest, and can require specific cache keys
  (e.g. caching per-user by including an auth header in the cache key)
  so one user's cached response is never served to another.
- Only available for **REST APIs**, not HTTP APIs — a real, frequently
  tested limitation. An HTTP API (cheaper, lower-latency, fewer
  features) needs caching built another way — typically CloudFront in
  front of it, or caching inside the Lambda function itself.

!!! success "The exam signal"

    "Reduce load on the backend for an API with repeated identical
    requests" → API Gateway caching, *if* it's a REST API. "Same
    requirement, but it's an HTTP API" → the trick is that built-in
    caching isn't available there at all — reach for CloudFront instead.

## Global Accelerator

Improves performance for **non-HTTP, or genuinely global, TCP/UDP
traffic** by routing it onto AWS's own private global network backbone
as early as possible, instead of the public internet.

- Gives your application **static anycast IP addresses** that never
  change, even as you add or remove backend endpoints (ALBs, NLBs, EC2
  instances) behind them in different regions.
- Routes a user's traffic to the nearest healthy AWS edge location, then
  onto AWS's backbone for the rest of the trip — cutting the number of
  internet hops and jitter along the way.
- Automatic failover to a healthy region's endpoint if the primary
  region becomes unhealthy, without any DNS change or TTL to wait out.

!!! danger "Global Accelerator vs CloudFront — the exam's favorite pairing here"

    Both make an application faster for global users, but for different
    traffic: **CloudFront** is for **HTTP/HTTPS content that can be
    cached** (static assets, cacheable API responses). **Global
    Accelerator** is for **non-HTTP protocols** (gaming, VoIP, IoT) or
    for HTTP traffic that genuinely can't be cached but still benefits
    from a faster network path and **static IPs** — a requirement
    CloudFront doesn't need or provide, since it's accessed by domain
    name. A question mentioning "static IP addresses" or "non-HTTP/TCP
    traffic" points to Global Accelerator; "cache content at the edge"
    points to CloudFront.
