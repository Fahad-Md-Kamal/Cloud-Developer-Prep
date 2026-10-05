---
title: Cohesion & Coupling
---

# Cohesion & Coupling

The two properties SOLID is actually optimizing for underneath —
**high cohesion** (things that belong together, grouped together) and
**low coupling** (things that don't need each other, kept apart). Most
of [SOLID Principles](solid-principles.md) is these two ideas applied
to specific situations: SRP is a cohesion rule, ISP and DIP are
coupling rules.

## "What's the difference between cohesion and coupling?"

**Answer:**

- **Cohesion** is about what's *inside* one module — how closely
  related its own responsibilities are to each other. High cohesion
  means everything in the class/module exists to serve one clear
  purpose.
- **Coupling** is about the *connections between* modules — how much
  one module needs to know about another's internals to work. Low
  coupling means modules interact through small, stable interfaces
  and don't reach into each other's implementation details.
- The goal is always **high cohesion, low coupling** — not "no
  coupling," since modules that never talk to each other can't form a
  working system. The aim is coupling that's narrow and explicit
  (a well-defined interface) instead of wide and implicit (reaching
  into internals, sharing mutable global state, relying on call
  order).

!!! example "Real-world analogy: a hospital department"
    - **High cohesion** is a cardiology ward where every nurse,
      specialist, and piece of equipment exists to serve one purpose
      — treating heart patients. Nothing in that ward is there for an
      unrelated reason.
    - **Low coupling** is how that ward talks to the pharmacy: through
      a standard prescription form, not by a cardiologist walking
      into the pharmacy and rearranging the shelves themselves. The
      ward depends on "pharmacy fills prescriptions," not on how the
      pharmacy organizes its inventory internally.
    - **Tight coupling** would be the ward only being able to function
      if a specific pharmacist is on shift, because only that person
      knows the undocumented way the ward actually submits requests —
      swap that one pharmacist out and the whole ward's workflow
      breaks.

## The cohesion spectrum (worst to best)

**Answer:**

- **Coincidental** — code grouped together for no reason at all (a
  `utils.py` with unrelated helpers dumped in because they didn't fit
  anywhere else).
- **Logical** — grouped because they're the "same category" of thing
  but don't actually work together (one class with `format_date()`,
  `format_currency()`, `format_phone()` — related only by the word
  "format").
- **Temporal** — grouped because they happen at the same time (an
  `on_startup()` that sets up logging, connects to the DB, and warms a
  cache — unrelated jobs that just all happen to run at boot).
- **Procedural** — grouped because they run in a specific sequence,
  not because they share data or purpose.
- **Communicational** — grouped because they operate on the same data,
  even if their purposes differ.
- **Sequential** — grouped because one's output is the next one's
  input — a real pipeline.
- **Functional** (the target) — every element exists to do exactly one
  well-defined job, and nothing in the module could be removed without
  breaking that one job. This is what `DocumentParser` from
  [SOLID's SRP section](solid-principles.md#1-single-responsibility-principle-srp)
  is aiming for.

## The coupling spectrum (worst to best)

**Answer:**

- **Content coupling** (worst) — one module directly reaches into and
  modifies another's internal state (e.g. mutating another class's
  "private" attributes directly, or monkey-patching its internals).
- **Common coupling** — multiple modules share global/mutable state
  (a shared global variable, a singleton everyone mutates) — a change
  anywhere can silently affect everyone else reading that state.
- **Control coupling** — one module passes a flag that dictates
  *how* another module's internal logic should branch (e.g.
  `process(data, mode="legacy")`), forcing the caller to know about
  the callee's internal branching.
- **Stamp coupling** — passing a whole data structure when only a few
  fields are actually needed, so a change to the structure's shape can
  break a consumer that only cared about two fields of it.
- **Data coupling** (the target) — modules exchange only the plain
  data/parameters they actually need through a clear signature —
  `repo.save(document: Document) -> str` from
  [SOLID's DIP section](solid-principles.md#5-dependency-inversion-principle-dip)
  is this: `DocumentService` passes exactly what `save()` needs and
  nothing about how it's stored.

## "How does this actually show up as a code smell?"

```python
# High coupling, low cohesion: OrderProcessor reaches into
# InventoryService's internals and also handles emailing --
# two unrelated responsibilities, tightly wired to another
# class's implementation details.
class OrderProcessor:
    def __init__(self, inventory_service):
        self.inventory_service = inventory_service

    def process(self, order):
        # reaching into inventory_service's internal dict directly --
        # content coupling: any change to its internal structure
        # breaks this caller
        self.inventory_service._stock[order.sku] -= order.qty

        # an unrelated responsibility bolted onto an order processor --
        # low cohesion
        smtp = smtplib.SMTP("smtp.example.com")
        smtp.sendmail("orders@shop.com", order.customer_email, "Order placed")


# High cohesion, low coupling: OrderProcessor only knows
# Inventory's public interface, and emailing is someone else's job.
class OrderProcessor:
    def __init__(self, inventory: InventoryService, notifier: Notifier):
        self.inventory = inventory
        self.notifier = notifier

    def process(self, order: Order) -> None:
        self.inventory.reserve(order.sku, order.qty)  # public method, not internal dict
        self.notifier.notify(order.customer_email, "Order placed")
```

**Answer:**

- The first version is coupled to `InventoryService`'s *implementation*
  (`._stock` dict) rather than its *interface* — renaming or
  restructuring that dict breaks `OrderProcessor` even though
  inventory logic never conceptually changed.
- It's also low-cohesion — "process an order" and "send an email" are
  two different reasons to change, exactly the SRP smell from
  [SOLID Principles](solid-principles.md#1-single-responsibility-principle-srp).
- The fixed version depends on `inventory.reserve()` — a stable,
  narrow interface — and delegates notification to its own
  collaborator, so each class has one reason to change and no class
  knows more about another than it needs to.

| Pros of high cohesion / low coupling | Cons / Trade-offs |
|---|---|
| A change in one module rarely ripples into others | Takes more upfront design to find the right seams |
| Modules are independently testable — low coupling means fewer things to mock | Too many tiny, narrowly-coupled modules adds navigation overhead |
| Easier to understand a module in isolation — high cohesion means its purpose is obvious | Over-decoupling (e.g. an interface for every single class, "just in case") is itself a cost with no real benefit |

## "Can code be too decoupled?"

**Answer:**

- Yes — coupling isn't free to remove, it's a trade-off against
  indirection. An interface/abstraction layer between two classes that
  will realistically never have a second implementation is pure
  ceremony, the same over-abstraction trap called out in
  [SOLID's DIP trade-offs](solid-principles.md#5-dependency-inversion-principle-dip).
  "Loose coupling" is a tool for isolating things that actually vary
  independently — not a goal to maximize everywhere regardless of
  whether anything in the system will ever change that way.

---

## Code Samples

No dedicated code samples yet for this section — the before/after
example above is meant to be read and reasoned about directly.
