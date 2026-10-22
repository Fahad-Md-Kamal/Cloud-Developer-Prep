---
title: "Event-Driven Architecture: CQRS & the Saga Pattern"
---

# Event-Driven Architecture: CQRS & the Saga Pattern

[Consistency & Consensus §2](../backend/consistency-and-consensus.md#2-eventual-consistency-in-practice-event-sourcing)
already covers event sourcing — an immutable event log as the source of
truth, with a read model replayed from it. This page covers the two
patterns that sit alongside it and get confused with it: CQRS (splitting
reads from writes) and the Saga pattern (a transaction that spans
multiple services, where no single database transaction can cover it).

## 1. "What is CQRS, and why split the read and write models at all?"

**Answer:**

- **CQRS (Command Query Responsibility Segregation)** means the model
  that handles **writes** (commands — "place this order") is a genuinely
  different model from the one that handles **reads** (queries — "show
  me this user's order history"), instead of one model serving both.
- The reason this earns its complexity: a single model trying to serve
  both jobs well tends to compromise both. A write model needs to
  enforce business rules and invariants correctly — that's its one job.
  A read model needs to answer the application's actual query shapes
  fast — which are often denormalized, aggregated, or joined in ways
  that would be awkward to enforce invariants against directly.
- Splitting them means each side can be optimized independently: the
  write side stays strict and simple (just enough structure to enforce
  correctness), while there can be *several* read models, each shaped
  for a specific screen or query pattern, updated asynchronously from
  the write side.

## 2. "Is CQRS the same thing as event sourcing — do you need both?"

**Answer:**

- No — they're independent decisions, commonly used together, but
  genuinely separable.
- **CQRS without event sourcing** is simpler: the write side is still
  just an ordinary mutable table enforcing business rules on update, and
  a separately maintained, denormalized read store is kept in sync
  (via a database trigger, an outbox pattern, or a change-data-capture
  stream) — no append-only event log required at all.
- **CQRS with event sourcing** is the fuller version: the write side
  *is* the event log itself, and every read model is a projection
  replayed from it — covered in full in
  [Consistency & Consensus §2](../backend/consistency-and-consensus.md#2-eventual-consistency-in-practice-event-sourcing).
- The practical decision: reach for CQRS alone when the only problem is
  "reads and writes need different shapes"; add event sourcing on top
  specifically when you also need a full audit trail or the ability to
  rebuild a corrupted read model from scratch by replaying history.

## 3. "What's the Saga pattern, and what problem does it solve that a single-database transaction doesn't have?"

**Answer:**

- A single database transaction gives you one guarantee for free: either
  every change inside it commits, or none do. That guarantee stops
  working the moment a business transaction spans **multiple services,
  each with its own database** — there's no shared transaction boundary
  across them, so a traditional commit/rollback simply isn't available.
- A **Saga** breaks that business transaction into a sequence of local
  transactions, one per service, each committing independently. If a
  later step fails, the saga runs **compensating actions** — explicit,
  purpose-built operations that undo the effect of each already-completed
  step, in reverse order — since there's no automatic rollback across
  services the way a single database transaction would give you for free.
- Two ways to coordinate the sequence:
    - **Orchestration** — a central coordinator explicitly tells each
      service what to do next and reacts to failures itself. Easier to
      reason about and debug (one place sees the whole flow), at the
      cost of that coordinator becoming a real point of coupling between
      every service it orchestrates.
    - **Choreography** — each service listens for events and reacts
      independently, with no central coordinator at all. More decoupled,
      but genuinely harder to trace — "what actually happened to this
      order" means reconstructing the story from events scattered across
      several services' logs instead of reading one coordinator's flow.

## A Saga in Motion: Success, Then a Failure Mid-Flight

<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of a saga for an order: payment and inventory steps succeeding, then shipping failing, triggering compensating actions that undo inventory and payment in reverse order" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="40" y="40" width="200" height="60" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="140" y="75" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Orchestrator</text>
<rect x="340" y="40" width="200" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.4;0.44;0.78;1" dur="19s" repeatCount="indefinite"></animate></rect>
<rect x="340" y="40" width="200" height="60" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.44;0.48;0.78;1" dur="19s" repeatCount="indefinite"></animate></rect>
<text x="440" y="70" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">Payment</text>
<text x="440" y="88" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.4;0.44;0.78;1" dur="19s" repeatCount="indefinite"></animate>charged</text>
<text x="440" y="88" font-size="12" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.44;0.48;0.78;1" dur="19s" repeatCount="indefinite"></animate>refunding…</text>
<rect x="590" y="40" width="200" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;1;1;0;0;1" keyTimes="0;0.2;0.44;0.48;0.62;1" dur="19s" repeatCount="indefinite"></animate></rect>
<rect x="590" y="40" width="200" height="60" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.5;0.54;0.62;1" dur="19s" repeatCount="indefinite"></animate></rect>
<text x="690" y="70" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">Inventory</text>
<text x="690" y="88" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.2;0.44;0.48;1" dur="19s" repeatCount="indefinite"></animate>reserved</text>
<text x="690" y="88" font-size="12" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.5;0.54;0.62;1" dur="19s" repeatCount="indefinite"></animate>releasing…</text>
<rect x="340" y="280" width="200" height="60" rx="8" fill="#fbe7e4" stroke="#c0392b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.38;0.42;0.56;0.6;1" dur="19s" repeatCount="indefinite"></animate></rect>
<text x="440" y="310" font-size="14" font-weight="600" text-anchor="middle" fill="#8e2d20"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.38;0.42;0.56;0.6;1" dur="19s" repeatCount="indefinite"></animate>Shipping</text>
<text x="440" y="328" font-size="12" text-anchor="middle" fill="#8e2d20"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.38;0.42;0.56;0.6;1" dur="19s" repeatCount="indefinite"></animate>failed</text>
<line x1="240" y1="70" x2="340" y2="70" stroke="#9aa5b3" stroke-width="2"></line>
<line x1="540" y1="70" x2="590" y2="70" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;1;1" keyTimes="0;0.2;1" dur="19s" repeatCount="indefinite"></animate></line>
<line x1="690" y1="100" x2="440" y2="280" stroke="#c0392b" stroke-width="2" stroke-dasharray="5,5"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.38;0.42;0.58;1" dur="19s" repeatCount="indefinite"></animate></line>
<line x1="590" y1="60" x2="540" y2="60" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.5;0.54;0.62;1" dur="19s" repeatCount="indefinite"></animate></line>
<line x1="340" y1="60" x2="240" y2="60" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.44;0.48;0.78;1" dur="19s" repeatCount="indefinite"></animate></line>
<text x="450" y="400" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.3;0.34;1" dur="19s" repeatCount="indefinite"></animate>Payment and Inventory each commit their own local transaction, in order.</text>
<text x="450" y="400" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.34;0.38;0.56;0.6;1" dur="19s" repeatCount="indefinite"></animate>Shipping fails — there's no automatic rollback across services.</text>
<text x="450" y="400" font-size="17" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.6;0.64;1" dur="19s" repeatCount="indefinite"></animate>Compensating actions run in reverse: release inventory, then refund payment.</text>
</svg>

## 4. "Walk through that example — payment and inventory succeed, shipping fails. What actually happens?"

**Answer:**

- The orchestrator calls Payment, which charges the customer and commits
  locally — step one succeeds.
- It then calls Inventory, which reserves the stock and commits locally
  — step two succeeds. From the orchestrator's view, the saga is two
  steps into a successful flow, with no single transaction spanning both.
- Shipping fails — no carrier available, say. There's nothing to "roll
  back" in the database sense; Payment and Inventory already committed
  their own local transactions and have no idea Shipping even exists.
- The orchestrator instead runs **compensating actions**, in reverse
  order: release the reserved inventory, then refund the payment. Each
  compensation is its own explicit operation, built and tested on
  purpose — there's no generic "undo" a database can perform across
  services on your behalf.

## 5. "What does eventual consistency actually look like to the user here?"

**Answer:**

- The same read-model lag already covered generally in
  [Consistency & Consensus §1](../backend/consistency-and-consensus.md#1-the-consistency-spectrum-from-strong-to-eventual)
  shows up concretely in CQRS: a write (command) can succeed while a
  query against the read model, issued immediately after, hasn't caught
  up to reflect it yet.
- The practical UX answer isn't to fight this with a slower, synchronous
  read — it's to design the interface around it: an optimistic update in
  the UI reflecting what the user just did, or an explicit "your order
  is being processed" state, rather than implying the read model is
  always instantly current when it structurally isn't.

| Pros | Cons / Trade-offs |
|---|---|
| CQRS lets read and write models each be optimized for their own job | Two models to keep in sync instead of one — real added complexity |
| Saga handles multi-service transactions with no shared database at all | Every step needs an explicit, tested compensating action — nothing is automatic |
| Orchestrated sagas are easy to trace — one place shows the whole flow | The orchestrator becomes a real coupling point across every service it coordinates |
| Choreographed sagas keep services fully decoupled from each other | Reconstructing "what actually happened" means piecing together events across services |

---

## Code Samples

No dedicated code samples for this page.
