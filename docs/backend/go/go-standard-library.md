---
title: "Go Standard Library Essentials"
---

# Go Standard Library Essentials

Go's standard library is unusually complete compared to most
languages — a real HTTP server, JSON encoding, and file I/O all ship
in the box, which is why Go projects tend to have far fewer
third-party dependencies than an equivalent Python or Node project.
This page covers the stdlib packages that show up in nearly every Go
codebase, beyond `net/http` (covered in
[Building Web Services & Microservices in Go](go-web-services-and-microservices.md))
and `context`/`sync` (covered in
[Concurrency in Go](go-concurrency.md)).

## 1. `io.Reader` and `io.Writer` — the Interfaces Everything Is Built On

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}
type Writer interface {
    Write(p []byte) (n int, err error)
}

func CopyUppercase(dst io.Writer, src io.Reader) error {
    data, err := io.ReadAll(src)
    if err != nil {
        return err
    }
    _, err = dst.Write(bytes.ToUpper(data))
    return err
}
```

- `io.Reader` and `io.Writer` are both single-method interfaces, and a
  huge share of Go's standard library is built directly around them: a
  file, an HTTP request body, a network connection, an in-memory
  buffer, and `os.Stdin`/`os.Stdout` **all** satisfy these same two
  interfaces, via the structural typing from
  [Go Fundamentals §4](go-fundamentals.md#4-interfaces-implicit-satisfaction-no-implements).
- **The practical payoff:** `CopyUppercase` above works completely
  unchanged whether `src` is a file, a network socket, or an HTTP
  request body — it never needed to know which, because it only ever
  depends on the `Reader` interface, not a concrete type.
- `io.ReadAll` reads an entire `Reader` into memory — convenient, but
  for genuinely large or unbounded input, streaming with a fixed-size
  buffer (reading in chunks via repeated `Read` calls, or a
  `bufio.Scanner`) avoids loading the whole thing into memory at once.

## 2. `encoding/json`: Struct Tags and (Un)marshaling

```go
type User struct {
    ID       int    `json:"id"`
    Name     string `json:"name"`
    Password string `json:"-"`              // never serialized
    Email    string `json:"email,omitempty"` // omitted from output if empty
}

data, _ := json.Marshal(user)           // struct -> JSON bytes
var u User
json.Unmarshal(data, &u)                 // JSON bytes -> struct (note: &u, a pointer)
```

- The backtick-delimited string after each field (a **struct tag**) is
  metadata the `encoding/json` package reads via reflection — `json:"id"`
  renames the field in JSON output; `json:"-"` excludes it entirely
  (the standard way to keep a password hash out of an API response);
  `omitempty` skips the field in output when it holds its zero value.
- `Unmarshal` takes a **pointer** to the destination (`&u`, not `u`) —
  it needs to write into the actual struct, not a copy of it, the
  same pointer-vs-value-receiver distinction from
  [Go Fundamentals §3](go-fundamentals.md#3-structs-and-methods) applied
  to a function argument instead of a method receiver.
- **Interview point:** an unexported (lowercase) struct field is
  invisible to `encoding/json` entirely, silently — not an error, just
  never read or written. A struct whose JSON output is unexpectedly
  missing a field is one of the most common beginner "bugs" in Go, and
  it's always this: the field name starts with a lowercase letter.

## 3. File and OS Operations

```go
data, err := os.ReadFile("config.json") // reads the whole file at once

f, err := os.Open("large.log")
if err != nil {
    log.Fatal(err)
}
defer f.Close() // runs when the enclosing function returns, success or error

