---
title: Home
icon: lucide/house
---

# Cloud Developer Prep

A living backend/cloud interview-prep guide, built from real practice
sessions rather than a static checklist. Currently focused on a
Senior Python/Django role (Python, Django/DRF, SQL, AWS, system design),
but structured to grow as new roles and topics come up.

## Current track: Senior Python/Django

- **[Python Core](python-core.md)** — language fundamentals interviewers
  actually probe: mutable defaults, generators, decorators, the GIL,
  context managers.
- **[Django & DRF](django-drf.md)** — ORM query optimization
  (`select_related` vs `prefetch_related`), migrations, signals,
  middleware, DRF serializers/permissions, Celery + Redis.
- **[SQL](sql.md)** — joins, indexing, normalization, window functions,
  transactions.
- **[AWS Services](aws-services.md)** — services with real hands-on
  experience (Lambda, S3, SQS, EC2, Docker) plus a crash-review of gap
  services named in target job descriptions (ECS, Aurora RDS, DynamoDB).
- **[System Design & Stories](system-design.md)** — STAR-shaped stories
  from real project experience, genericized for public posting (see note
  below), used to answer open-ended "design a system that..." questions.
- **[Session Log](session-log.md)** — a running, dated log of practice
  Q&A: what was asked, what was answered, what feedback came back. This is
  the actual record of prep sessions, not a rewritten summary.

## A note on names

Project stories on this site use generic labels ("geospatial data
platform client", "cybersecurity risk platform client") instead of real
client/product names, since this site is public. The technical substance
— stack, architecture, metrics — is real; only identifying names are
genericized.
