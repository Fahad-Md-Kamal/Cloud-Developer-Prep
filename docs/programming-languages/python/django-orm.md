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
