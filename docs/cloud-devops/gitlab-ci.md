---
title: "GitLab CI/CD"
---

# GitLab CI/CD

[Jenkins](jenkins-setup-and-pipeline-configuration.md) is a separate
server you install and plug into whatever Git host you use. GitLab CI
is the opposite approach — CI/CD built directly into the platform
itself, configured as plain YAML in the repo rather than a Groovy DSL
on a separate server. Both solve the same problem; which one a job
wants usually just depends on which platform the team is already on.

## 1. Pipeline Structure: `.gitlab-ci.yml`

```yaml
stages:
  - build
  - test
  - deploy

build-job:
  stage: build
  script:
    - docker build -t myapp:$CI_COMMIT_SHORT_SHA .

test-job:
  stage: test
  script:
    - pytest

deploy-job:
  stage: deploy
  script:
    - ./deploy.sh
  only:
    - main
```

- A pipeline is made of **stages** (`build`, `test`, `deploy`), run in
  order — every job in one stage has to finish before the next stage
  starts.
- Each **job** belongs to exactly one stage, and runs its own
  `script:` — a plain list of shell commands, no separate scripting
  language to learn for the basics.
- `only`/`rules` restrict when a job runs at all — e.g. only deploying
  from `main`, not from every feature branch's pipeline.

## 2. Runners: Who Actually Executes a Job

- A **runner** is the actual machine (or container) that picks up a
  job and runs its `script:` — GitLab's server just schedules jobs, it
  never executes them itself.
- **Shared runners** — provided by GitLab (gitlab.com, or a self-hosted
  instance's own pool) — available to any project, no setup needed.
- **Project/group-specific runners** — registered by the team itself,
  for jobs needing specific hardware, network access to internal
  systems, or a fully controlled environment.
- **Executor type** decides *how* a runner actually runs a job's
  script: `shell` (directly on the runner's own host), `docker` (each
  job in a fresh, isolated container), or `kubernetes` (each job as a
  pod in a cluster). `docker` is the common default — a clean
  environment per job, with no state leaking between runs.
- `tags:` on a job pins it to runners advertising that tag, for when a
  job needs something a generic shared runner doesn't have.

## 3. Job Ordering: Stages vs. a Real DAG

```yaml
test-unit:
  stage: test
  script: [pytest tests/unit]

test-integration:
  stage: test
  needs: [build-job]   # starts as soon as build-job finishes,
  script: [pytest tests/integration]  # doesn't wait for the rest of its own stage
```

- By default, every job in a stage runs in parallel, and the **entire
  next stage waits for the entire previous stage** to finish — even if
  one specific job doesn't actually depend on most of what's running
  alongside it.
- `needs:` replaces that stage-by-stage waiting with a real dependency
  graph (a DAG) — a job starts the moment its *specific* listed
  dependencies are done, not when its whole stage is done. For a
  pipeline with several slow, unrelated jobs in the same stage, this
  can cut total pipeline time significantly.

## 4. Artifacts vs. Caching — Different Problems, Often Confused

| | Artifacts | Cache |
|---|---|---|
| Scope | One pipeline run — passed from an earlier job/stage to a later one | Across separate pipeline runs over time |
| Typical use | Build output a later job needs (a compiled binary, a built image's layers) | Downloaded dependencies (`node_modules`, a pip cache) to avoid re-downloading every run |
| Without it | A later job can't see what an earlier job produced at all | Every run re-downloads the same dependencies from scratch |

- **Artifacts** exist to move *this run's* output between jobs — a
  `build` job's compiled output has to be an artifact for the `test`
  job after it to actually use it, since each job runs in its own
  fresh environment.
- **Cache** exists purely for speed across *different* runs — it's not
  guaranteed to be there (a cache can be evicted), so nothing should
  depend on the cache existing for correctness, only for saving time.

## 5. Variables & Secrets

- **CI/CD variables** can be set at the project, group, or instance
  level — a group-level variable is inherited by every project under
  it, instead of being copy-pasted into each one.
- **Protected variables** are only exposed to jobs running on protected
  branches/tags (typically `main`, or a release tag) — a pipeline
  triggered from an arbitrary feature branch never sees production
  credentials at all.
- **Masked variables** have their value hidden from job logs — so a
  secret doesn't end up readable in plain text in a build log that
  other team members (or anyone with repo access) can see.

## 6. Environments & Review Apps

- `environment:` on a deploy job tracks that deployment in GitLab's own
  UI — a visible history of what was deployed where, and when, with a
  one-click rollback to a previous deployment straight from that
  history.
- A **review app** is a dynamic, temporary environment spun up
  automatically for a merge request — a real, running instance of the
  change, reachable by a URL, for reviewing the actual behavior before
  merging, not just reading a diff.

## 7. GitLab CI vs. Jenkins

| | GitLab CI | Jenkins |
|---|---|---|
| Config | Plain YAML, built into the platform | Groovy DSL (Jenkinsfile), a separate server to run |
| Setup | Nothing to install if already on GitLab | Install, configure, and maintain the Jenkins server itself |
| Flexibility | Simpler for the common case; less scriptable for unusual logic | Full programming language (Groovy) for genuinely complex pipeline logic |
| Extensibility | Smaller plugin ecosystem, tightly coupled to GitLab itself | Huge plugin ecosystem, works with any Git host |
| Review/MR integration | Native — pipelines, review apps, and MRs are one connected UI | Needs separate plugins/webhooks to integrate with a Git host's MR/PR flow |

!!! success "The exam/interview-style signal"

    "Already on GitLab, want CI/CD with the least new infrastructure to
    run" → GitLab CI. "Need to support multiple Git hosts, or pipeline
    logic complex enough to need real conditionals/loops/shared
    libraries across many pipelines" → Jenkins' Groovy DSL earns its
    extra operational cost there.

---

## Code Samples

No dedicated code samples yet for this page — the `.gitlab-ci.yml`
snippets above are complete enough to adapt directly.
