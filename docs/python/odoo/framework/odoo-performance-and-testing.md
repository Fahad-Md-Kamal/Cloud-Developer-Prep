---
title: Odoo Performance & Testing
---

# Odoo Performance & Testing

The Odoo ORM hides the database, so slow code looks identical to fast
code until the data grows. Two skills close that gap: knowing how Odoo
loads data (prefetching), and writing tests that catch regressions,
including query counts.

!!! note "Version"
    Written for **Odoo 20**. Where an older version differs, the page says so.

## 1. "How does Odoo load data, and what is the N+1 problem?"

**Answer:**

- **Prefetching** is the key idea. When you read a field on one record,
  Odoo loads that field for **all records in the same recordset** (in
  batches of up to 1000), then caches them.
- So this is fast — one query for all names:

    ```python
    for partner in partners:      # partners is one recordset
        print(partner.name)
    ```

- **N+1** happens when you break the set apart. Each `browse(id)` or
  `search` inside a loop builds a new small set, so each pass runs its
  own query:

    ```python
    for pid in ids:
        partner = self.env['res.partner'].browse(pid)   # new set each time
        print(partner.name)                             # one query each
    ```

- Fix: build **one** recordset first, then loop over it.
- Same trap with `search` inside a loop. Search once with `in`, then
  group the results in Python.

## 2. "How do you aggregate without loading every record?"

```python
rows = self.env['sale.order'].read_group(
    domain=[('state', '=', 'sale')],
    groupby=['partner_id'],
    aggregates=['amount_total:sum'],
)
# rows is a list of tuples: (partner, total)
```

**Answer:**

- Do the counting and summing in PostgreSQL, not in a Python loop.
- In Odoo 20, `read_group(domain, groupby, aggregates, having, offset,
  limit, order)` runs `GROUP BY` in the database and returns a **list
  of tuples**.
- `_read_group` takes the same arguments. Its difference: related
  groupby values come back as recordsets, not plain ids.
- Older tutorials show the previous form, where `read_group` took
  `fields` and returned dictionaries. Translate before copying.
- Use `search_count` when you only need a count.
- For one-off heavy reports, raw SQL is allowed. Use parameters, and
  flush and invalidate the cache around it
  (`flush_model`, `invalidate_recordset`), or the ORM cache will be
  out of date. See [Odoo Security](odoo-security.md#6-how-do-you-secure-http-controllers-and-raw-sql).

## 3. "What else makes Odoo slow?"

**Answer:**

- **Stored computed fields with long dependency chains.** One change
  recomputes many records. See
  [Odoo ORM & Recordsets §5](odoo-orm-and-recordsets.md#5-how-do-computed-fields-work-and-when-do-you-use-storetrue).
- **Missing indexes.** Add `index=True` on fields you search or sort by
  often.
- **Non-stored computed fields in a list view.** They compute for every
  visible row.
- **Writes in a loop.** One `write` on a recordset is one `UPDATE`.
- **Creating records one by one.** Pass a list to `create`.
- **Heavy work inside a request.** Move it to a scheduled action (cron)
  or a queued job.
- Always measure first. See
  [Profiling & Optimization](../../performance-and-memory/profiling-and-optimization.md) for the
  general method.

## 4. "How do you find a slow query?"

**Answer:**

- Start the server with SQL logging (`--log-level=debug_sql`) and count
  the queries one action produces.
- Use developer mode's profiler to see Python time and SQL time per
  call.
- A page that runs hundreds of near-identical queries is the N+1 sign.
- Run `EXPLAIN ANALYZE` on the slowest query in PostgreSQL to see
  whether an index is missing.

## 5. "What are the main test classes?"

```python
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestLoan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.book = cls.env['library.book'].create({'title': 'Dune'})

    def test_borrow_sets_state(self):
        self.book.action_borrow()
        self.assertEqual(self.book.state, 'borrowed')
```

**Answer:**

- **`TransactionCase`** — each test runs in a database transaction that
  is **rolled back** at the end. Fast, and tests stay independent. Use
  it for most tests.
- **`HttpCase`** — starts the web server, for controllers and browser
  "tours" (scripted UI walk-throughs).
- **`Form`** (from `odoo.tests`) — simulates a user filling a form,
  **including `onchange`**. Use it to test onchange logic, because a
  plain `create` does not run it.
- **`@tagged`** controls when tests run. `post_install` runs after all
  modules load, which suits tests that need other modules.
- Run tests: `odoo-bin -d testdb -i my_module --test-enable --stop-after-init`,
  and narrow with `--test-tags /my_module`.

## 6. "What should you test?"

**Answer:**

- **Business rules** — each state transition and each constraint, with
  a case that should fail.
- **Security** — run the same action as a normal user with `with_user`.
  Check that a forbidden action raises `AccessError`.
- **Computed fields** — change a dependency and check the result
  updates.
- **Query count** — `with self.assertQueryCount(5):` fails the test if
  a change adds queries. This guards against N+1 coming back.

## 7. "Where does AI help?"

**Answer:**

- Good at drafting test boilerplate and listing edge cases for a
  method.
- Check that tests really assert behavior, not just that code ran. Make
  sure security tests use a non-admin user.
- A strong answer to "how do you code with AI?" says you review
  generated queries for N+1 and ask for a query-count test.
  See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 8. Interview Questions You're Likely to Get Asked

**Performance**

- "What is prefetching?" — expects batch loading of a field for the whole
  recordset, [§1](#1-how-does-odoo-load-data-and-what-is-the-n1-problem).
- "A list view is slow. How do you debug it?" — expects SQL logging,
  profiler, N+1 check, non-stored computed fields,
  [§4](#4-how-do-you-find-a-slow-query).
- "How do you total a field across thousands of records?" — expects
  `read_group` in the database, [§2](#2-how-do-you-aggregate-without-loading-every-record).

**Testing**

- "Why use `TransactionCase`?" — expects rollback per test,
  [§5](#5-what-are-the-main-test-classes).
- "How do you test an `onchange`?" — expects `Form`,
  [§5](#5-what-are-the-main-test-classes).
- "How do you stop N+1 coming back?" — expects `assertQueryCount`,
  [§6](#6-what-should-you-test).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Related: [Odoo Inheritance & Customization](odoo-inheritance.md).
