---
title: "LLM Gateway & Multi-Provider Integration"
---

# LLM Gateway & Multi-Provider Integration

Putting one API layer in front of OpenAI, Anthropic, Gemini, and
others — the pattern behind "unified LLM gateway" in a job description,
and what LiteLLM actually does for you.

## 1. "Why put a gateway layer in front of multiple LLM providers instead of calling each API directly?"

```python
# Without a gateway -- every call site knows about every provider's SDK
if provider == "openai":
    response = openai.chat.completions.create(model="gpt-4o", messages=messages)
elif provider == "anthropic":
    response = anthropic.messages.create(model="claude-opus-4", messages=messages)
elif provider == "gemini":
    response = genai.GenerativeModel("gemini-2.0").generate_content(messages)
```

**Answer:** Without a gateway, every call site in the codebase needs to
know each provider's SDK, request shape, and response shape — a
provider outage, price change, or model deprecation means hunting down
every call site. A gateway centralizes provider selection, credential
management, and response normalization behind one interface, so
switching or adding a provider is a config change, not a code change
scattered across the app.

**Where this maps to the platform's requirements:** "unified API layer,"
"authentication and API key lifecycle," and "evaluate new model
releases" are all naturally gateway-layer responsibilities, not
per-caller responsibilities.

## 2. "How does LiteLLM let you swap providers without changing application code?"

```python
from litellm import completion

# Same call shape regardless of which provider actually serves it --
# LiteLLM translates to each provider's native API internally.
response = completion(
    model="gpt-4o",  # or "claude-opus-4", "gemini/gemini-2.0-flash", ...
    messages=[{"role": "user", "content": "Summarize this document"}],
)
```

**Answer:** LiteLLM implements the OpenAI SDK's call shape as a
universal interface and translates it to whichever provider's native
API the `model` string points at — the calling code stays identical
whether it's actually hitting OpenAI, Anthropic, Gemini, or a
self-hosted model. Swapping providers, or falling back to a second
provider on failure, becomes a config/routing change instead of a
rewrite.

**Likely follow-up — "what does this NOT solve for you?"** Provider
responses still differ in subtle ways LiteLLM can't fully paper over —
token counting conventions, function-calling schema quirks, and content
policy differences. Test against the actual provider you're routing to,
not just against the unified interface.

## 3. "How do you handle a provider outage or rate limit gracefully in a multi-provider setup?"

```python
from litellm import completion
from litellm.exceptions import RateLimitError, ServiceUnavailableError

def completion_with_fallback(messages, primary="gpt-4o", fallback="claude-opus-4"):
    try:
        return completion(model=primary, messages=messages, timeout=10)
    except (RateLimitError, ServiceUnavailableError):
        return completion(model=fallback, messages=messages, timeout=10)
```

**Answer:** Explicit fallback chains (try provider A, fall back to
provider B on a rate limit or 5xx) rather than letting a provider
outage become a user-facing outage. LiteLLM supports this natively via
a router with a configured fallback list, but the underlying pattern —
timeout + typed exception handling + a secondary provider — is the
part worth understanding independent of the library.

| Pros | Cons / Trade-offs |
|---|---|
| One interface, one place to add auth/logging/retries for every provider | Another moving piece in the request path — a gateway bug affects every provider |
| Swapping or A/B testing providers is a config change | Abstraction can hide provider-specific capabilities (a feature one provider has and others don't) |
| Centralizes cost tracking and rate-limit handling across providers | Adds latency (however small) versus calling a provider directly |

## 4. "Beyond failing over on error, how do you load-balance across multiple providers or deployments during normal operation?"

```python
from dataclasses import dataclass

@dataclass
class ProviderMetrics:
    success_rate: float
    average_latency: float
    cost_per_token: float

def select_provider(providers: list[str], metrics: dict[str, ProviderMetrics],
                     strategy: str) -> str:
    if strategy == "lowest_cost":
        return min(providers, key=lambda p: metrics[p].cost_per_token)
    if strategy == "lowest_latency":
        return min(providers, key=lambda p: metrics[p].average_latency)
    if strategy == "highest_success_rate":
        return max(providers, key=lambda p: metrics[p].success_rate)
    raise ValueError(f"unknown strategy: {strategy}")
```

**Answer:** Failover is reactive — it only kicks in once a provider is
already failing. Load balancing is proactive: route *every* request
based on live metrics (rolling success rate, average latency,
cost-per-token) rather than sending everything to one primary until it
breaks. Common strategies are weighted-random (traffic split
proportional to a target ratio, e.g. for cost control), lowest-latency
(route to whichever provider is currently fastest), and
highest-success-rate (route away from a provider that's degrading
before it fully fails). A hybrid weighted score combining cost +
latency + success rate is what production routers actually use, rather
than picking a single dimension — pure lowest-cost routing will happily
send traffic to a provider that's slow or flaky, if it's cheap.

**Likely follow-up — "how do you avoid oscillating between providers
when metrics are noisy?"** Use a rolling window (last N requests or
last T minutes) rather than instantaneous values, and require a
metric to cross a threshold by a meaningful margin — not just be
momentarily lower — before shifting significant traffic, otherwise the
router thrashes on normal variance.

