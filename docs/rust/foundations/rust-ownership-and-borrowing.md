---
title: Rust Ownership & Borrowing
---

# Rust Ownership & Borrowing

Ownership is the one idea Rust is built around. **Every value has exactly
one owner, and when the owner goes out of scope the value is cleaned
up.** There is no garbage collector and no manual `free`. The compiler
inserts the cleanup for you, at a place it can prove is right. The rest
of the rules (moves, borrows, lifetimes) exist to make that one promise
safe. If you understand *why* these rules exist, the borrow checker stops
feeling like an opponent and starts feeling like a code reviewer who
never gets tired.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. All examples were
    compiled and run on 1.99.1, and the error messages are the real ones
    from that compiler.

## 1. "What problem does ownership solve?"

**Answer:**

- Programs need memory in two places:
    - The **stack**: fast, automatic, for values whose size is known at
      compile time. It is freed when a function returns.
    - The **heap**: for values whose size is only known at run time, or
      that must outlive a function (a `String`'s text, a `Vec`'s items).
      Someone must decide **when to free** it.
- Three ways languages answer "who frees the heap memory?":

| Approach | Used by | Cost |
|---|---|---|
| The programmer calls `free` | C | Use-after-free, double free, leaks |
| A garbage collector finds unused memory at run time | Java, Go, Kotlin, Python | Pauses, extra memory, less predictable timing |
| **The compiler decides, using ownership rules** | Rust | You learn the rules; no run-time cost |

- The three rules:
    1. Each value has one **owner** (a variable, a field, an element).
    2. There is only **one owner at a time**.
    3. When the owner goes **out of scope**, the value is **dropped**
       (its cleanup code runs, and heap memory is freed).
- This pattern is called **RAII** (Resource Acquisition Is Initialization).
  It works for **any resource**, not only memory: a file closes when its
  owner is dropped, a lock is released, a network connection is shut down.
- The result is memory safety **without** a run-time cost: the checks are
  done at compile time, and the compiled program contains only the
  `free` calls that are really needed.

## 2. "What exactly happens when a value is moved?"

```rust
let s = String::from("hello");
let t = s;                // `s` is MOVED into `t`
println!("{s} {t}");      // error: borrow of moved value: `s`
```

```text
error[E0382]: borrow of moved value: `s`
 --> compile_fail/use_after_move.rs:4:16
  |
2 |     let s = String::from("hello");
  |         - move occurs because `s` has type `String`, which does not implement the `Copy` trait
3 |     let t = s;
  |             - value moved here
4 |     println!("{s} {t}");
  |                ^ value borrowed here after move
```

**Answer:**

- A `String` on the stack is three words: a **pointer** to the heap text,
  a **length**, and a **capacity**. That is 24 bytes on a 64-bit machine.
  The text itself is on the heap.
- `let t = s;` copies those 24 bytes into `t`, then the compiler marks
  `s` as **invalid**. Both variables would point to the same heap text, so
  if both were dropped it would be freed twice. A move makes sure only
  **one** of them is ever dropped.
- Nothing is copied on the heap. A move is **cheap**: it is the same cost
  whether the `String` holds 5 bytes or 5 gigabytes.
- Moves happen everywhere ownership transfers:
    - Assigning to another variable (`let t = s`).
    - Passing to a function (`take(s)`). The callee now owns it.
    - Returning from a function. The caller now owns it.
    - Capturing in a `move` closure.
    - Looping with `for x in vec`, which consumes the whole vector.
    - Pattern matching that binds by value.
