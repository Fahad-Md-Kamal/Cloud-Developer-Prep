---
title: "Jenkins: Production Deployment Pipelines"
---

# Jenkins: Production Deployment Pipelines

A real, working pipeline built on top of everything in
[Jenkins: Setup & Pipeline Configuration](jenkins-setup-and-pipeline-configuration.md):
cloning a private repository with a scoped credential, building a Docker
image, and hardening the deploy stage until it's an actual running
application — not just a green build. Every failure quoted below actually
happened, in that order, on a real agent, working against a real practice
project (`investor-pro`). Security hardening, backups, the declarative
Jenkinsfile, multibranch/webhooks, and multi-agent pipeline patterns
continue in
[Jenkins: Security, Hardening & Production Patterns](jenkins-security-hardening-and-production-patterns.md).

## Real Pipeline Walkthrough: Git, Credentials & Docker

Cloning a private repository with a scoped credential, checking out a
specific branch, and building a Docker image from the result.

### What the agent host needs installed first

Neither `git` nor `docker` ships on a base Amazon Linux 2023 AMI — both
have to be installed explicitly, in the same `user_data` script that
installs Java:

``` bash
#!/bin/bash
sudo yum update -y
sudo yum install -y java-21-amazon-corretto git docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
```

!!! danger "Package names still don't transfer across distros"

    - `docker.io` is the Debian/Ubuntu apt package name for Docker; Amazon Linux 2023's `yum`/`dnf` repos just call it `docker`.
    - Running `yum install docker.io` fails immediately with "No match for argument" — the same failure shape as the Java package-naming mismatch, just one distro-naming gotcha away from a different tool.

`usermod -aG docker ec2-user` adds the agent's user to the group that owns
`/var/run/docker.sock` (normally `root:docker`, mode `660`) — without it,
every `docker` command fails with `permission denied while trying to
connect to the Docker daemon socket`, even though the daemon itself is
running fine.

!!! danger "Group membership doesn't apply to an already-running process"

    - Linux fixes a process's supplementary groups at the moment it's created — editing `/etc/group` afterward doesn't retroactively update a process that's already running.
    - If the Jenkins agent's `java -jar remoting.jar` process started *before* `usermod -aG docker` ran, that specific process keeps failing with "permission denied" on the docker socket forever — even though a brand-new SSH login to the same box (and even `id ec2-user`) correctly shows `docker` in its group list.
    - The account is fixed; the already-running process isn't.
    - Confirmed by checking the process's own uptime (`ps -o etime= -p <pid>`) — 48 minutes old, well before the fix.

!!! success "The actual fix: kill the old process, don't just re-run the build"

    On the node's own page (**Manage Jenkins → Nodes → agent-one**), click **Disconnect** first — this is easy to miss, and re-running a build without it just reuses the same stale, already-connected process. Only after it shows offline does **Launch agent** actually start a brand-new `remoting.jar` process, one that reads `/etc/group` fresh and correctly picks up the new membership.

### Authenticating to a private GitHub repository

- Cloning a public repo needs no credential at all — a "No credentials
  specified" line in the build log is completely normal for those.
- A private repo fails that same anonymous clone outright, so a credential
  has to exist in Jenkins before the `git` step can succeed.

1. Generate a GitHub Personal Access Token, scoped narrowly
:   GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**. Repository access: only the one repo needed. Permissions: **Contents: Read-only** — a clone needs nothing more.

2. Store it in Jenkins' credentials store, never in the pipeline script
:   **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**. Kind: **Username with password**. Username: the GitHub username. Password: the token. ID: a memorable string (`github-pat` below) referenced from the pipeline.

3. Reference it from the `git` step by that ID
:   `credentialsId: 'github-pat'` — Jenkins resolves the actual token at checkout time and masks it out of console logs; the pipeline script itself never contains the secret value.

An SSH deploy key is the alternative: generate a keypair, add the *public*
half under the repo's **Settings → Deploy keys** (read-only), add the
*private* half to Jenkins as an **"SSH Username with private key"**
credential, and use a `git@github.com:...` URL instead of HTTPS. More
setup, but scoped to exactly one repo rather than an account-wide token —
worth it across several private repos.

### The `git` step: url, credentialsId, branch — and beyond

