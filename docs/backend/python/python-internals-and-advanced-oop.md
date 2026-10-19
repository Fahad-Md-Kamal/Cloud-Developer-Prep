---
title: "Python Internals & Advanced OOP"
---

# Python Internals & Advanced OOP

Descriptors, metaclasses, MRO, and magic-method correctness — the
"expert Python" layer beyond day-to-day code, and where it actually
shows up in frameworks you already use (Django's ORM, DRF's
serializers). Flagged from a Senior Python Developer JD's
"Expert knowledge in Python + Django" requirement. Everything below
builds on two mechanics most OOP tutorials wave past as "just how
classes work" — object creation, and what `self` actually is.

## How an Object Actually Gets Created

`MyClass(args)` doesn't call `__init__` directly — it calls
`type.__call__(MyClass, args)`, which does exactly two things, in order:

1. Calls `MyClass.__new__(MyClass, args)` to actually **allocate** and
   return a new, empty instance.
2. Calls `instance.__init__(args)` on that instance to **populate** it.

This split is why `__new__` returns the object and `__init__` always
returns `None` (implicitly) — by the time `__init__` runs, the object
already exists; it only ever mutates it, never creates it.

!!! success "Why `__new__` exists at all, separate from `__init__`"

    `__new__` is the one to override when something needs to happen
    *before* there's an instance to mutate — returning an already-existing
    instance instead of a new one (the singleton pattern), returning an
    instance of a different subclass entirely, or subclassing an
    immutable built-in (`int`, `str`, `tuple`): their value has to be
    fixed at creation time, since nothing can mutate them afterward in
    `__init__`.

## What `self` Actually Is

`instance.attr` doesn't just check `instance.__dict__` — it checks, in
order: a **data descriptor** (has both `__get__` and `__set__` — e.g.
`property`) anywhere in the type's MRO wins outright, even over the
instance's own `__dict__`; otherwise the instance's own `__dict__` wins;
otherwise a plain class attribute or **non-data descriptor** (`__get__`
only) from the type's MRO is used.

