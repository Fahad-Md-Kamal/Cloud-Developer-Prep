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

- Separate the **read path** from the **write path** early — a viral
  spike is almost always read-heavy (many people viewing one thing),
  and the read path is the one that needs to absorb the spike, not
  necessarily the write path.
- Cache aggressively at the edge for the hot content specifically — a
  CDN or an application-level cache in front of the one viral item
  avoids hammering the origin/database for the same data repeatedly.
- Auto-scaling helps but isn't instant — it has a ramp-up time,
  during which a fixed-capacity buffer (rate limiting, graceful
  degradation, a queue absorbing excess write load) is what actually
  prevents an outage during the gap.
- Design for graceful degradation, not just more capacity — a
  simplified response (fewer personalized recommendations, a cached
  slightly-stale count) under load beats a full outage.

## 2. "How do you handle global distribution and latency?"

**Answer:**

- Data locality is the core question: can this data be served from a
  region close to the user, or does it need to come from a single
  authoritative source regardless of the user's location?
- Read-heavy, eventually-consistent-tolerant data can be replicated
  close to users (regional read replicas, a CDN); strongly consistent
  data (a financial balance, an inventory count) usually can't be, and
  the design has to accept the latency of reaching the authoritative
  source.
- Multi-region active-active (every region can serve writes) buys the
  lowest latency but forces a real answer to conflict resolution when
  two regions write to the same record near-simultaneously —
  active-passive (one region writes, others replicate) avoids that
  conflict at the cost of higher write latency for users far from the
  active region.

## 3. "How do you reason about data consistency in a distributed system, practically, not just as CAP-theorem trivia?"

**Answer:**

- The CAP theorem's practical form: under a network partition, choose
  between availability (keep serving, possibly stale/inconsistent
  data) and consistency (refuse to serve until the partition heals).
  This is a real per-feature decision, not a single property of the
  whole system — different parts of the same system reasonably make
  different choices.
- Ask "what actually breaks if this is briefly inconsistent?" for
  each piece of data — a social media like-count being off by a few
  for a few seconds is fine; a payment being double-charged is not.
  That answer, not a textbook default, should drive the choice.
- **Eventual consistency** is the practical middle ground for most
  read-heavy, non-financial data — accept a bounded staleness window
  in exchange for availability and lower latency.

## 4. "Microservices vs. monolith — how do you actually decide, instead of defaulting to microservices because it sounds more senior?"

**Answer:**

- A monolith is the right default for a new system, a small team, or
  unclear domain boundaries — it's faster to build, easier to debug
  (one process, one log stream, one deploy), and doesn't pay
  distributed-systems tax for problems that don't exist yet.
- Microservices earn their cost once there's a real, specific
  driver: independent team scaling (different teams need to deploy on
  different schedules without blocking each other), independent
  technical scaling (one component has radically different
  resource/scaling needs than the rest), or a genuine domain boundary
  that's stable enough to build an API contract around.
- Saying "it depends, and here's specifically what it depends on" is a
  stronger interview answer than confidently picking microservices by
  default — defaulting to the trendier-sounding answer without
  justification is a real signal of inexperience at senior level, not
  sophistication.

## 5. Worked example: designing a social-feed-style system, end to end

Walking the [System Design Methodology](system-design-methodology.md)
and pattern choices above through one concrete prompt: "design a
system where users post short updates and see a feed of updates from
people they follow."

- **Clarify requirements**: read-heavy or write-heavy? (Almost always
  read-heavy — far more feed views than posts.) Real-time delivery
  required, or is some staleness acceptable? Fan-out to how many
  followers, roughly — a user with 100 followers and a user with 10
  million followers are different engineering problems.
- **Capacity estimate**: posts/day, average follower count, and
  reads/day for feed views — this determines whether feed generation
  can happen at write time (fan-out-on-write) or has to happen at
  read time (fan-out-on-read).
- **Core design decision — fan-out-on-write vs. fan-out-on-read**:
  writing a new post into every follower's precomputed feed at post
  time makes reads cheap but writes expensive (and breaks down for
  very high follower counts); computing a feed at read time by
  merging each followed user's recent posts makes writes cheap but
  reads more expensive. Most real systems use a hybrid — fan-out on
  write for typical users, fan-out on read (or a capped/sampled
  fan-out) for very-high-follower accounts, to avoid one huge post
  triggering millions of synchronous writes.
- **Caching**: the recent-posts-per-user data and the assembled feed
  itself are both natural caching targets — see
  [Common System Design Patterns §2](system-design-patterns.md#2-how-do-you-decide-on-a-caching-strategy-for-a-system-design-answer)
  for the strategy choice.
- **Trade-off to name explicitly**: this is a consistency-vs-latency
  choice in the [§3](#3-how-do-you-reason-about-data-consistency-in-a-distributed-system-practically-not-just-as-cap-theorem-trivia)
  sense — a feed that's a few seconds stale is a fine trade for lower
  latency and lower write cost; that's worth stating out loud as a
  deliberate choice, not leaving implicit.
