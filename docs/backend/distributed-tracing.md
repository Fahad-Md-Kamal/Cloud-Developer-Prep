---
title: "Distributed Tracing"
---

# Distributed Tracing

What tracing shows that logs and metrics don't, how trace context
propagates across service boundaries (and what breaks it), and why you
sample instead of capturing everything — alongside
[Structured Logging](structured-logging.md) and
[Metrics & Prometheus](metrics-and-prometheus.md).

## 1. "What problem does distributed tracing solve that logs and metrics don't?"

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

## 2. "How does trace context propagate across service boundaries, and what breaks it?"

**Answer:** The `trace_id`/`span_id`/`parent_id` (standardized as the
W3C `traceparent` header) rides along on every outgoing call as an HTTP
header, and each service that receives it starts its own child span
under the same trace. It breaks wherever something doesn't forward that
header: a message queue hop that doesn't carry headers into the message
payload, a background task boundary that starts a fresh context instead
of inheriting the caller's, or a proxy/gateway that strips unrecognized
headers. The symptom is always the same — a trace that mysteriously
"ends" at a service boundary instead of continuing into the next hop.

## 3. "Why sample traces instead of capturing every one, and how would you decide the rate?"

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

## Code Samples

- `code_samples/chapter-6/observability.py` — includes the `Tracer`/
  `TraceSpan` pair referenced from
  [Structured Logging](structured-logging.md).

```bash
pip install -r code_samples/chapter-6/requirements.txt
python code_samples/chapter-6/observability.py
```
