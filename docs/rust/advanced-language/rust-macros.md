---
title: Rust Declarative and Procedural Macros
---

# Rust Declarative and Procedural Macros

A **macro** is code that **writes code** before the program is compiled. When
you write `vec![1, 2, 3]` or `#[derive(Debug)]`, the compiler runs a macro and
replaces it with ordinary Rust, then checks that result like any other code.
Rust has two families. **Declarative macros** (`macro_rules!`) match
patterns and substitute text-like pieces, all inside one file. **Procedural
macros** are real Rust programs that read the code as a stream of tokens and
produce new tokens. This page teaches both, from the first pattern to a
working derive, attribute and function-like macro, and when **not** to write a
macro at all.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. All code was compiled
    and run on Rust 1.99.1. The procedural macro crate used the versions
    that `cargo add` chose on the day of writing: `syn 3.0.9`,
    `quote 1.0.47`, `proc-macro2 1.0.107`. Macro expansion output below came
    from `rustc +nightly -Zunpretty=expanded`. Prerequisite:
    [Modules, Crates & Editions](../foundations/rust-modules-crates-and-editions.md).

## 1. "What is a macro, and how is it different from a function?"

**Answer:**

- A **function** runs at **run time** on **values**. A **macro** runs at
  **compile time** on **tokens** (the pieces the compiler splits code into:
  names, symbols, literals).
- Macros can do what functions cannot:
    - Take a **variable number of arguments** (`println!`, `vec!`).
    - **Generate items**: structs, `impl` blocks, functions, tests.
    - Run code at compile time and **reject bad input** with a custom
      error.
    - Add behaviour to your own types (`#[derive(...)]`).
- The call looks like `name!(...)`, `#[name]`, or `#[derive(Name)]`.
- Macros are checked **after** expansion: the compiler errors point to the
  expanded code, which is why macro errors can be confusing (§10).
- The cost: harder to read, harder to debug, slower compile times, and tools
  (rust-analyzer, Clippy) understand them less well. Use a function or a
  generic first (§11).

## 2. "How does `macro_rules!` work?"

```rust
macro_rules! square {
    ($x:expr) => {
        $x * $x
    };
}

square!(3 + 1)
```

```text
square!(3 + 1) = 16 (expr keeps precedence: (3+1)*(3+1))
```

What the compiler produced (from `rustc +nightly -Zunpretty=expanded`):

```text
let a = (3 + 1) * (3 + 1);
```

**Answer:**

- A `macro_rules!` macro is a list of **rules**. Each rule is
  `(pattern) => { template }`. The compiler tries the rules **in order**, uses
  the **first pattern that matches**, and fills in the template.
- `$x:expr` is a **metavariable**: `$x` is its name, `expr` is the **fragment
  specifier**, which says what **kind of syntax** it must match. Because
  `$x` is matched as one **expression**, the substitution keeps its
  structure. You get `(3 + 1) * (3 + 1)`, **not** `3 + 1 * 3 + 1` (which would
  be 7, the classic C preprocessor bug).
- Common fragment specifiers:

| Specifier | Matches | Example |
|---|---|---|
| `expr` | an expression | `a + 1`, `foo()` |
| `ident` | a name | `Config`, `port` |
| `ty` | a type | `Vec<String>` |
| `pat` | a pattern | `Some(x)` |
| `stmt` | a statement | `let x = 1` |
| `block` | a `{ ... }` block | `{ a; b }` |
| `item` | an item (fn, struct, ...) | `fn f() {}` |
| `path` | a path | `std::fmt::Debug` |
| `literal` | a literal | `"text"`, `42` |
| `lifetime` | a lifetime | `'a` |
| `vis` | a visibility (may be empty) | `pub(crate)` |
| `tt` | **one token tree**: anything in matched brackets, or a single token | `x`, `(a, b)` |

- A macro must be **defined before it is used** in the file (textual order),
  unless it is exported with `#[macro_export]`.
- A bad **follow-set** is rejected when the macro is defined. After `$e:expr`
  only `=>`, `,` or `;` may follow, so `$e:expr $f:expr` is an error:

