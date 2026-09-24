---
title: "Terraform: Operating in Production"
---

# Terraform: Operating in Production

Keeping state healthy once real changes start landing — drift, targeted
applies, moving resources without destroying them, recovering from a
half-applied run, machine-readable plans for automation, importing
existing resources, and debug logging. Builds on
[State, Environments & Regions](terraform-state-environments-and-regions.md);
see [Terraform Fundamentals](terraform-fundamentals.md) and
[Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md) for the
concepts referenced throughout.

## Drift Detection

Drift is state disagreeing with reality — someone widened a security
group rule in the console during an incident, or an ASG's
`desired_capacity` moved because a scaling policy fired.

``` bash
# Refresh Terraform's view of reality and show any drift, without touching anything
terraform plan -refresh-only

# Older/equivalent: refresh state, then a normal plan will show the same drift
terraform apply -refresh-only
```

``` text
  # aws_security_group.app has changed
  ~ resource "aws_security_group" "app" {
      ~ ingress = [
          + {
              + cidr_blocks = ["0.0.0.0/0"]
              + from_port   = 22
              + to_port     = 22
              + protocol    = "tcp"
            },
        ]
    }

This is a refresh-only plan, so Terraform will not take any actions.
```

!!! success "Schedule it, don't wait to trip over it"

    A weekly `plan -refresh-only` run in CI, posting its output
    somewhere visible, catches console-made changes within a week
    instead of at the next unrelated `apply`, when the drifted resource
    shows up mixed in with changes nobody intended to make.

!!! danger "Detecting drift isn't fixing it"

    `-refresh-only` only updates what Terraform believes state to be —
    it does not push your config back onto AWS, and it does not pull
    the drifted value into your `.tf` files either. Deciding whether
    the *console change* or the *code* is correct is still a human call
    every time.

## Targeted Apply, and When It's a Mistake

``` bash
# Apply changes to just this one resource, ignoring other pending diffs
terraform apply -target=aws_launch_template.app
```

!!! success "Legitimate use: an emergency, isolated fix"

    Production is down because of one resource, the fix is known, and a
    full `plan` right now would also apply three unrelated in-flight
    changes nobody's reviewed yet. `-target` applies only the fix.

!!! danger "The mistake: using it as a habit"

    - Repeated `-target` applies let a config and its state quietly
      drift apart from each other in a different way than drift
      detection above — not AWS vs. state, but "the parts of config
      that get applied" vs. "the parts that don't."
    - The next full, untargeted `apply` can produce a surprisingly large
      plan, because everything skipped over every targeted run finally
      shows up at once.
    - Terraform itself warns about this every time `-target` is used —
      treat that warning as accurate, not boilerplate.

## `moved` Blocks

Renaming a resource in code, or moving it into a module, changes its
address (`aws_instance.app` → `module.compute.aws_instance.app`).
Terraform matches state by address, not by intent — without help, it
reads that as "the old one was deleted, a new one must be created," and
plans a destroy-and-recreate of something that never actually changed
on AWS.

``` hcl
# after moving aws_instance.app into a module, add this alongside it
moved {
  from = aws_instance.app
  to   = module.compute.aws_instance.app
}
```

``` text
$ terraform plan
Note: Objects have changed outside of Terraform

  # aws_instance.app has moved to module.compute.aws_instance.app
    resource "aws_instance" "app" {
        id = "i-0aaa1111aaaa11111"
    }

No changes. Your infrastructure matches the configuration.
```

!!! success "This is exactly what a repo-layout refactor needs"

    Extracting an inline resource into a module — the "third time"
    moment from the rule of three (see [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md)) — is precisely when a
    `moved` block matters: it lets the refactor be a no-op against real
    infrastructure, instead of an accidental destroy-and-recreate of
    something already running in production.

!!! danger "This happened for real, on this exact mistake"

    - Switching an `aws_iam_user` resource from `count` to `for_each` —
      without a `moved` block — produced a plan reading `Plan: 4 to
      add, 0 to change, 3 to destroy`.
    - Typing `yes` anyway destroyed three real IAM users, then failed
      to recreate two of them (a race between the parallel destroy and
      create for the same username).
    - The fix was mechanical, not scary: since the destroyed users
      genuinely no longer existed, a follow-up `apply` recreated them
      cleanly with no conflict.
    - The lesson is the plan line itself — `count` → `for_each` always
      shows as unrelated destroy+create unless a `moved` block (or
      `state mv`, below) tells Terraform the two addresses are the same
      object — and "3 to destroy" in a plan is worth stopping on every
      single time, not just reading past.

