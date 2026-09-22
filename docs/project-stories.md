---
title: "Personal Project Stories"
---

# Personal Project Stories

Senior-level interviews often include one open-ended design question.
Rehearse these **out loud**, not just in your head, so the numbers come
out fluently instead of fumbled. Related: Chapter 26 (System Design
Interviews), Chapter 31 (Behavioral Interview Prep), Chapter 33 (Mock
Projects) cover the book's own hypothetical scenarios — these are your
*real* projects to use instead.

## Project A — Geospatial Data Platform

*Lead Developer, confidential client · 2025–present*

**Stack:** Django, PostGIS, AWS Lambda/SQS/Athena, React

- Designed and built the Django/PostGIS backend, modeling complex spatial
  data for enterprise use.
- Built an async data pipeline (S3 → Lambda → Athena) for large-scale
  geospatial data processing.
- Developed React components for interactive map rendering.

**Use for:** "How would you design an API that ingests large geospatial
datasets?" / "Tell me about a project with heavy async processing."

## Project B — Cybersecurity Risk Rating Platform

*Senior Software Engineer, confidential US client · 2023–2024*

**Stack:** Django REST Framework, FastAPI, Elasticsearch, Vue.js

- Built DRF and FastAPI microservices to process and serve
  Elasticsearch-backed threat rating data.
- Contributed Vue.js frontend features alongside backend development.
- **Improved API response times by ~30% through targeted query
  optimization.**

**Use for:** "How would you scale a Django app that's getting slow under
load?" — walk through query optimization → caching → async offload
(Celery) → read replicas → horizontal scaling behind a load balancer,
landing on this concrete result.

## Project C — AI Document Processing Tool

*Lead Developer, confidential client · 2025–present*

**Stack:** LangChain, Azure OpenAI, Azure Speech-to-Text, Cosmos DB

- Used speech-to-text ahead of retrieval/generation to convert audio and
  video inputs into structured text.
- Applied Retrieval-Augmented Generation (RAG) to keep knowledge updates
  flexible and improve output accuracy.
- Unified the workflow on cloud cognitive services + Cosmos DB for
  end-to-end media intelligence automation.
- **Reduced manual report generation by ~60%.**

**Use for:** "Walk me through how you'd add RAG-based search to an
existing product." Genuinely uncommon, strong answer — most candidates at
this level haven't shipped RAG end-to-end. If the interviewer's stack is
AWS-native (Lex) or IBM Watson/GCP rather than Azure, be ready to say:
"the concepts — embeddings, retrieval, prompt orchestration — transfer
directly, I just haven't used those specific SDKs." See also the
[MeetingFlow Case Study](meetingflow-case-study.md) for the deep technical write-up
behind this project.

## Project D — Omnichannel Customer Engagement Platform

*Senior Software Engineer, confidential client · 2021–2023*

**Stack:** Django REST Framework, Celery, Redis, JWT, FastAPI

- Developed backend services for a multi-tenant customer engagement
  platform.
- Implemented JWT-based multi-tenant authentication, integrated Celery +
  Redis for background task processing and caching.
- Built FastAPI-based onboarding automation to streamline client setup.

**Use for:** "Design a backend for a multi-tenant SaaS platform."

## Prep move

Before the interview, say each of the four "Use for" answers out loud,
timed to ~90 seconds each, until the numbers (30%, 60%) come out without
checking notes.
