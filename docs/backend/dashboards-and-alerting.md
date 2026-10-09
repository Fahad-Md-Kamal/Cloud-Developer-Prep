---
title: "Dashboards & Alerting"
---

# Dashboards & Alerting

What makes a Grafana dashboard actually useful during an incident, and
avoiding alert fatigue on an on-call rotation — the layer that turns
[Structured Logging](structured-logging.md) and
[Metrics & Prometheus](metrics-and-prometheus.md) into something a
human can act on at 3am.

## 1. "What makes a Grafana dashboard useful during an incident instead of just decorative?"

**Answer:** Organized around a method, not an arbitrary grid of
whatever metrics existed — commonly RED (Rate, Errors, Duration) for
request-driven services, or USE (Utilization, Saturation, Errors) for
resources. The panel someone needs first (current error rate, current
p99 latency) sits top-left, correlated to the same time range as
everything else on the page, ideally with a direct link out to the logs
or traces for the exact spike being looked at. A dashboard with forty
disconnected panels nobody has memorized the layout of is close to
useless three minutes into a live incident.

## 2. "How do you avoid alert fatigue on an on-call rotation?"

**Answer:** Alert on **symptoms** the user actually feels — SLO burn
rate, error ratio, latency (see
[Metrics & Prometheus §3](metrics-and-prometheus.md#3-design-slis-and-slos-for-an-api-endpoint-how-is-an-slo-different-from-an-sla)
for the error-budget mechanism behind this) — not on every internal
cause (CPU at 80% might be completely fine and expected). Every alert
should be actionable: if there's nothing a human can *do* about it at
3am, it shouldn't page, it should go to a dashboard instead. Use a
`for:` duration so transient blips don't fire, route by real severity
so a "nice to know" doesn't page the same way as "the site is down,"
and attach a runbook link to every alert so the response doesn't start
with "what does this even mean."

---

## Code Samples

No dedicated code samples yet for this page — dashboard layout and
alert routing are configuration concerns (Grafana JSON, Alertmanager
rules), not something to demo as a standalone script.
