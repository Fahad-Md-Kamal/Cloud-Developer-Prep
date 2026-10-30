---
title: Rust Guru Question Bank
---

# Rust Guru Question Bank

This page is a drill sheet: **about 120 hard questions with strong
answers**, grouped by topic. Each answer is short on purpose. Its last line
points to the page section that teaches the idea, so a wrong or shaky answer
tells you exactly what to re-read. Near the end are **predict-the-output**,
**predict-the-compile-error**, and **design** questions, because "explain it"
and "do it" are different skills.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Predict-the-output
    answers come from running `code_samples/rust/examples/guru_quiz.rs` on
    1.99.1 (a 64-bit machine). Predict-the-error items reuse files in
    `code_samples/rust/compile_fail/`, and the error codes were read from the
    real compiler.

## 1. "How should I use this question bank?"

**Answer:**

- **Core idea:** answer **out loud, before reading the answer.** Reading
  answers feels like learning and is not.
- Score each question: **2** = full answer with the "why", **1** = right
  idea, missing the reason, **0** = guessed. Re-read the linked section for
  every 0 and 1, then retry in a week.
- A "guru" answer has three parts: the **rule**, the **reason** (what goes
  wrong without it), and the **escape hatch** (what you do when the rule
  gets in your way).
- Groups 2 to 8 are concepts, group 9 to 11 are practice, group 12 is how to
  talk about this in an interview.

## 2. Ownership and borrowing

**Q1. "What does `let b = a;` do when `a` is a `String`, and when it is an `i32`?"**

