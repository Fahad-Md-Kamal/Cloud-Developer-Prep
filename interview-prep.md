# Interview Prep — Senior Python Developer (External Client via BJIT)

**Context:** External client interview, ~90 min with a test component. Format unconfirmed — could be live coding, verbal Q&A, written quiz, or a mix. Possibly next week (week of 2026-09-28). If selected, BJIT contracts you out as an augmented resource.

**Your positioning:** 6+ years Python/Django, self-rated expert in Python/Django/DRF/FastAPI, SQL, REST API design. This JD is a strong match — treat this as "confirm depth," not "close a big gap."

---

## 1. Gap check vs. the JD

| JD asks for | Your resume | Action |
|---|---|---|
| Python + Django (expert) | ★★★★★ | Just review edge cases (§3) |
| SQL / relational modeling | ★★★★★ | Review indexing, joins, normalization (§4) |
| AWS: ECS, Lambda, S3, Aurora RDS, SQS, DynamoDB | Have Lambda, S3, SQS, EC2, Docker. **Missing: ECS, Aurora RDS, DynamoDB** | 30–45 min crash review each (§5) — don't claim hands-on, but be able to talk sensibly |
| Nice to have: React/React Native/Golang | React ✓, Golang basic (★★★☆☆), React Native — none | Mention React confidently; be honest Golang is "working knowledge," no RN experience |
| Nice to have: AI/ML (Lex, Watson, GCP) | Azure OpenAI + LangChain RAG (CEC IRTool) | Reframe as: "I've built production RAG pipelines with LangChain/Azure OpenAI — the concepts (embeddings, retrieval, prompt orchestration) transfer directly to Lex/Watson/GCP, I just haven't used those specific SDKs" |
| Team collaboration, proactive, B2+/C1 English | N/A (soft skill / this call itself is evidence) | No prep needed beyond the interview itself |

---

## 2. Likely 90-min structure (unconfirmed — ask BJIT recruiter to confirm if possible)

A common shape for this kind of client-vetting round:
- 10–15 min: introductions, walk through your CV/projects
- 30–40 min: live coding or a written technical test (Python/Django/SQL)
- 20–30 min: verbal Q&A — architecture, past decisions, AWS, testing practices
- 10 min: your questions for them

**Action:** ask your BJIT contact (recruiter/account manager) directly: "Is the test live-coding, take-home, or multiple choice? Which tools (shared IDE, HackerRank, their own repo)?" Knowing this changes prep priority a lot — worth a quick message even if the answer is "not sure yet."

---

## 3. Python/Django review checklist

Go through these and make sure you can *explain and code* each, not just recognize it:

**Python core**
- Generators vs iterators; `yield` and `yield from`
- Decorators (with and without arguments), `functools.wraps`
- Context managers (`with`, `__enter__`/`__exit__`, `contextlib.contextmanager`)
- `*args`/`**kwargs`, mutable default argument gotcha
- GIL — what it is, why it matters, when `asyncio`/`multiprocessing`/`threading` each apply
- List/dict/set comprehensions vs generator expressions (memory tradeoffs)
- `@staticmethod` vs `@classmethod` vs instance method
- Exception handling: custom exceptions, `finally`, exception chaining
- Type hints, `Optional`, `Union`, basic `mypy` awareness

**Django / DRF**
- ORM: `select_related` vs `prefetch_related`, N+1 query problem (you fixed this at CyRisk — have that story ready)
- QuerySet laziness, `.values()` vs `.values_list()` vs full objects
- Migrations: how they work, squashing, data migrations vs schema migrations
- Django signals — what they're for, why they're often discouraged (implicit coupling)
- Middleware — request/response cycle, where auth/logging hooks in
- DRF: serializers (validation, `SerializerMethodField`), viewsets vs generic views, permission classes, throttling
- Authentication: JWT (you did this at Mevrik DCX — multi-tenant JWT), session vs token auth
- Celery + Redis: task queues, retries, idempotency, periodic tasks (Mevrik DCX experience)
- Caching strategies: query caching, Redis caching, cache invalidation
- Testing: `pytest-django`, fixtures, factory patterns, mocking external calls

**Be ready to whiteboard/code cold:**
- Design a Django model for a small domain (e.g., "design models for an order/inventory system")
- Write a DRF endpoint with validation and permission checks
- Spot and fix an N+1 query in a given view
- Write a raw SQL query with a join + aggregation from a schema they give you

---

## 4. SQL review checklist

