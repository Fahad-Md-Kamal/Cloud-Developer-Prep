---
title: CI/CD and Supply Chain
---

# CI/CD and Supply Chain

**CI** (Continuous Integration) is a machine that builds and tests every
change before it is merged. **CD** (Continuous Delivery or Deployment) is
the machine that then packages and ships it. The **supply chain** is
everything you did not write but run anyway: your dependencies, the build
tools, the base image of your container. A typical Rust program pulls in
dozens to hundreds of crates, and **build scripts and procedural macros
execute code on your machine at build time**, so supply-chain care is part
of the job. Rust's tooling is good here: a pinned `Cargo.lock`, a
central registry with advisories, and checking tools that run in seconds.

!!! note "Version"
    Written for **Rust 1.99** and the **2024 edition**. Tools run for this
    page: `cargo-deny` 0.20.2, `cargo-audit` 0.22.2 (1,395 advisories
    loaded), Docker with `rust:1.99-alpine`. Latest versions on crates.io:
    `cargo-vet` 0.10.3, `cargo-dist` 0.32.0, `cargo-release` 1.1.7,
    `cargo-chef` 0.1.78. GitHub Action major versions were read from their
    git tags: `actions/checkout` v7, `Swatinem/rust-cache` v2,
    `EmbarkStudios/cargo-deny-action` v2. **Not run:** the workflow itself
    (it needs GitHub), `cargo vet`, `cargo dist`, `cargo release`,
    cross-compilation with `cross` or `cargo zigbuild`, and publishing.

## 1. "What does a good Rust CI pipeline run?"

```yaml
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: dtolnay/rust-toolchain@stable
        with: { components: "rustfmt, clippy" }
      - uses: Swatinem/rust-cache@v2
      - run: cargo fmt --all -- --check
      - run: cargo clippy --workspace --all-targets --locked -- -D warnings
      - run: cargo test --workspace --locked
      - run: cargo doc --workspace --no-deps --locked
        env: { RUSTDOCFLAGS: "-D warnings" }
```

**Answer:**

- The steps, cheapest first, so failures come fast:

| Step | What it catches |
|---|---|
| `cargo fmt --check` | Formatting. Fails if the code is not what `rustfmt` would write. |
| `cargo clippy -- -D warnings` | Likely bugs and unidiomatic code. `-D warnings` turns every warning into an error. |
| `cargo test` | Unit, integration and doc tests (see [Testing & Documentation](../foundations/rust-testing-and-documentation.md)). |
| `cargo doc` with `RUSTDOCFLAGS=-D warnings` | Broken links in documentation. |
| MSRV job | The code builds on your minimum supported Rust version (see below). |
| Supply-chain job | Advisories, licenses, banned crates (§3). |

