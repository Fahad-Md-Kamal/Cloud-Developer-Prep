---
title: "System Design Methodology"
---

# System Design Methodology

How to approach an open-ended system design prompt systematically —
the meta-skill underneath any specific design question, before a
single box gets drawn.

## 1. "You're given an open-ended system design prompt — what's the first thing you do, before drawing anything?"

**Answer:**

- Clarify requirements first — **functional** (what does the system
  actually need to do) and **non-functional** (scale, latency,
  consistency needs). Jumping straight to boxes before establishing
  what's being built is the most common early mistake.
- Ask about scale explicitly: how many users, how many requests per
  second, read vs. write ratio. These numbers drive nearly every later
  architecture decision — a design for 1,000 users and a design for
  100 million users are different systems, not the same system scaled
  up.
- State assumptions out loud when the interviewer doesn't give a
  number. An assumption that's stated and reasoned about is fine; an
  unstated one that turns out wrong wastes the rest of the session
  building on the wrong foundation.

**Likely follow-up — "what if the interviewer says 'just pick reasonable numbers'?"**

- That's permission to move forward, not an invitation to skip the
  step — pick a concrete number, say it out loud, and note it's an
  assumption that can be revisited if it changes the design
  meaningfully.

## 2. "How do you do back-of-envelope capacity estimation quickly and correctly?"

**Answer:**

- Core technique: estimate requests/sec from daily active users and
  requests-per-user-per-day, then estimate storage from record size ×
  record count × retention period.
- Round aggressively to powers of 10 — precision doesn't matter here,
  order of magnitude does. The goal is "is this roughly a
  single-server problem, a sharded-database problem, or a
  distributed-systems problem," not an exact figure.
- Reference numbers worth having memorized: a day is ~86,400 seconds
  (~100k for quick mental math); 1 million requests/day is roughly 12
  requests/sec average (though peak traffic is what actually matters
  for capacity, not the average).
- The point of doing this isn't the specific number — it's proving the
  design can be sanity-checked against real constraints ("does this
  fit in memory on one machine," "does this exceed what a single
  database can write per second").

| Pros | Cons / Trade-offs |
|---|---|
| Forces the design to be grounded in real numbers, not vibes | Adds time pressure in an already time-boxed interview |
| Surfaces which components actually need to scale vs. which don't | Easy to over-invest time perfecting a number nobody asked for |
| Gives a concrete basis for later trade-off discussions | An estimate stated with false precision reads worse than a rounded one |

## 3. "How do you structure your time across a 45-60 minute system design interview?"

**Answer:**

- Rough allocation: ~5 minutes requirements clarification, ~5-10
  minutes capacity estimation, ~15-20 minutes high-level design,
  ~15-20 minutes deep dive into the one or two components the
  interviewer actually cares about, remaining time for trade-offs and
  wrap-up.
- Signal the transitions explicitly — "I'll sketch the high-level
  design first, then we can go deeper wherever you'd like" — this
  both manages time and demonstrates structured thinking, not just
  eventual correctness.
- The most common failure mode: spending 30 minutes perfecting the
  high-level box diagram and never reaching a deep dive, which is
  usually where the actual signal is for a senior-level interview.

**Likely follow-up — "what do you do if you're running out of time mid-deep-dive?"**

- Say so explicitly and propose a plan — "I'm going to keep this
  component's design at a higher level so we have time to touch on
  X" — rather than silently running out the clock or rushing the rest
  incoherently.
