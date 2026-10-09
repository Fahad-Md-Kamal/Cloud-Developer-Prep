---
title: "GraphQL Deep Dive"
---

# GraphQL Deep Dive

The other paradigm that comes up as its own topic now, not just a row
in [API Paradigms & Patterns' comparison table](api-paradigms-and-patterns.md#quick-reference)
— split out here the same way [gRPC](grpc-deep-dive.md) was, once there
was enough real depth to cover.

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

## 1. The Schema: GraphQL's Actual Contract

```graphql
type Order {
  id: ID!
  total: Float!
  customer: Customer!
  items: [OrderItem!]!
}

type Query {
  order(id: ID!): Order
}

type Mutation {
  cancelOrder(id: ID!): Order!
}

type Subscription {
  orderStatusChanged(orderId: ID!): Order!
}
```

**Answer:**

- The schema (written in SDL — Schema Definition Language) is the
  real, enforced contract — every query is validated against it before
  execution, and a client can introspect the schema itself to discover
  exactly what's queryable, which is what powers tools like GraphiQL's
  autocomplete.
- `!` marks a field as non-nullable — `total: Float!` means the server
  guarantees a value is always present; a resolver that returns `null`
  for a non-nullable field is a server-side bug, not a valid response.
- Three root types partition everything: `Query` (reads), `Mutation`
  (writes), `Subscription` (real-time updates, §5). A field can only
  exist under one of these roots — there's no ambiguity about whether
  an operation reads or writes, unlike REST where that's a convention
  (`GET` vs. `POST`) rather than something the schema enforces.

## 2. Resolvers and the N+1 Problem

```javascript
// Naive resolver -- looks innocent, is actually an N+1 query generator
const resolvers = {
  Query: {
    orders: () => db.orders.findAll(), // 1 query
  },
  Order: {
    customer: (order) => db.customers.findById(order.customerId), // N queries, one per order!
  },
};
```

**Answer:**

- Each field in a query has its own **resolver** function — GraphQL
  executes a query by walking the selection set and calling the
  resolver for each field, independently, resolving nested fields
  after their parent resolves.
- **This is exactly how the N+1 problem hides inside a GraphQL
  query**: fetching 50 orders then each order's `customer` field naively
  fires 50 separate `customer` lookups — one per order — the identical
  failure mode as
  [Django ORM's N+1 problem](../backend/python/django-orm.md#1-query-loading-patterns),
  just triggered by GraphQL's per-field resolver model instead of lazy
  ORM attribute access.
- **The standard fix is a DataLoader** (batching + per-request
  caching): instead of each `customer` resolver hitting the DB
  immediately, it registers the needed ID and the loader batches all
  registered IDs from the same tick of the event loop into one query:

```javascript
const customerLoader = new DataLoader(async (ids) => {
  const customers = await db.customers.findByIds(ids); // ONE query for all 50
  return ids.map((id) => customers.find((c) => c.id === id));
});

const resolvers = {
  Order: {
    customer: (order) => customerLoader.load(order.customerId), // batched automatically
  },
};
```

- **Interview point**: "how do you solve N+1 in GraphQL?" is really
  asking whether you know DataLoader (or your language's equivalent
  batching utility) exists and why naive per-field resolvers are a
  trap — the same root cause as REST/ORM N+1, wearing a different
  costume.

## 3. Mutations: Writes Are Still Just Fields

```graphql
mutation {
  cancelOrder(id: "12345") {
    id
    status
  }
}
```

**Answer:**

- A mutation is a field under the `Mutation` root type — syntactically
  almost identical to a query, with one semantic difference: the GraphQL
  spec guarantees top-level mutation fields in one request execute
  **sequentially**, not in parallel, specifically so one mutation's
  side effects can be relied on to have completed before the next
  starts. Query fields have no such ordering guarantee and may execute
  in parallel.
- A mutation conventionally *returns* the mutated object (`id`,
  `status` above) so the client can update its local cache without a
  separate follow-up query — this is a convention the ecosystem
  settled on, not a spec requirement, but deviating from it (returning
  nothing, or an unrelated shape) breaks most client-side caching
  libraries' expectations.
- Idempotency is still the caller's problem to design for, same as
  REST — GraphQL's spec says nothing about retry-safety; a mutation
  that isn't naturally idempotent needs the same idempotency-key
  pattern as
  [an at-least-once message handler](../backend/messaging-kafka-redis-and-aws.md#3-aws-sqs-vs-kafka-and-how-to-actually-handle-duplicate-events)
  if it needs to tolerate retries safely.

## 4. Why GraphQL Is Hard to Cache at the HTTP Layer

**Answer:**

- REST's cacheability comes from the URL being the cache key — `GET
  /orders/123` is always the same request, so a CDN/browser can cache
  its response by URL. GraphQL sends every query (regardless of shape)
  to the *same* endpoint, typically via `POST` — there's no stable URL
  per distinct query for HTTP-level infrastructure to key a cache on.
- **The real fixes**:
    - **Persisted queries** — the client sends a hash/ID representing
      a pre-registered query instead of the full query text; the
      server looks it up by ID. This turns each distinct query back
      into something with a stable identifier, which can now be used
      as a cache key (and as a `GET` request, restoring HTTP caching).
    - **Client-side normalized caching** — Apollo Client/Relay
      maintain a client-side cache normalized by object ID (every
      `Order` with `id: "123"` is one cache entry, regardless of which
      query fetched it), so a later query needing the same object can
      be served from cache without a network round trip at all. This
      solves client-perceived caching, but is a completely different
      mechanism from HTTP/CDN caching — don't conflate the two when
      asked about GraphQL caching in an interview.

## 5. Subscriptions: Real-Time Over GraphQL

```graphql
subscription {
  orderStatusChanged(orderId: "12345") {
    status
  }
}
```

**Answer:**

- A subscription is a long-lived operation — the client opens it once
  and the server pushes a new payload every time the underlying event
  occurs, matching the field's selection set exactly like a query
  would.
- **The transport underneath is not part of the GraphQL spec itself**
  — subscriptions are commonly implemented over WebSocket (the
  `graphql-ws` protocol) or, increasingly, over
  [Server-Sent Events](api-paradigms-and-patterns.md#6-server-sent-events-sse)
  for the simpler one-directional case. GraphQL defines the *query
  shape and execution semantics*; it deliberately doesn't mandate a
  transport, unlike gRPC which is tightly coupled to HTTP/2.

## 6. Schema Evolution and Federation

**Answer:**

- **Versioning philosophy**: GraphQL APIs conventionally don't version
  via a URL (`/v1`, `/v2`) the way REST does — the schema evolves
  additively. A new field is simply added; an old field being retired
  is marked `@deprecated(reason: "...")` and kept functional until
  clients have migrated off it, rather than being removed behind a new
  version number. This mirrors
  [REST Deep Dive §3](rest-deep-dive.md#3-versioning)'s
  "prefer additive changes" guidance, just as GraphQL's default
  convention rather than one option among several.
- **Federation** (Apollo Federation, GraphQL Mesh) lets multiple
  services each own a piece of one logical schema — a `Products`
  service owns the `Product` type, an `Orders` service owns `Order`
  but can reference `Product` by ID, and a gateway stitches them into
  one schema the client queries. This is the GraphQL-specific answer
  to "how do you do this in a microservices architecture without one
  team owning a monolithic schema."

## 7. Security: Query Cost and Depth

```graphql
# A deliberately malicious deeply-nested query --
# cheap to send, expensive to execute
query {
  order(id: "1") {
    customer {
      orders {
        customer {
          orders { customer { orders { id } } }
        }
      }
    }
  }
}
```

**Answer:**

- Because a client controls the query's *shape*, a deeply nested or
  broad query can force the server to do disproportionate work for a
  small request payload — a denial-of-service vector that doesn't
  exist the same way in REST, where each endpoint's cost is fixed by
  what the server chose to implement.
- **The standard defenses**: query depth limiting (reject queries
  nested past N levels), query complexity/cost analysis (assign each
  field a cost, sum it, reject queries over a budget), and persisted
  queries (§4) as a side effect also eliminate this entirely for
  clients restricted to a pre-approved query allowlist.

## When *Not* to Reach for GraphQL

**Answer:**

- **Simple CRUD with one consumer and stable, known data needs** — the
  resolver/schema overhead buys nothing a plain REST endpoint doesn't
  already provide, and REST's HTTP-level cacheability is strictly
  easier to get for free.
- **Public APIs where HTTP caching/CDN behavior matters a lot** —
  without investing in persisted queries, GraphQL gives this up by
  default.
- **Teams without the operational maturity for query cost limiting** —
  an unprotected GraphQL endpoint is a more exploitable DoS surface
  than an equivalent REST API, per §7.

## Interview Questions You're Likely to Get Asked

- "How do you solve the N+1 problem in GraphQL?" — §2, name DataLoader
  specifically, not just "optimize the resolver."
- "Why is GraphQL harder to cache than REST?" — §4, the missing stable
  per-query URL, and the two different fixes (persisted queries vs.
  client-side normalized caching) for two different caching layers.
- "How do GraphQL mutations differ from queries?" — §3, the
  sequential-execution guarantee specifically.
- "How does GraphQL handle real-time updates?" — §5, and that the
  transport (WebSocket/SSE) isn't part of the spec itself.
- "How would you version a GraphQL API?" — §6, additive-by-convention
  plus `@deprecated`, not URL versioning.
- "What's a GraphQL-specific security concern REST doesn't really
  have?" — §7, query depth/cost as a DoS vector controlled by the
  client's query shape.

---

## Code Samples

No dedicated code samples yet for this section — the schema/resolver
snippets above are enough to try directly against a small
Apollo Server or `graphql-js` setup.
