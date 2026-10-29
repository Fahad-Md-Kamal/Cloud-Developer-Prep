---
title: Home
icon: lucide/house
---

# Software Engineering Interview Prep, Start to Staff

**A Living, Multi-Domain Study & Interview Guide**

A full map of software engineering — Frontend, Python, Backend,
Architecture, Microservices & Distributed Systems, Software Testing,
Cyber Security, Database, Cloud & DevOps, AI & LLM, Machine Learning,
Algorithms, and Interview Prep — thirteen domains, 230+ chapters and
still growing, built from real practice sessions rather than a static
checklist.

- Each domain runs from real fundamentals up through senior/staff
  depth — this isn't scoped to one experience level or to backend
  alone.
- Most of it is **language-agnostic** — system design, architecture,
  testing, security, databases, cloud/DevOps, and behavioral prep
  apply whether the primary stack is Python, Go, Ruby, Rust, or a
  frontend framework.
- Python and Django get the deepest, most detailed coverage of any
  track on this site, since that's the author's own specialization and
  current job search — everything else stands on its own.

Hiring itself has changed, too — interviewers now routinely ask how
candidates actually use AI tools day to day, live coding happens with
an AI assistant in the room (not against one), some first-round panels
are run by an adaptive AI interviewer instead of a human, and resumes
increasingly pass through an AI-driven ATS before a person ever reads
them.
[Interviewing in the AI Era](interview-prep/interviewing-in-the-ai-era.md)
covers that layer directly.

## About this book

A living, multi-domain engineering study guide — not a single track
scoped to one role or one experience level.

- Covers the full breadth of a software engineering career: frontend,
  backend, architecture, QA/testing, cyber security, databases, cloud
  & DevOps, AI/LLM, algorithms, and interview prep.
- Each domain starts from real fundamentals (e.g. Manual Testing
  Fundamentals, Cybersecurity for Beginners, what an AI model even is)
  and goes up through senior/staff-level depth (e.g. distributed
  consensus, Terraform in production, the Staff Engineer mindset) — it
  serves someone starting a track from zero just as well as someone
  already deep into one.