- **`--locked` everywhere.** It makes Cargo **fail** if `Cargo.lock` is
  out of date, instead of silently updating it. CI then builds exactly
  what is committed. Commit `Cargo.lock` for applications; for libraries
  it is optional but useful for CI. (Details:
  [Toolchain & Cargo §5](../foundations/rust-toolchain-and-cargo.md#5-how-do-versions-cargolock-and-the-resolver-work).)
- **`RUSTFLAGS="-D warnings"`** as a CI-only environment variable is
  common. Do **not** put `#![deny(warnings)]` in the source: a new
  compiler release adds a lint, and your build breaks on a day you changed
  nothing.
- **MSRV job:** install the exact toolchain named by `rust-version` in
  `Cargo.toml` and run `cargo check`. This is what makes the MSRV a
  tested promise (policy in
  [Architecture & API Design §8](rust-project-architecture-and-api-design.md#8-what-is-an-msrv-policy-and-what-should-mine-be)).
- **Matrix builds** (`strategy.matrix`) run the same job on Linux, macOS
  and Windows, or on `stable` and `beta`. A `beta` job catches
  compiler regressions early. Run it as allowed-to-fail.
- The file in the sample was parsed as valid YAML; it was **not run** on
  GitHub. It lives in `code_samples/rust/ci_demo/ci/rust-ci.yml`, outside
  `.github/workflows/`, so it does nothing here.
- Pin third-party actions by **commit SHA** in high-security projects. A
  tag like `@v7` can be moved by the action's owner.

## 2. "How do I make CI builds fast?"

**Answer:**

- **Why Rust CI is slow:** a fresh runner compiles **every dependency from
  scratch** on every run. The compile step dominates (see
  [How the Compiler Works](../performance-and-internals/rustc-how-the-compiler-works.md)
  for why).
- **`Swatinem/rust-cache`** saves `target/` and the Cargo registry between
  runs. Its cache key includes the current `rustc` version, a hash of all
  `Cargo.toml`, `Cargo.lock` and toolchain files, and the job name
  (from its README). When any of them changes, you get a fresh cache. This
  is the default choice.
- **`sccache`** is a shared compiler cache (local disk or cloud storage)
  that caches individual compiler outputs. Better for large monorepos and
  several machines; more setup.
- **Faster feedback:** run `cargo check` (no code generation) for the
  quick job and the full `cargo test` in a second job in parallel.
- **Fewer dependencies and fewer features** speed up every build. The
  `--timings` flag (`cargo build --timings`) writes an HTML report of what
  took the time.
- Do not restore `target/` built by a **different toolchain version**:
  stale artifacts waste time or cause odd errors. The key above prevents
  it. If you cache by hand, put the Rust version in the key.

## 3. "How do I defend against bad dependencies?"

```bash
cargo install cargo-deny cargo-audit --locked
cargo deny check      # advisories, licenses, bans, sources
cargo audit           # Cargo.lock against the RustSec advisory database
```

Real output from the sample crate (`serde_json` and its 11 dependencies):

```text
advisories ok, bans ok, licenses ok, sources ok
```

```text
Fetching advisory database from `https://github.com/RustSec/advisory-db.git`
Loaded 1395 security advisories
Scanning Cargo.lock for vulnerabilities (12 crate dependencies)
```

(exit code 0: nothing found)

**Answer:**

- **`cargo audit`** checks `Cargo.lock` against the **RustSec advisory
  database**: known vulnerabilities, unmaintained crates, yanked
  versions. Run it on a **schedule** (daily), not only on commits:
  new advisories appear for code you did not change.
- **`cargo deny`** is the policy engine. Four checks, configured in
  `deny.toml`:

| Check | Question it answers |
|---|---|
| `advisories` | Any known vulnerabilities, or yanked versions (`yanked = "deny"`)? |
| `licenses` | Is every dependency's license on my allow list? |
| `bans` | Any crate I forbid, or several versions of one crate (`multiple-versions = "warn"`), or wildcard version requirements? |
| `sources` | Does everything come from the registries and repositories I allow (no unknown git dependencies)? |

- The sample `deny.toml` allows `MIT`, `Apache-2.0` and `Unlicense`
  (found: `memchr` is "Unlicense OR MIT"). Removing `MIT` and `Unlicense`
  from the list to see the check fail gave real errors such as:

```text
error[rejected]: failed to satisfy license requirements
48 │ license = "Unlicense OR MIT"
   │            rejected: license is not explicitly allowed
```

  A license policy matters legally: a copyleft license in a dependency can
  change what you may do with your own code. Ask your legal team which
  licenses are allowed; this page is not legal advice.
- **`cargo vet`** answers a different question: "has a **human I trust**
  reviewed this version?" Teams record audits (or import audits published
  by organizations they trust) and `cargo vet` fails on unreviewed
  dependencies. High effort, high value for security-critical software.
  Not run here.
- **Build scripts (`build.rs`) and procedural macros run arbitrary code
  at compile time**, with your user's permissions, in CI and on developer
  machines. A malicious crate does not need to be *called*; compiling it is
  enough. Mitigations: review new dependencies (their `build.rs`), keep the
  dependency list small, run CI without secrets on pull requests from
  forks, and build in a container or sandbox. (Background:
  [Toolchain & Cargo §8](../foundations/rust-toolchain-and-cargo.md#8-what-are-build-scripts-and-when-do-you-need-one).)
- **Typosquatting:** crates with names close to popular ones. Check the
  exact name and the download count before adding a dependency, and prefer
  well-known maintainers.
- **Updates are also risk management.** Dependabot or Renovate open pull
  requests for new versions; CI runs on them. Staying current means you get
  security fixes in small steps rather than one big jump.

## 4. "Can I get the same binary every time? (Reproducible builds)"

**Answer:**

- A **reproducible build** produces **bit-for-bit identical** output from
  the same source. It lets anyone check that a published binary really
  came from the published source.
- What I measured on the sample crate (macOS, Rust 1.99.1, release
  profile), comparing the SHA-256 (Secure Hash Algorithm) of the binary:

| Experiment | Same hash? |
|---|---|
| Same directory, same flags, built twice | **Yes** |
| Same sources copied to a different directory | **No**, with or without `--remap-path-prefix` |
| With `--remap-path-prefix`, strings in the binary containing the build directory's path | Went from 1 to **0** |

- Reading the results:
    - Builds are **deterministic** when the inputs are identical.
    - `--remap-path-prefix=FROM=TO` rewrites paths embedded in the binary
      (panic messages, debug info) so your username and directory layout
      do not leak. It worked: the path string disappeared.
    - But the **hash still changed** when the project moved. For a
      package that is a path dependency of itself, Cargo mixes its
      location into its identity, so symbol names changed. I did not
      chase the exact source further.
    - **Practical rule:** build in a **fixed path** (a container with
      `WORKDIR /app`), with pinned inputs: the same toolchain, the same
      `Cargo.lock` (`--locked`), the same flags, and `--remap-path-prefix`
      for paths you do not want embedded. That is what the Dockerfile in
      §6 does.
- Rust **1.95** stabilized **`--remap-path-scope`**, which chooses
  *where* remapping applies (macros, diagnostics, debug info, object
  files). The flag is accepted on stable 1.99 (checked). Read the "Remap
  source paths" section of the rustc book before using it.
- Other inputs that break reproducibility: timestamps, `build.rs` that
  reads the environment or the clock, and different C compilers or linkers.
  Set `SOURCE_DATE_EPOCH` if a build script embeds a date.

## 5. "How do I build for other platforms?"

**Answer:**

- **A target** is a triple such as `x86_64-unknown-linux-gnu` or
  `aarch64-apple-darwin`. `rustup target add <triple>` downloads the
  standard library for it, and `cargo build --target <triple>` builds.
- The hard part is the **linker and C libraries**, not Rust. You need a
  linker for the target.
- Three practical ways:
    - **Build natively in CI** on a runner of that operating system
      (simplest and most reliable; the usual choice for desktop tools).
    - **`cross`**: runs `cargo` inside a Docker image that has the right
      toolchain. Needs Docker.
    - **`cargo zigbuild`**: uses the Zig compiler as the linker, so one
      machine can target many platforms (and pick an older glibc version).
- **Static Linux binaries** use the **musl** C library: the target
  `x86_64-unknown-linux-musl`, or build inside `rust:alpine` as in §6.
  Caveats: musl's memory allocator is slower than glibc's for some
  allocation-heavy programs (consider swapping the global allocator and
  measure), and some C dependencies do not build on musl.
- Not run here (the Docker build in §6 is the musl case, and it ran).

## 6. "How do I put a Rust program in a small container?"

```dockerfile
# Multi-stage build: compile in a full toolchain image, ship only the binary.
FROM rust:1.99-alpine AS build
RUN apk add --no-cache musl-dev
WORKDIR /app
# 1) Cache dependencies: copy only the manifests and build a dummy main first.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main() {}' > src/main.rs \
 && cargo build --release --locked && rm -rf src target/release/hello-ci* target/release/deps/hello_ci*
# 2) Build the real code (only this layer reruns when source changes).
COPY src ./src
RUN cargo build --release --locked

# Final image: no shell, no libc, no package manager. Only the static binary.
FROM scratch
COPY --from=build /app/target/release/hello-ci /hello-ci
USER 10001
ENTRYPOINT ["/hello-ci"]
```

Real results:

```text
$ docker run --rm hello-ci:demo
{"app":"hello-ci","ok":true}

image size: 215992 bytes   (about 211 KB)

$ docker run --rm --entrypoint sh hello-ci:demo
... exec: "sh": executable file not found in $PATH      (message shortened)
```

**Answer:**

- **Multi-stage build:** the first stage has the compiler (hundreds of
  MB); the last stage copies **only the finished binary**. The final image
  here is about **211 KB**, because `FROM scratch` is an *empty* image and
  the binary is statically linked (the `rust:alpine` image targets musl,
  so the binary needs no libc).
- **Smaller attack surface for free:** the final image has **no shell,
  no package manager and no libc**. The run above shows `sh` does not
  exist. A compromised process has little to work with. `USER 10001`
  makes it run as a non-root user.
- **The dependency-caching trick:** Docker caches each layer. Copying only
  `Cargo.toml` and `Cargo.lock` and building a dummy `main` makes
  dependencies their own layer, rebuilt only when the lock file changes.
  Editing source then reruns just the last `cargo build`. `cargo-chef`
  automates the same idea for workspaces (not run here).
- **Choosing the final image:**

| Final image | Size | Has | Use when |
|---|---|---|---|
| `scratch` | tiny | Nothing (no shell, no CA certificates, no timezone data) | Static musl binary that needs nothing else |
| `gcr.io/distroless/static` and similar | small | CA certificates, timezone data, a non-root user | Same, plus HTTPS to outside servers |
| `debian:*-slim` or `alpine` | tens of MB | Shell, package manager | You need debugging tools, or dynamic linking to glibc |

- **Pitfall:** a `scratch` image has **no CA (Certificate Authority) root
  certificates**, so a program that makes HTTPS requests will fail to
  verify servers (unless the TLS crate bundles roots, as `webpki-roots`
  does). Copy certificates in or use distroless.
- **Pitfall:** `cargo build --release` inside Docker on a Mac builds
  for the container's architecture (Linux, possibly ARM). If you deploy to
  a different CPU, build with `--platform`.
- **Tag with something immutable** (the Git commit SHA) and, for
  high-security setups, reference base images by digest.
- Do not copy `target/`, `.git` or secrets into the build context. Use a
  `.dockerignore`.

## 7. "How do I release and publish a crate or a binary?"

**Answer:**

- **Before publishing a library:** run `cargo semver-checks` (see
  [Architecture & API Design §5](rust-project-architecture-and-api-design.md#5-what-changes-break-my-users-how-do-i-keep-semver)),
  update the changelog, set `rust-version`, `license`, `description` and
  `repository` in `Cargo.toml`, and run **`cargo publish --dry-run`** (it
  packages and builds the crate exactly as crates.io would, without
  uploading).
- **`cargo publish`** uploads to crates.io. **A published version is
  permanent**: you cannot delete or overwrite it. That is why the dry run
  matters.
- **Workspaces:** `cargo publish` can publish several packages in the
  workspace in one go (`--workspace`, or several `-p`), in dependency
  order; this was added in Rust 1.90. Checked: both flags appear in
  `cargo publish --help` on 1.99.
- **Yanking** (`cargo yank --version 1.0.1`): marks a bad version so **no
  new dependency can pick it**, while projects that already have it in
  `Cargo.lock` keep working. **A yank does not delete code or secrets.** If
  you published a secret, **rotate it immediately**; the Cargo book says
  this explicitly. `cargo yank --version 1.0.1 --undo` reverses it.
- **Automating releases:**
    - **`cargo release`** (`cargo-release` 1.1.7): bumps versions,
      updates the changelog, tags, publishes, in one command, usually
      run in CI or by a maintainer.
    - **`cargo dist`** (0.32.0): builds release binaries for several
      platforms in CI, makes installers (shell script, Homebrew, MSI,
      npm), and attaches them to a GitHub release.
- **Tokens:** publishing from CI needs a crates.io API token stored as a CI
  secret. Check the crates.io documentation for token-less ("trusted")
  publishing from CI. I could not read that page while writing, so this
  page does not describe it.
- **Release builds** should use the release profile settings from the
  sample (`lto = true`, `codegen-units = 1`, `panic = "abort"`,
  `strip = true`). These trade compile time for smaller and faster
  binaries (see
  [Performance Engineering](../performance-and-internals/rust-performance-engineering.md)).
  The sample binary is 335,536 bytes on macOS with these settings.

## 8. "How do AI tools help or hurt with CI and supply chain?"

**Answer:**

- Good for: drafting workflow YAML, Dockerfiles and `deny.toml`, and
  explaining a `cargo deny` or `cargo audit` report.
- They write **old action versions** (`actions/checkout@v3`, the
  deprecated `actions-rs/*` actions) from their training data. Check the
  current major version in the action's repository.
- They **hallucinate crate names**, and attackers register those names
  ("slopsquatting"). Never add a dependency an assistant suggested
  without checking the crate exists, who owns it, and how much it is used.
- They often put `COPY . .` before `cargo build` in a Dockerfile, which
  destroys layer caching (§6), and use a full `rust` image as the
  final stage.
- They love `#![deny(warnings)]` in source (§1) and `latest` image tags.
- Never paste secrets, tokens or private keys into a prompt, and give CI
  AI agents the least permission that works.
- See [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Pipeline**

- "What does your Rust CI run?" — expects fmt, clippy with `-D warnings`,
  test, doc, MSRV, `cargo deny`, all with `--locked`,
  [§1](#1-what-does-a-good-rust-ci-pipeline-run).
- "Why `--locked`?" — expects CI fails if the lock file is stale instead
  of changing silently,
  [§1](#1-what-does-a-good-rust-ci-pipeline-run).
- "Why is `#![deny(warnings)]` in source a bad idea?" — expects new
  compiler lints break a build nobody touched; use `RUSTFLAGS` in CI,
  [§1](#1-what-does-a-good-rust-ci-pipeline-run).
- "How do you speed up Rust CI?" — expects a build cache, `cargo check`
  jobs, fewer dependencies, `--timings`,
  [§2](#2-how-do-i-make-ci-builds-fast).

**Supply chain**

- "What is the difference between `cargo audit`, `cargo deny` and `cargo
  vet`?" — expects known vulnerabilities; policy (licenses, bans,
  sources); human review,
  [§3](#3-how-do-i-defend-against-bad-dependencies).
- "Why is adding a dependency a security decision?" — expects `build.rs`
  and procedural macros run code at build time,
  [§3](#3-how-do-i-defend-against-bad-dependencies).
- "What does `cargo yank` do?" — expects blocks new resolution, keeps
  existing lock files working, does not delete or protect secrets,
  [§7](#7-how-do-i-release-and-publish-a-crate-or-a-binary).
- "How do you get reproducible builds?" — expects fixed path, pinned
  toolchain and lock file, path remapping, no timestamps,
  [§4](#4-can-i-get-the-same-binary-every-time-reproducible-builds).

**Delivery**

- "How do you build a minimal container for a Rust service?" — expects
  multi-stage, musl static binary, `scratch` or distroless, a dependency
  caching layer, non-root user,
  [§6](#6-how-do-i-put-a-rust-program-in-a-small-container).
- "What breaks in a `scratch` image?" — expects no CA certificates, no
  timezone data, no shell to debug with,
  [§6](#6-how-do-i-put-a-rust-program-in-a-small-container).
- "How do you ship a CLI for several platforms?" — expects native runners
  or `cross`/`zigbuild`, `cargo dist`,
  [§5](#5-how-do-i-build-for-other-platforms),
  [§7](#7-how-do-i-release-and-publish-a-crate-or-a-binary).

---

## Code Samples

Package `code_samples/rust/ci_demo/` (own `Cargo.toml`; Rust 1.99.1).

- `src/main.rs` — a tiny program that prints a JSON line.
- `ci/rust-ci.yml` — an example GitHub Actions workflow (not active: it is
  outside `.github/workflows/`).
- `deny.toml` — the `cargo deny` policy used above.
- `Dockerfile` — the multi-stage, `scratch` image build.

```bash
cd code_samples/rust/ci_demo
cargo install cargo-deny cargo-audit --locked
cargo deny check
cargo audit
docker build -t hello-ci:demo .
docker run --rm hello-ci:demo
docker image inspect hello-ci:demo --format '{{.Size}} bytes'
```
