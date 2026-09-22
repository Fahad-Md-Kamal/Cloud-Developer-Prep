# SQL Practice — Solutions

Each query below was run against `practice.db` and the output shown is
real, not hand-computed. Check your own result against this after
attempting the problem, not before.

## 1. Warm-up join

```sql
SELECT e.name, d.name AS department_name, e.salary
FROM employees e
JOIN departments d ON e.department_id = d.id;
```

## 2. Average salary per department

```sql
SELECT d.name AS department_name, AVG(e.salary) AS avg_salary
FROM employees e
JOIN departments d ON e.department_id = d.id
GROUP BY d.name
ORDER BY avg_salary DESC;
```

## 3. HAVING

```sql
SELECT d.name AS department_name, AVG(e.salary) AS avg_salary
FROM employees e
JOIN departments d ON e.department_id = d.id
GROUP BY d.name
HAVING AVG(e.salary) > 65000;
```

Result: Engineering (82800.0), Sales (67750.0) — Marketing and Support
fall below the threshold and are filtered out. Note `HAVING` filters
*after* aggregation (on `AVG(salary)`), while `WHERE` would only be able
to filter on raw row values *before* grouping.

## 4. Rank within group

```sql
SELECT e.name, d.name AS department_name, e.salary,
    RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS salary_rank
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name, salary_rank;
```

## 5. Tie-handling trace (department 40)

```sql
SELECT name, salary,
    RANK() OVER (ORDER BY salary DESC) AS rnk,
    DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rnk,
    ROW_NUMBER() OVER (ORDER BY salary DESC) AS row_num
FROM employees
WHERE department_id = 40
ORDER BY salary DESC;
```

| name | salary | rnk | dense_rnk | row_num |
|---|---|---|---|---|
| Mia | 55000 | 1 | 1 | 1 |
| Noah | 52000 | 2 | 2 | 2 |
| Olivia | 52000 | 2 | 2 | 3 |
| Peter | 49000 | 4 | 3 | 4 |

Peter is the clearest signal: `RANK` jumps to 4 (skips 3, because two
rows tied for 2nd), `DENSE_RANK` doesn't skip (3), `ROW_NUMBER` doesn't
care about the tie at all and just keeps counting (4).

## 6. Top-N per group

```sql
SELECT name, department_name, salary
FROM (
    SELECT e.name, d.name AS department_name, e.salary,
        ROW_NUMBER() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS rn
    FROM employees e
    JOIN departments d ON e.department_id = d.id
) ranked
WHERE rn <= 2
ORDER BY department_name, salary DESC;
```

**Why the subquery is required:** window functions are computed *after*
`SELECT`/`WHERE` are logically evaluated, so you can't reference `rn` in
a `WHERE` clause in the same query that defines it — the engine doesn't
know about it yet at that stage. Wrapping it in a subquery (or a CTE)
computes `rn` first, then the outer query filters on it.

**Why `ROW_NUMBER` and not `RANK`/`DENSE_RANK` here** — this repo's data
makes the failure mode concrete. Every department has a tie for 2nd
place. Swap in `RANK()` and filter `WHERE rnk <= 2`:

```sql
SELECT name, department_name, salary
FROM (
    SELECT e.name, d.name AS department_name, e.salary,
        RANK() OVER (PARTITION BY e.department_id ORDER BY e.salary DESC) AS rnk
    FROM employees e
    JOIN departments d ON e.department_id = d.id
) ranked
WHERE rnk <= 2
ORDER BY department_name, salary DESC;
```

This returns **3 rows for every department** (Carol/Liam/Heidi/Olivia
all sneak in alongside their tied partner), not 2 — because `RANK` gives
both tied rows rank 2, and `rnk <= 2` keeps both. `ROW_NUMBER` always
assigns a strictly increasing, unique number, so `rn <= 2` guarantees
exactly 2 rows per group regardless of ties.

## 7. Running total

```sql
SELECT e.name, d.name AS department_name, e.hire_date, e.salary,
    SUM(e.salary) OVER (
        PARTITION BY e.department_id
        ORDER BY e.hire_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name, e.hire_date;
```

`SUM(...) OVER (... ORDER BY hire_date ROWS BETWEEN UNBOUNDED PRECEDING
AND CURRENT ROW)` is the running-total idiom: for each row, sum the
window function's target column over every row *from the start of the
partition up to and including the current row*, in `hire_date` order.
The explicit `ROWS BETWEEN` frame is worth including even though most
engines default to something equivalent when `ORDER BY` is present — the
default frame (`RANGE UNBOUNDED PRECEDING`) treats *tied* `ORDER BY`
values as one combined row, which silently changes the result if two
employees share a hire date. `ROWS BETWEEN` always treats each row
individually.

## 8. LAG/LEAD

```sql
SELECT e.name, d.name AS department_name, e.hire_date, e.salary,
    LEAD(e.salary) OVER (PARTITION BY e.department_id ORDER BY e.hire_date) AS next_hire_salary
FROM employees e
JOIN departments d ON e.department_id = d.id
ORDER BY d.name, e.hire_date;
```

`LEAD(column)` looks *forward* one row within the partition's `ORDER BY`
sequence; `LAG(column)` looks *backward* one row. The most recent hire in
each department (Erin, Liam, Ivan, Peter) has no "next hire," so
`next_hire_salary` is `NULL` for them — that's expected, not a bug.
