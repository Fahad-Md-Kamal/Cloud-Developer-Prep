# Capstone skeletons

Ten projects from the page `docs/rust/mastery/rust-capstone-projects.md`.
Each `src/cNN_*.rs` file has:

- the public API you must implement (bodies are `todo!()`),
- acceptance tests marked `#[ignore]`.

Workflow for one project:

```bash
cargo build                                   # the skeleton always compiles
cargo test c01 -- --ignored                   # all red: that is your starting point
# implement, then remove `#[ignore]` from the tests that pass
cargo test c01                                # green
```

Use `cargo test -- --ignored` to see every unfinished project.
Dependencies: the skeletons use only `std`. Add `tokio` (c05, c10 optional),
`loom` (c09) and others yourself with `cargo add`.
