---
title: Web Services with Axum
---

# Web Services with Axum

A Rust web service is a few small libraries stacked on top of each other, not
one big framework. **Tokio** runs the async code and the network sockets.
**hyper** speaks HTTP (HyperText Transfer Protocol). **tower** defines one
tiny interface, "a service turns a request into a response," that
middleware plugs into. **Axum** sits on top and adds routing and
**extractors** (typed parts of the request, such as JSON or a path
parameter). Once you see that Axum is mostly thin glue over `tower`, the
whole ecosystem becomes easy to follow.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Sample run and
    tested with `axum` 0.8.9, `tokio` 1.54.1, `tower` 0.5.3 and
    `tower-http` 0.7.1. Every request/response shown below was produced
    by the sample in `code_samples/rust/axum_api/`.

## 1. "What does a Rust web stack look like, and where does Axum fit?"

**Answer:**

- Axum is **not** a server and **not** a runtime. It is a router plus
  extractors built on `tower` and `hyper`.
- Layers, bottom to top:

| Layer | Crate | Job |
|---|---|---|
| Runtime | `tokio` | Runs `async` tasks, owns the sockets (see [Async Internals](../concurrency-and-async/rust-async-internals.md)) |
| HTTP protocol | `hyper` | Parses and writes HTTP/1 and HTTP/2 |
| Service interface | `tower` | The `Service` trait and `Layer` (middleware) |
| Ready-made middleware | `tower-http` | Tracing, timeouts, CORS (Cross-Origin Resource Sharing), compression |
| Framework | `axum` | Routing, extractors, responses |

- **Why this matters:** an Axum `Router` **is** a `tower::Service`. So
  every `tower` and `tower-http` layer works with it, and you can test it
  without opening a socket (§7).
- Comparison with the other main frameworks (versions as of writing,
  from crates.io):

| Framework | Version | Character |
|---|---|---|
| **Axum** | 0.8.9 | Built on `tower`/`hyper`, from the Tokio team; macro-free routing; the common default |
| **Actix Web** | 4.18.1 | Older and very fast; runs on its own `actix-rt` runtime wrapper and has its own middleware system instead of `tower` |
| **Rocket** | 0.5.2 | Macro-heavy, very ergonomic, batteries included |

- Choose Axum when you want the `tower` ecosystem and the least magic.
  The others are fine choices; the decision is mostly about team taste.

## 2. "How do I build the smallest working Axum service?"

```rust
use axum::{Json, Router, extract::{Path, State}, routing::get};

#[tokio::main]
async fn main() {
    let app = Router::new().route("/notes/{id}", get(fetch)).with_state(state);
    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

**Answer:**

- A **handler** is an `async fn` whose arguments are extractors and whose
  return value implements `IntoResponse`.
- `Router::new().route(path, method_router)` maps a path to handlers.
  Since Axum 0.8 path parameters use **braces**: `/notes/{id}` (older
  versions used `/notes/:id`).
- `method_router` is built with `get(h)`, `post(h)`, and can be chained:
  `get(list).post(create)`.
- `axum::serve(listener, app)` runs the server. It takes any `tokio`
  `TcpListener`, so you choose the address and the socket options.
- `#[tokio::main]` creates the runtime (see
  [Tokio and Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md)).

## 3. "What are extractors, and why does their order matter?"

**Answer:**

- An **extractor** is a type that knows how to build itself from a
  request. You list them as handler arguments, and Axum calls them for you.
- The ones you use daily:

| Extractor | Reads | Failure status |
|---|---|---|
| `Path<T>` | Path parameters such as `{id}` | 400 |
| `Query<T>` | The query string (`?contains=a`) | 400 |
| `Json<T>` | The body, as JSON | 400 bad syntax, 422 wrong shape, 415 wrong `Content-Type` |
| `State<S>` | The shared application state | cannot fail |
| `HeaderMap`, `Request` | Headers, or the raw request | none |

- **The body can only be read once**, so a body extractor (`Json`,
  `String`, `Bytes`, `Request`) **must be the last argument**. Putting
  `Json` first fails to compile, and the error is *not* helpful:

