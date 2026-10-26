---
title: "Go Fundamentals: Types, Structs & Interfaces"
---

# Go Fundamentals: Types, Structs & Interfaces

**Go** (also called **Golang**) is a compiled, statically-typed
language built at Google for writing reliable network services and
command-line tools that start fast, run efficiently, and deploy as a
single self-contained binary — no interpreter, no virtual environment,
no separate runtime to install on the target machine. That compiled,
single-binary nature is the root of most of what follows: Go trades
some of the expressiveness and runtime flexibility of a language like
Python for predictability, speed, and operational simplicity.

**Where Go is actually used:** its niche is cloud-native
infrastructure — most of the tools that run and orchestrate *other*
software are themselves written in Go, not just capable of deploying
Go workloads.

- **Containers & orchestration** — Docker (the `dockerd` daemon
  itself), Kubernetes, and containerd are all written in Go; it's the
  de facto language of the modern container ecosystem.
- **DevOps & infrastructure tooling** — Terraform (see
  [Terraform (IaC)](../../cloud-devops/terraform-fundamentals.md)),
  HashiCorp's Consul and Vault, Prometheus, and etcd (the distributed
  key-value store Kubernetes itself runs on) are all written in Go.
- **Databases** — CockroachDB (see
  [NewSQL: Distributed SQL](../../database/newsql-distributed-sql.md))
  and InfluxDB (see
  [Time-Series Databases](../../database/time-series-databases.md))
  are both written in Go.
- **At company scale** — Google (which created Go specifically for
  this kind of large-scale infrastructure work), Uber, Cloudflare, and
  Dropbox (which migrated performance-critical infrastructure off
  Python to Go) all run significant production Go.
- The common thread across all of it: Go gets reached for specifically
  where a service needs to start fast, run efficiently under
  sustained load, and deploy as a single dependency-free binary —
  exactly the properties named above.

## 1. Variables, Types & Zero Values

```go
var name string = "Alice"  // explicit type
age := 30                  // type inference — := only works inside a function
const MaxRetries = 3       // compile-time constant

var count int    // zero value: 0
var active bool  // zero value: false
var label string // zero value: "" (empty string)
```

- Go is **statically typed** — every variable's type is fixed at
  compile time and checked before the program ever runs, unlike
  Python where a name can be rebound to any type at any time.
- `:=` is shorthand for "declare and infer the type from the
  right-hand side" — only valid for a new variable inside a function;
  package-level variables need the explicit `var` form.
- **Every type has a zero value** — a variable that's declared but
  never explicitly set isn't `null`/`None`, it's a real, usable
  default (`0` for numbers, `""` for strings, `false` for booleans,
  `nil` for pointers/slices/maps/interfaces). This is a deliberate
  design choice: there's no "uninitialized" state a Go program can
  accidentally read, the class of bug a language with a true null
  reference has to guard against at every use site.

## 2. Slices — Not Quite Arrays

```go
arr := [3]int{1, 2, 3}      // array — fixed size, part of the type itself
s := []int{1, 2, 3}         // slice — the type everyone actually uses
s = append(s, 4)            // may or may not allocate a new backing array
```

- A Go **array** has its length baked into its type (`[3]int` and
  `[5]int` are different types entirely) — rarely used directly.
- A **slice** is what Python's list most directly corresponds to:
  a small struct of three fields — a pointer to a backing array, a
  length, and a capacity — not the data itself.
- **The gotcha this causes:** slicing a slice (`s[1:3]`) shares the
  *same* backing array as the original — writing through one slice can
  silently affect the other until `append` grows past capacity and
  allocates a fresh array. Interview-relevant: "why did modifying my
  sub-slice change the original?" is a real, common bug, and the
  answer is always this shared-backing-array behavior.
- `append` only allocates a new backing array when the slice's
  capacity is exceeded — otherwise it writes into existing spare
  capacity in place, which is why two slices derived from the same
  original can start aliasing each other unpredictably as they grow.

## 3. Structs and Methods

```go
type User struct {
    ID    int    `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

// A method with a pointer receiver — can mutate the struct
func (u *User) SetName(name string) {
    u.Name = name
}

