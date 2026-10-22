---
title: "Model Context Protocol (MCP)"
---

# Model Context Protocol (MCP)

MCP is one of the fastest-adopted standards to come out of the current
wave of AI tooling — Claude Code itself is an MCP client. Before the
practical "how do you build one" material, this page covers what
problem MCP actually solves and why it needed to be a protocol at all,
rather than just another library.

## 1. "What problem does MCP actually solve that tool-calling didn't already?"

**Answer:**

- [Tool-calling itself](how-llms-actually-work.md#6-when-an-agent-decides-to-call-a-tool-is-it-actually-reasoning-about-that-decision)
  — a model generating structured output that an application recognizes
  and executes — already existed before MCP, and MCP doesn't change that
  mechanism at all.
- What it actually solves is an **integration** problem: without a
  shared standard, every AI application that wants to read a file, query
  a database, or call an internal API has to write bespoke integration
  code for each tool or data source — and every tool/data source that
  wants to be usable by AI applications has to write bespoke
  integrations for each client. That's an N×M problem: N applications
  times M tools/data sources, each pair needing its own glue code.
- MCP standardizes the interface in the middle, the same shape as other
  successful standards: any MCP-compatible client can talk to any
  MCP-compatible server with zero bespoke integration code, the same way
  a USB-C port lets any compliant device talk to any compliant cable
  without a custom adapter per device.
- Concretely, this means a tool/data-source author writes **one** MCP
  server, and it instantly becomes usable by every MCP-compatible AI
  application (Claude Code, Claude Desktop, and others) — not a
  per-application integration.

## 2. "What's the actual client-server architecture, mechanically?"

**Answer:**

- An **MCP host** is the AI application itself (Claude Code, for
  example) — it runs one or more **MCP clients**, each of which connects
  to a separate **MCP server**.
- A server exposes some combination of three things:
    - **Tools** — callable functions the model can invoke (the same
      structured-output tool-calling mechanism as always, just exposed
      through this standard interface).
    - **Resources** — readable data the host can pull into context (a
      file's contents, a query result) without that data needing to be a
      callable function.
    - **Prompts** — reusable prompt templates the server provides, so
      common task framings don't need to be reinvented per client.
- Communication happens over **JSON-RPC 2.0** — a lightweight,
  long-established remote-procedure-call format — carried either over
  **local stdio** (the server runs as a subprocess, talking over
  stdin/stdout, the common case for a tool that runs on the same
  machine) or over **HTTP** for a server that needs to be reachable
  remotely.
- None of this changes what the model itself is doing — it's still just
  generating text, including the occasional structured tool-call-shaped
  output. MCP standardizes *how the host discovers and exposes* what's
  available to the model in the first place, not the generation
  mechanism underneath.

## 3. "How is an MCP tool actually different from a function the model calls directly?"

**Answer:**

- Mechanically, it isn't — once the host has made the tool available to
  the model, the model calls it exactly the same way it would call any
  other tool: by generating structured output matching the tool's
  declared schema, which the host recognizes and executes.
- The difference is entirely upstream of that moment: a hand-written
  tool function is wired into one specific application's codebase,
  while an MCP tool is exposed by a standalone server process that any
  MCP-compatible host can connect to and discover without custom code.
- This is also why building an MCP server doesn't require a different
  mental model of tool design than the advice already covered in
  [LangChain Agents §2](langchain-agents.md#2-tool-integration-and-custom-tool-creation-how-do-you-build-a-custom-tool-and-what-actually-makes-an-agent-pick-the-right-one)
  — narrow, single-purpose tools with precise descriptions matter
  exactly as much here, since the model is still picking a tool by
  matching its description against context, regardless of which
  protocol exposed that tool to it.

## 4. "When would you actually build an MCP server instead of just writing a custom tool function?"

**Answer:**

- Writing a plain function wired directly into your application is
  simpler and fine when the integration is genuinely one-off — a tool
  only one specific agent in one specific codebase will ever call.
- Build an MCP server when the same capability — a company's internal
  API, a specific database, a file system, a third-party service — needs
  to be reusable across multiple different AI applications or clients
  without re-implementing the same integration logic for each one.
- The same reasoning that favors a shared library over copy-pasted code
  across projects applies here: a one-off integration doesn't earn the
  extra process/protocol overhead, but a genuinely reused one earns it
  back many times over.

| Pros | Cons / Trade-offs |
|---|---|
| Write one server, usable by any MCP-compatible client — no per-application integration code | Real overhead (a separate process, a protocol layer) for a tool that will only ever be used by one application |
| Standard interface means a new AI application can use existing MCP servers with zero extra integration work | Still a relatively new, fast-moving standard — expect rougher edges than a decade-old protocol |
| Resources and prompts, not just tools, get the same standardized exposure | Tool descriptions still need the same careful, narrow design as any other tool-calling setup — the protocol doesn't fix a vague description |

---

## Code Samples

No dedicated code samples for this page — building and running an MCP
server is a setup/configuration task rather than a standalone runnable
snippet.
