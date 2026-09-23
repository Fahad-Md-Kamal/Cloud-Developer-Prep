---
title: "Autogen: Multi-Agent Orchestration"
---

# Autogen: Multi-Agent Orchestration

[Microsoft Autogen](https://microsoft.github.io/autogen/) — a concrete
framework for structuring a task as a conversation between multiple
agents, and one real implementation of the peer-to-peer topology
covered in
[Multi-Agent Systems](multi-agent-systems.md#2-what-are-the-common-ways-to-structure-how-multiple-agents-talk-to-each-other-and-how-do-you-pick-one).

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

**Answer:**

- A single LLM call is one-shot — prompt in, completion out, no way
  for the model to check its own work, run code, or iterate based on a
  result.
- Autogen structures a task as a **conversation between multiple
  agents**, each with a role (a planner, a coder, a critic, a
  code-executor).
- Example: the coder writes code, the executor runs it and reports
  back errors, the coder fixes it, and so on — without a human
  manually relaying each step.

## 2. "How is Autogen different from LangChain?"

**Answer:**

- LangChain is primarily a toolkit for *chaining* steps — retrieval,
  prompt templates, tool calls — in a largely predetermined sequence
  you design.
- Autogen is built around **agents conversing with each other** to
  reach a goal, where the actual sequence of who does what emerges
  from the conversation rather than being fully scripted upfront.
- They're not mutually exclusive — a LangChain-built tool or retrieval
  chain can be one capability an Autogen agent calls during its part
  of the conversation.

**Likely follow-up — "when would you reach for Autogen specifically?"**

- Tasks that genuinely benefit from role separation and iterative
  back-and-forth: code generation with self-correction, a
  researcher-and-critic pair refining an answer, multi-step tasks
  where one agent's output needs another agent's review before
  proceeding.
- For a single well-defined pipeline (retrieve → prompt → generate), a
  simpler LangChain chain or a direct API call is usually the better,
  more predictable choice.
- Multi-agent conversation adds real non-determinism and cost (more
  LLM calls per task) that isn't worth paying for a task that doesn't
  need it.

## 3. "What are the practical risks of a multi-agent conversation loop?"

**Answer:**

- **Cost** — each turn in the agent conversation is its own LLM call,
  so a task that would be one API call directly can become five or ten
  calls through a multi-agent exchange.
- **Runaway loops** — a poorly-bounded conversation (agents that keep
  "discussing" without converging) can loop far longer than expected.
- Production use needs:
    - An explicit max-turn limit.
    - A termination condition the agents actually respect.
    - Cost/latency budgets treated as first-class constraints, not an
      afterthought.
- This is the concrete version of the convergence problem raised for
  peer-to-peer topologies generally in
  [Multi-Agent Systems](multi-agent-systems.md#3-a-hierarchical-multi-agent-systems-supervisor-keeps-producing-bad-delegation-plans-or-a-peer-to-peer-conversation-wont-converge-how-do-you-debug-and-bound-that).

| Pros | Cons / Trade-offs |
|---|---|
| Handles tasks needing iteration/self-correction a single call can't | Meaningfully more expensive — many LLM calls per task instead of one |
| Role separation (planner/coder/critic) mirrors how a human team would tackle it | Less predictable/deterministic than a scripted chain — harder to test |
| Built-in code execution loop is genuinely useful for coding tasks | Needs explicit turn limits and termination conditions to avoid runaway loops |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Autogen multi-agent example added under `code_samples/`.
