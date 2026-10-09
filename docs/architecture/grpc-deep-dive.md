---
title: "gRPC Deep Dive"
---

# gRPC Deep Dive

An increasingly common standalone interview topic now, not just one
row in [API Paradigms & Patterns' comparison table](api-paradigms-and-patterns.md#quick-reference)
— split out here once it outgrew being one section among seven.

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

## 1. Protocol Buffers: The Wire Format Underneath Everything

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

**Answer:**

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

## 2. The Four RPC Types

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
  [API Paradigms & Patterns §5](api-paradigms-and-patterns.md#5-websocket)
  for that comparison.

## 3. Why HTTP/2 Is Load-Bearing, Not Incidental

**Answer:**

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

## 4. The Gotcha: Load Balancing gRPC

**"Why is load balancing gRPC harder than load balancing a REST API?"**

**Answer:**

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

## 5. Deadlines, Cancellation, and Status Codes

**Answer:**

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

## 6. Interceptors — gRPC's Middleware

**Answer:**

- Client-side and server-side **interceptors** wrap every call for
  cross-cutting concerns — auth token injection, logging, distributed
  tracing, automatic retries — the same structural role as
  Express/Django middleware, just operating at the RPC layer instead
  of the HTTP-request layer.
- A server interceptor is the natural place to enforce things like
  authentication uniformly across every RPC method without repeating
  the check in each handler — the RPC-layer equivalent of
  [DRF's permission classes](../backend/python/django-drf.md#4-authentication-permissions).

## 7. When *Not* to Reach for gRPC

**Answer:**

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

## Interview Questions You're Likely to Get Asked

- "What's the difference between gRPC and REST?" — the Protobuf-vs-JSON
  and HTTP/2-vs-HTTP/1.1 basics at the top of this page.
- "Walk me through the four RPC types and when you'd use each." — §2.
- "Why can't you just reuse a Protobuf field number after removing a
  field?" — §1's schema-evolution rules.
- "Why is load balancing gRPC traffic harder than balancing REST
  traffic?" — §4, the connection-level vs. stream-level distinction.
- "How does gRPC handle a client that's no longer waiting for a
  response?" — §5's deadline propagation and cancellation.
- "Where would gRPC be the wrong choice?" — §7; name the public-API and
  browser-client cases specifically, not just "when it doesn't fit."

---

## Code Samples

No dedicated code samples yet for this section — the `.proto`
snippets above are enough to try directly with `protoc` and the gRPC
plugin for your language of choice.
