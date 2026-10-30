---
title: "Observability: Tracing, Metrics & Logs"
---

# Observability: Tracing, Metrics and Logs

**Observability** means you can tell what a running program is doing from
the outside: **logs** (what happened), **traces** (how one request moved
through the code and services, with timings) and **metrics** (numbers
counted over time). In Rust the standard tool is the **`tracing`** crate.
Its core idea: instead of plain log lines, you record **events** (a point
in time) inside **spans** (a period of time with named fields). Spans nest,
so every event knows which request, user or job it belongs to, which is
exactly what is missing from `println!`.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Sample run with
    `tracing` 0.1.44, `tracing-subscriber` 0.3.23, `tokio` 1.54.1,
    `opentelemetry` 0.33.1, `opentelemetry_sdk` 0.33.1,
    `opentelemetry-stdout` 0.33.1, `tracing-opentelemetry` 0.34.0 and
    `metrics` 0.24.6. Outputs below are real. **Not run:** sending data to
    a real collector over the network (OTLP, the OpenTelemetry Protocol),
    a Prometheus exporter, and file logging with `tracing-appender`.

## 1. "What are events, spans and subscribers?"

**Answer:**

- **Event:** one moment: `info!(total = 750, "done")`. Like a log line,
  but with structured fields.
- **Span:** a period with a name and fields:
  `info_span!("batch", batch.size = 3)`. While the span is **entered**,
  every event inside belongs to it. Spans nest into a tree.
- **Subscriber:** the thing that receives events and spans and decides what
  to do: print, write JSON, send to a collector. You install **one**
  subscriber at startup. Library code only **emits**; it never decides
  where output goes.
- That split is why a library can use `tracing` without forcing a logging
  choice on you, the same way as the `log` crate, but with spans.
- The `tracing-log` bridge (enabled by default in `tracing-subscriber`)
  also turns old `log::info!` calls from other crates into events.
- **Layers** (`tracing_subscriber::Layer`) are composable parts of a
  subscriber: a filter, a text formatter, a JSON formatter, an
  OpenTelemetry exporter. You stack them on a `registry()`:

```rust
tracing_subscriber::registry()
    .with(filter)                                  // which levels/targets pass
    .with(tracing_subscriber::fmt::layer().json()) // how they are printed
    .init();
```

- **Levels:** `ERROR`, `WARN`, `INFO`, `DEBUG`, `TRACE`. Rule of thumb:
  `INFO` for business events you always want, `DEBUG` for development.

## 2. "How do I add `tracing` to a program?"

```rust
use tracing::{debug, info, info_span, instrument, Instrument};

#[instrument(skip(db, order), fields(order.id = order.id), err)]
async fn charge(db: &Db, order: &Order) -> Result<u64, String> {
    debug!(cents = order.cents, "charging");
    // ...
}
```

Real output (human format, `cargo run`):

```text
2026-10-30T16:35:26.459883Z  INFO batch{batch.size=3}: starting
2026-10-30T16:35:26.467867Z ERROR batch{batch.size=3}:charge{order.id=2}: error=order 2 has no amount
2026-10-30T16:35:26.467966Z  WARN batch{batch.size=3}: one charge failed e=order 2 has no amount
2026-10-30T16:35:26.467998Z  INFO batch{batch.size=3}: done total=750
```

**Answer:**

- `#[instrument]` wraps a function in a span named after it. Arguments
  become fields (they must implement `Debug`), so:
    - `skip(a, b)`: leave arguments out (big values, secrets, things
      without `Debug`).
    - `fields(name = expr)`: add your own fields.
    - `err`: log an `Err` return as an `ERROR` event (seen on line 2).
- Read the output: `batch{batch.size=3}:charge{order.id=2}:` is the **span
  path**. The error says exactly which batch and which order, with no
  extra code.
- **Do not log secrets.** `#[instrument]` records every argument unless
  skipped. Passwords, tokens and personal data must be in `skip(...)`.
