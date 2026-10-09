---
title: "Chapter 10: Observability \u2014 Logging, Metrics, and Tracing with Prometheus & Grafana"
---

# Chapter 10: Observability — Logging, Metrics, and Tracing with Prometheus & Grafana

Structured logging, Prometheus metrics, distributed tracing, and
dashboards/alerting — each as a question you should be able to answer
cold, with the trade-offs named explicitly.

---

## Part 1: Structured Logging

### 1. "Why structured (JSON) logging instead of plain text log lines?"

```python
import structlog

log = structlog.get_logger()

log.info("order_created", order_id=order.id, user_id=user.id, total=order.total)
# {"event": "order_created", "order_id": 123, "user_id": 45, "total": 99.5, ...}
```

**Answer:** A plain-text log line is only searchable by regex or
substring match; a structured line has named fields a log aggregator
(ELK, Loki) can index, filter, and aggregate on directly — "show me
every `order_created` event for `user_id=45`" is a query, not a grep.
The bigger win is correlation: attaching the same `request_id` (or
`trace_id`) to every log line emitted while handling one request lets
you pull the *entire* story of that request back out of a firehose of
interleaved logs from every other concurrent request.

| Pros | Cons / Trade-offs |
|---|---|
| Queryable/filterable in log aggregation tools, not just grep | Slightly more verbose to write and marginally more storage per line |
| A shared `request_id`/`trace_id` field ties a request's logs together | Requires discipline — an inconsistent field name (`user_id` vs `uid`) defeats the purpose |
| Machine-parseable — feeds dashboards and alerts directly | Team has to agree on and enforce a schema, or it degrades into free text with extra steps |

### 2. "How do you avoid logging PII or secrets while keeping logs actually useful?"

```python
SENSITIVE_KEYS = {"password", "ssn", "credit_card", "authorization"}

def redact_processor(logger, method_name, event_dict):
    for key in event_dict:
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict
```

**Answer:** Never log a raw request/response body wholesale — log
specific, named fields instead, and run every log line through a
redaction step that strips or masks known-sensitive keys before it
leaves the process. Structured logging makes this mechanical: with free
text you'd need a regex trying to guess where a credit card number
might appear; with named fields you just check the key against a
denylist. The same mindset applies to trace spans and metric labels —
anything with unbounded cardinality (a raw email as a label) is also a
metrics cost problem, not just a privacy one.

### 3. "What log level would you actually use, and how do you avoid that being arbitrary?"

**Answer:** `DEBUG` for detail only useful while actively developing;
`INFO` for expected, significant events (order placed, job completed);
`WARNING` for something recoverable but worth noticing (a retry
succeeded, a fallback path was taken); `ERROR` for an operation that
failed and needs attention; `CRITICAL` for the system itself being
down. The practical test that keeps this from being a judgment call
per-developer: "would someone reasonably want to be paged for this at
3am?" — if yes, it's `ERROR`/`CRITICAL`; if it's just interesting
context, it's `INFO` or lower.

---

## Part 2: Metrics and Monitoring with Prometheus

### 4. "Explain Prometheus's four metric types and when you'd reach for each."

```python
from prometheus_client import Counter, Gauge, Histogram

requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "status"]
)
active_connections = Gauge("active_connections", "Current open connections")
request_duration = Histogram(
    "http_request_duration_seconds", "Request duration", ["endpoint"]
)

requests_total.labels(method="GET", status="200").inc()
active_connections.set(42)
with request_duration.labels(endpoint="/api/orders").time():
    handle_request()
```

**Answer:** **Counter** only goes up (total requests, total errors) —
you graph its *rate* over time, never its raw value. **Gauge** can go up
or down (current active connections, queue depth) — it's a snapshot.
**Histogram** buckets observed values (request duration) so percentiles
can be computed *server-side* by aggregating buckets across every
instance. **Summary** computes quantiles client-side per process
instead — cheaper per-instance, but those per-instance quantiles can't
be meaningfully averaged or summed across replicas, which is why
Histogram is the usual default for anything you'll aggregate across a
fleet.

| Type | Pros | Cons / Trade-offs |
|---|---|
| Histogram | Aggregates correctly across instances; percentiles computed centrally | Bucket boundaries must be chosen up front — wrong buckets lose precision |
| Summary | Cheaper to compute per instance; exact quantiles for that instance | Not composable — can't merge quantiles from multiple instances meaningfully |

### 5. "How does Prometheus actually get metrics out of an application — push or pull?"

**Answer:** Pull-based: the application exposes a `/metrics` endpoint
with the current value of every metric, and Prometheus scrapes it on a
configured interval. This is the opposite of StatsD-style push, and it
has real advantages — Prometheus controls its own load, and a target
that's down is immediately visible as a failed scrape rather than
silence. The exception is short-lived batch jobs that finish before the
next scrape would ever hit them; those push their final values to a
**Pushgateway**, which Prometheus then scrapes instead.

**Likely follow-up — "what about a target behind NAT or in a serverless environment that Prometheus can't reach to scrape?"**
Same answer — push through a Pushgateway, or run a sidecar that
aggregates and exposes a stable scrape target on the app's behalf.

### 6. "Design SLIs and SLOs for an API endpoint. How is an SLO different from an SLA?"

```
# PromQL: percentage of requests under 300ms over the last 5 minutes
sum(rate(http_request_duration_seconds_bucket{le="0.3"}[5m]))
/ sum(rate(http_request_duration_seconds_count[5m]))
```

