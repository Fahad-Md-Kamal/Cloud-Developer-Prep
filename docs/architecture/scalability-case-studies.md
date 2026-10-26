---
title: "Scalability Case Studies"
---

# Scalability Case Studies

Viral traffic spikes, global distribution, distributed consistency,
and microservices-vs-monolith — the scalability judgment calls system
design interviews probe, plus a worked example tying the methodology
together end to end.

## 1. "How would you design for a sudden, unpredictable traffic spike — a post going viral, a flash sale?"

**Answer:**

- Separate **reads** (people viewing something) from **writes**
  (people creating or changing something) early. A viral spike is
  almost always a flood of *reads* — many people looking at the same
  one thing — so that's the side that needs to survive the spike.
- Cache the hot item specifically, as close to the user as possible —
  a CDN, or a cache sitting in front of your application. This way
  the database only gets asked for that one popular item *once*, not
  once per viewer.
- Auto-scaling (adding more servers automatically) helps, but it's not
  instant — new servers take time to start. During that gap, something
  else has to hold the line: slow down requests on purpose (rate
  limiting), or let extra write load pile up in a queue instead of
  hitting the database directly.
- Plan for a worse-but-working response, not just more capacity. A
  simplified page (fewer recommendations, a slightly outdated count)
  that still loads beats a page that doesn't load at all.

## 2. "How do you handle global distribution and latency?"

**Answer:**

- The core question: can this specific piece of data be served from a
  server near the user, or does every request have to go all the way
  back to one single "real" copy of it, wherever that lives?
- Data that can tolerate being slightly out of date (a product
  description, a social feed) can be copied to servers near the user —
  a CDN, or a read-only copy of the database in each region.
- Data that must always be exactly correct (a bank balance, how many
  items are left in stock) usually can't be copied around safely —
  every request has to reach the one real copy, wherever it is, even
  if that's slow for someone far away.
- **Multi-region, every region can write ("active-active"):** lowest
  latency for everyone, since nobody has to reach a distant server —
  but now you need a real plan for what happens if two regions both
  change the same record at nearly the same moment.
- **One region writes, others just copy ("active-passive"):** no
  conflicts to resolve, since there's only ever one place changes
  happen — but users far from that one region pay extra latency on
  every write.

## 3. Data Consistency: CAP and PACELC

!!! example "Real-world analogy: two bank branches, one phone line"
    - Two branches of the same bank share customer balances over a
      single phone line between them. Normally, whenever one branch
      changes a balance, it calls the other branch to keep both copies
      in sync.
    - **The phone line goes down.** A customer walks into Branch A and
      asks to withdraw money. Branch A has two choices: refuse the
      withdrawal until the phone line is back (both branches stay
      correct, but the customer is turned away), or allow it anyway
      (the customer is served, but the two branches' books might now
      disagree until the line comes back). That choice — correctness
      vs. serving the customer, *only during an outage* — is the
      **CAP theorem**.
    - **Now the phone line is working fine, no outage at all.** Branch
      A still has a choice on *every single transaction*: call Branch B
      and wait for them to confirm before telling the customer "done"
      (always correct, but slower), or tell the customer "done"
      immediately and update Branch B in the background (fast, but a
      customer checking their balance at Branch B half a second later
      might see the old number). That's the choice **PACELC** adds —
      the same correctness-vs-speed trade-off, but on a normal day with
      nothing broken.

**"How do you reason about data consistency in a distributed system,
practically, not just as CAP-theorem trivia?"**

**Answer:**

- When part of the system can't reach another part (a network
  **partition**), you must pick one: keep serving requests and risk
  showing stale/wrong data (**availability**), or stop serving until
  things reconnect and you're sure the data is right (**consistency**).
- This is a decision made **per feature**, not once for the whole
  system — different pieces of the same product can reasonably make
  opposite choices.
- The question to actually ask for each piece of data: "what really
  breaks if this is wrong for a few seconds?" A like-count being off
  by a few is fine. A payment being charged twice is not. That answer
  — not a rule from a textbook — should decide it.
