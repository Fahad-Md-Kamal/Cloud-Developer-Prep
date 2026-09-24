---
title: "Go for Python Developers"
---

# Go for Python Developers

Enough Go to read a Go codebase, discuss trade-offs against Python
confidently, and not freeze up if a lead-level interview probes
cross-stack versatility. Not a claim of Go expertise — a credible
"I can contribute and reason about this" baseline.

## Why Go Matters for Backend Engineers

**Key differences from Python:**

- Compiled and statically typed, vs. Python's interpreted, dynamic
  typing.
- Built-in concurrency primitives (goroutines) vs. Python's
  asyncio/threading split.
- Memory-efficient for high-throughput services.
- Fast compilation and single-binary deployment — no runtime
  interpreter or virtual environment needed on the target machine.

**When teams choose Go over Python:**

- High-performance microservices where raw throughput matters.
- CLI tools and SDKs distributed as a single binary.
- Systems programming.
- Network services requiring high concurrency with predictable memory
  use.

## Go Syntax Basics — Quick Reference

**Variable declaration:**

```python
# Python
name = "Alice"
age = 30
```

```go
// Go — multiple ways
var name string = "Alice"
age := 30  // type inference
const MaxRetries = 3
```

**Functions:**

```python
# Python
def add(a: int, b: int) -> int:
    return a + b
```

```go
// Go — multiple return values are idiomatic
func add(a int, b int) int {
    return a + b
}

// The standard error-handling pattern
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}
```

**Structs (similar to Python dataclasses):**

```python
# Python
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str
```

```go
// Go
type User struct {
    ID    int    `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

// Method on a struct
func (u *User) FullInfo() string {
    return fmt.Sprintf("%s (%s)", u.Name, u.Email)
}
```

**Interfaces — duck typing made explicit:**

```python
# Python — implicit protocol
class PaymentProcessor:
    def process(self, amount: float) -> bool: ...
```

```go
// Go — explicit interface
type PaymentProcessor interface {
    Process(amount float64) bool
}

type StripeProcessor struct{}

func (s *StripeProcessor) Process(amount float64) bool {
    return true
}
```

## Concurrency: Goroutines vs. Python AsyncIO

```python
# Python AsyncIO
import asyncio

async def fetch_data(url: str) -> dict:
    return data

async def main():
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
```

```go
// Go goroutines
func fetchData(url string, ch chan<- map[string]interface{}) {
    ch <- data
}

func main() {
    ch := make(chan map[string]interface{})
    for _, url := range urls {
        go fetchData(url, ch)  // launch goroutine
    }
    for i := 0; i < len(urls); i++ {
        result := <-ch  // receive from channel
    }
}
```

**Channels, the core concept:**

```go
ch := make(chan int)       // unbuffered — blocks until received
ch := make(chan int, 100)  // buffered — up to 100 pending

ch <- 42        // send
value := <-ch   // receive

// select waits on multiple channels — the Go analogue of asyncio.wait
select {
case msg := <-ch1:
    fmt.Println("Received from ch1:", msg)
case msg := <-ch2:
    fmt.Println("Received from ch2:", msg)
case <-time.After(1 * time.Second):
    fmt.Println("Timeout")
}
```

- Goroutines are lighter-weight than OS threads, and the runtime
  schedules them across available cores — real parallelism, not just
  concurrency on one thread the way Python's asyncio is (see
  [Concurrency & AsyncIO](../python/concurrency-and-asyncio.md) for what the GIL
  specifically restricts in Python).
- Channels are the idiomatic way goroutines communicate — "don't
  communicate by sharing memory, share memory by communicating" is
  Go's own framing of this.

## Error Handling — No Exceptions

```python
# Python
try:
    result = risky_operation()
except ValueError as e:
    handle_error(e)
```

```go
// Go — explicit error returns, checked at every call site
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

- Go has no exceptions for ordinary error handling — every fallible
  call returns an `error` value that the caller must explicitly check.
- This is a deliberate design choice: errors are values, not
  control-flow jumps — nothing is hidden in a stack unwind the way a
  Python exception can be.
- `%w` in `fmt.Errorf` wraps the original error so `errors.Is`/
  `errors.As` can still inspect the underlying cause further up the
  call stack.

## Building a REST API — Go vs. Python

```python
# Python (FastAPI)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: str

@app.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user
```

```go
// Go (using the gin framework)
package main

import (
    "github.com/gin-gonic/gin"
    "net/http"
)

type User struct {
    ID    int    `json:"id"`
    Name  string `json:"name"`
    Email string `json:"email"`
}

func main() {
    r := gin.Default()
    r.GET("/users/:user_id", func(c *gin.Context) {
        userID := c.Param("user_id")
        user, err := db.GetUser(userID)
        if err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "user not found"})
            return
        }
        c.JSON(http.StatusOK, user)
    })
    r.Run(":8080")
}
```

## Key Go Patterns for Microservices

**Context propagation** (critical for distributed systems — carries
cancellation/timeout/request-scoped values through a call chain):

```go
func fetchUserWithTimeout(ctx context.Context, userID string) (*User, error) {
    ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
    defer cancel()
    return userService.Get(ctx, userID)
}
```

**Graceful shutdown** (drain in-flight requests before exiting, on
`SIGINT`/`SIGTERM`):

```go
func main() {
    srv := &http.Server{Addr: ":8080"}
    go func() {
        if err := srv.ListenAndServe(); err != nil {
            log.Fatal(err)
        }
    }()

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    srv.Shutdown(ctx)
}
```

## Testing in Go

```python
# Python (pytest)
def test_add_numbers():
    assert add(2, 3) == 5
```

```go
// Go — table-driven tests are the idiomatic pattern
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

## Quick Reference: Go for Python Developers

| Concept | Python | Go |
|---|---|---|
| Package management | `pip install requests` | `go get github.com/...` |
| Virtual envs | `venv`, `virtualenv` | Go modules (`go.mod`) — no venv needed |
| Formatting | `black`, `ruff` | `go fmt` (built in, enforced) |
| Linting | `pylint`, `mypy` | `go vet`, `golangci-lint` |
| Dependency injection | Manual, or a framework | Interfaces + constructors |
| ORM | SQLAlchemy, Django ORM | GORM, sqlx (less "magic") |
| JSON | `json.loads()` / `json.dumps()` | `json.Marshal()` / `json.Unmarshal()` |
| Null handling | `None`, `Optional[T]` | `nil`, pointers `*T` |

**Interview talking points:**

- "While I'm Python-first, I understand Go's value for high-performance
  services and have read/contributed to Go microservices."
- "I appreciate Go's explicit error handling and built-in concurrency
  primitives, and can reason about trade-offs against Python's
  asyncio/GIL model."
