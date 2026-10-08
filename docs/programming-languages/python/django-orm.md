---
title: "Django ORM Query Cheat Sheet for Senior Engineers"
---

# Django ORM Query Cheat Sheet for Senior Engineers

This appendix is a practical Django ORM reference focused on interview-grade and production-grade query patterns. The goal is not to memorize every API surface, but to recognize when a query should be pushed into the database instead of being handled inefficiently in Python loops. For the PostgreSQL-side concepts behind these patterns — index selection, reading `EXPLAIN`, partitioning — see [PostgreSQL for Scale](../../data-and-engineering/postgresql-for-scale.md).

## 1. Query Loading Patterns

### 1.1 `select_related` for `ForeignKey` and `OneToOne`

Use `select_related` when you want Django to fetch related single-value objects with a SQL join.

```python
orders = (
    Order.objects
    .select_related("customer", "shipping_address")
)
```

**Use when:**
- detail pages need parent objects
- serializers are reading foreign keys repeatedly
- you want to avoid N+1 queries on single-value relations

### 1.2 `prefetch_related` for reverse relations and `ManyToMany`

Use `prefetch_related` when related collections would explode row counts if joined directly.

```python
orders = (
    Order.objects
    .select_related("customer")
    .prefetch_related("items__product")
)
```

**Interview point:** `select_related` uses SQL joins; `prefetch_related` performs additional queries and stitches results in Python.

### 1.3 Filtered `Prefetch`

Use `Prefetch` when you need a filtered subset of related rows without loading everything.

```python
from django.db.models import Prefetch

posts = Post.objects.prefetch_related(
    Prefetch(
        "comments",
        queryset=Comment.objects.filter(is_published=True),
        to_attr="published_comments",
    )
)
```

## 2. Aggregation and Annotation

### 2.1 Counting related objects

```python
from django.db.models import Count

authors = Author.objects.annotate(
    book_count=Count("books")
).order_by("-book_count")
```

### 2.2 Conditional aggregation

```python
from django.db.models import Count, Q

authors = Author.objects.annotate(
    published_book_count=Count(
        "books",
        filter=Q(books__status="published")
    )
)
```

### 2.3 Sum and average calculations

```python
from django.db.models import Avg, Sum

customers = Customer.objects.annotate(
    total_spent=Sum("orders__total_amount"),
    avg_order_value=Avg("orders__total_amount"),
)
```

**Use when:** dashboards, reporting APIs, leaderboards, and admin analytics screens need computed fields without raw SQL.

## 3. Conditional Expressions

### 3.1 `Case` and `When`

```python
from django.db.models import Case, CharField, Value, When

users = User.objects.annotate(
    account_type=Case(
        When(is_staff=True, then=Value("staff")),
        When(is_premium=True, then=Value("premium")),
        default=Value("regular"),
        output_field=CharField(),
    )
)
```

**Use when:** you want SQL-level branching for labels, flags, ordering, or business reporting.

## 4. In-Database Updates and Expressions

### 4.1 `F()` expressions

Use `F()` when the database should update a field relative to its current value.

```python
from django.db.models import F

Product.objects.filter(id=1).update(stock=F("stock") - 1)
```

**Why it matters:** avoids race-prone read-modify-write logic in Python.

### 4.2 Computed expressions with `ExpressionWrapper`

```python
from django.db.models import DecimalField, ExpressionWrapper, F

products = Product.objects.annotate(
    discounted_price=ExpressionWrapper(
        F("price") * 0.9,
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
)
```

## 5. Subqueries and Existence Checks

### 5.1 `Subquery` and `OuterRef`

Get each user's latest order total.

```python
from django.db.models import OuterRef, Subquery

latest_order_amount = (
    Order.objects
    .filter(customer=OuterRef("pk"))
    .order_by("-created_at")
    .values("total_amount")[:1]
)

users = User.objects.annotate(
    latest_order_total=Subquery(latest_order_amount)
)
```

**Use when:** you need one related value per parent row without loading all related rows.

### 5.2 `Exists`

```python
from django.db.models import Exists, OuterRef

recent_orders = Order.objects.filter(
    customer=OuterRef("pk"),
    status="pending",
)

users = User.objects.annotate(
    has_pending_orders=Exists(recent_orders)
)
```