- **Eventual consistency** is the practical middle ground for most
  read-heavy, non-financial data: accept that it might be briefly out
  of date, in exchange for staying available and fast. It's one point
  on a wider spectrum — see
  [Consistency & Consensus §1](../distributed-systems/consistency-and-consensus.md#1-the-consistency-spectrum-from-strong-to-eventual)
  for the options in between (causal, read-your-own-writes, monotonic
  reads, session, bounded staleness).

**"What does PACELC add on top of CAP?"**

- CAP only describes what happens **during an outage** (the phone line
  being down). PACELC's point: that same trade-off is still there
  **every single day, outage or not** — it's just consistency vs.
  *speed* instead of consistency vs. *staying online*.
- A concrete example: a database that waits for a backup copy to
  confirm every write before saying "saved" is choosing correctness
  over speed on *every write*, whether or not anything is broken. A
  database that says "saved" immediately and copies the data in the
  background is choosing speed over correctness — same trade, no
  outage involved.
- This is why PACELC is the more complete framework for an interview
  conversation: CAP only prepares you to answer "what happens during
  an outage" (rare). PACELC makes you name the speed-vs-correctness
  trade a system is making on a completely normal Tuesday, which is
  the trade that's actually being paid most of the time.
- Labeling real systems, using the two choices above (outage behavior
  / normal-day behavior): Cassandra and DynamoDB (in their default
  settings) choose availability during an outage and speed on a normal
  day — shorthand **PA/EL**. A traditional single-leader database set
  up to wait for a backup copy on every write chooses correctness both
  times — shorthand **PC/EC**.

## 4. "Microservices vs. monolith — how do you actually decide, instead of defaulting to microservices because it sounds more senior?"

**Answer:**

- A **monolith** (one single application, one codebase, one deploy) is
  the right starting point for a new system, a small team, or a domain
  nobody fully understands yet. It's faster to build, easier to debug
  — one process, one log to read — and doesn't add distributed-systems
  problems you don't have yet.
- **Microservices** (the system split into several independently
  deployed services) earn their cost once there's a real, specific
  reason: different teams need to ship on different schedules without
  blocking each other, one part of the system has very different
  resource needs than the rest, or there's a genuinely stable boundary
  worth building a formal API around.
- "It depends, and here's exactly what it depends on" is a stronger
  answer than confidently picking microservices by default — picking
  the trendier-sounding answer with no real justification is a sign of
  inexperience at senior level, not sophistication.

## 5. Worked example: designing a social-feed-style system, end to end

Walking the [System Design Methodology](system-design-methodology.md)
and the patterns above through one concrete prompt: "design a system
where users post short updates and see a feed of updates from people
they follow."

- **Clarify requirements first:** mostly reads or mostly writes? (Almost
  always reads — far more people viewing a feed than posting to it.)
  Does the feed need to update in real time, or can it lag a little?
  Roughly how many followers does a typical user have — a user with
  100 followers and a user with 10 million followers are different
  engineering problems.
- **Estimate the load:** posts per day, average follower count, feed
  views per day. This decides whether a feed can be pre-built the
  moment someone posts, or has to be assembled on the spot when
  someone opens it.
- **The core design decision: build the feed at post time, or at view
  time?**
    - **At post time ("fan-out-on-write"):** the moment someone posts,
      immediately add it to every follower's own pre-built feed. Makes
      viewing a feed cheap (it's already built), but makes posting
      expensive — and breaks down for an account with millions of
      followers, since one post now means millions of writes at once.
    - **At view time ("fan-out-on-read"):** don't pre-build anything;
      when someone opens their feed, pull recent posts from everyone
      they follow and merge them on the spot. Makes posting cheap, but
      makes every feed view more expensive.
    - Most real systems use both: pre-build the feed for typical
      accounts, but fall back to building-on-the-spot (or a
      capped/sampled version) for huge accounts — so one celebrity's
      post never triggers millions of writes at once.
    - This is the exact same idea as
      [SNS+SQS fan-out](../distributed-systems/messaging-kafka-redis-and-aws.md#4-aws-sns-vs-sqs-and-the-fan-out-pattern)
      — "do the expensive broadcast once, let everyone else work
      independently" — just aimed at feed entries instead of service
      events. The huge-account problem here is the same kind of
      bottleneck as one overwhelmed consumer there, and it's solved
      the same way: don't force the expensive path onto the one case
      that can't afford it.
- **Caching:** both a user's recent posts and their already-assembled
  feed are natural things to cache — see
  [Common System Design Patterns §2](system-design-patterns.md#2-how-do-you-decide-on-a-caching-strategy-for-a-system-design-answer)
  for how to pick a caching strategy.
- **Name the trade-off out loud:** this is the same speed-vs-correctness
  choice from [§3](#3-data-consistency-cap-and-pacelc) — a feed that's
  a few seconds behind is a perfectly reasonable trade for lower
  latency and cheaper writes. Say that it's a deliberate choice,
  rather than leaving it unstated.
