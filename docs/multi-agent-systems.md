---
title: "Multi-Agent Systems"
---

# Multi-Agent Systems

When and how to split a task across multiple cooperating LLM agents
instead of one — the coordination topologies that show up in practice
(sequential handoff, hierarchical/supervisor, peer-to-peer) and their
trade-offs — with Autogen covered as one concrete framework for
implementing this, not the whole scope of the page.

## 1. "When does a task actually need multiple agents instead of one well-prompted agent with tools?"

**Answer:** Default to a single agent — it's simpler to build, cheaper
to run, and far easier to debug and test, since there's one prompt and
one linear trace to reason about. Multi-agent decomposition earns its
complexity when a task genuinely needs **role separation that a single
prompt can't hold at once**: distinct responsibilities that benefit from
different system prompts, different tools, or an adversarial/critical
relationship between them (a writer and a reviewer, a planner and an
executor). It also helps when a task is naturally **parallelizable** —
independent sub-tasks that don't depend on each other's output can run
as separate agents concurrently rather than one agent working through
them serially. The warning sign that you've reached for multi-agent too
early: if the "agents" are just sequential prompts with no real
disagreement, parallelism, or specialization between them, that's a
single agent with several steps wearing an unnecessarily expensive
costume — each additional agent is another LLM call (or several) added
to every task, and non-determinism compounds with each additional model
in the loop.

**Likely follow-up — "give a concrete example where a single agent
genuinely can't do the job as well."** A code-generation task with
self-correction: one agent that both writes code and judges its own
correctness tends to be overly agreeable with its own output — the same
failure mode as asking someone to review their own work. Splitting into
a coder and a separate critic (or an execution step that reports back
real errors) gives an actual independent check, not just the same model
re-reading its own answer in a different turn of the same context. This
is also the core case Autogen (section 4) is built around.

| Pros | Cons / Trade-offs |
|---|---|
| Role specialization gives each agent a focused prompt/tool set instead of one overloaded prompt | Every additional agent is more LLM calls, more cost, and more latency per task |
| Independent sub-tasks can run in parallel across agents instead of serially in one | More non-determinism — the emergent interaction between agents is harder to test than one scripted flow |
| A separate critic/reviewer agent gives real independent checking a self-reviewing single agent can't | Easy to over-decompose a task that a single well-prompted agent would have handled fine |

## 2. "What are the common ways to structure how multiple agents talk to each other, and how do you pick one?"

```python
# Sequential handoff -- output of one agent becomes input to the next
draft = writer_agent.run(topic)
edited = editor_agent.run(draft)
final = fact_checker_agent.run(edited)

# Hierarchical/supervisor -- one agent plans and delegates, workers report back
plan = supervisor_agent.plan(task)
results = [worker_agents[step.role].run(step) for step in plan]
summary = supervisor_agent.synthesize(results)

# Peer-to-peer -- agents converse directly, no fixed controller
conversation = group_chat.run([agent_a, agent_b, agent_c], task)
```

**Answer:** Three topologies cover most real systems, and they trade off
predictability against flexibility. **Sequential handoff** is a fixed
pipeline — agent A's output becomes agent B's input, in a predetermined
order (draft → edit → fact-check). It's the most predictable and
easiest to test, essentially a chain with LLM-powered steps, but it
can't adapt if a later step discovers the earlier one needs redoing.
**Hierarchical/supervisor** has one agent (or a scripted controller)
that decomposes the task and delegates sub-tasks to specialized worker
agents, then synthesizes their results — this scales better to complex
tasks because the supervisor can adapt delegation based on intermediate
results, at the cost of the supervisor becoming a single point of
failure and a potential bottleneck. **Peer-to-peer** (Autogen's default
model, section 4) has agents converse directly with no fixed controller
— the sequence of who acts next emerges from the conversation itself.
This is the most flexible and can handle tasks whose shape isn't known
upfront, but it's also the least predictable and the hardest to put
hard bounds on.

