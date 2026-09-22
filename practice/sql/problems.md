# SQL Practice — Problem Set

Uses `practice.db` (built from `schema.sql`): 4 departments, 16
employees. Run each problem against the real database, don't just
reason about it on paper — open the shell and check your output:

```bash
sqlite3 practice/sql/practice.db
```

Then paste your query in. `.headers on` and `.mode column` make output
readable if you want it (optional).

Solutions are in `solutions.md` — don't open it until you've actually
run your own query and gotten a result you believe is right, wrong or
otherwise. Checking too early defeats the point.

---

**1. Warm-up join.** List every employee's name, department name, and
salary.

**2. Aggregate.** Average salary per department, highest first.

**3. HAVING.** Departments where the average salary is above 65000.

**4. Rank within group.** Each employee's name, department name, salary,
and salary rank within their department (1 = highest), ordered by
department then rank. (Same shape as the earlier session — redo it here
against real data.)

**5. Tie-handling trace.** For department 40 specifically (Mia, Noah,
Olivia, Peter — note the tie between Noah and Olivia), write out by hand
what `RANK()`, `DENSE_RANK()`, and `ROW_NUMBER()` would each produce,
*then* run the query and check yourself.

**6. Top-N per group.** Return only the top 2 highest-paid employees in
each department (name, department name, salary). Think about why
`RANK()`/`DENSE_RANK()` could return *more* than 2 rows for some
departments here, and which window function avoids that.

**7. Running total.** For each department, order employees by
`hire_date` (earliest first) and show a running total of salary as each
person joined — i.e. cumulative headcount cost over time per department.

**8. LAG/LEAD.** For each employee, show the salary of the *next-hired*
person in the same department (by `hire_date`), or `NULL` if they're the
most recent hire in their department.
