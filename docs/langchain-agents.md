---
title: "LangChain Agents"
---

# LangChain Agents

LangChain's own agent, tool, memory, and chain-composition fundamentals —
the building blocks you reach for before pulling in the wider "Lang*"
ecosystem covered in [LangChain Ecosystem: LangGraph, LangSmith,
LangServe](langchain-ecosystem.md), or multi-agent coordination as its own
topic (framework-agnostic patterns, with Autogen as a concrete example),
covered in [Multi-Agent Systems](multi-agent-systems.md). For general
FastAPI patterns that apply regardless of what's behind the endpoint,
see [Dependency Injection & Background Tasks](fastapi-dependency-injection.md)
and [Performance & Production Patterns](fastapi-performance-patterns.md)
— this page only covers what's specific to serving a LangChain agent.

## 1. Agent Types and Execution Patterns — "ReAct vs Plan-and-Execute vs a plain conversational chain — when do you pick which?"

```python
# ReAct: interleave reasoning and action, one step at a time
Thought: I need the customer's current subscription tier before I can answer.
Action: lookup_subscription
Observation: tier=pro, renews=2026-11-01
Thought: I have what I need to answer directly.
Final Answer: You're on the Pro plan, renewing November 1st.
```

**Answer:** A **ReAct** agent picks one action at a time and decides the
next step only after seeing that action's result — good when the right
sequence of tool calls genuinely depends on what earlier calls return (you
can't know which document to fetch until a search tool tells you what
exists). A **Plan-and-Execute** agent front-loads a full plan, then
executes it — cheaper (one planning call instead of a reasoning call per
step) and more predictable when the task decomposes cleanly up front, but
it can't easily adapt mid-plan if an early step returns something
unexpected without re-planning. A plain **conversational** chain skips
tool-calling reasoning entirely and just carries memory across turns — the
right choice when the task is "hold a context-aware conversation," not
"decide which of N tools to call."

**Likely follow-up — "why not always use ReAct, since it's the most
flexible?"** Cost and latency: every step is its own LLM call, so a
five-step ReAct task is five round-trips instead of one planning call.
Reach for Plan-and-Execute once you've seen that a task's steps are
largely independent of each other's results — you're paying for
adaptability you don't need.

| Pattern | Best for | Trade-off |
|---|---|---|
| ReAct | Steps depend on prior results (search, then decide what to fetch next) | One LLM round-trip per step — slow and token-expensive on long tasks |
| Plan-and-Execute | Task decomposes cleanly into largely independent steps | Can't easily adapt mid-plan without a full re-plan |
| Conversational (no tools) | Multi-turn chat where memory matters more than tool use | No tool-calling reasoning at all — wrong tool for anything action-oriented |

## 2. Tool Integration and Custom Tool Creation — "How do you build a custom tool, and what actually makes an agent pick the right one?"

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class DocSearchInput(BaseModel):
    query: str = Field(description="Keywords to search the internal knowledge base for.")
    max_results: int = Field(default=5, description="Maximum number of results to return.")

@tool("search-internal-docs", args_schema=DocSearchInput)
def search_internal_docs(query: str, max_results: int = 5) -> str:
    """Search the internal knowledge base for docs relevant to a query.
    Use this before answering any question about internal policy or process."""
    results = knowledge_base.search(query, limit=max_results)
    return "\n".join(f"- {r.title}: {r.snippet}" for r in results)
```

**Answer:** The agent doesn't see your tool's code — it sees the tool's
*name* and *docstring/description*, and picks a tool the same way it
picks any next token: based on how well the description matches the
current context. That makes the description the actual interface: state
precisely what the tool does and, ideally, *when* to use it ("use this
before answering any question about..."), not just what it accepts. Keep
each tool narrow and single-purpose — a `search_docs` and a
`search_tickets` tool the agent can tell apart beats one
`search_everything` tool with an ambiguous description. Validate inputs
with a Pydantic `args_schema` so malformed arguments fail before your
function body runs, and return errors as a normal string observation ("no
results found for X") rather than raising — a raised exception typically
kills the agent loop instead of letting it try a different approach.

**Likely follow-up — "what's the actual security risk in a tool, beyond
bad inputs?"** Prompt injection through tool *output* — if
`search_internal_docs` returns text that was itself written by an
untrusted source (a scraped webpage, a user-submitted ticket), that text
re-enters the agent's context and can contain instructions the model may
follow ("ignore previous instructions and..."). Treat tool output as
untrusted the same way you'd treat user input, and don't give a tool more
capability (e.g. write access) than the task actually needs.

## 3. Memory Systems — "Buffer, summary, or entity memory — how do you choose, and what breaks with each?"

```python
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI

memory = ConversationSummaryBufferMemory(
    llm=ChatOpenAI(temperature=0),
    max_token_limit=1000,
    return_messages=True,
)
# Once the buffered history exceeds max_token_limit, the oldest turns are
# summarized into a running summary instead of being dropped outright.
```

**Answer:** **Buffer memory** keeps the last N turns verbatim — simplest
and cheapest, but once a turn falls out of the window it's genuinely
gone; a user referencing something from 20 turns ago gets a "who?"
response. **Summary memory** compresses old turns into a running summary
instead of dropping them, preserving long-range context at the cost of an
extra LLM call per compression and the summary itself being a lossy,
occasionally-wrong paraphrase of what was actually said. **Entity
memory** tracks specific named entities (a customer, a product, a case
number) across the conversation regardless of how far back they were
mentioned — good for personalization, but it only helps for facts that
get recognized as entities; it's not a substitute for general recall.

**Likely follow-up — "you're running multiple stateless API replicas
behind a load balancer — where does memory actually live?"** Not in
process memory — a user's next message can land on a different replica.
Externalize memory to Redis or a database keyed by `session_id`, load it
at the start of a turn and persist it at the end, the same way you'd
externalize any other per-session state in a horizontally scaled service.

| Memory type | Strength | Failure mode |
|---|---|---|
| Buffer | Simple, cheap, exact recall within the window | Hard cutoff — anything outside the window is just gone |
| Summary | Preserves long-range context indefinitely | Extra LLM call per compression; summary can misrepresent what was said |
| Entity | Tracks specific facts regardless of recency | Only helps for recognized entities, not general conversational recall |

## 4. Chain Composition with LCEL — "What does `prompt \| model \| parser` actually buy you over calling each piece by hand?"

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("Summarize this ticket in one sentence: {ticket}")
model = ChatOpenAI().with_fallbacks([ChatOpenAI(model="gpt-4o-mini")])
chain = prompt | model | StrOutputParser()

chain.invoke({"ticket": "..."})         # sync
await chain.ainvoke({"ticket": "..."})  # async
chain.stream({"ticket": "..."})         # token-by-token, for free
```

**Answer:** Every LCEL component implements the same `Runnable` interface,
so composing them with `|` gives you `invoke`/`batch`/`stream`/`ainvoke`
uniformly across the *entire composed chain* — you get streaming through a
three-step chain without writing any streaming plumbing yourself, because
each step already knows how to pass partial output to the next. That
uniformity is also what makes `.with_fallbacks([...])` and `.with_retry()`
work as one-line wrappers around any chain, not just a single model call,
and what makes `RunnableParallel` a clean way to fan out independent
branches (e.g. summarize *and* classify a ticket in one call) instead of
hand-writing `asyncio.gather` around each piece.

**Likely follow-up — "when would you skip LCEL and just write a plain
Python function?"** When the "chain" is really just business logic with
one LLM call in the middle — LCEL's value is composing multiple
`Runnable` steps with shared streaming/retry/fallback behavior; wrapping a
single call in the abstraction for its own sake adds a layer without
buying anything.

## 5. Guardrails, Evaluation, and Safety — "How do you stop an agent from hallucinating a tool call or leaking sensitive data before it ships?"

```python
system_prompt = """You are a support assistant. Only answer using information
returned by your tools -- never from general knowledge. If no tool result
supports an answer, say so explicitly. Never repeat back a credit card
number, SSN, or password even if one appears in tool output."""
# Strip any "system"-role content from user-supplied input before it's
# ever concatenated into this prompt.
```