## `state mv` and `state rm`

`moved` blocks are the modern, declarative way to record a rename —
they live in code and survive a fresh checkout. `terraform state mv`
does the same rewrite imperatively, once, from the CLI — useful when
you need it done immediately and won't remember (or won't bother) to
leave a `moved` block behind.

``` bash
# Same effect as the moved block above, done directly against the state file
terraform state mv aws_instance.app module.compute.aws_instance.app

# Remove a resource from Terraform's management without destroying it in AWS --
# for handing a resource off to another team's config, or before a manual takeover
terraform state rm aws_instance.legacy_bastion

# List what's actually in state right now
terraform state list
```

!!! danger "`state rm` doesn't delete anything in AWS"

    It only removes the resource from Terraform's bookkeeping — the
    real EC2 instance keeps running, untouched. The easy mistake is
    expecting `state rm` to be a lightweight `destroy`; it's the
    opposite, a way to stop managing something while leaving it exactly
    as it is.

## Recovering a Half-Applied State

An `apply` can be interrupted mid-run — a killed terminal, a lost
network connection, a lock timeout — after some resources succeeded and
before others did. State reflects whatever finished before the
interruption; nothing about it is inherently corrupt, but it needs
deliberate steps to get back to normal, not blind re-running.

``` bash
# 1. If a lock was left behind by the interrupted run, confirm nothing else is actually applying, then:
terraform force-unlock <LOCK_ID>

# 2. Reconcile state with what's actually on AWS before touching anything else
terraform plan -refresh-only

# 3. A normal plan now shows only the resources still pending from the interrupted apply --
#    read it like any other plan before applying
terraform plan
terraform apply
```

!!! danger "force-unlock is a last resort, not a first reaction"

    Run it while the original process might still be applying, and two
    applies now race against the same state with no lock protecting
    either — the exact failure mode locking (see [State, Environments &
    Regions](terraform-state-environments-and-regions.md)) exists to
    prevent. Confirm the original process is actually dead (check who
    holds the lock, ask the team) before force-unlocking.

!!! success "Half-applied is recoverable precisely because state is incremental"

    Each resource is recorded as it succeeds, not all-or-nothing at the
    end — that's why `plan` after an interruption shows only what's
    left to do, rather than an all-or-nothing do-over of the entire
    config.

## Machine-Readable Plans for Automation

The human-readable plan output covered in
[Fundamentals](terraform-fundamentals.md) is for a person reading a
terminal. A CI pipeline needs to act on a plan programmatically — post
it as a PR comment, gate an approval on whether anything destructive is
in it — which means parsing it as structured data instead of text.

``` bash
# Save the plan to a binary file, then export it as JSON
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json

# Pull out just the destructive actions -- exactly the check an
# approval gate should run before anyone clicks "approve"
jq '.resource_changes[] | select(.change.actions | index("delete"))' tfplan.json
```

!!! note "Why -out matters here"

    `terraform show -json` without a saved plan file re-runs `plan`
    against current state — which can differ from the plan a human or a
    pipeline already reviewed, if anything changed in between. Saving
    with `-out` and applying that exact file (`terraform apply
    tfplan.binary`) guarantees the plan that was reviewed is the plan
    that gets applied, with nothing able to slip in between the two.

!!! success "This is the actual mechanism behind a PR approval gate"

    "terraform plan posted as a comment" and an approval gate in CI are
    both built on exactly this JSON output — a script reads
    `tfplan.json`, formats a summary, and posts it; the approval step
    re-checks it for anything destructive before allowing `apply` to
    run the saved `tfplan.binary`.

## Importing Existing Resources

Something created by hand in the console — or by anyone else, outside
Terraform entirely — has no entry in state. Terraform doesn't know it
exists, so `plan`/`apply` assumes it needs to be created, and AWS
rejects the create because the real thing is already there:

``` text
│ Error: creating IAM User (nsl-media-vault-app-s3-access): operation error IAM: CreateUser,
│ https response error StatusCode: 409, EntityAlreadyExists: User with name
│ nsl-media-vault-app-s3-access already exists.
```

