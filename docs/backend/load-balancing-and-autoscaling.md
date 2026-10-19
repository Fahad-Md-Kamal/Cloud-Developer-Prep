---
title: "Load Balancing & Auto-Scaling"
---

# Load Balancing & Auto-Scaling

Choosing a load-balancing algorithm, and scaling on the signal that
actually reflects user impact instead of a misleading one — part of the
same distributed-systems discussion as
[Fault Tolerance Patterns](fault-tolerance-patterns.md).

## 1. Choosing a Load-Balancing Algorithm

**"Round-robin, weighted round-robin, least-connections — how do you
pick?"**

```python
class LeastConnectionsBalancer:
    def select(self, backends: list[Backend]) -> Backend:
        return min(backends, key=lambda b: b.active_connections)
```

**Answer:** Each algorithm exists because requests and backends
*aren't* always equivalent — the right pick depends on exactly which
way they're not.

- **Round-robin** — send each request to the next backend in turn.
  Fine when requests are short and similar, and every backend is an
  identical instance — there's nothing uneven to account for.
- **Weighted round-robin** — same idea, but biased toward
  higher-capacity or lower-latency backends. Needed once instances
  *aren't* identical — mixed instance sizes, or a multi-region setup
  where some backends are simply closer to the user than others.
- **Least connections** — send each request to whichever backend
  currently has the fewest in-flight requests. Needed when requests
  vary a lot in how long they take — plain round-robin would keep
  sending a 5th request to a backend already stuck on 4 slow ones,
  while other backends sit idle.
- **Geo-routing** — send each request to the backend nearest the
  user's actual location. The same idea already covered for DNS-level
  routing in
  [Route 53's routing policies](../cloud-devops/load-balancing-and-dns.md#routing-policies),
  just applied at the load balancer instead of at DNS resolution.
- **Session affinity (sticky sessions)** — a separate concern from all
  of the above: keep sending the *same* user to the *same* backend.
  Only needed when a service holds per-user state in process memory —
  and it needs an expiry, or affinity to an instance that's since been
  replaced quietly breaks requests instead of failing loudly.

**Likely follow-up — "what's the risk with sticky sessions at scale?"**

- **Hot shards.** If the hash deciding which backend a user sticks to
  isn't well distributed, some backends end up carrying far more users
  than others while the rest sit idle — the exact problem load
  balancing exists to prevent, now reintroduced by the stickiness
  itself.

## 2. Auto-Scaling on the Right Signal

**"CPU usage looks fine but the service is falling behind. What went
wrong with the scaling policy?"**

**Answer:** CPU usage doesn't actually measure what matters for
I/O-bound or queue-backed services.

- **Why CPU misleads here:** a service can sit CPU-idle while every
  request is simply *waiting* — on a slow downstream call, or on a
  queue that's draining slower than it's filling. Nothing about that
  shows up as CPU load, so a CPU-based scaling policy never triggers.
- **The fix — scale on multiple signals instead:** P95/P99 latency,
  error rate, and — for anything sitting behind a queue — queue depth
  or consumer lag.
- **Queue lag specifically is a leading indicator**, not a lagging one:
  it rises *before* latency does. Scaling on it gives the system time
  to add capacity before requests actually start timing out, instead
  of reacting only after users are already affected.

---

## Code Samples

Runnable examples in `code_samples/chapter-7/` (shared with
[Fault Tolerance Patterns](fault-tolerance-patterns.md) /
[Consistency & Consensus](consistency-and-consensus.md) /
[Data & Capacity Scaling](data-and-capacity-scaling.md)):

- `load_balancing.py` — `WeightedRoundRobin`, `LeastConnectionsBalancer`,
  `GeoRouter`, `TrafficScaler`

```bash
pip install -r code_samples/chapter-7/requirements.txt
python code_samples/chapter-7/load_balancing.py
```
