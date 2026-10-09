---
title: "JavaScript & TypeScript Fundamentals"
---

# JavaScript & TypeScript Fundamentals

Design principles, functional programming concepts, and TypeScript's
type system from a React/React Native interview — the vocabulary
questions that separate "has written JS for years" from "can define
these precisely and connect them to how code is actually structured."

## 1. "Can you explain the Interface Segregation Principle?"

**Answer:**

- Same principle as
  [SOLID Principles §4](../../architecture/solid-principles.md#4-interface-segregation-principle-isp),
  applied to JS/TS: a component or module shouldn't be forced to accept
  props/parameters it never uses just because they're bundled into one
  shared interface.

```typescript
// Violates ISP -- every consumer of DataTable is forced to know about
// sorting, filtering, AND export, even a read-only table that uses none of them
interface DataTableProps {
  data: Row[];
  onSort: (col: string) => void;
  onFilter: (query: string) => void;
  onExport: (format: "csv" | "pdf") => void;
}

// Segregated -- compose only the capabilities a given table actually needs
interface SortableProps { onSort: (col: string) => void }
interface FilterableProps { onFilter: (query: string) => void }
interface ReadOnlyTableProps { data: Row[] }
```

- A read-only table built against `ReadOnlyTableProps` never needs to
  mock or stub `onSort`/`onFilter`/`onExport` in a test — it simply
  can't see them.

## 2. "What is low coupling? What is high cohesion, and how do you implement it?"

**Answer:**

- Same two properties as
  [Cohesion & Coupling](../../architecture/cohesion-and-coupling.md),
  in a frontend context: high cohesion means a component does one
  thing (a `SearchInput` renders a search box and reports its value —
  it doesn't also fetch results or manage pagination); low coupling
  means components depend on each other's *props/interface*, not their
  internals (a parent doesn't reach into a child's internal state via a
  ref unless that's the component's actual documented API).
- **In practice**: extract a custom hook when a component's internal
  logic (data fetching, form state) grows past its rendering
  responsibility — the hook becomes independently testable, and the
  component shrinks back down to "render this data," the same
  separation [SOLID's SRP](../../architecture/solid-principles.md#1-single-responsibility-principle-srp)
  describes.

## 3. "A Button component already has 14 props and the product team wants more — what design principles would you apply?"

**Answer:**

- This is Open/Closed in practice
  ([SOLID Principles §2](../../architecture/solid-principles.md#2-openclosed-principle-ocp)):
  a prop-per-variant design means every new visual variant is a
  *modification* to `Button` (a new prop, a new branch in its render
  logic) rather than an *extension*.
- **The fix**: a composition-based API — a `variant` prop backed by a
  style-lookup object/CSS classes instead of a boolean per style
  (`isDanger`, `isOutlined`, `isSmall`, ...), or composing smaller
  pieces (`<Button><Button.Icon /><Button.Label /></Button>`) so new
  combinations don't require touching `Button`'s own source at all.

## 4. Functional Programming: Immutability and Currying

```javascript
// Mutation -- the caller's array is silently changed
function addItem(cart, item) {
  cart.push(item);
  return cart;
}

// Immutable -- returns a new array, the original is untouched
function addItem(cart, item) {
  return [...cart, item];
}

// Currying -- a function that takes its arguments one at a time
const multiply = (a) => (b) => a * b;
const double = multiply(2);
double(5); // 10 -- "a" was supplied earlier, "b" supplied now
```

**Answer:**

- **Immutability** means a function never modifies its input — it
  returns a new value instead. This matters most in React specifically
  because React detects changes via reference equality (`===`) for
  performance — mutating an array/object in place means React can't
  tell it changed at all, since the reference is identical before and
  after.
- **Currying** transforms a function taking multiple arguments into a
  sequence of functions each taking one — `multiply(2)` above returns
  a new function with `a` already "baked in," waiting for `b`. The
  practical use: creating specialized functions from a general one
  without writing a new function by hand (`double`, `triple`, etc. are
  all just `multiply(n)`).

## 5. Code Quality, Review, and Refactoring Under Pressure

**"As the sole developer with another joining in a few months, how do you manage code quality?"**

**Answer:**

- Treat the codebase as if the second developer is already reading it
  — consistent naming/structure from day one, not a cleanup pass right
  before they join (which never actually happens under real deadline
  pressure). A linter/formatter config committed early enforces this
  automatically rather than relying on memory.
- README/setup docs and a few deliberately-written "why" comments on
  non-obvious decisions are cheap now and expensive to reconstruct
  later once the context is gone.

**"How would you spot an anti-pattern in review, and give the feedback?"**

- Name the *concrete* problem, not the abstract principle — "this prop
  drills through four components that don't use it" lands better than
  "this violates separation of concerns." Suggest the fix inline
  (a code suggestion), not just the criticism — the colleague ships
  faster and the standard is demonstrated, not just stated.

**"A fix needs refactoring but the client is worried about ROI and timeline — how do you handle it?"**

- Separate the ask into "what's safe to defer" vs. "what compounds if
  deferred" — a cosmetic inconsistency can wait; a pattern that makes
  every future feature slower to build (the actual cost a non-technical
  stakeholder needs translated into their terms: "the next three
  features in this area will each take longer until this is fixed")
  is the argument that actually moves a ROI-focused conversation,
  not "it's not clean code."

## 6. `Map` vs. plain object, and implementing a Singleton

```javascript
// Map -- any key type, guaranteed insertion-order iteration, no prototype pollution risk
const cache = new Map();
cache.set(userId, userData);
cache.get(userId);

// Singleton -- module-level state is naturally a singleton in JS,
// since a module is only evaluated once and its exports are cached
class ConfigStore {
  static #instance;
  static getInstance() {
    if (!ConfigStore.#instance) {
      ConfigStore.#instance = new ConfigStore();
    }
    return ConfigStore.#instance;
  }
}
```

**Answer:**

- Reach for `Map` over a plain object when: keys aren't strings (object
  keys coerce to strings; `Map` keys can be any type, including
  objects), you need the actual size (`map.size` vs. manually counting
  `Object.keys(obj).length`), or insertion-order iteration matters.
  `Map.prototype.get`/`.set` also avoid prototype-chain collisions — a
  plain object's `"constructor"` or `"__proto__"` as a key can silently
  collide with inherited properties; a `Map` has no such risk.
  A hash map (`Map`'s actual implementation) is typically faster than
  a plain object for frequent additions/deletions, since V8's object
  implementation optimizes for a stable, known shape — repeatedly
  adding/removing keys defeats that optimization.
- A **Singleton** in JS is almost free — a module's top-level state is
  evaluated once and cached by the module system, so `export default
  new ConfigStore()` from a single file *is* a singleton without any
  explicit pattern at all. The explicit `getInstance()` class pattern
  above is worth knowing for the interview, but in real JS code the
  module-level singleton is more idiomatic.

## 7. TypeScript's Type System

**"If you declare `type A` twice with different shapes, what does `const x: A` resolve to?"**

```typescript
type A = { size: number };
type A = { name: string };  // Error: Duplicate identifier 'A'.
```

- **This is a trick question** — unlike an `interface` (which supports
  *declaration merging*, where two `interface Foo` declarations combine
  into one with both sets of members), a `type` alias cannot be
  declared twice at all — it's a compile error, not a resolved type.
  The honest answer is naming this distinction directly: "that's
  actually invalid for a `type` alias; if these were both `interface
  A`, the result would merge into `{ size: number; name: string }`."

**"When would you use `ReturnType`? Why do we need generics?"**

```typescript
function createUser(name: string) {
  return { id: crypto.randomUUID(), name, createdAt: new Date() };
}

type User = ReturnType<typeof createUser>; // derives the shape instead of retyping it

function first<T>(items: T[]): T | undefined {
  return items[0]; // works for any T, with the return type still checked
}
```

- `ReturnType<typeof fn>` derives a type from a function's actual
  return value instead of duplicating that shape by hand — useful when
  the function (e.g. an ORM query builder, a factory) is the source of
  truth for a shape, so the type can't drift out of sync with the
  implementation.
- **Generics** exist so a function/type can work across many types
  *without* losing type safety — `first<T>` without a generic would
  either be typed `any` (no safety at all) or need one hand-written
  overload per type used with it.

**"What's a `.d.ts` file for? What's `package-lock.json`?"**

- A `xxxxxxxx.d.ts` file holds *type declarations only*, no runtime
  code — used to describe the shape of a JS library that has no
  built-in TypeScript types (a hand-written or published `@types/`
  package), so TypeScript code can import it with full type-checking
  even though the library itself is plain JS.
- `package-lock.json` pins the *exact* resolved version of every
  dependency (including transitive ones) actually installed, down to
  the specific patch version and its own checksum — `package.json`'s
  version ranges (`^1.2.0`) describe what's *acceptable*;
  `package-lock.json` is what was *actually* installed, which is what
  makes `npm ci` reproducible across machines and CI runs.

---

## Code Samples

No dedicated code samples yet for this section — each snippet above is
short enough to run directly in a browser console or TypeScript
playground (typescriptlang.org/play).
