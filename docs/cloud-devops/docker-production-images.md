---
title: "Docker: Production Container Images"
---

# Docker: Production Container Images

Building a container image that's actually fit to run in production, not
just one that works on a laptop. Knowing the `docker build`/`docker run`
commands gets you the laptop version — the fundamentals below are what
let you reason about a container when something goes wrong in
production, which the commands alone never will. The rest of the page
is a short, concrete checklist built on top of that understanding.

## What a Container Actually Is

From the OS's perspective, a container is just another process on the
host — it shares the host's kernel. "Containment" comes entirely from
three Linux kernel features, not from running a separate operating
system the way a VM does.

### Namespaces: What the Process Is Allowed to See

A namespace wraps a global kernel resource so a process inside it sees
its own isolated view, while the host (and every other container) keeps
seeing the real, unrestricted one.

`PID namespace`
:   The process that starts a container sees itself as PID 1 inside
    that namespace — even though the host sees it as some ordinary PID
    like 4821. Same process, two different views, which is exactly why
    `docker top` on the host and `ps aux` run inside the container print
    different numbers for the same running process.

`Network namespace`
:   Its own network interfaces, IP address, and routing table — this is
    why a container can bind to port 80 without conflicting with the
    host's own port 80, and why Docker has to explicitly *publish* a
    port to bridge the container's private network namespace back to
    the host's.