```text
error: `$e:expr` is followed by `$f:expr`, which is not allowed for `expr` fragments
 --> compile_fail/macro_fragment_follow.rs:3:14
  |
3 |     ($e:expr $f:expr) => {
  |              ^^^^^^^ not allowed after `expr` fragments
  |
  = note: allowed there are: `=>`, `,` or `;`
```

- Calling with input that matches **no** rule gives:

```text
error: unexpected end of macro invocation
 --> compile_fail/macro_no_rules_matched.rs:9:20
  |
2 | macro_rules! pair {
  | ----------------- when calling this macro
...
9 |     let p = pair!(1);
  |                    ^ missing tokens in macro arguments
  |
note: while trying to match `,`
```

## 3. "How do repetition and recursion work?"

```rust
macro_rules! hashmap {
    ($($k:expr => $v:expr),* $(,)?) => {{
        let mut m = HashMap::new();
        $( m.insert($k, $v); )*
        m
    }};
}

macro_rules! max {
    ($x:expr) => ($x);
    ($x:expr, $($rest:expr),+) => {{
        let a = $x;
        let b = max!($($rest),+);
        if a > b { a } else { b }
    }};
}

let m = hashmap! { "a" => 1, "b" => 2, };
let biggest = max!(3, 9, 4);
```

```text
hashmap! = [("a", 1), ("b", 2)]
max!(3, 9, 4) = 9
```

**Answer:**

- **Repetition** is written `$( ... ) separator repeat`. The repeat is `*`
  (zero or more), `+` (one or more) or `?` (zero or one). `$(,)?` allows an
  optional trailing comma.
- In the template, any metavariable that was matched inside `$( ... )*` must be
  used inside a matching `$( ... )*`. The block is **repeated once for each
  match**.
- **Recursion**: a macro can call itself. `max!` peels off the first
  argument and recurses on the rest. The recursion happens **at compile
  time**, so the result is plain nested `if`s. There is a **recursion
  limit** (128 by default: a `count!` over 140 tokens fails with "recursion limit reached while expanding"). Raise it with `#![recursion_limit = "256"]`.
- The double braces `{{ ... }}` make the expansion **a block expression** so
  it can hold `let` statements and still be used as a value.

## 4. "Can a macro generate structs and methods?"

```rust
macro_rules! make_struct {
    ($name:ident { $($field:ident : $ty:ty),* $(,)? }) => {
        #[derive(Debug)]
        struct $name { $($field: $ty),* }
        impl $name {
            $( fn $field(&self) -> &$ty { &self.$field } )*
            fn field_names() -> &'static [&'static str] { &[$(stringify!($field)),*] }
        }
    };
}
make_struct!(Config { host: String, port: u16 });
```

```text
Config { host: "localhost", port: 8080 } host()=localhost port()=8080 fields=["host", "port"]
```

**Answer:**

- Yes. A macro at item position can expand to any **items**. Here one line
  produces a struct, a getter for each field, and a list of field names.
- `stringify!($field)` turns a token into a string literal at compile time.
  `concat!`, `line!`, `file!`, `env!` and `include_str!` are built-in macros
  of the same family.
- This is the usual use of `macro_rules!`: **removing repetitive boilerplate**,
  for example implementing a trait for ten integer types:

```rust
macro_rules! impl_double {
    ($($t:ty),*) => { $( impl Double for $t { fn double(&self) -> Self { self * 2 } } )* };
}
impl_double!(i8, i16, i32, i64, u8, u16, u32, u64);
```

- Counting tokens at compile time needs recursion, because there is no
  built-in counter:

```rust
macro_rules! count {
    () => (0usize);
    ($head:tt $($tail:tt)*) => (1usize + count!($($tail)*));
}
const N: usize = count!(a b c d e);   // 5
```

```text
count!(a b c d e) = 5
```

- The expansion of `count!(a b c)` is `1usize + (1usize + (1usize + 0usize))`,
  which the compiler folds to a constant. It costs **nothing at run time**.

## 5. "What is a tt-muncher, and what are internal rules?"

