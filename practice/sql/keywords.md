# SQL Keyword Glossary

Every keyword used in `schema.sql`, `problems.md`, and `solutions.md`,
explained. Organized by where it shows up: schema definition first, then
query keywords roughly in the order you'd reach for them.

## Schema definition (`schema.sql`)

**`CREATE TABLE`** — defines a new table's columns and their types/
constraints. Nothing to do with querying data — this is schema setup.

**`DROP TABLE`** — deletes a table (and its data) entirely. `schema.sql`
uses `DROP TABLE IF EXISTS` so the script can be re-run safely to reset
the sandbox.

**`IF EXISTS`** — modifier on `DROP TABLE` (and other statements) that
suppresses the error if the thing being dropped doesn't exist yet — first
run vs. a reset behave the same way.

**`INTEGER` / `TEXT`** — column data types. `INTEGER` for whole numbers
(`id`, `salary`), `TEXT` for strings (`name`, `hire_date` — stored as
text here, SQLite doesn't have a dedicated date type).

**`PRIMARY KEY`** — marks a column as the table's unique row identifier.
In SQLite, `INTEGER PRIMARY KEY` also auto-increments.

**`NOT NULL`** — a constraint: this column can never be left empty
(`NULL`) on any row.

**`REFERENCES`** — declares a foreign key: `employees.department_id
REFERENCES departments(id)` means every `department_id` value must
correspond to a real row in `departments`. This is what makes the
`JOIN`s in every practice query meaningful — the relationship is
enforced, not just assumed.

**`INSERT INTO ... VALUES`** — adds rows to a table. `schema.sql` uses
this to seed the 4 departments and 16 employees.

## Selecting and filtering

**`SELECT`** — the query itself starts here: which columns (or
expressions) end up in the output.

**`AS`** — renames a column or expression in the output (an "alias").
`d.name AS department_name` — without it, both `employees.name` and
`departments.name` would show up in the result as ambiguous `name`
columns.

**`FROM`** — which table (or subquery) the rows come from.

**`JOIN ... ON`** — combines rows from two tables where the `ON`
condition matches. `JOIN departments d ON e.department_id = d.id` pairs
each employee with their department row. (Plain `JOIN` here means `INNER
JOIN` — only rows with a match on both sides survive; see the
[SQL page](../../docs/sql.md) for when you'd reach for `LEFT JOIN`
instead.)

**`WHERE`** — filters individual rows, evaluated *before* any grouping
or window functions. Used in problem 5 to narrow to one department
(`WHERE department_id = 40`) and in problem 6's outer query to keep only
`rn <= 2`.

**`ORDER BY`** — sorts the final result set. `DESC` = descending (highest
first); ascending is the default and rarely written explicitly.

## Aggregation

**`GROUP BY`** — collapses multiple rows into one row per distinct value
of the grouped column(s). This is the operation that's easy to reach for
by reflex when what you actually want is a window function (see
`solutions.md` problem 4 vs. `GROUP BY` — they solve different
problems).

**`HAVING`** — filters *after* grouping/aggregation, on the aggregated
value itself (e.g. `HAVING AVG(e.salary) > 65000`). `WHERE` can't do
this because at the point `WHERE` is evaluated, the aggregate (`AVG`)
doesn't exist yet.

**`AVG()` / `SUM()`** — aggregate functions: compute one value across a
group of rows. Used both as plain aggregates (problem 2/3) and inside a
window function (problem 7's running-total `SUM`).

## Window functions

**`OVER (...)`** — turns a function into a *window function*: instead of
collapsing rows (like `GROUP BY` + an aggregate would), it computes a
value for each row based on a "window" of related rows, while keeping
every row in the output. Everything inside the parentheses configures
that window.

**`PARTITION BY`** — inside `OVER(...)`, splits the rows into independent
groups (e.g. one per department) before the rest of the window logic
runs. Analogous to `GROUP BY`, but without collapsing rows.

**`RANK()`** — assigns a rank per partition based on the `ORDER BY`
inside `OVER(...)`; ties get the same rank, and the next rank *skips*
(1, 1, 3).

**`DENSE_RANK()`** — same as `RANK()`, but the next rank after a tie
*doesn't skip* (1, 1, 2).

**`ROW_NUMBER()`** — assigns a strictly unique, increasing number per
partition regardless of ties (1, 2, 3, 4...) — ties are broken
arbitrarily. This is why it's the right tool for "exactly N rows per
group" (problem 6), where `RANK`/`DENSE_RANK` can let extra tied rows
through.

**`LEAD(column)`** — looks forward to the *next* row within the
partition's `ORDER BY` sequence and returns that row's value for
`column`; `NULL` if there is no next row.

**`LAG(column)`** — same as `LEAD`, but looks *backward* to the previous
row instead.

**`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`** — explicitly
defines the window frame for problem 7's running total: "every row from
the start of the partition through the current row, counted
individually." Worth writing explicitly rather than relying on the
engine's default frame, which (under `RANGE`) can silently merge tied
`ORDER BY` values into one combined step.

## Subqueries

**`FROM (SELECT ... ) alias`** — a subquery used as a table. Needed in
problem 6 because a window-function output (`rn`) can't be filtered in
`WHERE` in the *same* query that computes it — the inner query computes
`rn` first, and the outer query then filters on it as if it were an
ordinary column.
