---
title: Databases in Rust
---

# Databases in Rust

A database driver in Rust does the same job as in any language: send SQL
(Structured Query Language) over a network connection and turn the rows
back into values. Rust adds two things. First, the **types** of your
queries can be **checked by the compiler** against the real schema.
Second, a **connection pool** has to live inside an async program, where
"waiting for a connection" is an `.await`, not a blocked thread. This page
uses **`sqlx`**, because it is async and checks SQL at compile time, and
compares it with **Diesel** and **SeaORM**.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Sample run against
    **PostgreSQL 17** (Docker image `postgres:17-alpine`) with `sqlx` 0.9.0,
    `sqlx-cli` 0.9.0 and `tokio` 1.54.1. Latest versions on crates.io when
    written: `diesel` 2.3.14, `sea-orm` 2.0.4. **Diesel and SeaORM were not
    run for this page**; their descriptions come from the project
    documentation, not from code compiled here.

## 1. "Which Rust database library should I use?"

**Answer:**

- **The choice is how much the library does for you.** From "you write SQL"
  to "you never see SQL":

| Library | Style | Async | What you get | What it costs |
|---|---|---|---|---|
| **`sqlx`** | You write SQL; macros check it | Yes, built in | Compile-time checked queries, pools, migrations, no DSL (Domain-Specific Language) | You write the SQL and the mapping |
| **Diesel** | Query-builder DSL in Rust | No (sync); the separate `diesel-async` crate adds async | Queries checked through generated `schema.rs` types; very strong typing | Heavy generic types, long compile errors, sync by default |
| **SeaORM** | Object-relational mapper (ORM) | Yes (built on `sqlx`) | Entities, relations, a query builder | More abstraction, more generated code |

- Start with `sqlx` when you know SQL and want to see what runs. Choose
  Diesel when you want the compiler to build the query for you. Choose
  SeaORM when the team expects an ORM.
- **Every one of them** needs the same ideas from this page: a pool,
  transactions, migrations, and care about N+1.

## 2. "What does `sqlx` check at compile time, and how?"

```rust
#[derive(Debug)]
struct Book {
    id: i64,
    title: String,
    pages: Option<i32>, // nullable column -> Option
}

async fn books_of(pool: &PgPool, author_id: i64) -> sqlx::Result<Vec<Book>> {
    sqlx::query_as!(Book, "SELECT id, title, pages FROM books WHERE author_id = $1 ORDER BY id", author_id)
        .fetch_all(pool)
        .await
}
```

**Answer:**

- The `query!`, `query_as!` and `query_scalar!` macros **connect to your
  database while the compiler runs**. The database's `DATABASE_URL` comes
  from the environment (or a `.env` file). They ask PostgreSQL to parse
  the query and describe its parameter and column types. Then the macro
  generates Rust code with exactly those types.
- That gives you, at compile time: the table and columns exist, the number
  and types of `$1`, `$2` parameters match, and nullable columns are
  `Option<T>`.
- A typo in a column name is a **compile error**, not a runtime one. Real
  output:

```text
error: error returned from database: column "nam" does not exist at line 3723
  --> src/main.rs:62:19
   |
62 |     let authors = sqlx::query!("SELECT id, nam FROM authors ORDER BY id").fetch_all(&pool).await?;
```

- A wrong Rust type for a nullable column is also caught: declaring
  `pages: i32` for a nullable column fails with
  the error "the trait bound `i32: From<Option<i32>>` is not satisfied".
- **The catch:** the database must already have the tables when you
  compile. The first build against an empty database fails with:

```text
error: error returned from database: relation "authors" does not exist at line 1449
  --> src/main.rs:20:21
```

  Run `sqlx migrate run` first (§4). Then build.
- There are also **unchecked** functions: `sqlx::query("SELECT ...")` and
  `query_as::<_, T>(..)` with `#[derive(sqlx::FromRow)]`. They check
  nothing at compile time. Use them when SQL is built dynamically.

## 3. "How do I build in CI or on a machine with no database?"

**Answer:**

- **Offline mode.** With a database reachable, run
  `cargo sqlx prepare`. It writes one JSON file per query into a `.sqlx/`
  folder (8 files for the sample). **Commit that folder.**
- Then set `SQLX_OFFLINE=true`. The macros read the saved files instead of
  connecting. Verified with the sample: with `DATABASE_URL` removed and
  `SQLX_OFFLINE=true`, `cargo build` succeeds.
- In CI add a check that `.sqlx/` is **up to date**:
  `cargo sqlx prepare --check` fails if a query changed and the files did
  not. Without it, the saved data silently goes stale.
- This is the same idea as a lock file: the checked queries are a
  recorded fact about the schema.

## 4. "How do migrations work?"

```bash
cargo install sqlx-cli --no-default-features --features rustls,postgres
export DATABASE_URL=postgres://postgres:demo@localhost:55432/demo
sqlx database create
sqlx migrate add create_authors_and_books     # creates migrations/<timestamp>_create_authors_and_books.sql
sqlx migrate run
```

