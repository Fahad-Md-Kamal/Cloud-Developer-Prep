---
title: "Computer Architecture & How a CPU Actually Processes Instructions"
---

# Computer Architecture & How a CPU Actually Processes Instructions

[How Interpreters & Compilers Actually Work](how-interpreters-and-compilers-work.md)
ends exactly where this page begins — machine code exists, and a
fetch-decode-execute cycle runs it. This page goes one level deeper:
what's actually inside a CPU, how it executes billions of instructions
per second instead of one at a time, and why that speed comes with real,
measurable trade-offs when it guesses wrong.

## 1. "What's the basic architecture almost every modern computer is built on?"

**Answer:**

- The **von Neumann model**: one memory storing both instructions and
  data together, a CPU, and I/O, all connected by a shared bus.
- Storing instructions and data in the *same* memory, addressed the
  *same* way, is what makes a stored-program computer flexible — a
  program can even treat its own instructions as data (self-modifying
  code, a compiler writing out an executable) — but it creates the
  **von Neumann bottleneck**: instructions and data compete for the same
  single channel to memory, which can limit throughput no matter how
  fast the CPU itself is.
- **Harvard architecture** is the alternative — genuinely separate
  memory and pathways for instructions vs. data, avoiding that
  contention entirely. It's less flexible for general-purpose computing,
  which is exactly why it's common specifically in
  [microcontrollers](../python/python-implementations.md#6-micropython-and-circuitpython-why-does-python-need-a-completely-separate-implementation-for-embedded-hardware) —
  a fixed, known program doesn't need the flexibility von Neumann's
  shared memory buys you, and avoiding the bottleneck matters more on
  constrained hardware.

## 2. "What's actually inside a CPU — what do registers, the ALU, and the control unit each do?"

**Answer:**

- **Registers** — a small number of extremely fast storage slots
  directly inside the CPU itself, holding the data currently being
  worked on. Even faster than
  [L1 cache](big-o-and-memory-hardware.md#the-memory-hierarchy-why-ram-isnt-one-speed) —
  the fastest, smallest, most expensive tier of the entire memory
  hierarchy, one step closer to the CPU than any cache level.
- **The ALU (Arithmetic Logic Unit)** — the component that actually
  performs arithmetic (add, subtract, multiply) and logic (AND, OR,
  comparisons) operations on the values currently sitting in registers.
- **The control unit** — decodes each instruction and generates the
  signals that orchestrate everything else: which registers the ALU
  should read from, what operation to perform, where the result should
  go. Nothing "decides" what to do on its own — the control unit is
  what turns a binary instruction into an actual sequence of real
  actions elsewhere in the chip.

## 3. "Walk through the fetch-decode-execute cycle in full detail — what actually happens for one instruction?"

**Answer:**

- **Fetch** — the **program counter (PC)** holds the memory address of
  the next instruction; that instruction is read from memory (or cache)
  into the **instruction register**, and the PC advances to point at
  whatever comes next.
- **Decode** — the control unit interprets the fetched instruction's
  binary encoding: which operation this is, and which registers or
  memory locations it actually operates on.
- **Execute** — the ALU (or another functional unit) actually performs
  the operation — an addition, a comparison, a memory address
  calculation.
- **Write-back** — the result gets written somewhere it can actually be
  used afterward — back into a register, or out to memory.
- This is the same cycle already named briefly in
  [How Interpreters & Compilers Actually Work §5](how-interpreters-and-compilers-work.md#5-once-you-actually-have-real-machine-code-what-does-the-cpu-do-to-execute-it) —
  this is the full version, the actual four distinct steps that single
  sentence was standing in for.

## How Pipelining Overlaps Multiple Instructions at Once

<svg viewBox="0 0 900 380" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of instruction pipelining: three instructions overlap across the fetch, decode, execute, and write-back stages simultaneously, so a new instruction completes every cycle once the pipeline is full, instead of waiting for each instruction to finish all four stages before the next one starts" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="380" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<text x="450" y="24" font-size="13" text-anchor="middle" fill="#5b6472">Four pipeline stages, running left to right over time</text>
<text x="40" y="70" font-size="13" font-weight="600" fill="#2b313b">Fetch</text>
<text x="40" y="140" font-size="13" font-weight="600" fill="#2b313b">Decode</text>
<text x="40" y="210" font-size="13" font-weight="600" fill="#2b313b">Execute</text>
<text x="40" y="280" font-size="13" font-weight="600" fill="#2b313b">Write-back</text>
<rect x="130" y="50" width="140" height="40" rx="6" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.02;0.22;0.26;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="200" y="75" font-size="13" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.02;0.22;0.26;1" dur="14s" repeatCount="indefinite"></animate>Instruction 1</text>
<rect x="290" y="120" width="140" height="40" rx="6" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.22;0.24;0.42;0.46;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="360" y="145" font-size="13" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.22;0.24;0.42;0.46;1" dur="14s" repeatCount="indefinite"></animate>Instruction 1</text>
<rect x="450" y="190" width="140" height="40" rx="6" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.42;0.44;0.62;0.66;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="520" y="215" font-size="13" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.42;0.44;0.62;0.66;1" dur="14s" repeatCount="indefinite"></animate>Instruction 1</text>
<rect x="610" y="260" width="140" height="40" rx="6" fill="#eef1f5" stroke="#434d5c" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.64;0.82;0.86;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="680" y="285" font-size="13" text-anchor="middle" fill="#2b313b"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.64;0.82;0.86;1" dur="14s" repeatCount="indefinite"></animate>Instruction 1</text>
<rect x="290" y="50" width="140" height="40" rx="6" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.22;0.24;0.42;0.46;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="360" y="75" font-size="13" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.22;0.24;0.42;0.46;1" dur="14s" repeatCount="indefinite"></animate>Instruction 2</text>
<rect x="450" y="120" width="140" height="40" rx="6" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.42;0.44;0.62;0.66;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="520" y="145" font-size="13" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.42;0.44;0.62;0.66;1" dur="14s" repeatCount="indefinite"></animate>Instruction 2</text>
<rect x="610" y="190" width="140" height="40" rx="6" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.64;0.82;0.86;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="680" y="215" font-size="13" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.64;0.82;0.86;1" dur="14s" repeatCount="indefinite"></animate>Instruction 2</text>
<rect x="450" y="50" width="140" height="40" rx="6" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.42;0.44;0.62;0.66;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="520" y="75" font-size="13" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.42;0.44;0.62;0.66;1" dur="14s" repeatCount="indefinite"></animate>Instruction 3</text>
<rect x="610" y="120" width="140" height="40" rx="6" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.64;0.82;0.86;1" dur="14s" repeatCount="indefinite"></animate></rect>
<text x="680" y="145" font-size="13" text-anchor="middle" fill="#1d4a78"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.62;0.64;0.82;0.86;1" dur="14s" repeatCount="indefinite"></animate>Instruction 3</text>
<text x="450" y="340" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.4;0.44;1" dur="14s" repeatCount="indefinite"></animate>While instruction 1 decodes, instruction 2 is already being fetched — the stages overlap.</text>
<text x="450" y="340" font-size="16" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.44;0.48;0.8;0.84;1" dur="14s" repeatCount="indefinite"></animate>Once the pipeline is full, a new instruction completes every single cycle.</text>
</svg>

## 4. "If one instruction takes four cycles, how do CPUs run billions of instructions per second?"

**Answer:**

- **Pipelining**: overlap the four stages across *multiple*
  instructions at once — while instruction 1 is in the execute stage,
  instruction 2 is being decoded, and instruction 3 is already being
  fetched, all in the same cycle, each in a different stage.
- This is a **throughput vs. latency** distinction worth holding onto
  precisely: any single instruction still takes four cycles start to
  finish — its individual latency doesn't shrink — but once the
  pipeline is full, a *new* instruction completes every single cycle,
  not every four.
- **Hazards** are what break this clean overlap: a **structural
  hazard** (two instructions needing the same hardware resource at
  once), a **data hazard** (an instruction needing a result the
  previous one hasn't finished producing yet), and a **control
  hazard** — the CPU doesn't know what to fetch next the moment it hits
  a conditional branch, since the branch's outcome isn't known until it
  actually executes, several stages later. Control hazards are common
  and costly enough to need their own dedicated mechanism, covered next.

## 5. "What's branch prediction and speculative execution, and why does a wrong guess cost real performance?"

**Answer:**

- The control hazard from §4 is a real, recurring problem — code is
  full of conditional branches (`if`/`else`, loop conditions), and a
  pipelined CPU that simply stalled and waited for every branch to
  resolve would give up most of pipelining's benefit.
- **Branch prediction** is the fix: the CPU guesses, based on the
  branch's own history and common patterns, which way it's likely to go
  — and **speculatively** starts fetching and executing instructions
  down that guessed path *before* the branch actually resolves.
- If the guess is right, there was no stall at all — pure win. If it's
  wrong, everything speculatively executed down the wrong path has to
  be **flushed** (discarded) and the pipeline restarted from the
  correct path — a real, measurable **misprediction penalty**, often
  costing more cycles than the CPU would have lost just waiting in the
  first place.
- This exact mechanism is also what the real-world **Spectre and
  Meltdown** vulnerabilities (disclosed 2018) exploited: speculative
  execution can briefly access data it ultimately has no right to use,
  and even though the *speculative result itself* gets discarded on a
  misprediction, it can leave measurable side effects (cache timing)
  an attacker can observe — a genuine case where a pure performance
  optimization turned out to have a real security cost.

## 6. "CISC vs. RISC — what's actually different, and does the distinction still matter today?"

**Answer:**

- **CISC (Complex Instruction Set Computing)**, the x86 philosophy —
  fewer, denser instructions, each capable of doing more work in one
  instruction (a single instruction that loads from memory, does
  arithmetic, and stores the result). Historically motivated by
  memory being expensive — packing more logic into fewer instructions
  meant smaller programs.
- **RISC (Reduced Instruction Set Computing)**, the ARM philosophy —
  many simple, uniform instructions, each doing one small thing,
  deliberately designed to be easy and predictable to pipeline
  efficiently.
- **The modern nuance worth naming directly**: real x86 chips today
  internally decode CISC instructions into simpler, RISC-like
  **micro-ops** before actually executing them — the external
  instruction set still differs, but the internal execution reality has
  converged significantly between the two philosophies.
- **Why this is still a live, practical question**: ARM's rise — Apple
  Silicon, mobile devices, and now AWS Graviton in cloud server
  instances — against x86's continued desktop/traditional-server
  dominance is a genuinely current architecture decision, not just
  historical trivia.

| | CISC (x86) | RISC (ARM) |
|---|---|---|
| Instructions | Fewer, more complex, denser | More, simpler, uniform |
| Pipelining | Harder — instructions vary a lot in what they do | Easier — uniform instructions are predictable to overlap |
| Historical motivation | Memory was expensive — pack more per instruction | Simplicity enables faster, more efficient hardware |
| Today | Internally decodes to RISC-like micro-ops anyway | Still externally simple; now scaling into servers (Graviton) |

## 7. "How does a physical multi-core chip relate to the threading/GIL story already covered for Python?"

**Answer:**

- Multiple cores on one chip are **genuinely separate, independent
  execution units** — each running its own complete fetch-decode-execute
  cycle (with its own registers, often its own L1/L2 cache) fully in
  parallel with the others, not sharing the pipeline the way
  hyperthreading on one core does.
- This is the actual hardware mechanism underneath
  [why multiprocessing achieves real parallel speedup for CPU-bound
  Python work while GIL-constrained threading can't](../python/threading-and-the-gil.md) —
  separate OS processes can genuinely be scheduled onto separate
  physical cores, each executing independently; threads inside one
  GIL-holding process are all competing for the same single core's
  bytecode-execution turn, regardless of how many physical cores the
  machine actually has.
- [Multiprocessing in Practice](../python/multiprocessing-in-practice.md)
  covers the practical Python-side mechanics of actually using this —
  this page is the hardware fact that makes that approach work at all.

## 8. "Why isn't a higher clock speed (GHz) simply 'faster,' on its own?"

**Answer:**

- Clock speed measures cycles per second — but how much actual useful
  work happens per cycle varies enormously: pipeline depth, whether the
  CPU is **superscalar** (executing more than one instruction per cycle
  through multiple parallel execution units at once), and
  architecture-generation efficiency improvements all change that
  number independently of raw GHz.
- A newer chip at a lower clock speed can comfortably outperform an
  older one at a higher clock speed — the same "a single number hides
  what actually matters" lesson already established for
  [what Big-O itself throws away](big-o-and-memory-hardware.md#what-big-o-actually-measures-and-what-it-throws-away):
  a clean, simple metric is a real signal, but never the whole picture
  on its own.

---

## Code Samples

No dedicated code samples for this page.
