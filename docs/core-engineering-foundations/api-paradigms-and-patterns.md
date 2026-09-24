---
title: API Paradigms & Patterns
---

# API Paradigms & Patterns

Every major API style, what it's actually for, and its real trade-offs
— the comparison knowledge interviewers use to check you understand
*why* REST is the default, not just how to build one, and that you know
when it *isn't* the right choice.

## 1. REST

```
GET /api/v1/orders/{order_id}
POST /api/v1/orders
```

**What it is:** Resources (nouns) manipulated via standard HTTP verbs
(`GET`/`POST`/`PUT`/`PATCH`/`DELETE`), JSON payloads, stateless
requests. The default choice for most public and internal HTTP APIs
today.

**Benefits:** Ubiquitous tooling (every language, every HTTP client);
cacheable by default via standard HTTP semantics (`ETag`, `Cache-Control`);
human-readable and easy to debug with just `curl`; stateless, so any
server can handle any request — trivially horizontally scalable.

**Best for:** Public APIs, CRUD-heavy applications, anything that
benefits from HTTP caching, and any team that wants the widest possible
client compatibility with the least specialized tooling.

| Pros | Cons / Trade-offs |
|---|---|
| Simple mental model, huge ecosystem, cacheable | Over-fetching/under-fetching — a client often gets more or less than it needs |
| Stateless — easy to scale horizontally | Multiple round trips for related resources (N+1 at the API level) |
| Human-debuggable with just a browser or `curl` | No built-in schema/contract — API docs (OpenAPI) are a separate, often-stale artifact |

## 2. SOAP

```xml
<soap:Envelope>
  <soap:Body>
    <GetOrderRequest xmlns="http://example.com/orders">
      <OrderId>12345</OrderId>
    </GetOrderRequest>
  </soap:Body>
</soap:Envelope>
```

**What it is:** XML-based messaging protocol with a rigid, formally
defined contract (WSDL — Web Services Description Language). Predates
REST's dominance; still very much alive in enterprise, banking,
healthcare (see HL7-era interfaces), and government systems with
long-lived, heavily-regulated integrations.

**Benefits:** WSDL provides a strict, machine-verifiable contract —
client code can often be generated automatically from it. Built-in
standards for security (WS-Security), transactions (WS-AtomicTransaction),
and reliable messaging that predate anything REST offers natively. Works
over transports other than HTTP (SMTP, message queues), not just the
web.

**Best for:** Enterprise integrations with strict contractual and
compliance requirements (financial transactions, healthcare data
exchange, government systems), especially where the integration
predates REST's dominance and replacing it isn't worth the risk.

| Pros | Cons / Trade-offs |
|---|---|
| Rigid, machine-verifiable contract (WSDL) — hard to integrate incorrectly | Verbose XML payloads — much larger than equivalent JSON |
| Mature standards for security/transactions/reliable delivery | Steep learning curve, heavier tooling, slower to iterate on |
| Transport-agnostic (HTTP, SMTP, message queues) | Rarely the right choice for a *new* API today — mentioned mainly for legacy-system interviews |

## 3. GraphQL

```graphql
query {
  order(id: "12345") {
    total
    customer { name }
  }
}
```

**What it is:** A query language where the client specifies exactly
which fields it needs, across potentially multiple resources, in one
request — the server exposes one endpoint and a schema, not many
resource-specific URLs.

