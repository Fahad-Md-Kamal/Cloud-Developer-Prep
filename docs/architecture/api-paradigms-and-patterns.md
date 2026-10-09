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

An increasingly common standalone interview topic, not just one row in
the comparison table below — worth going deeper than the summary above.

### Protocol Buffers: The Wire Format Underneath Everything

```protobuf
syntax = "proto3";

message OrderRequest {
  string order_id = 1;   // the number is the FIELD TAG, not a default value
}

message OrderResponse {
  string order_id = 1;
  double total = 2;
  repeated string product_names = 3;
}
```

- Protobuf encodes each field as `(field_number, wire_type, value)` —
  a compact tag-length-value binary format. Field *names* never appear
  on the wire at all, which is a large part of why Protobuf payloads
  are so much smaller than the equivalent JSON — no repeated string
  keys, no whitespace, no quoting.
- **The field number is the actual contract, not the field name.**
  This drives Protobuf's schema-evolution rules directly:
    - Adding a new field with a new number is always safe — old
      clients simply don't recognize it and ignore it.
    - **Never reuse a field number**, even after removing a field — a
      retired number should be marked `reserved` so a future field
      can't accidentally reuse it and misinterpret old binary data
      under the new field's meaning.
    - Renaming a field is safe (the wire format never carried the
      name); changing a field's *number* or its *wire type* is a
      breaking change.