```text
error[E0277]: the trait bound `fn(Json<String>, State<u32>) -> impl Future<Output = ()> {handler}: Handler<_, _>` is not satisfied
  = note: Consider using `#[axum::debug_handler]` to improve the error message
```

- That `Handler<_, _>` message is how Axum reports **every** handler
  problem. Turn on the `macros` feature of `axum` and add
  `#[axum::debug_handler]` above the handler. Then the compiler points at
  the real cause (see §6 for a real example).
- A handler can return a `Result<T, E>` as long as both `T` and `E`
  implement `IntoResponse`. This is how you do error handling (§4).
- The rejection statuses in the table were checked with tests in the
  sample: bad JSON syntax gives 400, valid JSON with a missing field gives
  422, a wrong `Content-Type` gives 415 with the text
  `Expected request with Content-Type: application/json`.

## 4. "How do I return errors cleanly?"

```rust
pub enum ApiError {
    NotFound(u64),
    Invalid(&'static str),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, msg) = match self {
            ApiError::NotFound(id) => (StatusCode::NOT_FOUND, format!("note {id} not found")),
            ApiError::Invalid(m) => (StatusCode::UNPROCESSABLE_ENTITY, m.to_string()),
        };
        (status, Json(serde_json::json!({ "error": msg }))).into_response()
    }
}

async fn fetch(State(s): State<AppState>, Path(id): Path<u64>) -> Result<Json<Note>, ApiError> {
    s.lock().unwrap().notes.get(&id).cloned().map(Json).ok_or(ApiError::NotFound(id))
}
```

**Answer:**

- One **error enum for the whole API**, with a single `IntoResponse`
  impl. Each variant decides its status code and body. Handlers then use
  `?` and never build responses by hand.
- Real response from the sample:

```text
GET /notes/1  (after deleting it)
404  {"error":"note 1 not found"}
```

- Keep **internal** error details (database messages, file paths) out of
  the body. Log them (see [Observability](rust-observability.md)) and
  return a generic message.
