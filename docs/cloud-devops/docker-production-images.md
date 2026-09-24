---
title: "Docker: Production Container Images"
---

# Docker: Production Container Images

Building a container image that's actually fit to run in production, not
just one that works on a laptop. The gap between the two is a short,
concrete checklist rather than a large topic, so this page stays short
too — each item below is the real substance behind one line of that
checklist, not padding to make it look longer.

## A Small, Cacheable Dockerfile

- Docker builds a Dockerfile top to bottom as a stack of layers, and
  caches each layer — a build only re-runs from the first instruction
  that actually changed, reusing every layer above it.
- Ordering matters because of that cache: instructions that change
  rarely (installing OS packages, installing dependencies from a lock
  file) belong near the top, and instructions that change on every
  commit (copying application source) belong at the bottom.
- Get that order backwards — copy the whole source tree before
  installing dependencies, say — and every single commit invalidates
  the dependency-install layer too, so a one-line code change triggers
  a full dependency reinstall on every build.
- Image size compounds the same way: unnecessary packages, build
  toolchains left behind, and package-manager caches not cleaned up in
  the same layer they were created in all end up shipped in the final
  image, making it slower to pull, slower to push, and larger to store
  than it needs to be.
- A `.dockerignore` matters for the same reason a `.gitignore` does —
  without one, `COPY . .` drags `.git`, local virtualenvs, and
  `node_modules` into the build context and into cache invalidation.

## Multi-Stage Builds

- A multi-stage build uses more than one `FROM` in a single Dockerfile —
  an early stage does the compiling/building with a full toolchain, and
  a later stage copies only the finished artifact out of it into a
  clean, minimal base image.
- Without this, a compiled language's production image ends up shipping
  the entire compiler and build toolchain alongside the actual binary —
  dead weight that's never used at runtime but still adds attack surface
  and download size.
- It applies just as well to interpreted languages with build steps —
  installing dev/build dependencies to compile a native extension or
  bundle frontend assets, then copying only the result into a stage that
  never installed those build dependencies at all.
- The practical payoff is a production image that's both smaller and has
  a smaller set of installed tools an attacker could use if they ever
  got a shell inside the container.

## Non-Root Users

- A container's default user, unless a Dockerfile says otherwise, is
  `root` — the same as running every production application as an
  administrator by default.
- That matters most for container *breakout* risk: a process running as
  `root` inside the container that finds a way to escape the container
  boundary lands as `root` on the host, whereas a non-root process
  escaping the same way lands as an unprivileged user.
- Fixing it is a couple of Dockerfile lines — create a dedicated user
  and group, `chown` the files the app needs, and switch to that user
  with `USER` before the process starts — but it has to be deliberate,
  since the default is silently insecure.
- It also catches real bugs early: an application that assumes it can
  write anywhere, or bind to a privileged port below 1024, fails
  immediately under a non-root user in a way it never would running as
  root, surfacing the assumption in development instead of in an
  incident.

## Health Endpoints

- A container that's *running* and a container that's actually *ready
  to serve traffic* aren't the same thing — a process can be up while
  still connecting to a database, warming a cache, or simply deadlocked
  without ever crashing.
- A dedicated health endpoint (or a `HEALTHCHECK` instruction hitting
  one) gives the orchestrator — Docker Compose, ECS, Kubernetes,
  whatever's scheduling the container — an actual signal to act on:
  don't route traffic to this instance yet, or restart it, it's stuck.
- Without one, the orchestrator's only signal is whether the process is
  still alive, which means a hung-but-alive process keeps receiving
  traffic indefinitely — the failure mode a health check exists
  specifically to catch.
- A real health check should verify the things that would actually make
  the service unable to do its job (can it reach its database, is a
  required cache connected), not just return `200 OK` unconditionally —
  the latter defeats the entire point.

## Configuration Through the Environment, Not Baked Into the Image

- The same image that gets tested in staging should be the exact image
  that runs in production — the only thing that should differ between
  environments is configuration (database URLs, feature flags, API
  keys), never the image itself.
- Baking environment-specific values into the image at build time breaks
  that: it means building a separate image per environment, which means
  what actually ran in staging is no longer provably the same artifact
  running in production.
- Reading configuration from environment variables (or files mounted at
  runtime, for larger config) at process start instead keeps one image
  portable across every environment it needs to run in.
- Secrets are the sharper version of the same rule: a secret baked into
  an image layer is recoverable by anyone who can pull that image, even
  if a later layer "removes" it — layers are additive, not a diff, so
  a secret written in one layer and deleted in the next is still sitting
  in the image history.

## Tagging by Commit

- The `latest` tag is a moving target — it points at whatever was most
  recently pushed, which means it's impossible to know which actual code
  is running just by looking at "we deployed `latest`."
- Tagging every build with something immutable and traceable — a Git
  commit SHA, most commonly — means a running container's tag is
  literally the answer to "what code is this," and rolling back is
  exactly "redeploy the previous tag," not "figure out what the previous
  version actually was."
- `latest` still has a place as a convenience pointer for local
  development, but it shouldn't be what production actually deploys —
  production should always pin an explicit, immutable tag.

## ECR and Image Scanning

- A private registry (Amazon ECR, on AWS) is where built images actually
  live between being pushed by CI and being pulled by whatever's running
  them — the same role Docker Hub plays for public images, but private
  and with IAM controlling who can push or pull.
- ECR can scan every pushed image against known CVE databases and
  surface vulnerabilities found in OS packages and language dependencies
  baked into the image — catching a vulnerable base image or dependency
  before it's ever deployed, not after.
- Combined with the smaller image from multi-stage builds above, there's
  simply less installed in the final image for a scan to flag in the
  first place — a minimal image isn't just smaller, it has a smaller
  vulnerability surface to begin with.

## A Local Multi-Container Stack to Develop Against

- Most real services don't run alone — there's a database, a cache, and
  sometimes an adjacent service they call, and none of that shows up
  when the application itself starts on its own.
- A local multi-container stack (a Docker Compose file describing the
  app plus its database, cache, and any other dependency it talks to)
  gives a single `up` command that reproduces the shape of production
  closely enough to actually develop and debug against — instead of
  mocking those dependencies away or requiring a shared remote
  environment just to run the app locally.
- It's also where the earlier bullets get exercised before anything ever
  reaches a real environment — the same non-root user, health check, and
  environment-driven configuration that production expects can be
  verified locally first, against the same image that would actually
  ship.
