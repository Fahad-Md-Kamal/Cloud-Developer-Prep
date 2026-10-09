---
title: "React & React Native"
---

# React & React Native

Rendering performance, state management, and React Native's
architecture — the recurring themes across two real React/React
Native interview panels.

## 1. Rendering Performance at Scale

**"A screen renders a list of 500 elements and has gotten slow — how would you make it faster?"**

**Answer:**

- **Virtualization** is the actual fix, not "memoize harder" —
  libraries like `react-window`/`react-virtualized` (or
  `FlatList`/`VirtualizedList` in React Native) only render the items
  currently visible in the viewport plus a small buffer, regardless of
  how many items the list logically has. 500 rendered DOM nodes becomes
  roughly 10-20 at any given time.
- **`React.memo`/`useMemo`/`useCallback`** prevent *unnecessary*
  re-renders of items that haven't changed, but don't reduce the
  *initial* render cost of 500 items — they solve a different problem
  (re-render churn) than virtualization solves (initial render + DOM
  size), and interviewers probing this question are checking whether
  the candidate reaches for the right one first.
- Other standard techniques worth naming: code-splitting
  (`React.lazy`) for anything not needed on first paint, and windowed
  pagination (load 50, fetch more on scroll) when virtualization alone
  isn't enough because the *data* itself (not just the render) is too
  large to hold entirely in memory.

**"Fast clicks overwhelm rendering — how do you handle that, and how do you cancel an in-flight fetch?"**

```javascript
function useSearch(query) {
  useEffect(() => {
    const controller = new AbortController();

    fetch(`/api/search?q=${query}`, { signal: controller.signal })
      .then(/* ... */)
      .catch((err) => {
        if (err.name !== "AbortError") throw err; // swallow only the expected cancellation
      });

    return () => controller.abort(); // cancels the in-flight request if query changes again
  }, [query]);
}
```

**Answer:**

- **Debouncing** the input (wait for a pause in typing before firing a
  request) reduces how often work even starts — the UX-facing half of
  the fix.
