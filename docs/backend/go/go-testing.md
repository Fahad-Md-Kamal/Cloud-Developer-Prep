---
title: "Testing in Go"
---

# Testing in Go

Go ships its own testing framework in the standard library —
`testing` — with no separate library needed to write and run a basic
test, unlike Python where `pytest` (or `unittest`) is a separate
dependency from day one. This page covers the idiomatic patterns built
on top of that standard-library foundation: table-driven tests,
`testify` for richer assertions, benchmarks, and fuzzing.

## 1. The Standard Library's `testing` Package

```go
func TestAdd(t *testing.T) {
    got := add(2, 3)
    want := 5
    if got != want {
        t.Errorf("add(2, 3) = %d; want %d", got, want)
    }
}
```

```bash
go test ./...       # run every test in the module
go test -v ./...     # verbose — print each test's name as it runs
go test -run TestAdd # run only tests matching this name pattern
```

- A test function's name must start with `Test`, take a single
  `*testing.T` parameter, and live in a file ending `_test.go` — Go's
  test runner discovers tests purely by this naming convention, no
  decorator or registration needed.
- `t.Errorf` records a failure and lets the test continue (useful for
  reporting multiple problems in one run); `t.Fatalf` records a
  failure and stops that test immediately — the Go equivalent of
  `pytest`'s assertion failing vs. explicitly calling `pytest.fail()`.
- `go test ./...` recursively runs every test in the module — the
  default command in CI, the same role `pytest` run with no arguments
  plays for a Python project.

## 2. Table-Driven Tests — the Idiomatic Pattern

```go
func TestDivide(t *testing.T) {
    tests := []struct {
        name    string
        a, b    float64
        want    float64
        wantErr bool
    }{
        {"valid", 10, 2, 5, false},
        {"zero divisor", 10, 0, 0, true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := divide(tt.a, tt.b)
            if (err != nil) != tt.wantErr {
                t.Errorf("unexpected error: %v", err)
            }
            if got != tt.want {
                t.Errorf("got %v, want %v", got, tt.want)
            }
        })
    }
}
```

- A **table-driven test** defines a slice of test cases (inputs +
  expected outputs) and loops over them, calling `t.Run` once per
  case — the closest Go idiom to `pytest.mark.parametrize`, just
  written out explicitly rather than via a decorator, since Go has no
  decorator syntax at all.
- `t.Run(tt.name, ...)` gives each case its own named sub-test — a
  failure reports exactly which case failed (`TestDivide/zero_divisor`),
  and `go test -run TestDivide/zero_divisor` can re-run just that one
  case while debugging.
- **Interview point:** this pattern is idiomatic enough that an
  interviewer reading Go test code written any other way (a long
  sequence of separate, nearly-identical `Test` functions) will likely
  ask why it wasn't table-driven — it's considered the default, not an
  optional style choice.

## 3. `testify` for Richer Assertions and Mocks

```go
import (
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/mock"
)

func TestAdd(t *testing.T) {
    assert.Equal(t, 5, add(2, 3))
    assert.NoError(t, err)
}

type MockPaymentProcessor struct{ mock.Mock }

func (m *MockPaymentProcessor) Process(amount float64) bool {
    args := m.Called(amount)
    return args.Bool(0)
}
```

- `testify/assert` replaces the standard library's manual
  `if got != want { t.Errorf(...) }` pattern with readable one-liners
  (`assert.Equal`, `assert.NoError`, `assert.True`) — not required,
  but close to universal in real-world Go codebases.
- `testify/mock` provides a base `mock.Mock` struct to embed — calling
  `m.Called(args...)` inside a mock's method records the call and
  returns pre-configured values, the Go equivalent of Python's
  `unittest.mock.Mock`, just requiring the mock struct's methods to be
  written out explicitly to satisfy the real interface being mocked
  (the same implicit-interface-satisfaction idea from
  [Go Fundamentals §4](go-fundamentals.md#4-interfaces-implicit-satisfaction-no-implements)
  — a mock just needs the right methods, nothing more).

## 4. Benchmarks

```go
func BenchmarkAdd(b *testing.B) {
    for i := 0; i < b.N; i++ {
        add(2, 3)
    }
}
```

```bash
go test -bench=. -benchmem ./...
```

- A benchmark function starts with `Benchmark`, takes a `*testing.B`,
  and loops `b.N` times — the test framework automatically adjusts
  `N` upward until it gets a stable, statistically meaningful timing
  measurement, rather than the developer guessing an iteration count.
- `-benchmem` additionally reports memory allocated per operation and
  how many allocations occurred — directly connecting back to
  [Go Memory Management & Performance §1](go-memory-and-performance.md#1-stack-vs-heap-and-escape-analysis):
  an unexpectedly high allocation count in a benchmark is often the
  first real signal a value is escaping to the heap that shouldn't be.
- Benchmarks are how a Go engineer backs up a performance claim with a
  number instead of an assumption — "I made this faster" without a
  benchmark showing the before/after is a weak claim in a Go-specific
  interview context, where the tooling to prove it is built in and
  expected to be used.

## 5. Fuzzing — a Go-Specific Testing Feature

```go
func FuzzReverse(f *testing.F) {
    f.Add("hello") // a seed corpus value
    f.Fuzz(func(t *testing.T, s string) {
        reversed := reverse(s)
        doubleReversed := reverse(reversed)
        if s != doubleReversed {
            t.Errorf("reverse(reverse(%q)) = %q", s, doubleReversed)
        }
    })
}
```

```bash
go test -fuzz=FuzzReverse -fuzztime=30s
```

- **Fuzzing** generates random, often malformed, inputs automatically
  and checks that a property holds for all of them — reverse-of-reverse
  equals the original above — rather than only checking the specific
  cases a human thought to write down. Go has native fuzzing support
  built into the standard `testing` package since Go 1.18, which most
  languages require a separate dedicated tool for.
- This is the same underlying idea as
  [Property-Based Testing](../../testing/property-based-testing.md)
  (Python's Hypothesis) — stating a property that must always hold
  instead of enumerating individual example inputs — just built
  directly into Go's own toolchain rather than a third-party library.
- A failing fuzz input gets automatically saved to a `testdata/fuzz/`
  corpus file and replayed as a normal regression test on every future
  `go test` run — once fuzzing finds a bug, that exact input becomes
  a permanent part of the test suite with no manual step required.

## 6. Interview Questions You're Likely to Get Asked

**Structure & idiom**

- "What makes a Go test idiomatic vs. just technically correct?" —
  expects naming table-driven tests as the expected default,
  [§2](#2-table-driven-tests-the-idiomatic-pattern).
- "How does Go discover which functions are tests, with no
  decorator?" — expects the `Test`-prefix + `*testing.T` parameter +
  `_test.go` filename convention, [§1](#1-the-standard-librarys-testing-package).

**Mocking & performance**

- "How do you mock a dependency behind an interface in Go?" —
  expects `testify/mock`, or a hand-written fake satisfying the
  interface, since Go's structural typing makes either trivial,
  [§3](#3-testify-for-richer-assertions-and-mocks).
- "How would you actually prove a change made a function faster?" —
  expects naming Go's built-in benchmarking, not an informal timing
  claim, [§4](#4-benchmarks).

**Fuzzing**

- "What's fuzzing, and how is it different from a table-driven test?"
  — expects: generated random inputs checking a property holds, vs.
  a fixed, human-written set of cases, [§5](#5-fuzzing-a-go-specific-testing-feature).

---

## Code Samples

No dedicated code samples for this page — every snippet above is
runnable directly with `go test` once the function under test
(`add`, `divide`, `reverse`) is supplied.