- Python and Django get the deepest, most detailed coverage since
  that's the author's own specialization and current job search, but
  that lives in its own dedicated [Python](#python) track rather than
  being baked into the rest of the guide. A Go, Kotlin, Ruby, Rust, or
  frontend engineer gets full value from everything else.

## Who should read this

- Anyone preparing for a software engineering interview, at any level
  from "learning the fundamentals" to Staff Engineer
- Engineers specializing in one domain — frontend, backend, QA,
  security, data, or cloud/DevOps — who want that domain covered in
  real depth, not a shallow survey
- Engineers targeting roles in AI/ML, distributed systems, or
  fullstack platforms
- Technical leads advancing toward Staff Engineer positions
- Python/Django engineers specifically, where this guide's deepest,
  most detailed track lives

## What this covers

- Frontend, backend, and architecture — language-agnostic system
  design, distributed architecture, and microservices at scale, plus a
  deep Python/Django track and Go/Kotlin/React/React
  Native/TypeScript/Angular material
- Software testing and QA, from manual test design through
  property-based and mutation testing
- Cyber security, from a beginner's roadmap through offensive
  security, SecOps, compliance, and AI/LLM-specific security
- Databases and data engineering, cloud/DevOps (a full AWS + Terraform
  + CI/CD ramp plan, including SAA-C03 exam prep), and algorithms/DSA
- AI/LLM integration and conversational agent development, starting
  from "what is a model" for readers with zero prior AI knowledge
- Machine learning, from classical algorithms and model evaluation
  through deep learning fundamentals, MLOps, and ML system design
- Technical leadership and interview mastery, including
  industry-vertical case studies (healthcare, fintech, telecom, energy)

## Current job-search track: Senior Python/Django

Practice work from live sessions lives as "Practice Notes" sections
inside the relevant chapter, not on separate pages:

- Mutable default arguments → [Practical Patterns](python/language-fundamentals/practical-patterns.md#practice-notes-from-live-session)
- `select_related` vs `prefetch_related` → [Django ORM Query Cheat Sheet](python/web-frameworks/django/django-orm.md#practice-notes-from-live-session)
- SQL window functions + practice sandbox → [PostgreSQL for Scale](database/postgresql-for-scale.md#practice-notes-from-live-session)
- Project stories for system-design questions → [Personal Project Stories](interview-prep/project-stories.md)
- Django & DRF in depth (serializers, permissions, auth, signals, migrations, testing, caching) → [Django & DRF Deep Dive](python/web-frameworks/django/django-drf.md)

## Contents

Organized by domain instead of by when each topic was added — each
top-level area one click deep from here.

### Frontend

- [Frontend Fundamentals](frontend/frontend-fundamentals.md)
- [CSS & Styling Frameworks](frontend/css-styling-frameworks.md)
- [CMS Platforms](frontend/cms-platforms.md)
- [AI-Assisted Development Tools & Workflows](frontend/ai-assisted-development.md)
- **JavaScript**
    - [JavaScript & TypeScript Fundamentals](frontend/js-ts/javascript-and-typescript-fundamentals.md) —
      SOLID/cohesion in JS, immutability, currying, `Map` vs. object, the TS type system
    - [React & React Native](frontend/js-ts/react-and-react-native.md) —
      rendering performance, Redux/Immer/RTK Query, the RN bridge architecture
    - [TypeScript & Angular for Backend Leads](frontend/js-ts/typescript-and-angular-for-backend-leads.md)

### Python

This site's deepest, most detailed track, since that's the author's
own specialization and current job search — generic section name on
purpose, covers any Python framework added here later (web, desktop,
or otherwise), not just Django/FastAPI.

- **Language Fundamentals**
    - [Python's Execution Model](python/language-fundamentals/pythons-execution-model.md)
    - [Python Implementations: CPython, PyPy, GraalPy & Beyond](python/language-fundamentals/python-implementations.md) —
      what PyPy's JIT actually speeds up, GraalVM interop, why Jython/IronPython stalled, MicroPython for embedded
    - [Typing & Generics](python/language-fundamentals/typing-and-generics.md)
    - [Syntax Idioms & Expressions](python/language-fundamentals/syntax-idioms-and-expressions.md) —
      conditional expressions, list/dict/set/generator comprehensions,
      the walrus operator, unpacking, `match`/`case`, f-strings
    - [Python Internals & Advanced OOP](python/language-fundamentals/python-internals-and-advanced-oop.md) — descriptors, metaclasses, MRO, dunder-method correctness
    - [Practical Patterns](python/language-fundamentals/practical-patterns.md)
- **Performance & Memory**
    - [Bit Manipulation Basics](python/performance-and-memory/bit-manipulation-basics.md)
    - [Memory & Caching](python/performance-and-memory/memory-and-caching.md)
    - [Data Structures & Their Memory Model](python/performance-and-memory/data-structures-and-memory.md)
    - [Profiling & Optimization](python/performance-and-memory/profiling-and-optimization.md) —
      cProfile/py-spy, tracemalloc, algorithmic complexity, bounding async concurrency
- **Concurrency & Parallelism**
    - [Choosing a Concurrency Model](python/concurrency/choosing-a-concurrency-model.md)
    - [Threading & the GIL](python/concurrency/threading-and-the-gil.md)
    - [AsyncIO Internals](python/concurrency/asyncio-internals.md)
    - [Worker Pools & Backpressure](python/concurrency/worker-pools-and-backpressure.md)
    - [Multiprocessing in Practice](python/concurrency/multiprocessing-in-practice.md)
    - [Capstone: A Concurrent Data Pipeline](python/concurrency/concurrent-data-pipeline-capstone.md)
- **Web Frameworks**
    - [Choosing a Python Web Framework](python/web-frameworks/choosing-a-python-web-framework.md) —
      Django vs. FastAPI vs. Node/Rails/Spring Boot, and when each wins
    - **Django & DRF**
        - [Django ORM Query Cheat Sheet](python/web-frameworks/django/django-orm.md)
        - [Django & DRF Deep Dive](python/web-frameworks/django/django-drf.md) — serializers, permissions,
          auth, signals, migrations, testing, caching
    - **FastAPI**
        - [Routing & Pydantic Validation](python/web-frameworks/fastapi/fastapi-routing-and-validation.md) —
          path/query/body parameters, validators, response models, auto `422`s
        - [Dependency Injection & Background Tasks](python/web-frameworks/fastapi/fastapi-dependency-injection.md)
        - [Auth, Middleware & Lifecycle Events](python/web-frameworks/fastapi/fastapi-auth-and-middleware.md) —
          OAuth2/JWT, security scopes, Starlette middleware ordering, `lifespan` startup/shutdown
        - [Database Integration & Testing](python/web-frameworks/fastapi/fastapi-database-and-testing.md) —
          SQLAlchemy 2.0 async + Alembic, `httpx.AsyncClient`, dependency overrides
        - [Performance & Production Patterns](python/web-frameworks/fastapi/fastapi-performance-patterns.md) —
          connection pooling, WebSockets, ASGI vs. WSGI
- **Odoo**
    - **Framework**
        - [ORM & Recordsets](python/odoo/framework/odoo-orm-and-recordsets.md) —
          recordsets, domains, x2many commands, computed fields, `env`
        - [Views, Actions & QWeb](python/odoo/framework/odoo-views-actions-and-qweb.md) —
          menu → action → view, view inheritance, new expression syntax, QWeb directives
        - [Inheritance & Customization](python/odoo/framework/odoo-inheritance.md) —
          `_inherit` vs `_inherits`, `super()`, XPath view changes, mixins
        - [Mail, Chatter & Activities](python/odoo/framework/odoo-mail-chatter-and-activities.md) —
          `mail.thread`, tracking, email routing and aliases, `activity_schedule`
        - [Security Model](python/odoo/framework/odoo-security.md) —
          `ir.access` rows with domains, multi-company, `sudo()`
        - [Automation & Server Actions](python/odoo/framework/odoo-automation-and-server-actions.md) —
          triggers, before/after filters, how rules patch `write`, rule vs. code
        - [Data Files, Sequences & Translations](python/odoo/framework/odoo-data-sequences-and-translations.md) —
          `noupdate`, `ir.sequence` (standard vs. no-gap), `.po` files
        - [Performance & Testing](python/odoo/framework/odoo-performance-and-testing.md) —
          prefetching, N+1, `read_group`, `TransactionCase`, `Form`
        - [Upgrades & Migration Scripts](python/odoo/framework/odoo-upgrades-and-migrations.md) —
          pre/post/end scripts, the exact upgrade order, hooks, upgrading custom modules
        - [Configuration & Deployment](python/odoo/framework/odoo-configuration-and-deployment.md) —
          `odoo.conf`, workers and limits, `proxy_mode`, what to check before going live
    - **Core Apps Flow**
        - [Sales to Cash](python/odoo/core-apps/odoo-sales-to-cash-flow.md) —
          bridge modules, hook methods, confirm → delivery → invoice, traced in the source
        - [Inventory Internals](python/odoo/core-apps/odoo-inventory-internals.md) —
          moves vs. quants, stock rules, reservation, what validate really does
        - [Accounting Internals](python/odoo/core-apps/odoo-accounting-internals.md) —
          `account.move`, journal items, balance check, posting, reconciliation
        - [Purchase to Pay](python/odoo/core-apps/odoo-purchase-to-pay-flow.md) —
          `_run_buy`, PO merging, approval, receipt, vendor bill
        - [Manufacturing Internals](python/odoo/core-apps/odoo-manufacturing-internals.md) —
          BoM vs. MO, `_run_manufacture`, multi-level shortages, mark as done
        - [Point of Sale Internals](python/odoo/core-apps/odoo-point-of-sale-internals.md) —
          offline sync with `sync_from_ui`, sessions, one combined entry at close
    - [Build an Odoo App: The Step-by-Step Plan](python/odoo/build-an-odoo-app-plan.md) —
      a Service Desk build in three parts (13 core steps, 7 design steps, 6 platform steps), each with a check and the page to read first
- **Python Standard Library**
    - [Pathlib & File Operations](python/standard-library/pathlib-and-file-operations.md)
    - [Collections & Itertools](python/standard-library/collections-and-itertools.md)
    - [Configuration & CLI Tools](python/standard-library/config-and-cli-tools.md)
    - [Functools: Caching & Decorators](python/standard-library/functools-patterns.md)
    - [Regex & Text Processing](python/standard-library/regex-and-text-processing.md)

### Backend

Backend language tracks beyond Python — earlier-stage tracks for
engineers coming from Go or Kotlin specifically, where Python's own
track (above) is this site's deepest.

**Go**

- [Go Fundamentals: Types, Structs & Interfaces](backend/go/go-fundamentals.md) —
  slices vs. arrays, structs and methods, interfaces as implicit/structural typing
- [Concurrency in Go: Goroutines, Channels & the Scheduler](backend/go/go-concurrency.md) —
  the M:N scheduler, channels, worker pools/fan-out-fan-in, `context`
- [Go Memory Management & Performance](backend/go/go-memory-and-performance.md) —
  escape analysis, the garbage collector, value vs. pointer semantics, `pprof`
- [Building Web Services & Microservices in Go](backend/go/go-web-services-and-microservices.md) —
  `net/http`, when gin/echo earn their place, middleware, graceful shutdown
- [Testing in Go](backend/go/go-testing.md) —
  table-driven tests, `testify`, benchmarks, native fuzzing
- [Go Standard Library Essentials](backend/go/go-standard-library.md) —
  `io.Reader`/`io.Writer`, `encoding/json`, file I/O, the `time` format gotcha

**Kotlin**

- [Kotlin for JVM Backend Interviews](backend/kotlin/kotlin-for-jvm-interviews.md) —
  coroutines vs. Python AsyncIO, Kotlin vs. Java

### Architecture

Framework-agnostic principles, system design methodology, and
technical leadership — apply regardless of which language or framework
sits underneath.

- **Code Quality & Engineering Practices**
    - [SOLID Principles](architecture/solid-principles.md)
    - [Cohesion & Coupling](architecture/cohesion-and-coupling.md)
    - [Design Patterns](architecture/design-patterns.md)
    - [Clean Code Practices](architecture/clean-code-practices.md)
    - [Refactoring Legacy Systems](architecture/refactoring-legacy-systems.md)
    - [Version Control & Git Workflows](architecture/version-control-and-git-workflows.md)
- **APIs**
    - [How the Internet Moves Files](architecture/how-the-internet-moves-files.md) —
      TCP segmentation, multipart uploads, chunked transfer, Range requests
    - [API Paradigms & Patterns](architecture/api-paradigms-and-patterns.md)
    - [REST Deep Dive](architecture/rest-deep-dive.md)
    - [GraphQL Deep Dive](architecture/graphql-deep-dive.md)
    - [gRPC Deep Dive](architecture/grpc-deep-dive.md)
    - [API Production Readiness](architecture/api-production-readiness.md)
- **Authentication, Authorization, and Security**
    - [Authentication Patterns](architecture/authentication-patterns.md) —
      11 mechanisms compared (sessions, JWT, OAuth2/OIDC, SAML, API
      keys, mTLS, HMAC signing, Kerberos, WebAuthn/passkeys, magic
      links), then JWT/OAuth2/MFA/SSO in depth
    - [Authorization Patterns](architecture/authorization-patterns.md)
    - [Security Hardening](architecture/security-hardening.md)
- **System Design Interviews**
    - [System Design Methodology](architecture/system-design-methodology.md)
    - [Architecture Diagramming & Communication](architecture/architecture-diagramming-and-communication.md) — includes the C4 model
    - [Common System Design Patterns](architecture/system-design-patterns.md)
    - [Scalability Case Studies](architecture/scalability-case-studies.md) — includes CAP and PACELC
    - [Event-Driven Architecture: CQRS & the Saga Pattern](architecture/event-driven-architecture.md) —
      splitting reads from writes, and compensating transactions across services

### Microservices & Distributed Systems

Service-to-service concerns at scale — language-agnostic, the same
way Architecture above is, just specifically about systems made of
many communicating services rather than any single one.

- **Microservices & Messaging**
    - [Service Boundaries & Architecture](distributed-systems/service-boundaries-and-architecture.md)
    - [Messaging: Kafka, Redis & AWS](distributed-systems/messaging-kafka-redis-and-aws.md) —
      includes SNS/SQS, the fan-out pattern, and idempotent event handling
    - [Inter-Service Communication](distributed-systems/inter-service-communication.md)
- **Distributed System Design**
    - [Fault Tolerance Patterns](distributed-systems/fault-tolerance-patterns.md)
    - [Load Balancing & Auto-Scaling](distributed-systems/load-balancing-and-autoscaling.md)
    - [Consistency & Consensus](distributed-systems/consistency-and-consensus.md)
    - [Data & Capacity Scaling](distributed-systems/data-and-capacity-scaling.md)
- **API Gateway & Resilience**
    - [API Gateway Architecture](distributed-systems/api-gateway-architecture.md)
    - [Rate Limiting Strategies](distributed-systems/rate-limiting-strategies.md)
    - [Circuit Breakers, Retries & Bulkheads](distributed-systems/circuit-breakers-retries-and-bulkheads.md)
    - [API Management & Versioning](distributed-systems/api-management-and-versioning.md)
    - [Kong API Gateway](distributed-systems/kong-api-gateway.md) — the concrete product behind "API Gateway (Kong)" in a JD
- **Observability**
    - [Structured Logging](distributed-systems/structured-logging.md)
    - [Metrics & Prometheus](distributed-systems/metrics-and-prometheus.md)
    - [Distributed Tracing](distributed-systems/distributed-tracing.md)
    - [Dashboards & Alerting](distributed-systems/dashboards-and-alerting.md)

### Software Testing

Covers the field broadly enough for someone starting a testing career,
not just a developer's testing literacy — manual test design, the
fuller testing-type vocabulary, non-functional testing, and QA tooling,
alongside test doubles, TDD, flakiness, and the less commonly taught
automation techniques (property-based, mutation, and contract testing)
that catch what example-based tests and coverage percentages
structurally can't.

- [Manual Testing Fundamentals: Test Case Design & Bug Reports](testing/manual-testing-fundamentals.md) —
  equivalence partitioning, boundary values, decision tables, writing a bug report
- [Testing Types & Levels: Smoke, Sanity, Regression & UAT](testing/testing-types-and-levels.md) —
  black-box/white-box/gray-box, and the type vocabulary beyond unit/integration/E2E
- [Testing Strategy: The Pyramid, the Trophy & What Not to Test](testing/testing-strategy-pyramid-and-trophy.md) —
  pyramid vs. trophy, what coverage percentage actually misses
- [Test Doubles & TDD](testing/test-doubles-and-tdd.md) — mock vs.
  stub vs. fake vs. spy, the red-green-refactor cycle
- [Non-Functional Testing: Performance, Security & Accessibility](testing/non-functional-testing.md) —
  load/stress/soak testing, OWASP-style security testing, WCAG accessibility
- [Flaky Tests & CI Test Strategy](testing/flaky-tests-and-ci-strategy.md) —
  the four real causes of flakiness, and structuring CI's test stage
- [QA Tools & the Path from Manual to Automation (SDET)](testing/qa-tools-and-the-sdet-path.md) —
  TestRail/Jira, Postman/API testing, and the realistic manual-to-automation path
- [Property-Based Testing](testing/property-based-testing.md) —
  Hypothesis, shrinking, and when a property actually exists to state
- [Mutation Testing](testing/mutation-testing.md) — why mutation score
  is a stronger signal than line coverage
- [Contract Testing](testing/contract-testing.md) — catching the gap
  between two services that each pass their own tests
- [Integration & End-to-End Testing in Practice](testing/integration-and-e2e-testing.md) —
  test database isolation, parallel test data, and scoping E2E to
  critical journeys
- [Testing Tools & Frameworks by Type](testing/testing-tools-and-frameworks.md) —
  pytest/JUnit/Jest, Selenium/Playwright/Cypress, Cucumber/Behave,
  REST Assured, Appium, visual regression, organized by test type
- [Testing AI & LLM Applications](testing/testing-ai-and-llm-applications.md) —
  testing non-deterministic output, hallucination rate, prompt
  regression testing, adversarial/red-team testing, bias testing

### Cyber Security

Existing security content elsewhere on this site (AuthN/AuthZ, database
breach prevention, AWS-specific security services) is all application
security — secure coding and prevention. This track is the broader
field: cryptography and network security fundamentals, offensive
security methodology, security operations, identity, compliance
frameworks, cloud security posture, the certification/career path, and
AI/LLM-specific security — cross-linking into the existing AppSec
content rather than duplicating it.

**Fundamentals**

- [Cybersecurity for Beginners: The Learning Roadmap](security/cybersecurity-for-beginners-roadmap.md) —
  the prerequisites (networking, Linux, scripting), the recommended
  order through this track, and the single biggest beginner mistake
- [Network Security Fundamentals](security/network-security-fundamentals.md) —
  stateful vs. stateless firewalls, zero trust, ARP/DNS spoofing, nmap & Wireshark
- [Cryptography Fundamentals](security/cryptography-fundamentals.md) —
  symmetric vs. asymmetric, the TLS handshake, digital signatures, why bcrypt not SHA-256
- [The OWASP Top 10, In Depth](security/owasp-top-10-in-depth.md) —
  the canonical map, with insecure design, vulnerable components, and SSRF covered in full

**Offensive & Defensive Operations**

- [Cybersecurity Tools by Category](security/cybersecurity-tools-by-category.md) —
  Nessus/OpenVAS, Burp Suite/ZAP, Metasploit, Hashcat, Splunk/ELK, Autopsy/Volatility
- [Offensive Security & Penetration Testing Methodology](security/offensive-security-and-pentesting.md) —
  recon through reporting, red/blue/purple team, bug bounty programs
- [Security Operations: SIEM, Logging & Incident Response](security/security-operations-and-incident-response.md) —
  log correlation, and the full incident response lifecycle
- [Threat Detection & Monitoring](security/threat-detection-and-monitoring.md) —
  security audit logging, anomaly detection & behavior analytics, vulnerability management

**Identity & Human-Factor Threats**

- [Identity Security: Zero Trust & Privileged Access](security/identity-security-zero-trust-and-pam.md) —
  continuous verification, MFA method strength, PAM and just-in-time access
- [Malware, Phishing & Social Engineering](security/malware-phishing-and-social-engineering.md) —
  virus/worm/trojan/ransomware mechanics, why phishing works

**Governance & Cloud Security**

- [Compliance & Security Frameworks](security/compliance-and-security-frameworks.md) —
  SOC 2, ISO 27001, GDPR, PCI-DSS
- [Cloud Security Fundamentals](security/cloud-security-fundamentals.md) —
  shared responsibility, CSPM, why most cloud incidents are misconfiguration

**Career & Case Studies**

- [Security Certifications & Career Path](security/security-certifications-and-career-path.md) —
  Security+, OSCP/CEH, GCIH/GCIA, CISSP, and which track each fits
- [Real-World Breach Case Studies (2023–2025)](security/real-world-breach-case-studies.md) —
  MOVEit, Change Healthcare, the Snowflake customer campaign, Microsoft
  Storm-0558, and 23andMe, each mapped to the mechanism that caused it

**AI Security**

- [AI & LLM Security](security/ai-and-llm-security.md) —
  the OWASP Top 10 for LLM Applications, excessive agency, RAG corpus poisoning, model theft
- [AI-Assisted Security Vulnerability Audits](security/ai-assisted-security-vulnerability-audit.md) —
  a reusable prompt covering the OWASP Top 10 plus token/auth-specific
  attack scenarios, to run against your own code

### Database

Everything database- and data-engineering-related in one place —
database architecture, fundamentals & security, web crawling/pipelines,
and distributed big-data compute.

**Database Architecture for Scale**

- [Database Types: The Decision Framework](database/database-types-overview.md) —
  relational, document, key-value, wide-column, graph, vector,
  time-series, search-engine, and NewSQL, each explained by the
  mechanism that fits its use case
- [PostgreSQL for Scale](database/postgresql-for-scale.md)
- [MongoDB for Scale](database/mongodb-for-scale.md)
- [Elasticsearch Architecture](database/elasticsearch-architecture.md)
- [Redis as a Database](database/redis-as-a-database.md) — beyond
  caching: persistence, data structures, when it's the primary store
- [Graph Databases (Neo4j)](database/graph-databases-neo4j.md) —
  index-free adjacency and when relationship traversal earns its cost
- [Time-Series Databases](database/time-series-databases.md) —
  InfluxDB, TimescaleDB, Prometheus, and why Postgres alone struggles here
- [Wide-Column Stores (Cassandra)](database/wide-column-stores-cassandra.md) —
  the LSM-tree write path, partition keys, tunable consistency
- [NewSQL: Distributed SQL](database/newsql-distributed-sql.md) —
  Raft consensus, and how it gets ACID plus horizontal scale
- [Cross-Store Architecture Patterns](database/cross-store-architecture-patterns.md)

**Fundamentals**

- [SQL & Relational Data Modeling](database/sql-data-modeling-fundamentals.md) —
  normalization, keys, JOINs, denormalization, DB-level constraints, MySQL-specific notes
- [Database Security & Breach Prevention](database/database-security-and-breach-prevention.md) —
  network isolation, PII encryption, secure backup handling

**Web Crawling & Pipelines**

- [Web Crawling at Scale](database/web-crawling-at-scale.md) —
  why some pages need a real browser, Selenium vs. Playwright's
  actual protocol difference, anti-bot fingerprinting
- [HTML Parsing & Data Pipelines](database/html-parsing-and-data-pipelines.md) —
  the DOM tree, BeautifulSoup vs. lxml, CSS selectors vs. XPath
- [Distributed Crawling Architecture](database/distributed-crawling-architecture.md) —
  Celery, Kafka, Ray, Bloom-filter frontiers, visibility timeouts
- [Data Cleaning, Normalization & Deduplication](database/data-cleaning-and-deduplication.md) —
  MinHash and LSH for near-duplicate detection at scale

**Big Data & Distributed Compute**

- [ETL vs. ELT: Data Pipeline Architecture](database/etl-vs-elt.md) —
  the one real difference, why ELT became viable, and when ETL still wins
- [Apache Spark & PySpark](database/spark-pyspark.md)
- [Databricks & Delta Lake](database/databricks-delta-lake.md)
- [Data Preprocessing: Pandas & NumPy](database/data-preprocessing-pandas-numpy.md)
- [Large-Scale Report Generation](database/large-scale-report-generation.md) —
  memory-efficient PDF/XLSX export from 10+GB source data

### Cloud & DevOps

A hands-on AWS/DevOps ramp plan — real CLI commands, a real Terraform
codebase, and a real Jenkins pipeline deploying a real application,
mistakes and fixes kept in as teaching material.

- [DevOps Principles & Delivery](cloud-devops/devops-principles-and-delivery.md) —
  The Three Ways, DORA metrics, SLOs/error budgets, deployment strategies
- [Linux Fundamentals for DevOps](cloud-devops/linux-fundamentals-for-devops.md) —
  processes/signals, systemd, disk/filesystem and networking troubleshooting
- [AWS Accounts & IAM](cloud-devops/aws-accounts-and-iam.md)
- **AWS Security & Governance**
    - [Encryption, Secrets & Identity Federation](cloud-devops/kms-secrets-and-cognito.md)
    - [AWS Organizations & Control Tower](cloud-devops/aws-organizations-and-control-tower.md)
    - [Security & Compliance Services](cloud-devops/aws-security-and-compliance-services.md)
    - [AWS Systems Manager](cloud-devops/aws-systems-manager.md)
- **AWS Networking (VPC)**
    - [VPC & Subnet Design](cloud-devops/aws-networking-vpc.md)
    - [Security Groups, Gateways & Flow Logs](cloud-devops/vpc-security-groups-and-flow-logs.md)
    - [VPC Connectivity & Hybrid Networking](cloud-devops/vpc-connectivity-and-hybrid-networking.md)
    - [CloudFront: Content Delivery & Edge Caching](cloud-devops/cloudfront-cdn.md)
- [Caching Layers & Global Accelerator](cloud-devops/caching-layers-and-global-accelerator.md)
- **Compute & Scaling**
    - [EC2, AMIs & Launch Templates](cloud-devops/compute-and-scaling.md)
    - [EC2 Instance Families, Purchasing Options & Placement Groups](cloud-devops/ec2-instance-types-and-purchasing-options.md)
    - [Auto Scaling Groups & Scaling Policies](cloud-devops/auto-scaling-groups.md)
- [Load Balancing & DNS](cloud-devops/load-balancing-and-dns.md) — includes ALB, NLB & Gateway Load Balancer
- **Databases**
    - [RDS Operations](cloud-devops/databases-rds-operations.md)
    - [Aurora & RDS Proxy](cloud-devops/aurora-and-rds-proxy.md)
    - [DynamoDB & ElastiCache](cloud-devops/dynamodb-and-elasticache.md)
- **Storage**
    - [S3, Secrets & Observability](cloud-devops/storage-and-observability.md) — includes CloudWatch vs. Prometheus/Grafana/Nagios
    - [EBS, EFS, FSx & Data Transfer](cloud-devops/storage-options-ebs-efs-fsx.md)
- [Cost Management: Cost Explorer, CUR & Data Transfer](cloud-devops/cost-management-tools.md)
- **Containers**
    - [Docker: Production Container Images](cloud-devops/docker-production-images.md)
    - [Container Orchestration: ECS & EKS](cloud-devops/container-orchestration-ecs-eks.md)
    - [Helm & GitOps](cloud-devops/helm-and-gitops.md)
- [Serverless & Managed Compute](cloud-devops/serverless-and-managed-compute.md) — Lambda limits, Elastic Beanstalk, AWS Batch, Step Functions
- [Messaging & Event-Driven Services](cloud-devops/messaging-and-event-driven-services.md) — SQS, SNS, EventBridge, Kinesis, Amazon MQ
- [Data Analytics: Glue, Lake Formation & EMR](cloud-devops/data-analytics-glue-lake-formation-emr.md)
- [Disaster Recovery Strategies & AWS Backup](cloud-devops/disaster-recovery-strategies.md) — Backup & Restore, Pilot Light, Warm Standby, Multi-Site Active/Active
- **Terraform (IaC)**
    - [Terraform Fundamentals](cloud-devops/terraform-fundamentals.md)
    - [Iteration, Modules & Advanced HCL](cloud-devops/terraform-modules-and-advanced-hcl.md)
    - [State, Environments & Regions](cloud-devops/terraform-state-environments-and-regions.md)
    - [Building a Platform in Code](cloud-devops/terraform-building-a-platform.md)
    - [EKS, Worked Examples & Lambda](cloud-devops/terraform-eks-and-lambda.md)
    - [Operating Terraform in Production](cloud-devops/terraform-operating-in-production.md)
- **CI/CD & Jenkins**
    - [Jenkins: Setup & Pipeline Configuration](cloud-devops/jenkins-setup-and-pipeline-configuration.md)
    - [Jenkins: Production Deployment Pipelines](cloud-devops/jenkins-production-deployment-pipelines.md)
    - [Jenkins: Security, Hardening & Production Patterns](cloud-devops/jenkins-security-hardening-and-production-patterns.md)
    - [GitLab CI/CD](cloud-devops/gitlab-ci.md)
    - [CI/CD & Progressive Delivery](cloud-devops/cicd-and-progressive-delivery.md) — includes diagnosing a green pipeline with a broken production deploy
- **Ansible (Configuration Management)**
    - [Ansible Fundamentals](cloud-devops/ansible-fundamentals.md)
    - [Handlers, Templates, Roles & Vault](cloud-devops/ansible-handlers-templates-roles-vault.md)
    - [Collections, Execution Environments & Automation Platform](cloud-devops/ansible-collections-and-automation-platform.md)
- [SAA-C03 Exam Prep: Domain Review Index](cloud-devops/saa-c03-exam-prep-index.md) —
  everything above, organized by the exam's 4 scored domains instead of
  by study week
- [SAA-C03 Practice Quiz](cloud-devops/saa-c03-practice-quiz.md) — 16
  self-made questions by domain, plus AWS's official 20-question
  practice set

### AI & LLM

**Fundamentals**

- [AGI & ASI: The Intelligence Spectrum](ai-llm/agi-and-asi.md) — narrow
  AI vs. AGI vs. ASI, how we'd measure AGI, and the alignment problem
- [Types of AI Models & What They Actually Cost](ai-llm/types-of-ai-models-and-their-cost.md) —
  genuinely starts from zero: what a model/training/a parameter even
  is, then classification vs. generation vs. embeddings, and why cost
  tracks output length, not task difficulty
- [How LLMs Actually Work: Tokens, Attention & Generation](ai-llm/how-llms-actually-work.md) —
  tokenization, self-attention, autoregressive sampling, why context
  windows are a hard limit
- [Fine-Tuning & the Model Training Lifecycle](ai-llm/fine-tuning-and-training-lifecycle.md) —
  pretraining, SFT, RLHF/DPO, LoRA, and when to actually fine-tune
- [Why LLMs Hallucinate](ai-llm/why-llms-hallucinate.md) — the mechanism,
  and how to actually reduce it in production

**Multimodal & Local Deployment**

- [Multimodal Models](ai-llm/multimodal-models.md) — how image/audio
  input fits into the same transformer mechanism as text
- [Quantization & Running Models Locally](ai-llm/quantization-and-local-models.md) —
  GGUF, llama.cpp, Ollama, and self-hosting trade-offs

**LLM APIs & Gateway**

- [LLM APIs & Providers](ai-llm/llm-apis-and-providers.md) — provider selection, auth, cost, async clients
- [LLM Gateway & Multi-Provider Integration](ai-llm/llm-gateway-multi-provider.md) — LiteLLM, provider fallback
- [LLM Response Caching](ai-llm/llm-response-caching.md) — semantic & hybrid caching

**Agents & Prompting**

- [Prompt Engineering & Context Management](ai-llm/prompt-engineering.md)
- [Agentic AI Fundamentals](ai-llm/agentic-ai-fundamentals.md) — the agent loop, and how to actually build agents with API access
- [Model Context Protocol (MCP)](ai-llm/model-context-protocol.md) —
  the standard behind Claude Code's own tool/resource access
- [Designing Adaptive AI Interview Systems](ai-llm/adaptive-ai-interview-systems.md) —
  LLM-driven question generation, answer scoring, and Computerized Adaptive Testing
- [Evaluating LLM Output at Scale](ai-llm/evaluating-llm-output.md) —
  benchmarks, golden sets, and LLM-as-judge pitfalls
- [Multi-Agent Systems](ai-llm/multi-agent-systems.md) — coordination topologies, debugging
- [Autogen: Multi-Agent Orchestration](ai-llm/autogen-orchestration.md)

**RAG & Retrieval**

- [Embeddings & Semantic Search](ai-llm/embeddings-semantic-search.md)
- [RAG & Vector Databases](ai-llm/rag-and-vector-databases.md)
- [RAG Project Ideas: Beginner to Production](ai-llm/rag-project-ideas.md) —
  a progression of build projects, from a single-PDF bot to a
  production-grade multi-tenant assistant

**LangChain**

- [LangChain Agents](ai-llm/langchain-agents.md) — agent types, tools, memory, LCEL
- [LangChain Ecosystem: LangGraph, LangSmith, LangServe](ai-llm/langchain-ecosystem.md) — plus LangCache

### Machine Learning

The classical ML body of knowledge — distinct from the LLM/agent-
focused material in AI & LLM above, and the skill set most "ML
Engineer"/"Data Scientist" interviews actually test.

**Foundations**

- [Supervised, Unsupervised & Reinforcement Learning](machine-learning/supervised-unsupervised-and-reinforcement-learning.md) —
  the three learning paradigms, and the bias-variance tradeoff underneath almost every technique that follows
- [Model Evaluation & Validation](machine-learning/model-evaluation-and-validation.md) —
  train/val/test splits, precision/recall/F1, ROC-AUC, MAE vs. RMSE

**ML Algorithms**

- [Classical ML: Regression, Trees & Ensembles](machine-learning/classical-ml-regression-trees-and-ensembles.md) —
  linear/logistic regression, decision trees, random forests, gradient boosting
- [Classical ML: Clustering, SVM & Dimensionality Reduction](machine-learning/classical-ml-clustering-svm-and-dimensionality-reduction.md) —
  k-means, DBSCAN, the kernel trick, PCA vs. t-SNE/UMAP
- [Deep Learning Fundamentals: Neural Networks Before Transformers](machine-learning/deep-learning-fundamentals.md) —
  backpropagation, vanishing gradients, CNNs, RNNs/LSTMs

**Model Building**

- [Feature Engineering for ML](machine-learning/feature-engineering-for-ml.md) —
  missing data, encoding, the data leakage trap, feature selection
- [Regularization & Hyperparameter Tuning](machine-learning/regularization-and-hyperparameter-tuning.md) —
  L1 vs. L2, dropout, cross-validation, grid vs. random vs. Bayesian search

**Production & MLOps**

- [MLOps: Experiment Tracking, Model Registry & CI/CD](machine-learning/mlops-experiment-tracking-and-deployment.md) —
  MLflow, model registries, shadow/canary deployment, batch vs. real-time serving
- [Model Monitoring & Drift Detection in Production](machine-learning/model-monitoring-and-drift-detection.md) —
  data drift vs. concept drift, what to monitor without waiting for labels
- [ML System Design Interviews](machine-learning/ml-system-design-interviews.md) —
  the ML-specific framework on top of regular system design, worked through a recommendation system

### Algorithms

A parallel-track universal skill, not backend-architecture-specific —
usually practiced alongside everything else, not saved for last.

- [Big-O & the Hardware Underneath It](dsa/big-o-and-memory-hardware.md) —
  cache lines, memory locality, virtual memory
- [How Interpreters & Compilers Actually Work](dsa/how-interpreters-and-compilers-work.md) —
  lexing/parsing/AST, bytecode, JIT compilation (animated), the CPU's fetch-decode-execute cycle
- [Computer Architecture & How a CPU Actually Processes Instructions](dsa/computer-and-cpu-architecture.md) —
  registers/ALU/control unit, pipelining (animated), branch prediction
  and Spectre/Meltdown, CISC vs. RISC, why multi-core is real hardware
  parallelism
- [Blind 75, Grind 75 & NeetCode 150](dsa/blind-75-grind-75-neetcode-150.md)
- [Visualizing Algorithms with AI](dsa/ai-assisted-algorithm-visualization.md) —
  a reusable prompt for generating a NeetCode-style step-through visualizer for your own solution
- [Arrays & Hashing](dsa/2-1-arrays-and-hashing.md)
- [Two Pointers](dsa/2-2-two-pointers.md)
- [Sliding Window](dsa/2-3-sliding-window.md)
- [Stack](dsa/2-4-stack.md)
- [Binary Search](dsa/2-5-binary-search.md)
- [Linked List](dsa/2-6-linked-list.md)
- [Trees](dsa/2-7-trees.md)
- [Tries / Prefix Tree](dsa/2-8-tries-prefix-tree.md)
- [Heap / Priority Queue](dsa/2-9-heap-priority-queue.md)
- [Backtracking](dsa/2-10-backtracking.md)
- [Graphs](dsa/2-11-graphs.md)
- [Dynamic Programming](dsa/2-12-dynamic-programming.md)
- [Design](dsa/2-13-design.md)

### Interview Prep

The capstone — behavioral prep, mock interviews, resume polish, project
stories for behavioral/system-design questions, domain-vertical deep
dives, and a final countdown review. Comes last: it's what you do right
before the interview, after the technical material above.

- [Behavioral Interview Prep: STAR, Leadership & Conflict](interview-prep/behavioral-interview-prep.md) —
  the STAR method precisely enough to use, plus disagreement/failure story framing
- [Leadership for Engineers](interview-prep/leadership-mentoring-and-team-scaling.md) —
  mentoring, reviews, team scaling (parked outline, not yet fleshed out)
- [Staff Engineer Mindset](interview-prep/staff-engineer-mindset.md) —
  strategy, influence without authority, vision (parked outline, not yet fleshed out)
- [Interviewing in the AI Era](interview-prep/interviewing-in-the-ai-era.md)
- [Take-Home & Live-Coding Exercises](interview-prep/take-home-and-live-coding-exercises.md) —
  real, scoped coding tasks recalled from interviews, e.g. a weather CLI
- [Resume, GitHub & Case Study Optimization](interview-prep/resume-github-and-case-study-optimization.md) —
  impact bullets, a GitHub profile that signals skill, turning a project into a readable case study
- [Validating Your Skill Level](interview-prep/validating-your-skill-level.md) —
  backing up a self-rated "expert" claim with something external
- [Final Review — The 30-Day Countdown](interview-prep/final-review-30-day-countdown.md) —
  a customizable week-by-week template across this site's actual current domains
- [Personal Project Stories](interview-prep/project-stories.md) — real project STAR stories
  for system-design/behavioral questions
- [Meeting-Intelligence System Case Study](interview-prep/meeting-intelligence-case-study.md)
- **Healthcare Interoperability** — genuinely healthcare-specific
  content from a real healthcare-interoperability-focused JD, a real
  domain gap, not yet an active application track
    - [FHIR R4](interview-prep/healthcare/fhir-r4.md)
    - [SMART on FHIR & Bulk Data Export](interview-prep/healthcare/smart-on-fhir-and-bulk-data.md) —
      the OAuth2 app-authorization layer and population-scale `$export`
    - [HL7 v2.x & C-CDA](interview-prep/healthcare/hl7-ccda.md)
    - [Healthcare Terminology](interview-prep/healthcare/healthcare-terminology.md) — SNOMED CT, LOINC, RxNorm
    - [Patient Matching & MPI](interview-prep/healthcare/patient-matching-mpi.md)
    - [HIPAA & PHI-Safe Engineering](interview-prep/healthcare/hipaa-phi-safety.md)
- **Fintech Interoperability** — the direct fintech parallel to
  Healthcare Interoperability above, same shape: a modern API standard,
  its auth/consent layer, legacy message rails, data taxonomy, entity
  resolution, and compliance engineering
    - [Open Banking & Financial Data APIs](interview-prep/fintech/open-banking-and-financial-apis.md) —
      FDX/PSD2, and what it replaced (screen scraping)
    - [FAPI & Consent Authorization Flows](interview-prep/fintech/fapi-and-consent-flows.md) —
      the stricter OAuth2 profile, token binding via mutual TLS
    - [Legacy Payment Rails: ISO 8583 & SWIFT MT/MX](interview-prep/fintech/iso8583-and-swift-mt-mx.md)
    - [Financial Data Taxonomy](interview-prep/fintech/financial-data-taxonomy.md) — MCC, ISO 4217, ISO 20022 codes
    - [Entity Resolution: KYC, AML & Beneficial Ownership](interview-prep/fintech/kyc-aml-entity-resolution.md) —
      why this becomes a graph problem, and why the precision/recall tuning flips vs. healthcare
    - [PCI-DSS & Financial Data Safety Engineering](interview-prep/fintech/pci-dss-and-financial-data-safety.md) —
      tokenization vs. encryption, the never-store-SAD rule
- **Telecom Interoperability** — same shape again: TM Forum/CAMARA APIs,
  SS7's actual role in SIM-swap/SMS-interception attacks, and fraud-ring
  detection as a graph problem
    - [TM Forum Open APIs](interview-prep/telecom/tm-forum-open-apis.md) —
      the API catalog, plus CAMARA's network-capability APIs
    - [Authorization for Telecom APIs: CIBA & Number Verification](interview-prep/telecom/telecom-api-authorization.md)
    - [Legacy Signaling: SS7 & Diameter](interview-prep/telecom/ss7-and-diameter.md) —
      how cross-carrier call routing actually works, and why SS7 has no built-in authentication
    - [Telecom Data Taxonomy](interview-prep/telecom/telecom-data-taxonomy.md) —
      CDRs, MCC/MNC (not fintech's MCC), E.164
    - [Entity Resolution: Subscriber Identity, SIM Swap & Fraud Rings](interview-prep/telecom/subscriber-identity-and-fraud-resolution.md)
    - [Telecom Compliance: CALEA, Number Portability & Data Retention](interview-prep/telecom/telecom-compliance.md)
- **Energy & Utilities Interoperability** — same shape once more: Green
  Button, why Modbus/DNP3 have zero built-in security by original
  design, and NERC CIP's physical-consequence risk model
    - [Green Button & Energy Data APIs](interview-prep/energy/green-button-and-energy-apis.md)
    - [Green Button Connect: Authorization & Consent](interview-prep/energy/green-button-connect-authorization.md)
    - [Legacy Industrial Protocols: Modbus, DNP3 & SCADA](interview-prep/energy/modbus-dnp3-and-scada.md) —
      why these protocols have no authentication at all, not just old age
    - [Energy Data Taxonomy](interview-prep/energy/energy-data-taxonomy.md) —
      interval reads, rate schedules, billed vs. AMI data
    - [Entity Resolution: Grid Assets & Customer-Meter Matching](interview-prep/energy/grid-asset-entity-resolution.md) —
      grid topology as a graph problem, outage correlation as a validation loop
    - [Energy & Utilities Compliance: NERC CIP](interview-prep/energy/energy-compliance.md)

## A note on names

[Personal Project Stories](interview-prep/project-stories.md) uses generic project labels
("geospatial data platform client", "cybersecurity risk platform
client") left over from when this content lived on a public site. The
repo is private now, so these could be restored to the real project
names if useful — ask if you want that
done.
