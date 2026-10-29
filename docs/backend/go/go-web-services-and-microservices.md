---
title: "Building Web Services & Microservices in Go"
---

# Building Web Services & Microservices in Go

Go's standard library already contains a full, production-capable
**HTTP** (Hypertext Transfer Protocol) server and router — `net/http`
— which is unusual compared to most languages, where a web framework
is a third-party necessity from the very first line of code. This page
covers `net/http` first, then when and why a framework like **gin**
earns its place on top of it. For general REST API design principles
that apply regardless of language, see
[REST Deep Dive](../../architecture/rest-deep-dive.md).

## 1. `net/http`: The Standard Library Is Already a Web Framework

```go
type userHandler struct{ db *Database }

func (h *userHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    userID := r.PathValue("id")
    user, err := h.db.GetUser(userID)
    if err != nil {
        http.Error(w, "user not found", http.StatusNotFound)
        return
    }
    json.NewEncoder(w).Encode(user)
}

func main() {
    mux := http.NewServeMux()
    mux.Handle("GET /users/{id}", &userHandler{db: db})
    http.ListenAndServe(":8080", mux)
}
```

- `http.Handler` is a one-method interface (`ServeHTTP(w, r)`) —
  anything satisfying it can handle a request, the same implicit
  interface satisfaction covered in
  [Go Fundamentals §4](go-fundamentals.md#4-interfaces-implicit-satisfaction-no-implements).
  A plain function can also become a handler via `http.HandlerFunc`,
  which adapts any `func(w, r)` to satisfy the interface.
- `http.ServeMux` (Go 1.22+) is the built-in router — it supports
  method-specific patterns (`GET /users/{id}`) and path parameters
  (`r.PathValue("id")`) directly, which used to require a third-party
  router in older Go versions.
- `w http.ResponseWriter` is itself an interface — writing to it
  streams the response directly; `json.NewEncoder(w).Encode(user)`
  writes JSON straight to the response without building an
  intermediate string first, the same streaming instinct as a
  `StreamingResponse` in a Python web framework.

## 2. When a Framework Like gin Earns Its Place

```go
// Go (using the gin framework)
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

- `net/http` alone is fully capable but low-level — no built-in request
  binding/validation, no middleware chaining convention, no route
  grouping. Frameworks like **gin** and **echo** add exactly that
  layer on top, the same role FastAPI's extras play on top of Python's
  raw ASGI (Asynchronous Server Gateway Interface).
- **gin**'s `gin.Context` bundles the request, response, and
  convenience methods (`c.JSON`, `c.Param`, request binding) into one
  object passed through every handler and middleware — a genuinely
  faster router than `net/http`'s default mux in gin's case, due to
  its trie-based route matching.
- **Interview point:** "when would you skip a framework entirely?" —
  a small service with few routes, or one where minimizing
  dependencies matters (a CLI tool's embedded HTTP server, a sidecar)
  is a legitimate reason to stay on plain `net/http` — the standard
  library being this capable is a genuinely distinctive Go trait worth
  naming directly, not just reaching for gin by reflex the way reaching
  for Express is reflexive in Node.

## 3. Middleware

```go
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r) // call the wrapped handler
        log.Printf("%s %s took %v", r.Method, r.URL.Path, time.Since(start))
    })
}

mux.Handle("/users/", loggingMiddleware(userHandler))
```

- Go middleware is just a function that takes a `Handler` and returns
  a new `Handler` wrapping it — there's no special middleware concept
  in the language, just regular function composition using the
  `Handler` interface from [§1](#1-nethttp-the-standard-library-is-already-a-web-framework).
- Order matters the same way it does in any framework: the
  outermost-wrapping middleware runs first on the way in and last on
  the way out — wrapping `loggingMiddleware(authMiddleware(handler))`
  means logging wraps (and times) the auth check too.
- gin/echo provide the same idea through their own `Use()` registration
  methods, which is syntactic convenience over this exact same
  wrap-a-handler pattern underneath.

## 4. Structuring a Go Microservice

**Answer:**

- A common, idiomatic layout separates `cmd/` (the `main` package,
  one subdirectory per binary if the repo builds more than one),
  `internal/` (packages only this module can import — Go's compiler
  enforces this, a real access-control boundary, not just a
  convention), and often a top-level `pkg/` for code genuinely meant
  to be imported by other modules.
- Within `internal/`, the same layering discipline that benefits any
  backend applies: handlers/routers stay thin (parse the request, call
  a service, write the response), services hold business logic, and a
  repository/store layer wraps the actual database calls — the Go
  version of the service-layer pattern already established for
  [Django](../../python/web-frameworks/django/django-drf.md#1-project-structure-that-scales)
  and
  [FastAPI](../../python/web-frameworks/fastapi/fastapi-database-and-testing.md#3-repository-service-layer-pattern).
- **gRPC** is a common choice for service-to-service calls within a Go
  microservices architecture specifically because Go's `protoc`
  tooling and generated code are first-class, well-maintained, and the
  language's static typing matches Protocol Buffers' own schema-first
  design — see [gRPC Deep Dive](../../architecture/grpc-deep-dive.md)
  for the protocol itself, language-agnostic.

## 5. Graceful Shutdown

```go
func main() {
    srv := &http.Server{Addr: ":8080"}
    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatal(err)
        }
    }()

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit // block until a shutdown signal arrives

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    srv.Shutdown(ctx) // stop accepting new requests, drain in-flight ones
}
```

- `srv.Shutdown(ctx)` stops accepting new connections immediately but
  lets in-flight requests finish, up to the context's deadline — the
  exact pattern that makes a rolling deployment safe: a server that
  just exits on `SIGTERM` drops whatever request was mid-flight at
  that instant, every single deploy.
- This is the same `SIGTERM`-first, grace-period, forced-stop-after
  pattern covered generally in
  [Linux Fundamentals for DevOps](../../cloud-devops/linux-fundamentals-for-devops.md#processes-signals)
  — Go's `http.Server.Shutdown` is just the application-level
  implementation of that same contract.
- `signal.Notify` is how a Go program listens for OS signals at all —
  without it, `SIGTERM` terminates the process immediately with the
  default behavior, never giving `Shutdown` a chance to run.

## 6. Interview Questions You're Likely to Get Asked

**HTTP & framework choice**

- "Why can Go build a real web server with zero third-party
  dependencies, when most languages can't?" — expects naming
  `net/http`'s completeness as a standard library design choice,
  [§1](#1-nethttp-the-standard-library-is-already-a-web-framework).
- "When would you skip gin/echo and stay on plain `net/http`?" —
  expects a real reason (few routes, minimizing dependencies), not "I
  always use a framework," [§2](#2-when-a-framework-like-gin-earns-its-place).

**Architecture & operations**

- "What does `internal/` actually enforce in a Go module, beyond
  convention?" — expects knowing the Go compiler itself blocks
  importing it from outside the module, [§4](#4-structuring-a-go-microservice).
- "What happens to an in-flight request if your Go service receives
  `SIGTERM` with no shutdown handling?" — expects: it's dropped
  immediately, the direct case for `srv.Shutdown`,
  [§5](#5-graceful-shutdown).

---

## Code Samples

No dedicated code samples for this page — every snippet above is a
complete, runnable server with `go run` once a `db`/handler dependency
is supplied.