**Why it matters:** `Exists` is usually better than fetching records when all you need is a boolean.

## 6. Window Functions

Rank employees by salary inside each department.

```python
from django.db.models import F, Window
from django.db.models.functions import Rank

employees = Employee.objects.annotate(
    dept_rank=Window(
        expression=Rank(),
        partition_by=[F("department")],
        order_by=F("salary").desc(),
    )
)
```

**Use when:** analytics APIs need top-N per group, rankings, or running calculations.

## 7. Date-Based Reporting

```python
from django.db.models import Count
from django.db.models.functions import TruncMonth

stats = (
    Order.objects
    .annotate(month=TruncMonth("created_at"))
    .values("month")
    .annotate(total_orders=Count("id"))
    .order_by("month")
)
```

**Use when:** building charts, monthly reports, and KPI endpoints.

## 8. Complex Filtering

### 8.1 `Q` objects

```python
from django.db.models import Q

users = User.objects.filter(
    Q(is_active=True) &
    (Q(role="admin") | Q(role="manager")) &
    ~Q(email__icontains="test")
)
```

### 8.2 Reverse relation filtering

```python
customers = Customer.objects.filter(
    orders__items__product__category="Laptop"
).distinct()
```

**Why `distinct()` matters:** joins can duplicate parent rows.

## 9. Transactions and Locking

Use row-level locking for critical workflows such as stock deduction, payments, or ticket allocation.

```python
from django.db import transaction

with transaction.atomic():
    product = Product.objects.select_for_update().get(pk=1)
    if product.stock > 0:
        product.stock -= 1
        product.save()
```

**Interview point:** pair `transaction.atomic()` with `select_for_update()` when concurrent writers must not step on each other.

**Likely follow-up — "what's the cost of `select_for_update` under contention?"** It
serializes access to the locked rows — every other transaction wanting
the same row blocks until the lock is released, which is correct but
throttles throughput hard on a hot row. Scope it to the narrowest row
set and the shortest transaction possible; reach for it only where
correctness genuinely requires it, since it trades throughput for
consistency.

## 10. Query Shaping and Memory Control

### 10.1 Fetch only what you need

```python
users = User.objects.only("id", "name", "email")
```

Or use plain dictionaries for API/reporting layers:

```python
users = User.objects.values("id", "name", "email")
```

### 10.2 Common rule

If the caller only needs a small subset of fields, do not materialize full model instances unnecessarily.

## 11. Five ORM Patterns to Memorize for Interviews

If time is short, memorize these five:

1. `select_related` vs `prefetch_related`
2. `annotate(Count(...))`
3. `F()` expressions for atomic updates
4. `Subquery` + `OuterRef`
5. `transaction.atomic()` + `select_for_update()`

## 12. Senior-Level Discussion Points

When discussing Django ORM in interviews, try to speak in this order:

1. identify the data access pattern
2. inspect query count and generated SQL
3. reduce N+1 queries
4. add or verify indexes
5. move computation into the database when appropriate
6. measure again before changing architecture

Good concise summary:

> Most Django ORM problems are not caused by Django itself. They come from weak query design, missing indexes, poor loading strategy, or doing work in Python that should have been done in SQL.

## 13. Custom Managers and QuerySets

```python
class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class Product(models.Model):
    objects = models.Manager()        # default, unrestricted
    active = ActiveManager()          # Product.active.all()
```

Chainable custom queryset methods so they combine with `.filter()`/`.exclude()` naturally:

```python
class OrderQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(status="pending")

    def for_customer(self, customer):
        return self.filter(customer=customer)

class Order(models.Model):
    objects = OrderQuerySet.as_manager()

# Order.objects.pending().for_customer(user) -- chains cleanly
```

**Use when:** a filter/annotation combination is repeated across
multiple views/services — centralizing it in a manager method means
one place to fix a bug instead of N call sites that each got it
slightly differently.

**Interview point:** the first model `Manager` declared becomes the
default (`_default_manager`), used by reverse relations and
`related_name` lookups — if `objects` isn't your first-declared
manager, reverse FK traversal can silently use the wrong one.

## 14. Bulk Operations