**Likely follow-up — "which one would you default to, and why?"**
Sequential handoff, unless the task specifically needs the adaptability
the other two provide — it's the easiest to reason about, test, and put
cost/latency bounds on, since the number of LLM calls is fixed and known
in advance. Move to hierarchical when sub-tasks genuinely need dynamic
delegation based on what's discovered mid-task (an unknown number of
sub-questions, work that only becomes clear after an earlier step
completes). Reach for peer-to-peer conversation only when the task
benefits from genuine back-and-forth negotiation between roles and
you're willing to pay the cost/predictability price for it — which in
practice is a smaller slice of real tasks than it might initially seem,
since most "agents need to negotiate" tasks can usually be reframed as a
supervisor with a retry/refinement loop.

| Pros | Cons / Trade-offs |
|---|---|
| Sequential handoff: fixed, predictable call count — easiest to test and cost-bound | Can't adapt mid-task — a later step discovering an earlier mistake has no way to loop back |
| Hierarchical/supervisor: adapts delegation based on intermediate results, scales to complex tasks | Supervisor is a single point of failure/bottleneck — a bad plan misdirects every worker under it |
| Peer-to-peer: most flexible, handles tasks whose shape isn't known upfront | Least predictable and hardest to bound — needs explicit turn limits to avoid runaway conversation loops |

## 3. "A hierarchical multi-agent system's supervisor keeps producing bad delegation plans, or a peer-to-peer conversation won't converge — how do you debug and bound that?"

**Answer:** Treat it the same way you'd debug any multi-stage pipeline —
isolate which stage is actually failing before trying to fix the whole
system at once. For a bad supervisor plan, test the planning step in
isolation against known-good decompositions the same way you'd unit-test
one component, rather than only ever observing it through the full
system's end-to-end output; a supervisor prompt that lacks clear
criteria for how to split work is a prompting problem localized to one
agent, not a multi-agent-architecture problem. For a peer-to-peer
conversation that won't converge, the fix is usually structural rather
than a better prompt: an explicit maximum-turn limit, a concrete
termination condition each agent is instructed to check for and respect
(not just "stop when you think you're done"), and — if convergence is
still unreliable — reconsidering whether the task actually needed
peer-to-peer conversation at all versus a more constrained topology
(question 2) that doesn't have an open-ended termination problem in the
first place.

| Pros | Cons / Trade-offs |
|---|---|
| Isolating and testing one agent's step (e.g. the supervisor's plan) in isolation localizes the actual bug | Requires building that isolated test harness — more upfront work than testing the system only end-to-end |
| Explicit turn limits and termination conditions give a hard ceiling on runaway conversations | A hard turn limit can cut off a conversation that was genuinely still converging, not looping |
| Falling back to a more constrained topology removes the open-ended convergence problem entirely | Gives up the flexibility that made peer-to-peer attractive for the task in the first place |

## 4. Autogen: a concrete framework for peer-to-peer multi-agent conversation

The rest of this page covers [Autogen](https://microsoft.github.io/autogen/)
specifically — Microsoft's framework for structuring a task as a
conversation between multiple agents, one concrete implementation of the
peer-to-peer topology from question 2.

### 4.1 "What problem does Autogen solve that a single LLM call doesn't?"

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

### 4.2 "How is Autogen different from LangChain?"

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

### 4.3 "What are the practical risks of a multi-agent conversation loop?"

**Answer:** Cost and runaway loops — each turn in the agent
conversation is its own LLM call, so a task that would be one API call
directly can become five or ten calls through a multi-agent exchange,
and a poorly-bounded conversation (agents that keep "discussing" without
converging) can loop far longer than expected. Production use needs an
explicit max-turn limit, a termination condition the agents actually
respect, and cost/latency budgets treated as first-class constraints,
not an afterthought — this is the concrete version of the convergence
problem raised for peer-to-peer topologies generally in question 3.

| Pros | Cons / Trade-offs |
|---|---|
| Handles tasks needing iteration/self-correction a single call can't | Meaningfully more expensive — many LLM calls per task instead of one |
| Role separation (planner/coder/critic) mirrors how a human team would tackle it | Less predictable/deterministic than a scripted chain — harder to test |
| Built-in code execution loop is genuinely useful for coding tasks | Needs explicit turn limits and termination conditions to avoid runaway loops |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable Autogen multi-agent example, or a sequential-handoff/hierarchical-supervisor
example for the framework-agnostic patterns above, added under
`code_samples/`.
