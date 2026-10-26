---
title: "Python Syntax Idioms: Ternary, Comprehensions, Walrus & Pattern Matching"
---

# Python Syntax Idioms: Ternary, Comprehensions, Walrus & Pattern Matching

An **expression** produces a value (`2 + 2`, `x if cond else y`); a
**statement** performs an action and produces nothing (`for`,
`if`, a plain assignment). This distinction matters because every
feature on this page exists specifically to let more logic be written
as a compact *expression* instead of a multi-line *statement* — which
is exactly why they show up constantly in interviews and code review:
they're a direct test of how comfortable someone is writing idiomatic,
not just correct, Python.

## 1. The Ternary Operator (Conditional Expression)

```python
status = "adult" if age >= 18 else "minor"

# equivalent, spelled out as a statement
if age >= 18:
    status = "adult"
else:
    status = "minor"
```

**Answer:**

- Python calls this a **conditional expression** — "ternary operator"
  is the common, language-agnostic name (any operator taking three
  operands), but Python's own docs use the former term.
- The order reads differently from C-family languages
  (`cond ? a : b`): Python puts the **result first** — `a if cond else
  b` — which is a frequent source of confusion for anyone coming from
  C, Java, or JavaScript.
- **Interview point:** it's an *expression*, so it can be used
  anywhere a value is expected — inside a function call's argument, a
  list literal, an f-string — not just on the right side of an
  assignment. Nesting more than one, though (`a if x else b if y else
  c`), is a real readability cost most style guides flag — a chain of
  `if`/`elif`/`else` statements reads better past two branches.

## 2. Comprehensions: List, Dict, Set, and Generator

```python
squares = [n * n for n in range(10)]                    # list
evens_only = [n for n in range(10) if n % 2 == 0]        # with a filter
lookup = {n: n * n for n in range(10)}                   # dict
unique_lengths = {len(w) for w in words}                 # set
total = sum(n * n for n in range(10))                    # generator -- no brackets at all
```

**Answer:**

- A **comprehension** builds a new collection by looping over an
  iterable and optionally filtering it, in one expression — the
  compact alternative to writing an empty collection, a `for` loop,
  and repeated `.append()`/`[key] =` calls as four separate statements.
- All four (list, dict, set, generator) share the same shape: `for` to
  iterate, an optional `if` to filter, and an expression at the front
  describing what each kept item becomes.
- **The generator expression is the one most worth knowing well** —
  dropping the brackets (`(n * n for n in range(10))`, or no brackets
  at all when it's the sole argument to a function like `sum(...)`
  above) produces values **lazily, one at a time**, instead of
  building the entire list in memory first. For a huge or unbounded
  iterable, that's the difference between the program running at all
  and running out of memory.
- **Interview point:** "when would a comprehension be the *wrong*
  choice?" — expects naming readability, not performance, as the real
  limit: a comprehension with more than one `for` or more than one
  `if`, or non-trivial logic in the expression itself, is usually
  clearer written back out as a real `for` loop. A comprehension
  that needs a comment to explain it has already lost its own reason
  to exist.

| Form | Builds | Lazy? |
|---|---|---|
| `[... for ... ]` | A list, all at once | No — fully built in memory |
| `{k: v for ...}` | A dict | No |
| `{... for ...}` | A set | No |
| `(... for ...)` | A generator | Yes — one value at a time, on demand |

## 3. The Walrus Operator (Assignment Expressions)

```python
# Without walrus -- the length is computed, and named, twice
if len(data) > 10:
    process(len(data))

# With walrus -- computed once, bound to n, and usable immediately
if (n := len(data)) > 10:
    process(n)
```

**Answer:**

- `:=` (added in Python 3.8) lets an assignment happen **inside** an
  expression — a plain `=` is a statement and can't appear inside an
  `if` condition, a comprehension, or any other expression context at
  all; `:=` can.
- The name comes from its shape resembling a sideways walrus with
  tusks (`:=`) — a real, if informal, piece of Python trivia worth
  knowing since the feature is still commonly just called "the walrus
  operator" even in formal contexts.
- **Where it actually earns its place:** avoiding computing or calling
  something twice (as above), and inside comprehensions, where there
  was previously no way to both filter on a computed value *and* reuse
  that same value in the kept expression:

```python
results = [y for x in data if (y := expensive(x)) is not None]
# without walrus, expensive(x) would need to be called twice per item
```

- **Interview point:** it's deliberately restricted — `:=` cannot be
  used for a bare top-level assignment (`x := 5` alone is a syntax
  error; it needs to be inside a larger expression), specifically to
  stop it from just becoming a shorter, more confusing version of `=`
  everywhere.

## 4. Unpacking and Starred Expressions