| Parameter | What it does |
|---|---|
| `url` | The remote to clone — HTTPS or SSH form, matching whichever credential type is in use. |
| `credentialsId` | The Jenkins credentials-store ID to authenticate with. Omitted entirely for a public repo, as the earlier "No credentials specified" log line showed. |
| `branch` | A plain branch name — slashes included, e.g. `holding/ui`, a perfectly normal git branch name — resolved against the remote. Also accepts a tag ref directly, e.g. `refs/tags/v1.2.3`, for building from a specific release point instead of a moving branch. |
| `changelog` / `poll` | Booleans controlling whether this checkout contributes to Jenkins' build-changelog UI and SCM-polling baseline — usually left at their defaults unless a job deliberately checks out more than one repository. |

After checkout, Jenkins exposes what it just cloned as environment
variables — `env.GIT_COMMIT` (the full SHA) and `env.GIT_BRANCH` — usable
straight in a later stage, e.g. tagging a Docker image by commit instead of
only by build number:

``` groovy
sh "docker build -t investor-pro:${env.GIT_COMMIT.take(7)} ."
```

The full commit message isn't exposed as an env var, but a plain
`git log` in a `sh` step captures it just as easily, once the repo is
checked out:

``` groovy
def msg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
```

### The pipeline, line by line

The actual working pipeline this section is built from:

``` groovy
pipeline{
    agent {label 'agent-one'}
    stages{
        stage("Code"){
            steps{
                echo "This is cloning the code"
                git credentialsId: 'github-pat', url: 'https://github.com/Fahad-Md-Kamal/investor-pro.git', branch:"holding/ui"
                echo "Code cloned successfully"
            }
        }
        stage("Build"){
            steps{
                echo "This is building the code"
                sh "docker build -t investor-pro:${env.BUILD_NUMBER} -t investor-pro:latest ."
            }
        }
        stage("Test"){
            steps{
                echo "This is testing the code"
            }
        }
        stage("Deploy"){
            steps{
                echo "This is deploying the code"
            }
        }
    }
}
```

`pipeline { ... }`
:   The declarative-syntax root block — everything inside it is Jenkins-managed structure, not arbitrary Groovy.

`agent {label 'agent-one'}`
:   Pins this entire pipeline to the one node advertising the label `agent-one` — every stage below runs on that same machine, in the same workspace.

`stages { ... }`
:   The container for every named phase of the build — purely organizational, holds one or more `stage` blocks.

`stage("Code") { ... }`
:   One named phase, shown as its own box in Jenkins' pipeline visualization. The name is just a label — `"Code"` could as easily be `"Checkout"`.

`steps { ... }`
:   The actual commands run inside a stage — every stage needs exactly one.

`echo "..."`
:   Prints a line to the build's console log — used here purely for readability while watching a run, no functional effect.

`git credentialsId: ..., url: ..., branch: ...`
:   The simplified checkout step (above) — clones `url` at `branch`, authenticating with the named credential.

`sh "..."`
:   Runs a shell command on the agent, in the current stage's workspace — here, the actual `docker build`.

`${env.BUILD_NUMBER}`
:   A Jenkins built-in environment variable — the current job's build number, incrementing every run. Used here as an image tag so every build produces a distinct, traceable image, alongside a floating `latest` tag for convenience.

### The Docker build itself

- `docker build ... .` uses `.` — the workspace root — as its build
  context, which works because the `git` step above clones directly into
  the workspace root rather than a subdirectory; the real `Dockerfile` at
  the repo's top level is found without needing a `-f` path.
- Two tags in one command (`-t investor-pro:${env.BUILD_NUMBER} -t
  investor-pro:latest`) apply both at once, from a single build — no need
  to build twice or run a separate `docker tag`.

!!! success "What actually running this looked like"

    Code stage: clone succeeds, credential accepted, correct branch checked out. Build stage: multi-stage `apt-get`/`uv sync` output streams through exactly as it would locally, image exported and tagged. Test and Deploy stages (still placeholder `echo`s here) run last. `Finished: SUCCESS` — the same pipeline shape the declarative Jenkinsfile in [Security, Hardening & Production Patterns](jenkins-security-hardening-and-production-patterns.md) builds on next, just with real steps instead of placeholders.