**Answer:** An **SLI** is the measured indicator itself — e.g., "% of
requests completing under 300ms," computed straight from metrics. An
**SLO** is the internal target for that indicator (99.9% of requests
under 300ms) that the team holds itself to. An **SLA** is an external,
often contractual, commitment with consequences for missing it — usually
set looser than the internal SLO so there's margin before it actually
matters commercially. The practical payoff of an SLO is the **error
budget**: if the SLO allows 0.1% of requests to fail and you're well
under that, you have budget to take risk (ship a risky deploy); burn
through the budget and the answer becomes "stop shipping features, fix
reliability."

### 7. "Write an alerting rule for a high error rate. What's wrong with alerting on absolute error count?"

```yaml
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m])) > 0.05
  for: 10m
  labels:
    severity: page
  annotations:
    summary: "Error rate above 5% for 10 minutes"
```

**Answer:** Absolute error count (`errors > 100`) doesn't account for
traffic volume — 100 errors out of 100,000 requests is fine, 100 errors
out of 200 is an outage, and a fixed threshold can't tell them apart.
Alert on the **ratio** — errors as a fraction of total traffic — so the
threshold means the same thing at 2am and at peak load. The `for: 10m`
clause matters just as much as the expression: without it, a
30-second blip trips the alert and pages someone for something that
self-resolved before they even opened their laptop.

---

## Part 3: Distributed Tracing

### 8. "What problem does distributed tracing solve that logs and metrics don't?"

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def handle_order(order_id: str):
    with tracer.start_as_current_span("handle_order") as span:
        span.set_attribute("order_id", order_id)
        with tracer.start_as_current_span("charge_payment"):
            await payment_service.charge(order_id)
        with tracer.start_as_current_span("update_inventory"):
            await inventory_service.reserve(order_id)
```

**Answer:** Metrics tell you *that* something is slow, in aggregate,
across a whole fleet. Logs tell you *what happened* inside one service.
Neither shows the causal chain of one specific request as it crosses
service boundaries — was the 2-second response slow because of the
payment service, the inventory service, or the gateway itself? A trace
is a tree of spans sharing one `trace_id`, so a single slow request can
be opened up and the exact hop that ate the time is visible directly,
instead of inferred by cross-referencing logs from three services by
timestamp.

| Pros | Cons / Trade-offs |
|---|---|
| Shows exactly which hop/service caused the latency in one specific request | Real per-request overhead (span creation, context propagation) |
| Turns "which service is the bottleneck" from a guess into a direct answer | Full capture at high volume is expensive to store — needs sampling |

### 9. "How does trace context propagate across service boundaries, and what breaks it?"

**Answer:** The `trace_id`/`span_id`/`parent_id` (standardized as the
W3C `traceparent` header) rides along on every outgoing call as an HTTP
header, and each service that receives it starts its own child span
under the same trace. It breaks wherever something doesn't forward that
header: a message queue hop that doesn't carry headers into the message
payload, a background task boundary that starts a fresh context instead
of inheriting the caller's, or a proxy/gateway that strips unrecognized
headers. The symptom is always the same — a trace that mysteriously
"ends" at a service boundary instead of continuing into the next hop.

### 10. "Why sample traces instead of capturing every one, and how would you decide the rate?"

**Answer:** At real traffic volume, capturing and storing a full trace
for every single request is expensive and mostly redundant — most
requests are unremarkable. **Head-based sampling** decides at the start
of a request (e.g., "keep 1%") — cheap, but it might discard exactly the
slow or error trace you'd want later, since the decision is made before
anything interesting has happened. **Tail-based sampling** decides
after the full trace is assembled, so it can deliberately keep
everything that errored or was slow while sampling the boring majority
— better signal, more infrastructure to buffer and evaluate complete
traces before deciding. A common compromise: low-rate head sampling for
general visibility, plus an always-keep rule for anything that errors.

---

## Part 4: Dashboards and Alerting

### 11. "What makes a Grafana dashboard useful during an incident instead of just decorative?"

**Answer:** Organized around a method, not an arbitrary grid of
whatever metrics existed — commonly RED (Rate, Errors, Duration) for
request-driven services, or USE (Utilization, Saturation, Errors) for
resources. The panel someone needs first (current error rate, current
p99 latency) sits top-left, correlated to the same time range as
everything else on the page, ideally with a direct link out to the logs
or traces for the exact spike being looked at. A dashboard with forty
disconnected panels nobody has memorized the layout of is close to
useless three minutes into a live incident.

### 12. "How do you avoid alert fatigue on an on-call rotation?"

**Answer:** Alert on **symptoms** the user actually feels — SLO burn
rate, error ratio, latency — not on every internal cause (CPU at 80%
might be completely fine and expected). Every alert should be
actionable: if there's nothing a human can *do* about it at 3am, it
shouldn't page, it should go to a dashboard instead. Use a `for:`
duration so transient blips don't fire, route by real severity so a
"nice to know" doesn't page the same way as "the site is down," and
attach a runbook link to every alert so the response doesn't start with
"what does this even mean."

---

## Summary

1. **Structured logging** — named fields over free text, correlated by
   a shared request/trace ID, with redaction built into the pipeline
   rather than bolted on after the fact.
2. **Metrics** — Counter/Gauge/Histogram/Summary each answer a
   different question; Prometheus's pull model and PromQL ratios (not
   raw counts) are what make alerts meaningful.
3. **SLIs/SLOs/SLAs** — a measured indicator, an internal target with
   an error budget, and an external contractual commitment are three
   different things that get conflated constantly.
4. **Tracing** — the only tool that shows the causal chain of one
   request across service boundaries; propagation breaks silently at
   queue/async boundaries, and sampling is a cost/signal trade-off.
5. **Dashboards and alerts** — organized by RED/USE, alerting on
   user-facing symptoms with actionable, runbook-backed pages, not on
   every internal fluctuation.
