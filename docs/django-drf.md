---
title: Django & DRF
---

# Django & DRF

## Checklist

- ORM: `select_related` vs `prefetch_related`, the N+1 query problem (see
  worked example below)
- QuerySet laziness, `.values()` vs `.values_list()` vs full objects
- Migrations: how they work, squashing, data migrations vs schema
  migrations
- Django signals — what they're for, why they're often discouraged
  (implicit coupling)
- Middleware — request/response cycle, where auth/logging hooks in
- DRF: serializers (validation, `SerializerMethodField`), viewsets vs
  generic views, permission classes, throttling
- Authentication: JWT, session vs token auth, multi-tenant auth patterns
- Celery + Redis: task queues, retries, idempotency, periodic tasks
- Caching strategies: query caching, Redis caching, cache invalidation
- Testing: `pytest-django`, fixtures, factory patterns, mocking external
  calls

## Be ready to whiteboard/code cold

- Design a Django model for a small domain (e.g. "design models for an
  order/inventory system")
- Write a DRF endpoint with validation and permission checks
- Spot and fix an N+1 query in a given view
- Write a raw SQL query with a join + aggregation from a schema given on
  the spot

## Worked example: `select_related` vs `prefetch_related`

Given this view:

```python
def get_reports(request):
    reports = Report.objects.filter(status='active')
    data = [
        {"title": r.title, "owner": r.owner.name, "org": r.owner.organization.name}
        for r in reports
    ]
    return JsonResponse(data, safe=False)
```

**Problem:** every iteration hits the DB again for `r.owner` and
`r.owner.organization` — classic N+1.

**The nuance that matters at senior level** — the two fixes are not
interchangeable:

| | Use for | How |
|---|---|---|
| `select_related` | `ForeignKey` / `OneToOne` (single-valued, "to-one") relations | SQL `JOIN`, one query |
| `prefetch_related` | reverse FK / `ManyToMany` (multi-valued, "to-many") relations | a second query, joined in Python |

`owner` is a FK on `Report`, and `organization` is a FK on `owner` — both
single-valued, always "one row points to one related row." Correct fix:

```python
reports = Report.objects.filter(status='active') \
    .select_related('owner', 'owner__organization')
```

Using `prefetch_related` here would still reduce query count vs. the
original, but it's the wrong tool — extra queries instead of a single
JOIN. Interviewers probe this specific distinction to separate "knows N+1
is bad" from "actually understands the ORM."

**Rule of thumb:** if you can reach the field through a chain of dots
without ever going "backwards" through a `ForeignKey`/`M2M`, use
`select_related`. If at any point you're fetching a *collection* (reverse
FK, M2M), use `prefetch_related`.

!!! note "Session note"
    Covered in the [session log](session-log.md#2026-09-22) — N+1
    correctly diagnosed; initial fix used `prefetch_related`, corrected to
    `select_related` after discussion of the to-one/to-many distinction.