```rust
macro_rules! settings {
    (@acc $vec:ident;) => {};
    (@acc $vec:ident; $key:ident = $val:expr; $($rest:tt)*) => {
        $vec.push((stringify!($key), $val.to_string()));
        settings!(@acc $vec; $($rest)*);
    };
    ($($body:tt)*) => {{
        let mut v: Vec<(&str, String)> = Vec::new();
        settings!(@acc v; $($body)*);
        v
    }};
}

let s = settings! { name = "demo"; retries = 3; debug = true; };
```

```text
settings! = [("name", "demo"), ("retries", "3"), ("debug", "true")]
```

**Answer:**

- A **tt-muncher** is a recursive macro that takes its input as raw token
  trees (`$($body:tt)*`) and **eats one piece per step** (`key = value;`), then
  recurses on the leftover (`$($rest:tt)*`). It lets you invent syntax that
  `expr` or `ty` cannot parse, such as `name = "demo";`.
- The **`@acc`** rules are **internal rules**: by convention a leading `@name`
  marks a private helper rule inside the same macro. The public rule (last
  one) sets up state and calls the helper. This avoids exporting extra
  helper macros.
- **Rule order matters**: the specific `@acc` rules come **first**, otherwise
  the catch-all rule would match every call, including the recursive ones.
- Tt-munchers are powerful but **slow to compile** and hard to debug (each step
  re-parses the remainder, so cost grows with input length). If you need a
  grammar this complex, switch to a procedural macro (§7).

## 6. "What is macro hygiene, and what is `$crate`?"

```rust
macro_rules! double_it {
    ($e:expr) => {{
        let x = 2;      // this `x` is invisible to the caller
        $e * x
    }};
}
let x = 10;
double_it!(x + 1)       // uses the CALLER's x = 10, so (10 + 1) * 2
```

```text
double_it!(x + 1) with caller x=10 -> 22
```

```text
error[E0425]: cannot find value `secret` in this scope
  --> compile_fail/macro_hygiene.rs:10:20
   |
10 |     println!("{}", secret);
   |                    ^^^^^^ not found in this scope
   |
help: an identifier with the same name is defined here, but is not accessible due to macro hygiene
```

**Answer:**

- **Hygiene** means a **local variable defined inside a macro** is a
  different variable from one with the same name at the call site. In
  `double_it!`, the macro's `x` (2) does not capture or shadow the caller's
  `x` (10). Without hygiene (as in C macros) the macro's `x` would capture
  the caller's and give a wrong result.
- It works both ways: a `let secret = 42;` inside a macro is **not visible**
  to the caller afterwards (the error above).
- Hygiene covers **local variables and labels**. It does **not** cover
  items: a macro **can** define a function or struct that the caller sees,
  as `make_struct!` did.
- To let the caller name the variable, **take an `ident` as input**:
  `($name:ident) => { let $name = 42; }`.
- **`$crate`** expands to the crate where the macro was **defined**. Always
  use `$crate::path::to::item` for items the macro refers to, so the macro
  still works when exported and called from another crate:

```rust
macro_rules! shout_it {
    ($s:expr) => { $crate::helpers::shout($s) };
}
```

- To export a macro to other crates, add `#[macro_export]`. It then lives at
  the crate root (`my_crate::shout_it!`).

## 7. "What changed for `expr` in edition 2024?"

```rust
macro_rules! takes_expr {
    ($e:expr) => { "matched as expr" };
    ($($t:tt)*) => { "fell through to tt" };
}
macro_rules! takes_expr_2021 {
    ($e:expr_2021) => { "matched as expr_2021" };
    ($($t:tt)*) => { "fell through to tt" };
}
```

Edition 2024:

```text
takes_expr!(const { 1 }) -> matched as expr
takes_expr_2021!(const { 1 }) -> fell through to tt
takes_expr!(_) -> matched as expr
```

The same file compiled with `--edition 2021`:

```text
takes_expr!(const { 1 }) -> fell through to tt
takes_expr_2021!(const { 1 }) -> fell through to tt
takes_expr!(_) -> fell through to tt
```

**Answer:**

- In **edition 2024** the `expr` fragment also matches **`const { ... }`
  blocks** and the **underscore expression `_`**. In 2021 it does not.
