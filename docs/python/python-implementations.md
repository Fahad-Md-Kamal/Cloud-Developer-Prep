---
title: "Python Implementations: CPython, PyPy, GraalPy & Beyond"
---

# Python Implementations: CPython, PyPy, GraalPy & Beyond

Every other Python page on this site describes CPython specifically —
its [execution model](pythons-execution-model.md), its
[GIL](threading-and-the-gil.md), its
[memory model](python-internals-and-advanced-oop.md). This page is the
one level up: all of these are implementations of the *same* Python
language specification, and the real differences between them are what
they translate your code *to*, and what runtime or ecosystem they
actually run inside.

## 1. "Aren't these all just 'Python' — what's actually different between them?"

**Answer:**

- Every implementation here parses and runs the same Python language —
  the same syntax, the same semantics for classes, closures, exceptions.
- What differs is the **execution strategy underneath**: interpreting
  bytecode in C, compiling hot code to machine code at runtime, running
  on top of another managed runtime (the JVM, .NET's CLR), or a
  from-scratch minimal reimplementation sized for a microcontroller.
- The practical choice is driven by **what you actually need** — raw
  execution speed for long-running pure-Python code, interoperability
  with a specific other ecosystem (Java, .NET), or the ability to run at
  all on hardware with almost no memory — not by any difference in the
  language itself.

## 2. "What is CPython, and why is it the one everyone means by default?"

**Answer:**

- The reference implementation, written in C — the bytecode compiler,
  eval loop, and memory model already covered in
  [Python's Execution Model](pythons-execution-model.md) and
  [Python Internals & Advanced OOP](python-internals-and-advanced-oop.md).
- It's the implementation the [GIL](threading-and-the-gil.md) actually
  belongs to, and the one virtually every C-extension package (NumPy,
  pandas's C internals) is written against first — which is exactly why
  it remains the default: the surrounding ecosystem assumes it.

## 3. "What is PyPy, and how does its JIT actually make Python code faster than CPython?"

**Answer:**

- PyPy adds a **tracing JIT (Just-In-Time) compiler**: it watches code
  as it actually runs, identifies loops that execute many times (the
  "hot" paths), and compiles *those specific paths* directly to machine
  code — bypassing the per-instruction eval-loop overhead
  [CPython always pays](pythons-execution-model.md#the-eval-loop)
  entirely, for exactly the code that's actually worth optimizing.
- This is a direct, practical application of the same insight behind
  profiling before optimizing elsewhere on this site — most of a
  program's total runtime is spent in a small fraction of its code, so
  compiling only that fraction gets most of the possible speedup without
  needing to compile everything.
- **Where it wins**: long-running, CPU-bound pure-Python services —
  often a 4-10x speedup once the JIT has warmed up.
- **Where it doesn't help, or actively costs**: short-lived scripts (the
  JIT needs time observing the code run before it compiles anything, so
  a script that exits quickly never gets to the payoff), and
  C-extension-heavy code — PyPy's C-API compatibility layer (`cpyext`)
  lets many C extensions run, but with real overhead and real gaps, and
  numeric code already delegating to a C extension like NumPy is already
  running at C speed under CPython, so there's nothing left for a JIT to
  meaningfully speed up.

## 4. "What is GraalPy, and why would someone reach for it over PyPy for a performance-sensitive use case?"

**Answer:**

- GraalPy also JIT-compiles Python, but its actual value proposition is
  different from PyPy's: it runs on **GraalVM**, Oracle's polyglot
  virtual machine, which means Python code can directly interoperate
  with Java, JavaScript, or Ruby objects **in the same process**, not
  just run pure Python faster in isolation.
- The deciding use case: embedding Python inside an existing
  JVM-based system (calling Python from Java, or vice versa, without
  a network call or serialization boundary between them) — a problem
  PyPy doesn't address at all, since PyPy has no polyglot interop story.
- If the goal is purely "make my existing pure-Python service run
  faster," PyPy is the more mature, narrower-purpose tool; if the goal
  is "run Python and Java/JS code together in one process," GraalPy is
  solving a problem PyPy simply isn't built for.

## 5. "Jython and IronPython — why did these stall, and are they still relevant today?"

**Answer:**

- **Jython** runs Python on the **JVM**, compiling Python to JVM
  bytecode — giving direct access to Java libraries and classes from
  Python code with no bridge or serialization layer.
- **IronPython** does the equivalent for **.NET's CLR** — direct access
  to .NET libraries from Python.
- Both stalled for years without full Python 3 support, at exactly the
  time the broader Python ecosystem (packages, tooling, other projects)
  moved decisively to Python 3 — a practical disqualifier serious enough
  that both are largely legacy choices today, relevant mainly to
  maintaining a codebase already built on them rather than a reasonable
  choice for new work.

## 6. "MicroPython and CircuitPython — why does Python need a completely separate implementation for embedded hardware?"

**Answer:**

- CPython's interpreter and standard library assume an operating
  system, a filesystem, and megabytes of RAM available — a
  microcontroller with kilobytes of RAM simply cannot run any of that,
  regardless of how it's configured.
- **MicroPython** is a from-scratch, minimal reimplementation — its own
  compact bytecode compiler and VM, a drastically reduced standard
  library, and direct access to hardware registers (GPIO pins, timers)
  — specifically sized to fit and run on resource-constrained chips.
- **CircuitPython** is Adafruit's fork of MicroPython, not a separate
  implementation built from scratch — tuned specifically for
  beginner/educational ergonomics (the board appears as a USB drive you
  edit files on directly, with automatic reload) and broad driver
  support for Adafruit's own hardware, trading some of MicroPython's
  flexibility for a friendlier day-one experience.

## 7. "Can you actually AOT-compile a Python project — which tool, and how do you pick fast?"

**The one thing to know first:** AOT compilation is genuinely harder
for Python than for C/Rust, because Python defers almost everything —
types, even what a name refers to — to runtime. Every tool below works
around that the same general way: either you add type hints, it falls
back to the normal interpreter for anything too dynamic, or it only
supports a narrower, less dynamic slice of the language.

**Pick by what you actually want:**

- Compile the whole project as-is, no rewrites → **Nuitka**
- Speed up one hot module, willing to add type hints → **Cython** or
  **mypyc**
- Speed up numerical/array code specifically → **Numba**
- Ship one file so users don't need Python installed → **PyInstaller**
  / **cx_Freeze** — not a speedup, see below
- Fine with a new, Python-*like* language for real native speed →
  **Codon**

| Tool | What it needs from you | What you actually get | Best for |
|---|---|---|---|
| **Nuitka** | Nothing — compiles existing `.py` files directly | A real compiled executable/extension; falls back to the normal interpreter for anything too dynamic to resolve | Speeding up or distributing an existing project with no rewrites |
| **Cython** | Rewriting hot code in a Python superset (`.pyx`), with optional type declarations | Speed scales with how much typing you add — near-C speed when fully typed | Hand-optimizing one specific hot module or library |
| **mypyc** | Type hints (the ones mypy already checks) | A compiled C extension built from already-typed `.py` code | A project that's already fully type-hinted |
| **Numba** | A `@jit` decorator on a function (usually NumPy-based numeric code) | JIT by default; a real AOT mode (`numba.pycc`) exists for a standalone compiled version | Numerical/array-heavy functions specifically |
| **Codon** | Accepting it isn't full Python — some dynamic features aren't supported | Full native compiled speed via LLVM | New, performance-critical code — not an existing dynamic codebase |
| **PyInstaller / cx_Freeze** | Nothing | One distributable file — but the code still runs as interpreted bytecode, exactly as fast as before | Shipping to someone without Python installed — not a performance tool at all |

**The one thing worth remembering if you only remember one thing:**
"I made a `.exe`" and "I made my code faster" are two completely
different problems. PyInstaller solves the first; everything else in
this table solves the second.

## Summary: Implementation → Runtime → Why You'd Use It

| Implementation | Runs on | Why you'd use it | Key trade-off |
|---|---|---|---|
| CPython | Native (C) | The default — what the ecosystem targets | No JIT; the GIL limits thread-level parallelism |
| PyPy | Native (JIT, RPython) | Long-running, CPU-bound pure-Python code, 4-10x faster | Slow warm-up; weaker C-extension compatibility |
| GraalPy | GraalVM | Interop with Java/JS/Ruby in one process | Narrower ecosystem/tooling than CPython |
| Jython | JVM | Direct Java library access from Python | Stalled on Python 3 support — largely legacy |
| IronPython | .NET CLR | Direct .NET library access from Python | Same Python 3 lag as Jython |
| MicroPython | Microcontrollers | Running Python at all on kilobytes of RAM | Drastically reduced standard library |
| CircuitPython | Microcontrollers (Adafruit boards) | Beginner-friendly embedded Python | A fork of MicroPython, not a separate implementation |

---

## Code Samples

No dedicated code samples for this page.
