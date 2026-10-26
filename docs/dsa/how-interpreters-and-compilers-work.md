---
title: "How Interpreters & Compilers Actually Work"
---

# How Interpreters & Compilers Actually Work

[Python's Execution Model](../backend/python/pythons-execution-model.md)
and
[Python Implementations](../backend/python/python-implementations.md)
cover this mechanism for CPython and its alternatives specifically.
This page is the general, language-agnostic version underneath all of
it — the actual pipeline every language's toolchain runs in some form,
whether it compiles ahead of time, interprets on the fly, or does both
at once.

## 1. "What actually happens between source code and a running program — what are the real stages?"

**Answer:**

- **Lexical analysis (lexing)** — the raw source text gets split into
  **tokens**: keywords, identifiers, operators, literals. `x = a + 1`
  becomes a flat stream like `[NAME x] [EQUALS] [NAME a] [PLUS]
  [NUMBER 1]` — no structure yet, just meaningful chunks.
- **Parsing** — those tokens get assembled into an **Abstract Syntax
  Tree (AST)**, a tree structure that actually captures the program's
  grammar: an assignment node, with a name on one side and an addition
  expression (itself a node with two children) on the other. This is
  the first point where "structure" exists at all — tokens alone don't
  know that `+` binds its two neighbors together.
- **Semantic analysis** — checking the AST actually makes sense beyond
  pure grammar: is `a` an already-declared name, do the types involved
  support `+`, is this assignment even valid in this scope. A program
  can be grammatically perfect and still fail here.
- **Code generation** — translating the validated AST into some lower-level
  form: real machine code, bytecode, or (rarely, and slowly) just
  executing the AST directly node by node.
- Every language's toolchain runs some version of this pipeline — what
  actually differs between languages isn't whether these stages happen,
  it's **what the final stage produces**, and **when**.

## 2. "What's the actual difference between a compiler and an interpreter?"

**Answer:**

- A **compiler** translates the *entire* program into another form —
  usually machine code — **before** execution ever begins, as a wholly
  separate step. Once compiled, running the program means running that
  translated output directly; the compiler itself isn't involved anymore.
- An **interpreter** executes the program's instructions **directly, as
  it goes**, without first producing a separate, persistent translated
  artifact the way a compiler does.
- The common misconception worth correcting: this isn't a clean binary
  split in practice. Pure interpretation — walking the AST node by node,
  re-deriving meaning every single time a line executes — is genuinely
  slow and rare. Most real "interpreted" languages (Python, Java, C#)
  actually **compile to bytecode first**, then interpret *that* — a
  hybrid, not pure interpretation, covered next.

## 3. "What's bytecode, and why do most 'interpreted' languages compile to it instead of interpreting source text directly?"

**Answer:**

- Bytecode is a simplified, lower-level instruction set — not real
  machine code the CPU can run directly, but far simpler and more
  uniform than raw source text or a tree of AST nodes.
- Compiling to bytecode turns the expensive lexing/parsing/AST-building
  work into a **one-time cost** — done once (and often cached, the way
  CPython caches `.pyc` files) — rather than something repeated on
  every single execution.
- A bytecode interpreter is then just a tight loop: fetch the next
  bytecode instruction, dispatch on what it is, execute it, repeat —
  dramatically faster than re-parsing text or re-walking a tree node by
  node each time, because the hard structural work already happened
  once, upfront.
- This is exactly the mechanism behind
  [CPython's own eval loop](../backend/python/pythons-execution-model.md#the-eval-loop) —
  not a Python-specific trick, but this page's general pattern, applied
  to one concrete language.

## How a JIT Compiler Actually Changes Behavior Mid-Run

<svg viewBox="0 0 900 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of JIT compilation: a program starts out interpreting bytecode, the runtime detects a loop running repeatedly, compiles that loop to real machine code, and switches to running the compiled version for the rest of execution" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="400" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<rect x="350" y="30" width="200" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="450" y="63" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Program Starts</text>
<rect x="350" y="150" width="200" height="60" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="3"><animate attributeName="stroke" values="#2f6fb3;#2f6fb3;#9aa5b3;#9aa5b3" keyTimes="0;0.4;0.44;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="450" y="176" font-size="14" font-weight="600" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.4;0.44;1" dur="16s" repeatCount="indefinite"></animate>Interpreting Bytecode</text>
<text x="450" y="176" font-size="14" font-weight="600" text-anchor="middle" fill="#8a98ab"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.4;0.44;1" dur="16s" repeatCount="indefinite"></animate>Interpreting Bytecode</text>
<text x="450" y="194" font-size="12" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.4;0.44;1" dur="16s" repeatCount="indefinite"></animate>fetch, dispatch, execute — one instruction at a time</text>
<text x="450" y="194" font-size="12" text-anchor="middle" fill="#8a98ab"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.4;0.44;1" dur="16s" repeatCount="indefinite"></animate>(this loop no longer runs here)</text>
<rect x="640" y="150" width="200" height="60" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.32;0.36;0.6;0.64;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="740" y="176" font-size="13" font-weight="600" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.32;0.36;0.6;0.64;1" dur="16s" repeatCount="indefinite"></animate>This loop ran 10,000 times</text>
<text x="740" y="194" font-size="12" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.32;0.36;0.6;0.64;1" dur="16s" repeatCount="indefinite"></animate>— compiling it now</text>
<rect x="350" y="290" width="200" height="60" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="450" y="316" font-size="14" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="16s" repeatCount="indefinite"></animate>Running Compiled Machine Code</text>
<text x="450" y="334" font-size="12" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="16s" repeatCount="indefinite"></animate>no interpreter overhead left for this path</text>
<line x1="450" y1="85" x2="450" y2="150" stroke="#9aa5b3" stroke-width="2"></line>
<line x1="550" y1="180" x2="640" y2="180" stroke="#9aa5b3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.32;0.36;0.6;0.64;1" dur="16s" repeatCount="indefinite"></animate></line>
<line x1="700" y1="210" x2="480" y2="290" stroke="#1f9d6b" stroke-width="2" stroke-dasharray="5,5"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="16s" repeatCount="indefinite"></animate></line>
<text x="450" y="390" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.3;0.34;1" dur="16s" repeatCount="indefinite"></animate>Execution starts out interpreting bytecode, same as any bytecode-based language.</text>
<text x="450" y="390" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.34;0.38;0.58;0.62;1" dur="16s" repeatCount="indefinite"></animate>The runtime notices this specific loop is "hot" and compiles it to real machine code.</text>
<text x="450" y="390" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.68;0.72;1" dur="16s" repeatCount="indefinite"></animate>From here on, THIS loop runs as native machine code — no more interpreter overhead for it.</text>
</svg>

## 4. "What's JIT compilation, and how is it genuinely different from both ahead-of-time compiling and plain interpreting?"

**Answer:**

- **Ahead-of-time (AOT) compiling** (C, Rust, Go) translates the entire
  program to machine code **before it ever runs** — all the translation
  cost is paid once, upfront, at build time; the resulting binary then
  runs directly on the CPU with zero further translation needed.
- **Pure/bytecode interpretation** pays a smaller upfront cost but a
  repeated, ongoing per-instruction cost during every single execution
  — the eval loop never stops doing its fetch-dispatch-execute work.
- **JIT (Just-In-Time) compilation** is the middle path: start by
  interpreting bytecode like normal, but **watch which code actually
  runs frequently** — a loop executed thousands of times — and compile
  *just that part* to real machine code **during execution**, then
  switch to running the compiled version for the rest of the program's
  life. [PyPy](../backend/python/python-implementations.md#3-what-is-pypy-and-how-does-its-jit-actually-make-python-code-faster-than-cpython),
  the JVM, and JavaScript's V8 engine are all real, widely-used examples
  of exactly this pattern.
- The payoff: near-AOT speed for the specific code that actually
  matters (the hot loops), without paying AOT's full upfront
  compilation cost for code that only ever runs once and would never
  earn back that investment.

## Comparing the Four Execution Strategies

| Approach | When translation happens | Startup cost | Peak execution speed | Biggest advantage | Biggest disadvantage | Real examples |
|---|---|---|---|---|---|---|
| **AOT compilation** | Entirely before execution, as a separate build step | None at run time — already compiled | Fastest possible — runs as native machine code from the first instruction | No translation overhead ever, at run time | Full translation cost paid upfront, even for code that runs once or never | C, Rust, Go |
| **Pure/AST interpretation** | Never fully — re-derived on every single run | Lowest — no build step at all | Slowest — re-parses or re-walks the tree structure every execution | Nothing to build or cache — just run the source directly | Repeats the expensive structural work (lexing/parsing) every single time | Simple scripting tools; rare in production language runtimes |
| **Bytecode interpretation** | Once, before first run (often cached to disk) | Low — one-time compile, frequently cached | Moderate — no re-parsing, but still one bytecode instruction at a time, forever | Parsing cost paid once, not per run; no separate build step for the user | Still pays per-instruction interpreter overhead for the entire run, with no path to native speed | CPython (no JIT at all) |
| **JIT compilation** | Starts interpreting bytecode, compiles hot code to machine code mid-run | Low to start; real warm-up delay before hot paths speed up | Near-AOT for hot loops once compiled; interpreted speed everywhere else | Gets AOT-level speed exactly where it's earned, without paying it where it isn't | Warm-up cost, more complex runtime, and short-lived programs never benefit | PyPy, the JVM (HotSpot), V8 (JavaScript) |

**The one-sentence way to hold all four in your head:** the real
spectrum is *when* you pay the translation cost (never, once upfront,
once per run, or only for the parts that earn it back) — every other
difference in this table falls out of that one choice.

## The Same Comparison, Drawn Out

<svg viewBox="0 0 900 520" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Static diagram comparing AOT compilation, pure AST interpretation, bytecode interpretation, and JIT compilation as horizontal timelines, showing when translation work happens relative to execution for each approach" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="520" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<text x="165" y="22" font-size="13" text-anchor="middle" fill="#5b6472">Earlier — a separate build step</text>
<text x="560" y="22" font-size="13" text-anchor="middle" fill="#5b6472">Now — running `python file.py` / `./program`</text>
<line x1="270" y1="36" x2="270" y2="452" stroke="#9aa5b3" stroke-width="2" stroke-dasharray="5,5"></line>
<text x="40" y="58" font-size="14" font-weight="600" fill="#2b313b">AOT</text>
<rect x="80" y="66" width="180" height="50" rx="6" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="170" y="96" font-size="12" text-anchor="middle" fill="#7a5c14">Compile to machine code</text>
<rect x="270" y="66" width="590" height="50" rx="6" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"></rect>
<text x="565" y="96" font-size="12" text-anchor="middle" fill="#0f6b45">Run — native machine code, full speed from instruction one</text>
<text x="40" y="148" font-size="14" font-weight="600" fill="#2b313b">Pure / AST</text>
<rect x="270" y="156" width="59" height="50" fill="#eef1f5" stroke="#434d5c" stroke-width="1"></rect>
<rect x="329" y="156" width="59" height="50" fill="#fdf3e3" stroke="#b5831f" stroke-width="1"></rect>
<rect x="388" y="156" width="59" height="50" fill="#eef1f5" stroke="#434d5c" stroke-width="1"></rect>
<rect x="447" y="156" width="59" height="50" fill="#fdf3e3" stroke="#b5831f" stroke-width="1"></rect>
<rect x="506" y="156" width="59" height="50" fill="#eef1f5" stroke="#434d5c" stroke-width="1"></rect>
<rect x="565" y="156" width="59" height="50" fill="#fdf3e3" stroke="#b5831f" stroke-width="1"></rect>
<rect x="624" y="156" width="59" height="50" fill="#eef1f5" stroke="#434d5c" stroke-width="1"></rect>
<rect x="683" y="156" width="59" height="50" fill="#fdf3e3" stroke="#b5831f" stroke-width="1"></rect>
<rect x="742" y="156" width="59" height="50" fill="#eef1f5" stroke="#434d5c" stroke-width="1"></rect>
<rect x="801" y="156" width="59" height="50" fill="#fdf3e3" stroke="#b5831f" stroke-width="1"></rect>
<text x="565" y="224" font-size="11" text-anchor="middle" fill="#5b6472">translating and executing the same lines, over and over, every single run</text>
<text x="40" y="248" font-size="14" font-weight="600" fill="#2b313b">Bytecode</text>
<rect x="270" y="256" width="50" height="50" rx="6" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<rect x="320" y="256" width="540" height="50" rx="6" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<text x="590" y="286" font-size="12" text-anchor="middle" fill="#1d4a78">Interpreting bytecode — one instruction at a time, for the whole run</text>
<text x="40" y="348" font-size="14" font-weight="600" fill="#2b313b">JIT</text>
<rect x="270" y="356" width="50" height="50" rx="6" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<rect x="320" y="356" width="180" height="50" rx="6" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<line x1="500" y1="350" x2="500" y2="412" stroke="#1f9d6b" stroke-width="2" stroke-dasharray="3,3"></line>
<text x="500" y="340" font-size="11" text-anchor="middle" fill="#0f6b45">hot loop compiled here</text>
<rect x="500" y="356" width="360" height="50" rx="6" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"></rect>
<text x="680" y="386" font-size="12" text-anchor="middle" fill="#0f6b45">Running compiled native code for the hot path</text>
<rect x="60" y="468" width="14" height="14" fill="#fdf3e3" stroke="#b5831f"></rect>
<text x="80" y="479" font-size="11" fill="#2b313b">Translating / compiling</text>
<rect x="280" y="468" width="14" height="14" fill="#eef1f5" stroke="#434d5c"></rect>
<text x="300" y="479" font-size="11" fill="#2b313b">Interpreting raw source/AST (slowest)</text>
<rect x="60" y="494" width="14" height="14" fill="#eaf2fb" stroke="#2f6fb3"></rect>
<text x="80" y="505" font-size="11" fill="#2b313b">Interpreting bytecode</text>
<rect x="280" y="494" width="14" height="14" fill="#e8f7f0" stroke="#1f9d6b"></rect>
<text x="300" y="505" font-size="11" fill="#2b313b">Running native machine code (fastest)</text>
</svg>

The divider is the detail every explanation tends to skip: AOT's
translation happens in a genuinely separate, earlier command (`gcc`,
`cargo build`) — by the time you actually run the program, there's
nothing left to translate at all. The other three all do their
translation work **inside the same run** you're waiting on, which is
exactly why Python startup time includes compiling to bytecode, not
just executing it.

## 5. "Once you actually have real machine code, what does the CPU do to 'execute' it?"

**Answer:**

- Machine code is a sequence of binary-encoded instructions in the
  CPU's own instruction set (x86-64, ARM) — this is the literal bottom
  of the entire stack every stage above has been translating toward.
- The CPU runs a continuous **fetch-decode-execute cycle**: fetch the
  next instruction from memory (at the address the program counter
  currently points to), decode which operation it actually represents,
  execute it (an arithmetic operation in the ALU, a memory load/store, a
  jump that changes the program counter itself), then advance to the
  next instruction — repeated billions of times per second.
- Everything described earlier in this page — lexing, parsing, bytecode,
  JIT compilation — exists entirely to eventually produce instructions
  this one simple, relentless cycle can actually run. There's no deeper
  mechanism underneath this step; it's where the translation chain ends.

## 6. "Where does linking fit in, for a compiled language?"

**Answer:**

- A compiler typically processes one source file at a time, producing
  an **object file** per file — not yet a complete, runnable program,
  since references to functions or variables defined in a *different*
  file can't be resolved while compiling each file in isolation.
- The **linker** combines those object files (and pulls in any needed
  library code) into one final executable, resolving those
  cross-file references — the actual step between "compiled code
  exists" and "a runnable program exists," worth naming explicitly since
  it's a distinct stage most simplified explanations skip straight past.

---

## Code Samples

No dedicated code samples for this page.