| | Replaces | Caveat |
|---|---|---|
| `bulk_create()` | a loop of `.save()` calls | skips `save()`/signals by default; tune `batch_size` for very large sets |
| `bulk_update()` | a loop of `.save(update_fields=[...])` | still one query per *batch*, not per row |
| `in_bulk()` | `{obj.pk: obj for obj in qs}` | returns a dict keyed by pk (or another unique field) in one query |
| `.iterator(chunk_size=...)` | loading a huge queryset fully into memory | streams rows instead of caching the whole queryset |

```python
Product.objects.bulk_create(
    [Product(name=n, price=p) for n, p in new_products],
    batch_size=500,
)
```

**Interview point:** `bulk_create`/`bulk_update` do **not** call
`Model.save()` or fire `pre_save`/`post_save` signals — any side
effect living in `save()` or a signal handler silently doesn't run.
This is the most commonly missed gotcha in interviews about this
topic.

## 15. `get_or_create` / `update_or_create` — and the Race Condition

```python
obj, created = Customer.objects.get_or_create(
    email=email,
    defaults={"name": name},
)
```

- **The race:** two concurrent requests both check "does this email
  exist?", both see no row, both try to `INSERT` — one wins, the
  other hits an `IntegrityError` on a unique constraint (if one
  exists) or, worse, creates a duplicate (if no unique constraint
  exists to catch it).
- `get_or_create` does **not** make the check-then-create atomic on
  its own.
- **The real fix:** a unique constraint on `email` (so the duplicate
  path is impossible) plus catching `IntegrityError` and retrying as
  a `get()`, or wrapping the call in `transaction.atomic()` with
  `select_for_update()` on a parent row if the race needs to be fully
  excluded rather than just safely detected.

## 16. Raw SQL Escape Hatches

```python
# .raw() -- returns model instances
customers = Customer.objects.raw(
    "SELECT * FROM customers WHERE created_at > %s", [cutoff]
)

# connection.cursor() -- returns plain rows, no model mapping at all
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT org_id, COUNT(*) FROM orders GROUP BY org_id")
    rows = cursor.fetchall()
```

**Use when:** a query is expressible in SQL but not reasonably in the
ORM (a recursive CTE, a vendor-specific function the ORM has no
wrapper for) — reach for `.raw()`/`connection.cursor()` as the last
resort, not the first, since it loses the ORM's query-building
composability and database portability.

**Interview point:** both forms still use parameterized queries (`%s`
placeholders) — never f-string/format raw SQL with user input, which
is a direct SQL injection vector.

## 17. Multiple Databases and Routers

```python
class ReplicaRouter:
    def db_for_read(self, model, **hints):
        return "replica"

    def db_for_write(self, model, **hints):
        return "default"
```

**Use when:** read replicas (route `SELECT`s to a replica, writes to
the primary), or genuinely separate databases per concern (an
analytics DB separate from the transactional one). `.using("replica")`
overrides the router per-call when needed.

**Interview point:** a read immediately after a write, routed to a
replica, can read stale data if replication lag hasn't caught up —
this is the actual trade-off behind "just add a read replica," not a
free win.

## 18. Diagnosing Query Behavior

- `from django.db import connection; connection.queries` — every
  query run so far in the current request (needs `DEBUG=True` or
  explicit `reset_queries()`/`CaptureQueriesContext` in tests).
- `str(queryset.query)` — the exact SQL a queryset *would* run,
  without executing it — the fastest way to confirm a suspected N+1
  or a missing filter before it ever hits the DB.
- `queryset.explain(analyze=True)` — Django's wrapper around the
  database's `EXPLAIN` (see
  [PostgreSQL for Scale](../../data-and-engineering/postgresql-for-scale.md)
  for reading the plan itself).
- `django-debug-toolbar` in local dev — surfaces query count and
  duplicate queries per request visually; the fastest way to catch an
  N+1 that unit tests (which often use small fixtures) don't surface
  at scale.

## 19. Interview Questions You're Likely to Get Asked

Real questions interviewers ask about Django ORM, grouped by what
they're actually probing.

**Query loading & N+1**