A plain function defined inside a class is itself a non-data
descriptor — every function object has a `__get__`. Accessing
`instance.method` doesn't hand back the raw function; it calls the
function's `__get__(instance, owner)`, which returns a **bound
method** — a small wrapper remembering *both* the function and the
instance, so calling it automatically passes `instance` as the first
argument. `self` isn't the language secretly injecting a hidden
argument — it's the exact same
[descriptor protocol covered next](#1-whats-a-descriptor-and-where-have-you-actually-used-one-without-realizing-it),
just applied to plain functions instead of a custom `__get__`/`__set__`
pair.

<svg viewBox="0 0 900 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of obj.method(x) resolving through the descriptor protocol into a bound method, then unpacking into method(obj, x)" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="10" y="150" width="165" height="110" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="92" y="190" font-size="14" font-weight="600" text-anchor="middle" fill="#2b313b">obj.method</text>
<text x="92" y="210" font-size="12" text-anchor="middle" fill="#5b6472">attribute access</text>
<rect x="195" y="150" width="165" height="110" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<text x="277" y="182" font-size="13" font-weight="600" text-anchor="middle" fill="#1d4a78">function.__get__</text>
<text x="277" y="202" font-size="13" font-weight="600" text-anchor="middle" fill="#1d4a78">(obj, type(obj))</text>
<text x="277" y="222" font-size="11" text-anchor="middle" fill="#3d699a">descriptor fires</text>
<rect x="380" y="150" width="165" height="110" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="462" y="182" font-size="13" font-weight="600" text-anchor="middle" fill="#7a5c14">bound method</text>
<text x="462" y="202" font-size="12" text-anchor="middle" fill="#9a7420">remembers:</text>
<text x="462" y="220" font-size="12" text-anchor="middle" fill="#9a7420">function + obj</text>
<rect x="565" y="150" width="165" height="110" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="647" y="190" font-size="13" font-weight="600" text-anchor="middle" fill="#2b313b">bound_method(x)</text>
<text x="647" y="210" font-size="12" text-anchor="middle" fill="#5b6472">called normally</text>
<rect x="750" y="150" width="140" height="110" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"></rect>
<text x="820" y="182" font-size="13" font-weight="600" text-anchor="middle" fill="#0f6b45">method(obj, x)</text>
<text x="820" y="202" font-size="12" text-anchor="middle" fill="#3d9a73">self = obj,</text>
<text x="820" y="220" font-size="12" text-anchor="middle" fill="#3d9a73">no magic</text>
<circle r="9" fill="#d9822b" cy="205"><animate attributeName="cx" values="92;277;462;647;820;820" keyTimes="0;0.22;0.44;0.66;0.85;1" dur="12s" repeatCount="indefinite"></animate></circle>
<text x="450" y="340" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.2;0.24;1" dur="12s" repeatCount="indefinite"></animate>obj.method is attribute access — Python finds a function on the class.</text>
<text x="450" y="340" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.22;0.26;0.42;0.46;1" dur="12s" repeatCount="indefinite"></animate>The function is a descriptor — its __get__ runs automatically.</text>
<text x="450" y="340" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.44;0.48;0.64;0.68;1" dur="12s" repeatCount="indefinite"></animate>__get__ returns a bound method — a package of (function, obj).</text>
<text x="450" y="340" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.68;0.72;1" dur="12s" repeatCount="indefinite"></animate>Calling it runs method(obj, x) — self was always just obj, passed normally.</text>
</svg>

## 1. "What's a descriptor, and where have you actually used one without realizing it?"

```python
class PositiveNumber:
    def __set_name__(self, owner, name):
        self._name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self._name)

    def __set__(self, instance, value):
        if value < 0:
            raise ValueError(f"{self._name} must be positive")
        setattr(instance, self._name, value)

class Product:
    price = PositiveNumber()

    def __init__(self, price):
        self.price = price  # goes through PositiveNumber.__set__
```

**Answer:**

- A descriptor is any object implementing `__get__`, `__set__`, or
  `__delete__` and assigned as a class attribute — Python routes
  attribute access on instances of that class through those methods.
- `property` is the built-in descriptor most people already know; a
  custom descriptor is the same mechanism, reusable across multiple
  attributes/classes instead of one `property` per attribute.
- You've used one without realizing it: **Django model fields**
  (`models.CharField()`) and **DRF serializer fields** are both
  descriptors — that's literally how `instance.some_field` reads the
  validated/converted value instead of the raw field-definition
  object.
- Same mechanism behind `@staticmethod`, `@classmethod`, and bound-method
  lookup itself (functions are descriptors — that's how `self` gets
  bound automatically).

**Likely follow-up — "why would you write one yourself instead of just using `property`?"**

- `property` is one-off — tied to a single class, redefined per
  attribute.
- A descriptor is reusable validation/transformation logic shared
  across many attributes or classes without repeating the same
  `@property`/`@x.setter` pair each time.
- Worth it once the same validation rule (e.g. "must be positive,"
  "must be a valid slug") applies to several fields across a codebase —
  exactly the pattern Django/DRF fields are built on.

| Pros | Cons / Trade-offs |
|---|---|
| Reusable validation/transformation logic across many attributes/classes | Non-obvious to someone unfamiliar with the descriptor protocol — "spooky action" on attribute access |
| The actual mechanism behind Django/DRF fields, `property`, `@classmethod` | Debugging requires knowing to look at the class, not just the instance |
| Centralizes a rule in one place instead of repeating it per `@property` | Overkill for a single one-off attribute — plain `property` is simpler |

## 2. "What's a metaclass, and when would you actually reach for one?"

```python
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class ConnectionPool(metaclass=SingletonMeta):
    def __init__(self):
        self.connections = []
```

**Answer:**

- A metaclass is "the class of a class" — `type` is the default
  metaclass every class is an instance of; a custom metaclass controls
  *how classes themselves get created*, not how instances behave.
- Common real use: Django's `ModelBase` metaclass is what collects
  every `models.CharField()` etc. declared on a model into its field
  registry behind the scenes — it intercepts class creation to
  register fields.
- Most "I need a metaclass" cases are actually better solved by
  `__init_subclass__` (simpler, added specifically to cover the common
  metaclass use cases) or a class decorator.
- Reach for an actual metaclass only when class *creation itself* needs
  controlling — which base classes are allowed, auto-registering every
  subclass in a registry, enforcing that certain methods are
  overridden — not just adding behavior to instances.

**Likely follow-up — "give a case where `__init_subclass__` isn't enough and you need a real metaclass."**

- Needing to intercept or modify the class's namespace *before* the
  class object is created (metaclasses can rewrite the attribute dict
  via `__prepare__`/`__new__`) — `__init_subclass__` only runs *after*
  the class already exists.
- Needing to combine behavior across multiple unrelated base classes'
  metaclasses (metaclass conflicts) — `__init_subclass__` doesn't need
  to solve this since it isn't itself a metaclass.

| Pros | Cons / Trade-offs |
|---|---|
| Full control over class creation — registration, validation, field collection | Steepest learning curve of any Python OOP feature — genuinely confuses most readers |
| The real mechanism behind Django's ORM model registration | `__init_subclass__` covers most real use cases with far less complexity |
| Can enforce structural rules across an entire class hierarchy at definition time | Metaclass conflicts between unrelated base classes are a real, annoying failure mode |

## 3. "Explain MRO — how does Python resolve a method call under multiple inheritance?"

```python
class A:
    def greet(self): return "A"

class B(A):
    def greet(self): return "B"

class C(A):
    def greet(self): return "C"

class D(B, C):
    pass

D().greet()   # "B"
D.__mro__     # (D, B, C, A, object)
```

**Answer:**

- Python uses **C3 linearization** to compute a single, consistent
  method resolution order for a class with multiple bases —
  `D.__mro__` shows the exact lookup order.
- The rule that matters in practice: a subclass always comes before
  its parents, and left-to-right order in the class definition
  (`class D(B, C)`) is preserved — `B` is checked before `C` since `B`
  is listed first.
- This is what makes `super()` well-defined even with multiple
  inheritance — `super()` doesn't mean "my direct parent," it means
  "the next class in the MRO," which is why cooperative multiple
  inheritance (every class calling `super().__init__()`) works
  correctly instead of silently skipping a class.

**Likely follow-up — "where does this actually bite people in real code?"**

- Django's class-based views and mixins — mixin order
  (`class MyView(LoginRequiredMixin, ListView)`) matters precisely
  because of MRO; getting it backwards silently changes which
  `get()`/`dispatch()` runs first.
- The "diamond problem" (two parents share a common ancestor) is
  exactly what C3 linearization exists to resolve deterministically —
  without it, which `A` a `D(B, C)` instance "really" uses would be
  ambiguous.

| Pros | Cons / Trade-offs |
|---|---|
| Deterministic, well-defined lookup order even with complex hierarchies | Multiple inheritance is genuinely harder to reason about than single inheritance |
| `super()` chains work correctly across mixins when every class cooperates | One class skipping `super().__init__()` breaks the whole cooperative chain silently |
| Explains real framework behavior (Django mixin ordering) precisely | MRO conflicts (`TypeError: Cannot create a consistent MRO`) are confusing to debug the first time |

## 4. "What breaks if you implement `__eq__` without `__hash__`, or implement them inconsistently?"

```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __eq__(self, other):
        return isinstance(other, Point) and (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        return hash((self.x, self.y))
```

**Answer:**

- Defining `__eq__` without `__hash__` makes instances **unhashable**
  by default — Python sets `__hash__` to `None` automatically once
  `__eq__` is overridden, so the object can no longer go in a `set` or
  be used as a `dict` key.
- The hash contract: **if two objects are equal, they must have the
  same hash.** Breaking this silently corrupts sets/dicts — two
  "equal" objects can end up treated as different keys, or a lookup
  that should hit misses entirely.
- Practical rule: hash only on the same fields used in `__eq__`, and
  only on fields that don't change after the object is created —
  hashing a mutable field that later changes means the object's hash
  bucket no longer matches where it actually lives in the set/dict.

**Likely follow-up — "why does this matter for a Django/DRF codebase specifically?"**

- Putting model instances or DTOs in a `set()` for deduplication, or
  using them as dict keys for a lookup cache, silently breaks if
  `__eq__`/`__hash__` aren't implemented consistently — an easy
  mistake when a custom `__eq__` gets added for test assertions later
  and nobody thinks about hashing.
- Django model instances already define `__eq__`/`__hash__` based on
  primary key — a common bug is overriding `__eq__` on a subclass for
  a "compare by business logic" reason and accidentally breaking the
  inherited hash behavior everywhere else the model is used in a set.

| Pros / Correct pattern | Cons / Failure mode |
|---|---|
| Hash only immutable fields also used in `__eq__` | Hashing a mutable field means the object "moves" in its hash bucket after mutation |
| Let Python auto-disable `__hash__` when only `__eq__` is needed (no set/dict usage) | Manually keeping `__hash__` while changing `__eq__`'s logic is easy to make inconsistent |
| Match `__eq__`'s type check (`isinstance`) so it's symmetric | An asymmetric `__eq__` (works one direction, not the other) silently breaks sorting/dedup |

## 5. "Explain Python's memory model — how does it actually know when to free an object?"

**Answer:**

- CPython's primary mechanism is **reference counting**: every object
  carries a count of how many references point to it. `x = Document()`
  sets the count to 1; `y = x` bumps it to 2; when a reference goes out
  of scope or is reassigned, the count drops. The moment it hits `0`,
  the object is freed **immediately** — not on some later GC pass.
- This is why Python's memory reclamation feels more deterministic
  than Java's or Go's garbage-collected heaps for most objects — a
  local variable going out of scope at the end of a function typically
  frees its object right then, not at some unpredictable future pause.
- **Reference counting alone can't free a cycle** — two objects that
  reference each other (`a.child = b; b.parent = a`) never hit a
  refcount of `0` even after nothing else references either one. For
  this, CPython runs a separate **cyclic garbage collector**
  (the `gc` module) periodically, which specifically looks for and
  collects groups of objects that are unreachable from outside the
  group even though their internal refcounts are non-zero.
- `sys.getrefcount(obj)` shows an object's current reference count (it
  reports one more than you'd expect, since passing `obj` to
  `getrefcount` itself creates a temporary reference).