`Mount namespace`
:   Its own view of the filesystem mount table — the root filesystem a
    container sees (built from the image's layers, below) is real to
    it, while the host's actual root filesystem is unaffected.

`UTS / IPC / User namespaces`
:   Isolated hostname, inter-process communication, and (optionally)
    user/group ID mapping — rounding out the illusion of a separate
    machine without actually being one.

!!! danger "A container escape is a namespace escape"

    If a process breaks out of its PID/mount/network namespaces, it
    lands directly on the host, with whatever privileges its user ID
    has there — this is *why*
    [running as non-root inside the container](#non-root-users) matters
    so much: the namespace boundary is the only thing standing between
    "contained" and "just a normal host process," and it's a boundary
    in the kernel's bookkeeping, not a hardware-enforced wall the way a
    VM's hypervisor boundary is.

### cgroups: How Much the Process Is Allowed to Use

Namespaces control *what a process can see*; **cgroups** (control
groups) control *how much of the host's actual resources it can use* —
CPU time, memory, disk I/O, network bandwidth. `docker run --memory=512m`
isn't a Docker-specific feature being enforced by the Docker daemon
watching the process — it's Docker writing that limit into a cgroup, and
the kernel itself enforcing it (including killing the process with an
OOM kill if it exceeds the memory limit), the exact same mechanism a
systemd service or a Kubernetes pod's resource limits are built on.

### Union Filesystem: Why Layers Actually Cache, and Why a Deleted Secret Isn't Really Gone

This is the mechanism behind two facts already asserted elsewhere on
this page —
["a build only re-runs from the first changed layer"](#a-small-cacheable-dockerfile)
and
["a secret deleted in a later layer is still sitting in the image history"](#configuration-through-the-environment-not-baked-into-the-image)
— rather than just taking both on faith.

An image's layers stack through a **union (overlay) filesystem**: every
layer below the top one is **read-only**, and the container's own
**writable layer** sits on top. Reading a file checks the stack
top-down and returns the first copy found. Writing to a file that
already exists in a read-only layer below triggers **copy-on-write**:
the kernel copies that file *up* into the writable layer first, and the
write happens to that copy — the original, lower-layer version is never
touched.

<svg viewBox="0 0 760 500" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of copy-on-write across a container's union filesystem layers" style="width:100%;height:auto;max-width:760px;display:block;margin:0 auto;font-family:inherit;">
<defs><marker id="cow-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5b6472"></path></marker></defs>
<rect x="60" y="60" width="640" height="110" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"></rect>
<text x="80" y="92" font-size="21" font-weight="600" fill="#0f6b45">Layer 3 — Container's Writable Layer</text>
<rect x="60" y="200" width="640" height="110" rx="8" fill="#eef1f5" stroke="#8a98ab" stroke-width="2"></rect>
<text x="80" y="232" font-size="21" font-weight="600" fill="#434d5c">Layer 2 — App Dependencies (read-only)</text>
<rect x="60" y="340" width="640" height="110" rx="8" fill="#eef1f5" stroke="#8a98ab" stroke-width="2"></rect>
<text x="80" y="372" font-size="21" font-weight="600" fill="#434d5c">Layer 1 — Base OS (read-only)</text>
<line x1="35" y1="70" x2="35" y2="440" stroke="#5b6472" stroke-width="2" stroke-dasharray="6,6" marker-end="url(#cow-arrow)"></line>
<text x="35" y="462" font-size="16" fill="#5b6472" text-anchor="middle">lookup order</text>
<rect x="380" y="385" width="130" height="50" rx="6" fill="#ffffff" stroke="#434d5c" stroke-width="2"></rect>
<text x="445" y="416" font-size="18" fill="#2b313b" text-anchor="middle">config.yml</text>
<g transform="translate(380,385)"><animateTransform attributeName="transform" attributeType="XML" type="translate" values="380,385;380,385;380,105;380,105" keyTimes="0;0.34;0.6;1" dur="9s" repeatCount="indefinite"></animateTransform><rect width="130" height="50" rx="6" fill="#ffffff" stroke="#434d5c" stroke-width="2"><animate attributeName="fill" values="#ffffff;#ffffff;#d7f5e9;#d7f5e9" keyTimes="0;0.34;0.6;1" dur="9s" repeatCount="indefinite"></animate><animate attributeName="stroke" values="#434d5c;#434d5c;#1f9d6b;#1f9d6b" keyTimes="0;0.34;0.6;1" dur="9s" repeatCount="indefinite"></animate></rect><text x="65" y="31" font-size="18" text-anchor="middle" fill="#2b313b">config.yml</text><animate attributeName="opacity" values="0;0;1;1;1;0" keyTimes="0;0.33;0.35;0.95;0.99;1" dur="9s" repeatCount="indefinite"></animate></g>
<text x="380" y="480" font-size="20" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.32;0.34;1" dur="9s" repeatCount="indefinite"></animate>1. Read config.yml → found in Layer 1. Nothing moves for a read.</text>
<text x="380" y="480" font-size="20" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.33;0.35;0.65;0.67;1" dur="9s" repeatCount="indefinite"></animate>2. Write requested → file copied UP into Layer 3 first.</text>
<text x="380" y="480" font-size="20" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.68;1" dur="9s" repeatCount="indefinite"></animate>3. Write lands only in Layer 3 — Layer 1's original is untouched.</text>
</svg>

!!! danger "This is why a deleted secret still ships in the image"

    Layers are additive, never a diff. If a secret is written in Layer 1
    and a later layer runs `rm` on it, the file in Layer 1 still exists —
    the delete just adds a "whiteout" marker in the layer above it that
    hides the file from view. Anyone who pulls the image and inspects
    Layer 1 directly (`docker save`, then extract the tarball) can still
    read it. The fix is the same one already covered — never write a
    secret into a layer in the first place.

### Why This Beats a VM for Density, and Loses to One for Isolation

- A VM boots an entire kernel and OS inside a hypervisor-managed virtual
  machine; a container just starts a process with a restricted view
  (namespaces) and a resource cap (cgroups) on a kernel that was already
  running — which is the entire reason containers start in milliseconds
  and a VM takes tens of seconds.
- The trade-off runs the other way on security: a VM's hypervisor
  boundary is hardware-enforced and far harder to escape than a
  namespace boundary, which is kernel bookkeeping. This is why
  ECS/EKS worker nodes are themselves EC2 VMs running containers on top
  — combining both layers rather than picking one.
- Containers existed as a concept before Docker (`chroot`, Solaris
  Zones, LXC) — Docker's actual contribution was packaging (the image
  format and Dockerfile) and a developer-friendly interface on top of
  kernel primitives that already existed. Docker didn't invent
  containment, and knowing that is most of the way to understanding
  what a `FROM`/`RUN`/`COPY` instruction is actually doing underneath.

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

## Data Persistence: Volumes vs. Container Lifecycle

- A container's writable layer is ephemeral — stop and remove the
  container (or shut down the host it's running on) and anything
  written inside it that isn't in a volume is gone. This is the direct
  answer to "how do you prevent data loss when your database container
  shuts down."
- A named volume (or a bind mount to the host filesystem) persists
  independently of the container's lifecycle:
  `docker volume create pgdata` then mounting
  `-v pgdata:/var/lib/postgresql/data` means the container itself can
  be destroyed and recreated while the actual data survives untouched.
- Treat the container as disposable — it's the volume that actually
  needs backing up, not the container.
- At real production scale, a volume on a single host is itself a
  single point of failure. The actual fix isn't "trust Docker volumes
  harder" — it's a managed, durable data store (RDS, a replicated
  EBS-backed volume) or simply not running the production database
  inside a container on a single machine at all.