## Hardening the Deploy Stage: Frontend Builds, Dockerfile Gotchas & Cleanup

The pipeline above reaches `Finished: SUCCESS` — but a green build is not
the same as a working deployment. Everything below is a real gap between
the two, found by actually opening the deployed URL rather than trusting
the pipeline's own exit code.

### A stage can only have one `steps` block

``` groovy
stage("Code"){
    steps{ /* clone */ }
    steps{ /* copy .env */ }   // invalid -- a second steps block
}
```

!!! danger ""Expected one steps block, but got 2""

    A declarative `stage` allows exactly one `steps` block. This fails before a single step runs — Jenkins rejects the whole script at validation time, not partway through execution. The fix is just merging both step lists into the one block the stage is allowed to have.

### Building a frontend on the same agent that's already tight on resources

A `t3.micro` agent (1GB RAM, an 8GB disk already shared with Jenkins
itself and every Docker image built) is a genuinely hard place to run
`npm install` and `npm run build` — this hit real disk pressure, and
separately investigated (and rejected) `nvm` as the way to get Node onto
the box at all.

!!! danger "nvm installs Node for the wrong user, in a way Jenkins can't see anyway"

    - `user_data` runs as **root**, not `ec2-user` — so `curl ... | bash` followed by `nvm install 24` puts Node under `/root/.nvm`, invisible to the account Jenkins actually builds as.
    - Fixing that user mismatch still wouldn't be enough: nvm works by having an *interactive* shell's `~/.bashrc` source `nvm.sh` and rewrite `PATH`.
    - Jenkins' SSH-launched agent and every pipeline `sh` step run a **non-interactive, non-login** shell, which never sources `~/.bashrc`.
    - Same shape of bug as the `docker` group issue above: works fine when you SSH in by hand, silently doesn't apply in the actual automated context.
    - A distro package (NodeSource's `yum`/`dnf` repo) avoids both problems at once — the binaries land on the system `PATH` for every user and every shell type, no sourcing required.

!!! success "The fix that actually held: don't build the frontend on the agent at all"

    - Rather than fighting a tiny instance's resources for every build, the frontend gets built once (locally, or wherever's convenient).
    - The built `dist/` output — `index.html` plus a hashed `assets/` folder, Vite's default output — is committed directly into the repo under `src/webapp/frontend_dist/`.
    - Since the Dockerfile already does `COPY src ./src`, the built assets ride along automatically — zero Node.js on the agent, zero npm install, zero frontend build step in the pipeline at all.
    - The backend's own path resolution matches this exactly: `FRONTEND_DIST_ROOT = APP_ROOT / "frontend_dist"`, i.e. right next to `app.py` inside `src/webapp/` — the same directory the Docker image already contains.

### A container that "runs" but never actually starts the app

``` text
STATUS: Restarting (0) 3 seconds ago
COMMAND: "python3"
```

!!! danger "No CMD in the Dockerfile means the base image's default runs instead"

    - Exit code `0`, not a crash — the tell.
    - With no `CMD`/`ENTRYPOINT` in the Dockerfile, `docker run` falls back to `python:3.12-slim`'s own default command: a bare `python3` interpreter.
    - Detached (`-d`), its stdin is closed immediately, the REPL hits EOF and exits cleanly, and `--restart unless-stopped` loops that forever.
    - No application code ever runs, which is also why `docker logs` came back completely empty — there was nothing to log.
    - Fix: `CMD ["python3", "main.py"]`, pointed at the repo's actual ASGI entrypoint.

### Dockerfile CMD vs docker-compose's command

- Once a `docker-compose.yml` exists alongside the Dockerfile, its
  `command:` key fully **overrides** the Dockerfile's `CMD` — it doesn't
  merge with it.
- Precedence, highest to lowest: a command passed directly on the CLI,
  then a compose service's `command:`, then the Dockerfile's own `CMD` as
  the last-resort fallback for a bare `docker run` (only different if the
  Dockerfile uses `ENTRYPOINT` instead — then `CMD`/`command:` become
  arguments *appended to* the entrypoint rather than replacing it).

