"""Regenerate the Rust section of zensical.toml's nav and of docs/index.md.

Usage (from anywhere):  python3 scripts/generate_rust_nav.py

The page list below is the single source of truth for Rust page order, nav
labels, H1 titles and index descriptions. A page is listed only if its file
exists, so you can add pages one at a time: create the .md file, run this
script, then run scripts/generate_nav_manifest.py and `zensical build --clean`.
"""
import os
import re

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R='rust/'
GROUPS=[
 ('Foundations','foundations',[
  ('rust-toolchain-and-cargo','Toolchain & Cargo','Toolchain & Cargo','rustup, editions, what `cargo build` does, profiles, features, workspaces'),
  ('rust-ownership-and-borrowing','Ownership & Borrowing','Ownership & Borrowing','moves, drop order, the borrow rules and why they exist, reading borrow errors'),
  ('rust-lifetimes','Lifetimes','Lifetimes','elision, structs that borrow, `\'static`, higher-ranked bounds, 2024 `impl Trait` capture'),
  ('rust-types-enums-and-patterns','Types, Enums & Patterns','Types, Enums & Patterns','number rules, enums, every pattern form, let chains, `if let` guards'),
  ('rust-error-handling','Error Handling','Error Handling','`Result` and `?`, `thiserror` vs `anyhow`, panics, error design'),
  ('rust-collections-and-strings','Collections & Strings','Collections & Strings','`Vec` internals, UTF-8 strings, `HashMap`, `BTreeMap`, choosing a container'),
  ('rust-traits-and-generics','Traits & Generics','Traits & Generics','static vs dynamic dispatch, dyn compatibility, associated types, blanket impls'),
  ('rust-iterators-and-closures','Iterators & Closures','Iterators & Closures','lazy adapters, custom iterators, `Fn`/`FnMut`/`FnOnce`, returning closures'),
  ('rust-smart-pointers','Smart Pointers & Interior Mutability','Smart Pointers','`Box`, `Rc`/`Arc`/`Weak`, `RefCell`, `Cow`, `OnceLock`, `Deref`'),
  ('rust-modules-crates-and-editions','Modules, Crates & Editions','Modules, Crates & Editions','privacy rules, re-exports, what each edition changed, the 2024 edition'),
  ('rust-testing-and-documentation','Testing & Documentation','Testing & Docs','unit, integration and doc tests, `proptest`, testable design'),
 ]),
 ('Advanced Language','advanced-language',[
  ('rust-memory-layout-and-dsts','Memory Layout & Dynamically Sized Types','Memory Layout & DSTs','size and alignment, `repr`, niches, fat pointers, `Sized`'),
  ('rust-advanced-traits-and-type-level-design','Advanced Traits & Type-Level Design','Advanced Traits','GATs, higher-ranked bounds, typestate, sealed traits, const generics'),
  ('rust-variance-dropck-and-phantomdata','Variance, Drop Check & PhantomData','Variance & Drop Check','subtyping, invariance, dropck, `PhantomData`, auto traits'),
  ('rust-unsafe-and-miri','Unsafe Rust & Miri','Unsafe & Miri','the five powers, undefined behaviour, aliasing models, `MaybeUninit`, Miri'),
  ('rust-ffi-and-c-interop','FFI & C Interoperability','FFI & C Interop','`extern "C"`, `repr(C)`, bindgen, ownership across the boundary, PyO3'),
  ('rust-macros','Declarative & Procedural Macros','Macros','`macro_rules!`, derive, attribute and function-like proc macros, hygiene'),
 ]),
 ('Concurrency & Async','concurrency-and-async',[
  ('rust-threads-and-synchronization','Threads & Synchronization','Threads & Sync','`Send`/`Sync`, scoped threads, channels, `Mutex`, `Condvar`, rayon'),
  ('rust-atomics-and-memory-ordering','Atomics & Memory Ordering','Atomics & Ordering','`Ordering`, happens-before, CAS loops, building a spinlock'),
  ('rust-async-internals','Async Rust Internals','Async Internals','`Future`, `Poll`, wakers, state machines, `Pin`, writing an executor'),
  ('rust-tokio-and-async-patterns','Tokio & Async Patterns','Tokio & Async Patterns','runtime, tasks, `select!`, cancellation safety, backpressure, shutdown'),
 ]),
 ('Performance & Internals','performance-and-internals',[
  ('rust-performance-engineering','Performance Engineering','Performance Engineering','measuring, profiling, allocation, cache, SIMD, release tuning'),
  ('rustc-how-the-compiler-works','How rustc Works','How rustc Works','pipeline, MIR, borrow checker, monomorphization, compile times'),
  ('rust-no-std-and-embedded','no_std & Embedded Rust','no_std & Embedded','`core` vs `alloc`, panics, allocators, embedded HAL'),
  ('rust-webassembly','Rust & WebAssembly','WebAssembly','targets, `wasm-bindgen`, size tuning, WASI'),
 ]),
 ('Production Rust','production',[
  ('rust-web-services-with-axum','Web Services with Axum','Web Services (Axum)','Tokio, tower, extractors, middleware, state, graceful shutdown'),
  ('rust-databases','Databases in Rust','Databases','`sqlx`, Diesel, pools, transactions, migrations'),
  ('rust-serde-and-serialization','Serde & Serialization','Serde','how derive works, formats, zero-copy, custom (de)serializers'),
  ('rust-observability','Observability: Tracing, Metrics & Logs','Observability','`tracing`, spans, OpenTelemetry, metrics'),
  ('rust-project-architecture-and-api-design','Project Architecture & API Design','Architecture & API Design','workspace layout, API guidelines, semver, error boundaries'),
  ('rust-cli-and-systems-programming','CLI Tools & Systems Programming','CLI & Systems','`clap`, processes, files, signals, memory mapping'),
  ('rust-ci-cd-and-supply-chain','CI/CD & Supply Chain','CI/CD & Supply Chain','pipelines, `cargo deny`/`audit`, containers, reproducible builds'),
 ]),
 ('Mastery','mastery',[
  ('modern-rust-2024-to-1-99','Modern Rust: 2024 Edition to 1.99','Modern Rust','what changed from Rust 1.85 to 1.99, release by release'),
  ('rust-for-python-go-and-kotlin-developers','Rust for Python, Go & Kotlin Developers','Rust for Python/Go/Kotlin','idiom translation tables and the traps for each background'),
  ('rust-capstone-projects','Capstone Projects','Capstone Projects','ten graded projects from a CLI tool to a lock-free queue'),
  ('rust-guru-question-bank','Guru Question Bank','Guru Question Bank','deep questions with answers, grouped by topic'),
 ]),
]
toml_lines=['  { "Rust" = [\n','      { "Learning Roadmap" = "rust/rust-learning-roadmap.md" },\n']
idx=['### Rust\n\n',
'A deep, version-checked track for becoming a Rust expert, written for\n',
'**Rust 1.99** and the **2024 edition**. Every page has runnable code\n',
'in `code_samples/rust/` that was compiled and run, and real compiler\n',
'errors. Start at the roadmap, then follow the groups in order.\n\n',
'- [Rust Learning Roadmap](rust/rust-learning-roadmap.md) — the path, the stages, how to practice, and the reading list\n']
for title,folder,pages in GROUPS:
    items=[p for p in pages if os.path.exists(f'docs/rust/{folder}/{p[0]}.md')]
    if not items: continue
    toml_lines.append(f'      {{ "{title}" = [\n')
    idx.append(f'- **{title}**\n')
    for stem,h1,label,desc in items:
        toml_lines.append(f'          {{ "{label}" = "rust/{folder}/{stem}.md" }},\n')
        idx.append(f'    - [{h1}](rust/{folder}/{stem}.md) —\n      {desc}\n')
    toml_lines.append('      ] },\n')
toml_lines.append('  ] },\n')
t=open('zensical.toml').read()
# remove existing Rust block
m=re.search(r'  \{ "Rust" = \[\n.*?\n  \] \},\n',t,re.S)
block=''.join(toml_lines)
if m: t=t[:m.start()]+block+t[m.end():]
else:
    a='  { "Backend" = ['
    assert a in t
    t=t.replace(a,block+a,1)
open('zensical.toml','w').write(t)
x=open('docs/index.md').read()
body=''.join(idx)
m=re.search(r'### Rust\n.*?(?=\n### )',x,re.S)
if m: x=x[:m.start()]+body.rstrip('\n')+'\n'+x[m.end():]
else:
    a='### Backend\n'
    assert a in x
    x=x.replace(a,body+'\n'+a,1)
open('docs/index.md','w').write(x)
print('nav + index updated')