- **`AbortController`** is the mechanism-level answer — calling
  `.abort()` on an in-flight `fetch` cancels it and rejects its promise
  with an `AbortError`. In a `useEffect`, returning `controller.abort`
  as the cleanup function means every time `query` changes, the
  *previous* request is cancelled before the new one starts — without
  this, a slow first response arriving after a fast second response
  can overwrite correct data with stale data (a classic React race
  condition, structurally the same "two operations racing over shared
  state" hazard as
  [Concurrency & AsyncIO's threading pitfalls](../../backend/python/concurrency-and-asyncio.md#2-what-kinds-of-problems-do-threaded-programs-face-and-how-do-you-overcome-them),
  just at the UI layer instead of the OS thread layer).

## 2. React Fundamentals: Portals and Uncontrolled Components

**Answer:**

- **`createPortal`** renders a component's output into a different DOM
  node than its logical parent in the React tree — the standard use
  case is a modal/tooltip/dropdown that needs to escape a parent's
  `overflow: hidden` or `z-index` stacking context while still
  behaving like a normal React child (event bubbling, context, state
  all work normally despite the different DOM location).
- **Uncontrolled components** let the DOM itself hold the input's
  value (read via a `ref` when needed) instead of React re-rendering on
  every keystroke to hold it in state. Reach for this when the value is
  only needed on submit (a simple form field) and the per-keystroke
  re-render isn't buying anything — a controlled component is still the
  default whenever the value needs to drive other UI in real time
  (live validation, a character counter, a search-as-you-type field).

## 3. State Management: Redux, Immer, and RTK Query

**"How would you choose a state management approach when you don't know what features are coming?"**

**Answer:**

- Start with React's own built-in state (`useState`/`useReducer` +
  Context) and reach for a dedicated library (Redux/Zustand/Jotai)
  only once state is genuinely shared across many unrelated parts of
  the tree — adding Redux before that point is solving a problem the
  app doesn't have yet, the same premature-abstraction judgment as
  [Dependency Inversion's trade-off](../../architecture/solid-principles.md#5-dependency-inversion-principle-dip).
  Under genuine feature uncertainty, this is the safer default
  specifically because it's the easiest to *add* structure to later —
  retrofitting Redux onto an app that didn't need it yet is cheaper
  than unwinding one that was adopted too early.

**"What shouldn't go in Redux? What's Immer for? What's RTK Query for?"**

```javascript
// Immer lets you "mutate" a draft; it produces a new immutable
// state object under the hood -- no manual spread-everything
const reducer = (state, action) => {
  switch (action.type) {
    case "ADD_ITEM":
      return produce(state, (draft) => {
        draft.cart.items.push(action.item); // looks like mutation, isn't
      });
  }
};
```

- **Server-fetched/cacheable data doesn't belong in Redux as
  hand-managed state** — tracking loading/error/caching/refetching for
  every API call by hand in reducers duplicates what a dedicated data
  layer already solves. **RTK Query** (Redux Toolkit's built-in data
  fetching layer) exists precisely for this: it handles caching,
  deduplication of in-flight requests, and automatic refetch
  invalidation — leaving Redux proper for genuinely client-only UI
  state (a modal's open/closed state, form drafts, UI preferences).
- **Immer** solves immutable-update ergonomics — updating a deeply
  nested object immutably by hand means spreading every level
  (`{...state, cart: {...state.cart, items: [...state.cart.items, item]}}`);
  Immer lets code "mutate" a `draft` object directly while actually
  producing a new immutable object underneath, removing the
  boilerplate without giving up the immutability React needs (§4 in
  [JavaScript & TypeScript Fundamentals](javascript-and-typescript-fundamentals.md#4-functional-programming-immutability-and-currying)).

## 4. React Native: The Bridge Architecture

**Answer:**

- React Native's (legacy) architecture runs JavaScript in its own
  thread, completely separate from native UI threads (iOS's main
  thread, Android's UI thread) — the **bridge** is the asynchronous,
  serialized messaging layer between them. A `View` or `Text` component
  rendered in JS doesn't directly manipulate a native UI element; it
  sends a serialized message across the bridge describing what should
  change, and the native side applies it.
- **Why this matters for performance**: bridge messages are
  asynchronous and batched, not instantaneous function calls — an
  animation or gesture handler that needs to respond on every frame
  (60fps, ~16ms budget) can visibly stutter if it's routing through the
  bridge on every frame instead of running natively. This is the direct
  motivation behind libraries like `react-native-reanimated`, which run
  animation logic on the native thread directly, bypassing the bridge
  for the performance-critical path.
- The newer architecture (JSI — JavaScript Interface) replaces the
  serialized bridge with direct, synchronous JS-to-native calls,
  removing this specific bottleneck — worth naming as the direction
  React Native has actually moved, not just the legacy model.

## 5. Testing and Styling

**Answer:**

- **Testing**: component tests (React Testing Library) that query by
  role/text the way a user would, rather than by implementation detail
  (a CSS class, a component's internal state) — the same "test
  behavior, not internals" judgment as backend testing's unit-test
  layer in
  [Clean Code Practices' Testing Strategy](../../architecture/clean-code-practices.md#testing-strategy),
  applied to the DOM instead of a service.
- **Promises vs. `async`/`await`**: `async`/`await` is syntactic sugar
  over Promises — same underlying mechanism, but sequential-looking
  code is dramatically easier to read than a `.then()` chain once more
  than one or two steps are involved, and error handling collapses to
  an ordinary `try/catch` instead of a `.catch()` at the end of a
  chain. Prefer `async`/`await` by default; reach for raw
  `Promise.all`/`Promise.race` when the actual goal is running multiple
  promises concurrently, which `await`ing them one at a time would
  serialize unnecessarily.
- **Tailwind CSS**: utility classes directly in markup instead of
  maintaining separate stylesheet files — the trade-off is verbose
  class lists in exchange for never context-switching between a
  component file and a CSS file, and never accumulating unused CSS
  (Tailwind's build step purges any class never actually used).

---

## Code Samples

No dedicated code samples yet for this section — each snippet above is
short enough to run directly in a sandbox (CodeSandbox/Expo Snack for
the React Native example).