`terraform import` fixes this — and only this. It does not create,
modify, or delete anything in AWS; it just writes an entry into the
state file saying "this resource address already corresponds to this
real object."

``` bash
# Syntax: terraform import <resource address> <the resource's real ID>
terraform import 'aws_iam_user.example["nsl-media-vault-app-s3-access"]' nsl-media-vault-app-s3-access
```

!!! note "The ID on the right isn't universal"

    What counts as "the ID" is resource-type-specific — for
    `aws_iam_user` it's the username, for `aws_instance` it's the
    instance ID (`i-0aaa1111aaaa11111`), for `aws_s3_bucket` it's the
    bucket name. Always check the specific resource's page on the
    [Terraform
    Registry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
    — it documents the exact import ID format, usually right at the
    bottom of the page.

After importing, run `plan` — it should show **0 to change** if your
config's arguments already match the real object's actual settings. If
they don't match, `plan` shows exactly what it would change to bring
the real object in line with your code — read that like any other plan
before applying.

!!! danger "Importing into a count index is fragile"

    Importing into `aws_iam_user.example[3]` ties the import to a
    *position* in a list (the same `count` gotcha covered in [Modules &
    Advanced HCL](terraform-modules-and-advanced-hcl.md), again). If
    that list ever reorders, index `3` can silently point at a
    different resource next `apply`. Importing into a `for_each`-keyed
    address instead — `aws_iam_user.example["nsl-media-vault-app-s3-access"]`,
    as above — ties the import to a stable name that can't shift
    underneath it.

### Worked example: importing a resource that must never be destroyed

Bringing a genuinely important resource under Terraform's control — a
long-running production instance, not a throwaway learning one —
deserves an extra step before anything else touches it.

``` hcl
resource "aws_instance" "critical_app" {
  ami           = "ami-0333333333333333"
  instance_type = "t3.micro"

  tags = {
    Name = "critical-app"
  }

  lifecycle {
    prevent_destroy = true   # add this in the same edit as the import, not after
  }
}
```

``` bash
terraform import aws_instance.critical_app i-0aaa1111aaaa11111
terraform plan   # confirm 0 to change, or read exactly what doesn't match yet
```

With `prevent_destroy` already in place, a routine, safe change —
updating tags, say — applies normally:

``` text
  # aws_instance.critical_app will be updated in-place
  ~ resource "aws_instance" "critical_app" {
        id   = "i-0aaa1111aaaa11111"
      ~ tags = {
            "Name"  = "critical-app"
          + "Owner" = "fahad"
        }
    }

Plan: 0 to add, 1 to change, 0 to destroy.
```

!!! success "prevent_destroy is the actual safety net here"

    Before this instance was imported, nothing about it could be
    "destroyed by Terraform" — Terraform didn't know it existed. The
    moment it's imported, that protection disappears unless something
    replaces it — which is exactly `prevent_destroy`'s job. Add it in
    the *same* edit as the import itself, not as a follow-up step: any
    change that would force replacement (the `-/+` case from
    [Fundamentals](terraform-fundamentals.md)) now fails outright with
    an error instead of silently destroying and recreating a resource
    that was never meant to be disposable.

## Debug Logging: TF_LOG and TF_LOG_PATH

When a plan or apply fails with an error too vague to act on,
Terraform's own internal logging — normally silent — can be turned on
to see exactly what it's doing: every provider RPC call, every HTTP
request to AWS, every internal decision.

``` bash
export TF_LOG=DEBUG          # TRACE, DEBUG, INFO, WARN, or ERROR -- TRACE is the noisiest
terraform plan

# unset when done -- it stays exported for every future command in this shell otherwise
unset TF_LOG
```

!!! note "TRACE vs DEBUG"

    `TRACE` is the most verbose level — it includes the exact HTTP
    requests and responses between the provider and AWS's API, useful
    for tracking down a provider bug or an unexpected API response.
    `DEBUG` is one level down: Terraform's own internal decisions and
    provider RPC calls, usually enough for "why did it plan to do that"
    without the sheer volume of raw HTTP traffic.

Left on, `TF_LOG` prints directly to the terminal, mixed in with normal
plan/apply output — usable for a quick look, unmanageable for anything
longer. `TF_LOG_PATH` redirects it to a file instead:

``` bash
export TF_LOG=DEBUG
export TF_LOG_PATH="/home/fahad/logs/debug.log"
terraform apply
```

!!! danger "The directory has to already exist"

    Terraform does not create missing directories in `TF_LOG_PATH` —
    pointing it at `/home/fahad/logs/debug.log` when
    `/home/fahad/logs/` doesn't exist yet fails to write the log at all
    (checked directly: a fresh `logs/` directory genuinely doesn't
    exist until something creates it). `mkdir -p` the directory first,
    the same requirement as any other tool writing to a path you
    haven't set up yet.

!!! note "The log file is appended to, not overwritten"

    Every subsequent command with the same `TF_LOG_PATH` set keeps
    adding to the same file rather than starting fresh — a log from an
    hour ago and one from just now sit in the same file, back to back.
    Delete or rotate it manually between debugging sessions, or it
    grows indefinitely and makes finding the relevant run harder each
    time.

!!! success "Unset both when done"

    Both variables persist for every Terraform command run in that
    shell session afterward, not just the one that needed debugging —
    exactly the same "stray environment variable" class of surprise as
    the credential-precedence gotcha in
    [Fundamentals](terraform-fundamentals.md). A stray `TF_LOG=TRACE`
    left set makes every future `plan` print pages of noise nobody
    asked for; `unset TF_LOG TF_LOG_PATH` (or just open a fresh
    terminal) once the debugging is done avoids that.

## Beyond the Checkpoint: Terraform Associate Certification

An external, formal validation of everything covered across this
series — HashiCorp's own [Terraform Associate
(004)](https://developer.hashicorp.com/terraform/tutorials/certification-004/associate-review-004)
exam, current as of late 2026 (the prior 003 version retired January
2026).

|  |  |
|---|---|
| Format | 1 hour, online proctored, ~57 questions (multiple choice / multiple answer / true-false) |
| Cost | ~$70.50 USD + local taxes |
| Validity | 2 years |
| Prerequisites | None |
| Tests against | Terraform 1.12 |

### The 8 official objectives

1. **Infrastructure as Code with Terraform** — what IaC is, its
   advantages, multi-cloud/hybrid/service-agnostic workflows
2. **Terraform Fundamentals** — installing/versioning providers,
   multi-provider configs, how state is used (see
   [Fundamentals](terraform-fundamentals.md) and
   [State, Environments & Regions](terraform-state-environments-and-regions.md))
3. **Core Terraform Workflow** — `init`, `validate`, `plan`, `apply`,
   `destroy`, `fmt` (see [Fundamentals](terraform-fundamentals.md))
4. **Terraform Configuration** — `resource` vs `data`, cross-resource
   references, variables/outputs, complex types,
   expressions/functions, resource dependencies, custom validation
   conditions, sensitive data handling including Vault (see
   [Fundamentals](terraform-fundamentals.md) and
   [Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md))
5. **Terraform Modules** — sourcing, variable scope, using, versioning
   (see [Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md)
   and [EKS, Worked Examples & Lambda](terraform-eks-and-lambda.md))
6. **Terraform State Management** — local backend, state locking,
   remote state via `backend`, drift (see
   [State, Environments & Regions](terraform-state-environments-and-regions.md)
   and drift detection above)
7. **Maintain Infrastructure with Terraform** — `import`, inspecting
   state via the CLI, verbose logging (all above, in this file)
8. **HCP Terraform** — creating infrastructure via HCP Terraform,
   collaboration/governance features, workspaces/projects, integrations

!!! success "Objectives 1–7: already in strong shape"

    Every objective above except the last has a real, hands-on match
    somewhere in this series — not just reading about the concept, but
    having hit its actual failure modes against a real account (drift,
    a corrupted lock, a botched import, a missing `depends_on`). That's
    a meaningfully stronger position than most exam preparation, which
    is usually reading-only.

!!! danger "Objective 8 (HCP Terraform) is the one clean gap"

    Nothing in this material has touched HCP Terraform specifically —
    its workspaces/projects, collaboration and governance features, or
    run-integration model. That's roughly one-eighth of the exam,
    covering a genuinely different product surface (a hosted service,
    not the CLI/provider mechanics everything else here is built on) —
    worth deliberate, separate study before sitting the exam, rather
    than assuming it's covered by the remote-backend/state concepts
    already learned.

!!! note "Checkpoint"

    Given a diagram, produce working, readable, reproducible code
    inside the session, and perform state operations without notes —
    then hand over the repository.