**Benefits:** Solves REST's over/under-fetching directly — a mobile
client and a desktop client can request different fields from the same
query without needing separate endpoints. One round trip for data that
would take several nested REST calls. The schema is a real,
enforced contract (unlike REST's optional OpenAPI docs).

**Best for:** Mobile/SPA clients with varied, evolving data needs, and
APIs serving multiple frontends with different data shapes from the
same backend.

| Pros | Cons / Trade-offs |
|---|---|
| Client gets exactly the fields it needs, one request | Much harder to cache at the HTTP layer — every query can be shaped differently |
| Strongly-typed schema is a real, enforced contract | A naive resolver can hide an N+1 query problem behind one deceptively simple query |
| Great for aggregating multiple backend resources for a UI | More backend complexity — resolvers, schema stitching, query cost/depth limiting |

## 4. gRPC

```protobuf
service OrderService {
  rpc GetOrder (OrderRequest) returns (OrderResponse);
}
```

**What it is:** RPC framework using Protocol Buffers (a compact binary
format) over HTTP/2, with native support for streaming (client, server,
or bidirectional). Contracts are defined in `.proto` files, and client/
server code is generated from them.

**Benefits:** Protobuf is far more compact and faster to
serialize/deserialize than JSON. HTTP/2 gives multiplexing (many calls
over one connection) and native streaming. The generated client/server
code eliminates a whole class of "the client sent the wrong shape" bugs.

**Best for:** Internal service-to-service communication in a
microservices architecture, especially where latency and throughput
matter and every service is under your own control (both ends need
Protobuf/gRPC support, which makes it a poor fit for public APIs
consumed by arbitrary third parties).

| Pros | Cons / Trade-offs |
|---|---|
| Fast, compact binary payloads; native streaming | Not human-readable — needs tooling (`grpcurl`) to debug, unlike REST + `curl` |
| Generated client/server code from one `.proto` contract | Browser support is limited/awkward without a proxy (grpc-web) |
| HTTP/2 multiplexing — many calls over one connection | Poor fit for public APIs — third parties would need gRPC tooling too |

## 5. WebSocket

```python
async def handler(websocket):
    async for message in websocket:
        await websocket.send(f"echo: {message}")
```

**What it is:** A persistent, full-duplex connection over a single TCP
socket — either side can push a message at any time, without the
request/response cycle HTTP normally requires.

**Benefits:** True bidirectional, low-latency communication — the
server can push to the client without the client asking first, and the
client can send without waiting for a prior response to resolve. One
connection stays open, avoiding the overhead of repeated HTTP
handshakes for frequent updates.

**Best for:** Chat applications, live collaborative editing,
multiplayer/real-time features, live trading/pricing dashboards —
anything needing frequent, low-latency updates in *both* directions.

| Pros | Cons / Trade-offs |
|---|---|
| True bidirectional push — no polling overhead | Stateful connection — load balancing and horizontal scaling need sticky sessions or a shared pub/sub backend |
| Low latency once connected — no per-message HTTP overhead | Doesn't fit standard HTTP caching/CDN infrastructure at all |
| One connection handles many message types | More complex reconnection/backoff logic needed on the client for a reliable experience |

## 6. Server-Sent Events (SSE)

```python
async def stream_events():
    yield "data: {\"progress\": 42}\n\n"
```

**What it is:** A lightweight, one-way (server → client) streaming
protocol over plain HTTP — the server keeps a response open and pushes
events as they happen; the client listens via `EventSource` in a
browser.

**Benefits:** Much simpler than WebSocket when the client never needs
to push back — no special protocol upgrade, works over plain HTTP/1.1,
and browsers auto-reconnect on disconnect for free.

**Best for:** Live progress updates (a long-running job's status),
live notifications, streaming an LLM response token-by-token — anything
one-directional, server-to-client.

| Pros | Cons / Trade-offs |
|---|---|
| Simpler than WebSocket — plain HTTP, no special protocol upgrade | One-directional only — no client-to-server push on the same connection |
| Built-in browser reconnection via `EventSource` | Older HTTP/1.1 connection limits per domain can matter at scale |
| Easier to load-balance than WebSocket in many setups | Less broadly supported outside browsers than plain HTTP |

## 7. Webhooks vs. Polling

Webhooks push events to the consumer instead of the consumer repeatedly
asking "anything new?" — right for real-time notifications and
async-workflow integrations, wrong for consumers behind a firewall that
can't receive inbound requests, or for ultra-high-volume low-value
events where the overhead of a webhook per event isn't worth it.
Basics: a subscription URL to register, retries with backoff on
delivery failure, signature verification so the consumer can trust the
payload actually came from you, and a small payload + follow-up fetch
for anything large rather than pushing the full object every time.

| Pros | Cons / Trade-offs |
|---|---|
| No polling waste — the consumer only does work when something happened | Consumer must expose a reachable public endpoint |
| Near-real-time delivery | Delivery isn't guaranteed by default — needs retries, and the consumer must handle duplicates |
| Decouples producer from needing to know when a consumer wants updates | Debugging is harder — failures happen async, out of band from any request the consumer made |

---

## Quick Reference

| | REST | SOAP | GraphQL | gRPC | WebSocket | SSE |
|---|---|---|---|---|---|---|
| Payload | JSON | XML | JSON | Protobuf | Any | Text (`data:` events) |
| Direction | Request/response | Request/response | Request/response | Request/response + streaming | Bidirectional | Server → client only |
| Best fit | Public APIs, CRUD | Legacy enterprise integration | Multi-shape client needs | Internal service-to-service | Real-time bidirectional | Server-push updates |
| Human-debuggable | Yes (`curl`) | Somewhat (verbose XML) | Yes (GraphiQL/Playground) | No (needs `grpcurl`) | Needs a client tool | Yes (`curl`/`EventSource`) |