- `String` is **moved**: `b` owns the heap buffer and `a` can no longer be used.
- `i32` is `Copy`: both stay valid, because copying the bits is the whole copy.
- Reason: a move prevents two owners from freeing the same buffer.
- [Ownership & Borrowing §2](../foundations/rust-ownership-and-borrowing.md#2-what-exactly-happens-when-a-value-is-moved)

**Q2. "What is the difference between `Copy` and `Clone`?"**

- `Copy` is a marker for types where a plain bit copy is a correct duplicate.
  It happens **implicitly** on every use and you cannot customize it.
- `Clone` is an explicit `.clone()` that may allocate or run arbitrary code.
- Every `Copy` type is also `Clone`; the reverse is false (`String`).
- [Ownership & Borrowing §3](../foundations/rust-ownership-and-borrowing.md#3-what-is-the-difference-between-copy-and-clone)

**Q3. "Can a type be both `Copy` and have a `Drop` implementation?"**

- No. The compiler rejects it, because implicit copies would run the
  destructor twice for one resource.
- Corollary: types that own heap memory or handles are never `Copy`.
- [Ownership & Borrowing §3](../foundations/rust-ownership-and-borrowing.md#3-what-is-the-difference-between-copy-and-clone)

**Q4. "In what order are locals, struct fields, and temporaries dropped?"**

- **Locals** drop in **reverse** declaration order.
- **Struct fields** drop in **declaration** order, after the struct's own
  `Drop::drop` runs. `Vec` elements drop front to back.
- A **temporary** drops at the end of its statement; in edition 2024, temporaries
  in a block's **tail expression** drop before the block's locals.
- `let _ = value;` does **not** bind, so the value drops immediately. `let _x`
  keeps it alive to the end of scope. See the predict-the-output item in
  [§10](#10-predict-the-output).
- [Ownership & Borrowing §4](../foundations/rust-ownership-and-borrowing.md#4-when-exactly-are-values-dropped-and-in-what-order)

**Q5. "Why can't you have two `&mut` references to the same value?"**

- The rule is **aliasing XOR mutability**: many readers, or one writer.
- Without it, one reference could invalidate another (a `push` that reallocates
  a `Vec` while someone holds a pointer into it), and two threads could race.
- It also lets the compiler assume no other pointer changes the data, which
  allows optimizations (like C's `restrict`, applied everywhere).
- [Ownership & Borrowing §5](../foundations/rust-ownership-and-borrowing.md#5-what-are-the-rules-of-borrowing-and-why-do-they-exist)

**Q6. "What is NLL (non-lexical lifetimes)?"**

- A borrow lasts until its **last use**, not until the end of the block.
- This is why `let r = &mut v; r.push(1); v.push(2);` compiles: `r` is no
  longer used when `v` is touched.
- It is a property of the borrow checker working on the control-flow graph
  (MIR), not of the syntax. See [How rustc Works](../performance-and-internals/rustc-how-the-compiler-works.md).
- [Ownership & Borrowing §6](../foundations/rust-ownership-and-borrowing.md#6-what-does-the-borrow-checker-actually-check-how-do-you-read-its-errors)

**Q7. "Why does `let first = &v[0]; v.push(4); println!(\"{first}\");` fail?"**

- `push` may **reallocate** the buffer, so `first` could point at freed memory.
  The compiler reports `E0502`: cannot borrow `v` as mutable because it is also
  borrowed as immutable.
- Fixes: copy the value out (`let first = v[0];`), finish using `first`
  before pushing, or use an index instead of a reference.
- [Ownership & Borrowing §7](../foundations/rust-ownership-and-borrowing.md#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it)

**Q8. "How do you take a `String` out of a `&mut Option<String>` or a `&mut Vec<String>`?"**

- You cannot move out of a borrow (`E0507`), but you can **swap something in**:
  `Option::take()`, `std::mem::take(&mut s)`, `std::mem::replace`, or
  `Vec::swap_remove`.
- Or clone, or restructure to own the value.
- [Ownership & Borrowing §7](../foundations/rust-ownership-and-borrowing.md#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it)

**Q9. "Is `std::mem::forget` unsafe? Is leaking memory a safety violation?"**

- `forget` is **safe**. Leaking is memory-safe (the memory is just never freed).
- Therefore **safe code must not rely on `Drop` running** for soundness. This
  is why scoped threads use a closure-based API (`thread::scope`) instead of a
  guard object whose `Drop` joins the threads.
- [Smart Pointers §3](../foundations/rust-smart-pointers.md#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for)

**Q10. "Does ownership mean Rust always moves, and so copies memory?"**

- A move is a **bitwise copy of the value** (for a `Vec`, 24 bytes of pointer,
  capacity and length), not of the heap data. Optimizers often remove even that.
- Large inline values (a big array) do get copied; `Box` them or pass by
  reference.
- [Ownership & Borrowing §2](../foundations/rust-ownership-and-borrowing.md#2-what-exactly-happens-when-a-value-is-moved)

## 3. Lifetimes

**Q11. "What does a lifetime annotation actually do?"**

- It **changes nothing at run time** and does not extend any value's life.
  It is a **name for a relationship** ("the result lives no longer than `a`")
  so the compiler can check callers.
- [Lifetimes §1](../foundations/rust-lifetimes.md#1-what-is-a-lifetime-really)

**Q12. "What are the lifetime elision rules?"**

- Each reference input gets its own lifetime.
- If there is exactly one input lifetime, the output gets it.
- If one input is `&self` or `&mut self`, the output gets the lifetime of `self`.
- Otherwise you must write them (`E0106`, missing lifetime specifier).
- [Lifetimes §3](../foundations/rust-lifetimes.md#3-what-are-the-elision-rules-and-why-can-you-usually-skip-lifetimes)

**Q13. "`fn longest(a: &str, b: &str) -> &str` fails. Why, and what is the fix?"**

- Two inputs, no `self`: the compiler cannot know which one the output borrows.
- Fix: `fn longest<'a>(a: &'a str, b: &'a str) -> &'a str`. The result is valid only
  as long as **both** inputs are.
- [Lifetimes §2](../foundations/rust-lifetimes.md#2-when-do-you-have-to-write-a-lifetime)

**Q14. "What are the two meanings of `'static`?"**

- `&'static T`: a reference that is valid for the whole program (string literals,
  leaked data).
- `T: 'static` as a **bound**: `T` contains no non-`'static` borrows. An owned
  `String` satisfies it.
- `thread::spawn` requires `'static` for this reason: the new thread may
  outlive the caller's locals.
- [Lifetimes §5](../foundations/rust-lifetimes.md#5-what-does-static-mean-it-has-two-meanings)

**Q15. "Is `T: 'static` the same as 'lives forever'?"**

- No. It means "**could** live forever because it holds no short borrows".
  A `String` can be dropped any time and is still `'static`.
- [Lifetimes §5](../foundations/rust-lifetimes.md#5-what-does-static-mean-it-has-two-meanings)

**Q16. "What is a higher-ranked trait bound (`for<'a>`)?"**

- "For **every** lifetime `'a`." `F: for<'a> Fn(&'a str) -> &'a str` means the
  closure works for a reference of any lifetime chosen by the caller of `F`.
- `F: Fn(&str) -> &str` is sugar for exactly that, so you rarely write it out.
- [Lifetimes §7](../foundations/rust-lifetimes.md#7-what-is-a-higher-ranked-bound-fora)

**Q17. "Why can't a struct hold a reference to its own field?"**

- If the struct moves, the reference would point at the old address. Safe Rust
  cannot prove it will not move.
- Options: store **indices** or offsets, use `Rc`/`Arc`, split into two
  structs, or use `Pin` with `unsafe` (this is what async state machines do).
- [Lifetimes §4](../foundations/rust-lifetimes.md#4-how-do-structs-hold-references-and-what-is-the-mut-self-trap)

**Q18. "What changed for `impl Trait` in return position in the 2024 edition?"**

- It now captures **all** in-scope lifetimes by default. Before, only type
  parameters were captured and you added `+ '_` or `+ 'a` by hand.
- Opt out with `use<..>`, for example `impl Iterator<Item = u32> + use<>`.
- [Lifetimes §8](../foundations/rust-lifetimes.md#8-how-do-lifetimes-interact-with-impl-trait-and-what-changed-in-2024)

**Q19. "When should you avoid lifetime parameters altogether?"**

- When the struct would be long-lived, stored in collections, or sent across
  threads. Own the data (`String`, `Arc<str>`) instead.
- Use borrowing structs for short, local views (parsers, iterators).
- [Lifetimes §10](../foundations/rust-lifetimes.md#10-when-should-you-avoid-lifetime-parameters-entirely)

## 4. Types, patterns, and errors

**Q20. "What happens on integer overflow?"**

- In a **debug** build `+` panics. In a **release** build it wraps (two's
  complement) by default. Both are **defined behavior**, never undefined.
- Pick the behavior you mean: `checked_add`, `wrapping_add`, `saturating_add`,
  `overflowing_add`, and `strict_add` (always panics, 1.91).
- Change the profile with `overflow-checks = true`.
- [Types, Enums & Patterns §1](../foundations/rust-types-enums-and-patterns.md#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose)

**Q21. "What does `as` do for numeric casts?"**

- Integer to a smaller integer **truncates**. Float to integer **saturates**,
  and `NaN` becomes 0. Signed to unsigned reinterprets the bits.
- `as` never fails, which is also its danger: prefer `try_from` / `into` where
  loss would be a bug.
- [Types, Enums & Patterns §1](../foundations/rust-types-enums-and-patterns.md#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose)

**Q22. "Why is `Option<&T>` the same size as `&T`?"**

- A reference can never be null, so the all-zero bit pattern is free to mean
  `None`. This is the **niche** optimization; the same applies to `Box`, `Rc`,
  `NonZero*`, and `Vec`.
- [Memory Layout & DSTs §6](../advanced-language/rust-memory-layout-and-dsts.md#6-what-is-niche-optimization-and-why-is-optionboxt-free)

**Q23. "What does `#[non_exhaustive]` do, and why use it?"**

- On an enum or struct from **another crate**, callers must include a `_ =>`
  arm (or `..`) and cannot construct the type with a struct literal.
- It lets you add variants or fields later without a **semver break**.
- [Architecture & API Design §5](../production/rust-project-architecture-and-api-design.md#5-what-changes-break-my-users-how-do-i-keep-semver)

**Q24. "What is `let ... else`?"**

- `let Some(x) = opt else { return; };` binds on success and **must diverge**
  (return, break, panic) on failure. It keeps the happy path unindented.
- [Types, Enums & Patterns](../foundations/rust-types-enums-and-patterns.md)

**Q25. "What are let chains and `if let` guards, and which versions?"**

- Let chains (`if let A = x && cond && let B = y`) are stable since **1.88** in
  the **2024 edition** only. `if let` guards in `match` arms are stable since
  **1.95**.
- [Modern Rust §2](../mastery/modern-rust-2024-to-1-99.md#2-what-new-control-flow-and-pattern-features-exist)

**Q26. "How does `?` work?"**

- On `Err(e)` it returns early with `From::from(e)`, so the error type is
  converted. On `Option` it returns `None`. The function's return type must
  fit (`Result` or `Option`).
- `main` can return `Result<(), E>` where `E: Debug`.
- [Error Handling §2](../foundations/rust-error-handling.md#2-how-does-the-operator-work)

**Q27. "`thiserror` or `anyhow`?"**

- `thiserror` for **libraries**: a precise `enum` callers can match on.
- `anyhow` for **applications**: one opaque error type with `.context(..)`
  messages, for reporting and logging, not matching.
- [Error Handling §5](../foundations/rust-error-handling.md#5-when-do-you-use-thiserror-and-when-anyhow)

**Q28. "When is a panic the right choice?"**

- For **bugs** (a broken invariant, an impossible state) and in tests and
  examples. Not for expected failures like bad input or a missing file.
- `unwrap()` is fine when you can prove it cannot fail; prefer
  `expect("why it cannot fail")`.
- [Error Handling §6](../foundations/rust-error-handling.md#6-when-is-a-panic-right-and-what-happens-when-one-occurs)

**Q29. "What does `panic = \"abort\"` change?"**

- No unwinding: the process aborts at the panic. The binary is smaller and
  slightly faster, but `catch_unwind` cannot catch anything and destructors do
  not run during the panic.
- Unwinding across an `extern "C"` boundary is **not allowed**; see Q66.
- [Toolchain & Cargo §4](../foundations/rust-toolchain-and-cargo.md#4-what-are-profiles-and-what-do-dev-and-release-really-change)

**Q30. "Why make illegal states unrepresentable? Give an example."**

- Use types so wrong combinations do not compile: an `enum` with data
  instead of a struct with a `status` string plus optional fields, or a
  **typestate** (`Door<Open>` vs `Door<Closed>`).
- [Types, Enums & Patterns §7](../foundations/rust-types-enums-and-patterns.md#7-how-do-you-design-types-so-wrong-states-cannot-exist)

## 5. Traits and generics

**Q31. "Static versus dynamic dispatch: what is the trade-off?"**

- Generics (`T: Trait`) are **monomorphized**: one copy per type, direct calls,
  inlining, bigger binary, slower compile.
- `dyn Trait` uses a **vtable**: one copy, an indirect call, no inlining,
  heterogeneous collections.
- Rule of thumb: generics by default, `dyn` at **boundaries** where the type
  varies at run time or code size matters.
- [Traits & Generics §2](../foundations/rust-traits-and-generics.md#2-what-is-the-difference-between-generics-and-dyn-trait)

**Q32. "What makes a trait dyn compatible?"**

- It must not require `Self: Sized`, return `Self`, or have generic methods
  (unless those methods say `where Self: Sized`), and its methods need a
  receiver. `async fn` and return-position `impl Trait` in a trait also make it
  not dyn compatible. The error is `E0038`.
- [Traits & Generics §3](../foundations/rust-traits-and-generics.md#3-what-does-it-mean-that-a-trait-is-dyn-compatible)

**Q33. "What is the orphan rule, and how do you work around it?"**

- You may implement a trait for a type only if the **trait or the type is local
  to your crate** (`E0117` otherwise). This keeps two crates from implementing
  the same trait for the same type.
- Workaround: a **newtype** (`struct Wrapper(Vec<String>)`) and implement the
  trait for it.
- [Traits & Generics §1](../foundations/rust-traits-and-generics.md#1-what-is-a-trait-and-how-do-you-use-one)

**Q34. "Associated type or generic parameter?"**

- Use an **associated type** when there is exactly **one** sensible choice per
  implementing type (`Iterator::Item`). Use a **generic parameter** when one
  type can implement the trait several ways (`From<A>`, `From<B>`).
- [Traits & Generics §1](../foundations/rust-traits-and-generics.md#1-what-is-a-trait-and-how-do-you-use-one)

**Q35. "What is a blanket impl, and why can two overlap?"**

- `impl<T: Display> MyTrait for T` covers every `Display` type. Another impl of
  `MyTrait` for a concrete type that is also `Display` **overlaps** and is
  rejected (`E0119`), because stable Rust has no specialization.
- [Advanced Traits §8](../advanced-language/rust-advanced-traits-and-type-level-design.md#8-what-are-supertraits-blanket-impls-and-marker-traits)

**Q36. "`impl Trait` in argument position, return position, and `dyn Trait`?"**

- Argument: sugar for a generic. Return: **one** hidden concrete type chosen by
  the function. `dyn Trait` (boxed): any number of types at run time.
- A function returning `if c { A } else { B }` with `impl Trait` fails, because
  that is two types; box it as `Box<dyn Trait>`.
- [Traits & Generics §2](../foundations/rust-traits-and-generics.md#2-what-is-the-difference-between-generics-and-dyn-trait)

**Q37. "What is `Sized`, and what does `?Sized` mean?"**

- `Sized` types have a size known at compile time; every generic parameter has an
  implicit `T: Sized` bound. `T: ?Sized` opts out, which lets `T` be `str`,
  `[U]`, or `dyn Trait` (behind a pointer).
- [Memory Layout & DSTs §8](../advanced-language/rust-memory-layout-and-dsts.md#8-what-does-sized-mean-and-what-is-sized)

**Q38. "What is trait object upcasting?"**

- Since **1.86**, `&dyn Sub` or `Box<dyn Sub>` converts to its supertrait
  object (`dyn Super`) with no helper method.
- [Modern Rust §3](../mastery/modern-rust-2024-to-1-99.md#3-what-changed-for-async-closures-and-traits)

**Q39. "Why isn't `f64` `Ord`, and what do you do to sort floats?"**

- `NaN != NaN`, so `==` is not reflexive (`PartialEq` only) and `<` has no total
  order (`PartialOrd` only). `sort()` needs `Ord`.
- Use `sort_by(|a, b| a.total_cmp(b))`, or wrap in an ordered-float type.
- [Traits & Generics §5](../foundations/rust-traits-and-generics.md#5-what-are-the-traits-you-must-know-by-heart)

**Q40. "What is monomorphization, and what does it cost?"**

- The compiler generates a separate copy of a generic function for each concrete
  type. Result: zero run-time cost, but longer **compile time** and bigger
  binaries. Reduce it with `dyn`, or by moving non-generic work into an inner
  function.
- [How rustc Works §5](../performance-and-internals/rustc-how-the-compiler-works.md#5-what-is-monomorphization-and-what-does-it-cost)

**Q41. "What contract do `Hash` and `Eq` have?"**

- If `a == b` then `hash(a) == hash(b)`. Break it and a `HashMap` silently loses
  keys. Deriving both together keeps them consistent.
- [Collections & Strings §4](../foundations/rust-collections-and-strings.md#4-how-does-hashmap-work-and-what-should-you-know-before-using-it)

## 6. Collections, iterators, closures, smart pointers

**Q42. "How does `Vec` grow, and how do you avoid repeated reallocation?"**

- It keeps a pointer, a length, and a capacity. When full it allocates a larger
  buffer **geometrically** and moves items (amortized O(1) `push`). The exact
  factor is an implementation detail.
- Use `Vec::with_capacity(n)` or `reserve` when you know the size.
- [Collections & Strings §2](../foundations/rust-collections-and-strings.md#2-how-does-vec-work-inside-and-what-are-vec-array-and-slice)

**Q43. "Why can't you index a `String` with `s[0]`?"**

- A `String` is UTF-8 **bytes**; one character can take 1 to 4 bytes, so an
  integer index is ambiguous and O(n) if it meant "character".
- Use `.chars()`, `.char_indices()`, byte-range slices (they **panic** if not on
  a boundary), or `get(range)` which returns `None`.
- [Collections & Strings §3](../foundations/rust-collections-and-strings.md#3-how-do-strings-work-why-cant-you-index-them)

**Q44. "How does `HashMap` hash by default, and why does iteration order vary?"**

- It uses **SipHash** with a random key per map, to resist hash-flooding
  attacks. The random key also randomizes iteration order.
- For speed with trusted keys use a faster hasher (`ahash`, `rustc-hash`). For
  stable order use `BTreeMap` or `IndexMap`.
- [Collections & Strings §4](../foundations/rust-collections-and-strings.md#4-how-does-hashmap-work-and-what-should-you-know-before-using-it)

**Q45. "When do you pick `BTreeMap` over `HashMap`?"**

- When you need **sorted** iteration, range queries (`range(a..b)`), or
  predictable worst-case time. `HashMap` is faster for plain lookup.
- [Collections & Strings §5](../foundations/rust-collections-and-strings.md#5-when-do-you-want-a-btreemap-vecdeque-or-binaryheap)

**Q46. "Why are iterators lazy, and what triggers them?"**

- Adapters (`map`, `filter`, `take`) only build a new iterator. Work happens when
  a **consumer** (`collect`, `sum`, `for`, `count`, `find`) pulls items. This lets
  the compiler fuse a chain into one loop and lets `take(3)` stop early.
- [Iterators & Closures §1](../foundations/rust-iterators-and-closures.md#1-what-is-an-iterator-and-why-is-it-lazy)

**Q47. "How do you turn `Vec<Result<T, E>>` into `Result<Vec<T>, E>`?"**

- `iter.collect::<Result<Vec<_>, _>>()?` stops at the first `Err`. The same trick
  works for `Option`. It works because `Result<V, E>: FromIterator<Result<T, E>>`.
- [Iterators & Closures §3](../foundations/rust-iterators-and-closures.md#3-how-do-you-build-a-collection-from-an-iterator)

**Q48. "What are `Fn`, `FnMut`, and `FnOnce`?"**

- By what the closure **does with its captures**: only reads (`Fn`), mutates
  (`FnMut`), or moves a captured value out (`FnOnce`). Every `Fn` is also
  `FnMut` and `FnOnce`.
- `move` changes how a closure **captures** (by value), not which trait it
  implements.
- [Iterators & Closures §6](../foundations/rust-iterators-and-closures.md#6-what-is-a-closure-and-how-does-it-capture-variables)

**Q49. "`impl Fn` or `Box<dyn Fn>` for returning a closure?"**

- `impl Fn` when you return **one** closure type: no allocation, can inline.
  `Box<dyn Fn>` when the type varies (branches, a `Vec` of callbacks).
- [Iterators & Closures §7](../foundations/rust-iterators-and-closures.md#7-how-do-you-pass-and-return-closures)

**Q50. "What does `RefCell` do, and when does it panic?"**

- It moves the borrow rules to **run time**: any number of `borrow()` or one
  `borrow_mut()`. Breaking the rule panics (`already borrowed`). `try_borrow`
  returns a `Result` instead.
- It is single-threaded (`!Sync`); the thread-safe cousin is `Mutex`/`RwLock`.
- [Smart Pointers §4](../foundations/rust-smart-pointers.md#4-what-is-interior-mutability)

**Q51. "How do `Rc` cycles leak, and how do you break them?"**

- Two `Rc`s that point at each other never reach count 0, so they are never
  freed. Make the back-pointer a `Weak` (parent pointers in a tree); `upgrade()`
  returns `Option<Rc<T>>`.
- [Smart Pointers §3](../foundations/rust-smart-pointers.md#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for)

**Q52. "When is `Cow` useful?"**

- When a function **usually** returns its input unchanged but **sometimes**
  needs to modify it: `Cow<'a, str>` borrows in the common case and allocates
  only when needed.
- [Smart Pointers §5](../foundations/rust-smart-pointers.md#5-what-are-cow-oncelock-and-lazylock-for)

**Q53. "`Box<dyn Trait>` or an `enum`?"**

- An `enum` when the set of variants is **closed** and known: faster, no
  allocation, exhaustive `match`. `Box<dyn Trait>` when others can **add** types
  (plugins).
- [Smart Pointers §8](../foundations/rust-smart-pointers.md#8-how-do-you-choose-between-them)

## 7. Advanced language: layout, variance, unsafe, FFI, macros

**Q54. "Why can a struct's size change when you reorder its fields?"**

- **Padding** keeps each field aligned. The default `repr(Rust)` lets the compiler
  reorder fields to minimize padding (the sample struct is 8 bytes, but 12 with
  `repr(C)`). `repr(C)` keeps source order, which FFI needs.
- Layout of `repr(Rust)` is **not guaranteed**; never assume it.
- [Memory Layout & DSTs §4](../advanced-language/rust-memory-layout-and-dsts.md#4-what-do-reprc-packed-align-transparent-and-repru8-do)

**Q55. "What is a fat pointer?"**

- A pointer to a **dynamically sized type** carries extra data: `&[T]` and `&str`
  hold a pointer and a **length** (16 bytes on 64-bit), `&dyn Trait` holds a
  pointer and a **vtable** pointer.
- [Memory Layout & DSTs §7](../advanced-language/rust-memory-layout-and-dsts.md#7-what-is-the-difference-between-a-thin-pointer-and-a-fat-pointer)

**Q56. "What is a zero-sized type, and what is it good for?"**

- A type with size 0 (`()`, `PhantomData`, a unit struct). Used as markers
  (typestate), as the "key" in a `HashSet<K, ()>` (`HashSet` is exactly that),
  and as free "capabilities" in type-level designs. A `Vec<()>` never allocates
  and reports capacity `usize::MAX`.
- [Memory Layout & DSTs §9](../advanced-language/rust-memory-layout-and-dsts.md#9-what-is-a-zero-sized-type-and-why-is-it-useful)

**Q57. "What is variance, and why is `&mut T` invariant in `T`?"**

- Variance says when `Foo<'long>` can stand in for `Foo<'short>`. `&'a T` is
  **covariant** (a long borrow can be used as a short one).
- `&mut T` is **invariant** in `T`: if `&mut &'static str` could shrink to
  `&mut &'a str`, you could write a short-lived string into it and leave a
  dangling `'static` reference behind. That is error `E0597` in the compile-fail
  sample.
- [Variance & Drop Check §3](../advanced-language/rust-variance-dropck-and-phantomdata.md#3-why-is-mut-t-invariant-show-me-the-bug-it-prevents)

**Q58. "What does the drop checker protect against?"**

- A type with a `Drop` impl may **read** borrowed data in its destructor, so that
  data must still be alive when the destructor runs. This forces locals to be
  declared in the right order. The standard library opts out for some types with
  the unstable `#[may_dangle]`.
- [Variance & Drop Check §4](../advanced-language/rust-variance-dropck-and-phantomdata.md#4-what-is-the-drop-checker-and-what-is-it-protecting)

**Q59. "What is `PhantomData` for?"**

- It tells the compiler "this type **acts as if** it owns or borrows a `T`" when
  no field does. It sets **variance**, drop-check ownership, and auto traits
  (`Send`/`Sync`). `PhantomData<*const ()>` makes a type `!Send`.
- [Variance & Drop Check §6](../advanced-language/rust-variance-dropck-and-phantomdata.md#6-what-does-phantomdata-do-and-how-do-i-choose-its-type)

**Q60. "What do `Send` and `Sync` mean, and who implements them?"**

- `T: Send` means it is safe to **move** a `T` to another thread. `T: Sync`
  means `&T` is `Send`, so it is safe to **share** a reference across threads.
- They are **auto traits**: derived from field types. `Rc` is neither (non-atomic
  count); `RefCell` is `Send` but not `Sync`; `MutexGuard` is not `Send`.
- `unsafe impl Send for T {}` is you promising the compiler it is safe.
- [Threads & Sync §2](../concurrency-and-async/rust-threads-and-synchronization.md#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race)

**Q61. "What can `unsafe` do that safe code cannot?"**

- Five things: dereference a raw pointer, call an `unsafe` function, access or
  modify a `static mut`, implement an `unsafe` trait, and access a `union`
  field. It does **not** turn off the borrow checker or other checks.
- [Unsafe & Miri §1](../advanced-language/rust-unsafe-and-miri.md#1-what-does-unsafe-actually-allow)

**Q62. "Name five kinds of undefined behavior."**

- A dangling or misaligned pointer dereference, an out-of-bounds access,
  violating aliasing rules (`&mut` while another pointer reads), an invalid
  value (`bool` = 3, a null `&T`), reading uninitialized memory, and data races.
- UB is not "a crash": the optimizer may assume it never happens, so the program
  can do anything.
- [Unsafe & Miri §2](../advanced-language/rust-unsafe-and-miri.md#2-what-is-undefined-behaviour-and-why-is-it-so-bad)

**Q63. "How do you check `unsafe` code?"**

- Run the tests under **Miri** (`cargo +nightly miri test`), which interprets
  your code and reports out-of-bounds, use-after-free, invalid values, and
  aliasing violations. Add sanitizers and `loom` for concurrency. Keep `unsafe`
  blocks small with a `// SAFETY:` comment naming the invariant.
- [Unsafe & Miri §8](../advanced-language/rust-unsafe-and-miri.md#8-how-do-i-find-undefined-behaviour-show-me-miri)

**Q64. "Why is `MaybeUninit` needed, and what replaced `mem::uninitialized`?"**

- An uninitialized value of a type like `bool` or `&T` is **instant UB**, even if
  never read. `MaybeUninit<T>` is a wrapper that may hold uninitialized bytes
  and is only turned into `T` after you write it (`assume_init`).
  `mem::uninitialized` is deprecated for that reason.
- [Unsafe & Miri §7](../advanced-language/rust-unsafe-and-miri.md#7-what-are-maybeuninit-manuallydrop-and-transmute-and-what-are-their-traps)

**Q65. "What changed for `unsafe` in the 2024 edition?"**

- `unsafe extern "C" { .. }` blocks, `#[unsafe(no_mangle)]`, the
  `unsafe_op_in_unsafe_fn` lint warns (an `unsafe fn` body needs its own
  `unsafe {}`), references to `static mut` are denied, and `env::set_var` is
  `unsafe`.
- [Modules, Crates & Editions §5](../foundations/rust-modules-crates-and-editions.md#5-what-changed-in-the-2024-edition)

**Q66. "What happens if a Rust panic unwinds into C?"**

- It is undefined unless the ABI allows it. A plain `extern "C"` function now
  **aborts** the process on panic. Use `extern "C-unwind"` only when both sides
  are built to unwind.
- Defensive pattern: wrap the body in `catch_unwind` and return an error code.
- [FFI & C Interop §7](../advanced-language/rust-ffi-and-c-interop.md#7-what-happens-if-rust-panics-inside-an-extern-c-function)

**Q67. "Who frees memory across an FFI boundary?"**

- **Whoever allocated it**, with the same allocator. Rust hands out a
  `Box::into_raw` pointer plus a `free_thing` function; C must call that and
  never `free()`. Never assume Rust's `Vec` and C's `malloc` share an allocator.
- [FFI & C Interop §4](../advanced-language/rust-ffi-and-c-interop.md#4-how-do-i-share-a-struct-and-who-owns-what)

**Q68. "What is macro hygiene?"**

- Variables a `macro_rules!` macro **creates** do not clash with variables at the
  call site, even with the same name. Hygiene covers local variables and labels,
  not items like functions and types.
- [Macros §6](../advanced-language/rust-macros.md#6-what-is-macro-hygiene-and-what-is-crate)

**Q69. "What are the three kinds of procedural macros, and where must they live?"**

- Function-like (`sql!(..)`), derive (`#[derive(Describe)]`), and attribute
  (`#[timed]`). They run **at compile time** on token streams, in a separate
  crate with `proc-macro = true`, which is compiled **before** the crate that
  uses it.
- [Macros §8](../advanced-language/rust-macros.md#8-how-do-procedural-macros-work-and-why-must-they-live-in-their-own-crate)

## 8. Concurrency and atomics

**Q70. "Why is `Rc` not `Send`?"**

- Its reference count is non-atomic. Two threads cloning at once could corrupt
  the count and free memory early. `Arc` uses atomic operations (slower) and is
  `Send` when `T: Send + Sync`. The compiler error is `E0277`: `Rc<..>` cannot
  be sent between threads safely.
- [Threads & Sync §2](../concurrency-and-async/rust-threads-and-synchronization.md#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race)

**Q71. "`Arc<Mutex<T>>`, `RwLock`, or an atomic?"**

- Atomic for a single integer or flag. `Mutex` by default. `RwLock` only when
  reads **far** outnumber writes and hold the lock long enough to matter
  (it can be slower than `Mutex` for short sections).
- [Threads & Sync §3](../concurrency-and-async/rust-threads-and-synchronization.md#3-how-do-you-share-mutable-state-arcmutext)

**Q72. "What is lock poisoning?"**

- If a thread **panics while holding** a `Mutex`, the lock is marked poisoned
  and later `lock()` calls return `Err(PoisonError)`, because the protected data
  may be half-updated. You can recover with `into_inner()` if you can repair the
  state. (`parking_lot` mutexes do not poison.)
- [Threads & Sync §4](../concurrency-and-async/rust-threads-and-synchronization.md#4-what-is-lock-poisoning)

**Q73. "How do you avoid deadlocks?"**

- Always take locks in the **same global order**, hold them for the shortest time,
  never call unknown code while holding one, and prefer message passing.
- Edition 2024 fixes one trap: the `if let` scrutinee temporary now drops
  before the `else` block, so a `Mutex` guard is no longer held there.
- [Threads & Sync §7](../concurrency-and-async/rust-threads-and-synchronization.md#7-how-do-deadlocks-happen-and-how-do-you-avoid-them)

**Q74. "What do scoped threads solve?"**

- `thread::scope` lets spawned threads **borrow locals**, because the scope joins
  them all before returning. `thread::spawn` needs `'static` and gives
  `E0373` (closure may outlive the current function) when you borrow.
- [Threads & Sync §1](../concurrency-and-async/rust-threads-and-synchronization.md#1-how-do-you-start-a-thread-and-what-is-a-scoped-thread)

**Q75. "Explain `Acquire`, `Release`, `Relaxed`, and `SeqCst` in plain words."**

- `Relaxed`: the operation is atomic, with **no ordering** with other memory.
- `Release` (a store) plus `Acquire` (a load of the same atomic): everything
  written **before** the release is visible **after** the acquire. This is how
  you hand off data.
- `SeqCst`: all threads agree on one global order of such operations. Strongest,
  and the safe default when unsure.
- [Atomics & Ordering §2](../concurrency-and-async/rust-atomics-and-memory-ordering.md#2-what-are-relaxed-acquire-release-acqrel-and-seqcst)

**Q76. "Is `Relaxed` enough for a shared counter?"**

- Yes for a **pure statistics counter**, where only the final total matters.
  No if other data is published based on the counter's value.
- [Atomics & Ordering §2](../concurrency-and-async/rust-atomics-and-memory-ordering.md#2-what-are-relaxed-acquire-release-acqrel-and-seqcst)

**Q77. "What is the ABA problem?"**

- A compare-and-swap sees value A, another thread changes A to B and back to A,
  and the CAS succeeds although the structure changed. Common in lock-free
  stacks; fixes are version tags, hazard pointers, or epoch-based reclamation.
- [Atomics & Ordering §6](../concurrency-and-async/rust-atomics-and-memory-ordering.md#6-what-is-the-aba-problem-and-what-else-is-new-in-the-atomics-api)

**Q78. "`compare_exchange` or `compare_exchange_weak`?"**

- `_weak` may fail **spuriously** even when the value matches, but can be faster
  on some CPUs. Use it inside a retry **loop**; use the strong version for a
  single attempt.
- [Atomics & Ordering §4](../concurrency-and-async/rust-atomics-and-memory-ordering.md#4-how-does-compare_exchange-work-and-what-are-update-and-try_update)

**Q79. "What is false sharing?"**

- Two threads write **different** variables that sit on the same CPU cache line,
  so the line bounces between cores. Fix by padding or aligning hot fields to
  separate cache lines (commonly 64 bytes).
- [Threads & Sync §9](../concurrency-and-async/rust-threads-and-synchronization.md#9-what-else-should-you-know-thread-locals-file-locks-false-sharing)

## 9. Async and Tokio

**Q80. "What does an `async fn` compile to?"**

- A **state machine** type that implements `Future`. Each `.await` is a state;
  locals that live across an await are stored in the future itself. Calling the
  function runs **nothing** until the future is polled.
- [Async Internals §1](../concurrency-and-async/rust-async-internals.md#1-what-does-an-async-fn-compile-to)

**Q81. "Why does `Pin` exist?"**

- A future may hold references **into itself** (a local borrowed across an
  `.await`). Moving it would invalidate them. `Pin<&mut F>` promises the future
  will not move. Types that are safe to move opt out with `Unpin`.
- [Async Internals §5](../concurrency-and-async/rust-async-internals.md#5-why-does-pin-exist)

**Q82. "What does 'cancellation safety' mean?"**

- A future is cancelled by **dropping** it, possibly at any `.await`. A cancel-safe
  future loses no data when dropped mid-way. In `tokio::select!`, the branches
  that lose are dropped, so a non-cancel-safe future (such as one that has half
  read a message) can lose data.
- [Tokio & Async Patterns §3](../concurrency-and-async/rust-tokio-and-async-patterns.md#3-what-is-cancellation-safety-and-how-do-select-and-timeouts-work)

**Q83. "Why must you never block inside async code?"**

- Async tasks share a few worker threads. A blocking call (`std::thread::sleep`,
  a CPU loop, sync file or DB I/O) pins a worker, and other tasks on it stall.
- Use async APIs, or `spawn_blocking` for blocking work.
- [Tokio & Async Patterns §7](../concurrency-and-async/rust-tokio-and-async-patterns.md#7-what-are-the-classic-async-mistakes)

**Q84. "Why does holding a `std::sync::MutexGuard` across `.await` fail to compile in `tokio::spawn`?"**

- The guard is `!Send`, so the future is `!Send`, but `tokio::spawn` needs a
  `Send` future ("future cannot be sent between threads safely"). Even when it
  compiles, holding it risks a deadlock.
- Fix: drop the guard before the `.await`, or use `tokio::sync::Mutex` when you
  must hold across an await.
- [Tokio & Async Patterns §7](../concurrency-and-async/rust-tokio-and-async-patterns.md#7-what-are-the-classic-async-mistakes)

**Q85. "Can a trait have an `async fn` and still be used as `dyn Trait`?"**

- Not directly: the returned future type is hidden, so the trait is not dyn
  compatible (`E0038`). Use generics, or return `Pin<Box<dyn Future<..>>>`
  explicitly (what the `async-trait` crate does).
- [Async Internals §6](../concurrency-and-async/rust-async-internals.md#6-what-does-async-fn-in-a-trait-do-and-why-cant-it-be-dyn)

**Q86. "What are async closures?"**

- Since **1.85**, `async |x| ..` is a closure that returns a future which may
  **borrow from the closure's captures**. They implement `AsyncFn`,
  `AsyncFnMut`, and `AsyncFnOnce`.
- [Modern Rust §3](../mastery/modern-rust-2024-to-1-99.md#3-what-changed-for-async-closures-and-traits)

**Q87. "`spawn`, `spawn_blocking`, or `block_in_place`?"**

- `spawn`: async work on the runtime. `spawn_blocking`: sync or CPU work on a
  **separate** blocking thread pool. `block_in_place`: run blocking code on the
  **current** worker (multi-thread runtime only), telling Tokio to move the other
  tasks away.
- [Tokio & Async Patterns §7](../concurrency-and-async/rust-tokio-and-async-patterns.md#7-what-are-the-classic-async-mistakes)

**Q88. "How do you apply backpressure?"**

- Use **bounded** channels (`mpsc::channel(n)`): `send().await` waits when the
  queue is full, slowing the producer. Add a `Semaphore` to cap concurrent work.
  Unbounded channels hide overload until memory runs out.
- [Tokio & Async Patterns §4](../concurrency-and-async/rust-tokio-and-async-patterns.md#4-which-channel-do-you-use-and-how-do-you-get-backpressure)

**Q89. "How do you shut a Tokio service down gracefully?"**

- Listen for a signal (`ctrl_c`/SIGTERM), then tell tasks to stop with a
  `CancellationToken` or a `watch` channel, stop accepting new work, let in-flight
  work finish with a timeout, and `join` the tasks (`JoinSet`).
- [Tokio & Async Patterns §5](../concurrency-and-async/rust-tokio-and-async-patterns.md#5-how-do-you-shut-down-gracefully)

**Q90. "What does `.await` do if the future is not ready?"**

- It returns control to the **executor**, which runs other tasks. When the
  future's **waker** is called, the executor polls it again. If nothing calls the
  waker, the task sleeps forever.
- [Async Internals §2](../concurrency-and-async/rust-async-internals.md#2-what-are-future-poll-context-and-waker)

## 10. Predict the output

Run `cargo run --example guru_quiz` to check any of these. Cover the answers
first.

**Q91. "What does this print, and in what order?"**

```rust
struct Noisy(&'static str);
impl Drop for Noisy { fn drop(&mut self) { println!("drop {}", self.0); } }
struct Pair { first: Noisy, second: Noisy }
fn main() {
    let _a = Noisy("local a");
    let _b = Noisy("local b");
    let _pair = Pair { first: Noisy("field 1"), second: Noisy("field 2") };
    let _ = Noisy("underscore");
    println!("end of function");
}
```

- Output: `drop underscore`, `end of function`, `drop field 1`, `drop field 2`,
  `drop local b`, `drop local a`.
- `let _` drops at once; locals drop in reverse; a struct's fields drop in
  declaration order.
- [Ownership & Borrowing §4](../foundations/rust-ownership-and-borrowing.md#4-when-exactly-are-values-dropped-and-in-what-order)

**Q92. "What are `len()`, `chars().count()`, and `is_char_boundary(2)` of `\"héllo\"`?"**

- `6`, `5`, and `false`. The `é` is 2 bytes (`195 169`), so byte index 2 is in the
  middle of it.
- [Collections & Strings §3](../foundations/rust-collections-and-strings.md#3-how-do-strings-work-why-cant-you-index-them)

**Q93. "What do `-7 / 2`, `-7 % 2`, and `(-7i32).rem_euclid(2)` give?"**

- `-3`, `-1`, `1`. Division truncates toward zero and `%` takes the sign of the
  left side; `rem_euclid` is always non-negative.
- [Types, Enums & Patterns §1](../foundations/rust-types-enums-and-patterns.md#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose)

**Q94. "What do `255u8 as i8`, `-1i32 as u32`, and `300i32 as u8` give?"**

- `-1`, `4294967295`, `44` (300 mod 256). Same bits, reinterpreted or truncated.
- [Types, Enums & Patterns §1](../foundations/rust-types-enums-and-patterns.md#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose)

**Q95. "What do `3.9 as i32`, `-3.9 as i32`, `f64::NAN as i32`, and `1e20 as i32` give?"**

- `3`, `-3`, `0`, `2147483647` (`i32::MAX`). Float to int truncates toward zero
  and **saturates**; `NaN` is 0.
- [Types, Enums & Patterns §1](../foundations/rust-types-enums-and-patterns.md#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose)

**Q96. "Is `0.1 + 0.2 == 0.3`? What do `i32::MAX.wrapping_add(1)`, `saturating_add(1)`, and `checked_add(1)` give?"**

- `false` (binary floating point). `-2147483648`, `2147483647`, `None`.
- [Types, Enums & Patterns §1](../foundations/rust-types-enums-and-patterns.md#1-how-do-numbers-behave-and-where-is-rust-strict-on-purpose)

**Q97. "How many times does the closure run?"**

```rust
let calls = std::cell::Cell::new(0);
let it = [1, 2, 3].iter().map(|x| { calls.set(calls.get() + 1); x * 2 });
println!("{}", calls.get());          // A
let v: Vec<i32> = it.collect();
println!("{}", calls.get());          // B
```

- A prints `0` (lazy, nothing ran). B prints `3`.
- Another run: `.inspect(..).find(|&&x| x > 1)` over `[1, 2, 3, 4]` stops after
  **2** items, so `find` is short-circuiting.
- [Iterators & Closures §1](../foundations/rust-iterators-and-closures.md#1-what-is-an-iterator-and-why-is-it-lazy)

**Q98. "What are the sizes (64-bit) of `Option<&u8>`, `Option<u32>`, and `Option<NonZeroU32>`?"**

- `8`, `8`, `4`. `&u8` has a niche (never null) so `Option` is free. `u32` has no
  spare value, so `Option<u32>` adds a tag plus padding. `NonZeroU32` has a niche.
- Also `&str` and `&[u8]` are 16, `&dyn Send` is 16, `String` and `Vec<u8>` are
  24, and `()` is 0.
- [Memory Layout & DSTs §6](../advanced-language/rust-memory-layout-and-dsts.md#6-what-is-niche-optimization-and-why-is-optionboxt-free)

**Q99. "What does this print?"**

```rust
let a = Rc::new(5);
let b = Rc::clone(&a);
println!("{}", Rc::strong_count(&a));
drop(b);
let w = Rc::downgrade(&a);
println!("{} {}", Rc::strong_count(&a), Rc::weak_count(&a));
drop(a);
println!("{}", w.upgrade().is_some());
```

- `2`, then `1 1`, then `false`. Once the last strong reference is gone the
  value is dropped, and `upgrade()` returns `None`.
- [Smart Pointers §3](../foundations/rust-smart-pointers.md#3-when-do-you-use-rc-and-arc-and-what-are-weak-pointers-for)

**Q100. "What does this print?"**

```rust
let mut c = 0;
let mut inc = || c += 1;
inc(); inc();
println!("{c}");
let s = String::from("hi");
let f = move || s.len();
println!("{} {}", f(), f());
```

- `2`, then `2 2`. The first closure borrows `c` mutably until its last use;
  the `move` closure owns `s` but `len()` only needs `&self`, so it is `Fn` and
  can be called repeatedly.
- [Iterators & Closures §6](../foundations/rust-iterators-and-closures.md#6-what-is-a-closure-and-how-does-it-capture-variables)

**Q101. "What do `\"a,b,,c\".split(',')`, `\" a  b \".split_whitespace()`, and `max_by_key` / `min_by_key` ties produce?"**

- `["a", "b", "", "c"]`; `["a", "b"]`.
- `["aa", "bb", "c"].iter().max_by_key(|s| s.len())` gives `"bb"` (the **last**
  maximum), and `["aa", "bb", "c", "d"].iter().min_by_key(..)` gives `"c"` (the
  **first** minimum).
- [Collections & Strings §6](../foundations/rust-collections-and-strings.md#6-what-are-the-iteration-forms-and-how-does-ownership-flow-through-a-collection)

**Q102. "What do `sum` and `product` of an empty `i32` iterator give? Is `a` usable after `let b = a;` for `a = [1, 2, 3]`?"**

- `0` and `1`. Yes: arrays of `Copy` types are `Copy`.
- [Ownership & Borrowing §3](../foundations/rust-ownership-and-borrowing.md#3-what-is-the-difference-between-copy-and-clone)

## 11. Predict the compile error

For each snippet, name the **error code** and the fix. The files are in
`code_samples/rust/compile_fail/`.

**Q103. "Why does this fail?" (`two_mut_borrows.rs`)**

```rust
let mut v = vec![1, 2, 3];
let a = &mut v;
let b = &mut v;
a.push(4);
b.push(5);
```

- `E0499`: cannot borrow `v` as mutable more than once at a time. Use one
  borrow at a time, or finish with `a` before creating `b`.
- [Ownership & Borrowing §5](../foundations/rust-ownership-and-borrowing.md#5-what-are-the-rules-of-borrowing-and-why-do-they-exist)

**Q104. "Why does this fail?" (`mutate_while_borrowed.rs`)**

```rust
let mut v = vec![1, 2, 3];
let first = &v[0];
v.push(4);
println!("{first}");
```

- `E0502`: cannot borrow `v` as mutable because it is also borrowed as
  immutable. `first` is used after the `push`. Copy the value or reorder.
- [Ownership & Borrowing §6](../foundations/rust-ownership-and-borrowing.md#6-what-does-the-borrow-checker-actually-check-how-do-you-read-its-errors)

**Q105. "Why does this fail?" (`dangling_reference.rs`)**

```rust
fn make<'a>() -> &'a String {
    let s = String::from("temp");
    &s
}
```

- `E0515`: cannot return reference to local variable `s`. Return the `String`
  itself (ownership moves out).
- [Lifetimes §9](../foundations/rust-lifetimes.md#9-what-are-the-common-lifetime-errors-and-the-standard-fixes)

**Q106. "Why does this fail?" (`missing_lifetime.rs`)**

```rust
fn longest(a: &str, b: &str) -> &str { if a.len() > b.len() { a } else { b } }
```

- `E0106`: missing lifetime specifier. Add `<'a>` and tie both inputs and the
  output.
- [Lifetimes §3](../foundations/rust-lifetimes.md#3-what-are-the-elision-rules-and-why-can-you-usually-skip-lifetimes)

**Q107. "Why does this fail?" (`spawn_borrows_local.rs`)**

```rust
let data = vec![1, 2, 3];
let handle = std::thread::spawn(|| println!("{data:?}"));
handle.join().unwrap();
```

- `E0373`: the closure may outlive the current function but borrows `data`. Use
  `move`, or `thread::scope`.
- [Threads & Sync §1](../concurrency-and-async/rust-threads-and-synchronization.md#1-how-do-you-start-a-thread-and-what-is-a-scoped-thread)

**Q108. "Why does this fail?" (`thread_rc_not_send.rs`)**

```rust
let shared = Rc::new(5);
let s2 = Rc::clone(&shared);
std::thread::spawn(move || println!("{s2}")).join().unwrap();
```

- `E0277`: `Rc<i32>` cannot be sent between threads safely. Use `Arc`.
- [Threads & Sync §2](../concurrency-and-async/rust-threads-and-synchronization.md#2-what-are-send-and-sync-and-how-does-rust-prevent-a-data-race)

**Q109. "Why does this fail?" (`missing_trait_bound.rs`)**

```rust
fn largest<T>(items: &[T]) -> &T {
    let mut m = &items[0];
    for i in items { if i > m { m = i; } }
    m
}
```

- `E0369`: binary operation `>` cannot be applied to `&T`. Add `T: PartialOrd`.
- [Traits & Generics §4](../foundations/rust-traits-and-generics.md#4-how-do-you-write-generic-code-and-what-are-bounds)

**Q110. "Why does this fail?" (`move_out_of_borrow.rs`)**

```rust
let names = vec![String::from("a"), String::from("b")];
let r = &names;
let first = r[0];
```

- `E0507`: cannot move out of index of `Vec<String>`. Borrow (`&r[0]`) or
  clone (`r[0].clone()`).
- [Ownership & Borrowing §7](../foundations/rust-ownership-and-borrowing.md#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it)

**Q111. "Why does this fail?" (`not_dyn_compatible.rs`)**

```rust
trait Cloner {
    fn dup(&self) -> Self;
    fn map<F: Fn(i32) -> i32>(&self, f: F) -> i32;
}
fn use_it(_c: &dyn Cloner) {}
```

- `E0038`: the trait `Cloner` is not dyn compatible: `dup` returns `Self` and
  `map` is generic. Add `where Self: Sized` to those methods or use generics.
- [Traits & Generics §3](../foundations/rust-traits-and-generics.md#3-what-does-it-mean-that-a-trait-is-dyn-compatible)

**Q112. "Why does this fail?" (`conflicting_blanket_impl.rs`)**

- `E0119`: conflicting implementations of trait `Describe` for type `i32`.
  A blanket `impl<T: Display> Describe for T` overlaps a specific impl for a
  type that is also `Display`. Remove one, or use a newtype.
- [Advanced Traits §8](../advanced-language/rust-advanced-traits-and-type-level-design.md#8-what-are-supertraits-blanket-impls-and-marker-traits)

## 12. Design and judgment questions

These have no single right answer. Strong answers state a **choice**, the
**trade-off**, and **how you would check it worked**.

**Q113. "Design a thread-safe LRU cache."**

- Start with `Mutex<LruInner>` where `LruInner` holds a `HashMap` plus a linked
  structure (indices into a `Vec` avoid `unsafe`). Measure contention; if it
  matters, **shard** the cache by key hash across several mutexes.
- Mention eviction on insert, `get` updating recency (so reads need `&mut`),
  and tests with several threads.
- Related: [Threads & Synchronization](../concurrency-and-async/rust-threads-and-synchronization.md),
  [Collections & Strings](../foundations/rust-collections-and-strings.md).

**Q114. "Design a rate limiter for an HTTP service."**

- Token bucket per key: atomic or mutex-protected counters plus a refill time
  stored as an `Instant`. In `tower`, wrap as a **layer** so every route gets
  it; return `429` with `Retry-After`.
- Distributed limits need shared state (Redis); say that a local limiter only
  limits one instance.
- Related: [Web Services with Axum](../production/rust-web-services-with-axum.md).

**Q115. "Design a plugin system."**

- In-process: a trait plus `Box<dyn Plugin>`, registered at start. Third-party
  binaries: a stable **C ABI** (`extern "C"`), a **WASM** component, or separate
  processes (gRPC). Rust has **no stable ABI** for its own types, so loading
  Rust `.so` files built by different compilers is unsafe.
- Related: [FFI & C Interop](../advanced-language/rust-ffi-and-c-interop.md),
  [WebAssembly](../performance-and-internals/rust-webassembly.md).

**Q116. "A service uses too much memory. How do you find out why?"**

- Measure first: a heap profiler (`dhat`, `heaptrack`, or the allocator's
  stats), then look for unbounded channels, caches without a limit, `clone`s of
  large data, and `Vec`s holding capacity after shrinking.
- Fix with bounds, `shrink_to_fit`, `Arc` sharing, or streaming instead of
  loading all data.
- Related: [Performance Engineering](../performance-and-internals/rust-performance-engineering.md).

**Q117. "Expose a Rust library to Python. What are your options and risks?"**

- **PyO3 with maturin** for a native extension (best ergonomics), a C ABI with
  `cffi`, or an out-of-process service. Risks: GIL handling, copying data across
  the boundary (use buffers or `numpy` views), panics (convert to Python
  exceptions), and building wheels for each platform.
- Related: [FFI & C Interop](../advanced-language/rust-ffi-and-c-interop.md),
  [Rust for Python, Go & Kotlin Developers](rust-for-python-go-and-kotlin-developers.md).

**Q118. "You inherit callback-heavy code. How do you move it to async safely?"**

- Wrap one boundary at a time with channels or `oneshot`, keep blocking parts in
  `spawn_blocking`, add timeouts and cancellation handling, and test with
  paused time (`#[tokio::test(start_paused = true)]`).
- Related: [Tokio & Async Patterns](../concurrency-and-async/rust-tokio-and-async-patterns.md).

**Q119. "How would you design the error handling of a large service?"**

- Typed errors (`thiserror`) per layer, **one error boundary** at the edge that
  maps them to HTTP status codes and a stable JSON body, `anyhow`-style context
  inside tasks, `tracing` spans so each error carries a request id, and no
  `unwrap()` outside tests.
- Related: [Error Handling](../foundations/rust-error-handling.md),
  [Observability](../production/rust-observability.md).

**Q120. "How do you keep a public crate's API stable?"**

- Follow SemVer, run `cargo semver-checks`, mark enums and structs
  `#[non_exhaustive]`, **seal** traits you do not want others to implement, keep
  dependencies' types out of your public API, and set an MSRV policy.
- Related: [Architecture & API Design](../production/rust-project-architecture-and-api-design.md).

## 13. How do AI tools change this, and how do you talk about it?

**Answer:**

- **Core idea:** interviewers now ask **how you verify** what an assistant gives
  you. A guru answer includes the check: compile, `clippy`, tests, Miri,
  `loom`, a benchmark.
- **Hurt:** assistants state wrong guarantees with confidence (an
  invented method name, `Relaxed` where `Acquire` is needed, a "safe" `unsafe`
  block). The questions above are exactly the ones where a plausible wrong
  answer is common, so practise without the tool first.
- **Help:** use an assistant to **quiz you**: "ask me one hard Rust question
  about lifetimes, wait for my answer, then grade it against the Rust
  Reference". Check its grading against the linked page.
- **Help:** paste a compiler error and ask for the **reason** behind the rule,
  not just a fix. Then try to explain the fix back in your own words.
- Live coding with an AI present: narrate your design, state the invariants,
  and run the tests. See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

---

## Code Samples

- `code_samples/rust/examples/guru_quiz.rs`: the predict-the-output items
  (drop order, strings, number casts, laziness, sizes, `Rc` counts, closures).
- `code_samples/rust/compile_fail/`: files for the predict-the-error items
  (`two_mut_borrows.rs`, `mutate_while_borrowed.rs`, `dangling_reference.rs`,
  `missing_lifetime.rs`, `spawn_borrows_local.rs`, `thread_rc_not_send.rs`,
  `missing_trait_bound.rs`, `move_out_of_borrow.rs`, `not_dyn_compatible.rs`,
  `conflicting_blanket_impl.rs`).

```bash
cd code_samples/rust
cargo run --example guru_quiz
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/two_mut_borrows.rs   # fails on purpose
```