!!! danger ""It works under docker-compose but not under a bare docker run" is a real, common gap"

    - A compose file can quietly fix a problem a bare `docker run` still has.
    - Here, `docker-compose.yml` pointed `DATABASE_URL` at `postgres:5432` (the Postgres service's *name*, resolved over compose's own Docker network), while the app's own `.env` still says `@localhost:5432`.
    - Inside any container, `localhost` means that container itself, not a sibling container and not the host.
    - A Jenkins `Deploy` stage doing a bare `docker run`, for simplicity, never gets that compose-level override — the app starts, tries to reach a database on its own loopback, and fails.
    - A problem invisible until someone actually checks whether the deployed app works, not just whether the pipeline went green.

### The actual fix: let a Makefile target run docker-compose, not the Jenkinsfile itself

Rather than re-implementing `docker-compose.yml`'s networking logic inside
the pipeline, the `Deploy` stage was rewritten to call the project's own
`Makefile`:

``` groovy
sh "make start"
```

``` text
# Makefile
start:
	docker compose up -d --build
```

!!! success "This fixes the DATABASE_URL/localhost problem for good"

    `docker compose up` builds the app image *and* starts it alongside Postgres on compose's own network, with compose's own environment override taking effect (`DATABASE_URL: postgresql://...@postgres:5432/...`) — the exact override a bare `docker run` could never see. One Makefile target now matches whatever the project's maintainers already use locally, instead of a second, parallel deployment recipe hand-written inside the Jenkinsfile that can quietly drift from it.

