# Rust samples

Runnable code for the [Rust track](../../docs/rust/rust-learning-roadmap.md).
Written and run on **Rust 1.99.1**, edition 2024. Install with `rustup`.

## Layout

| Path | What it is | How to run |
|---|---|---|
| `examples/*.rs` | One file per page topic (std only) | `cargo run --example NAME` |
| `compile_fail/*.rs` | Files that must **fail** to compile; their error text is quoted in the pages | `rustc --edition 2024 --emit=metadata -o /dev/null compile_fail/FILE.rs` |
| `src/lib.rs`, `tests/` | Unit, integration, doc and property tests | `cargo test` |
| `internals/` | Plain `rustc` files for the compiler page | see the page |
| `async_demo/` | Tokio, rayon, loom | `cargo run --example tokio_patterns` inside it |
| `ffi_demo/` | C interop (`build.sh` builds and runs the C program) | `./build.sh` |
| `macros_demo/` | Proc-macro workspace | `cargo run` inside `demo_app/` |
| `perf_demo/`, `nostd_demo/`, `wasm_demo/`, `wasm_bindgen_demo/` | Performance, `no_std`, WebAssembly | see each page |
| `axum_api/`, `sqlx_demo/`, `serde_demo/`, `tracing_demo/`, `cli_grep/`, `arch_demo/`, `semver_demo/`, `ci_demo/` | Production pages | see each page |
| `capstones/` | Skeletons for the ten capstone projects (`todo!()` bodies, ignored tests) | `cargo test -- --ignored` once you implement one |

Each folder with its own `Cargo.toml` is a separate package with its own
dependencies, so the root crate stays dependency-light.

## Notes

- `examples/ub_cases.rs` has deliberate undefined behaviour. Run it only
  under Miri: `cargo +nightly miri run --example ub_cases`.
- Timings on the performance page come from one Apple-silicon Mac and will
  differ on your machine.
- The root crate allows a few clippy lints on purpose, because the
  samples demonstrate the pitfalls those lints flag.
- Check the root crate: `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test`.