- A macro written for 2021 that relies on `const { }` or `_` **falling through**
  to another rule would change behaviour. The new fragment **`expr_2021`**
  keeps the old matching rules, so you can keep the old behaviour in a
  2024 crate.
- The migration (`cargo fix --edition`) rewrites every `expr` to `expr_2021`
  so nothing changes. Usually you **revert** that for macros where you want the
  new expressions, after checking that no other rule would now match
  `const` or `_` by mistake (source: the Edition Guide, "Macro Fragment
  Specifiers").

## 8. "How do procedural macros work, and why must they live in their own crate?"

```toml
# demo_macros/Cargo.toml
[lib]
proc-macro = true

[dependencies]
proc-macro2 = "1.0.107"
quote = "1.0.47"
syn = { version = "3.0.9", features = ["full"] }
```

**Answer:**

- A **procedural macro** is a Rust **function** that the compiler **runs
  during compilation**. It takes a `TokenStream` (the code as tokens) and
  returns a new `TokenStream`.
- There are **three kinds**:
    - **Derive**: `#[derive(Name)]` on a struct or enum, adds `impl`s.
    - **Attribute**: `#[name]` on an item, replaces the item.
    - **Function-like**: `name!(...)`, like `macro_rules!` but with
      arbitrary Rust code to parse and produce.
- The crate must set **`proc-macro = true`**. Such a crate can **only export
  macros** (no ordinary public functions or types), because the compiler
  **loads it as a plugin**, so it must be compiled **first**, for the **host
  machine**, even when you cross-compile.
- That is why you always see **two crates**: `foo` (your library) and
  `foo_macros` (or `foo-derive`). The library re-exports the macros so users
  depend on only one.
- **Three helper crates** do the real work:
    - **`syn`**: parses a `TokenStream` into a typed syntax tree
      (`DeriveInput`, `ItemFn`, `LitStr`...).
    - **`quote`**: the `quote! { ... }` macro builds tokens from a template,
      with `#var` for interpolation and `#(...)*` for repetition.
    - **`proc-macro2`**: a `TokenStream` type that also works **outside** a
      macro (in unit tests), used by `syn` and `quote`.
- **Cost**: `syn` is a large dependency. A clean debug build of the demo macro
  crate with `syn` (feature `full`) took about **2 seconds** on this machine
  (Apple Silicon). The cost is paid again by **every project** that uses a
  derive, which is one reason compile times grow (see
  [How rustc Works](../performance-and-internals/rustc-how-the-compiler-works.md)).
- Proc macros run **arbitrary code** at build time with your permissions. A
  malicious or hijacked proc-macro crate is a supply-chain risk. See
  [CI/CD & Supply Chain](../production/rust-ci-cd-and-supply-chain.md).

## 9. "Show me a derive macro, an attribute macro and a function-like macro."

**Derive**: `#[derive(Describe)]` adds `describe()`, which lists a struct's
fields and types.

```rust
#[proc_macro_derive(Describe)]
pub fn derive_describe(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    let name = &ast.ident;
    let (impl_generics, ty_generics, where_clause) = ast.generics.split_for_impl();
    // ... collect named fields, or return a compile error ...
    quote! {
        impl #impl_generics #name #ty_generics #where_clause {
            pub fn describe() -> String {
                let parts: Vec<String> = vec![ #(#lines),* ];
                format!("{} {{ {} }}", stringify!(#name), parts.join(", "))
            }
        }
    }
    .into()
}
```

```rust
#[derive(Describe)]
struct User { id: u64, name: String, tags: Vec<String> }

#[derive(Describe)]
struct Wrapper<T> { inner: T }
```

```text
User { id: u64, name: String, tags: Vec<String> }
Wrapper { inner: T }
```

- **`split_for_impl`** copies the struct's generics, so `Wrapper<T>` works
  without extra code. Forgetting it is the most common derive bug.
- A derive **adds** code; it never changes the struct itself.

**Attribute**: `#[timed]` wraps a function and prints its run time.

```rust
#[timed]
fn slow_sum(n: u64) -> u64 { (1..=n).sum() }
```

```text
[timed] slow_sum took 8.5µs
slow_sum(1000) = 500500
```

(The time varies on every run.) The macro rebuilds the function's body:
it records `Instant::now()`, runs the **original body** inside a closure,
prints the time, and returns the result. An attribute macro receives the
**whole item** and **replaces** it, so it can wrap, rewrite or remove it.

**Function-like**: `shout!("text")` checks its argument **at compile time** and
expands to an uppercase string literal.

```text
QUIET TEXT
```

- Since **Rust 1.99**, an attribute macro may also be applied to an
  **out-of-line module** (`#[passthrough] mod inner;`, where the module
  body is in `inner.rs`). The macro then receives the module's file
  contents as tokens. This compiled on 1.99.1 in the sample.

## 10. "How do I report errors and debug a macro?"

```text
error: Describe can only be derived for structs
 --> demo_app/compile_fail/derive_on_enum.rs:4:6
  |
4 | enum Color {
  |      ^^^^^
```

```text
error: Describe supports only structs with named fields
 --> demo_app/compile_fail/derive_on_tuple_struct.rs:4:8
  |
4 | struct Pair(u8, u8);
  |        ^^^^
```

```text
error: shout! needs a non-empty string
 --> demo_app/compile_fail/shout_empty.rs:2:33
  |
2 |     let s = demo_macros::shout!("");
  |                                 ^^
```

**Answer:**

- **Never `panic!` in a proc macro.** The error is ugly and has no useful
  location. Return a **compile error with a span** instead:
  `syn::Error::new_spanned(&node, "message").to_compile_error().into()`.
  The compiler then underlines the **user's** code, as above.
- **A span** is a location in the source. Reusing the span of the offending
  token (`lit.span()`, or `new_spanned(&ast.ident, ...)`) points the error at
  the right place. Spans also control **hygiene** in proc macros:
  `Span::call_site()` behaves unhygienically, `Span::mixed_site()` like
  `macro_rules!`.
- `compile_error!("message")` does the same for `macro_rules!`: put it in a
  rule that handles bad input.
- **See what a macro produced**:
    - `cargo expand` (a separate tool: `cargo install cargo-expand`; not
      installed here).
    - `rustc +nightly -Zunpretty=expanded file.rs`, used for the output on
      this page.
    - In a `macro_rules!`, `trace_macros!` and `log_syntax!` exist but are
      **unstable** (nightly).
    - For proc macros, **`println!` is not visible** during build unless you
      use `eprintln!`, and the output appears only when compiling.
- **Test proc macros** with a normal crate that uses them (`demo_app`), and
  with **`trybuild`** (compile-fail tests that compare the error text) for the
  error cases. The samples here use a small shell script (`check_errors.sh`)
  for the same purpose.
- Macro errors often point at the **macro call** instead of the root cause.
  Expand first, then read the generated code.

## 11. "When should I not write a macro?"

**Answer:**

- **Use a function** if you only need to reuse logic. **Use generics and
  traits** if you need to support many types. A macro is the **last** tool.
- Write a macro **only** when:
    - You need a **variable number of arguments** or a custom syntax.
    - You must **generate items** (an `impl` per type, enum variants, tests).
    - You must **inspect the code's structure** (field names, a derive).
    - You want a **compile-time check** a function cannot do.
- Costs: **compile time** (a tt-muncher or a `syn`-heavy derive slows every
  build), **IDE support** (autocompletion often fails inside macro input),
  **error quality**, and **readability**.
- Prefer an **existing** derive from a trusted crate (`serde`, `thiserror`,
  `clap`, `strum`) over writing your own. See
  [Serde & Serialization](../production/rust-serde-and-serialization.md) and
  [Error Handling](../foundations/rust-error-handling.md).
- Prefer **`macro_rules!`** for small repetitive code in one crate. Use a
  **proc macro** only when `macro_rules!` cannot express the syntax or the
  input needs real parsing.
- Keep macros **small and documented**, with examples in the doc comment so
  they are also doc tests.

## 12. "How do AI tools help or hurt here?"

**Answer:**

- **Good at**: drafting a `macro_rules!` for a repetitive `impl`, explaining
  an expansion, and writing the `syn` and `quote` skeleton of a derive.
- **Bad at**: **`syn` and `quote` versions**. Training data mixes `syn`
  1 and 2, and the API changed. Generated code often fails to compile. This
  page's code compiled with `syn 3.0.9`; paste the **current** version and
  fix by reading the docs.
- Models often **forget generics** (`split_for_impl`), **forget to report an
  error** for unsupported input (they `unwrap()` or `panic!`), and forget
  **hygiene** and **`$crate`**.
- A good prompt: give an **input example and the exact expansion you want**,
  then ask for the macro. Check it with `-Zunpretty=expanded`.
- Ask first: "can this be a generic function?" A tool that jumps straight to
  a macro is adding cost.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 13. Interview Questions You're Likely to Get Asked

**Basics**

- "What is the difference between a macro and a function?" — expects compile
  time on tokens, variable arguments, generating items,
  [§1](#1-what-is-a-macro-and-how-is-it-different-from-a-function).
- "What does `$x:expr` mean?" — expects metavariable plus fragment specifier,
  and why `square!(3 + 1)` is 16,
  [§2](#2-how-does-macro_rules-work).
- "What are the three kinds of procedural macros?" — expects derive,
  attribute, function-like,
  [§8](#8-how-do-procedural-macros-work-and-why-must-they-live-in-their-own-crate).

**Depth**

- "What is macro hygiene?" — expects macro locals do not clash with caller
  names, but items are visible,
  [§6](#6-what-is-macro-hygiene-and-what-is-crate).
- "What is `$crate` for?" — expects absolute paths to the defining crate so
  exported macros work,
  [§6](#6-what-is-macro-hygiene-and-what-is-crate).
- "Why must a proc macro be in its own crate?" — expects `proc-macro = true`,
  compiled first for the host, exports only macros,
  [§8](#8-how-do-procedural-macros-work-and-why-must-they-live-in-their-own-crate).
- "What do `syn`, `quote` and `proc-macro2` do?" — expects parse, generate,
  and a portable token type,
  [§8](#8-how-do-procedural-macros-work-and-why-must-they-live-in-their-own-crate).
- "What changed for `expr` in edition 2024?" — expects `const {}` and `_`,
  `expr_2021`,
  [§7](#7-what-changed-for-expr-in-edition-2024).
- "How do you report an error from a proc macro?" — expects spanned
  `compile_error`, not `panic!`,
  [§10](#10-how-do-i-report-errors-and-debug-a-macro).

**Design**

- "How would you count the arguments of a macro at compile time?" — expects
  recursive `count!` over `tt`,
  [§4](#4-can-a-macro-generate-structs-and-methods).
- "When would you avoid a macro?" — expects function or generics first, and the
  compile-time and tooling costs,
  [§11](#11-when-should-i-not-write-a-macro).
- "Why do derive macros slow builds?" — expects `syn` and the macro crate
  compiling first on every dependency tree,
  [§8](#8-how-do-procedural-macros-work-and-why-must-they-live-in-their-own-crate).

---

## Code Samples

All files are in `code_samples/rust/` and were run on Rust 1.99.1.

- `examples/macro_rules.rs` — `square!`, `hashmap!`, `max!`, `make_struct!`,
  `count!`, a tt-muncher with internal rules, hygiene, `$crate`, and the
  `expr` versus `expr_2021` difference.
- `macros_demo/` — a Cargo workspace with its own `Cargo.lock`:
    - `demo_macros/` — the proc-macro crate (`#[derive(Describe)]`,
      `#[timed]`, `shout!`, `#[passthrough]`).
    - `demo_app/` — a binary that uses them, and `compile_fail/` with four
      bad inputs.
    - `check_errors.sh` — compiles each `compile_fail` file and prints the
      error text.
- `compile_fail/macro_fragment_follow.rs`, `macro_no_rules_matched.rs`,
  `macro_hygiene.rs` — the three `macro_rules!` errors quoted above.

```bash
cd code_samples/rust
cargo run --example macro_rules
rustc --edition 2021 -o /tmp/m21 examples/macro_rules.rs && /tmp/m21   # see the 2021 difference

cd macros_demo
cargo run -p demo_app
sh check_errors.sh
rustc +nightly -Zunpretty=expanded some_file.rs      # see an expansion
```