// A method with a value receiver — operates on a copy
func (u User) FullInfo() string {
    return fmt.Sprintf("%s (%s)", u.Name, u.Email)
}
```

- A **struct** is Go's grouped-data type — closest to a Python
  `@dataclass`, but with no inheritance: Go composes structs instead
  of extending them (§4).
- A **method** is a function with a *receiver* — the `(u *User)` or
  `(u User)` before the method name. Whether that receiver is a
  pointer (`*User`) or a value (`User`) is a real, meaningful choice:
  a pointer receiver can modify the actual struct; a value receiver
  gets its own copy and any changes it makes vanish when it returns.
- **Interview point:** the rule of thumb is consistency — if *any*
  method on a type needs a pointer receiver (to mutate state, or to
  avoid copying a large struct on every call), use pointer receivers
  for *all* of that type's methods, so callers don't have to reason
  about which methods see mutations and which don't.

## 4. Interfaces — Implicit Satisfaction, No `implements`

```go
type PaymentProcessor interface {
    Process(amount float64) bool
}

type StripeProcessor struct{}

func (s *StripeProcessor) Process(amount float64) bool {
    return true
}

// StripeProcessor satisfies PaymentProcessor automatically —
// no "implements" keyword, no explicit declaration anywhere
var p PaymentProcessor = &StripeProcessor{}
```

- A type satisfies a Go interface simply by having the right methods —
  there's no `implements` keyword, no explicit declaration linking the
  type to the interface at all. This is **structural typing**:
  duck typing made explicit and checked at compile time, rather than
  Python's duck typing, which is dynamic and only fails at runtime
  when a missing method is actually called.
- **Embedding** — placing one struct (or interface) inside another
  with no field name — is Go's answer to inheritance, and it's
  composition, not an "is-a" relationship: the outer struct gets the
  inner one's fields and methods *promoted* onto it directly, but
  there's no polymorphism — a function expecting the outer type can't
  accept the inner type and vice versa, unlike real inheritance.
- **Interview point:** "does Go have inheritance?" — the honest
  answer is no, by design — embedding gives code reuse without the
  fragile-base-class problems inheritance hierarchies create, and
  interfaces give polymorphism without needing an explicit type
  hierarchy to opt into it.

## 5. Error Handling — No Exceptions

```go
result, err := riskyOperation()
if err != nil {
    return err
}
// use result

// Idiomatic error wrapping preserves context up the call stack
func processFile(path string) error {
    data, err := os.ReadFile(path)
    if err != nil {
        return fmt.Errorf("failed to read file %s: %w", path, err)
    }
    return nil
}
```

- Go has **no exceptions** for ordinary error handling — every
  fallible call returns an `error` value the caller must explicitly
  check, instead of Python's `try`/`except` catching a thrown
  exception anywhere up the call stack.
- This is a deliberate trade-off: errors are ordinary values, not a
  separate control-flow mechanism — nothing is hidden in a stack
  unwind, at the cost of `if err != nil` appearing after nearly every
  call that can fail.
- `%w` in `fmt.Errorf` **wraps** the original error so `errors.Is`/
  `errors.As` can still inspect the underlying cause further up the
  call stack — without it, wrapping with `%v` loses that chain and
  only the final string message survives.
- `panic`/`recover` exist but are reserved for genuinely unrecoverable
  program states (a programming bug, not an expected failure like "the
  network call timed out") — using them for ordinary error flow is
  considered un-idiomatic Go.

## 6. Interview Questions You're Likely to Get Asked

**Types & memory**

- "Why did modifying a sub-slice change the original slice too?" —
  expects the shared-backing-array explanation, [§2](#2-slices-not-quite-arrays).
- "When should a method use a pointer receiver vs. a value receiver?"
  — expects mutation needs + the consistency rule, [§3](#3-structs-and-methods).

**Interfaces & design**

- "Does Go have inheritance? How do you get code reuse without it?" —
  expects naming embedding and composition, and that it's not a true
  "is-a" relationship, [§4](#4-interfaces-implicit-satisfaction-no-implements).
- "How does a type satisfy an interface in Go?" — expects structural
  typing: having the right methods is sufficient, no explicit
  declaration, [§4](#4-interfaces-implicit-satisfaction-no-implements).

**Error handling**

- "Why does Go not have exceptions, and what's the trade-off?" —
  expects errors-as-values vs. hidden control flow,
  [§5](#5-error-handling-no-exceptions).
- "What does `%w` actually do in `fmt.Errorf` that `%v` doesn't?" —
  expects error wrapping and `errors.Is`/`errors.As`,
  [§5](#5-error-handling-no-exceptions).

---

## Code Samples

No dedicated code samples for this page — every snippet above is a
complete, minimal example runnable directly with `go run`.