- This follows the same split as in
  [Error Handling §5](../foundations/rust-error-handling.md#5-when-do-you-use-thiserror-and-when-anyhow):
  a typed enum at the boundary. Use `thiserror` for the enum in a larger
  service; `anyhow` is fine inside `main`.

## 5. "How do I share state between handlers?"

**Answer:**

- `Router::with_state(value)` stores one value. Handlers read it with
  `State<T>`. The value must be `Clone`; that is why it is usually an
  `Arc` or a type that holds one (a database pool already is one).
- The sample uses `Arc<Mutex<Store>>` from the standard library. That is
  correct **only because the lock is never held across an `.await`**.
- Holding a `std::sync::MutexGuard` across an `.await` makes the handler's
  future not `Send`, and Axum refuses to compile it. With
  `#[axum::debug_handler]` the real error is:

```text
error: future cannot be sent between threads safely
 --> examples/g.rs:5:1
  |
5 | #[axum::debug_handler]
  | ^^^^^^^^^^^^^^^^^^^^^^ future returned by `handler` is not `Send`
  = help: within `impl Future<Output = String>`, the trait `Send` is not implemented for `std::sync::MutexGuard<'_, u32>`
note: future is not `Send` as this value is used across an await
7 |     let guard = s.lock().unwrap();
  |         ----- has type `std::sync::MutexGuard<'_, u32>` which is not `Send`
8 |     tokio::task::yield_now().await;
  |                              ^^^^^ await occurs here, with `guard` maybe used later
```

- Fixes, in order of preference: finish with the lock before the `.await`
  (copy the data out), put the state behind a task and talk to it through
  a channel, or use `tokio::sync::Mutex` (only when you truly must hold the
  lock across an `.await`; it is slower).
- Why `Send` is needed: the Tokio multi-thread runtime can move a task to
  another thread at every `.await`. See
  [Threads and Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md).
- Real service state is a **database pool** (see
  [Databases](rust-databases.md)), not a `Mutex<BTreeMap>`. The map is only
  there to keep the sample self-contained.

## 6. "How does middleware work? What is a tower layer?"

```rust
async fn add_version_header(req: Request, next: Next) -> Response {
    let mut res = next.run(req).await;
    res.headers_mut().insert("x-api-version", HeaderValue::from_static("1"));
    res
}

Router::new()
    .route("/notes", get(list).post(create))
    .layer(middleware::from_fn(add_version_header))
    .layer(TimeoutLayer::with_status_code(StatusCode::REQUEST_TIMEOUT, Duration::from_millis(200)))
    .layer(TraceLayer::new_for_http())
    .with_state(state)
```

**Answer:**

- A `tower::Service` is "something that takes a request and returns a
  future of a response." A **`Layer`** wraps one service in another. A
  middleware is a layer.
- Two ways to write one:
    - `middleware::from_fn(async fn(Request, Next) -> Response)`: simple,
      good for most app code.
    - A real `Layer` and `Service` pair: more code, fully reusable, how
      libraries are written.
- **Order matters.** Each `.layer(..)` wraps everything added **before**
  it. The **last** `.layer` call is the **outermost** layer and sees the
  request **first**. In the example, `TraceLayer` sees a request first and
  sees the final response last, so its timing includes the timeout and the
  version header.
- `.layer` on a `Router` wraps only routes added **before** it. A route
  added after the call is not covered, which surprises people.
- `tower-http` supplies the standard layers: `TraceLayer` (log each
  request), `TimeoutLayer`, `CorsLayer`, `CompressionLayer`,
  `RequestBodyLimitLayer`. Always set a **body size limit** and a
  **timeout** on a public service.
- Result of the sample's timeout layer (a handler that sleeps 5 s, limit
  200 ms), tested with paused time and also with `curl`:

```text
GET /slow  ->  408 Request Timeout
```

## 7. "How do I test a handler without starting a server?"

```rust
use tower::ServiceExt; // for `oneshot`

let app = app(AppState::default());
let res = app
    .clone()
    .oneshot(Request::builder().method("POST").uri("/notes")
        .header("content-type", "application/json")
        .body(Body::from(r#"{"title":"first"}"#)).unwrap())
    .await
    .unwrap();
assert_eq!(res.status(), StatusCode::CREATED);
```

**Answer:**

- Because a `Router` is a `Service`, you call it directly:
  `oneshot(request)` sends **one** request and gives the response. No
  port, no network, tests run in microseconds and can run in parallel.
- `ServiceExt::oneshot` consumes the service, so call `app.clone()` for
  each request (cloning a `Router` is cheap).
- Read the body with `http_body_util::BodyExt::collect`.
- Test the **failure** paths too (bad JSON, wrong content type, missing
  record). The sample has 3 tests, all pass: a CRUD round trip, the
  extractor rejection codes, and the timeout with
  `#[tokio::test(start_paused = true)]` (the 5-second sleep completes
  instantly because Tokio advances a fake clock; needs the `test-util`
  feature of `tokio` as a dev-dependency).
- For one end-to-end smoke test, bind to port `0` (the OS picks a free
  port) and use a real HTTP client.

## 8. "How do I shut down gracefully?"

```rust
axum::serve(listener, app)
    .with_graceful_shutdown(async {
        signal::ctrl_c().await.expect("install Ctrl-C handler");
        println!("shutting down: finishing in-flight requests");
    })
    .await
    .unwrap();
```

**Answer:**

- `with_graceful_shutdown(future)` stops accepting **new** connections
  when the future completes, and then waits for in-flight requests to
  finish.
- In a container the stop signal is **SIGTERM**, not Ctrl-C. Use
  `tokio::signal::unix::signal(SignalKind::terminate())` and wait on both.
  Ctrl-C was run and verified with the sample (it prints
  `shutting down: finishing in-flight requests` and exits); SIGTERM was
  **not** run here.
- Add a **hard deadline** (for example `tokio::time::timeout` around the
  server) so one stuck request cannot block a deployment forever.
- Background tasks (queues, schedulers) need their own shutdown signal. See
  [Tokio and Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md).

## 9. "What do I need before this goes to production?"

**Answer:**

- **Observability:** `TraceLayer` plus the `tracing` crate, with a request
  ID in every log line. See [Observability](rust-observability.md).
- **Limits:** request body size, request timeout, connection limits,
  rate limiting at the proxy or with a `tower` layer.
- **Configuration** from environment variables (parsed once into a typed
  struct at startup; fail fast if invalid).
- **Health endpoints:** a cheap `/healthz` (process is up) and a `/readyz`
  that checks dependencies.
- **TLS (Transport Layer Security):** usually terminated at a load
  balancer or reverse proxy. Axum itself can serve TLS through
  `axum-server` or `hyper-rustls`, but most teams do not need it.
- **Container and pipeline:** see [CI/CD & Supply Chain](rust-ci-cd-and-supply-chain.md).
- **Input is untrusted:** validate after deserializing (see
  [Serde](rust-serde-and-serialization.md)).

## 10. "How do AI tools help or hurt with web services?"

**Answer:**

- Good for: boilerplate (routes, request/response structs, `IntoResponse`
  impls) and writing the `oneshot` tests.
- They often write **old Axum syntax**: `/:id` paths, `axum::Server::bind`,
  `#[async_trait]` on custom extractors. Axum 0.8 uses `/{id}`,
  `axum::serve`, and plain `async fn` in extractor traits (the
  `async_trait` macro is not needed since 0.7). If the code does not compile, check the
  version first.
- They happily hold a `std::sync::Mutex` guard across an `.await`, or
  use `.unwrap()` on the lock in code that should not panic. Ask for the
  guard scope to be shown.
- A useful prompt: "List every `.await` in this handler and say what locks
  or borrows are alive across it."
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 11. Interview Questions You're Likely to Get Asked

**Concepts**

- "What is Axum built on?" — expects `tower` and `hyper` on Tokio; a
  `Router` is a `Service`, [§1](#1-what-does-a-rust-web-stack-look-like-and-where-does-axum-fit).
- "How is Axum different from Actix Web?" — expects `tower` ecosystem and
  `tower` middleware and no route macros versus Actix's own middleware system,
  [§1](#1-what-does-a-rust-web-stack-look-like-and-where-does-axum-fit).
- "What is an extractor?" — expects a type built from a request, body
  extractor last, [§3](#3-what-are-extractors-and-why-does-their-order-matter).

**Practical**

- "Why does my handler not compile and the error mentions `Handler`?" —
  expects `#[axum::debug_handler]`, usual causes: body extractor not last,
  non-`Send` future, a return type without `IntoResponse`,
  [§3](#3-what-are-extractors-and-why-does-their-order-matter).
- "How do you turn domain errors into HTTP responses?" — expects one enum
  implementing `IntoResponse`,
  [§4](#4-how-do-i-return-errors-cleanly).
- "In what order do layers run?" — expects the last `.layer` is outermost,
  [§6](#6-how-does-middleware-work-what-is-a-tower-layer).
- "How do you test a handler?" — expects `oneshot` on the `Router`, no
  socket, [§7](#7-how-do-i-test-a-handler-without-starting-a-server).

**Production**

- "Why can't you hold a `std::sync::MutexGuard` across `.await` in a
  handler?" — expects the future becomes not `Send`; fix by scoping the
  guard, [§5](#5-how-do-i-share-state-between-handlers).
- "How do you shut down gracefully in Kubernetes?" — expects SIGTERM, stop
  accepting, drain, hard deadline,
  [§8](#8-how-do-i-shut-down-gracefully).

---

## Code Samples

Package `code_samples/rust/axum_api/` (own `Cargo.toml`; Rust 1.99.1,
`axum` 0.8.9).

- `src/lib.rs` — the router, handlers, `ApiError`, layers and 3 tests.
- `src/main.rs` — the server with Ctrl-C graceful shutdown.
- `compile_fail/body_extractor_not_last.rs` and
  `compile_fail/guard_across_await.rs` — the two failing handlers whose
  error text is quoted above. To check one, copy it into `examples/` and
  run `cargo build --example NAME` (add the `macros` feature to see the
  `debug_handler` output).

```bash
cd code_samples/rust/axum_api
cargo test                       # 3 tests pass
cargo run                        # then, in another terminal:
curl -si -XPOST localhost:3000/notes -H 'content-type: application/json' -d '{"title":"hello"}'
curl -s localhost:3000/slow -w ' [%{http_code}]\n'    # 408 after 200 ms
```
