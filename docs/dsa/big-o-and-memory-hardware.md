---
title: "Big-O & the Hardware Underneath It"
---

# Big-O & the Hardware Underneath It

Knowing the Big-O of an algorithm is the tool-usage version of
algorithmic thinking — it's a label you can look up or memorize. The
fundamentals below are *why* two algorithms with the identical Big-O can
have wildly different real-world speed, which is what separates
reciting a complexity class from actually reasoning about performance —
exactly the kind of follow-up a senior-level interview asks after the
Big-O answer.

## What Big-O Actually Measures, and What It Throws Away

Big-O describes how the **number of operations** grows as input size
grows, as an upper bound — nothing more. By design, it **discards**:

- **Constant factors** — an algorithm doing `5n` operations and one
  doing `500n` operations are both "O(n)."
- **What each operation actually costs on real hardware** — Big-O
  treats every "operation" as equally expensive, which is almost never
  true once memory is involved.

That second point is the one most interview answers stop short of, and
it comes entirely from the hardware underneath the code.

## The Memory Hierarchy: Why "RAM" Isn't One Speed

A CPU doesn't read data from one uniform pool of "memory" — it reads
through a hierarchy, each level dramatically slower than the one above
it:

| Level | Roughly how fast | Roughly how big |
|---|---|---|
| CPU registers | ~instant | A few dozen values |
| L1 cache | ~1 ns | Tens of KB |
| L2 cache | ~4 ns | Hundreds of KB |
| L3 cache | ~15 ns | A few MB |
| Main memory (RAM) | ~100 ns | GBs |
| SSD | ~100,000 ns | Hundreds of GBs–TBs |

Each step down is roughly an order of magnitude slower — a value that
has to come from RAM instead of L1 cache costs *roughly 100x* more time,
even though both are "just reading memory" from the algorithm's point of
view. Big-O counts both as one identical operation.

## Cache Lines & Locality: Why an Array Beats a Linked List at the Same Big-O

The CPU never fetches a single value from RAM in isolation — it fetches
an entire **cache line** at once (commonly 64 bytes), on the bet that
nearby memory will probably be needed next. This single fact explains a
result that confuses people comparing Big-O tables: scanning an array
and scanning a linked list are both "O(n)," but one is consistently
faster in practice.

- An array's elements sit **contiguously** in memory. Reading element 0
  pulls in a whole cache line — elements 1, 2, 3 (and more, depending on
  their size) often arrive **for free** in that same fetch, with zero
  additional trips to RAM.
- A linked list's nodes are **scattered** wherever the allocator
  happened to place each one independently. Following `.next` almost
  never lands in an already-loaded cache line — nearly every node is a
  fresh cache miss, a fresh ~100 ns trip to RAM.

<svg viewBox="0 0 900 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram comparing an array scan, which serves most reads from one cached line, against a linked-list scan, which trips to RAM for nearly every node" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="0" y="0" width="900" height="460" fill="#ffffff" stroke="#d0d5dd" stroke-width="1"></rect>
<rect x="20" y="40" width="160" height="90" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="100" y="80" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">CPU</text>
<text x="100" y="100" font-size="12" text-anchor="middle" fill="#5b6472">reads one element</text>
<rect x="280" y="40" width="200" height="90" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="380" y="80" font-size="14" font-weight="600" text-anchor="middle" fill="#7a5c14">Cache Line</text>
<text x="380" y="100" font-size="12" text-anchor="middle" fill="#9a7420">holds ~8 array elements</text>
<rect x="680" y="40" width="200" height="90" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<text x="780" y="80" font-size="14" font-weight="600" text-anchor="middle" fill="#1d4a78">RAM</text>
<text x="780" y="100" font-size="12" text-anchor="middle" fill="#3d699a">~100 ns per trip</text>
<text x="450" y="170" font-size="17" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.44;0.47;1" dur="14s" repeatCount="indefinite"></animate>Array scan — 8 elements</text>
<circle r="8" fill="#1f9d6b" cy="200"><animate attributeName="cx" values="100;380;380;380" keyTimes="0;0.04;0.4;1" dur="14s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.44;0.46;1" dur="14s" repeatCount="indefinite"></animate></circle>
<text x="450" y="200" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.44;0.47;1" dur="14s" repeatCount="indefinite"></animate>Only 1 trip to RAM loads the whole cache line — the next 7 reads are free.</text>
<text x="450" y="170" font-size="17" font-weight="600" text-anchor="middle" fill="#8e2d20"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.47;0.5;0.95;0.98;1" dur="14s" repeatCount="indefinite"></animate>Linked list scan — 8 nodes</text>
<circle r="8" fill="#c0392b" cy="200"><animate attributeName="cx" values="100;100;780;100;780;100;780;100;780;100;100" keyTimes="0;0.47;0.53;0.59;0.65;0.71;0.77;0.83;0.89;0.95;1" dur="14s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.47;0.5;0.95;0.98;1" dur="14s" repeatCount="indefinite"></animate></circle>
<text x="450" y="200" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.47;0.5;0.95;0.98;1" dur="14s" repeatCount="indefinite"></animate>Every node is scattered in memory — 8 separate trips to RAM for the same 8 elements.</text>
<text x="450" y="420" font-size="19" font-weight="600" text-anchor="middle" fill="#1f2a3a">Same Big-O, O(n). Roughly 8x the RAM trips for the linked list — the gap Big-O doesn't count.</text>
</svg>

!!! success "What this means in an interview"

    Reciting "both are O(n)" answers the question asked. Adding "but the
    array will almost always be faster in practice at realistic sizes,
    because sequential access is cache-friendly and pointer-chasing
    isn't" is the senior-level follow-up — it shows the Big-O answer is
    a floor for reasoning about performance, not the end of it.

## Virtual Memory: The Even More Expensive Miss

Programs never address physical RAM directly — each process gets its
own **virtual** address space, translated to physical addresses by the
CPU's memory management unit, with recent translations cached in the
**TLB** (Translation Lookaside Buffer). A **page fault** — the data
isn't even resident in RAM, and has to be pulled from disk/swap — costs
on the order of **milliseconds**, another 10,000x+ jump past even a RAM
access. This is the same hierarchy as the cache-line story above, one
level further down: a dataset that doesn't fit in RAM at all can be
orders of magnitude slower than one that barely does, for reasons no
Big-O analysis of the algorithm itself will ever surface.

## The Actual Takeaway

Big-O is a **starting point for reasoning, not the final answer**. The
hardware underneath — cache lines, memory locality, paging — is where
real-world performance differences between same-complexity algorithms
actually come from, and it's exactly why
[data structure memory layout](../backend/python/data-structures-and-memory.md)
(how contiguous or scattered a structure actually is) matters as much in
practice as its textbook complexity does.
