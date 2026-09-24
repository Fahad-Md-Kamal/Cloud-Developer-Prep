---
title: "Terraform: State, Environments & Regions"
---

# Terraform: State, Environments & Regions

What state actually holds, and how one codebase serves multiple
environments and regions safely. Builds on
[Terraform Fundamentals](terraform-fundamentals.md) and
[Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md); see
[Building a Platform](terraform-building-a-platform.md) for the real
infrastructure this then provisions, and
[Operating Terraform in Production](terraform-operating-in-production.md)
for the day-2 operations that build on state directly (drift, `state
mv`/`rm`, imports).

## What State Holds

- Terraform can't ask AWS "what does my config manage?" — AWS just has
  resources, with no concept of which ones "belong" to a given `.tf`
  file.
- The state file is Terraform's own record of that mapping: for every
  resource block, it stores the real resource ID and every attribute
  AWS returned when it was created.

``` json
{
  "resources": [
    {
      "type": "aws_instance",
      "name": "app",
      "instances": [
        {
          "attributes": {
            "id": "i-0aaa1111aaaa11111",
            "ami": "ami-0111111111111111",
            "instance_type": "t3.micro",
            "public_ip": "203.0.113.10"
          }
        }
      ]
    }
  ]
}
```

- Every `plan` is really a three-way comparison: your `.tf` files
  (desired), the state file (what Terraform believes it last created),
  and a fresh read of the real AWS API (what actually exists).
- A mismatch between the last two is **drift** — someone changed the
  security group by hand in the console, and state doesn't know yet.

!!! danger "Never hand-edit the state file"

    It's JSON, so it's tempting to fix a stuck reference by hand. Don't
    — a malformed edit corrupts every future plan silently. Use
    `terraform state` subcommands (see [Operating Terraform in
    Production](terraform-operating-in-production.md)) for anything
    that looks like a state surgery.

!!! danger "State contains secrets in plaintext"

    An RDS password passed as a resource argument ends up readable in
    plaintext inside the state file, even if the variable itself is
    marked `sensitive` (that only hides it from CLI output, not from
    the file). This is the whole reason state must live in a backend
    with access control, never committed to git.

## Remote Backend with Locking

By default, state lives in a local `terraform.tfstate` file next to
your config — fine solo, broken the moment a second engineer runs
`apply` from their own laptop against their own copy of that file. A
**remote backend** moves state to shared storage; **locking** stops two
applies from racing against it at the same time.

``` hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "fahad-terraform-state"
    key            = "dev/network/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-locks"   # locking, pre-2023 syntax
    encrypt        = true
  }
}
```

!!! danger "The backend block doesn't inherit the provider's profile"

    A real `terraform init -migrate-state` failed with `403 Forbidden`
    on the S3 bucket, even though the exact same bucket worked fine for
    every other command. Cause: the `backend "s3" { }` block above has
    no `profile` argument, so it never inherits `profile = "fahad"`
    from the `provider "aws" { }` block below it — backend
    initialization happens before providers are even loaded, so nothing
    carries over automatically. With no explicit profile, it silently
    fell back to this machine's *default* AWS credential chain, which
    resolved to a completely different AWS account that had no access
    to the bucket at all. The fix is adding `profile = "fahad"` directly
    inside the `backend` block — it needs its own credentials, stated
    explicitly, every time.

|  | Local state | S3 remote state |
|---|---|---|
| Collaboration | Breaks the moment a second person runs `apply` from their own copy | One shared source of truth for the whole team |
| Locking | None — two concurrent applies can corrupt it | DynamoDB or S3-native locking (below) prevents the race |
| Durability | One laptop's disk — no backup, one `rm` away from gone | S3's own durability, plus optional bucket versioning for point-in-time recovery |
| Setup complexity | Zero — works with no configuration | Needs a bucket, IAM permissions, and its own credential config (see the note above) |
| Credential scope | Same identity as everything else automatically | Resolved independently of the provider block — easy to misconfigure, as above |
| Cost | Free | Small S3 storage/request cost, plus DynamoDB cost only if not using native locking |

!!! note "S3 native locking (Terraform ≥ 1.10 / AWS provider ≥ 5.x)"

    Newer Terraform versions can lock directly on the S3 object using
    conditional writes — no separate DynamoDB table required. Either
    approach solves the same problem: without locking, two `apply` runs
    starting seconds apart both read the same "before" state and can
    each write back an "after" that discards the other's changes.

