---
title: "Frontend Fundamentals"
---

# Frontend Fundamentals

**Status: placeholder.** Flagged from the Svea Solar Senior Fullstack
Engineer (Django) JD gap analysis (2026-09-23) — "solid frontend
development skills, specific framework not required." The only
existing frontend content on this site is Angular-specific (inside
[TypeScript & Angular for Backend Leads](typescript-and-angular-for-backend-leads.md),
aimed at backend leads talking to an Angular team), not
framework-agnostic fundamentals, and not React —
which pairs with Django at least as often as Angular in practice. Not
yet given the full Q&A deep-dive treatment this site's other chapters
have.

**Topics to cover when this gets deep-dived:**

- Core JS/TS fundamentals a backend-leaning fullstack engineer should
  stay sharp on: event loop, closures, async/await, module systems.
- Component-based UI architecture — props/state, unidirectional data
  flow — as concepts transferable across React/Angular/Vue, not tied
  to one framework.
- React specifics, since it's the most likely pairing with Django:
  hooks, rendering behavior, common gotchas (stale closures,
  unnecessary re-renders).
- State management approaches: local component state vs. a global
  store (Redux/Zustand/Context) vs. server-state libraries (React
  Query/SWR).
- Consuming a REST API from the frontend — mirrors the existing
  ["API Design Patterns Angular Teams Love"](typescript-and-angular-for-backend-leads.md#api-design-patterns-angular-teams-love)
  angle already written for Angular, generalized.
- Accessibility basics: semantic HTML, ARIA, keyboard navigation.
- Build tooling at a conceptual level (Vite/Webpack) — enough to
  discuss trade-offs, not deep bundler expertise.
- Interview framing: "you're primarily backend — convince me you can
  own a frontend feature end-to-end."
