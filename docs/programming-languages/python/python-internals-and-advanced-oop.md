---
title: "Python Internals & Advanced OOP"
---

# Python Internals & Advanced OOP

Descriptors, metaclasses, MRO, and magic-method correctness — the
"expert Python" layer beyond day-to-day code, and where it actually
shows up in frameworks you already use (Django's ORM, DRF's
serializers). Flagged from the BJIT Senior Python Developer JD's
"Expert knowledge in Python + Django" requirement.

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

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable descriptor/metaclass example added under `code_samples/`.
