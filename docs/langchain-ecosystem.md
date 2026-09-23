---
title: "LangChain Ecosystem: LangGraph, LangSmith, LangServe"
---

# LangChain Ecosystem: LangGraph, LangSmith, LangServe

The "Lang*" tools beyond core LangChain — orchestration, observability,
and deployment. For LangChain's own agent/chain/tool fundamentals, see
[Chapter 22: Building Conversational AI Agents with LangChain](chapter-22.md).

## 1. LangGraph — "What problem does this solve that a plain LangChain chain doesn't?"

```python
from langgraph.graph import StateGraph, END

def should_retry(state) -> str:
    return "retry" if state["needs_retry"] else "done"

graph = StateGraph(AgentState)
graph.add_node("generate", generate_step)
graph.add_node("validate", validate_step)
graph.add_conditional_edges("validate", should_retry, {"retry": "generate", "done": END})
```

**Answer:** A standard LangChain chain is fundamentally a straight-line
sequence — step A, then B, then C. Real agent workflows need loops
("keep retrying until validation passes"), branches ("if the tool call
failed, take a different path"), and checkpoints ("pause here for human
approval before continuing"). LangGraph models the workflow as an
explicit state graph — nodes are steps, edges (including *conditional*
edges) decide what runs next based on the current state — which a
linear chain has no clean way to express.

**Likely follow-up — "how does this relate to Autogen, which also does
multi-step agent orchestration?"** Different orchestration philosophy:
Autogen frames it as multiple agents *conversing* to reach a goal;
LangGraph frames it as an explicit state machine you design up front.
LangGraph's flow is more predictable and easier to test (you can reason
about every possible edge), at the cost of needing to actually design
the graph rather than letting behavior emerge from an agent
conversation.

| Pros | Cons / Trade-offs |
|---|---|
| Explicit graph is testable and debuggable — every transition is a defined edge | More upfront design work than a simple linear chain |
| Naturally supports retry loops, branching, and human-in-the-loop pauses | Overkill for a genuinely linear pipeline — adds structure you don't need |
| State persistence between steps is a first-class concept, not bolted on | Another abstraction layer on top of LangChain to learn |

## 2. LangSmith — "How do you debug a multi-step LangChain agent in production when something goes wrong?"

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "..."
# Every chain/agent run is now traced automatically -- no code changes
# to the chain itself needed.
```

**Answer:** Without tracing, a failed or wrong agent output is a black
box — you see the final result, not which of the 5 intermediate steps
(retrieval, tool call, prompt, generation) actually went wrong.
LangSmith captures every step of a run — the exact prompt sent, the
model's raw output, which tool was called with what arguments, latency
and token count per step — so debugging becomes "look at the trace and
find the step that produced the bad output" instead of guessing.

**Where this actually shows up:** the JD-level requirement "monitor
backend performance, debug production issues, improve observability"
applied specifically to LLM/agent systems — traditional APM tools
(Prometheus/Grafana, see [Chapter 10](chapter-10.md)) show you latency
and error rates, but not *why* an agent produced a specific wrong
answer. LangSmith fills that gap specifically for LLM call chains.

| Pros | Cons / Trade-offs |
|---|---|
| Full visibility into every intermediate step, not just the final output | Sends trace data to LangSmith's platform — a data-residency consideration for sensitive prompts |
| Minimal code changes to enable — mostly configuration | Adds a dependency on an external service for debugging your own system |
| Supports evaluation datasets — regression-test prompt/chain changes | Doesn't replace general infra observability (still need Chapter 10's RED metrics too) |

## 3. LangServe — "How do you turn a LangChain chain into a production API?"

```python
from fastapi import FastAPI
from langserve import add_routes

app = FastAPI()
add_routes(app, my_chain, path="/summarize")
# Automatically provides POST /summarize/invoke, /summarize/stream,
# /summarize/batch -- plus an interactive playground UI.
```

**Answer:** `add_routes` wraps any LangChain `Runnable` (a chain, an
agent) as a set of FastAPI endpoints — synchronous invoke, streaming,
and batch — without hand-writing the request/response handling,
streaming plumbing, or schema validation yourself. It's the deployment
counterpart to LangChain's chain-building: build the chain, then expose
it with a few lines instead of a full custom API layer.

**Likely follow-up — "when would you skip LangServe and just write the
FastAPI endpoint yourself?"** When the API needs behavior LangServe's
generated routes don't cleanly support — custom auth logic per
endpoint, non-standard response shaping, or integrating the chain as
just one piece of a larger endpoint that also does other work. LangServe
is fastest when the chain *is* the endpoint; once the endpoint needs to
do meaningfully more than invoke the chain, plain FastAPI (see
[FastAPI](fastapi.md)) gives more control.

| Pros | Cons / Trade-offs |
|---|---|
| Streaming, batch, and sync endpoints generated automatically from one chain | Generated routes are opinionated — less flexible than hand-written endpoints |
| Built-in playground UI for manual testing without a separate frontend | Best fit when the chain *is* the API — awkward when it's one piece of a bigger endpoint |
| Less boilerplate than wiring up streaming responses by hand | Yet another framework-specific convention layered on top of FastAPI |

## 4. LangCache — the named product behind "semantic caching for LLMs"

**Answer:** LangCache (from Redis) is a concrete, managed implementation
of the semantic caching pattern already covered in
[LLM Response Caching](llm-response-caching.md#2-explain-semantic-caching-how-is-it-different-from-exact-match-caching)
— it embeds incoming prompts, checks for a semantically similar cached
entry above a similarity threshold, and returns the cached response on
a hit, all as a managed service rather than something you build and
operate yourself on raw Redis. Worth knowing as the specific named
product a JD might reference, but the *pattern* underneath it (embed →
similarity search → cache hit/miss) is the transferable knowledge —
see the linked page for how that pattern actually works and its
precision/recall trade-offs.
