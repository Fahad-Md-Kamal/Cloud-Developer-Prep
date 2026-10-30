//! tracing demo. Run one mode at a time (inside `code_samples/rust/tracing_demo`):
//!   cargo run                      # human-readable logs
//!   cargo run -- json              # one JSON object per line
//!   cargo run -- otel              # spans exported as OpenTelemetry (to stdout)
//!   cargo run -- panic             # a panic hook that logs through tracing
//!   RUST_LOG=debug cargo run       # change the filter without recompiling

use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use metrics::{Counter, Gauge, Histogram, Key, KeyName, Metadata, Recorder, SharedString, Unit};
use opentelemetry::trace::TracerProvider as _;
use opentelemetry_sdk::trace::SdkTracerProvider;
use tracing::{Instrument, debug, error, info, info_span, instrument, warn};
use tracing_subscriber::{EnvFilter, prelude::*};

#[derive(Debug)]
struct Order {
    id: u32,
    cents: u64,
}

// `#[instrument]` makes a span named after the function; arguments become fields.
// `skip` leaves a field out, `fields` adds new ones, `err` logs an Err at ERROR level.
#[instrument(skip(db, order), fields(order.id = order.id), err)]
async fn charge(db: &Db, order: &Order) -> Result<u64, String> {
    debug!(cents = order.cents, "charging");
    tokio::time::sleep(Duration::from_millis(5)).await;
    metrics::counter!("charges_total", "result" => if order.cents > 0 { "ok" } else { "bad" })
        .increment(1);
    if order.cents == 0 {
        return Err(format!("order {} has no amount", order.id));
    }
    db.total.fetch_add(order.cents, Ordering::Relaxed);
    Ok(order.cents)
}

struct Db {
    total: AtomicU64,
}

// A tiny `metrics` recorder that keeps counters in a map. Real programs install an
// exporter (Prometheus, OpenTelemetry); without any recorder `counter!` does nothing.
#[derive(Default, Clone)]
struct MemoryRecorder(Arc<Mutex<HashMap<String, Arc<AtomicU64>>>>);

impl Recorder for MemoryRecorder {
    fn describe_counter(&self, _: KeyName, _: Option<Unit>, _: SharedString) {}
    fn describe_gauge(&self, _: KeyName, _: Option<Unit>, _: SharedString) {}
    fn describe_histogram(&self, _: KeyName, _: Option<Unit>, _: SharedString) {}
    fn register_counter(&self, key: &Key, _: &Metadata<'_>) -> Counter {
        let name = format!(
            "{}{:?}",
            key.name(),
            key.labels()
                .map(|l| format!("{}={}", l.key(), l.value()))
                .collect::<Vec<_>>()
        );
        let cell = self.0.lock().unwrap().entry(name).or_default().clone();
        Counter::from_arc(cell)
    }
    fn register_gauge(&self, _: &Key, _: &Metadata<'_>) -> Gauge {
        Gauge::noop()
    }
    fn register_histogram(&self, _: &Key, _: &Metadata<'_>) -> Histogram {
        Histogram::noop()
    }
}

#[tokio::main]
async fn main() {
    let mode = std::env::args().nth(1).unwrap_or_default();
    // The filter comes from RUST_LOG; the default is "info".
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    let registry = tracing_subscriber::registry().with(filter);
    let mut provider = None;
    match mode.as_str() {
        "json" => registry
            .with(tracing_subscriber::fmt::layer().json())
            .init(),
        "otel" => {
            let p = SdkTracerProvider::builder()
                .with_simple_exporter(opentelemetry_stdout::SpanExporter::default())
                .build();
            let tracer = p.tracer("tracing_demo");
            registry
                .with(tracing_opentelemetry::layer().with_tracer(tracer))
                .init();
            provider = Some(p);
        }
        _ => registry
            .with(tracing_subscriber::fmt::layer().with_target(false))
            .init(),
    }

    let rec = MemoryRecorder::default();
    metrics::set_global_recorder(rec.clone()).unwrap();

    let db = Arc::new(Db {
        total: AtomicU64::new(0),
    });
    let root = info_span!("batch", batch.size = 3);
    async {
        info!("starting");
        let mut tasks = Vec::new();
        for (id, cents) in [(1, 500), (2, 0), (3, 250)] {
            let db = db.clone();
            // Spawned tasks do NOT inherit the current span: attach it explicitly.
            tasks.push(tokio::spawn(
                async move { charge(&db, &Order { id, cents }).await }
                    .instrument(tracing::Span::current()),
            ));
        }
        for t in tasks {
            if let Err(e) = t.await.unwrap() {
                warn!(%e, "one charge failed");
            }
        }
        info!(total = db.total.load(Ordering::Relaxed), "done");
        error!(code = 42, "an example error event");
    }
    .instrument(root)
    .await;

    if mode == "panic" {
        // Without a hook, a panic message goes to stderr only and never reaches your log pipeline.
        std::panic::set_hook(Box::new(|info| {
            let loc = info
                .location()
                .map(|l| format!("{}:{}", l.file(), l.line()));
            error!(panic.location = loc.as_deref(), panic.message = %info, "thread panicked");
        }));
        let _ = std::panic::catch_unwind(|| panic!("boom"));
    }

    for (k, v) in rec.0.lock().unwrap().iter() {
        println!("metric {k} = {}", v.load(Ordering::Relaxed));
    }
    if let Some(p) = provider {
        p.shutdown().unwrap(); // flush exporters before exit
    }
}
