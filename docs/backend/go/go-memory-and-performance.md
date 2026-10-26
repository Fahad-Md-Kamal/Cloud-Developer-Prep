---
title: "Go Memory Management & Performance"
---

# Go Memory Management & Performance

Go manages memory automatically with a **garbage collector (GC)** —
like Python, a developer doesn't manually `free()` memory the way C
requires — but Go's compiler also decides, at compile time, whether
each value can live on the fast, cheap **stack** or must go on the
slower, GC-managed **heap**. That decision, called **escape
analysis**, is the single biggest lever for Go performance most
engineers never learn to look at directly.

## 1. Stack vs. Heap, and Escape Analysis

```go
func createUser() *User {
    u := User{Name: "Alice"} // does this escape to the heap?
    return &u                 // yes — its address outlives this function's stack frame
}

func sumSquares(n int) int {
    total := 0 // stays on the stack — never referenced outside this function
    for i := 0; i < n; i++ {
        total += i * i
    }
    return total
}
```

- The **stack** is fast to allocate on and automatically reclaimed
  when a function returns — no garbage collector involvement at all.
  The **heap** is where anything that must outlive its creating
  function's stack frame has to live, and the GC is responsible for
  reclaiming it once nothing references it anymore.
- **Escape analysis** is the Go compiler deciding, for every value,
  whether it can safely stay on the stack or must "escape" to the
  heap — `createUser` above returns a pointer to a local variable, so
  that variable's memory has to survive past the function returning,
  forcing it onto the heap. `sumSquares`'s `total` never leaves the
  function, so it stays on the stack.
- `go build -gcflags="-m"` prints the compiler's actual escape
  analysis decisions for a file — a genuinely practical tool, not just
  theory, for answering "why is this function allocating more than I
  expected."
- **Interview point:** fewer heap allocations means less work for the
  GC later — this is the real reason "avoid unnecessary pointers for
  small, short-lived values" is real Go performance advice, not just a
  style preference; each avoidable heap escape is one more object the
  GC eventually has to trace and reclaim.

## 2. The Garbage Collector

**Answer:**

- Go's GC is a **concurrent, tri-color mark-and-sweep collector** —
  "concurrent" meaning it runs mostly alongside the program instead of
  fully pausing it, which is what keeps Go's GC pause times
  characteristically short (sub-millisecond to low-millisecond, even
  on multi-gigabyte heaps) compared to older stop-the-world
  collectors.
- The practical trade-off for that low pause time: Go's GC runs more
  frequently and uses more CPU overall than a collector tuned purely
  for throughput — it's optimized for latency (consistent, short
  pauses), not for squeezing the absolute minimum total GC CPU time
  out of a batch job.
- `GOGC` (default `100`) controls how aggressively the GC runs — it
  triggers a collection when the heap has grown by that percentage
  since the last collection. Lowering it collects more often (less
  memory used, more CPU spent); raising it (or `GOMEMLIMIT` as a hard
  cap) trades memory for fewer, less frequent collections.
- **Interview point:** "does Go have memory leaks if it's garbage
  collected?" — yes, and the honest answer names the real cause: a Go
  program leaks when something keeps a reference alive longer than
  intended (a goroutine blocked forever on a channel no one writes to
  anymore, a slice holding onto a huge backing array through a tiny
  sub-slice, a global map that only ever grows) — the GC can only
  reclaim memory nothing references, not memory something is still,
  mistakenly, holding onto.

## 3. Value Semantics vs. Pointer Semantics

```go
type BigStruct struct {
    Data [1000]int
}

func processByValue(b BigStruct) { /* gets a full 1000-int copy */ }
func processByPointer(b *BigStruct) { /* gets an 8-byte pointer */ }
```

- Passing a struct **by value** copies the entire thing onto the new
  function's stack frame — fine and often faster for small structs
  (a few fields), since stack allocation and copying a small amount of
  data is cheap and avoids any heap/GC involvement at all.
- Passing **by pointer** avoids the copy, which matters once a struct
  is large (as `BigStruct` above) or when the function genuinely needs
  to mutate the caller's original value, not a copy of it.
- **Interview point:** "should I always use pointers for performance?"
  — no, and this is a common overcorrection: for small structs, a
  pointer can actually be *slower*, since it forces the value to
  escape to the heap ([§1](#1-stack-vs-heap-and-escape-analysis)) when
  it could otherwise have stayed on the stack as a value — the real
  rule is struct size and mutation need, not a blanket "pointers are
  faster" assumption.

## 4. Profiling with `pprof`

```go
import _ "net/http/pprof"

func main() {
    go http.ListenAndServe("localhost:6060", nil) // exposes /debug/pprof/
    // ... rest of the program
}
```

```bash
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30  # CPU profile
go tool pprof http://localhost:6060/debug/pprof/heap                # memory profile
go tool pprof http://localhost:6060/debug/pprof/goroutine           # goroutine dump
```

- `pprof` is Go's built-in profiler — importing `net/http/pprof` for
  its side effect alone (the blank `_` import) registers profiling
  endpoints on an HTTP server with zero other code changes.
- A **CPU profile** samples where the program is actually spending
  time; a **heap profile** shows what's allocated and by which call
  path, the direct tool for chasing down the unexpected allocations
  escape analysis ([§1](#1-stack-vs-heap-and-escape-analysis))
  predicted; a **goroutine profile** dumps every currently-running
  goroutine and its stack — the standard tool for diagnosing a
  goroutine leak (a growing goroutine count that never shrinks back
  down).
- `go test -bench=. -benchmem` runs benchmarks and reports allocations
  per operation alongside time per operation — the benchmark-level
  equivalent of a heap profile, scoped to one function instead of a
  whole running program.

## 5. Interview Questions You're Likely to Get Asked

**Memory fundamentals**

- "What decides whether a value lives on the stack or the heap in
  Go?" — expects escape analysis, and that it's a compiler decision,
  not a manual one, [§1](#1-stack-vs-heap-and-escape-analysis).
- "Can a garbage-collected language still leak memory? How?" —
  expects naming a real retained-reference cause (a stuck goroutine, a
  growing global, a sub-slice holding a huge backing array),
  [§2](#2-the-garbage-collector).

**Performance judgment**

- "Should you pass a struct by pointer for performance?" — expects
  the nuanced answer: depends on struct size and mutation need, not a
  blanket rule, [§3](#3-value-semantics-vs-pointer-semantics).
- "How would you find out why a function is allocating more memory
  than expected?" — expects naming `-gcflags="-m"` and/or a heap
  profile via `pprof`, [§1](#1-stack-vs-heap-and-escape-analysis) and
  [§4](#4-profiling-with-pprof).

---

## Code Samples

No dedicated code samples for this page — the `pprof` snippet is a
complete, runnable setup with `go run` once a real handler/workload is
added.