- **Small objects don't even call `malloc()` per allocation.** CPython's
  `pymalloc` pre-allocates large chunks ("arenas"), carves them into
  fixed-size "pools," and reuses freed slots — objects under ~512 bytes
  (most Python objects) come from this pool instead of a fresh OS
  allocation each time. This is the real reason object creation is fast
  despite being garbage collected.

### The cyclic GC in depth: generations, thresholds, and how it actually finds a cycle

**Answer:**

- The core idea: the cyclic GC exists for exactly one job — catching
  reference cycles reference counting can't free — and it's
  **generational** because most objects die young, so scanning
  brand-new objects often and ancient ones rarely is far cheaper than
  scanning everything equally.
- **Three generations** — gen 0 (newest), gen 1, gen 2 (oldest,
  longest-lived). A new object starts in gen 0; surviving a gen-0
  collection promotes it to gen 1, then eventually gen 2.
- **Thresholds decide when each generation runs** —
  `gc.get_threshold()` returns something like `(700, 10, 10)`: gen 0 is
  scanned every 700 net allocations; gen 1 every 10 gen-0 collections;
  gen 2 every 10 gen-1 collections. Older generations run far less
  often, since surviving this long makes an object statistically
  unlikely to be garbage.
- **How it actually detects a cycle ("trial deletion"):** for a
  candidate set of objects, it computes how many references *into*
  that set come from *outside* it — by temporarily subtracting every
  internal (within-the-set) reference from each object's refcount. If
  the remaining external count is 0 for the whole group, the entire
  group is unreachable garbage, even though each object's real refcount
  is still non-zero. It's answering "is anything outside this group
  keeping it alive," not inspecting any single object in isolation.