!!! danger "`-reconfigure` and `-migrate-state` answer different questions — picking the wrong one loses track of real infrastructure"

    - Adding a `backend "s3" { ... }` block to a config that already had
      real, applied resources (a live VPC, NAT Gateway, subnets)
      produced exactly the error the table above predicts: `Backend
      configuration changed`, with `init` refusing to proceed until
      told which of two flags to use.
    - The two are not interchangeable: **`-reconfigure`** tells
      Terraform to just start using the new backend as-is, treating it
      as empty — correct only when there's no existing state worth
      keeping, e.g. local testing that never got applied for real.
    - **`-migrate-state`** actually copies the current state into the
      new backend first, so everything Terraform already knows about
      keeps being tracked.
    - Running `-reconfigure` against a backend switch with real applied
      resources would have made Terraform believe nothing existed yet
      in S3, while the VPC/NAT/subnets kept right on existing (and
      billing) in AWS, untracked — the next `apply` could easily have
      tried to create a second copy of everything instead of
      recognizing what was already there.
    - `-migrate-state` was the correct flag here, confirmed by a
      `terraform plan` immediately after showing `No changes. Your
      infrastructure matches the configuration.` against the new
      backend.

### Migrating dynamodb_table to use_lockfile

A real `apply` on Terraform 1.16 produced a live deprecation warning:

``` text
│ Warning: Deprecated Parameter
│
│ The parameter "dynamodb_table" is deprecated.
│ Use parameter "use_lockfile" instead.
```

The fix is a one-line swap in the backend block:

``` hcl
backend "s3" {
  bucket       = "fmk-terraform-backup"
  key          = "tf-state/locking/terraform.tfstate"
  region       = "ap-south-1"
  use_lockfile = true          # was: dynamodb_table = "dynamodb-state-locking"
  profile      = "fahad"
}
```

``` bash
terraform init -reconfigure   # not -migrate-state -- the bucket/key didn't move,
                              # only the locking mechanism did
```

!!! note "-reconfigure vs -migrate-state"

    Changing any backend argument makes Terraform refuse to proceed
    until you tell it what to do with existing state — but which flag
    depends on *what* changed. `-migrate-state` is for when the state's
    actual location changed (a different bucket or key) and the old
    state needs copying into the new location. `-reconfigure` is for
    when the location is identical and only settings like this one
    changed — it just re-applies the new config against the state
    that's already sitting right there, no copying needed. Using
    `-migrate-state` when nothing moved, or vice versa, is a common way
    to get a confusing error instead of the migration you meant.

!!! success "The old DynamoDB table isn't automatically cleaned up"

    Switching to `use_lockfile` just stops *this config* from using the
    table — it doesn't delete it, and doesn't check whether anything
    else still depends on it. Safe to delete only after confirming no
    other project's backend still points at the same
    `dynamodb_table`.

``` bash
# What locking looks like when it's doing its job
$ terraform apply
Acquiring state lock. This may take a few moments...
Error: Error acquiring the state lock

Lock Info:
  ID:        7c2f9e1a-...
  Path:      dev/network/terraform.tfstate
  Operation: OperationTypeApply
  Who:       teammate@laptop
```

!!! success "This is what makes CI safe"

    Remote state with locking is the prerequisite for any CI pipeline
    applying Terraform — a CI job applying on merge and an engineer
    running `plan` locally have to share one source of truth, or the
    pipeline's idea of "current state" silently diverges from reality.

### Reading and overwriting remote state directly: pull and push

``` bash
# Read-only -- download the current remote state, print it to stdout
terraform state pull > state-snapshot.json

# Inspect it without needing raw S3/console access
terraform state pull | jq '.resources[].name'

# Dangerous -- unconditionally overwrite the remote state with a local file
terraform state push state-snapshot.json
```

|  | `state pull` | `state push` |
|---|---|---|
| Direction | Remote → local (a copy) | Local → remote (overwrites it) |
| Touches real state? | No — read-only, always safe to run | Yes — replaces whatever the remote currently holds |
| Good for | Inspecting or scripting against state (piping into `jq`) without console/S3 access | Recovering from a known-good backup, or a manual fix nothing else can do |
| The catch | A point-in-time snapshot — stale the moment anyone else applies after you pulled it | No diff, no plan, no confirmation prompt shown first — a stale or wrong local file silently erases what Terraform knows about real infrastructure |