!!! danger "echo "make start" runs nothing — it just prints the words"

    - A one-character-category mistake with a completely silent failure mode: writing `echo "make start"` instead of `sh "make start"` prints the literal text `make start` to the console log and does nothing else.
    - The build still reaches `Finished: SUCCESS`, because nothing in an `echo` step can fail — there's no command being run to fail.
    - The tell in the log is structural, not textual: a real shell step shows up as `[Pipeline] sh` followed by a line starting with `+` (the shell echoing what it's about to run); an `echo` step shows only `[Pipeline] echo` and the string itself, with no `+` line anywhere.
    - A green pipeline that changed nothing is a strong sign to check for exactly this.

!!! danger "Yet more tools a base AL2023 AMI doesn't have"

    - Running `make start` surfaced two more gaps in the same "assume nothing is preinstalled" pattern: `make` itself isn't on the base image (`make: command not found`, fixed with `yum install -y make`).
    - Even once Docker Compose's CLI plugin is installed, `docker compose build` separately requires the **Buildx** plugin — "`compose build requires buildx 0.17.0 or later`" — a *different* plugin binary, not bundled with Compose itself.
    - Neither AL2023's `yum` repos nor Docker's own package ship it directly; the fix is downloading the plugin binary from Buildx's GitHub releases into the same `/usr/libexec/docker/cli-plugins/` directory Compose's own plugin lives in.
    - Since Buildx's release asset name embeds its version number (`buildx-v0.37.1.linux-amd64`, not a stable filename), resolving the latest tag via GitHub's API first avoids hand-typing a version number into the script that will eventually go stale.

### Every build leaves behind a full image, forever, unless something removes it

``` groovy
sh """
    docker image prune -f
    docker images investor-pro --format '{{.Tag}}' \\
        | grep -vE '^(latest|${env.BUILD_NUMBER})\$' \\
        | xargs -r -I {} docker rmi investor-pro:{} || true
"""
```

!!! danger "Disk usage that grows by one full image every single build"

    - `docker build -t investor-pro:${env.BUILD_NUMBER} -t investor-pro:latest .` creates a brand-new ~1.3GB image on every run, and nothing removes the previous numbered tag automatically.
    - By build 18, if none of the earlier 17 images had ever been cleaned up, that alone is many times the agent's entire 8GB disk — exactly the kind of accumulation that trips a low-disk-space monitor (or the Free Temp Space false-positive covered in [setup & pipeline configuration](jenkins-setup-and-pipeline-configuration.md)) and takes the agent offline, with the actual cause being old, unused images rather than anything about the current build.
    - The snippet above runs right after the new container is already live, so there's no window where the image actually in use gets deleted out from under it — it keeps only `latest` and the build currently deployed, and reclaims everything else, every time.

### Deploying the wrong branch entirely

!!! danger "A Jenkinsfile pointed at a branch that never got the fix merged into it"

    - Every fix above — the Dockerfile `CMD`, the `frontend_dist` restructuring — happened on a feature branch.
    - Pointing the `git` step's `branch:` at `main` instead brought back the *exact same* "bare `python3`, exit 0" crash loop from earlier, because `main`'s own Dockerfile still had no `CMD` at all — the two branches had genuinely diverged (`git merge-base --is-ancestor` confirmed neither contained the other), each carrying real, non-overlapping work.
    - There's no Jenkins-side fix for this — it's a git problem wearing a deployment failure's clothes.
    - `git log --oneline branchA..branchB` shows what one branch has that the other doesn't; merging (not rebasing, once a branch may already be deployed from) brings both sets of changes together before pointing the pipeline back at whichever branch is meant to be the source of truth.

## Point-to-Point Deploy: investor-pro, Start to Finish

The sections above are the debugging story — every individual bug, in the
order it was actually found. This is the destination: the current,
complete pipeline for this project, clone to a fully running, fully-seeded
application, with nothing left commented out or half-working. Five stages,
each doing exactly one job.

``` groovy
pipeline{
    agent {label 'agent-one'}
    stages{
        stage("Code"){
            steps{
                git credentialsId: 'github-pat', url: 'https://github.com/Fahad-Md-Kamal/investor-pro.git', branch:"main"
                sh "mv .env.example .env"
            }
        }
        stage("Test"){
            steps{
                echo "This is testing the code"
            }
        }
        stage("Deploy"){
            steps{
                sh "make start"
            }
        }
        stage("Setup-Data"){
            steps{
                sh """
                    mkdir -p data/raw
                    unzip -o stock-data.zip -d ./data/raw/amarstock
                """
            }
        }
        stage("Ingest All Data"){
            steps{
                sh "docker compose exec -T app python -m src.ingest_data --source all"
            }
        }
    }
}
```

| Stage | What it does | Why it's built this way |
|---|---|---|
| Code | Clones the repo with a scoped credential, checks out `main`, and turns the committed `.env.example` into the real `.env` the app and compose both read from. | Every later stage assumes `.env` already exists — nothing else in the pipeline creates it. |
| Test | Still a placeholder. A real test suite would run here, before anything gets deployed — failing fast on broken code beats deploying it and finding out from Setup-Data or Ingest instead. | Ordered before Deploy deliberately, even while empty — the position is part of the design, not just the content. |
| Deploy | `make start` → `docker compose up -d --build`: builds the app image and starts it alongside Postgres, on compose's own network, with compose's environment override correctly pointing `DATABASE_URL` at the `postgres` service rather than `localhost`. | One Makefile target instead of hand-rolled `docker build`/`docker run` in the Jenkinsfile — the pipeline never re-implements deployment logic the project already maintains for local dev. |
| Setup-Data | Unzips the project's own bundled sample dataset (`stock-data.zip`, committed to the repo — no external download, no credentials needed) onto the agent's workspace. | `-o` forces silent overwrite (the non-interactive-shell lesson above) — a reused workspace's stale extracted files would otherwise stall the stage on an unanswerable prompt. |
| Ingest All Data | Runs the actual ingestion *inside* the running `app` container via `docker compose exec`, not on the bare agent host. | The container already has Python, `uv`, and every dependency from `uv sync` baked in at build time — the agent host deliberately has none of that, so ingestion has to run where the environment actually exists. |

!!! note "One quiet dependency between Setup-Data and Ingest All Data"

    `docker-compose.yml`'s `app` service mounts `./data:/app/data` — without that volume, the files **Setup-Data** unzips onto the host workspace would be invisible to the container **Ingest All Data** execs into, since every container has its own isolated filesystem regardless of which host directory the exec'ing shell happens to be in. The two stages only work together because of a line in a file neither one directly touches.

!!! success "What "point-to-point" actually means here"

    Starting from a bare EC2 instance with only the install script's tools on it (Java, git, Docker, Compose, Buildx, make) and an empty Jenkins workspace, this pipeline alone produces a running FastAPI app, a healthy Postgres database, and a fully populated dataset — no manual SSH step, no console click beyond pressing Build. Every stage above exists because a version without it was tried first and failed in exactly the way the earlier sections describe.
