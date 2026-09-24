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
[Practical Patterns](practical-patterns.md#practice-notes-from-live-session).

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
[Django ORM Query Cheat Sheet](django-orm.md#practice-notes-from-live-session).

### Q3 — Rank within a group / window functions (SQL)

**Asked:** given `employees(id, name, department_id, salary, hire_date)`
and `departments(id, name)`, return each employee's name, department
name, salary, and salary rank *within their department*, ordered by
department then rank.

**Answer:** `SELECT name, department_id, salary FROM employees GROUP BY department.`

**Feedback:** Missed on multiple fronts — `GROUP BY department` isn't a
valid column (`department_id`), and `GROUP BY` was the wrong tool
regardless, since it collapses rows into one per group instead of
ranking within them. No join to `departments` for the name, and no
window function at all, which was the actual point of the question.
Correct answer uses `RANK() OVER (PARTITION BY department_id ORDER BY
salary DESC)` — see full writeup for the `PARTITION BY` vs `GROUP BY`
distinction and `RANK`/`DENSE_RANK`/`ROW_NUMBER` tie-handling
differences.

**Status:** ❌ gap — window functions are not yet solid. This was called
out ahead of time as "common in senior-level tests," so it's a priority
for more reps before the real interview, not just a one-off review. Full
writeup: [PostgreSQL for Scale](postgresql-for-scale.md#worked-example-rank-within-a-group-window-functions).

### Q4 — Practice sandbox problem 1: warm-up join (SQL)

**Asked:** write a query listing every employee's name, department name,
and salary, and run it against the real `practice.db`.

**Attempt 1:** `SELECT e.name, d.name, e.salary WHERE employees AS e
JOIN departments AS d ON e.department_id = d.department_id;` —
`WHERE` used where `FROM` was needed (can't introduce a table via
`WHERE` — it only filters rows after a `FROM` has already supplied
them).

**Attempt 2:** fixed `FROM`/`WHERE`, but `ON e.department_id =
d.department_id` still failed — `departments` only has `id`/`name`
(per `schema.sql`); `department_id` only exists on `employees` as the
foreign key. Should be `d.id`.

**Attempt 3:** `SELECT e.name, d.name, e.salary FROM employees e JOIN
departments d ON e.department_id = d.id;` — ran clean, all 16 rows
correct.

**Status:** ✅ correct on the third try, in the real sandbox (not just
talked through). Pattern to watch: both bugs came from not checking the
schema before writing the join — guessed a column name instead of
confirming it. Worth being deliberate about glancing at the schema
first under real interview time pressure, since there's no `sqlite3`
error message to lean on there.

---

*Next session: continue through the practice sandbox problems (2–8:
aggregates, HAVING, then window functions), then AWS gap topics
(ECS/Aurora/DynamoDB — [AWS Services Quick Reference](aws-services.md))
and a full mock run-through.*
