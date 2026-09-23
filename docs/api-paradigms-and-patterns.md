---
title: API Paradigms & Patterns
---

# API Paradigms & Patterns

REST vs. alternatives, and push vs. pull for event delivery — the
comparison questions interviewers use to check you understand *why*
REST is the default, not just how to build one.

## REST vs. GraphQL vs. gRPC

| | REST | GraphQL | gRPC |
|---|---|---|---|
| Paradigm | Resource-oriented | Query-based | Service/RPC-oriented |
| Data fetching | Over/under-fetching risk; multiple round trips | Client specifies exact fields, one request | Strong contracts, less flexible ad-hoc queries |
| Payload | JSON | JSON | Protobuf (compact binary) |
| Transport | HTTP/1.1 | HTTP/1.1 | HTTP/2 (streaming, multiplexing) |
| Best fit | Public APIs, cacheable CRUD | Mobile/SPA clients needing tailored data | Internal high-performance service-to-service |

## Webhooks vs. Polling

Webhooks push events to the consumer instead of the consumer repeatedly
asking "anything new?" — right for real-time notifications and
async-workflow integrations, wrong for consumers behind a firewall that
can't receive inbound requests, or for ultra-high-volume low-value
events where the overhead of a webhook per event isn't worth it.
Basics: a subscription URL to register, retries with backoff on
delivery failure, signature verification so the consumer can trust the
payload actually came from you, and a small payload + follow-up fetch
for anything large rather than pushing the full object every time.