```python
import gc

gc.get_threshold()   # e.g. (700, 10, 10) -- gen0, gen1, gen2 collection frequency
gc.collect()         # force a full collection on demand
gc.disable()         # turns off the CYCLIC collector only -- refcounting still runs
gc.freeze()          # treat everything currently alive as permanent, stop re-scanning it
```

- `gc.disable()` is sometimes used for short-lived scripts/CLI tools —
  if the process exits soon anyway, paying cycle-collection overhead
  during its lifetime buys nothing.
- `gc.freeze()` is for long-running services: call it once after
  startup, once large static structures are loaded, so every future
  collection has a smaller pool of objects to re-examine instead of
  re-scanning data that was never going away.
- **Interview trap to avoid:** the GIL and the GC are two unrelated
  locks on two unrelated things — the GIL protects bytecode execution
  ([Threading & the GIL](threading-and-the-gil.md)); the cyclic GC
  is purely about memory, and runs independently of it.

### Weak references: holding a reference that doesn't count

```python
import weakref

class Node:
    def __init__(self, name):
        self.name = name

parent = Node("parent")
child = Node("child")
child.parent_ref = weakref.ref(parent)  # doesn't increment parent's refcount

print(child.parent_ref())  # call it to get the actual object (or None if freed)
```

- A `weakref.ref` points at an object **without** incrementing its
  reference count — the referenced object can still be freed as if the
  weak reference didn't exist. Calling the weak reference returns the
  live object, or `None` if it's already been garbage collected.