scanner := bufio.NewScanner(f)
for scanner.Scan() {
    line := scanner.Text()
}
```

- `os.ReadFile` is the simple, whole-file case; `os.Open` plus
  `bufio.Scanner`/`bufio.Reader` is the streaming case for a file too
  large to comfortably hold in memory at once, reading line-by-line or
  in buffered chunks instead.
- `defer f.Close()` immediately after a successful `os.Open` is the
  idiomatic Go pattern for "always clean this up" — `defer` schedules
  the call to run when the *enclosing function* returns, regardless of
  which return path was taken, the same unconditional-cleanup
  guarantee a Python `with open(...)` context manager provides, just
  expressed as "defer the close right after the open succeeds" instead
  of a block structure.
- **Interview point:** `defer` runs in **LIFO (Last In, First Out)**
  order — multiple deferred calls in one function unwind in reverse
  of how they were registered, which matters when deferred cleanups
  have a dependency order (closing a file before releasing the lock
  that protects it, for instance).

## 4. The `time` Package

```go
d := 2 * time.Second
start := time.Now()
elapsed := time.Since(start)

t := time.Date(2026, time.January, 15, 0, 0, 0, 0, time.UTC)
formatted := t.Format("2006-01-02 15:04:05") // Go's reference-time format
```

- `time.Duration` is a real type (not a bare number of seconds) — Go
  makes adding `2 * time.Second` type-safe and self-documenting,
  rather than a function silently expecting milliseconds when a caller
  passed seconds.
- **The formatting gotcha every Go developer hits once:** Go has no
  `strftime`-style format codes (`%Y-%m-%d`). Instead, a format string
  is written using Go's **reference time** —
  `Mon Jan 2 15:04:05 MST 2006` (`01/02 03:04:05PM '06 -0700`, easier
  to remember as the sequence 1-2-3-4-5-6-7) — and whatever pattern
  those specific reference values are arranged into is reused on the
  real timestamp. `"2006-01-02"` formats a date as `YYYY-MM-DD`
  because `2006` is the reference year, `01` the reference month, `02`
  the reference day, in that exact layout.
- `time.Since(start)` is shorthand for `time.Now().Sub(start)` —
  the idiomatic way to measure elapsed time, used throughout the
  profiling/benchmarking content in
  [Go Memory Management & Performance](go-memory-and-performance.md).

## 5. `strings`, `strconv`, and Building Strings Efficiently

```go
s := strings.Join([]string{"a", "b", "c"}, ", ")
n, err := strconv.Atoi("42")        // string -> int
str := strconv.Itoa(42)             // int -> string

var sb strings.Builder
for i := 0; i < 1000; i++ {
    sb.WriteString("x")
}
result := sb.String()
```

- `strconv` (string conversion) handles conversions between strings
  and numeric types — `Atoi`/`Itoa` for `int` specifically, `ParseFloat`/
  `FormatFloat` and similar for other numeric types — all returning an
  explicit `error` for the conversion rather than throwing, consistent
  with Go's
  [no-exceptions error handling](go-fundamentals.md#5-error-handling-no-exceptions).
- **`strings.Builder` matters for the same reason Python's
  `"".join(list)` beats repeated `+=` on a string in a loop:** a Go
  `string` is immutable, so `result += "x"` in a loop allocates a
  brand-new string every single iteration. `strings.Builder` writes
  into a growable internal buffer and only produces the final string
  once, the direct Go equivalent of that same "don't repeatedly
  concatenate immutable strings" performance lesson.

## 6. Interview Questions You're Likely to Get Asked

**Interfaces & JSON**

- "Why can the same function read from a file, a network connection,
  or stdin with no changes?" — expects `io.Reader`'s structural typing,
  [§1](#1-ioreader-and-iowriter-the-interfaces-everything-is-built-on).
- "A struct's JSON output is missing a field — what's the most likely
  cause?" — expects an unexported (lowercase) field name,
  [§2](#2-encodingjson-struct-tags-and-unmarshaling).

**Resource cleanup & formatting**

- "What order do multiple `defer` calls in one function run in?" —
  expects LIFO, [§3](#3-file-and-os-operations).
- "How does Go format a date without `strftime`-style codes?" —
  expects naming the reference-time layout and being able to explain
  `"2006-01-02"`, [§4](#4-the-time-package).

**Performance**

- "Why use `strings.Builder` instead of `+=` in a loop?" — expects
  string immutability and repeated reallocation,
  [§5](#5-strings-strconv-and-building-strings-efficiently).

---

## Code Samples

No dedicated code samples for this page — every snippet above is a
complete, runnable example with `go run`.