- Fields with `%` use `Display` (`%e`), with `?` use `Debug` (`?order`).
  `warn!(%e, "one charge failed")` produced `e=order 2 has no amount`.
- Use dotted field names (`order.id`) consistently; they become
  attribute names downstream.

## 3. "How do I control what is printed, and how do I get JSON?"

```bash
cargo run                       # human text, INFO and above
cargo run -- json               # one JSON object per line
RUST_LOG=debug cargo run        # more detail, no recompile
RUST_LOG=info,tracing_demo=debug cargo run   # INFO everywhere, DEBUG for one crate
```

Real JSON line (one event inside two spans, formatted here for reading):

```json
{"timestamp":"2026-10-30T16:35:26.482802Z","level":"ERROR",
 "fields":{"error":"order 2 has no amount"},"target":"tracing_demo",
 "span":{"order.id":2,"name":"charge"},
 "spans":[{"batch.size":3,"name":"batch"},{"order.id":2,"name":"charge"}]}
```

**Answer:**

- `EnvFilter` (feature `env-filter`) reads the **`RUST_LOG`** variable.
  Syntax: `target=level` pairs separated by commas. Change verbosity of a
  running deployment by restarting with a different variable. Real
  output with `RUST_LOG=debug`:

```text
DEBUG batch{batch.size=3}:charge{order.id=2}: charging cents=0
DEBUG batch{batch.size=3}:charge{order.id=1}: charging cents=500
```

- In production use **JSON** (`fmt::layer().json()`, feature `json`).
  Log systems can index `level`, `fields.error` and each span field.
  Plain text can only be searched with regular expressions.
- Write to **standard output** and let the platform (Docker, Kubernetes)
  collect it. This is simpler and safer than log files.
- If you must write to a file without blocking, `tracing-appender` has a
  non-blocking writer (not run here). Keep its guard value alive, or lines
  are lost at exit.
- Colors: the sample output above had ANSI colors turned off with
  `NO_COLOR=1`. Disable them when output is not a terminal.

## 4. "How does `tracing` work with async code?"

```rust
// Spawned tasks do NOT inherit the current span: attach it explicitly.
tokio::spawn(
    async move { charge(&db, &Order { id, cents }).await }
        .instrument(tracing::Span::current()),
);
```

**Answer:**

- A span is "current" for the **thread** while you hold it entered. An
  `async` task can move between threads and be paused, so you must **not**
  hold `span.enter()` across an `.await`. Use `.instrument(span)` on the
  future instead, or `#[instrument]` on an `async fn`. Both enter the span
  on every poll and exit when it pauses.
- **`tokio::spawn` creates a new task with no parent span.** Verified:
  without `.instrument(Span::current())` the line becomes
  `ERROR charge{order.id=2}: error=...` and the `batch{batch.size=3}`
  context is **gone**. With it, the batch is the parent, as in §2.
- This is the most common reason traces look broken in async services.
  (How tasks and wakers work: [Async Internals](../concurrency-and-async/rust-async-internals.md).)
- A span stays **open** (not closed) until it is dropped. A span stored
  in a long-lived struct makes a trace that never ends.

## 5. "How do traces leave the process? What is OpenTelemetry?"

```rust
let provider = SdkTracerProvider::builder()
    .with_simple_exporter(opentelemetry_stdout::SpanExporter::default())
    .build();
let tracer = provider.tracer("tracing_demo");
tracing_subscriber::registry()
    .with(tracing_opentelemetry::layer().with_tracer(tracer))
    .init();
// ... run ...
provider.shutdown().unwrap(); // flush before exit
```

**Answer:**

- **OpenTelemetry** (often "OTel") is a vendor-neutral standard for
  traces, metrics and logs. Your app exports data in its format (usually
  over OTLP) to a **collector** or a vendor backend.
- Your code stays plain `tracing`. The **`tracing-opentelemetry` layer**
  turns every `tracing` span into an OTel span. This is the whole
  integration.
