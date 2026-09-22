---
title: Session Log
---

# Session Log

A running, dated record of practice sessions — actual questions asked,
actual answers given, actual feedback. Not a rewritten summary; entries
get appended as sessions happen.

## 2026-09-22

**Context:** kickoff prep session for a Senior Python Developer role
(external client via BJIT, ~90 min interview + test, target date unknown
— possibly the week of 2026-09-28).

### Q1 — Mutable default arguments (Python core)

**Asked:**

```python
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item("a"))
print(add_item("b"))
```
What does the second `print` output, and why? How would you fix it?

**Answer:** Correctly predicted `['a']` then `['a', 'b']`. Reasoning
given: "because it reuses the same parameter value items."

**Feedback:** Output correct. Reasoning refined — default arguments are
evaluated once at function *definition* time, creating a single shared
object, not "reused per call." Fix (the `None` sentinel idiom) required a
prompt but was then given correctly.

**Status:** ✅ solid after one nudge. Full writeup:
[Python Core](python-core.md#worked-example-mutable-default-arguments).

### Q2 — N+1 queries / `select_related` vs `prefetch_related` (Django ORM)

**Asked:** a view iterating `Report.objects.filter(...)` and accessing
`r.owner.name` and `r.owner.organization.name` per row — diagnose the
performance issue and fix it.

**Answer:** Correctly identified the N+1 query problem. Initial fix used
`prefetch_related("owner")`.

**Feedback:** `prefetch_related` was the wrong tool here — `owner` and
`owner.organization` are both `ForeignKey` (single-valued/"to-one")
relations, which call for `select_related` (a SQL `JOIN`, one query).
`prefetch_related` is for reverse FK / `ManyToMany` ("to-many")
relations. Correct fix:
`Report.objects.filter(...).select_related('owner', 'owner__organization')`.

**Status:** ⚠️ needs another rep — N+1 diagnosis is solid, but
`select_related`/`prefetch_related` choice needs to become automatic, not
a "which one was it again" pause under interview pressure. Full writeup:
[Django & DRF](django-drf.md#worked-example-select_related-vs-prefetch_related).

---

*Next session: continue Django/DRF drills, then move to SQL and AWS gap
topics.*
