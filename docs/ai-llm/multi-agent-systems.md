---
title: "Multi-Agent Systems"
---

# Multi-Agent Systems

When and how to split a task across multiple cooperating LLM agents
instead of one — the coordination topologies that show up in practice
(sequential handoff, hierarchical/supervisor, peer-to-peer), their
trade-offs, and how to debug one that isn't working. For a concrete
framework built around one of these topologies, see
[Autogen: Multi-Agent Orchestration](autogen-orchestration.md).

## 1. "When does a task actually need multiple agents instead of one well-prompted agent with tools?"

**Answer:**

- Default to a single agent — it's simpler to build, cheaper to run,
  and easier to debug/test, since there's one prompt and one linear
  trace to reason about.
- Multi-agent decomposition earns its complexity when a task genuinely
  needs **role separation a single prompt can't hold at once**:
    - Distinct responsibilities that benefit from different system
      prompts or different tools.
    - An adversarial/critical relationship between roles (a writer and
      a reviewer, a planner and an executor).
- It also helps when a task is naturally **parallelizable** —
  independent sub-tasks that don't depend on each other's output can
  run as separate agents concurrently instead of one agent working
  through them serially.
- Warning sign you've reached for multi-agent too early: the "agents"
  are just sequential prompts with no real disagreement, parallelism,
  or specialization between them.
    - That's a single agent with several steps wearing an
      unnecessarily expensive costume.
    - Each additional agent is another LLM call (or several) added to
      every task, and non-determinism compounds with each additional
      model in the loop.

**Likely follow-up — "give a concrete example where a single agent
genuinely can't do the job as well."**

- Code generation with self-correction: one agent that both writes
  code and judges its own correctness tends to be overly agreeable
  with its own output — the same failure mode as asking someone to
  review their own work.
- Splitting into a coder and a separate critic (or an execution step
  that reports back real errors) gives an actual independent check,
  not just the same model re-reading its own answer in a different
  turn of the same context.
- This is also the core case
  [Autogen](autogen-orchestration.md) is built around.

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

**Answer:** Three topologies cover most real systems, trading
predictability against flexibility.

- **Sequential handoff** — a fixed pipeline: agent A's output becomes
  agent B's input, in a predetermined order (draft → edit →
  fact-check).
    - Most predictable and easiest to test — essentially a chain with
      LLM-powered steps.
    - Can't adapt if a later step discovers the earlier one needs
      redoing.
- **Hierarchical/supervisor** — one agent (or a scripted controller)
  decomposes the task, delegates sub-tasks to specialized worker
  agents, then synthesizes their results.
    - Scales better to complex tasks — the supervisor can adapt
      delegation based on intermediate results.
    - The supervisor becomes a single point of failure and a
      potential bottleneck.
- **Peer-to-peer** — agents converse directly with no fixed
  controller; the sequence of who acts next emerges from the
  conversation itself.
  ([Autogen's](autogen-orchestration.md) default model.)
    - Most flexible — can handle tasks whose shape isn't known
      upfront.
    - Least predictable and hardest to put hard bounds on.

**Likely follow-up — "which one would you default to, and why?"**

- Sequential handoff, unless the task specifically needs the
  adaptability the other two provide.
- It's the easiest to reason about, test, and put cost/latency bounds
  on, since the number of LLM calls is fixed and known in advance.
- Move to hierarchical when sub-tasks genuinely need dynamic
  delegation based on what's discovered mid-task (an unknown number of
  sub-questions, work that only becomes clear after an earlier step
  completes).
- Reach for peer-to-peer conversation only when the task benefits from
  genuine back-and-forth negotiation between roles and you're willing
  to pay the cost/predictability price — in practice a smaller slice
  of real tasks than it might initially seem, since most "agents need
  to negotiate" tasks can usually be reframed as a supervisor with a
  retry/refinement loop.

| Pros | Cons / Trade-offs |
|---|---|
| Sequential handoff: fixed, predictable call count — easiest to test and cost-bound | Can't adapt mid-task — a later step discovering an earlier mistake has no way to loop back |
| Hierarchical/supervisor: adapts delegation based on intermediate results, scales to complex tasks | Supervisor is a single point of failure/bottleneck — a bad plan misdirects every worker under it |
| Peer-to-peer: most flexible, handles tasks whose shape isn't known upfront | Least predictable and hardest to bound — needs explicit turn limits to avoid runaway conversation loops |

## 3. "A hierarchical multi-agent system's supervisor keeps producing bad delegation plans, or a peer-to-peer conversation won't converge — how do you debug and bound that?"

**Answer:**

- Treat it the same way you'd debug any multi-stage pipeline —
  isolate which stage is actually failing before trying to fix the
  whole system at once.
- For a bad supervisor plan:
    - Test the planning step in isolation against known-good
      decompositions, the same way you'd unit-test one component,
      rather than only ever observing it through the full system's
      end-to-end output.
    - A supervisor prompt that lacks clear criteria for how to split
      work is a prompting problem localized to one agent, not a
      multi-agent-architecture problem.
- For a peer-to-peer conversation that won't converge, the fix is
  usually structural rather than a better prompt:
    - An explicit maximum-turn limit.
    - A concrete termination condition each agent is instructed to
      check for and respect — not just "stop when you think you're
      done."
    - If convergence is still unreliable, reconsider whether the task
      actually needed peer-to-peer conversation at all versus a more
      constrained topology (question 2) that doesn't have an
      open-ended termination problem in the first place.

| Pros | Cons / Trade-offs |
|---|---|
| Isolating and testing one agent's step (e.g. the supervisor's plan) in isolation localizes the actual bug | Requires building that isolated test harness — more upfront work than testing the system only end-to-end |
| Explicit turn limits and termination conditions give a hard ceiling on runaway conversations | A hard turn limit can cut off a conversation that was genuinely still converging, not looping |
| Falling back to a more constrained topology removes the open-ended convergence problem entirely | Gives up the flexibility that made peer-to-peer attractive for the task in the first place |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable sequential-handoff or hierarchical-supervisor example added
under `code_samples/`. For an Autogen-specific example, see
[Autogen: Multi-Agent Orchestration](autogen-orchestration.md).
