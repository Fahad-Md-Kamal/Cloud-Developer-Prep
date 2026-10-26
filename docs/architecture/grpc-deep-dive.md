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

**What it is:** an RPC (Remote Procedure Call) framework using Protocol
Buffers (a compact binary format) over HTTP/2, with native support for
streaming (client, server, or bidirectional). Contracts are defined in
`.proto` files, and client/server code is generated from them.

**Benefits:** Protobuf is far more compact and faster to
serialize/deserialize than JSON. HTTP/2 gives multiplexing (many calls
over one connection) and native streaming. The generated client/server
code eliminates a whole class of "the client sent the wrong shape" bugs.

**Best for:** Internal service-to-service communication in a
microservices architecture, especially where latency and throughput
matter and every service is under your own control (both ends need
Protobuf/gRPC support, which makes it a poor fit for public APIs
consumed by arbitrary third parties).

## RPC vs. REST: Two Different Mental Models

<svg viewBox="0 0 900 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Static diagram comparing RPC and REST: RPC calls a named procedure like GetOrder, with each operation as its own distinct function; REST sends a small fixed set of HTTP verbs to a URL representing a resource, with the same verbs reused across every resource" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="440" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<text x="225" y="26" font-size="18" font-weight="600" text-anchor="middle" fill="#2b313b">RPC</text>
<text x="675" y="26" font-size="18" font-weight="600" text-anchor="middle" fill="#2b313b">REST</text>
<line x1="450" y1="38" x2="450" y2="420" stroke="#9aa5b3" stroke-width="2" stroke-dasharray="5,5"></line>
<rect x="145" y="50" width="160" height="50" rx="6" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="225" y="80" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">Client</text>
<line x1="225" y1="100" x2="225" y2="148" stroke="#9aa5b3" stroke-width="2"></line>
<text x="225" y="130" font-size="12" text-anchor="middle" fill="#5b6472">GetOrder(orderId=123)</text>
<rect x="145" y="150" width="160" height="50" rx="6" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<text x="225" y="172" font-size="13" font-weight="600" text-anchor="middle" fill="#1d4a78">Server</text>
<text x="225" y="190" font-size="10" text-anchor="middle" fill="#1d4a78">runs the matching procedure</text>
<text x="225" y="230" font-size="11" font-weight="600" text-anchor="middle" fill="#2b313b">Also exposed, as separate named calls:</text>
<text x="225" y="250" font-size="11" text-anchor="middle" fill="#5b6472">CreateOrder(...)</text>
<text x="225" y="268" font-size="11" text-anchor="middle" fill="#5b6472">CancelOrder(orderId)</text>
<text x="225" y="286" font-size="11" text-anchor="middle" fill="#5b6472">ListOrders(customerId)</text>
<text x="225" y="325" font-size="12" text-anchor="middle" fill="#1f2a3a">Each operation is its own named</text>
<text x="225" y="343" font-size="12" text-anchor="middle" fill="#1f2a3a">procedure — the verb is the function name.</text>
<rect x="595" y="50" width="160" height="50" rx="6" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="675" y="80" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">Client</text>
<line x1="675" y1="100" x2="675" y2="148" stroke="#9aa5b3" stroke-width="2"></line>
<text x="675" y="130" font-size="12" text-anchor="middle" fill="#5b6472">GET /orders/123</text>
<rect x="595" y="150" width="160" height="50" rx="6" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<text x="675" y="172" font-size="13" font-weight="600" text-anchor="middle" fill="#1d4a78">Server</text>
<text x="675" y="190" font-size="10" text-anchor="middle" fill="#1d4a78">interprets the verb on the resource</text>
<text x="675" y="230" font-size="11" font-weight="600" text-anchor="middle" fill="#2b313b">Same fixed verbs, every resource:</text>
<text x="675" y="250" font-size="11" text-anchor="middle" fill="#5b6472">POST /orders</text>
<text x="675" y="268" font-size="11" text-anchor="middle" fill="#5b6472">PUT /orders/123</text>
<text x="675" y="286" font-size="11" text-anchor="middle" fill="#5b6472">DELETE /orders/123</text>
<text x="675" y="325" font-size="12" text-anchor="middle" fill="#1f2a3a">A small, fixed set of verbs, applied</text>
<text x="675" y="343" font-size="12" text-anchor="middle" fill="#1f2a3a">uniformly to any resource URL.</text>
<text x="450" y="400" font-size="13" text-anchor="middle" fill="#5b6472">RPC: many named operations, each its own call.  REST: few fixed verbs, reused across every resource.</text>
</svg>

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
  [Schema Evolution for Long-Lived Event Streams](../distributed-systems/messaging-kafka-redis-and-aws.md#2-schema-evolution-for-long-lived-event-streams),
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
  [DRF's permission classes](../python/django-drf.md#4-authentication-permissions).

## 7. Channels: The Connection Management Abstraction

**Answer:**

- A gRPC **channel** is the client-side abstraction representing a
  connection to a server — not necessarily one single raw TCP/HTTP2
  connection, one-to-one; the channel is what actually manages
  connection setup, reconnection, and (depending on configuration)
  which real backend address a given call goes out on.
- This is the object §4's "client-side load balancing" was actually
  referring to — a channel can be configured with a **resolver** (how
  to discover candidate backend addresses — DNS, or a service-discovery
  mechanism like xDS) and a **load-balancing policy** (round-robin,
  pick-first) that decides which resolved address each new call
  actually uses.
- Channels are meant to be created once and reused for the life of an
  application, not created fresh per call — creating one has real setup
  cost (connection establishment, a TLS handshake if applicable), and
  reusing a single channel across many calls is exactly what lets
  HTTP/2 multiplexing (§3) do its job at all.

## 8. Security: TLS and Authentication

**Answer:**

- gRPC distinguishes two separate kinds of credentials, worth naming
  precisely: **channel credentials** secure the transport itself (TLS
  — applied once, per channel), and **call credentials** authenticate
  an individual *request* (a bearer token, an API key), attached as
  metadata on each call, independent of whether the transport itself
  is encrypted.
- In production, gRPC channels run over TLS essentially by default —
  an *insecure* channel is explicitly named "insecure" in most client
  libraries specifically because it's the exception being opted into,
  the opposite convention from plain HTTP, where unencrypted was
  historically the unmarked default.
- Call-level auth tokens travel as **gRPC metadata** — functionally
  HTTP/2 headers, exposed through gRPC's own metadata API rather than
  raw header manipulation — read and validated by a
  [server interceptor](#6-interceptors-grpcs-middleware) uniformly
  across every RPC, the same pattern already covered there.
- **mTLS (mutual TLS)** — both client and server present certificates,
  each verifying the other's identity — is common specifically for
  internal service-to-service gRPC traffic inside a zero-trust mesh
  (Istio/Envoy, already named in §4), where "which service is actually
  calling me" needs to be cryptographically verified, not assumed from
  network location alone.

## 9. Server Reflection — Debugging Without a Local .proto File

**Answer:**

- [§13](#13-when-not-to-reach-for-grpc) names the real debuggability
  trade-off: gRPC isn't `curl`-able the way REST is, because a client
  normally needs the `.proto` contract in hand to know how to
  construct a call at all.
- **Server reflection** is gRPC's own answer to part of that gap: a
  service can expose a reflection API
  (`grpc.reflection.v1.ServerReflection`) letting a client discover its
  available methods and message shapes **at runtime**, without the
  `.proto` file being distributed to it in advance.
- This is exactly what lets `grpcurl` and Postman's gRPC support call
  an unfamiliar gRPC service interactively, the same way `curl` can hit
  a REST endpoint without the caller holding OpenAPI docs first —
  reflection doesn't make gRPC as universally debuggable as REST+JSON,
  but it closes a real, practical chunk of that gap for ad hoc
  debugging and exploration.

## 10. Retries and the Service Config

**Answer:**

- gRPC supports **declarative, built-in retry policies**, configured
  per method through a **service config** (JSON, supplied by the client
  or resolved alongside the server address) — specifying which status
  codes are retryable, how many attempts, and backoff parameters,
  without the application hand-writing its own retry loop.
- This matters specifically because of the same
  [status-code specificity already covered in §5](#5-deadlines-cancellation-and-status-codes) —
  only some codes (`UNAVAILABLE`, for instance) represent a genuinely
  transient condition worth retrying; retrying `INVALID_ARGUMENT` or
  `PERMISSION_DENIED` just repeats a failure that will never succeed —
  the identical reasoning behind
  [error-type-specific retry logic](../ai-llm/llm-apis-and-providers.md#7-walk-through-error-handling-and-retry-strategy-for-an-llm-api-call-whats-different-from-a-typical-rest-api-retry)
  already established elsewhere on this site.
- This is a narrower, protocol-level tool than a full
  [circuit breaker](../distributed-systems/circuit-breakers-retries-and-bulkheads.md#2-how-does-a-circuit-breaker-interact-with-retries-and-timeouts-what-breaks-if-you-get-the-order-wrong) —
  gRPC's retry policy decides "should this one call be retried," not
  "should we stop sending calls to a service that's clearly down
  entirely." A production system typically layers both: gRPC's retry
  policy for the fast, local decision, a circuit breaker for the
  broader one.

## 11. Health Checking: The grpc.health.v1 Protocol

**Answer:**

- gRPC defines a standard **health-checking protocol**
  (`grpc.health.v1.Health`) — a well-known RPC service any gRPC server
  can implement, letting a load balancer or orchestrator query a
  specific service's health by name over the same gRPC channel,
  instead of needing a separate plain-HTTP health endpoint bolted on
  alongside it.
- This matters concretely in Kubernetes: a gRPC-aware readiness/
  liveness probe calls this standard health service directly (using
  `grpc_health_probe` as the actual probe binary, since kubelet's
  native HTTP probes don't speak gRPC) instead of requiring every gRPC
  service to additionally expose and maintain a separate HTTP endpoint
  just to be probed.
- This is the gRPC-specific version of the general
  [health check](../cloud-devops/load-balancing-and-dns.md#health-checks-debugging-guide)
  concept already covered elsewhere on this site — same purpose,
  implemented as a real gRPC call instead of an HTTP one.

## 12. Protobuf Beyond Basic Messages: oneof, Maps & Well-Known Types

**Answer:**

- **`oneof`** — declares a set of fields where **at most one** can
  actually be set at a time, encoding a genuine "exactly one of these
  alternatives" relationship directly in the schema, rather than
  leaving it as an unenforced convention.
- **`map<K, V>`** — a native map type, instead of hand-rolling a
  repeated key-value message pair to represent the same thing.
- **Well-known types** — standard, pre-defined messages shipped with
  Protobuf itself for extremely common cases: `google.protobuf.Timestamp`
  (instead of every team inventing its own timestamp representation),
  `Duration`, `Empty` (a genuinely empty message, for an RPC that takes
  or returns nothing meaningful), and `Any` (a field that can hold an
  arbitrary, dynamically-typed message, resolved by a type URL carried
  alongside the data — the explicit, opt-in escape hatch for the
  dynamic flexibility Protobuf's static schema otherwise deliberately
  doesn't allow).
- **Tooling note**: modern teams increasingly manage `.proto` files
  with **buf** rather than raw `protoc` directly — it adds linting and,
  notably, **breaking-change detection** that mechanically enforces the
  exact
  [field-number/schema-evolution rules already covered in §1](#1-protocol-buffers-the-wire-format-underneath-everything) —
  turning "never reuse a field number" from a rule a reviewer has to
  remember into one a CI check actually catches.

## 13. When *Not* to Reach for gRPC

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
| TLS essentially on by default, with mTLS a natural fit for service meshes | One more credential layer (channel vs. call credentials) to get right |
| Built-in retry policies and standard health checking need no custom code | Both are still narrower tools than a full circuit breaker or app-level health logic |
| Server reflection makes ad hoc debugging genuinely possible without a local `.proto` | Still not as universally accessible as a self-describing REST+OpenAPI endpoint |

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
- "What's a gRPC channel, and how is it different from a single HTTP/2
  connection?" — §7.
- "How does gRPC actually handle authentication — walk through channel
  vs. call credentials." — §8.
- "How would you debug a gRPC service you don't have the `.proto` for?"
  — §9's server reflection.
- "Does gRPC have built-in retries, or do you have to write your own?"
  — §10's service config, and how it relates to a circuit breaker.
- "How does Kubernetes health-check a gRPC service, given its probes
  speak HTTP?" — §11's `grpc.health.v1` protocol and `grpc_health_probe`.
- "Where would gRPC be the wrong choice?" — §13; name the public-API and
  browser-client cases specifically, not just "when it doesn't fit."

---

## Code Samples

No dedicated code samples yet for this section — the `.proto`
snippets above are enough to try directly with `protoc` and the gRPC
plugin for your language of choice.
