---
title: "Choosing a Python Web Framework"
---

# Choosing a Python Web Framework

Django vs. FastAPI, and Python vs. other backend ecosystems — the
"why this stack" questions that come up when justifying a technology
choice, not the framework-specific mechanics themselves. For those,
see [Django & DRF](django-orm.md) and
[FastAPI: Dependency Injection & Background Tasks](fastapi-dependency-injection.md).

## 1. "Django vs. FastAPI — how do you decide which one to reach for on a new service?"

**Answer:**

- **Django**: batteries-included — ORM, admin panel, auth, migrations,
  forms all built in and integrated. Best for a full web application
  with significant CRUD, an admin interface, and a data model that
  benefits from Django's ORM.

!!! info "Batteries-included"

    The framework ships with almost everything built in and
    pre-integrated (ORM, admin, auth, forms), instead of making you
    assemble it from separate third-party packages. The term comes
    from Python's own tagline for its standard library.

- **FastAPI**: async-first, minimal, explicit — Pydantic-based
  validation, automatic OpenAPI/Swagger docs generated from type
  hints, no built-in ORM/admin (bring your own, e.g. SQLAlchemy). Best
  for high-throughput APIs, I/O-bound services calling many external
  APIs concurrently, or when auto-generated API docs are a real
  requirement.

!!! info "Async-first"

    Built from the ground up around `async`/`await` (non-blocking
    I/O), rather than having async support bolted onto a framework
    originally designed as synchronous. FastAPI is async-first;
    Django's async support arrived later and is still partial in
    places — see [Concurrency & AsyncIO](concurrency-and-asyncio.md)
    for what async actually buys you and when it doesn't matter.

!!! info "Micro-framework"

    The opposite of batteries-included: a minimal core, usually just
    routing, where everything else (ORM, auth, admin) is a separate
    package you choose and wire up yourself. Flask and FastAPI both
    start here, though FastAPI adds validation and docs generation as
    part of its core.

- Django REST Framework narrows the gap for API-only use cases, but
  still carries Django's synchronous-first ORM underneath — FastAPI is
  async natively, ground-up.
- Team/product factor: Django's admin panel alone can save weeks of
  internal-tooling work — if the project needs an admin UI for
  non-engineers, that's a strong pull toward Django regardless of
  async needs.

**Likely follow-up — "could you use both in the same organization?"**

- Yes, commonly: Django for the primary web app and admin/back-office,
  FastAPI for a specific high-throughput or async-heavy service (an
  AI/LLM gateway, a webhook processor) — not mutually exclusive at the
  org level. Matches how [Chapter 6](chapter-6.md) treats FastAPI as
  one service type among several in a microservices architecture.

| Pros: Django | Cons: Django |
|---|---|
| Batteries-included — ORM, admin, auth, forms, migrations all integrated and consistent | Heavier for a small, pure-API service — machinery you may not need |
| Huge, mature ecosystem and battle-tested conventions | Async support is newer/partial compared to a framework built async-first |
| Admin panel alone can replace weeks of internal tooling | More opinionated — harder to deviate from "the Django way" |

| Pros: FastAPI | Cons: FastAPI |
|---|---|
| Async-first — high concurrency for I/O-bound workloads without extra plumbing | No built-in ORM/admin — must choose and wire up your own (e.g. SQLAlchemy) |
| Automatic OpenAPI/Swagger docs generated from type hints, always in sync with code | Smaller batteries-included surface — auth, admin, forms are DIY |
| Pydantic validation is fast, type-safe, and doubles as the API schema | Less opinionated — more upfront project-structure decisions |

## 2. "Why would a team choose Python (Django/FastAPI) over Node.js/Express for a backend?"

**Answer:**

- Python's ecosystem for data processing, ML/AI integration, and
  scientific computing (NumPy/Pandas, PyTorch, and the LLM tooling
  ecosystem — LangChain, the OpenAI/Anthropic SDKs) is far deeper than
  Node's — relevant the moment the backend needs to do more than serve
  JSON.
- Django's batteries-included model gets a CRUD-heavy application to
  production faster than assembling an equivalent Express + ORM + auth
  + admin stack from separate packages.
- Node/Express's real strength: a single-language stack (JS/TS) shared
  with the frontend, and a non-blocking I/O model that's arguably
  simpler to reason about than Python's asyncio/GIL split — legitimate
  reasons a team picks Node, not something to dismiss.
- Honest framing for an interview: it's not "Python is strictly
  better" — Python wins when the backend needs data/ML-adjacent work
  or Django's batteries; Node wins when the team wants one language
  end-to-end or already has a JS-heavy stack.

**Likely follow-up — "what would make you recommend Node instead, even on a Python-shop team?"**

- A genuinely thin API layer in front of a frontend-heavy application.
- A team already all-in on TypeScript across the stack.
- A real-time-heavy feature set (Node's event-loop model and ecosystem
  like Socket.io) where Python's async story is comparatively less
  mature.

| Pros: Python (Django/FastAPI) | Cons vs. Node/Express |
|---|---|
| Much deeper data/ML/AI ecosystem — relevant once the backend isn't just CRUD | Two languages across the stack if the frontend is JS/TS — real context-switching cost |
| Django's batteries-included model reaches production faster for CRUD-heavy apps | Node's non-blocking I/O model is arguably simpler to reason about than asyncio + GIL |
| FastAPI closes most of the async/performance gap Python used to have vs. Node | Smaller pool of "full-stack JS" engineers who move freely between frontend and backend |

## 3. "Why Django over Ruby on Rails or Java Spring Boot?"

**Answer:**

- **Django vs. Rails** — both are "batteries-included,
  convention-over-configuration" frameworks solving the same
  philosophy in different languages. The real decision driver is
  usually team/hiring pool and ecosystem (Python's ML/data ecosystem
  vs. Ruby's), not a technical gap between the frameworks themselves.

!!! info "Convention over configuration"

    The framework has one "expected" way to do something (where files
    go, how a model maps to a table) and just does it, instead of
    asking you to configure every decision explicitly. Faster to
    start, harder to deviate from once a project needs something the
    convention doesn't anticipate.

- **Django vs. Spring Boot** — Spring Boot (Java/Kotlin) is the
  heavier-weight, more enterprise-oriented option: stronger static
  typing, mature for large regulated enterprises, but meaningfully
  more boilerplate and a slower iteration loop than Django for a
  small-to-mid-size team.
- The honest, senior-level answer to a "why X over Y" question like
  this is rarely "framework A is technically superior" — it's team
  composition, hiring market, existing codebase/ecosystem investment,
  and the nature of the workload (data/ML-heavy → Python; large
  regulated enterprise monolith → Java; team already JS-heavy → Node).

**Likely follow-up — "if you joined a team already using Rails or Spring, would you push to rewrite in Django?"**

- No — a working system in a well-supported framework isn't a rewrite
  candidate just because of personal stack preference.
- A rewrite needs a concrete pain point (hiring difficulty, a proven
  performance ceiling, a hard ecosystem gap like ML integration) to
  justify the cost, not framework preference alone.

| Consideration | Favors Python/Django | Favors Rails / Spring Boot |
|---|---|---|
| Data/ML/AI integration needs | Python's ecosystem is significantly deeper | Not Rails/Spring's strength |
| Team already deep in Ruby or the JVM ecosystem | — | Switching costs (hiring, retraining) usually outweigh framework preference |
| Large, regulated enterprise monolith | — | Spring Boot's maturity and typing rigor is a genuine fit |
| Fast, CRUD-heavy MVP | Django's admin + ORM ships faster | Rails' "convention over configuration" is comparably fast |
