---
title: "SQL & Relational Data Modeling"
---

# SQL & Relational Data Modeling

Schema design fundamentals — normalization, keys, relationships, JOIN
types, and constraints — as distinct from
[PostgreSQL for Scale](postgresql-for-scale.md), which covers indexing,
replication, and sharding for a schema that's already well-designed.
Flagged from the BJIT Senior Python Developer JD's "Proficient in SQL
(data modeling and structuring relational databases)" requirement.

## 1. "Given a flat, spreadsheet-style requirement, walk through normalizing it into proper tables."

```sql
-- Flat / unnormalized: one row per order, customer + product info repeated
-- order_id | customer_name | customer_email | product_name | product_price | qty

-- Normalized into three tables:
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL
);
```

**Answer:**

- **1NF (First Normal Form)** — every column holds a single, atomic
  value, no repeating groups. A `product_names` column holding a
  comma-separated list violates this.
- **2NF** — every non-key column depends on the *whole* primary key,
  not just part of it. Only matters with composite keys — a table
  keyed on `(order_id, product_id)` shouldn't also store
  `customer_email`, since that depends only on `order_id`.
- **3NF** — every non-key column depends on the key and *nothing but*
  the key. `customer_email` doesn't belong in `orders` at all — it
  depends on `customer_id`, not on the order itself, so it belongs in
  `customers`.
- The practical version of all three: **if updating one fact requires
  updating it in multiple rows, the schema isn't normalized yet.**
  Repeating `customer_email` on every order row means an email change
  requires updating every one of that customer's orders — normalizing
  it into `customers` means updating one row.

**Likely follow-up — "what actually goes wrong if you skip this?"**

