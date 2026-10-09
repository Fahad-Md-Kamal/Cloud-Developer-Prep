---
title: Home
icon: lucide/house
---

# Engineering for Scale: Backend, AI, and System Design Mastery

**A Comprehensive Interview Preparation Guide** — by Fahad Md Kamal

A living backend/cloud interview-prep guide, built from real practice
sessions rather than a static checklist. Most of it is
**language-agnostic** — system design, data structures & algorithms,
distributed architecture, cloud/DevOps, databases, security, and
behavioral prep apply whether the primary stack is Python, Go, Ruby,
Rust, or anything else. One unified tree — 38 chapters + appendices,
plus a running practice log cross-linked into the specific chapter
each round belongs to.

Hiring itself has changed, too — interviewers now routinely ask how
candidates actually use AI tools day to day, live coding happens with
an AI assistant in the room (not against one), some first-round panels
are run by an adaptive AI interviewer instead of a human, and resumes
increasingly pass through an AI-driven ATS before a person ever reads
them.
[Interviewing in the AI Era](interview-prep/interviewing-in-the-ai-era.md)
covers that layer directly.

!!! warning "Private content — repo must stay private"
    Contains real company names (Lawstronaut, Optimizely, Cefalo). The
    [Meeting-Intelligence System Case Study](interview-prep/meeting-intelligence-case-study.md)
    has been anonymized (no client/project name, no domain-identifying
    details) but the repo should still stay private.

## About this book

