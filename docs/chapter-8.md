---
title: "Chapter 8: Database Architecture for Scale \u2014 PostgreSQL, MongoDB, and Elasticsearch"
---

# Chapter 8: Database Architecture for Scale — PostgreSQL, MongoDB, and Elasticsearch

Master database design and optimization for high-scale applications. Learn advanced PostgreSQL features, MongoDB operations, and Elasticsearch for search and analytics.

## Learning Objectives

- Design scalable database architectures
- Optimize PostgreSQL for high-performance workloads
- Implement MongoDB for document-based applications
- Use Elasticsearch for search and real-time analytics
- Handle database migrations and schema evolution

## Key Topics

### 1. PostgreSQL Advanced Features
- Advanced indexing strategies (B-tree, GIN, GiST)
- Query optimization and execution plans
- Partitioning and sharding techniques
- Replication and high availability
- JSON/JSONB for semi-structured data

### 1.1 PostgreSQL + Django ORM Performance Patterns

In Django systems, database performance problems usually come from the boundary between ORM usage and PostgreSQL execution. Senior engineers should be able to reason about both layers together.

**Key patterns to discuss:**
- choose indexes based on actual filters, joins, and ordering clauses
- inspect SQL and query plans before guessing at optimizations
- reduce query count with `select_related` and `prefetch_related`
- push aggregation and filtering into SQL instead of looping in Python
- use row locks only when correctness requires them

```python
from django.db.models import Count, F, Q

accounts = (
    Account.objects
    .filter(is_active=True)
    .annotate(
        open_invoice_count=Count(
            "invoices",
            filter=Q(invoices__status="open")
        ),
        available_credit=F("credit_limit") - F("used_credit"),
    )
    .order_by("-available_credit")
)
```

This kind of query is a good interview example because it combines filtering, aggregation, and computed fields without leaving the ORM.

### 2. MongoDB for Scale
- Document modeling and schema design
- Aggregation pipeline optimization
- Sharding and replica sets
- Index optimization for queries
- Change streams for real-time updates

### 3. Elasticsearch Architecture
- Index design and mapping strategies
- Query DSL and aggregations
- Cluster setup and node management
- Performance tuning and optimization
- Integration with application stacks

### 4. Database Architecture Patterns
- CQRS with separate read/write databases
- Database per microservice pattern
- Data synchronization strategies
- Backup and disaster recovery
- Monitoring and performance metrics

## Practical Examples

- Optimizing PostgreSQL for a high-traffic application
- Building a MongoDB-based content management system
- Implementing full-text search with Elasticsearch

## Interview Preparation

- Database scaling architecture discussions
- Query optimization scenarios
- NoSQL vs SQL trade-off questions

---

## Practice Notes (from live session)

### SQL practice sandbox

A real SQLite database (`employees`/`departments`, seeded with deliberate
salary ties) plus an 8-problem set (joins through
`RANK`/`ROW_NUMBER`/`LAG`/`LEAD`) and verified solutions live in this
repo at [`practice/sql/`](https://github.com/Fahad-Md-Kamal/Cloud-Developer-Prep/tree/main/practice/sql):

```bash
cd practice/sql
sqlite3 practice.db < schema.sql   # one-time setup
sqlite3 practice.db                # open the shell and start querying
```

Beyond that, [PG Exercises](https://pgexercises.com/) for more query
volume, *Use The Index, Luke* for reading query plans and indexes.

### Worked example: rank within a group (window functions)

Schema: `employees(id, name, department_id, salary, hire_date)`,
`departments(id, name)`.

**Task:** each employee's name, department name, salary, and their salary
rank *within their department* (1 = highest paid), ordered by department
then rank.

```sql
SELECT
    e.name,
    d.name AS department_name,
    e.salary,
    RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS salary_rank
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name, salary_rank;
```

#### Tracing it on real data

Abstract syntax doesn't stick — trace it on actual rows instead.

**Sample data:**

| name | department_id | salary |
|---|---|---|
| Alice | 10 | 90000 |
| Bob | 10 | 80000 |
| Carol | 10 | 80000 |
| Dave | 20 | 70000 |
| Eve | 20 | 60000 |

Running `RANK() OVER (PARTITION BY department_id ORDER BY salary DESC)`
produces:

| name | department_id | salary | salary_rank |
|---|---|---|---|
| Alice | 10 | 90000 | 1 |
| Bob | 10 | 80000 | 2 |
| Carol | 10 | 80000 | 2 |
| Dave | 20 | 70000 | 1 |
| Eve | 20 | 60000 | 2 |

**Step by step:**

1. **`PARTITION BY department_id`** — mentally split the table into
   buckets, one per department. Nothing is deleted or merged; every row
   is still there.
2. **`ORDER BY salary DESC`** (inside `OVER(...)`) — within *each bucket
   separately*, sort by salary, highest first.
3. **`RANK()`** — walk down each bucket's sorted order and assign 1st,
   2nd, etc., restarting at 1 every time you cross into a new bucket.
   Tied rows (Bob and Carol, both 80000) get the same rank.

**Why not plain `ORDER BY` + row position?** That gives one ranking
across the *whole table* (Alice would be #1 overall, Dave #4 overall).
`RANK() OVER (PARTITION BY ...)` gives a ranking that resets **per
group**, in a single query, without collapsing rows the way `GROUP BY`
would.

**The core idea, stated generally:** `PARTITION BY` splits the result
set into groups — here, one per department — **without collapsing rows**
the way `GROUP BY` does (`GROUP BY` produces one row per group; a window
function keeps every row and just annotates it). `ORDER BY salary DESC`
inside the `OVER (...)` clause then ranks rows within each partition.

**Tie handling — the other thing this tests:**

| Function | Ties | Next rank after a tie |
|---|---|---|
| `ROW_NUMBER()` | always unique (1,2,3,4...) | n/a |
| `RANK()` | same rank | **skips** (1,1,3,4) |
| `DENSE_RANK()` | same rank | **doesn't skip** (1,1,2,3) |

!!! note "Session note"
    Covered in the [session log](session-log.md#2026-09-22) — first
    attempt used `GROUP BY` (wrong tool: collapses rows instead of
    ranking within them) with no join and no window function. Flagged
    for another rep before the real interview.