- The sample uses the **stdout exporter** so you can see what would be
  sent. Real output (shortened) for one `charge` span:

```text
Name         : charge
TraceId      : d62c5edd8df3913589c1c9ace8a4f591
SpanId       : 536d6ba551cb1387
ParentSpanId : ae4597757eb07cc7
Attributes:
    ->  code.file.path: String(Static("src/main.rs"))
    ->  order.id: String(Owned("3"))
    ->  busy_ns: I64(34667)
    ->  idle_ns: I64(7580541)
```

- Three things to notice: all spans share one **`TraceId`** (one logical
  request), each has a **`ParentSpanId`** (the tree), and
  **`busy_ns` / `idle_ns`** show time spent running versus waiting
  (valuable for async code).
- In production replace the stdout exporter with the OTLP exporter
  (`opentelemetry-otlp` crate), and use a **batch** exporter, not the
  simple one, so exporting does not slow requests. Not run here.
- **Always call `shutdown()` (or flush) before exit.** Spans are buffered;
  without it, the last ones are lost. Verified: the sample calls it, and
  every span (the batch and the three `charge` calls) was printed.
- **Across services:** the trace ID travels in the `traceparent` HTTP
  header (W3C Trace Context). HTTP middleware (see
  [Web Services with Axum §6](rust-web-services-with-axum.md#6-how-does-middleware-work-what-is-a-tower-layer))
  extracts it from incoming requests and injects it into outgoing ones.
  The OpenTelemetry crates have a propagator for this. Not run here.
- **Sampling:** at scale you keep only a fraction of traces (for example
  1 in 100, plus all errors). Decide it in the SDK or the collector.

## 6. "How do I add metrics?"

```rust
metrics::counter!("charges_total", "result" => "ok").increment(1);
```

Real output after the sample's three charges, read from a tiny in-memory
recorder:

```text
metric charges_total["result=bad"] = 1
metric charges_total["result=ok"] = 2
```

**Answer:**

- A **metric** is a number tracked over time. Three kinds: a **counter**
  (only goes up: requests served), a **gauge** (goes up and down: queue
  length) and a **histogram** (distribution: request duration).
- The **`metrics`** crate is a **facade**, like `log`: your code calls
  `counter!`, `gauge!`, `histogram!`; a **recorder** installed once at
  startup decides what to do. With **no recorder** installed the calls
  do almost nothing (the crate documents a "noop" recorder), so libraries
  can be instrumented for free.
- The sample installs a 40-line recorder to show the mechanism. In
  production, install an exporter crate (for example a Prometheus
  exporter, or OpenTelemetry metrics). Not run here.
- **Labels are dangerous.** Every distinct label value makes a new time
  series. A user ID or URL as a label creates millions of series and can
  take down the metrics system. Labels must have **few, fixed values**
  (`result=ok|bad`, status code class, route template like `/notes/{id}`).
- Alternatively, OpenTelemetry has its own metrics API. Pick one metrics
  API per service and stay with it.
- **What to measure first:** the RED method for services: **R**ate
  (requests per second), **E**rrors (failed requests), **D**uration
  (latency histogram). Add saturation (pool usage, queue length).

## 7. "How do I handle panics and backtraces in production?"

```rust
std::panic::set_hook(Box::new(|info| {
    let loc = info.location().map(|l| format!("{}:{}", l.file(), l.line()));
    error!(panic.location = loc.as_deref(), panic.message = %info, "thread panicked");
}));
```

Real output (`cargo run -- panic`, first part of the event):

```text
ERROR thread panicked panic.location="src/main.rs:117" panic.message=panicked at src/main.rs:117:45:
```

**Answer:**

- By default a panic prints to **standard error** only. It never reaches
  your structured log or your trace. A **panic hook** turns it into an
  event with the same fields as every other error.
- In an async server, a panic in a spawned task is caught by the runtime:
  the task ends and the `JoinHandle` returns a `JoinError`. The process
  keeps running, so without a hook nobody notices. (See
  [Error Handling §6](../foundations/rust-error-handling.md#6-when-is-a-panic-right-and-what-happens-when-one-occurs).)
- `RUST_BACKTRACE=1` prints a stack trace on panic; `RUST_BACKTRACE=full`
  adds more. Build release binaries with debug line info
  (`[profile.release] debug = "line-tables-only"`) if you want readable
  traces in production, at the cost of a larger binary.
- With `panic = "abort"` in the profile there is no unwinding. The hook
  still runs, and then the process exits immediately. For an abort,
  your orchestrator's restart policy is the safety net.
- Capture backtraces for **errors** with `anyhow` (`{:?}` prints the
  chain) and error-reporting crates. See
  [Error Handling §8](../foundations/rust-error-handling.md#8-how-do-you-get-a-backtrace-and-what-does-async-change).

## 8. "How do AI tools help or hurt with observability?"

**Answer:**

- Good for: adding `#[instrument]` across a codebase, writing the
  subscriber setup, and explaining an OTel span dump.
- They put **secrets and large values** into spans by default: ask for
  `skip` on credentials and request bodies, and review the result.
- They add `println!` or `log::info!` where `tracing` is the project's
  standard. Insist on one system.
- They create **high-cardinality metric labels** (user IDs, full URLs)
  without a warning. Review every label.
- AI assistants are also useful consumers of good observability: paste a
  JSON log or trace for an incident and ask for a timeline. Remove
  personal data first.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Concepts**

- "Why `tracing` and not `log`?" — expects spans with fields and
  structured data, async-aware, still bridges `log`,
  [§1](#1-what-are-events-spans-and-subscribers).
- "What is the difference between an event and a span?" — expects a
  moment versus a period that groups events,
  [§1](#1-what-are-events-spans-and-subscribers).
- "Logs, traces, metrics: when each?" — expects what happened, the path
  of one request, numbers over time,
  [§6](#6-how-do-i-add-metrics).

**Practical**

- "Why are my spans missing in spawned tasks?" — expects spawn does not
  inherit the span; use `.instrument(Span::current())`,
  [§4](#4-how-does-tracing-work-with-async-code).
- "Why must you not hold `span.enter()` across `.await`?" — expects the
  task can move or pause; use `instrument`,
  [§4](#4-how-does-tracing-work-with-async-code).
- "How do you change log levels without a redeploy?" — expects `RUST_LOG`
  with `EnvFilter` (a restart with a new variable, or a reload handle),
  [§3](#3-how-do-i-control-what-is-printed-and-how-do-i-get-json).
- "What does `#[instrument]` record by default, and what is risky?" —
  expects all `Debug` arguments, so skip secrets,
  [§2](#2-how-do-i-add-tracing-to-a-program).

**Production**

- "How does a trace cross services?" — expects trace ID in the
  `traceparent` header, propagators,
  [§5](#5-how-do-traces-leave-the-process-what-is-opentelemetry).
- "Why can a metric label take down your monitoring?" — expects
  cardinality: one series per distinct value,
  [§6](#6-how-do-i-add-metrics).
- "How do you make sure panics show up in your logs?" — expects a panic
  hook, task panics become `JoinError`,
  [§7](#7-how-do-i-handle-panics-and-backtraces-in-production).

---

## Code Samples

Package `code_samples/rust/tracing_demo/` (own `Cargo.toml`; Rust 1.99.1).

- `src/main.rs` — one binary with four modes: text, JSON, OpenTelemetry
  (stdout exporter), and a panic hook; it also shows `#[instrument]`,
  span propagation into spawned tasks, and a small `metrics` recorder.

```bash
cd code_samples/rust/tracing_demo
cargo run                    # human-readable
cargo run -- json            # JSON lines
cargo run -- otel            # OpenTelemetry spans on stdout
cargo run -- panic           # panic hook logs through tracing
RUST_LOG=debug cargo run     # change the filter without recompiling
NO_COLOR=1 cargo run         # plain text, no color codes
```
