---
title: "Agentic AI Fundamentals"
---

# Agentic AI Fundamentals

What "agentic AI" actually means, why you'd split work across multiple
agents, and how to actually build one with real API/tooling access —
before diving into coordination topologies in
[Multi-Agent Systems](multi-agent-systems.md).

## 1. "What is agentic AI, in plain terms?"

**Answer:**

- A single LLM call is one-shot — prompt in, response out, done.
- An **agent** wraps the LLM in a loop that can act and observe, not
  just respond.
- The loop: **Reason** (decide what to do next) → **Act** (call a
  tool) → **Observe** (see the result) → repeat until the goal is done.
- "Agentic" means the LLM decides how many steps to take and in what
  order — you don't hard-code the sequence yourself.

**Core building blocks:**

- **LLM** — the reasoning engine deciding what happens next.
- **Tools** — what the agent can actually do (run code, query a DB,
  call an API, edit a file).
- **Memory/context** — what it remembers as it works through the task.
- **Orchestrator** — the code driving the loop and enforcing stop
  conditions, so it doesn't run forever or spiral on a bad decision.

**Likely follow-up — "give a concrete example."**

- A coding agent: read a file → decide what's wrong → run a build →
  observe the error → fix it → repeat until the build passes.

**Likely follow-up — "is the model actually *deciding* to call a tool, or
just predicting text?"**

- Just predicting text — there's no separate decision-making step
  bolted onto the model. Tool-calling uses the exact same
  next-token-prediction mechanism as generating a sentence; the model
  has simply been fine-tuned to recognize when a structured,
  schema-matching output is the most probable thing to generate next,
  given the current context and the tools it's been told are available.
- That's worth knowing because it explains real failure modes: a vague
  or overlapping tool description confuses the pattern match the same
  way an ambiguous prompt confuses any other generation, and nothing
  inside generation itself checks "does this tool actually exist"
  before those tokens come out — that check happens in the calling
  code, after the fact.
- See [How LLMs Actually Work §6](how-llms-actually-work.md#6-when-an-agent-decides-to-call-a-tool-is-it-actually-reasoning-about-that-decision)
  for the full mechanism.

## 2. "Why split into multiple agents instead of one?"

**Answer — reasons to split:**

- One agent juggling everything means mixed context and one bloated
  system prompt.
- Splitting gives each agent a narrow job — a focused prompt, a
  focused tool set.
- Independent sub-tasks can run in parallel instead of serially.
- A separate reviewer/critic agent gives real independent checking —
  a single agent reviewing its own output tends to rubber-stamp itself.

**Common coordination patterns, at a glance:**

- **Orchestrator/manager** — one lead agent delegates to workers,
  merges results. Easiest to debug.
- **Pipeline** — sequential handoff, A's output feeds B feeds C. Good
  for ordered stages.
- **Conversational/peer** — agents talk to each other until they
  converge. Most flexible, hardest to bound.

**The main risk:**

- Debugging is harder than a single agent — if agent B misreads agent
  A's output, you get a confidently wrong result with no obvious
  failure point.
- Default to orchestrator/pipeline unless the task genuinely needs
  open-ended negotiation between agents.

For the full breakdown of these patterns, their trade-offs, and how to
debug a multi-agent loop that won't converge, see
[Multi-Agent Systems](multi-agent-systems.md).

## 3. "I have a Claude subscription through my organization — how do I actually build multiple agents?"

**Answer — first, check which access you actually have:**

- A **claude.ai seat** (Pro/Team/Enterprise) is chat-UI access only.
- It does **not** let you write code that calls Claude programmatically.
- **API access** (console.anthropic.com, billed by token usage) is
  separate — that's what you need to actually build agents in code.
- Ask your org whether you have both, or just the chat seat — this is
  a common gap.

**Once you have API access, three practical paths:**

- **Claude Code** (an agent orchestration tool from Anthropic)
    - Already has multi-agent orchestration built in.
    - Spawns subagents with their own context and tools.
    - Runs scripted, deterministic multi-agent pipelines.
    - Needs zero extra setup if the goal is "get agentic workflows
      running," not "build a custom product."
    - Its own tool/resource access to external systems runs on
      [Model Context Protocol](model-context-protocol.md) — worth
      knowing as the concrete, real-world example of that standard.
- **Claude Agent SDK** (Python/TypeScript)
    - A library, not a framework — gives you the agent loop (tool use,
      context management) as building blocks.
    - You write the tools and orchestration logic yourself.
    - Full control, no extra abstractions to learn — a natural fit for
      a Python background.
- **Frameworks on top of the API**
    - LangChain/LangGraph, Autogen, CrewAI.
    - Add ready-made agent/tool/memory abstractions and coordination
      primitives.
    - Cost: another layer of framework-specific convention to learn.
    - See [LangChain Agents](langchain-agents.md) and
      [Autogen: Multi-Agent Orchestration](autogen-orchestration.md)
      for the concrete APIs.

| Pros | Cons / Trade-offs |
|---|---|
| Claude Code: zero setup, already running | Less control — tied to its own orchestration model |
| Agent SDK: full control, minimal abstraction | You build the tools, memory, and orchestration yourself |
| Frameworks (LangChain/Autogen/CrewAI): fastest to a working prototype | Another abstraction layer, framework-specific conventions to learn |

---

## Code Samples

No dedicated code samples yet for this section.
