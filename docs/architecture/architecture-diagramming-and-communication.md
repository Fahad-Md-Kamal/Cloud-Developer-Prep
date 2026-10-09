---
title: "Architecture Diagramming & Communication"
---

# Architecture Diagramming & Communication

"Draw the architecture" is ambiguous until a zoom level is picked —
the C4 model, discussing trade-offs convincingly, and handling a
deep-dive follow-up that wasn't anticipated.

## 1. "What is the C4 model, and why does 'draw the architecture' need a model at all?"

**Answer:**

- The **C4 model** (Context, Containers, Components, Code — created by
  Simon Brown) describes a software system at four different zoom
  levels, each for a different audience.
- One diagram trying to serve every audience usually satisfies none of
  them — a system design interview's "draw the architecture" is
  ambiguous until a level is picked; jumping straight to
  implementation-level detail when the interviewer wanted the
  high-level shape (or vice versa) is a common miss.
- **Level 1 — System Context**: the system as a single box, showing
  how it relates to users and other systems around it. No technical
  detail. Audience: anyone, including non-technical stakeholders.
- **Level 2 — Container**: zooms into the system, showing its
  high-level deployable units (a web app, an API, a database, a
  queue, a mobile app) and how they communicate. "Container" here
  means *separately runnable/deployable thing*, not a Docker
  container specifically — a common point of confusion. Audience: any
  technical person, not just architects.
- **Level 3 — Component**: zooms into *one* container, showing its
  major internal building blocks and their interactions — inside an
  API container, that's controllers, services, repositories.
  Audience: developers working on that specific container.
- **Level 4 — Code**: zooms into one component, typically a class
  diagram. Rarely hand-maintained in practice since it goes stale
  fast — usually generated on demand from an IDE when actually
  needed, not kept as a static artifact.

**Likely follow-up — "which level do you actually draw in a system design interview?"**

- Level 1 briefly, to confirm scope with the interviewer, then Level 2
  as the main high-level design — that's the level most system design
  interviews are actually asking for.
- Level 3 only for the specific component the interviewer deep-dives
  into, not for the whole system — drawing Level 3 detail for
  everything wastes time on parts nobody asked about.
- Level 4 essentially never comes up live; if class-level detail
  matters, it's discussed in words, not drawn.

| Pros | Cons / Trade-offs |
|---|---|
| Matches diagram detail to the actual audience/question, not a one-size-fits-all diagram | Four levels is more structure to hold in your head than "just draw boxes" |
| Level 2 (Container) maps directly onto what most system design interviews are really asking for | Picking the wrong level for the moment (too detailed or too abstract) still happens without discipline |
| Gives a shared vocabulary ("this is a Level 2 question") for redirecting scope with the interviewer | Level 4 is rarely useful to maintain and easy to over-invest in anyway |

## 2. "How do you discuss trade-offs convincingly instead of just listing options?"

**Answer:**

- State the actual axis of tension — consistency vs. availability,
  cost vs. latency, simplicity vs. flexibility — not just "there are
  pros and cons" without naming what's actually being traded.
- Tie the choice back to the requirements gathered earlier: "given we
  said writes need to succeed even during a network partition, I'm
  choosing AP here" is a grounded answer; a generic textbook
  CAP-theorem recitation disconnected from the specific prompt is not.
- Be ready to reverse the decision if the interviewer changes a
  requirement mid-conversation — rigid attachment to one answer reads
  worse than the specific choice made, since it signals the choice
  wasn't actually reasoned from the requirements in the first place.

## 3. "How do you handle a deep-dive follow-up you didn't fully anticipate?"

**Answer:**

- Reason out loud from first principles rather than freezing —
  "I haven't designed this exact piece before, but here's how I'd
  think about it" is a legitimate, genuinely valued answer at senior
  level, not a red flag.
- Ask a clarifying question back if the follow-up itself is ambiguous
  — the same discipline as the opening requirements-gathering step,
  just applied mid-interview instead of at the start.
- Narrate the reasoning process, not just the eventual answer — an
  interviewer evaluating a deep-dive is usually watching *how* the
  gap gets closed, not just whether the final answer happens to be
  right.