```rust
sqlx::migrate!("./migrations").run(&pool).await?; // embedded in the binary at compile time
```

**Answer:**

- A migration is a numbered SQL file. `sqlx` records each applied one in a
  `_sqlx_migrations` table, with a **checksum**. If you edit a migration
  that was already applied, the next run fails. Never edit applied
  migrations; add a new one.
- `sqlx::migrate!("./migrations")` **embeds** the files in the binary, so
  the program can migrate itself at startup. The real output of
  `sqlx migrate run` for the sample:

```text
Applied 20261030163318/migrate create authors and books (9.0435ms)
```

- Run migrations at startup only for small services. With several
  instances, prefer a **separate migration step** in the deploy (one
  runner, before the new code starts).
- **Safe schema changes** are an old problem, not a Rust one: add a column
  as nullable first, deploy the code, backfill, then add `NOT NULL`. Never
  drop a column the running version still reads.

## 5. "How does the connection pool work, and how big should it be?"

```rust
let pool = PgPoolOptions::new()
    .max_connections(5)
    .acquire_timeout(Duration::from_secs(3))
    .connect(&url)
    .await?;
```

**Answer:**

- A **pool** keeps a set of open connections and lends them out.
  Opening a PostgreSQL connection is slow (network, authentication, a new
  server process), so you reuse them. `PgPool` is cheap to `clone`
  (it is a handle) and is what you put in the application state (see
  [Web Services with Axum §5](rust-web-services-with-axum.md#5-how-do-i-share-state-between-handlers)).
- Defaults in `sqlx` (from its source): `max_connections` **10**,
  `acquire_timeout` **30 s**, `idle_timeout` 10 min, `max_lifetime`
  30 min.
- When all connections are in use, `pool.acquire()` **waits**. After the
  timeout it returns an error. The sample holds all 5 connections and
  asks for a sixth:

```text
pool exhausted: pool timed out while waiting for an open connection
```

- **Sizing.** There is no magic number. The facts:
    - PostgreSQL has a hard limit (`max_connections`, 100 by default)
      shared by **all** service instances. `instances x pool size` must fit
      under it, with room for admin and migration connections.
    - A database can only do so much in parallel (about its CPU count).
      More connections than that mostly add queueing and memory.
    - Start small (for example 5 to 10 per instance), measure the wait
      time to acquire, and raise it only when you see waiting.
    - For many instances, put **PgBouncer** (a connection pooler) in front.
- **Never hold a connection while doing slow non-database work** (an HTTP
  call, a sleep). Fetch, release, then work. A leaked or held connection is
  the usual cause of "everything times out".
- Set a short `acquire_timeout`. A request that fails fast is better than
  one that waits 30 s and then fails anyway.

## 6. "How do transactions work in `sqlx`?"

```rust
async fn add_author_with_books(pool: &PgPool, name: &str, titles: &[&str]) -> sqlx::Result<i64> {
    let mut tx = pool.begin().await?;
    let author_id = sqlx::query_scalar!("INSERT INTO authors (name) VALUES ($1) RETURNING id", name)
        .fetch_one(&mut *tx)
        .await?;
    for t in titles {
        sqlx::query!("INSERT INTO books (author_id, title) VALUES ($1, $2)", author_id, t)
            .execute(&mut *tx)
            .await?;
    }
    tx.commit().await?; // dropping `tx` without commit rolls back
    Ok(author_id)
}
```

**Answer:**

- `pool.begin()` takes one connection and starts a transaction. You pass
  `&mut *tx` as the executor so every query uses that same connection.
- **Rollback is automatic.** If `?` returns early, or the future is
  dropped, `tx` is dropped without `commit`, and the transaction rolls
  back. This is the RAII (Resource Acquisition Is Initialization) idea
  from [Ownership §4](../foundations/rust-ownership-and-borrowing.md#4-when-exactly-are-values-dropped-and-in-what-order),
  applied to a database.
- Verified in the sample: adding a second author named "Ada" fails on the
  `UNIQUE` constraint, and the books count stays at 3 (Ada's two books
  plus Bob's "Pipes"), so nothing from the failed call remained:

```text
duplicate author: error returned from database: duplicate key value violates unique constraint "authors_name_key" at line 666
books after rollback: 3
```

- Keep transactions **short**. Do not `.await` slow things inside one;
  it holds a connection and row locks.
- A function taking `&mut Transaction` or `impl Executor` can run inside
  or outside a transaction; this is the standard way to compose
  repository calls.

## 7. "What is the N+1 problem, and how do I fix it?"

**Answer:**

- **N+1:** one query loads N parent rows, then the code runs **one more
  query for each parent** to load its children. The cost is N round trips
  to the database instead of 1. It looks fine with 10 rows in a test and
  breaks at 10,000 in production.
- It is easy to write in any language, and ORMs hide it well. With `sqlx`
  it is visible because every query is explicit.
- The sample runs both ways on 2 authors and 3 books (real output):

```text
N+1 style: 3 queries, 3 books
JOIN style: 1 query, 3 rows
ANY($1) style: 1 query, 3 books
```

- Fixes:
    - **`JOIN`**: one query returns parent and child columns together.
      Group the rows in Rust. Use `LEFT JOIN` to keep parents with no
      children, and mark the child columns as nullable with the
      `AS "title?"` override so the macro gives `Option`.
    - **`WHERE parent_id = ANY($1)`** with a slice: one query for all
      children, then group by `parent_id` in a `HashMap`. `sqlx` sends the
      slice as a PostgreSQL array.
- Always **index the foreign key** (`books.author_id`). The sample's
  migration creates the index. PostgreSQL does **not** index foreign key
  columns for you.

## 8. "How should I structure database code?"

**Answer:**

- Keep SQL in **one module** (a "repository"), behind functions or a trait
  that return **your own types**, not rows. The rest of the program never
  imports `sqlx`.
- The layered version of this idea, with a trait as the boundary, is in
  [Project Architecture §3](rust-project-architecture-and-api-design.md#3-how-do-i-keep-the-core-free-of-databases-and-frameworks).
- Test repository code against a **real database** (a container or a
  throwaway schema), not a mock. A mock cannot tell you the SQL is
  wrong. `sqlx` also provides `#[sqlx::test]`, which gives each test its
  own temporary database (not run here).
- Map database errors to your own error type at this boundary
  (unique violation to `AlreadyExists`, no rows to `NotFound`). The caller
  should not need to know it was PostgreSQL.
- Use the database's strengths: constraints (`UNIQUE`, `CHECK`,
  foreign keys) enforce rules even when two requests race. The sample's
  duplicate-author failure came from a constraint, not from code.

## 9. "How do AI tools help or hurt with database code?"

**Answer:**

- Good for: writing the SQL, migrations, and the `Option`-for-nullable
  struct mapping, and for translating a Diesel query into SQL or back.
- They often use **runtime** `query()` with string building, which loses
  every check on this page. Ask for `query_as!`.
- They invent `sqlx` APIs from older versions (0.5 to 0.7). A compile error
  in a `sqlx` call is usually a version mismatch; check the docs for the
  version in `Cargo.toml`.
- They produce N+1 loops without noticing. A useful review prompt: "List
  every query that runs inside a loop."
- Never paste real connection strings or production data into a prompt.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Choosing**

- "`sqlx` or Diesel or SeaORM?" — expects the spectrum: SQL checked by
  macros, DSL with strong types (sync), ORM on `sqlx`,
  [§1](#1-which-rust-database-library-should-i-use).
- "What does `query!` do at compile time?" — expects it connects to the
  database, so SQL errors are compile errors,
  [§2](#2-what-does-sqlx-check-at-compile-time-and-how).

**Practical**

- "How do you build `sqlx` code in CI without a database?" — expects
  `cargo sqlx prepare`, commit `.sqlx/`, `SQLX_OFFLINE=true`, and a
  `--check` step,
  [§3](#3-how-do-i-build-in-ci-or-on-a-machine-with-no-database).
- "What happens if you edit an applied migration?" — expects the checksum
  check fails; write a new migration,
  [§4](#4-how-do-migrations-work).
- "What happens to a transaction when the function returns early?" —
  expects drop without commit rolls back,
  [§6](#6-how-do-transactions-work-in-sqlx).

**Production**

- "How do you size a connection pool?" — expects instances x pool under
  the server limit, start small, measure acquire wait, PgBouncer,
  [§5](#5-how-does-the-connection-pool-work-and-how-big-should-it-be).
- "What is N+1, and how do you fix it?" — expects the loop of queries,
  `JOIN` or `= ANY($1)`, an index on the foreign key,
  [§7](#7-what-is-the-n1-problem-and-how-do-i-fix-it).
- "Why is a long transaction bad?" — expects held connection and locks,
  [§6](#6-how-do-transactions-work-in-sqlx).

---

## Code Samples

Package `code_samples/rust/sqlx_demo/` (own `Cargo.toml`; Rust 1.99.1,
`sqlx` 0.9.0). It was run against a real PostgreSQL 17 container.

- `src/main.rs` — pool, embedded migrations, a transaction with rollback,
  N+1 versus `JOIN` versus `ANY($1)`, and pool exhaustion.
- `migrations/*_create_authors_and_books.sql` — the schema, with the
  foreign key index.
- `.sqlx/` — the saved query data for offline builds (commit it).

```bash
cd code_samples/rust/sqlx_demo
docker run -d --rm --name rust-demo-pg -e POSTGRES_PASSWORD=demo -e POSTGRES_DB=demo \
  -p 55432:5432 postgres:17-alpine
export DATABASE_URL=postgres://postgres:demo@localhost:55432/demo
cargo install sqlx-cli --no-default-features --features rustls,postgres
sqlx migrate run          # create the tables BEFORE compiling the macros
cargo run
SQLX_OFFLINE=true cargo build      # no database needed (uses .sqlx/)
docker stop rust-demo-pg
```