## 5. "How would you A/B test two models or providers against each other in production?"

```python
from dataclasses import dataclass

@dataclass
class ExperimentConfig:
    name: str
    traffic_split: dict[str, float]  # e.g. {"gpt-4o": 0.5, "claude-opus-4": 0.5}
    minimum_sample_size: int

def assign_variant(config: ExperimentConfig, rng) -> str:
    roll = rng.random()
    cumulative = 0.0
    for provider, share in config.traffic_split.items():
        cumulative += share
        if roll <= cumulative:
            return provider
    return next(iter(config.traffic_split))  # fallback for float rounding
```

**Answer:** Split live traffic between variants by a configured
percentage, record per-variant metrics (latency, cost, success rate,
and — the part that's LLM-specific — some proxy for output quality:
user thumbs-up/down, a downstream task success signal, or an
LLM-as-judge score), and don't call a winner until you've hit a minimum
sample size and a real statistical significance test, not just "variant
B's average looked better this afternoon." A multi-armed bandit
(shifting traffic toward the better-performing variant *during* the
experiment instead of waiting for a fixed-duration test to end) trades
some statistical cleanliness for faster convergence and less traffic
wasted on a clearly-losing variant — reasonable for cost-sensitive
experiments, less rigorous for a decision that needs to hold up to
scrutiny.

| Pros | Cons / Trade-offs |
|---|---|
| Data-driven model/provider selection instead of anecdote-driven | Needs real traffic volume to reach significance — slow for low-traffic features |
| Bandit approach limits cost/quality exposure to the losing variant | Bandit's faster convergence trades off some statistical rigor |
| Catches provider-specific quality differences a benchmark might miss | Output-quality metrics for LLMs are inherently harder to define than latency/cost |

## 6. "Beyond routing by provider health or cost, how do you cut spend on queries that don't need your best model?"

```python
async def generate(query: str, complexity: str = "auto"):
    if complexity == "auto":
        # Cheap model classifies the query cheaply before the real call
        complexity = await cheap_model.classify_complexity(query)

    model = "gpt-3.5-turbo" if complexity == "simple" else "gpt-4"
    return await llm.generate(query, model=model)
```

**Answer:**

- Not every request needs the most capable (and most expensive) model
  — route by **query complexity**, not just by provider health/cost.
- A cheap, fast model can act as a triage step: classify whether a
  query is simple enough for a cheap model or genuinely needs the
  expensive one, before the real generation call happens.
- This is a distinct dimension from the provider-level load balancing
  in question 4 — that routes *between providers* for the same
  request; this routes *between model tiers* based on what the
  request actually needs.

**Likely follow-up — "what's the risk of getting the triage step wrong?"**

- A misclassified complex query routed to the cheap model produces a
  worse answer than the user would have gotten otherwise — the triage
  step itself needs monitoring (sampling misclassified cases, not
  just trusting it silently).
- The triage call itself has a cost and adds latency — worth it only
  when the cheap/expensive split is skewed enough (most traffic is
  genuinely simple) that the savings outweigh the extra call.

---

## Code Samples

- `code_samples/chapter-21/multi_provider_llm_client.py` — provider
  abstraction, failover, rate limiting, async connection pooling across
  providers
- `code_samples/chapter-21/ab_testing_framework.py` — traffic-split
  experiment management, multi-armed bandit routing, statistical
  significance testing