!!! danger "push is a last resort, not a routine command"

    `state push` normally refuses to run if the remote state has moved
    on since your local copy was pulled (compared by an internal serial
    number) — that check exists specifically to stop exactly the
    accident this command makes possible. Overriding it with `-force`
    removes that last safety check entirely. Reach for `terraform state
    mv`/`rm` (see [Operating Terraform in
    Production](terraform-operating-in-production.md)) for routine
    state surgery; `push` is for genuine disaster recovery, not
    day-to-day use.

## Environment Isolation — Directories vs Workspaces

Two ways to run the same code against `dev` and `stg` without
duplicating the resource definitions themselves.

|  | Separate directories | Terraform workspaces |
|---|---|---|
| Structure | `environments/dev/`, `environments/stg/`, each with their own `backend.tf` and `.tfvars` | One directory, `terraform workspace new stg` creates a separate state within the same backend |
| State isolation | Fully separate state files, separate backend keys — a mistake in one physically cannot touch the other | Separate state, same backend config — one bad backend change affects every workspace |
| Blast radius of a bug | A typo in `environments/dev/main.tf` can't reach staging at all | A bug in the single shared `main.tf` reaches every workspace next apply |
| Good fit | Environments that should be able to diverge (different instance sizes, different modules even) and where mistakes must stay contained | Truly identical environments, or short-lived ones (a workspace per PR preview) |

``` bash
# Workspaces, for comparison
terraform workspace new stg
terraform workspace select stg
terraform apply -var-file=stg.tfvars
terraform workspace show   # confirm which one you're about to apply into
```

### The full terraform workspace command set

`terraform workspace new <name>`
:   Creates a new workspace with its own empty state, and switches to
    it immediately. Every project starts with one workspace already,
    called `default` — it's there even if you never run this command.

`terraform workspace select <name>`
:   Switches to an existing workspace. This is the step it's easy to
    forget before an `apply` — there's no prompt or warning, it just
    silently applies into whichever workspace was already selected.

`terraform workspace list`
:   Lists every workspace that exists for this configuration, with an
    asterisk marking the one currently active.

`terraform workspace show`
:   Prints just the name of the currently active workspace — the fast
    way to confirm what `apply` is actually about to touch, worth
    running as a habit right before it.

`terraform workspace delete <name>`
:   Removes a workspace and its state file. Terraform refuses if that
    workspace's state still has resources in it — run `destroy` inside
    that workspace first, or the delete fails rather than silently
    orphaning real infrastructure.

!!! danger "The workspace footgun"

    Nothing in the terminal loudly reminds you which workspace is
    selected — running `terraform apply` after forgetting a `workspace
    select` applies into whichever one you left active. Separate
    directories (see the layout in [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md)) exist specifically to
    make that mistake structurally impossible: the environment is which
    directory you `cd` into, not invisible session state.

### Pros and cons, specifically for separating credentials

One question workspaces can't answer: do they separate *which AWS
account or credentials* an environment uses? No — the `provider "aws" {
... }` block is one static config for the entire run, untouched by
which workspace is active.

- **Pro:** fast to spin up — `terraform workspace new` is one command,
  no new directory or backend config to write.
- **Pro:** state stays genuinely isolated per workspace, even though
  the config is shared.
- **Pro:** a good fit for short-lived, truly identical environments — a
  workspace per PR preview, disposable by design.
- **Con:** no credential or account separation at all — every workspace
  shares the exact same `provider` block, so it can't be the mechanism
  that keeps `dev` and `prod` on separate AWS accounts.
- **Con:** nothing in the terminal shows which workspace is active — a
  forgotten `workspace select` applies into whichever one was last left
  selected.
- **Con:** one shared `main.tf` means one bug reaches every workspace on
  the next `apply` — no structural containment the way separate
  directories give you.

## Remote State Data Sources Between Layers

Splitting a platform into layers (network, then compute, then
application) means the compute layer needs values — a VPC ID, a subnet
list — that only the network layer's state actually holds.
`terraform_remote_state` reads another layer's state as a data source,
read-only.

