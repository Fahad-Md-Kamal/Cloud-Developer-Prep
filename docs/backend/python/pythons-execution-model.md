---
title: "Python's Execution Model: From Source to a Running Call Stack"
---

# Python's Execution Model: From Source to a Running Call Stack

Knowing Python's syntax is the tool-usage version of knowing Python.
This page is the mechanism underneath it: what actually happens between
typing `python3 script.py` and your first line executing, what a
function call actually *is*, and why a variable reference resolves to
the value it does — the fundamentals that let you reason about a bug
`print()`-debugging alone never will.

## From `python3 script.py` to a Running Process

- The shell asks the OS to create a new process (`fork`, then `exec` on
  Linux/macOS) and loads the `python3` binary into it — this is no
  different from launching any other program.
- The CPython interpreter then initializes its own internal state
  before your code runs at all: built-in types, the `sys` module, the
  import system, and the handful of modules every Python program
  implicitly depends on.
- Only after that initialization finishes does the interpreter start
  actually processing your script.

## Source to Bytecode

Python doesn't execute your `.py` file's text directly — it compiles it
first, every time, into an intermediate form the interpreter actually
runs:

1. **Tokenize** the source into a stream of tokens (keywords,
   identifiers, operators).
2. Parse those tokens into an **AST** (Abstract Syntax Tree) — a
   structural representation of the code's grammar.
3. **Compile** the AST into **bytecode** — a sequence of simple,
   stack-based instructions (`LOAD_FAST`, `CALL`, `BINARY_OP`, …) that
   the interpreter's eval loop actually executes.

``` python
import dis
def add(a, b):
    return a + b
dis.dis(add)
```

- For an imported module, this compiled bytecode is cached on disk as a
  `.pyc` file under `__pycache__/`, so the next run skips straight to
  bytecode if the source hasn't changed since — the thing a stale
  `__pycache__` directory occasionally breaks.
- The script you run directly (`python3 script.py`) is compiled fresh
  every time and never cached this way — only *imported* modules get
  the `.pyc` cache.

## The Eval Loop

At the center of CPython is one large loop, written in C, that does
nothing but: fetch the next bytecode instruction, dispatch on what kind
of instruction it is, execute it, and move to the next one. Every single
thing a running Python program does — every function call, every
attribute lookup, every arithmetic operation — is this loop executing
one more bytecode instruction.

!!! success "This is the entire reason the GIL exists"

    Since this loop only ever executes one bytecode instruction at a
    time, only one thread can be inside it at once — which is exactly
    what the
    [GIL](concurrency-and-asyncio.md#1-explain-the-gil-then-explain-why-threads-still-help-io-bound-code-despite-it)
    is: the lock that enforces "only one thread runs Python bytecode at
    a time." Understanding the eval loop is what makes the GIL stop
    being an arbitrary rule and start being an obvious consequence of
    how the interpreter is built.

## Function Calls and the Call Stack: Frames

Calling a function doesn't just "jump" somewhere — it creates a brand
new **frame object**: a chunk of memory holding that call's local
variables, the bytecode being executed, and exactly where to resume the
*caller* once this call returns. Frames stack on top of each other, one
per active call — this stack of frames **is** the call stack.

```python
x = "global"
def outer():
    y = "enclosing"
    def inner():
        print(x, y)
    inner()
outer()
```

## Variable Scoping: LEGB

Looking up a name doesn't search "everywhere" — it checks a fixed order
of scopes and stops at the first match: **L**ocal (the current frame),
**E**nclosing (an outer function's frame, for a closure), **G**lobal
(the module's own namespace), **B**uilt-in (`len`, `print`, and the
rest). This is exactly why `inner()` above can read `x` and `y` without
either being passed in as an argument — each lookup just walks down the
stack of frames already sitting there.

<svg viewBox="0 0 820 520" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of the call stack building up as outer and inner are called, then variable lookups walking the stack via LEGB" style="width:100%;height:auto;max-width:820px;display:block;margin:0 auto;font-family:inherit;">
<rect x="40" y="380" width="740" height="100" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="64" y="412" font-size="15" font-weight="600" fill="#2b313b">Module / Global frame</text>
<text x="64" y="434" font-size="14" fill="#434d5c">x = "global"</text>
<rect x="40" y="260" width="740" height="100" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.07;0.1;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="64" y="292" font-size="15" font-weight="600" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.07;0.1;1" dur="16s" repeatCount="indefinite"></animate>outer() frame — Enclosing</text>
<text x="64" y="314" font-size="14" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.07;0.1;1" dur="16s" repeatCount="indefinite"></animate>y = "enclosing"</text>
<rect x="40" y="140" width="740" height="100" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.17;0.2;1" dur="16s" repeatCount="indefinite"></animate></rect>
<text x="64" y="172" font-size="15" font-weight="600" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.17;0.2;1" dur="16s" repeatCount="indefinite"></animate>inner() frame — Local</text>
<text x="64" y="194" font-size="14" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.17;0.2;1" dur="16s" repeatCount="indefinite"></animate>print(x, y) runs here</text>
<circle r="10" fill="#d9822b" cx="500"><animate attributeName="cy" values="190;190;190;340;340;430;430;190;190;190;340;430;430;190" keyTimes="0;0.2;0.37;0.44;0.5;0.56;0.63;0.7;0.72;0.9;0.95;0.98;0.99;1" dur="16s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;0;1;1;1;1;1;0;0;0;1;1;1;0" keyTimes="0;0.2;0.22;0.44;0.46;0.56;0.58;0.68;0.7;0.9;0.92;0.98;0.99;1" dur="16s" repeatCount="indefinite"></animate></circle>
<text x="410" y="480" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.18;0.21;1" dur="16s" repeatCount="indefinite"></animate>outer() is called, then inner() — each call pushes a new frame.</text>
<text x="410" y="480" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.37;0.4;0.63;0.66;1" dur="16s" repeatCount="indefinite"></animate>Looking up y: not in Local (inner) → found in Enclosing (outer). Stop there.</text>
<text x="410" y="480" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.68;0.71;0.95;0.98;1" dur="16s" repeatCount="indefinite"></animate>Looking up x: not Local, not Enclosing → found in Global (module). Stop there.</text>
</svg>

!!! danger "A name not found anywhere in LEGB is a `NameError`, not a crash elsewhere"

    If a lookup walks Local → Enclosing → Global → Built-in and still
    finds nothing, Python raises `NameError` at the exact line doing the
    lookup — it never silently treats a missing name as `None` or `0`.
    This is also why a variable only assigned *inside* an `if` block
    that didn't run is a `NameError` if read afterward, not some
    default value — assignment is what creates the name in that frame's
    local namespace in the first place; there's nothing there until a
    `=` actually runs.

## Threads: From `threading.Thread` to a Real OS Thread

`threading.Thread` is a thin wrapper — starting one makes CPython ask
the OS to create a genuine native thread (`pthread_create` on
Linux/macOS), scheduled by the OS exactly like a thread in any other
language. Python doesn't invent its own thread concept underneath;
[the GIL](concurrency-and-asyncio.md#1-explain-the-gil-then-explain-why-threads-still-help-io-bound-code-despite-it)
is the one thing CPython bolts on top of otherwise-ordinary OS threads —
every thread is real and OS-scheduled, but only one at a time is ever
allowed inside the eval loop above, executing Python bytecode.

For what that one restriction actually means in practice — when threads
still help despite it, and how AsyncIO/multiprocessing fit around it —
see
[Concurrency & AsyncIO](concurrency-and-asyncio.md).
