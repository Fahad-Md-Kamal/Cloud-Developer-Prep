---
title: "Terraform Fundamentals: From Clicks to Code"
---

# Terraform Fundamentals: From Clicks to Code

Provisioning by clicking in the AWS console or typing one-off `aws` CLI
commands leaves no record of *intended* state — only whatever state
infrastructure happens to be in right now. Terraform's job is to make
that intended state a file you can read, diff, review and re-apply. This
is the first of a five-part Terraform series; see
[Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md),
[State, Environments & Regions](terraform-state-environments-and-regions.md),
[Building a Platform](terraform-building-a-platform.md), and
[Operating Terraform in Production](terraform-operating-in-production.md)
for what follows.

## What Terraform Is, and Why

- Terraform is an Infrastructure-as-Code (IaC) tool — you describe the
  infrastructure you want in text files, and Terraform figures out which
  API calls turn what currently exists into that.
- This is a **declarative** model: you say *what* should exist ("one
  t3.micro instance, this security group attached"), not *how* to get
  there.
- Compare that to console/CLI work, which is **imperative** — each `aws
  ec2 run-instances` command is a step, and nothing records that the step
  happened except the resource itself.

|  | Console / CLI | Terraform |
|---|---|---|
| What you write | A sequence of clicks or commands to run once | A description of the end state, applied repeatedly |
| Record of intent | None — only whatever exists right now | The `.tf` files, committed to git |
| Re-running it | Re-clicking or re-running risks creating duplicates | Re-applying an unchanged config does nothing (idempotent) |
| Review before change | Not possible — the change already happened | `terraform plan` shows the change before it happens |

!!! note "Idempotent"

    Running the same Terraform config twice in a row with nothing changed
    produces "no changes" the second time — it doesn't create a second
    copy of anything. This is the property that makes it safe to re-run
    in CI on every commit, unlike re-running a one-off `aws` command by
    hand.

- Terraform itself is cloud-agnostic — the same tool manages AWS, GitHub,
  Datadog, or a Kubernetes cluster.
- What connects it to a specific system is a **provider**: a plugin that
  translates Terraform's generic "create this resource" into that
  system's actual API calls.

## Install & Provider Configuration

``` bash
# Install (Linux, via HashiCorp's apt repo)
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | \
  sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

terraform version
```

- Every Terraform project starts by declaring which providers it needs,
  and pinning their versions — the same principle as pinning a package
  version in `requirements.txt`, for the same reason.
- An unpinned provider can ship a breaking change and your next `plan`
  behaves differently with no line changed in your own code.

``` hcl
# versions.tf
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"   # any 5.x, never 6.x
    }
  }
}

provider "aws" {
  region  = "ap-south-1"
  profile = "fahad"
}
```

!!! danger "Unpinned = unreproducible"

    Skip `required_providers` and Terraform silently installs whatever
    the latest provider version is the first time anyone runs `init`.
    Two engineers running `init` a week apart can end up on two
    different AWS provider versions, applying the exact same `.tf`
    files with different results.

### A shorter command, if you want one

- `terraform` gets typed dozens of times an hour — a shell alias
  shortens it to two letters.
- This is a shell feature, not a Terraform one, so it goes in your
  shell's own config file, not anywhere in this project.

``` bash
# zsh (~/.zshrc) or bash (~/.bashrc) -- same syntax either way
echo "alias tf='terraform'" >> ~/.zshrc
source ~/.zshrc   # reload the current shell so the new alias takes effect

tf plan
tf apply
tf state list
```

!!! note "Where it lives matters"

    An alias defined only by typing it at the prompt disappears the
    moment that terminal closes. Appending it to `~/.zshrc`/`~/.bashrc`
    makes it permanent — that file re-runs every time a new interactive
    shell starts, which is also why a fresh terminal always picks up an
    edit without needing `source` at all.

### Widening the constraint later needs -upgrade

Bump `version = "~> 5.0"` to `"~> 6.0"` after `init` has already run
once, and a plain `terraform init` fails instead of picking up the new
version:

``` text
│ Error: Failed to query available provider packages
│
│ Could not retrieve the list of available versions for provider hashicorp/aws:
│ locked provider registry.terraform.io/hashicorp/aws 5.100.0 does not match
│ configured version constraint ~> 6.0; must use terraform init -upgrade to
│ allow selection of new versions
```

``` bash
terraform init -upgrade
```

!!! note "Why plain init can't fix this on its own"

    - `.terraform.lock.hcl` records the exact provider version everyone
      on the project is currently using — that's the whole point of a
      lock file (same reason a `package-lock.json` exists).
    - A bare `init` only *installs* whatever the lock file already says;
      it deliberately never widens a lock to satisfy a new constraint on
      its own, since silently upgrading everyone's provider version on a
      routine `init` is exactly the unreproducible behavior the lock
      file exists to prevent.
    - `-upgrade` is the explicit, opt-in step that re-resolves the
      constraint and rewrites the lock file — commit that rewritten lock
      file so the rest of the team gets the same resolved version.

!!! danger "A stray env var beats the profile every time"

    - A real `plan` once failed with `InvalidClientTokenId: The security
      token included in the request is invalid` — even though `aws sts
      get-caller-identity --profile fahad` worked fine from a different
      terminal, same machine, same credentials file.
    - Cause: an `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` left exported
      earlier in that specific shell session, from something typed by
      hand.
    - Both the AWS CLI and the Terraform AWS provider check environment
      variables *before* the profile in `~/.aws/credentials` — a stale
      exported key silently overrides `profile = "fahad"` in every
      command run in that terminal, with no warning that it's happening.
    - `env | grep AWS` is the first thing to check when a credential
      error doesn't match what `~/.aws/credentials` actually contains.

## HCL Basics: Resources & Data Sources

Terraform's config language is HCL. Everything is a named block: a
**type**, a **local name** you choose, and a body of arguments.

### If you already know a programming language

HCL isn't object-oriented, but the shapes rhyme closely enough that
mapping onto OOP terms you already know is a legitimate shortcut — as
long as you also clock where the mapping breaks down.

| HCL | OOP equivalent |
|---|---|
| A provider (`hashicorp/aws`) | An imported library/SDK — brings a vocabulary of pre-built "classes" into scope, the way `import boto3` brings AWS's API surface into a Python script |
| A resource/data **type** (`aws_instance`, `aws_ami`) | A class — a fixed blueprint of what arguments and attributes this kind of thing has. You never define one yourself; the provider plugin ships it, versioned (above) |
| `resource "aws_instance" "app" { ami = ... }` | Instantiating an object: `app = aws_instance(ami=...)`. The local name (`"app"`) is the variable you're assigning that instance to |
| A `data` block | Calling a read-only getter/query function — not constructing something new, just fetching an existing object's attributes into a reference you can use |
| `aws_instance.app.public_ip` | Dot-notation property access on an object instance — exactly like `my_object.public_ip` |
| A `variable` block | A typed function parameter, complete with a default value and validation — closer to a TypeScript-style typed parameter than an untyped one |
| A `locals` block | A local constant computed once — like `const` in JS or `final` in Java: read-only, can't be overridden from outside |
| An `output` block | A `return` statement — hands a value back to whoever called this config: a human at the CLI for a root module, or the parent config for a child module |
| A `module` call | Calling a function with named arguments (its `variable`s) that hands back named return values (its `output`s) — see [Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md) for designing that interface |

!!! danger "Where the analogy breaks"

    - You can't subclass `aws_instance`, add a method to it, or define
      your own resource types — the "classes" here are closed, fixed by
      whatever the provider version ships.
    - HCL isn't executed top-to-bottom like a script: block order in the
      file is irrelevant.
    - Terraform reads the references between blocks to build a
      dependency graph, then executes in whatever order that graph
      requires — closer to how a spreadsheet evaluates formulas by
      their cell references than to a program running line by line.

!!! note "Typed, but not general-purpose"

    - `variable` blocks are genuinely strictly typed (`string`,
      `number`, `bool`, `list(...)`, `map(...)`, `object({...})`) with
      no implicit coercion between incompatible types, and support the
      same kind of input validation you'd write at a typed function's
      boundary.
    - What HCL doesn't have is general-purpose control flow — no
      user-defined classes, no arbitrary loops, no if/else statements
      outside of a handful of expression-level substitutes (a ternary,
      `for` expressions, `dynamic` blocks).
    - It's a declarative configuration language with a real type system
      bolted on, not a programming language you'd write an algorithm in.

``` hcl
resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

- `resource` means "create and manage this" — Terraform will create it,
  and destroy it if you remove the block.
- `data` means "look this up, don't manage it" — for something that
  already exists and you just need to reference (an existing AMI, an
  existing VPC someone else created).

### What you can set vs what Terraform tells you afterward

An `aws_instance` plan shows 40+ fields, but only a handful are ones you
control — the rest are marked `(known after apply)` because AWS assigns
them at creation time and no config value could ever have set them.

``` text
  + resource "aws_instance" "app_server" {
      + ami                          = "ami-0333333333333333"   # you set this
      + instance_type                = "t3.micro"                # you set this
      + arn                          = (known after apply)        # AWS assigns this
      + id                           = (known after apply)        # AWS assigns this
      + key_name                     = (known after apply)        # settable, just unset
      + public_ip                    = (known after apply)        # AWS assigns this
      + subnet_id                    = (known after apply)        # settable, just unset
      + vpc_security_group_ids       = (known after apply)        # settable, just unset
    }
```

- `(known after apply)` covers two different situations that look
  identical in a plan: an argument you simply didn't set (like
  `key_name` or `subnet_id` above — add it and it stops being unknown),
  and a true output that no config value could ever populate (like `arn`
  or `id` — those only exist once AWS creates the real object).

| Category | Examples on `aws_instance` |
|---|---|
| Set, and showing a real value | `ami`, `instance_type`, `tags` |
| Optional, unset — add these to customise | `key_name`, `subnet_id`, `vpc_security_group_ids`, `associate_public_ip_address`, `availability_zone`, `user_data`, `monitoring`, `root_block_device`, `metadata_options`, `iam_instance_profile` |
| Pure output — never settable, at all | `arn`, `id`, `instance_state`, `private_dns`, `public_dns`, `primary_network_interface_id`, `password_data` |

!!! success "The registry docs tell you which is which"

    Every resource page on the [Terraform
    Registry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
    splits into an "Argument Reference" section (settable) and an
    "Attributes Reference" section (read-only). If something's listed
    only under Attributes, no amount of config will ever set it
    directly; it's always read back via a reference like
    `aws_instance.app_server.public_ip`, the same dot-notation used for
    `data.aws_ami.ubuntu.id` below.

``` hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "app" {
  ami           = data.aws_ami.ubuntu.id   # reference: type.name.attribute
  instance_type = "t3.micro"
  vpc_security_group_ids = [aws_security_group.web.id]
}
```

### The data block, reserved keywords vs names you chose

`data`
:   Reserved keyword — "look this up, don't create or manage it." The
    opposite of `resource`.

`"aws_ami"`
:   The data source's **type**. Fixed, defined by the AWS provider —
    this is the provider's built-in "look up an AMI" query, not
    something you name yourself.

`"ubuntu"`
:   A local name **you invented**. Purely a label so the rest of your
    config can reference this lookup (`data.aws_ami.ubuntu.id` above).
    Rename it to `"my_ami"` and nothing breaks except that one
    reference.

`most_recent`
:   A fixed argument from the `aws_ami` schema, not custom. When the
    filters below match more than one AMI, take the newest instead of
    erroring on ambiguity.

`filter { name = "name" ... }`
:   `filter` is a repeatable nested block — stack several and all must
    match (AND logic). Inside it, `name` is a fixed key that says
    *which AMI field* you're filtering on; confusingly, its value here
    is also the literal string `"name"`, meaning "filter on the AMI's
    own Name field" (as opposed to architecture, owner-alias, etc.) —
    the key and the value are unrelated, they just happen to use the
    same word.

`values`
:   Fixed argument, always a list even for one item. Supports `*`
    wildcards — the trailing `*` here exists because the real AMI name
    ends in a build timestamp that changes with every release.

`owners`
:   Fixed top-level argument, restricts results to AMIs published by
    this specific AWS account. `099720109477` is Canonical's real,
    publicly documented account ID for official Ubuntu AMIs — not a
    secret, the same ID AWS's own docs use.

!!! danger "Why owners isn't optional"

    Without it, the name-pattern filter alone could match an AMI from
    *any* account that happens to use a similar name — including a
    malicious lookalike published to look official. Pinning `owners` is
    what makes this query trustworthy, not just convenient.

!!! note "This runs as a live query"

    The whole `data` block executes against the real AWS API at
    `plan`/`apply` time — it returns whatever AMI currently matches, so
    `aws_instance.app` always gets the latest Ubuntu AMI instead of a
    hardcoded ID that goes stale next month.

!!! note "This is where dependency order comes from"

    - `aws_instance.app` references `aws_security_group.web.id` and
      `data.aws_ami.ubuntu.id` — Terraform reads these references to
      build its dependency graph automatically.
    - It knows to create the security group before the instance without
      you writing anything that says "do this first."
    - This is exactly why explicit `depends_on` (see [Modules & Advanced
      HCL](terraform-modules-and-advanced-hcl.md)) is a last resort, not
      a first instinct — most ordering should come from references like
      these.

### Heredoc strings — for a multi-line value like user_data

Writing a multi-line script inline as a normal quoted string means
escaping every newline. A heredoc avoids that — everything between the
opening marker and its matching closing line is taken literally,
newlines included:

``` hcl
resource "aws_instance" "app" {
  # ...
  user_data = <<-EOF
    #!/bin/bash
    sudo apt-get update
    sudo apt-get install -y apache2
  EOF
}
```

!!! danger "No space between <<- and the marker"

    `<<- EOF` (with a space) fails to parse at all —
    `Invalid expression: Expected the start of an expression, but found
    an invalid expression token` — because `<<-` and the marker name
    have to be written as one unbroken token, `<<-EOF`. With the space,
    Terraform doesn't recognize it as a heredoc opener, and everything
    that follows (including the actual script content) gets misparsed
    as HCL rather than treated as string content.

!!! note "Why the hyphen"

    `<<-EOF` (with the hyphen) strips the leading whitespace common to
    every line, which is what lets the closing `EOF` sit indented to
    match the surrounding code instead of needing to start at column 0,
    the way a plain `<<EOF` would require.

## The Workflow: init, plan, apply, destroy

``` bash
# 1. Download providers/modules this config needs (run once per checkout, or after adding one)
terraform init

# 2. Show what WOULD change, without changing anything
terraform plan

# 3. Actually make the change (re-shows the plan, asks for confirmation)
terraform apply

# 4. Tear everything this config manages back down
terraform destroy
```

`init`
:   Downloads the provider plugins declared in `versions.tf` and any
    modules referenced by `source`, and sets up the backend that stores
    state (see [State, Environments &
    Regions](terraform-state-environments-and-regions.md)). Safe to
    re-run any time — it doesn't touch real infrastructure.

`plan`
:   Compares your `.tf` files against Terraform's record of what it
    last created (the state file) and against the real infrastructure,
    and prints exactly what it would add, change, or destroy. Nothing
    is touched. This is the step you never skip.

`apply`
:   Runs the same comparison as `plan`, shows it to you, and — after
    you type `yes` — makes the real API calls.

`destroy`
:   The inverse of `apply`: deletes everything this config currently
    manages. Same confirmation prompt, same real API calls, in reverse.

!!! success "Never apply without reading the plan"

    The habit that matters more than any command: read what `plan` says
    before typing `yes` at `apply`. A one-line variable change can
    produce a plan that destroys and recreates a database if it touches
    a value that forces replacement — the diff is the only place that
    would be visible before it happens.

## Reading a Plan Diff Line by Line

``` text
Terraform will perform the following actions:

  # aws_instance.app will be updated in-place
  ~ resource "aws_instance" "app" {
        id            = "i-0aaa1111aaaa11111"
      ~ instance_type = "t3.micro" -> "t3.small"
        # (28 unchanged attributes hidden)
    }

  # aws_launch_template.app must be replaced
-/+ resource "aws_launch_template" "app" {
      ~ id          = "lt-0bbb2222bbbb22222" -> (known after apply)
      ~ image_id    = "ami-0111111111111111" -> "ami-0222222222222222" # forces replacement
        name_prefix = "app-"
    }

Plan: 1 to add, 1 to change, 1 to destroy.
```

`~` update in-place
:   The resource stays, but an attribute changes on the live object —
    no downtime for something like an EC2 instance's `instance_type`
    (it does still require a stop/start under the hood for that
    particular attribute, which Terraform will also tell you about).

`-/+` destroy and re-create (replacement)
:   The changed attribute can't be updated on the existing object at
    all — AWS's API has no "update" call for it — so Terraform must
    delete the old one and create a new one. The line `# forces
    replacement` tells you exactly which attribute triggered this.

`+` / `-` alone
:   A resource being newly created, or a resource being removed because
    its block was deleted from the config.

"Plan: X to add, Y to change, Z to destroy"
:   The summary line at the bottom. Read the detail above it first — "1
    to change" reads harmless right up until you notice it's the
    production database's launch template being replaced, not updated.

!!! danger "The line to actually watch for"

    `# forces replacement` is the single most consequential phrase in
    any plan output. For anything stateful (a database, an EBS volume
    with data on it), a forced replacement means the resource is
    destroyed and a brand-new empty one created in its place —
    Terraform will not warn you beyond this comment, and it will not
    stop to ask if you're sure that's what you meant.

## Variables, Locals & Outputs

Three ways values flow through a config: `variable` for input the
caller supplies, `locals` for a value computed once and reused, `output`
for a value handed back out.

``` hcl
variable "environment" {
  type        = string
  description = "dev or stg"
  validation {
    condition     = contains(["dev", "stg"], var.environment)
    error_message = "environment must be \"dev\" or \"stg\"."
  }
}

locals {
  name_prefix = "app-${var.environment}"   # computed once, referenced everywhere below
}

resource "aws_instance" "app" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
  tags          = { Name = local.name_prefix }
}

output "instance_public_ip" {
  value       = aws_instance.app.public_ip
  description = "Public IP, for the smoke test after apply."
}
```

!!! note "variable vs locals"

    A `variable` is set from outside the config — a `.tfvars` file, a
    `-var` flag, an environment variable. A `locals` value is computed
    inside the config from other values and can never be overridden
    from outside. If you find yourself wanting to override a `locals`
    value, it should have been a `variable` from the start.

!!! success "Validation catches typos before AWS does"

    Without the `validation` block above, passing `environment =
    "staging"` (instead of `"stg"`) would sail through `plan` and only
    fail deep into `apply` once some downstream resource tries to use
    it, with a much less obvious error. Same principle as module-level
    validation (see [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md)), applied to root-level
    variables too.

### Outputting a whole count/for_each collection, not just one instance

- The `output` above reads one instance's `public_ip` directly.
- With `count` or `for_each`, there's no single instance to read from —
  `aws_instance.app` is a collection, one object per index or key.
- A `for` expression inside the output pulls one attribute out of every
  entry at once:

``` hcl
resource "aws_instance" "app" {
  count = 3
  # ...
}

output "instance_ids" {
  value       = { for idx, inst in aws_instance.app : idx => inst.id }
  description = "Every instance's ID, keyed by its count index."
}
# result: { 0 = "i-0aaa...", 1 = "i-0bbb...", 2 = "i-0ccc..." }
```

!!! note "This is a map comprehension, not a loop"

    `{ for k, v in collection : k => v.attr }` reads almost exactly
    like Python's `{k: v.attr for k, v in collection.items()}` — both
    take an iterable of key/value pairs and return a brand-new map with
    the same keys but transformed values. Unlike a Python `for`
    statement, there's no loop body here at all — the whole expression
    *is* the result, which is true of every `for` in HCL, inside an
    `output`, a `locals`, or a `for_each` argument alike.

## Supplying Variable Values — .tfvars Files and Loading Order

- A `variable` block declares that an input exists. It doesn't supply a
  value — that's a separate question, and a `.tfvars` file is the most
  common answer.
- It's just a list of assignments, one per variable, no `variable`
  keyword involved:

``` hcl
# stage.tfvars
instance_type    = "t3.micro"
region           = "ap-south-1"
ami_id           = "ami-0333333333333333"
username_prefix  = "fmk-tf"
app_env          = "staged"
```

- A second file, `production.tfvars`, declares the exact same variable
  names with different values — that's the entire mechanism behind "the
  same code, different environment."
- Nothing in `main.tf` changes; only which file gets loaded does.

### Two ways a .tfvars file actually gets loaded

`terraform.tfvars` (or anything named `*.auto.tfvars`)
:   Loaded automatically, every time — no flag needed. Convenient for a
    single-environment project, but it means there's nothing in the
    command line that says which values got used; you'd have to go look
    at the file.

Any other filename — `stage.tfvars`, `production.tfvars`
:   Never loaded automatically. Requires an explicit `-var-file` flag,
    every time:

``` bash
terraform plan  -var-file="stage.tfvars"
terraform plan  -var-file="production.tfvars"
```

This is the better default for anything with more than one environment
— the environment being targeted is now visible in the command itself,
not hidden inside a filename someone has to already know to look for.

!!! note "Precedence, when more than one source sets the same variable"

    - Lowest to highest: a `TF_VAR_name` environment variable, then
      `terraform.tfvars`, then any `*.auto.tfvars` files
      (alphabetical), then every `-var-file` in the order given on the
      command line, then a bare `-var` flag — highest priority, wins
      over everything.
    - In practice this rarely needs memorizing in full; the one rule
      worth keeping is that whatever's passed explicitly on the command
      line always beats whatever's sitting in a file.

### A variable with no type accepts anything

``` hcl
# valid HCL -- no type, no default, no description
variable "app_env" {}
```

!!! danger "No type means no validation at all"

    - This isn't a shortcut, it's an opt-out. Terraform infers the type
      from whatever's actually passed at runtime and checks nothing — a
      `.tfvars` file typo that supplies a list where a string was
      expected won't be caught here; it'll propagate until something
      downstream breaks, with an error far away from the actual
      mistake.
    - It also means the variable is **required** with no visible signal
      of what shape a caller should supply — compare that to `variable
      "instance_count"` with `type = number` and `default = 2`, which
      documents both the shape and a safe fallback in three lines.
    - Always give a variable a `type`, even one as loose as `any` —
      that's still a deliberate choice, not an accident of leaving the
      argument out.

---

## Code Samples

- `code_samples/terraform/basics/` — variable/output/tfvars patterns
  from this page (`var-file/`, `var-tfvar/`, `var-multi-tfvars/`,
  `output/`), plus a plain `main.tf`/`variable.tf` starting point
- `code_samples/terraform/day-1/` — a minimal first `init`/`plan`/`apply`
  project