``` hcl
# in the compute layer
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "fahad-terraform-state"
    key    = "dev/network/terraform.tfstate"
    region = "ap-south-1"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.private_subnet_id
  # ...
}
```

!!! note "Only outputs cross the boundary"

    A layer can only read another layer's declared `output` values, not
    its internal resources — which is exactly the module-interface
    discipline from [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md), applied between whole
    layers instead of between a module and its caller. If compute needs
    a value the network layer hasn't output yet, the fix is adding that
    output, not reaching around it.

!!! danger "A layer boundary is also a blast-radius boundary"

    Splitting into layers means a network change requires its own
    `plan`/`apply`, separate from the compute layer's — you can no
    longer `apply` the whole platform in one command. That's the
    tradeoff: smaller, safer applies, at the cost of the multi-layer
    `apply` sequencing this buys you.

## Provider Aliases & a Second Region as a Variable

A `provider` block configures one region (or account). `alias` lets a
single config talk to a second one — the mechanism behind "the same
code applied to a second region by changing variables only."

``` hcl
# providers.tf
provider "aws" {
  region = var.primary_region     # e.g. "ap-south-1"
}

provider "aws" {
  alias  = "secondary"
  region = var.secondary_region   # e.g. "eu-west-1"
}

# usage -- everything else about the resource is identical
resource "aws_s3_bucket" "backup" {
  provider = aws.secondary
  bucket   = "${var.name_prefix}-backup-${var.secondary_region}"
}
```

For a full second-region deployment (not just one bucket), the cleaner
pattern is calling the same module twice, once per provider:

``` hcl
module "platform_primary" {
  source = "../modules/platform"
  providers = { aws = aws }
  region = var.primary_region
}

module "platform_secondary" {
  source = "../modules/platform"
  providers = { aws = aws.secondary }
  region = var.secondary_region
}
```

!!! success "Why this satisfies the deliverable"

    Nothing inside `modules/platform` hardcodes a region anywhere —
    every AZ, AMI lookup, and CIDR is already parameterised (this is
    what "the whole platform in code," in [Building a
    Platform](terraform-building-a-platform.md), actually depends on).
    Standing up `eu-west-1` becomes calling the module a second time
    with a different provider alias, not writing new resource blocks.

## fmt, validate, a Linter and a Scanner — From the First Commit

Four checks, in order of how cheap they are to run, all before a plan
ever touches real AWS:

``` bash
# 1. Formatting -- purely cosmetic, zero false positives
terraform fmt -recursive -check

# 2. Syntax and internal consistency -- catches typos, type mismatches, missing required args
terraform validate

# 3. Linting -- style and correctness rules validate can't see
tflint

# 4. Security scanning -- known-bad patterns (open SG, unencrypted volume, public S3)
tfsec .
# or: checkov -d .
```

`terraform fmt`
:   Rewrites files to canonical indentation and alignment. `-check`
    makes it exit non-zero instead of rewriting — the form to run in
    CI, so a PR fails instead of silently reformatting someone's
    branch.

`terraform validate`
:   Checks the config is internally consistent — references resolve,
    types match, required arguments are present. It does *not* check
    against real AWS state; a config can `validate` cleanly and still
    fail at `apply` because of an actual AWS-side constraint.

`tflint`
:   Catches things that are syntactically valid but wrong — an invalid
    instance type for the AWS provider, an unused variable, a
    deprecated argument.

`tfsec` / `checkov`
:   Static security scanners: flag a security group open to
    `0.0.0.0/0`, an unencrypted EBS volume, a public S3 bucket, before
    any of it is ever created.

!!! success "This is the same gate a CI pipeline runs"

    These four checks are exactly the pull-request gate a CI pipeline
    (Jenkins, GitHub Actions) should run on every Terraform PR —
    running them locally is rehearsal for wiring the identical commands
    into CI, not a separate step.

---

## Code Samples

- `code_samples/terraform/tf-state/` — a remote S3 backend with
  locking
- `code_samples/terraform/tf-state-locking/` — two independent
  projects (`project-1/`, `project-2/`) sharing one backend, to see
  locking actually block a concurrent apply
- `code_samples/terraform/tf-workspace/` — environment isolation via
  `terraform workspace`