- "Your API response time doubled after a serializer field started
  reading a related object. How do you find out why, and how do you
  fix it?" — expects: enable query logging/debug toolbar, count
  queries, recognize N+1, apply `select_related` (to-one) or
  `prefetch_related` (to-many); see
  [§1](#1-query-loading-patterns) and the
  [Practice Notes](#practice-notes-from-live-session) round below.
- "When would `prefetch_related` still cause more queries than you
  expect?" — expects: a `Prefetch` object isn't reused across
  unrelated querysets, or a loop re-evaluates a queryset that wasn't
  actually cached (e.g. slicing it differently each time).

**Atomicity & concurrency**

- "Two requests hit 'decrement stock' at the same time. Walk me
  through what happens with: no locking, `F()` expressions, and
  `select_for_update()`." — expects: without locking, a lost update
  is possible; `F()` pushes the arithmetic into the DB's own atomic
  `UPDATE` ([§4.1](#41-f-expressions)); `select_for_update()`
  additionally serializes access across a *multi-statement*
  transaction where `F()` alone isn't enough (e.g. check-then-act
  logic). See [§9](#9-transactions-and-locking).
- "What's wrong with `get_or_create` under high concurrency?" —
  expects the race condition in
  [§15](#15-get_or_create-update_or_create-and-the-race-condition).

**Schema & migrations**

- "You need to rename a column on a table that's read thousands of
  times a second, with zero downtime. What's your plan?" — expects
  the add-nullable → dual-write → backfill → cut over → drop pattern
  in [Django & DRF Deep Dive §7](django-drf.md#7-migrations).

**Performance & memory**

- "You need to export 10 million rows to a report. What goes wrong if
  you just do `for row in Model.objects.all()`?" — expects: the full
  queryset gets cached in memory; `.iterator()` (or chunked
  `.values_list()` pagination) streams instead — see
  [§10](#10-query-shaping-and-memory-control) and
  [Large-Scale Report Generation](../../data-and-engineering/large-scale-report-generation.md).
- "When would `bulk_create` be the wrong choice even though it's
  faster?" — expects: when per-row side effects in `save()`/signals
  are actually required ([§14](#14-bulk-operations)) — speed isn't
  free if it silently skips behavior the rest of the system depends
  on.

**Aggregation & subqueries**

- "Get each customer's most recent order without fetching every
  order." — expects `Subquery`+`OuterRef` sliced to one row,
  [§5.1](#51-subquery-and-outerref), not a Python loop over
  `prefetch_related`.
- "You only need to know *if* a customer has any pending orders, not
  the orders themselves. What's the most efficient query?" — expects
  `Exists()` ([§5.2](#52-exists)) over `.filter(...).count() > 0`,
  since `Exists` stops at the first match instead of counting all
  rows.

**ORM fundamentals & security**

- "What is the actual purpose of an ORM?" — expects: it maps
  application objects to relational rows/tables so code manipulates
  objects instead of hand-writing SQL for every operation, while still
  allowing an escape hatch ([§16](#16-raw-sql-escape-hatches)) when it
  doesn't fit. The value isn't "avoiding SQL" — it's a consistent,
  composable way to build queries, plus one place where cross-cutting
  concerns (connection handling, query building, migrations) live
  once instead of being reimplemented per query.
- "Are there security reasons to use an ORM? Name some." — expects:
  the ORM parameterizes query values by default (bound parameters, not
  string interpolation into SQL), which closes off the most common SQL
  injection vector automatically. The risk reappears exactly where the
  ORM is bypassed — [§16](#16-raw-sql-escape-hatches)'s raw SQL escape
  hatch, if that code path f-strings/formats user input into the query
  instead of parameterizing it.

**Design judgment**

- "When would you *not* use the ORM at all for a query?" — expects
  recognizing the raw-SQL escape hatch's real trade-off
  ([§16](#16-raw-sql-escape-hatches)) — portability and composability
  lost, not "the ORM is bad."
- "Where do you draw the line between a custom manager method and a
  service function?" — expects: a manager method for "a reusable way
  to *query* data" (still returns a queryset), a service function for
  "a reusable *business operation*" (does something, possibly
  spanning multiple models) — mixing the two makes managers do too
  much.

---

## Practice Notes (from live session)

### `select_related` vs `prefetch_related` — a real N+1 round

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
    Covered in the [session log](../../session-log.md#2026-09-22) — N+1
    correctly diagnosed; initial fix used `prefetch_related`, corrected to
    `select_related` after discussion of the to-one/to-many distinction.