A guide for senior backend engineers with 5+ years of experience
targeting Staff/Senior roles, covering system design, distributed
architecture, cloud, AI system integration, and technical leadership
— usable regardless of primary language. Python and Django get the
deepest, most detailed coverage since that's the author's own
specialization and current job search, but that lives inside the
Python subsection of [Backend](#backend) rather than being baked into
the rest of the guide. A Go, Kotlin, Ruby, or Rust engineer gets full
value from everything else and can treat Python as the one subsection
to skim past, or use [Backend](#backend)'s earlier-stage Go/Kotlin
material as the starting point to eventually fill in with their own
language's full track.

## Who should read this

- Senior backend engineers preparing for interviews, in any primary
  language
- Engineers targeting roles in AI/ML, distributed systems, or
  fullstack platforms
- Technical leads advancing toward Staff Engineer positions
- Python/Django engineers specifically, where this guide's deepest,
  most detailed track lives

## What this covers

- System design, distributed architecture, and microservices at scale
  — language-agnostic
- Data structures & algorithms, databases, and cloud/DevOps —
  language-agnostic
- AI/LLM integration and conversational agent development
- A deep Python/Django track, plus Go, Kotlin, and React/React
  Native/TypeScript/Angular material
- Technical leadership and interview mastery

## Study timeline

Originally structured as a 6-month intensive preparation program, each part
building on the previous one.

## Current job-search track: Senior Python/Django

Practice work from live sessions lives as "Practice Notes" sections
inside the relevant chapter, not on separate pages:

- Mutable default arguments → [Practical Patterns](backend/python/practical-patterns.md#practice-notes-from-live-session)
- `select_related` vs `prefetch_related` → [Django ORM Query Cheat Sheet](backend/python/django-orm.md#practice-notes-from-live-session)
- SQL window functions + practice sandbox → [PostgreSQL for Scale](database/postgresql-for-scale.md#practice-notes-from-live-session)
- AWS gap services (ECS, Aurora RDS, DynamoDB) → [AWS Services Quick Reference](cloud-devops/aws-services.md)
- Project stories for system-design questions → [Personal Project Stories](interview-prep/project-stories.md)
- Django & DRF in depth (serializers, permissions, auth, signals, migrations, testing, caching) → [Django & DRF Deep Dive](backend/python/django-drf.md)

## Contents

Organized by domain instead of by when each topic was added — ten
top-level areas, each one click deep from here.

- **[Session Log](session-log.md)** — running, dated record of live
  practice Q&A, cross-linked into the chapters below.

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

### Backend

Python gets the deepest, most detailed coverage since that's the
author's own specialization and current job search; Go and Kotlin are
earlier-stage tracks for engineers coming from those languages.

**Python** — generic section name on purpose, covers any Python
framework added here later (web, desktop, or otherwise), not just
Django/FastAPI.

- [Typing & Generics](backend/python/typing-and-generics.md)
- [Bit Manipulation Basics](backend/python/bit-manipulation-basics.md)
- [Concurrency & AsyncIO](backend/python/concurrency-and-asyncio.md)
- [Threading in Practice](backend/python/threading-in-practice.md)
- [Multiprocessing in Practice](backend/python/multiprocessing-in-practice.md)
- [Building Worker Pools From Scratch](backend/python/building-worker-pools.md)
- [Capstone: A Concurrent Data Pipeline](backend/python/concurrent-data-pipeline-capstone.md)
- [Memory & Caching](backend/python/memory-and-caching.md)
- [Practical Patterns](backend/python/practical-patterns.md)
- [Python Internals & Advanced OOP](backend/python/python-internals-and-advanced-oop.md) — descriptors, metaclasses, MRO, dunder-method correctness
- [Choosing a Python Web Framework](backend/python/choosing-a-python-web-framework.md) —
  Django vs. FastAPI vs. Node/Rails/Spring Boot, and when each wins
- **Django & DRF**
    - [Django ORM Query Cheat Sheet](backend/python/django-orm.md)
    - [Django & DRF Deep Dive](backend/python/django-drf.md) — serializers, permissions,
      auth, signals, migrations, testing, caching
- **FastAPI**
    - [Dependency Injection & Background Tasks](backend/python/fastapi-dependency-injection.md)
    - [Performance & Production Patterns](backend/python/fastapi-performance-patterns.md)
- **Python Standard Library**
    - [Pathlib & File Operations](backend/python/pathlib-and-file-operations.md)
    - [Collections & Itertools](backend/python/collections-and-itertools.md)
    - [Configuration & CLI Tools](backend/python/config-and-cli-tools.md)
    - [Functools: Caching & Decorators](backend/python/functools-patterns.md)
    - [Regex & Text Processing](backend/python/regex-and-text-processing.md)

**Go**

- [Go for Python Developers](backend/go/go-for-python-developers.md)

**Kotlin**

- [Kotlin for JVM Backend Interviews](backend/kotlin/kotlin-for-jvm-interviews.md) —
  coroutines vs. Python AsyncIO, Kotlin vs. Java

**Microservices & Distributed Systems**

- **Microservices & Messaging**
    - [Service Boundaries & Architecture](backend/service-boundaries-and-architecture.md)
    - [Messaging: Kafka, Redis & AWS](backend/messaging-kafka-redis-and-aws.md) —
      includes SNS/SQS, the fan-out pattern, and idempotent event handling
    - [Inter-Service Communication](backend/inter-service-communication.md)
- **Distributed System Design**
    - [Fault Tolerance Patterns](backend/fault-tolerance-patterns.md)
    - [Load Balancing & Auto-Scaling](backend/load-balancing-and-autoscaling.md)
    - [Consistency & Consensus](backend/consistency-and-consensus.md)
    - [Data & Capacity Scaling](backend/data-and-capacity-scaling.md)
- **API Gateway & Resilience**
    - [API Gateway Architecture](backend/api-gateway-architecture.md)
    - [Rate Limiting Strategies](backend/rate-limiting-strategies.md)
    - [Circuit Breakers, Retries & Bulkheads](backend/circuit-breakers-retries-and-bulkheads.md)
    - [API Management & Versioning](backend/api-management-and-versioning.md)
    - [Kong API Gateway](backend/kong-api-gateway.md) — the concrete product behind "API Gateway (Kong)" in a JD
- **Observability**
    - [Structured Logging](backend/structured-logging.md)
    - [Metrics & Prometheus](backend/metrics-and-prometheus.md)
    - [Distributed Tracing](backend/distributed-tracing.md)
    - [Dashboards & Alerting](backend/dashboards-and-alerting.md)

### Architecture

Framework-agnostic principles, system design methodology, and
technical leadership — apply regardless of which language or framework
sits underneath.

- **Clean Code, Design Patterns, and SOLID Principles**
    - [SOLID Principles](architecture/solid-principles.md)
    - [Cohesion & Coupling](architecture/cohesion-and-coupling.md)
    - [Design Patterns](architecture/design-patterns.md)
    - [Clean Code Practices](architecture/clean-code-practices.md)
    - [Refactoring Legacy Systems](architecture/refactoring-legacy-systems.md)
- **APIs**
    - [API Paradigms & Patterns](architecture/api-paradigms-and-patterns.md)
    - [REST Deep Dive](architecture/rest-deep-dive.md)
    - [GraphQL Deep Dive](architecture/graphql-deep-dive.md)
    - [gRPC Deep Dive](architecture/grpc-deep-dive.md)
    - [API Production Readiness](architecture/api-production-readiness.md)
- **Authentication, Authorization, and Security**
    - [Authentication Patterns](architecture/authentication-patterns.md)
    - [Authorization Patterns](architecture/authorization-patterns.md)
    - [Security Hardening](architecture/security-hardening.md)
    - [Threat Detection & Monitoring](architecture/threat-detection-and-monitoring.md)
- [Performance Profiling, Optimization, and Caching](architecture/chapter-5.md)
- [Version Control & Git Workflows](architecture/version-control-and-git-workflows.md)
- **System Design Interviews**
    - [System Design Methodology](architecture/system-design-methodology.md)
    - [Architecture Diagramming & Communication](architecture/architecture-diagramming-and-communication.md) — includes the C4 model
    - [Common System Design Patterns](architecture/system-design-patterns.md)
    - [Scalability Case Studies](architecture/scalability-case-studies.md) — includes CAP and PACELC
- [Event-Driven Architectures and Async Workflows](architecture/chapter-27.md)
- [Building for Resilience](architecture/chapter-28.md)
- [Leadership for Engineers](architecture/chapter-29.md)
- [Crafting the Staff Engineer Mindset](architecture/chapter-30.md)

### Database

Everything database- and data-engineering-related in one place —
database architecture, database security, SQL/relational modeling,
web crawling/pipelines, distributed big-data compute, and
preprocessing.

- **Database Architecture for Scale**
    - [PostgreSQL for Scale](database/postgresql-for-scale.md)
    - [MongoDB for Scale](database/mongodb-for-scale.md)
    - [Elasticsearch Architecture](database/elasticsearch-architecture.md)
    - [Cross-Store Architecture Patterns](database/cross-store-architecture-patterns.md)
- [Database Security & Breach Prevention](database/database-security-and-breach-prevention.md) —
  network isolation, PII encryption, secure backup handling
- [SQL & Relational Data Modeling](database/sql-data-modeling-fundamentals.md) —
  normalization, keys, JOINs, denormalization, DB-level constraints, MySQL-specific notes
- **Web Crawling & Pipelines**
    - [Web Crawling at Scale](database/chapter-11.md)
    - [HTML Parsing and Data Pipelines](database/chapter-12.md)
    - [Distributed Crawling Architecture](database/chapter-13.md)
    - [Data Cleaning, Normalization, and Deduplication](database/chapter-14.md)
    - [Building and Managing Large MongoDB Clusters](database/chapter-15.md)
- **Big Data & Distributed Compute**
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
- [AWS Accounts & IAM](cloud-devops/aws-accounts-and-iam.md)
- **AWS Networking (VPC)**
    - [VPC & Subnet Design](cloud-devops/aws-networking-vpc.md)
    - [Security Groups, Gateways & Flow Logs](cloud-devops/vpc-security-groups-and-flow-logs.md)
- **Compute & Scaling**
    - [EC2, AMIs & Launch Templates](cloud-devops/compute-and-scaling.md)
    - [Auto Scaling Groups & Scaling Policies](cloud-devops/auto-scaling-groups.md)
- [Load Balancing & DNS](cloud-devops/load-balancing-and-dns.md)
- [Databases: RDS Operations](cloud-devops/databases-rds-operations.md)
- [Storage & Observability](cloud-devops/storage-and-observability.md) — includes CloudWatch vs. Prometheus/Grafana/Nagios
- **Containers**
    - [Docker: Production Container Images](cloud-devops/docker-production-images.md)
    - [Container Orchestration: ECS & EKS](cloud-devops/container-orchestration-ecs-eks.md)
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
    - [CI/CD & Progressive Delivery](cloud-devops/cicd-and-progressive-delivery.md) — includes diagnosing a green pipeline with a broken production deploy
- [AWS Services Quick Reference](cloud-devops/aws-services.md) — current job-search
  track's AWS gap review (ECS, Aurora RDS, DynamoDB)

### AI & LLM

**LLM APIs & Gateway**

- [LLM APIs & Providers](ai-llm/llm-apis-and-providers.md) — provider selection, auth, cost, async clients
- [LLM Gateway & Multi-Provider Integration](ai-llm/llm-gateway-multi-provider.md) — LiteLLM, provider fallback
- [LLM Response Caching](ai-llm/llm-response-caching.md) — semantic & hybrid caching

**Agents & Prompting**

- [Prompt Engineering & Context Management](ai-llm/prompt-engineering.md)
- [Agentic AI Fundamentals](ai-llm/agentic-ai-fundamentals.md) — the agent loop, and how to actually build agents with API access
- [Designing Adaptive AI Interview Systems](ai-llm/adaptive-ai-interview-systems.md) —
  LLM-driven question generation, answer scoring, and Computerized Adaptive Testing
- [Multi-Agent Systems](ai-llm/multi-agent-systems.md) — coordination topologies, debugging
- [Autogen: Multi-Agent Orchestration](ai-llm/autogen-orchestration.md)

**RAG & Retrieval**

- [Embeddings & Semantic Search](ai-llm/embeddings-semantic-search.md)
- [RAG & Vector Databases](ai-llm/rag-and-vector-databases.md)

**LangChain**

- [LangChain Agents](ai-llm/langchain-agents.md) — agent types, tools, memory, LCEL
- [LangChain Ecosystem: LangGraph, LangSmith, LangServe](ai-llm/langchain-ecosystem.md) — plus LangCache

### Algorithms

A parallel-track universal skill, not backend-architecture-specific —
usually practiced alongside everything else, not saved for last.

- [Blind 75, Grind 75 & NeetCode 150](dsa/chapter-36.md)
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

- [Behavioral Interview Prep](interview-prep/chapter-31.md)
- [Interviewing in the AI Era](interview-prep/interviewing-in-the-ai-era.md)
- [Technical Interview Deep Dives](interview-prep/chapter-32.md)
- [Mock Projects](interview-prep/chapter-33.md)
- [Take-Home & Live-Coding Exercises](interview-prep/take-home-and-live-coding-exercises.md) —
  real, scoped coding tasks recalled from interviews, e.g. a weather CLI
- [Resume, GitHub, and Case Study Optimization](interview-prep/chapter-34.md)
- [Validating Your Skill Level](interview-prep/validating-your-skill-level.md) —
  backing up a self-rated "expert" claim with something external
- [Final Review — The 30-Day Countdown](interview-prep/chapter-35.md)
- [Personal Project Stories](interview-prep/project-stories.md) — real project STAR stories
  for system-design/behavioral questions
- [Meeting-Intelligence System Case Study](interview-prep/meeting-intelligence-case-study.md)
- **Healthcare Interoperability** — the genuinely healthcare-specific
  content from the Intellias JD, a real domain gap, not yet an active
  application track
    - [FHIR R4](interview-prep/healthcare/fhir-r4.md)
    - [HL7 v2.x & C-CDA](interview-prep/healthcare/hl7-ccda.md)
    - [Healthcare Terminology](interview-prep/healthcare/healthcare-terminology.md) — SNOMED CT, LOINC, RxNorm
    - [Patient Matching & MPI](interview-prep/healthcare/patient-matching-mpi.md)
    - [HIPAA & PHI-Safe Engineering](interview-prep/healthcare/hipaa-phi-safety.md)

## A note on names

[Personal Project Stories](interview-prep/project-stories.md) uses generic project labels
("geospatial data platform client", "cybersecurity risk platform
client") left over from when this content lived on a public site. The
repo is private now, so these could be restored to the real project
names if useful — ask if you want that
done.
