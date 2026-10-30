//! sqlx demo against PostgreSQL. Start a database first (see the page), then:
//!   export DATABASE_URL=postgres://postgres:demo@localhost:55432/demo
//!   cargo run
//! The `query!`/`query_as!` macros check SQL against the live database at
//! COMPILE time (or against the saved `.sqlx/` data when SQLX_OFFLINE=true).

use sqlx::postgres::PgPoolOptions;
use sqlx::{PgPool, Postgres, Transaction};
use std::time::Duration;

#[derive(Debug)]
struct Book {
    id: i64,
    title: String,
    pages: Option<i32>, // nullable column -> Option
}

async fn add_author_with_books(pool: &PgPool, name: &str, titles: &[&str]) -> sqlx::Result<i64> {
    let mut tx: Transaction<'_, Postgres> = pool.begin().await?;
    let author_id =
        sqlx::query_scalar!("INSERT INTO authors (name) VALUES ($1) RETURNING id", name)
            .fetch_one(&mut *tx)
            .await?;
    for t in titles {
        sqlx::query!(
            "INSERT INTO books (author_id, title) VALUES ($1, $2)",
            author_id,
            t
        )
        .execute(&mut *tx)
        .await?;
    }
    tx.commit().await?; // dropping `tx` without commit rolls back
    Ok(author_id)
}

async fn books_of(pool: &PgPool, author_id: i64) -> sqlx::Result<Vec<Book>> {
    sqlx::query_as!(
        Book,
        "SELECT id, title, pages FROM books WHERE author_id = $1 ORDER BY id",
        author_id
    )
    .fetch_all(pool)
    .await
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let url = std::env::var("DATABASE_URL")?;
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .acquire_timeout(Duration::from_secs(3))
        .connect(&url)
        .await?;

    sqlx::migrate!("./migrations").run(&pool).await?; // embedded at compile time
    sqlx::query!("TRUNCATE books, authors RESTART IDENTITY CASCADE")
        .execute(&pool)
        .await?;

    let a = add_author_with_books(&pool, "Ada", &["Notes", "More Notes"]).await?;
    let b = add_author_with_books(&pool, "Bob", &["Pipes"]).await?;
    let ada = books_of(&pool, a).await?;
    println!(
        "books of Ada: {} (first: #{} {:?}, pages {:?})",
        ada.len(),
        ada[0].id,
        ada[0].title,
        ada[0].pages
    );

    // A failing transaction rolls back everything it did.
    let dup = add_author_with_books(&pool, "Ada", &["Never saved"]).await;
    println!("duplicate author: {}", dup.unwrap_err());
    let n = sqlx::query_scalar!("SELECT count(*) FROM books")
        .fetch_one(&pool)
        .await?;
    println!("books after rollback: {}", n.unwrap_or(0));

    // N+1: one query for the authors, then one query PER author.
    let authors = sqlx::query!("SELECT id, name FROM authors ORDER BY id")
        .fetch_all(&pool)
        .await?;
    let mut n_plus_one = 0;
    for au in &authors {
        let bs = books_of(&pool, au.id).await?; // N extra round trips
        n_plus_one += bs.len();
    }
    println!(
        "N+1 style: {} queries, {} books",
        1 + authors.len(),
        n_plus_one
    );

    // Fix: one JOIN (or `WHERE author_id = ANY($1)`) and group in Rust.
    let rows = sqlx::query!(
        r#"SELECT a.name, b.title AS "title?" FROM authors a LEFT JOIN books b ON b.author_id = a.id ORDER BY a.id, b.id"#
    )
    .fetch_all(&pool)
    .await?;
    println!("JOIN style: 1 query, {} rows", rows.len());
    let ids = [a, b];
    let any = sqlx::query_as!(
        Book,
        "SELECT id, title, pages FROM books WHERE author_id = ANY($1)",
        &ids[..]
    )
    .fetch_all(&pool)
    .await?;
    let first = &any[0];
    println!(
        "ANY($1) style: 1 query, {} books (first: #{} {:?}, pages {:?})",
        any.len(),
        first.id,
        first.title,
        first.pages
    );

    // Pool behaviour: hold every connection, the next acquire times out.
    let held: Vec<_> = futures_hold(&pool, 5).await;
    let err = pool.acquire().await.unwrap_err();
    println!("pool exhausted: {err}");
    drop(held);
    Ok(())
}

async fn futures_hold(pool: &PgPool, n: usize) -> Vec<sqlx::pool::PoolConnection<Postgres>> {
    let mut v = Vec::new();
    for _ in 0..n {
        v.push(pool.acquire().await.unwrap());
    }
    v
}