- `INNER` vs `LEFT`/`RIGHT` vs `FULL OUTER` join — when each applies
- Indexing: when an index helps vs hurts, composite indexes, `EXPLAIN`/`EXPLAIN ANALYZE`
- Normalization (1NF–3NF) and when to deliberately denormalize
- Window functions (`ROW_NUMBER`, `RANK`, `PARTITION BY`) — common in senior-level tests
- Aggregate queries: `GROUP BY` + `HAVING` vs `WHERE`
- Transactions: isolation levels, deadlocks, `SELECT FOR UPDATE`
- Your PostGIS/geospatial experience (Zenrin) is a differentiator — be ready to explain spatial indexing (GiST) if asked, since most candidates won't have this

**Practice:** pick 2–3 LeetCode-style SQL problems (medium difficulty, joins + window functions) and do them without looking anything up, timed to ~10 min each.

---

## 5. AWS crash review (your stated gaps)

You know Lambda, S3, SQS, EC2, Docker well. Spend focused time on:

**ECS (Elastic Container Service)**
- What it is: managed container orchestration (alternative to running your own K8s)
- Fargate vs EC2 launch type — Fargate = serverless containers, no instance management
- Task definitions, services, target groups (usually behind an ALB)
- How it'd fit your experience: "similar to how I deployed with Docker, ECS just adds orchestration/scaling on top"

**Aurora RDS**
- MySQL/PostgreSQL-compatible managed relational DB, but with AWS's own storage layer (faster replication, auto-scaling storage, up to 15 read replicas)
- Aurora Serverless — auto-scaling capacity for variable workloads
- Since you're strong on PostgreSQL, frame it as: "Aurora Postgres is wire-compatible with Postgres, the DBA-facing work is nearly identical — the difference is in replication/failover architecture underneath"

**DynamoDB**
- NoSQL key-value/document store, single-digit ms latency at scale
- Partition key (+ optional sort key), no joins, denormalize by design
- When to use it vs RDS: high-throughput, simple access patterns, don't need relational queries
- Contrast with your PostGIS/relational-heavy background honestly — you'd want to convey you understand *when* to reach for it, not that you're a DynamoDB expert

Don't over-invest here — 30–45 min per service is enough to hold a competent conversation. The JD says "basic knowledge," so depth expectations are low; the risk is having *nothing* to say, not being under-qualified.

---

## 6. System design / architecture prompts to rehearse

Senior-level interviews often include one open-ended design question. Rehearse out loud (not just in your head) for prompts like:

- "Design a backend for a multi-tenant SaaS platform" — you have a real answer: Mevrik DCX (JWT multi-tenant auth, Celery+Redis for background work)
- "How would you design an API that ingests large geospatial datasets?" — Zenrin (S3 → Lambda → Athena async pipeline)
- "How would you scale a Django app that's getting slow under load?" — talk through: query optimization (your CyRisk 30% API improvement story), caching, read replicas, async offload to Celery, horizontal scaling behind a load balancer
- "Walk me through how you'd add RAG-based search to an existing product" — CEC IRTool is a genuinely strong, uncommon answer here (speech-to-text → RAG → structured output, 60% reduction in manual work)

**Prep move:** write 1–2 sentences of STAR-shaped notes (Situation/Task/Action/Result) for each of your 4 key projects so the numbers (30%, 60%) come out fluently, not fumbled.

---

## 7. Questions to ask them (shows seniority + genuine interest)

- What does the existing tech stack look like beyond what's in the JD — monolith or services, current AWS usage?
- What's driving the need for augmented resourcing right now — new project, backlog, team gap?
- What would success look like in the first 90 days?
- Is there an existing test suite / CI setup, or is that something I'd help establish?
- Team size and how a contractor is integrated day-to-day (standups, sprint cadence)?

---

## 8. Logistics for a 90-min test-inclusive session

- Confirm timezone and exact tool/platform beforehand if possible (BJIT recruiter can usually get this)
- Quiet space, stable internet, webcam-ready if video
- Have a scratch environment ready: local Python/Django project you can share-screen and demo from if asked "show me something you built" (Zenrin or CyRisk work if allowed, or a small personal repo)
- Keep this CV open in a second window — you'll want your own numbers/stories at hand

---

## Suggested prep schedule (if interview is ~1 week out)

- **Day 1–2:** Python/Django checklist (§3) — do it by writing code, not just reading
- **Day 2–3:** SQL practice problems (§4) — timed
- **Day 3:** AWS crash review (§5) — ECS, Aurora, DynamoDB
- **Day 4:** System design rehearsal (§6) — say answers out loud, ideally to someone else or recorded
- **Day 5:** Mock interview run-through (ask me to do this interactively — I can play interviewer)
- **Day before:** Light review only, logistics check (§8), sleep

---

*Next step: tell me when to run a mock interview (live Q&A, or a coding/SQL problem set) and I'll drive it interactively.*
