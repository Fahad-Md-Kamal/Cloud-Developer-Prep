---
title: "LLM APIs & Providers"
---

# LLM APIs & Providers

Provider selection, auth, cost, and the production client-side concerns
(async architecture, token management, rate limiting, retries,
monitoring) that come up when integrating LLM APIs directly — as
opposed to routing through a gateway. For the gateway/multi-provider
abstraction layer itself, see
[LLM Gateway & Multi-Provider Integration](llm-gateway-multi-provider.md);
for response caching, see
[LLM Response Caching](llm-response-caching.md).

## 1. "How do you choose between OpenAI, Anthropic, and Vertex AI/Azure OpenAI for a given task?"

```python
PROVIDER_PROFILES = {
    "openai/gpt-4o": {
        "context_tokens": 128_000,
        "strengths": ["function calling", "vision", "broad tooling ecosystem"],
    },
    "anthropic/claude-opus-4": {
        "context_tokens": 200_000,
        "strengths": ["long-document reasoning", "large context, high accuracy"],
    },
    "google/gemini-2.0-flash": {
        "context_tokens": 1_000_000,
        "strengths": ["very large context", "native multimodal", "GCP-native"],
    },
    "azure/gpt-4o": {
        "context_tokens": 128_000,
        "strengths": ["data residency", "enterprise compliance (SOC 2, HIPAA)"],
    },
}
```

**Answer:** There's no universally "best" provider — the decision is
driven by the specific task and constraints. Context window matters for
long-document work (Claude and Gemini both give more headroom than
GPT-4o before you need chunking). Function-calling maturity and
ecosystem tooling still favor OpenAI for agentic/tool-use-heavy
workloads. Compliance and data-residency requirements (regulated
industries, contractual data-location constraints) often force Azure
OpenAI even when it isn't the strongest model, because it's deployed
inside the customer's own Azure tenant. In practice, teams pick a
*default* provider and keep the abstraction layer (see the gateway
page) thin enough that a second provider is a config change, not a
rewrite, when a task's requirements shift.

**Likely follow-up — "would you hardcode this mapping?"** No — externalize
it as config (model name, context length, cost per 1k tokens,
capabilities) so a new model release or price change doesn't require a
code deploy. `code_samples/chapter-21/config/llm_providers.json` is a
worked example of this: per-provider rate limits, per-model context
length and `cost_per_1k_tokens`, and a capability list, all as data.

## 2. "How do you manage API keys and credentials for multiple LLM providers securely?"

```python
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class APICredentials:
    api_key: str
    organization_id: Optional[str] = None
    project_id: Optional[str] = None

class CredentialManager:
    def __init__(self, secrets_client):
        self._secrets = secrets_client  # e.g. a Vault/Secrets Manager client

    def get_credentials(self, provider: str) -> APICredentials:
        # Never read raw keys from source, env files committed to the repo,
        # or application config -- pull from a secrets manager per request/startup.
        secret = self._secrets.get_secret(f"llm/{provider}")
        return APICredentials(**secret)
```