- This is the same additive-first discipline as
  [Schema Evolution for Long-Lived Event Streams](../backend/chapter-6.md#4-schema-evolution-for-long-lived-event-streams),
  applied to RPC contracts instead of Kafka events — the same lesson
  shows up at every layer that needs forward/backward compatibility.

### The Four RPC Types

```protobuf
service OrderService {
  rpc GetOrder (OrderRequest) returns (OrderResponse);                      // unary
  rpc ListOrders (ListRequest) returns (stream OrderResponse);              // server streaming
  rpc UploadOrders (stream OrderRequest) returns (UploadSummary);           // client streaming
  rpc TrackOrders (stream OrderRequest) returns (stream OrderResponse);     // bidirectional streaming
}
```

| RPC type | Shape | Real use case |
|---|---|---|
| Unary | 1 request → 1 response | A simple lookup — the direct REST-equivalent case |
| Server streaming | 1 request → N responses | Live status updates, a large result set streamed instead of paginated |
| Client streaming | N requests → 1 response | Batch upload acknowledged once at the end, not per-item |
| Bidirectional streaming | N requests ↔ N responses | Live chat, real-time tracking — genuinely concurrent in both directions |

- Bidirectional streaming is a capability REST cannot express
  structurally without bolting WebSockets on separately — see
  [§5](#5-websocket) below for that comparison.

### Why HTTP/2 Is Load-Bearing, Not Incidental

- **Multiplexing** — many concurrent RPCs share *one* TCP connection,
  each as an independent, interleaved stream. This removes the
  application-layer head-of-line blocking HTTP/1.1 had, where one slow
  request could block others queued behind it on the same connection.
- **Binary framing** — HTTP/2 itself is a binary protocol; this is
  part of why gRPC is built on HTTP/2 specifically rather than
  HTTP/1.1, which has no native framing concept to carry Protobuf
  messages efficiently.
- **Header compression (HPACK)** — repeated metadata (auth tokens,
  content-type) across many calls on the same connection is
  compressed incrementally instead of resent in full on every call.
- **Streaming only exists because of this** — the four RPC types above
  are possible specifically because HTTP/2 supports long-lived,
  bidirectional data frames on a single stream. gRPC's streaming model
  is HTTP/2's native streaming model with Protobuf framing on top, not
  a gRPC-specific invention.

### The Gotcha: Load Balancing gRPC

**"Why is load balancing gRPC harder than load balancing a REST API?"**

- A standard L4 (TCP-level) load balancer balances *connections*, not
  individual requests. Since gRPC multiplexes many RPCs over one
  long-lived HTTP/2 connection, an L4 balancer sees a single
  connection and routes *every* RPC on it to the *same* backend
  instance — one client with a busy, long-lived connection can pin a
  disproportionate amount of traffic to one instance while others sit
  idle, the opposite of what load balancing is supposed to achieve.
- **The fix is one of two approaches**:
    - **Client-side load balancing** — the client itself is aware of
      multiple backend addresses (commonly via a mechanism like
      client-side xDS) and distributes individual calls across them
      directly, rather than relying on a single connection to one
      load balancer.
    - **An L7 proxy that understands HTTP/2 framing** well enough to
      balance at the *individual stream* level instead of the
      connection level — Envoy is the standard choice here, which is
      also why gRPC and service meshes (Istio, built on Envoy) show up
      together so often in real architectures.
- **This is the single most common "wait, that's harder than it
  sounds" follow-up** once a candidate claims gRPC production
  experience — a strong answer names the actual mechanism (connection-
  level vs. stream-level balancing), not just "you need a good load
  balancer."

### Deadlines, Cancellation, and Status Codes

- gRPC has **first-class deadline propagation** — a client sets a
  deadline on a call, and that deadline travels with the call through
  every downstream hop. A service three calls deep can see "this
  caller only has 200ms left" and bail out early instead of doing
  work for a caller that will time out and discard the result anyway.
  REST has no protocol-level equivalent — any deadline behavior is
  bolted on per-application, if it exists at all.
- **Cancellation propagates automatically** — if a client cancels a
  streaming call, the server is notified and can stop producing data,
  rather than continuing work no one will read.
- gRPC has its own status code set (`OK`, `NOT_FOUND`,
  `DEADLINE_EXCEEDED`, `UNAVAILABLE`, `PERMISSION_DENIED`,
  `RESOURCE_EXHAUSTED`, and others) — richer and more RPC-specific than
  reusing HTTP status codes, since gRPC only borrows HTTP/2 for
  transport, not its status-code semantics.

### Interceptors — gRPC's Middleware

- Client-side and server-side **interceptors** wrap every call for
  cross-cutting concerns — auth token injection, logging, distributed
  tracing, automatic retries — the same structural role as
  Express/Django middleware, just operating at the RPC layer instead
  of the HTTP-request layer.
- A server interceptor is the natural place to enforce things like
  authentication uniformly across every RPC method without repeating
  the check in each handler — the RPC-layer equivalent of
  [DRF's permission classes](../backend/python/django-drf.md#4-authentication-permissions).

### When *Not* to Reach for gRPC

- **Public APIs for arbitrary third-party consumers** — they'd need
  gRPC tooling and access to your `.proto` contracts; REST+JSON's
  universal `curl`-ability wins for anything consumed outside your own
  organization.
- **Browser clients** — gRPC isn't natively callable from a browser;
  it needs `grpc-web` plus a translating proxy, unlike a REST endpoint
  a browser can `fetch()` directly.
- **Debuggability matters more than raw performance** — `grpcurl`
  exists, but it's not `curl`; a binary wire format that isn't
  human-readable has a real cost during incident debugging.

| Pros | Cons / Trade-offs |
|---|---|
| Fast, compact binary payloads; native streaming | Not human-readable — needs tooling (`grpcurl`) to debug, unlike REST + `curl` |
| Generated client/server code from one `.proto` contract | Browser support is limited/awkward without a proxy (grpc-web) |
| HTTP/2 multiplexing — many calls over one connection | Poor fit for public APIs — third parties would need gRPC tooling too |
| First-class deadline propagation and call cancellation | Load balancing requires stream-aware tooling (Envoy) or client-side balancing — a plain L4 balancer pins traffic to one backend |

**Interview Questions You're Likely to Get Asked**

- "What's the difference between gRPC and REST?" — the Protobuf-vs-JSON
  and HTTP/2-vs-HTTP/1.1 basics at the top of this section.
- "Walk me through the four RPC types and when you'd use each." — the
  table above.
- "Why can't you just reuse a Protobuf field number after removing a
  field?" — the schema-evolution rules above.
- "Why is load balancing gRPC traffic harder than balancing REST
  traffic?" — the connection-level vs. stream-level distinction above.
- "How does gRPC handle a client that's no longer waiting for a
  response?" — deadline propagation and cancellation above.
- "Where would gRPC be the wrong choice?" — name the public-API and
  browser-client cases specifically, not just "when it doesn't fit."

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