- **Update anomalies** — the same fact stored in multiple places can
  drift out of sync (one order row gets the customer's new email,
  another doesn't).
- **Insertion anomalies** — can't add a new product until someone
  orders it, if product data only exists embedded in order rows.
- **Deletion anomalies** — deleting a customer's only order also
  deletes the only record of their email, if it was never split out.

| Pros | Cons / Trade-offs |
|---|---|
| No duplicated data — one place to update a fact, no drift | More tables means more JOINs to reconstruct the full picture |
| Insertion/deletion anomalies structurally can't happen | Over-normalizing (deep normal forms beyond 3NF) can hurt read performance for little real benefit |
| Matches how Django/DRF model relationships map naturally to normalized tables | Requires understanding the data's actual dependencies up front, not just listing columns |

## 2. "Primary keys vs. foreign keys — and how do you model a many-to-many relationship?"

```sql
-- Many-to-many needs a junction table -- neither side can hold
-- a simple foreign key, since either side can relate to many of the other.
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL
);

CREATE TABLE enrollments (
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id INTEGER NOT NULL REFERENCES courses(id),
    enrolled_at TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (student_id, course_id)  -- composite key: a student
                                          -- can't enroll in the same
                                          -- course twice
);
```

**Answer:**

- A **primary key** uniquely identifies a row within its own table. A
  **foreign key** references a primary key in another table, enforcing
  that the referenced row actually exists (referential integrity).
- **One-to-many** (one customer, many orders): the foreign key lives on
  the "many" side — `orders.customer_id`.
- **Many-to-many** (students and courses: a student takes many courses,
  a course has many students): neither table can hold a single foreign
  key to the other. A **junction table** (`enrollments`) sits between
  them, holding a foreign key to each side — this is the standard,
  only correct way to model M:M in a relational schema.
- The junction table's own primary key is often a **composite key**
  (both foreign keys together), which also enforces "a student can't
  enroll in the same course twice" as a side effect of the schema
  itself, not application code.
- In Django, this is exactly what `ManyToManyField` generates under
  the hood — the framework creates the junction table for you, and
  `through=` lets you use a custom one (e.g. to add `enrolled_at`).

**Likely follow-up — "when would you use a custom `through` model instead of a plain `ManyToManyField`?"**

- As soon as the relationship itself has data — `enrolled_at`, a
  `role` on a membership, a `quantity` on an order line — the junction
  table stops being just a bridge and becomes a real entity with its
  own attributes, which Django's plain `ManyToManyField` can't hold.

| Pros | Cons / Trade-offs |
|---|---|
| Foreign keys enforce referential integrity at the database level, not just in application code | Every relationship traversal costs a JOIN — more tables than a denormalized flat structure |
| Junction table naturally prevents duplicate M:M pairs via a composite key | A junction table with meaningful data of its own needs to be modeled explicitly (Django's `through=`), not left implicit |
| Matches Django's own `ManyToManyField` implementation — same mental model | Composite primary keys are less common knowledge than a simple auto-incrementing `id` |

## 3. "Walk through the JOIN types and when each is actually correct."

```sql
-- INNER JOIN: only rows with a match on both sides
SELECT c.name, o.id
FROM customers c
INNER JOIN orders o ON o.customer_id = c.id;

-- LEFT JOIN: every customer, even those with zero orders (o.id is NULL for them)
SELECT c.name, o.id
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id;

-- Self-join: find employees who share the same manager
SELECT e1.name, e2.name AS coworker
FROM employees e1
JOIN employees e2 ON e1.manager_id = e2.manager_id AND e1.id <> e2.id;
```

**Answer:**

- **INNER JOIN** — only rows where both sides match. Use when a row
  without a match is meaningless for the question being asked ("orders
  and their customers" — an order without a customer shouldn't exist).
- **LEFT JOIN** — every row from the left table, with `NULL`s filled in
  for unmatched right-side columns. Use when the absence of a match
  *is* the answer — "which customers have never ordered anything"
  is a `LEFT JOIN ... WHERE o.id IS NULL`.
- **RIGHT JOIN** — the mirror of `LEFT JOIN`; rarely used in practice
  since swapping table order and using `LEFT JOIN` reads more naturally.
- **FULL OUTER JOIN** — everything from both sides, matched where
  possible, `NULL`-filled where not. Rare — mostly for reconciliation
  ("what's in table A but not B, and vice versa, in one query").
- **Self-join** — a table joined to itself, for relationships within
  one table (employees and their manager, both rows drawn from the
  same `employees` table). Needs table aliases (`e1`, `e2`) since the
  table name alone is ambiguous.

**Likely follow-up — "what's the actual difference between filtering in the `ON` clause vs. the `WHERE` clause on a LEFT JOIN?"**

- A condition in `ON` is applied *while matching*, before rows are
  combined — unmatched left rows still appear, with `NULL` on the
  right side.
- The same condition in `WHERE` is applied *after* the join completes —
  it can filter out the unmatched (`NULL`) rows entirely, silently
  turning what looked like a `LEFT JOIN` back into an effective `INNER
  JOIN`. This is a genuinely common, subtle bug.

| Pros | Cons / Trade-offs |
|---|---|
| INNER JOIN is the simplest and usually correct default for "related records" queries | Easy to reach for INNER JOIN when the question actually needs LEFT (e.g. "customers with no orders") |
| LEFT JOIN cleanly answers "does X have zero of Y" questions | A WHERE clause filter on the right table can silently undo the LEFT JOIN's purpose |
| Self-joins reuse one table for hierarchical/peer relationships without denormalizing | Self-joins need careful aliasing — easy to write an ambiguous or wrong condition |

## 4. "When would you deliberately denormalize a schema?"

**Answer:**

- Normalization optimizes for **write correctness and no duplication**;
  denormalization trades some of that for **read performance** — fewer
  JOINs needed to answer a common query.
- Classic case: a `product_name` and `product_price` snapshot stored
  directly on an `order_line` row, even though that duplicates data
  already in `products`. Reason: an order should show what the price
  *was at the time of purchase*, not the product's current price — this
  isn't really denormalization for performance, it's a case where the
  normalized model was actually wrong (order lines and current product
  price are different facts that shouldn't share a row).
- Genuine performance denormalization: a `posts.comment_count` column,
  updated on insert/delete, instead of `COUNT(*)` over a `comments`
  table on every page load. Trades a small write-time cost (updating
  one extra column) for a much cheaper read.
- This is the same territory as
  [the JSONB question in PostgreSQL for Scale](postgresql-for-scale.md#5-when-does-jsonb-in-postgres-make-sense-vs-a-normalized-column-or-vs-reaching-for-mongo) —
  denormalization and "store it as JSONB instead of a normalized
  column" are the same underlying trade-off (read simplicity vs. write
  correctness/queryability) at different scales.

**Likely follow-up — "how do you keep a denormalized counter from drifting out of sync?"**

- Update it in the same transaction as the write that changes the
  count (insert a comment → increment the counter, both committed
  together) rather than a separate, possibly-failing follow-up step.
- Periodically reconcile with a real `COUNT(*)` in a background job as
  a safety net — denormalized counters drift eventually from missed
  edge cases (a failed transaction that partially applied, a manual DB
  fix), and a reconciliation job catches that before it compounds.

| Pros | Cons / Trade-offs |
|---|---|
| Meaningfully faster reads for expensive aggregate/JOIN-heavy queries | Duplicated data can drift out of sync if not updated carefully |
| Avoids re-computing the same expensive query on every request | Every write path that affects the denormalized value needs updating — easy to miss one |
| A snapshot column (price-at-purchase) can be the *correct* model, not just a performance hack | Denormalizing too early, before a real performance problem exists, adds complexity for no benefit |

## 5. "Beyond what the Django ORM validates, what would you enforce at the database level?"

```sql
ALTER TABLE orders
    ADD CONSTRAINT quantity_positive CHECK (quantity > 0);

ALTER TABLE customers
    ADD CONSTRAINT email_unique UNIQUE (email);

ALTER TABLE orders
    ADD CONSTRAINT fk_customer
    FOREIGN KEY (customer_id) REFERENCES customers(id)
    ON DELETE RESTRICT;  -- vs. CASCADE, SET NULL
```

**Answer:**

- Application-level validation (Django form/serializer validation) only
  protects data written *through that code path* — a direct DB write,
  a data migration, a bug that bypasses validation, or another service
  sharing the same database won't go through it. Database constraints
  are the actual last line of defense.
- **`NOT NULL`** — enforce required fields at the schema level, not
  just `required=True` on a serializer.
- **`UNIQUE`** — enforce uniqueness atomically; checking "does this
  email already exist" in application code before inserting has a race
  condition (two requests both check "no match" before either inserts)
  that a `UNIQUE` constraint closes entirely.
- **`CHECK`** — enforce invariants like "quantity must be positive"
  directly in the schema.
- **Foreign key `ON DELETE` behavior** maps directly to Django's
  `on_delete` argument: `CASCADE` (delete dependents too), `RESTRICT`/
  `PROTECT` (refuse the delete if dependents exist), `SET NULL` (null
  out the reference). Knowing the DB-level semantics is what makes
  Django's `on_delete` choice a real decision instead of a default left
  on autopilot.

**Likely follow-up — "why not just rely on Django's validation and skip the DB constraints?"**

- Django's validation is bypassed by `bulk_create` (skips `save()` and
  therefore model-level validation), raw SQL, migrations that backfill
  data, and any other service that touches the same database — a
  constraint at the DB level is the only guarantee that holds
  regardless of which code path writes the row.

| Pros | Cons / Trade-offs |
|---|---|
| DB constraints hold regardless of which code path writes the data — the actual last line of defense | A constraint violation surfaces as a raw DB error, needs translating into a friendly application-level message |
| `UNIQUE` closes race conditions that an application-level "check then insert" can't | Migrations that add a constraint can fail against existing data that already violates it |
| `ON DELETE` behavior makes cascade/restrict/null-out an explicit, reviewable schema decision | Overly strict constraints can make legitimate edge-case data operations harder than they should be |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable schema-design exercise (flat requirement → normalized schema
→ Django models) added under `code_samples/`.