**Answer:** Treat LLM API keys the same as any other production secret:
pulled from a secrets manager (not `.env` files or source), scoped per
environment (dev/staging/prod get separate keys so a leaked dev key
can't touch production spend), and rotated on a schedule without a
deploy — the credential manager re-fetches rather than the key being
baked into a config map at build time. Add per-key usage/cost
attribution so a compromised or misbehaving key is identifiable from
billing data alone, and put role-based access on who can *retrieve* a
raw key vs. who can only call through an internal service that holds
one.

| Pros | Cons / Trade-offs |
|---|---|
| Centralized rotation — one place to rotate/revoke, not N call sites | Adds a dependency on the secrets manager's own availability |
| Per-environment isolation limits blast radius of a leaked key | More moving parts than reading `os.environ` directly |
| Usage/cost attribution per key aids audit and anomaly detection | Requires discipline — a hardcoded fallback key defeats the whole point |

## 3. "What actually drives LLM API cost, and how do you estimate it before shipping a feature?"

```python
from decimal import Decimal

# Real asymmetry: output tokens typically cost 2-4x input tokens
PRICING_PER_1K = {
    "gpt-4o": {"input": Decimal("0.005"), "output": Decimal("0.015")},
    "gpt-3.5-turbo": {"input": Decimal("0.0005"), "output": Decimal("0.0015")},
}

def estimate_monthly_cost(model: str, requests_per_day: int,
                           avg_input_tokens: int, avg_output_tokens: int) -> Decimal:
    price = PRICING_PER_1K[model]
    per_request = (Decimal(avg_input_tokens) / 1000 * price["input"]
                   + Decimal(avg_output_tokens) / 1000 * price["output"])
    return per_request * requests_per_day * 30
```

**Answer:** Cost is `(input_tokens * input_price) + (output_tokens *
output_price)` per request, summed over volume — but the two token
types aren't priced equally: output tokens are consistently the more
expensive side (roughly 2-4x input, provider-dependent), so a feature
that generates long completions (summaries, long-form drafts) costs far
more per request than one that just classifies or extracts a short
answer from a long input. Before shipping, estimate with realistic
average token counts for *both* sides, multiply by expected daily
volume, and sanity-check against a monthly budget — this catches
"we picked GPT-4 for a high-volume, low-value classification task" long
before it shows up as a bill. `cost_optimization_system.py` builds this
into a full tracker with per-department/per-application cost
attribution and downgrade-opportunity detection (flagging requests
where a cheaper model would likely produce equivalent quality).

## 4. "Design an async client for calling an LLM API under load — what does it need beyond `await client.chat.completions.create(...)`?"

```python
import asyncio
import aiohttp

class AsyncLLMClient:
    def __init__(self, max_concurrent_requests: int = 100, timeout_s: float = 30):
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._session: aiohttp.ClientSession | None = None
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(self, *exc):
        await self._session.close()

    async def generate(self, prompt: str, model: str) -> str:
        async with self._semaphore:  # bound concurrency, don't overrun the provider
            return await self._request(prompt, model)
```

**Answer:** A bare per-call `await` doesn't bound concurrency — fan out
1,000 requests with `asyncio.gather` and you'll fire 1,000 simultaneous
connections at the provider and get rate-limited immediately. A
production client needs: a semaphore (or similar) capping in-flight
requests to a sane number; one shared, reused `aiohttp`/`httpx` session
for connection pooling instead of opening a new TCP+TLS connection per
call; explicit per-request timeouts (LLM calls can hang far longer than
a typical REST call under provider-side load); and a way to fail fast
via a circuit breaker when the provider is clearly down, instead of
queuing requests behind a dead endpoint.

**Likely follow-up — "how is this different from just using the
provider SDK's built-in async client?"** The SDK's async client handles
the HTTP mechanics, but concurrency bounding, cross-provider connection
pooling, and application-level circuit breaking are still the caller's
responsibility — the SDK doesn't know your target throughput or your
fallback provider.

## 5. "How do you count and manage tokens before sending a request, and why does it matter?"

```python
import tiktoken

class TokenManager:
    def __init__(self):
        self._encoders = {"gpt-4o": tiktoken.encoding_for_model("gpt-4o")}

    def count_tokens(self, text: str, model: str) -> int:
        return len(self._encoders[model].encode(text))

    def fits_budget(self, prompt: str, model: str, max_input_tokens: int) -> bool:
        return self.count_tokens(prompt, model) <= max_input_tokens
```

**Answer:** Token count determines both cost and whether a request even
fits the model's context window — sending a prompt that exceeds it
fails outright, not gracefully. `tiktoken` gives exact counts for
OpenAI's tokenizer; other providers don't expose an equivalent public
tokenizer, so token counts for Claude or Gemini are estimates (roughly
4 characters per token as a rule of thumb) unless the provider exposes
a counting endpoint. In practice: count before sending, truncate or
summarize the least-important context first when over budget (not a
blind tail-truncation that might cut off the actual question), and
budget tokens across system prompt + conversation history + user input
+ reserved output space — it's easy to forget that the model's own
"max tokens" setting for the *response* also eats into what's available
in a shared context-length limit on some providers.

## 6. "How do you rate-limit your own outgoing requests to a provider, instead of just reacting to 429s?"

```python
import time
from collections import deque
from asyncio import Lock

class SlidingWindowLimiter:
    def __init__(self, max_requests_per_minute: int):
        self._limit = max_requests_per_minute
        self._request_times: deque[float] = deque()
        self._lock = Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.time()
            while self._request_times and now - self._request_times[0] > 60:
                self._request_times.popleft()
            if len(self._request_times) < self._limit:
                self._request_times.append(now)
                return True
            return False
```

**Answer:** Waiting for a 429 and then backing off means you've already
wasted a request and eaten a latency hit for the caller behind it. A
client-side limiter (sliding window or token bucket, sized to the
provider's published per-minute/per-day limits) throttles *before* the
request goes out, so the app degrades predictably — queue or reject
early — rather than discovering the limit reactively. This is separate
from the routing/failover logic in a multi-provider gateway (see the
gateway page): this is per-provider, client-side throttling to avoid
tripping the limit in the first place, one layer below "which provider
do I fall back to when I do get rate-limited." `config/rate_limits.json`
in the code samples is a worked example of per-provider limits (global,
per-provider requests/min, tokens/min) externalized as config rather
than hardcoded constants.

## 7. "Walk through error handling and retry strategy for an LLM API call — what's different from a typical REST API retry?"

```python
import random
from enum import Enum

class LLMErrorType(Enum):
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    MODEL_OVERLOAD = "model_overload"
    CONTENT_FILTER = "content_filter"     # not retryable
    AUTHENTICATION = "authentication"      # not retryable

MAX_RETRIES = {
    LLMErrorType.RATE_LIMIT: 5,
    LLMErrorType.TIMEOUT: 3,
    LLMErrorType.MODEL_OVERLOAD: 4,
    LLMErrorType.CONTENT_FILTER: 0,
    LLMErrorType.AUTHENTICATION: 0,
}

def backoff_delay(attempt: int, error_type: LLMErrorType) -> float:
    base = 2 ** attempt
    jitter = random.uniform(0.5, 1.5)
    return base * jitter * (2 if error_type == LLMErrorType.RATE_LIMIT else 1)
```

**Answer:** The key difference from a generic REST retry is
*classification* — an LLM API's failure modes aren't uniformly
retryable. A `429` or a transient `503` (model overload) should retry
with exponential backoff and jitter; a content-filter rejection or an
auth failure retrying won't ever succeed and just burns time and
quota — those should fail fast and surface to the caller. Rate limits
specifically warrant a longer backoff than a generic timeout, since
hammering a rate-limited endpoint with fast retries makes the underlying
throttling worse. Wrap the whole thing in a circuit breaker so a
provider that's clearly down (multiple consecutive failures) stops
receiving new requests for a cooldown window instead of every in-flight
request individually working through its own retry budget against a
dead endpoint.

| Pros | Cons / Trade-offs |
|---|---|
| Error-type-specific retry avoids wasting attempts on unretryable failures | Requires knowing each provider's actual error taxonomy — not one-size-fits-all |
| Jittered exponential backoff avoids thundering-herd retries | Adds latency for the caller on the retried path — needs a sane overall timeout budget |
| Circuit breaker stops cascading load onto an already-struggling provider | Another piece of state to monitor — a stuck-open breaker silently kills traffic |

## 8. "What do you track in production to catch cost or performance problems before they page someone?"

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LLMRequestMetrics:
    timestamp: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_dollars: float
    success: bool
    application: str
```

**Answer:** Per-request metrics (provider, model, token counts,
latency, cost, success, and an application/team label for attribution)
feeding real-time aggregation, not just periodic batch reports. The
dimensions that actually catch problems early: cost by
provider/model/application (a single misconfigured caller can spike
spend fast), latency percentiles rather than averages (P95/P99 catch
degradation an average hides), and success-rate trend per provider (a
slow decline is a leading indicator of a provider having a bad day,
before it becomes an outage). Pair this with budget alerts (threshold
on projected monthly spend, not just current spend) and anomaly
detection on the request-volume/cost time series — a sudden 10x spike
is usually a bug (an unbounded retry loop, a runaway batch job), not
organic growth. `cost_optimization_system.py` and
`fastapi_llm_server.py` show this wired into an actual service: the
FastAPI layer emits the metrics, the cost system aggregates and flags
downgrade/caching opportunities from them.

## 9. "What security and compliance monitoring is specific to LLM APIs, as opposed to a typical API?"

```python
import re

PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "email": r"\b[\w.-]+@[\w.-]+\.\w+\b",
}

def scan_prompt_for_pii(prompt: str) -> list[str]:
    return [pii_type for pii_type, pattern in PII_PATTERNS.items()
            if re.search(pattern, prompt)]
```

**Answer:** A typical API's security monitoring is about who can call
it; an LLM API adds monitoring of *what's inside the payload itself* on
both sides — the prompt going out to a third-party provider, and the
completion coming back. On the outbound side: scanning prompts for PII
before they leave the network boundary (a name, SSN, or medical detail
pasted into a prompt by an end user shouldn't silently go to an external
provider without a policy decision about that), with redaction or
blocking depending on data classification. On the inbound side:
scoring responses for safety/policy violations before they reach a user
or get logged verbatim. Both need an audit trail — which requests
touched PII, what was redacted, whether a response tripped a safety
check — because compliance frameworks (GDPR, HIPAA, SOC 2) require
demonstrating this happened, not just that the capability exists.
`security_monitoring.py` implements PII detection/redaction, response
safety scoring, and audit logging together; the test suite in
`tests/test_comprehensive_llm_system.py` includes security/auth test
cases for this layer.

| Pros | Cons / Trade-offs |
|---|---|
| Catches PII leakage to third-party providers before it happens, not after an incident | Regex/pattern-based PII detection has real false-negative and false-positive rates |
| Audit trail satisfies compliance evidence requirements (GDPR/HIPAA/SOC 2) | Scanning every prompt/response adds latency to the request path |
| Response safety scoring catches provider-side quality/safety regressions | Needs tuning per data-sensitivity level — over-redaction breaks legitimate use cases |

---

## Code Samples

- `code_samples/chapter-21/cost_optimization_system.py` — real-time cost
  tracking, model-downgrade opportunity detection, predictive monthly
  cost modeling
- `code_samples/chapter-21/security_monitoring.py` — PII detection and
  redaction, response safety scoring, audit logging
- `code_samples/chapter-21/fastapi_llm_server.py` — production FastAPI
  server: auth/rate-limiting middleware, multi-provider request
  handling, streaming responses
- `code_samples/chapter-21/production_integration_example.py` — all of
  the above (client, cost tracking, caching, security, A/B testing)
  wired together into one service
- `code_samples/chapter-21/tests/test_comprehensive_llm_system.py` —
  unit/integration/performance/security test patterns for this layer
- `code_samples/chapter-21/config/llm_providers.json` — per-provider
  model catalog: context length, cost per 1k tokens, capabilities
- `code_samples/chapter-21/config/rate_limits.json` — global and
  per-provider rate limit config (requests/min, tokens/min, concurrency)