```python
a, b = b, a                           # swap -- no temp variable needed
first, *rest = [1, 2, 3, 4]           # first = 1, rest = [2, 3, 4]
*init, last = [1, 2, 3, 4]            # init = [1, 2, 3], last = 4
first, *middle, last = [1, 2, 3, 4]   # first = 1, middle = [2, 3], last = 4

def greet(*args, **kwargs):           # collect extra positional/keyword args
    print(args, kwargs)

greet(*[1, 2, 3], **{"name": "Alice"})  # spread a list/dict back out as arguments
```

**Answer:**

- **Unpacking** assigns the elements of an iterable to multiple names
  in one statement — `a, b = b, a` is Python's idiomatic swap, working
  because the right side is fully evaluated into a temporary tuple
  *before* either assignment happens, so there's no need for a manual
  temp variable the way C-family languages require.
- A single `*name` in an unpacking target collects **everything else**
  into a list — at most one starred target is allowed per unpacking,
  since Python has no way to know how to split "everything else"
  between two of them.
- `*args`/`**kwargs` in a function **definition** are the same idea
  applied to collecting arguments: `*args` gathers extra positional
  arguments into a tuple, `**kwargs` gathers extra keyword arguments
  into a dict.
- The same `*`/`**` syntax in a function **call** does the reverse —
  **spreads** an existing list/dict back out into separate positional/
  keyword arguments, which is how one function can forward whatever it
  received straight through to another (`def wrapper(*args, **kwargs):
  return real_func(*args, **kwargs)`).

## 5. Structural Pattern Matching (`match`/`case`)

```python
def handle(command):
    match command.split():
        case ["go", direction] if direction in ("north", "south", "east", "west"):
            return f"Moving {direction}"
        case ["go", _]:
            return "Can't go that way"
        case ["look"]:
            return describe_room()
        case [action, *rest]:
            return f"Unknown action: {action}"
        case _:
            return "I don't understand"
```

**Answer:**

- `match`/`case` (added in Python 3.10) is **not** a switch statement
  — the common comparison undersells it. A `case` pattern can
  **destructure** the matched value (pulling `direction` out of a
  two-element list above) and **guard** with an `if` condition, in one
  line each, not just compare equality.
- Patterns can match on a value's **shape**: a list of a specific
  length, a dict with specific keys present, or even a class's
  attributes (`case Point(x=0, y=0):`) — genuinely structural matching
  against the data's form, not a sequence of `if`/`elif isinstance()`
  checks written out by hand.
- `_` is the **wildcard** — matches anything and binds nothing, used
  both as a catch-all final case and inside a pattern to mean "this
  position's value doesn't matter" (`case ["go", _]:` above matches
  "go" followed by anything).
- **Interview point:** "isn't this just `if`/`elif` in disguise?" — the
  honest answer is that simple equality-only matching genuinely is
  equivalent either way, but once a pattern needs to destructure
  *and* check structure at the same time, the `if`/`elif isinstance()`
  + manual unpacking equivalent gets meaningfully longer and easier to
  get wrong — that's the real case for reaching for `match` instead of
  just reflexively using it.

## 6. F-Strings (Formatted String Literals)

```python
name, score = "Alice", 94.5
f"{name} scored {score:.1f}%"           # "Alice scored 94.5%"
f"{name=}, {score=}"                    # "name='Alice', score=94.5" -- debug shorthand
f"{'high' if score >= 90 else 'low'}"   # any expression is valid inside {}
```

**Answer:**

- An **f-string** (`f"..."`, added in Python 3.6) embeds expressions
  directly inside a string literal's `{}` — evaluated and formatted
  inline, instead of `.format()`'s positional placeholders or
  `%`-style formatting's separate argument tuple.
- `{value:.1f}` is a **format spec** after the colon — controls things
  like decimal precision, padding, and alignment, the same mini-syntax
  `.format()` and `format()` itself use, just inline here.
- `{name=}` is the **debug specifier** (Python 3.8+) — expands to both
  the expression's source text and its value (`name='Alice'`),
  specifically for quick `print(f"{some_var=}")` debugging without
  having to type the variable's name twice.
- **Any valid expression** can go inside `{}`, including the ternary
  operator from [§1](#1-the-ternary-operator-conditional-expression) —
  f-strings aren't limited to plain variable names.
- **Security note, not just a style one:** never build a SQL query (or
  any other command a lower-trust layer will execute) with an
  f-string — see
  [Django ORM Query Cheat Sheet §16](django-orm.md#16-raw-sql-escape-hatches)
  for exactly why string-formatting user input into a query is an
  injection risk regardless of which formatting syntax does it.

---

## Code Samples

No dedicated code samples for this page — every snippet above is
small enough to run directly in a Python REPL.