- **Two real uses this solves:**
    - **Breaking reference cycles deliberately** — a parent/child
      relationship where the child needs to point back to its parent
      (`child.parent_ref`) without that back-pointer keeping the
      parent alive forever, or forcing it to wait for a cyclic-GC pass
      instead of being freed immediately via refcounting.
    - **Caches that shouldn't keep entries alive** — `weakref.WeakValueDictionary`
      (or `WeakKeyDictionary`) holds entries only as long as something
      *else* in the program still references the value. The moment the
      real owner drops its reference, the cache entry disappears on
      its own — useful for an object-identity cache that must never be
      the reason an object stays in memory.
- **Interview point:** this is the mechanism-level answer to "what's
  the difference between a cache that leaks memory and one that
  doesn't" — a plain `dict` cache (or `functools.lru_cache` from
  [Memory & Caching §2](memory-and-caching.md#2-implement-an-lru-cache-what-data-structures-does-it-need-and-why-both))
  holds a real, counted reference and keeps every cached object alive
  until explicitly evicted; a `WeakValueDictionary` never does that by
  itself.

## 6. "How is a dict (or a hash map in any language) actually structured?"

**Answer:**

- The core idea, true in any language: a hash map is an array, and
  `hash(key) % array_size` picks which slot to check — everything else
  is just "what happens when two keys land on the same slot."
- **Two real collision-resolution strategies:**
    - **Chaining** (Java's `HashMap`) — each slot holds a linked list
      (or a small tree, in modern Java, once a bucket gets large) of
      every key that hashed there.
    - **Open addressing** (Python's `dict`) — no lists. On a collision,
      probe a different slot using a fixed sequence until an empty one
      is found — no per-entry pointer overhead for a list node.
- **Python's actual structure is two arrays, not one** (since 3.6,
  guaranteed by the language spec since 3.7) — this is the detail that
  explains why `dict` preserves insertion order:
    - A **sparse index table** mapping `hash → position`.
    - A **dense array** of `(hash, key, value)` entries, in the exact
      order they were inserted.
    - A lookup hashes the key, finds its position via the sparse
      table, then reads that slot from the dense array. Iteration just
      walks the dense array in order — insertion order falls out for
      free, and the sparse table only needs to store small integers,
      not full entries, which is also why this redesign (the "compact
      dict") cut `dict` memory use measurably.
- **Resizing** — once the table is about 2/3 full (its load factor), a
  larger array is allocated and every entry is rehashed into it. This
  is *why* a hash map lookup is "usually O(1)" rather than a hard
  guarantee on every single call — the occasional resize is itself
  O(n), amortized across all the O(1) operations between resizes.

```python
# A hash collision doesn't change correctness, only speed -- both keys
# still resolve to their own value via probing, just with extra steps.
d = {}
d["a"] = 1   # hash("a") -> slot N (say)
d["b"] = 2   # hash("b") -> also slot N -- probe to the next open slot instead
```

**Interview point:** "is a dict lookup always O(1)?" is a trap —
amortized average-case O(1), assuming a reasonable hash function
spreads keys evenly. A pathological hash function (or a type with a
broken `__hash__`) that sends every key to the same slot degrades
every lookup to O(n), scanning the whole probe chain.

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable descriptor/metaclass example added under `code_samples/`.
