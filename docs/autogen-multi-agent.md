---
title: "Autogen: Multi-Agent Orchestration"
---

# Autogen: Multi-Agent Orchestration

Microsoft's multi-agent framework — what problem it solves that a
single LLM call doesn't, and how it differs from LangChain (which this
site already covers separately).

## 1. "What problem does Autogen solve that a single LLM call doesn't?"

```python
from autogen import ConversableAgent

assistant = ConversableAgent(
    "assistant",
    system_message="You write Python code to solve tasks.",
    llm_config={"model": "gpt-4o"},
)
user_proxy = ConversableAgent(
    "user_proxy",
    human_input_mode="NEVER",
    code_execution_config={"work_dir": "coding"},
)

user_proxy.initiate_chat(assistant, message="Plot y = x^2 from -10 to 10")
```

**Answer:** A single LLM call is one-shot — prompt in, completion out,
no way for the model to check its own work, run code, or iterate based
on a result. Autogen structures a task as a **conversation between
multiple agents**, each with a role (a planner, a coder, a critic, a
code-executor) — the coder writes code, the executor runs it and
reports back errors, the coder fixes it, and so on, without a human
manually relaying each step.

## 2. "How is Autogen different from LangChain?"

**Answer:** LangChain is primarily a toolkit for *chaining* steps —
retrieval, prompt templates, tool calls — in a largely predetermined
sequence you design. Autogen is built around **agents conversing with
each other** to reach a goal, where the actual sequence of who does
what emerges from the conversation rather than being fully scripted
upfront. They're not mutually exclusive — a LangChain-built tool or
retrieval chain can be one capability an Autogen agent calls during its
part of the conversation.

**Likely follow-up — "when would you reach for Autogen specifically?"**
Tasks that genuinely benefit from role separation and iterative
back-and-forth — code generation with self-correction, a
researcher-and-critic pair refining an answer, multi-step tasks where
one agent's output needs another agent's review before proceeding. For
a single well-defined pipeline (retrieve → prompt → generate), a
simpler LangChain chain or a direct API call is usually the better,
more predictable choice — multi-agent conversation adds real
non-determinism and cost (more LLM calls per task) that isn't worth
paying for a task that doesn't need it.

## 3. "What are the practical risks of a multi-agent conversation loop?"

**Answer:** Cost and runaway loops — each turn in the agent
conversation is its own LLM call, so a task that would be one API call
directly can become five or ten calls through a multi-agent exchange,
and a poorly-bounded conversation (agents that keep "discussing" without
converging) can loop far longer than expected. Production use needs an
explicit max-turn limit, a termination condition the agents actually
respect, and cost/latency budgets treated as first-class constraints,
not an afterthought.

| Pros | Cons / Trade-offs |
|---|---|
| Handles tasks needing iteration/self-correction a single call can't | Meaningfully more expensive — many LLM calls per task instead of one |
| Role separation (planner/coder/critic) mirrors how a human team would tackle it | Less predictable/deterministic than a scripted chain — harder to test |
| Built-in code execution loop is genuinely useful for coding tasks | Needs explicit turn limits and termination conditions to avoid runaway loops |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Autogen multi-agent example added under `code_samples/`.
