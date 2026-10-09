---
title: "Structured Logging"
---

# Structured Logging

Why structured (JSON) logging beats plain text, keeping PII and secrets
out of logs without making them useless, and picking a log level that
isn't arbitrary — the first layer of observability, alongside
[Metrics & Prometheus](metrics-and-prometheus.md) and
[Distributed Tracing](distributed-tracing.md).

## 1. "Why structured (JSON) logging instead of plain text log lines?"

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

## 2. "How do you avoid logging PII or secrets while keeping logs actually useful?"

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

## 3. "What log level would you actually use, and how do you avoid that being arbitrary?"

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

## Code Samples

- `code_samples/chapter-6/observability.py` — a `Tracer`/`TraceSpan`
  pair, `MetricsCollector`, `StructuredLogger`, and `HealthMonitor`
  (shared with [Metrics & Prometheus](metrics-and-prometheus.md) and
  [Distributed Tracing](distributed-tracing.md))

```bash
pip install -r code_samples/chapter-6/requirements.txt
python code_samples/chapter-6/observability.py
```
