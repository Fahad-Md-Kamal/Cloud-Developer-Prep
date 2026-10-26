---
title: "Threat Detection & Monitoring"
---

# Threat Detection & Monitoring

Audit logging, anomaly detection, and vulnerability management —
catching what [Security Hardening](../architecture/security-hardening.md)'s
defenses don't stop outright, fast enough to matter. For rate limiting
and DDoS defense specifically, see
[Rate Limiting Strategies §5](../distributed-systems/rate-limiting-strategies.md#5-rate-limiting-as-a-defense-against-abuse-and-ddos).

## 1. Security Audit Logging

**"What must a security audit log capture, and what must it never contain?"**

```python
def log_security_event(event_type, user_id, ip, resource, outcome, correlation_id):
    logger.info(
        "security_event", event_type=event_type, actor=user_id, ip=ip,
        resource=resource, outcome=outcome, correlation_id=correlation_id,
    )  # never log passwords, tokens, or raw PII
```

**Answer:**

- Standardize fields across every event (actor, subject, action,
  resource, outcome, timestamp, correlation ID) so events are
  queryable across services, not just readable one at a time.
- Never log passwords, tokens, or raw PII — hash/tokenize identifiers
  where the raw value isn't actually needed.
- Ship to a centralized, access-restricted, integrity-protected store
  — the audit log is itself a target once an attacker is inside.
- Predefine alert rules (repeated auth failures, privilege escalation,
  key rotation, policy denials) — an unalerted log is just storage.

## 2. Anomaly Detection and Behavior Analytics

**"How do you detect account-takeover behavior without drowning the security team in false positives?"**

```python
def risk_score(activity, baseline) -> float:
    score = 0.0
    if activity.ip not in baseline.known_ips: score += 0.25       # geographic anomaly
    if is_impossible_travel(activity, baseline): score += 0.30
    if is_off_hours(activity.timestamp, baseline): score += 0.15
    if activity.device_id not in baseline.known_devices: score += 0.20
    return min(score, 1.0)
```

**Answer:**

- Build a baseline per user (typical times, locations, devices) —
  "normal" varies hugely by role and person, a global threshold won't fit.
- Correlate multiple weak signals instead of alerting on any single
  one — impossible travel + new device + off-hours is strong; any one
  alone usually isn't.
- Route medium-risk to step-up auth; reserve hard blocks for
  high-confidence cases.
- Tune against precision/recall with real security-ops feedback, not a
  model's default sensitivity — an untrusted detector's alerts get
  ignored within a month.

**Follow-up — "isn't ML overkill here?"** Often, to start — a handful
of correlated rule-based signals catches most real cases and is far
easier to explain/debug than an opaque model. Reach for ML once you
have enough labeled incident data to validate it's actually doing
better.

## 3. Vulnerability Management and Security Testing

**"How do you keep dependency and code vulnerabilities from piling up silently?"**

```bash
bandit -r src/ -f json          # SAST: code-level issues
safety check -r requirements.txt --json   # dependency vulnerabilities
```

**Answer:**

- Automate SAST, dependency scanning, and container image scanning in
  CI — on every change, not as an occasional manual exercise.
- Prioritize by actual risk (a critical CVE in an internet-facing
  service beats a medium finding in an internal batch job).
- Track remediation to closure, not just detection — a scanner nobody
  acts on adds process without adding security.

---

## Code Samples

See [Authentication Patterns' Code Samples](../architecture/authentication-patterns.md#code-samples)
for the full `code_samples/chapter-4/` runnable examples this chapter
group shares.
