---
title: "Metrics & Prometheus"
---

# Metrics & Prometheus

Prometheus's four metric types, how it actually pulls data out of an
application, and the SLI/SLO/SLA distinction everyone conflates —
alongside [Structured Logging](structured-logging.md) and
[Distributed Tracing](distributed-tracing.md).

## 1. "Explain Prometheus's four metric types and when you'd reach for each."

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
|---|---|---|
| Histogram | Aggregates correctly across instances; percentiles computed centrally | Bucket boundaries must be chosen up front — wrong buckets lose precision |
| Summary | Cheaper to compute per instance; exact quantiles for that instance | Not composable — can't merge quantiles from multiple instances meaningfully |

## 2. "How does Prometheus actually get metrics out of an application — push or pull?"

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

## 3. "Design SLIs and SLOs for an API endpoint. How is an SLO different from an SLA?"

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

## 4. "Write an alerting rule for a high error rate. What's wrong with alerting on absolute error count?"

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
self-resolved before they even opened their laptop. See
[Dashboards & Alerting §2](dashboards-and-alerting.md#2-how-do-you-avoid-alert-fatigue-on-an-on-call-rotation)
for the broader alerting philosophy this rule is one example of.

---

## Code Samples

- `code_samples/chapter-6/observability.py` — includes a
  `MetricsCollector` alongside the `Tracer`/`StructuredLogger`/
  `HealthMonitor` referenced from
  [Structured Logging](structured-logging.md).

```bash
pip install -r code_samples/chapter-6/requirements.txt
python code_samples/chapter-6/observability.py
```