- A **partial move** takes one field out of a struct. The other fields
  stay usable, but the struct as a whole cannot be used again (see
  `ownership_moves` in [Code Samples](#code-samples)).
- When a move is conditional (`if cond { drop(s) }`), the compiler keeps a
  hidden **drop flag** at run time to remember whether to drop at scope
  end. You never see it, and it costs one bit.

## 3. "What is the difference between Copy and Clone?"

**Answer:**

- **`Copy`** types are duplicated by a plain bit copy whenever you assign
  or pass them. The original **stays valid**. Integers, floats, `bool`,
  `char`, shared references (`&T`), and tuples or arrays made only of
  `Copy` types are all `Copy`.
- **`Clone`** is an **explicit** `.clone()` call that can run any code,
  including allocating a full deep copy. It is never implicit.
- A type can be `Copy` only if:
    - All its fields are `Copy`.
    - It does **not** implement `Drop`. If a type needs cleanup, a silent
      bit copy would give you two owners of one resource.
- `&mut T` is **not** `Copy` (two live mutable references would break the
  rules), and neither are `String`, `Vec`, or `Box`.
- Rule of thumb for APIs:
    - Small, plain data: derive `Copy` (`#[derive(Clone, Copy)]`).
    - Anything that owns heap data: `Clone` only.
- `Clone` in Rust is **visible cost**. A `.clone()` in a hot loop is
  usually a design smell. A `.clone()` to get past the borrow checker is
  fine **if you know why** and it is not in a hot path. See
  [§7](#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it).

## 4. "When exactly are values dropped, and in what order?"

**Answer:**

- A value is dropped when its **owner goes out of scope**, **unless it
  was moved first**. Then the new owner decides.
- The **order** is predictable:
    - **Local variables** are dropped in **reverse order of declaration**.
      The last variable declared is dropped first.
    - **Struct fields** and **tuple or array elements** are dropped in
      **declaration (index) order**, after the struct's own `Drop`
      code runs.
    - **Temporaries** are dropped at the end of the statement that created
      them, except that `let x = &temp();` extends the temporary's life to
      the end of the block.
- The output of `ownership_moves` shows the reverse order: `d`, then `c`,
  then `b`.
- `std::mem::drop(x)` is not special. It is a function that takes `x` **by
  value** and does nothing, so `x` is dropped at the end of `drop`. That
  is how you end a value's life early.
- **Edition 2024 changed one rule.** Temporaries in a block's **final
  expression** used to live until after the block's local variables were
  dropped. They are now dropped **before** them. This fixes a classic
  error:

    ```rust
    fn len_of_cell() -> usize {
        let c = RefCell::new(String::from(".."));
        c.borrow().len()   // 2021: error[E0597]: `c` does not live long enough
    }                      // 2024: compiles
    ```

  In 2021 the `Ref` temporary outlived `c` and its destructor needed `c`.
  See `tail_expr_temporaries` in [Code Samples](#code-samples).
- **`mem::forget`** makes a value never drop, and it is **safe** Rust.
  Leaking memory is not memory-unsafe. The guarantee is "no use after
  free", not "no leaks". (`Rc` cycles also leak, for the same reason.)
- **`ManuallyDrop<T>`** is the tool for taking drop into your own hands in
  `unsafe` code. See [Unsafe Rust & Miri](../advanced-language/rust-unsafe-and-miri.md).
- If a `drop` runs **during a panic** and panics again, the process
  aborts. Keep `Drop` code simple, and never let it fail.

## 5. "What are the rules of borrowing, and why do they exist?"

**Answer:**

- A **reference** lets code use a value without owning it:
    - `&T` — a **shared** (read-only) reference.
    - `&mut T` — an **exclusive** (read-write) reference.
- The rule, in one sentence: **at any time, a value has either any number
  of shared references, or exactly one mutable reference, never both.**
  Some people say it as "aliasing XOR mutability."
- Why this exact rule: three real bugs need **two accesses to one place
  where at least one writes**:
    - **Iterator invalidation**: pushing to a vector while looping over it
      may reallocate, leaving the loop reading freed memory.
    - **Data races**: two threads, one writing, no synchronization.
    - **Use after free**: a reference kept after the owner dropped.
- A reference must **never outlive** its owner. The compiler checks this
  with **lifetimes**. See [Lifetimes](rust-lifetimes.md).
- Borrow checking is done by the compiler on the control-flow graph and
  costs **nothing at run time**. A `&T` is a plain pointer.
- The rule also allows **optimizations**. If the compiler knows nobody else
  can change a value through another path, it can keep it in a register.
  This is a performance gain that C and C++ get only with `restrict`.

## 6. "What does the borrow checker actually check? How do you read its errors?"

```text
error[E0502]: cannot borrow `v` as mutable because it is also borrowed as immutable
 --> compile_fail/mutate_while_borrowed.rs:4:5
  |
3 |     let first = &v[0];
  |                  - immutable borrow occurs here
4 |     v.push(4);
  |     ^^^^^^^^^ mutable borrow occurs here
5 |     println!("{first}");
  |                ----- immutable borrow later used here
```

**Answer:**

- Since Rust 2018 the checker uses **non-lexical lifetimes** (NLL). A
  borrow lasts from where it is created to its **last use**, not to the end
  of the block. In the example above, removing the `println!` makes the
  code compile, because `first` is never used after `push`.
- The error message has **three parts**. Read them in order:
    1. *Where* the first borrow starts.
    2. *Where* the conflicting access happens.
    3. *Where* the first borrow is **used later**, which is what keeps it
       alive. This third line is the one that tells you what to change.
- The errors you will meet most:

| Code | Message (short) | Usual fix |
|---|---|---|
| `E0382` | borrow of moved value | Borrow instead of moving, or `.clone()`, or restructure |
| `E0499` | cannot borrow as mutable more than once | Finish one use before the next, or split the data |
| `E0502` | cannot borrow as mutable because it is also borrowed as immutable | End the shared borrow earlier, or copy the value out first |
| `E0505` | cannot move out because it is borrowed | End the borrow before the move |
| `E0507` | cannot move out of index or borrowed content | Borrow (`&r[0]`), `.clone()`, or `mem::take` |
| `E0515` | cannot return reference to local variable | Return the owned value |
| `E0597` | does not live long enough | Make the owner live longer, or own the data |
| `E0716` | temporary value dropped while borrowed | Bind the temporary to a variable |

- **Two-phase borrows** make `v.push(v.len())` legal. The `&mut v` is
  created first but only **activated** after the arguments, including the
  read `v.len()`, have been evaluated.
- **Reborrowing**: when you pass a `&mut T` to a function, Rust usually
  **reborrows** it (a short loan from your reference) rather than moving
  it, so you can use it again afterwards.
- **Disjoint fields** can be borrowed mutably at the same time:
  `let a = &mut p.a; let b = &mut p.b;` is fine because the compiler
  tracks fields separately. Through a **method**, it cannot, because the
  method signature borrows all of `self`.
- The checker is **conservative**: it rejects some programs that are
  actually safe, because proving them safe needs more analysis than the
  rules allow. A newer analysis (Polonius) is being developed for this
  and is not stable yet.

## 7. "How do you work with the borrow checker instead of against it?"

**Answer:**

- **Keep borrows short.** Compute, copy out the small result, drop the
  reference, then mutate.
- **Use indices instead of references** when you need to read and then
  write the same collection. `scores[best] += 1` after finding `best` by
  index avoids holding a reference.
- **Move out of borrowed places safely** with the helpers made for it:

| Tool | Does |
|---|---|
| `Option::take()` | Takes the value, leaves `None` |
| `mem::take(&mut x)` | Takes the value, leaves `Default::default()` |
| `mem::replace(&mut x, new)` | Puts `new`, returns the old value |
| `mem::swap(&mut a, &mut b)` | Swaps two places |

- **Split a borrow** with `split_at_mut`, `split_first_mut`, `chunks_mut`, or
  by destructuring a struct into separate field borrows.
- **Use the Entry API** on maps instead of "get, then insert", which holds
  a borrow across the insert.
- **Take `self` by value** for operations that consume an object (builders,
  `into_*` methods). Ownership then flows through the call chain.
- **Choose parameter types by what the function needs:**

| Signature | Meaning |
|---|---|
| `fn f(x: &T)` | Only reads. The caller keeps ownership. |
| `fn f(x: &mut T)` | Changes it in place. The caller keeps ownership. |
| `fn f(x: T)` | Takes ownership: stores it, or consumes it. |
| `fn f(x: impl Into<String>)` | Accepts `&str` or `String`, and the callee needs an owned `String`. |
| `fn f(x: impl AsRef<str>)` | Accepts many string types, only reads. |
| `fn f(x: &str)` instead of `&String` | Accepts more callers. Prefer slices (`&str`, `&[T]`) in parameters. |
| `Cow<'_, str>` | Borrow when possible, allocate only when needed. |

- **`.clone()` is acceptable** when the data is small, or when it is not on
  a hot path, or when it removes a complicated lifetime. Measure before
  you worry.
- **`Rc<RefCell<T>>` is the last resort**, not the first tool. It moves the
  borrow check from compile time to run time, and it can panic. Reach for
  a better data layout first. See [Smart Pointers](rust-smart-pointers.md).
- A common design fix: **make the data model tree-shaped.** Graph-like
  structures with back-references fight the checker. Store items in a
  `Vec` and refer to them by **index or ID** (an "arena" or "slotmap"
  pattern).
- Run `ownership_patterns` to see `take`, `replace`, a builder, `Cow`, and
  index-based updates working together.

## 8. "How does this compare with other languages?"

**Answer:**

| Language | Memory management | What Rust adds |
|---|---|---|
| C | Manual `malloc`/`free` | Compile-time proof of no use-after-free or double free |
| C++ | RAII, move semantics, smart pointers | Moves are the **default** and checked; use-after-move is a compile error; references are checked |
| Go | Garbage collector | No pauses and lower memory use, in exchange for learning the rules; plus data-race safety |
| Python | Reference counting plus a cycle collector | No run-time counter per object; but no easy sharing |
| Java, Kotlin | Garbage collector | Same trade as Go; plus values are really inline (no object header) |

- The biggest mental shift from a **garbage-collected** language: assigning
  an object does **not** create a second reference to it. It **moves**
  it. To share, you borrow, or you choose a shared owner (`Rc`, `Arc`)
  on purpose.
- The biggest shift from **C++**: Rust's moves cannot leave a
  "valid but unspecified" object behind. A moved-from variable is simply
  gone.

## 9. "How do you use AI tools while learning ownership?"

**Answer:**

- Paste the **whole error** and the **smallest code** that triggers it.
  Ask "which rule is being broken and why does that rule exist?", not
  "fix this".
- AI tools often "fix" a borrow error by adding `.clone()` or
  `Rc<RefCell<...>>` everywhere. That compiles but hides the design
  problem. Ask for a version **without** extra clones, and compare.
- Always check a suggestion against [§7](#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it).
- Do not let a tool write `unsafe` to get around a borrow error. That is
  almost never the right answer.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Ownership**

- "What are the three ownership rules?" — expects one owner, one at a
  time, drop at scope end,
  [§1](#1-what-problem-does-ownership-solve).
- "What happens in memory when you move a `String`?" — expects the
  24-byte header is copied, the heap text is not, and the source is
  invalidated,
  [§2](#2-what-exactly-happens-when-a-value-is-moved).
- "Why can't a type be both `Copy` and `Drop`?" — expects a bit copy would
  create two owners of one resource,
  [§3](#3-what-is-the-difference-between-copy-and-clone).
- "In what order are locals and struct fields dropped?" — expects locals
  in reverse order, fields in declaration order,
  [§4](#4-when-exactly-are-values-dropped-and-in-what-order).

**Borrowing**

- "State the borrowing rule and the bugs it prevents." — expects
  many `&T` or one `&mut T`, and iterator invalidation, data races, and use
  after free,
  [§5](#5-what-are-the-rules-of-borrowing-and-why-do-they-exist).
- "What are non-lexical lifetimes?" — expects a borrow ends at its last
  use, [§6](#6-what-does-the-borrow-checker-actually-check-how-do-you-read-its-errors).
- "Why does `v.push(v.len())` compile?" — expects two-phase borrows,
  [§6](#6-what-does-the-borrow-checker-actually-check-how-do-you-read-its-errors).
- "Is leaking memory unsafe in Rust?" — expects no: `mem::forget` and
  `Rc` cycles are safe, [§4](#4-when-exactly-are-values-dropped-and-in-what-order).

**Practice**

- "You need to take a `String` out of a `&mut Option<String>`. How?" —
  expects `Option::take()`,
  [§7](#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it).
- "Should this function take `String`, `&String`, or `&str`?" — expects
  `&str` to read, `impl Into<String>` or `String` to store,
  [§7](#7-how-do-you-work-with-the-borrow-checker-instead-of-against-it).
- "What did edition 2024 change about temporaries?" — expects the tail
  expression rule,
  [§4](#4-when-exactly-are-values-dropped-and-in-what-order).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/ownership_moves.rs` — moves, `Copy`, `clone`, borrowing, partial
  moves, and drop order with a noisy `Drop`.
- `examples/borrow_rules.rs` — NLL, reborrowing, field splitting, and
  `split_at_mut`.
- `examples/ownership_patterns.rs` — `take`, `replace`, a builder, `Cow`,
  `impl AsRef`, and index-based updates.
- `examples/tail_expr_temporaries.rs` — the edition 2024 temporary rule.
  Compile it with `rustc --edition 2021` to see the old error.
- `compile_fail/*.rs` — one file per error in the table above. Each one
  fails on purpose. Run `rustc --edition 2024 --emit=metadata file.rs` to
  see the message.

```bash
cd code_samples/rust
cargo run --example ownership_moves
cargo run --example borrow_rules
rustc --edition 2024 --emit=metadata -o /tmp/out compile_fail/use_after_move.rs
```