**Answer:** Treat this as two separate problems. **At request time**:
pre/post filters for PII and disallowed intents, schema-constrained tool
inputs (so a malformed or out-of-policy call fails validation before it
executes), and prompt hardening — a system prompt that states the policy
explicitly, plus stripping any user-supplied text that looks like a
system instruction before it reaches the prompt. Prefer retrieval-grounded,
citation-bearing answers over free generation for anything where a wrong
answer has real consequences. **Before and after shipping a prompt/model
change**: offline evals against a golden set (does grounding, safety, and
tool-calling correctness regress?) as a CI gate, then online evals —
shadow or canary the change and compare win-rate against the current
baseline before a full rollout. [LangSmith](langchain-ecosystem.md#2-langsmith-how-do-you-debug-a-multi-step-langchain-agent-in-production-when-something-goes-wrong)
is the practical tool for building and running that golden-set regression
suite, since it can turn traced production runs directly into an
evaluation dataset.

**Likely follow-up — "what's the actual failure mode of skipping the
offline eval gate?"** A prompt tweak that fixes one reported issue
silently regresses three others that weren't being watched — without a
golden set run in CI on every change, you only find out from user
complaints, after it's already in production.

| Layer | Catches | Doesn't catch |
|---|---|---|
| Input/output filters | PII leakage, disallowed intents, malformed tool args | A confidently wrong but well-formed answer |
| Offline evals (golden set) | Regressions on known failure cases, tool-calling correctness | Novel failure modes not represented in the golden set |
| Online evals (shadow/canary) | Real-world regressions the golden set missed | Slow feedback — needs live traffic to surface an issue |

## 6. Multi-Agent Coordination within LangChain — "How do you route between specialized agents, handle fallback, and add a human-in-the-loop step, without pulling in a whole separate framework?"

```python
def route(state: dict) -> str:
    intent = classify_intent(state["input"])  # cheap classifier or a small LLM call
    return {"billing": "billing_agent", "technical": "tech_agent"}.get(intent, "general_agent")

def with_fallback(primary_agent, fallback_agent):
    def run(input_):
        try:
            return primary_agent.invoke(input_)
        except AgentExecutionError:
            return fallback_agent.invoke(input_)  # e.g. a smaller/cheaper model, or a canned response
    return run
```

**Answer:** At small scale this is just software: an **intent classifier
or router function** dispatches to the specialized agent (or chain) best
suited to the request — coordination doesn't require a "master agent"
reasoning about it in natural language; a plain function is faster and
more testable. **Fallback** wraps a primary agent call in a try/except
that falls back to a cheaper model, a simpler chain, or a canned response
on failure or timeout, rather than surfacing an error to the user.
**Human-in-the-loop** means pausing execution at a defined point — before
an irreversible action, or when the agent's own confidence is low — and
waiting for approval before continuing.

**Likely follow-up — "at what point do you reach for LangGraph instead of
hand-rolled routing and fallback functions?"** Once you need this to
actually *loop* (retry with a different tool and re-evaluate), need the
human-approval pause to survive a process restart rather than just block a
running function, or need more than two or three routing branches — at
that point you're reimplementing a state machine by hand, and
[LangGraph](langchain-ecosystem.md#1-langgraph-what-problem-does-this-solve-that-a-plain-langchain-chain-doesnt)
gives you that state machine, with persisted checkpoints, as a first-class
concept instead. For multi-agent systems built as a framework of agents
*conversing* with each other to reach a goal, rather than one LangChain
agent with routed tools/sub-chains, see
[Multi-Agent Systems](multi-agent-systems.md).

## 7. FastAPI Integration — Streaming an Agent's Response — "What's actually different about streaming an agent turn, versus streaming a plain LLM completion?"

For general FastAPI patterns — dependency injection, background tasks,
connection pooling, `asyncio.gather` for concurrent calls — see
[Dependency Injection & Background Tasks](fastapi-dependency-injection.md)
and [Performance & Production Patterns](fastapi-performance-patterns.md);
none of that is specific to serving an agent. What
*is* agent-specific is what you stream and how a stateful conversation
maps onto stateless HTTP/WebSocket connections.

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    agent = get_agent_for_session(session_id)
    try:
        while True:
            user_input = await websocket.receive_text()
            async for event in agent.astream_events({"input": user_input}, version="v2"):
                # Surfaces intermediate steps too: tool calls starting/ending,
                # not just the final answer's tokens.
                if event["event"] == "on_chat_model_stream":
                    await websocket.send_json({"type": "token", "data": event["data"]["chunk"].content})
                elif event["event"] == "on_tool_start":
                    await websocket.send_json({"type": "tool_start", "name": event["name"]})
    except WebSocketDisconnect:
        release_agent_for_session(session_id)
```

**Answer:** A plain completion is one stream of tokens. An agent turn can
include several LLM calls interleaved with tool calls — `astream_events`/
`astream_log` expose *that whole sequence* as a stream of typed events (a
tool starting, a tool finishing, each model token), so the client can show
"searching knowledge base…" while a tool runs and then stream the final
answer's tokens, instead of the connection going silent for however long
the tool call takes. That intermediate visibility is what makes an agent
feel responsive on a multi-second, multi-step turn.

**Likely follow-up — "why WebSocket instead of Server-Sent Events here, if
you're just streaming events in one direction?"** Either works for the
streaming-out half. WebSocket earns its keep when the client needs to send
something back *mid-turn* — most commonly a cancel/interrupt message while
the agent is still working, which a one-directional SSE stream can't carry
without a separate request. If the UI never needs to interrupt a running
turn, SSE is simpler and works through more corporate proxies than raw
WebSocket.

## 8. FastAPI Integration — Stateful Agents on Stateless Infrastructure — "The agent holds conversation memory — how do you reconcile that with a stateless, horizontally-scaled API?"

**Answer:** Don't keep the agent (or its memory) pinned to a process —
reconstruct it per request from state externalized in Redis/a database,
keyed by `session_id`, the same pattern as §3 above. A WebSocket
connection *is* naturally pinned to one server process for its lifetime,
but that's a connection-routing convenience, not a place to keep
authoritative state — if that instance restarts mid-conversation, a
reconnect needs to rebuild the same context from the external store, not
lose it.

**Likely follow-up — "what if reconstructing memory on every request is
too slow?"** Cache the deserialized memory object itself (not just the raw
conversation history) for the lifetime of an active WebSocket connection,
and only round-trip to Redis on connect/disconnect and after each turn —
you still get the durability of externalized state without paying the
deserialization cost on every single message.

## Code Samples

Runnable-pattern examples in `code_samples/chapter-22/` (the LangChain and
FastAPI classes in some of these are hand-rolled/mocked stand-ins rather
than the real libraries, so read them as reference architecture — the
patterns they demonstrate — not as drop-in production code):

- `langchain_agent.py` — `ReActAgent` and `PlanAndExecuteAgent`
  implementations, a custom `BaseTool` subclass, and `ConversationBuffer`/
  `EntityMemory` classes — the agent-type, tool, and memory patterns from
  §1–3 above.
- `fastapi_integration.py` — a real FastAPI app (`ConversationalAIService`,
  `SessionManager`, `WebSocketManager`, `RateLimiter`) wiring conversation
  endpoints, a streaming WebSocket chat endpoint, and Redis-backed session
  state — the §7–8 patterns above, plus a full rate limiter and auth
  dependency.
- `multi_agent_orchestration.py` — `WorkflowOrchestrator` coordinating
  multiple specialized `Agent` subclasses through a `Task`/`Workflow`
  dependency graph with retries — a fuller, workflow-engine-style version
  of the routing/fallback pattern in §6.
- `testing_examples.py` — integration tests (`LangChainAgentTests`,
  `FastAPIIntegrationTests`, `MultiAgentOrchestrationTests`) exercising the
  other modules together, including a mocked Redis pool and generated test
  fixtures — a template for testing an agent pipeline end-to-end rather
  than only unit-testing each piece.
- `production_deployment.py` — `HealthChecker`, `MetricsCollector`,
  `CircuitBreaker`, `LoadBalancer`, and `AutoScaler` implementations —
  general production-ops patterns (health checks, circuit breaking,
  autoscaling) applied around an agent service; not LangChain-specific,
  but a concrete reference for wiring these up around an agent deployment.
- `config.ini` — example configuration layout (DB pools, Redis, rate
  limits, circuit-breaker thresholds, feature flags) for a production
  deployment of the services above.

```bash
pip install langchain langchain-openai fastapi uvicorn pydantic redis pytest
```
