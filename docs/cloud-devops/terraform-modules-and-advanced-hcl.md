---
title: "Terraform: Iteration, Modules & Advanced HCL"
---

# Terraform: Iteration, Modules & Advanced HCL

The language features that shape everything downstream — repetition,
conditional structure, module design — then packaging it for reuse. See
[Terraform Fundamentals](terraform-fundamentals.md) for the basics this
builds on, and [State, Environments &
Regions](terraform-state-environments-and-regions.md) for what comes
next.

## count vs for_each

Both repeat a resource block. `count` indexes by number (`0`, `1`,
`2`…). `for_each` indexes by a stable key from a map or set of strings.
That difference is small on day one and expensive a month later.

``` hcl
# count -- indexed by position
resource "aws_subnet" "private" {
  count      = length(var.private_cidrs)
  vpc_id     = var.vpc_id
  cidr_block = var.private_cidrs[count.index]
  tags       = { Name = "private-${count.index}" }
}
# state addresses: aws_subnet.private[0], aws_subnet.private[1], aws_subnet.private[2]

# for_each -- indexed by key
resource "aws_subnet" "private" {
  for_each   = var.private_subnets   # map(object({ cidr = string, az = string }))
  vpc_id     = var.vpc_id
  cidr_block = each.value.cidr
  availability_zone = each.value.az
  tags       = { Name = "private-${each.key}" }
}
# state addresses: aws_subnet.private["a"], aws_subnet.private["b"], aws_subnet.private["c"]
```

!!! danger "The gotcha"

    Remove the middle element from a `count`-driven list and every
    subnet after it shifts down one index. Terraform doesn't see "one
    subnet removed" — it sees `[2]` now holding what used to be at
    `[3]`, so it destroys and recreates every resource from that index
    onward, not just the one you actually deleted. On a subnet with an
    attached NAT gateway or an RDS instance, that's an outage triggered
    by an unrelated one-line diff.

!!! success "The fix"

    `for_each` keys are strings, not positions, so removing one entry
    (`aws_subnet.private["b"]`) only touches that address — everything
    else in state is untouched. If you're stuck with a list, convert it
    to a map keyed by something stable first: `{ for s in var.list :
    s.name => s }`.

!!! danger "`count.index` only exists where `count` is set"

    - Trying to reference `count.index` inside a `locals` block fails
      outright: `Error: Reference to "count" in non-counted context —
      The "count" object can only be used in "module", "resource", and
      "data" blocks, and only when the "count" argument is set.`
    - A `locals` block has no loop of its own to index into.
    - Building a list of per-item values for later use needs a `for`
      expression with its own loop variable instead — `[for i in
      range(3) : "name-${i}"]` — then index into that list with
      `count.index` from inside the resource that actually has `count`.

### merge() — overriding one key of a map without losing the rest

- A common need with `count`/`for_each`: reuse a shared base set of tags
  on every resource, but give each instance its own `Name`.
- Assigning `tags` directly replaces the whole map — `merge()` combines
  two maps instead, with the second map's keys winning on any overlap:

``` hcl
variable "project_environment" {
  type = map(string)
  default = {
    Name  = "app"
    Owner = "fahad"
    Event = "learning-devops-tf"
  }
}

resource "aws_instance" "app" {
  count = 3
  # ...
  tags = merge(
    var.project_environment,
    { Name = "${var.project_environment["Name"]}-${count.index + 1}" }
  )
}
# result per instance: { Name = "app-1", Owner = "fahad", Event = "learning-devops-tf" }
#                       { Name = "app-2", Owner = "fahad", Event = "learning-devops-tf" }  ...
```

!!! danger "Without merge(), the rest of the map silently disappears"

    - `tags = { Name = "app-${count.index + 1}" }` on its own is valid
      HCL — it just replaces `tags` entirely, so `Owner` and `Event`
      quietly vanish from every instance with no warning.
    - `merge(mapA, mapB)` returns a new map containing every key from
      both — `mapB`'s value wins wherever a key exists in both — which
      is what lets one shared variable stay the single source of truth
      for the tags every resource has in common.

|  | `count` | `for_each` |
|---|---|---|
| Index type | Number | String key (map or set) |
| Removing a middle item | Reshuffles and recreates everything after it | Destroys only that one resource |
| Reference syntax | `count.index` | `each.key` / `each.value` |
| Good fit | N identical, disposable copies (e.g. N NAT gateways, one per AZ index) | Anything you'll add to, remove from, or look up by name later |

Default to `for_each`. Reach for `count` only for a genuinely fixed,
order-independent replication count, or the simple `count = var.enabled
? 1 : 0` toggle for an optional resource.

## Dynamic Blocks

A `dynamic` block generates a repeatable *nested* block from a list or
map — for arguments that appear once per resource, plain interpolation
is enough; `dynamic` is for things like a security group's `ingress`
block, where you need a variable number of them.

``` hcl
variable "ingress_rules" {
  type = list(object({
    port        = number
    cidr_blocks = list(string)
    description = string
  }))
}

resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = var.vpc_id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = "tcp"
      cidr_blocks = ingress.value.cidr_blocks
      description = ingress.value.description
    }
  }
}
```

!!! note "Only for nested blocks"

    `dynamic` exists because `ingress { ... }` is a nested block, not an
    argument — you can't just pass it a list the way you'd pass a list
    to `cidr_blocks`. If the thing you're repeating is a plain argument,
    you don't need `dynamic` at all; a `for` expression inside the
    argument is enough.

!!! danger "Readable but easy to overuse"

    A security group with one `dynamic "ingress"` block driven by a
    well-named variable is clear. Three or four nested `dynamic` blocks
    inside one resource, each driven by a different variable, is
    usually a sign the resource wants to be a module instead — dynamic
    blocks trade explicitness for flexibility, and that trade stops
    paying off past one level of nesting.

!!! danger "A dynamic block only means anything inside a resource"

    Writing `dynamic "ingress" { ... }` at the top level of a file — not
    nested inside any `resource` block — fails with `Unexpected block:
    Blocks of type "dynamic" are not expected here`. A `dynamic` block
    generates a nested block *for whichever resource it lives inside*;
    on its own, with no resource around it, Terraform doesn't recognize
    `dynamic` as a valid block type at all. It has to sit exactly where
    a literal `ingress { }` block would otherwise go, inside `resource
    "aws_security_group" "main" { ... }`.

!!! note "ingress.value isn't self-reference — it's a name collision"

    - The label on `dynamic "ingress"` does two jobs at once: it says
      which nested block type to generate, *and* it becomes the default
      name of the loop variable inside `content { }` — which is why
      `ingress.value` can look like the block referencing itself.
    - It isn't; it's the same role as `each.value` on a resource-level
      `for_each`, just defaulting to a name that happens to match the
      block label.
    - An explicit `iterator` argument removes the ambiguity — add
      `iterator = rule` alongside `for_each` in the block above, then
      use `rule.value.port` in place of every `ingress.value.port`
      inside `content { }`. Same result, but `rule.value` reads
      unambiguously as "the current item," never as the block calling
      itself.

## `lifecycle` and Explicit Dependencies

Terraform infers most dependencies automatically from references
between resources. `lifecycle` and `depends_on` exist for the cases it
can't infer, or gets wrong for your situation.

### lifecycle meta-argument

``` hcl
resource "aws_launch_template" "app" {
  name_prefix   = "app-"
  image_id      = var.ami_id
  instance_type = var.instance_type

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "primary" {
  # ...
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [password]   # rotated out-of-band, don't fight it
  }
}
```

`create_before_destroy`
:   Builds the replacement before tearing down the original. Without
    it, a launch template change destroys the old template first — if
    the new one fails to create, the ASG is left pointing at nothing.
    Essential for anything an ASG or ALB target group references.

`prevent_destroy`
:   Makes `terraform destroy` (and any plan that would replace the
    resource) fail loudly instead of deleting it. Use it on anything
    with data you can't regenerate from code — the primary database,
    not the ASG.

`ignore_changes`
:   Tells Terraform to stop diffing specific attributes, even if the
    real resource drifts from what's in config. Use it for values
    something else legitimately manages (autoscaling-adjusted
    `desired_capacity`, a password rotated by Secrets Manager) — never
    as a blanket way to silence a diff you don't understand.

!!! danger "prevent_destroy blocks real teardown too"

    It doesn't distinguish "someone fat-fingered `destroy`" from "we're
    intentionally decommissioning this." A genuine teardown means
    removing the `lifecycle` block (or setting `prevent_destroy =
    false`) first, applying that change, then destroying — an explicit
    two-step, by design.

### Explicit depends_on

Terraform sees a dependency wherever one resource's argument references
another resource's attribute. `depends_on` is for ordering that exists
only in AWS's behavior, not in any attribute reference — e.g. an IAM
role's policy attachment finishing before the compute resource that
assumes that role is created.

``` hcl
resource "aws_ecs_service" "app" {
  # nothing here references aws_iam_role_policy_attachment.ecs_exec directly,
  # but the task will fail to start if the permissions aren't attached yet
  depends_on = [aws_iam_role_policy_attachment.ecs_exec]
  # ...
}
```

!!! success "Reach for it last"

    Every explicit `depends_on` is a sign Terraform couldn't infer the
    relationship from your config. Before adding one, check whether
    restructuring the reference (e.g. reading the role's ARN from an
    output instead of hardcoding it) would let Terraform infer the same
    ordering automatically — that stays correct even if the resources
    are later refactored.

## Module Interface Design

A module's `variables.tf` and `outputs.tf` are its API. Everything
inside `main.tf` is an implementation detail the caller shouldn't need
to know about.

``` hcl
# variables.tf
variable "name" {
  type        = string
  description = "Prefix applied to every resource this module creates."
}

variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "EC2 instance type for the ASG's launch template."
  validation {
    condition     = can(regex("^t3\\.", var.instance_type))
    error_message = "Only t3.* instance types are approved for this environment."
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC to launch into. No default -- callers must be explicit."
}

# outputs.tf
output "asg_name" {
  value       = aws_autoscaling_group.this.name
  description = "Name of the created Auto Scaling Group, for attaching alarms."
}

output "security_group_id" {
  value       = aws_security_group.this.id
  description = "SG ID, so callers can add extra ingress rules without editing this module."
}
```

!!! note "Required vs optional"

    A variable with no `default` is required — the caller must supply
    it, and Terraform refuses to plan without it. That's the right
    choice for anything with no safe guess (`vpc_id`, `name`). Give a
    `default` only to genuinely optional knobs (`instance_type`, tag
    overrides) — defaulting something like `vpc_id` "for convenience" is
    how a module quietly gets applied into the wrong VPC.

!!! success "Validate at the boundary"

    A `validation` block turns "the apply failed 4 minutes in with an
    opaque AWS error" into "the plan refused to run with a one-line
    message," for the exact same underlying mistake. Put constraints you
    already know at input time (allowed instance families, CIDR shape,
    name length limits) into `validation` blocks rather than discovering
    them from a provider error.

Pin the module's own required versions too, so a caller can't apply it
against an incompatible Terraform or provider release without being
told explicitly:

``` hcl
# versions.tf
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

!!! danger "A child module can't see the caller's `locals` or `variables` at all"

    - A real error, hit building a VPC module: `locals { env = "staging"
      }` lived in the root module, and the child module referenced
      `local.env` directly in a resource's tags — failing immediately
      with `Reference to undeclared local value`.
    - A module is a fully isolated scope; it has no visibility into
      whatever called it, no matter how "nearby" the value looks in the
      file tree.
    - The fix is always the same shape: declare `variable "env" {}` in
      the module's own `variables.tf` (no `default`, since the caller
      must always supply it — see "required vs optional" above), then
      pass it in explicitly from the call site: `module "vpc" { source =
      "./modules/vpc"; env = local.env }`.
    - The value crosses the boundary only because it's named as an
      argument, never because the module happened to be a subdirectory
      of the one that defined it.

!!! danger "`module.vpc.id` doesn't exist until the module says it does"

    - A follow-on error in the same session: `vpc_id = module.vpc.id`
      inside a sibling module call, failing with `Unsupported attribute`
      — the `vpc` module had no `outputs.tf` at all.
    - Nothing about a resource living inside a module makes its
      attributes automatically visible outside it; an `output` block is
      the only thing that exposes anything, and the output's *name* is
      what the caller references (`output "id" { value = aws_vpc.main.id
      }` makes `module.vpc.id` valid — the name doesn't have to match
      the underlying attribute, though keeping it identical, as here, is
      the least surprising choice).
    - The same mistake showed up a second time moments later, in a
      subnet module's own `output.tf` that referenced a resource label
      (`aws_subnet.private_zone1`) that had since been renamed to
      `aws_subnet.sn` in `main.tf` — the output file simply hadn't been
      updated to match.
    - Renaming a resource inside a module doesn't just risk breaking
      `main.tf`; every `output` referencing that resource needs the same
      rename.

### Shaping data at the boundary between two modules

A module's output doesn't have to hand back exactly what it holds
internally — narrowing it to just what the next module needs is itself
part of interface design. A `main.tf` wiring a `network` module's output
into a `compute` module's input does exactly this:

``` hcl
module "compute" {
  source = "./modules/compute"
  subnet_ids = { for az, subnet in module.network.public_subnets : az => subnet.id }
  # ...
}
```

`module.network.public_subnets` is a map of *whole subnet objects* (id,
cidr_block, arn, tags — everything). `compute`'s `subnet_ids` variable
only wants plain ID strings. The for-expression bridges that gap:

``` text
module.network.public_subnets                    the for-expression's result
{                                                  {
  "1a" = { id = "subnet-0aaa...",                    "1a" = "subnet-0aaa..."
            cidr_block = "11.0.1.0/24",     -->       "1b" = "subnet-0bbb..."
            arn = "...", tags = {...} }              }
  "1b" = { id = "subnet-0bbb...", ... }
}
```

!!! success "Same keys in, same keys out"

    `for az, subnet in ... : az => subnet.id` keeps every key exactly as
    it was (`"1a"`, `"1b"`) and replaces only the value — the whole
    subnet object collapses down to just its `.id`. This is the same
    map-to-map for-expression as
    [Fundamentals](terraform-fundamentals.md)'s collection output, just
    used at a module boundary instead of in an `output` block —
    narrowing a rich internal object down to the one field a caller
    actually needs, rather than making every downstream module reach
    into fields it has no business touching.

## Versioning & Sourcing Modules

Where a module's code lives, and how a caller pins to a specific version
of it, has direct consequences for whether a `plan` run next month
reproduces the one you ran today.

| Source | Syntax | Reproducible? |
|---|---|---|
| Local path | `source = "../modules/network"` | Yes, but only within one repo — fine for a single-repo layout |
| Git, floating branch | `source = "git::https://.../network.git?ref=main"` | No — `main` keeps moving, the same config can resolve to different code tomorrow |
| Git, pinned tag | `source = "git::https://.../network.git?ref=v1.4.0"` | Yes — a tag is (by convention) immutable |
| Terraform Registry | `source = "app.terraform.io/org/network/aws"`, `version = "~> 1.4"` | Yes, with the added benefit of registry-enforced semver |

``` hcl
module "network" {
  source  = "git::https://github.com/example-org/tf-modules.git//network?ref=v1.4.0"
  name    = "app"
  vpc_cidr = "10.0.0.0/16"
}

module "ecs_service" {
  source  = "app.terraform.io/example-org/ecs-service/aws"
  version = "~> 2.1"

  name        = "api"
  cluster_arn = module.ecs_cluster.arn
}
```

!!! danger "A floating ref isn't a version"

    `?ref=main` means "whatever the module author most recently
    pushed." Two engineers running `terraform plan` an hour apart, on
    the exact same calling code, can get different plans if `main`
    moved in between — and there's no diff in your own repo to explain
    why. Always pin to a tag or a full commit SHA, never a branch name.

!!! success "Semver on the module itself"

    A published module should bump its major version on any breaking
    interface change (a variable removed, a required input added, an
    output renamed) — exactly like a library. Callers then use `~>`
    constraints to accept patch/minor updates automatically while
    breaking changes require a deliberate version bump in the caller's
    own code.

## Composition vs Over-Abstraction, and Repo Layout

A module is worth the indirection when it's used more than once, or
when its interface has genuinely stabilized. Before either is true, a
module is just a resource block wearing a costume — one more file to
open to see what actually gets created.

!!! success "Rule of three"

    Write the resource inline the first time. Copy it the second time.
    Only extract a module the third time a near-identical block shows
    up — by then the actual variable inputs (what really differs
    between the three copies) are obvious, instead of guessed at up
    front.

!!! danger "Over-abstraction looks like caution"

    A module with 40 input variables "for flexibility," most of which
    every caller sets to the same default, isn't reusable — it's one
    specific configuration with extra steps. It hides the actual
    resource shape from anyone reading the calling code, and every new
    requirement means threading one more variable through the whole
    interface. If every caller passes the same value for a variable,
    that value belongs inside the module, not in its interface.

### A repository layout that survives a year of change

``` text
.
├── modules/
│   ├── network/          # VPC, subnets, route tables, NAT
│   ├── security-groups/
│   ├── compute-asg/      # launch template + ASG + target group attachment
│   └── ecs-service/      # task def + service, one block per microservice
├── environments/
│   ├── dev/
│   │   ├── main.tf       # calls the modules above with dev's variable values
│   │   ├── backend.tf    # dev's remote state config
│   │   └── terraform.tfvars
│   └── stg/
│       ├── main.tf       # same module calls, staging's variable values
│       ├── backend.tf
│       └── terraform.tfvars
└── .github/workflows/    # or Jenkinsfile -- fmt, validate, plan-on-PR
```

The two environment directories call the *same* modules with different
variable values and a different backend key — that's what makes "dev
and stg differ only by variable values" actually true, rather than
aspirational. Nothing about a module's internals should need to know
which environment is calling it.

## Provisioners — file, connection, and Why They're a Last Resort

- Everything so far declares *desired state* — Terraform figures out the
  API calls.
- A `provisioner` is the one place that breaks that model: it runs an
  imperative action (upload a file, run a script) against a resource
  right after it's created, over SSH or WinRM.
- It needs a `connection` block to say how to actually log in — which
  needs a real key pair to exist first.

### Generating a key pair to a custom path

`ssh-keygen` prompts for a save location; pointing it somewhere other
than the default `~/.ssh/id_rsa` keeps a project-specific key out of
your global SSH config:

``` bash
ssh-keygen -t rsa -b 2048
# Enter file in which to save the key (~/.ssh/id_rsa): ./deployer_key
# Enter passphrase (empty for no passphrase): [leave blank for a provisioner -- see note below]
```

This writes two files: `deployer_key` (the **private** key — never
committed, never shared) and `deployer_key.pub` (the **public** key —
safe to share, this is what AWS actually stores). Terraform reads the
public half into `aws_key_pair`, and the private half into the
`connection` block below to actually authenticate:

``` hcl
resource "aws_key_pair" "deployer" {
  key_name   = "deployer-key"
  public_key = file("./deployer_key.pub")
}
```

!!! danger "A hand-typed key is one truncation away from a real error"

    A public key pasted or retyped as an inline string is easy to
    accidentally clip — a real `apply` once failed with
    `InvalidKey.Format: Key is not in valid OpenSSH public key format`
    because the leading `AAAAB3NzaC1yc2E...` chunk (a fixed, required
    part of every RSA key's encoding) got cut off during a copy-paste.
    Reading the key with `file("./deployer_key.pub")`, as above, removes
    the chance of that entirely — the exact bytes `ssh-keygen` wrote are
    what gets sent, nothing retyped in between.

!!! danger "key_name = \"a-string\" isn't a reference — it's a coincidence"

    - `key_name = "deployer-key"` on the instance and `key_name =
      "deployer-key"` on the `aws_key_pair` happening to match is
      invisible to Terraform's dependency graph — a bare string creates
      no edge between the two resources.
    - A real `apply` creating both at once launched the EC2 instance and
      the key pair *in parallel*, and the instance's `RunInstances` call
      reached AWS before the key pair existed, failing with
      `InvalidKeyPair.NotFound` even though the key pair resource itself
      succeeded moments later in the same apply.
    - The fix is the reference already used above — `key_name =
      aws_key_pair.deployer.key_name` — which both names the actual key
      and forces the correct creation order, the same mechanism used for
      any two resources that need to happen in sequence.

!!! danger "An empty passphrase is the practical choice for a provisioner"

    An SSH key with a passphrase demands it interactively on every
    connection — but the `file` provisioner authenticates
    non-interactively, with no way to type a passphrase in when
    Terraform asks. A passphrase-protected key here just fails auth
    silently, the same "looks like a hang, not an error" symptom as the
    wrong-username case below. For a key that automation (not a human at
    a terminal) is going to use, leave the passphrase blank.

``` hcl
resource "aws_instance" "app" {
  ami           = var.ami_id
  instance_type = "t3.micro"
  key_name      = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.main.id]

  provisioner "file" {
    source      = "./provisioned_file.txt"
    destination = "/home/ec2-user/provisioned_file.txt"
  }

  connection {
    type        = "ssh"
    host        = self.public_ip
    user        = "ec2-user"
    private_key = file("./deployer_key")
    timeout     = "4m"
  }
}
```

!!! danger "Wrong SSH user looks like a hang, not an error"

    A real `apply` using `user = "ubuntu"` against an Amazon Linux 2023
    AMI sat at `Still creating...` for over 4 minutes with no error
    message at all — because Amazon Linux's login user is `ec2-user`,
    not `ubuntu`. Every failed SSH attempt is silently retried until the
    `connection` block's own `timeout` is exhausted, so a wrong username
    doesn't fail fast — it fails slow, looking exactly like a stuck
    instance. Match the user to the AMI family: `ec2-user` for Amazon
    Linux, `ubuntu` for Ubuntu, `admin` for Debian.

!!! danger "The destination path needs to be writable by that user"

    Fixing the username above can surface a second, different failure:
    `scp: /home/provisioned_file.txt: Permission denied`. `/home/`
    itself is owned by `root` — no login user can write directly into
    it, only into their own subdirectory one level down
    (`/home/ec2-user/`). `/tmp` is the simpler default destination when
    the exact home directory isn't worth hardcoding, since it's
    world-writable regardless of which user connects.

### local-exec — runs on your machine, not the resource

Easy to misread at first: `local-exec` runs its command on whatever
machine is running `terraform apply` — never on the resource itself,
and it needs no `connection` block at all, because it never connects to
anything.

``` hcl
resource "aws_instance" "app" {
  # ...
  provisioner "local-exec" {
    command = "touch hello.txt"
  }
}
```

!!! danger "\"touch hello.txt\" doesn't touch the instance"

    A real run of the block above created `hello.txt` sitting in the
    same directory `terraform apply` was run from — not on the EC2
    instance, not anywhere in AWS. `local-exec` is for side effects on
    the machine running Terraform itself: writing an output value to a
    local file, triggering a local notification, kicking off a script
    that talks to some other system entirely. To actually run a command
    *on* the resource, the provisioner needed is `remote-exec`, next.

### remote-exec — runs commands on the resource, over the same connection

Same `connection` block as `file` (SSH, same host/user/key) — but
instead of uploading a file, it runs shell commands directly on the
remote resource:

``` hcl
resource "aws_instance" "app" {
  # ...
  provisioner "remote-exec" {
    inline = [
      "sudo yum install -y httpd",
      "sudo systemctl enable --now httpd"
    ]
  }
  connection {
    type        = "ssh"
    host        = self.public_ip
    user        = "ec2-user"
    private_key = file("./deployer_key")
  }
}
```

!!! note "inline vs script vs scripts"

    `inline` (above) is a list of commands run in order, each over its
    own SSH exec call — fine for two or three lines. `script` uploads
    and runs one local script file; `scripts` does the same for a list
    of them. For anything longer than a handful of commands, a script
    file is easier to read, test locally, and version — the same
    reasoning that already favors a `userdata.sh` file over an inline
    heredoc.

!!! note "Prefer user_data over a provisioner whenever the choice exists"

    - `user_data` runs as part of the instance's own boot process — no
      SSH session, no network round-trip from wherever `apply` happens
      to run, no connection timeout to tune.
    - A provisioner needs Terraform itself to hold an SSH connection
      open during `apply`, which means it can fail for reasons that
      have nothing to do with the resource being wrong — a security
      group change, a flaky network, a key mismatch.
    - HashiCorp's own guidance is to treat provisioners as a last
      resort, for the narrow cases `user_data` genuinely can't cover
      (pulling a file that doesn't exist until another resource in the
      same `apply` finishes, for instance) — not as the default way to
      configure a new instance.

### SSHing in yourself afterward — the same key, a manual connection

Everything above wires a key pair into an instance so *Terraform's own*
provisioner can log in. Logging in yourself afterward, from a terminal,
reuses the exact same key pair — no separate setup:

``` bash
chmod 400 ./deployer_key   # SSH refuses a private key that's readable by anyone else
ssh -i "./deployer_key" ec2-user@<instance-public-dns-or-ip>
```

!!! danger "The ingress CIDR means \"from,\" never \"to\""

    A real security group ended up with its port-22 rule allowing the
    EC2 instance's own public IP — which looked plausible, since that's
    literally the address baked into the instance's own hostname
    (`ec2-203-0-113-10...`). But an ingress `cidr_blocks` always means
    "traffic is allowed to arrive *from* this address" — never "this is
    the address being connected to." The instance's own IP is
    irrelevant to its own ingress rules; what belongs there is the
    **client's** IP — the machine running `ssh`, found with `curl
    ifconfig.me`, not the server being connected to. Getting this
    backwards produces the same silent, response-less hang as any other
    SG mismatch — nothing distinguishes "wrong direction" from "wrong IP
    entirely" at the network level.

!!! danger "A hardcoded personal IP goes stale"

    Locking SSH to "just my IP" via a `/32` CIDR is good practice over
    `0.0.0.0/0`, but most home and mobile ISPs assign dynamic addresses
    — the correct CIDR today can silently stop working after a router
    reboot or a network change, with the exact same symptom as every
    other SG mismatch: `ssh` just hangs, no error to point at the real
    cause. Re-running `curl ifconfig.me` and comparing it against the
    security group's current rule is the fastest way to rule this in or
    out before suspecting the key, the instance, or anything else.

## Templating: templatefile() and .tftpl Files

An IAM policy can be built with `jsonencode({...})` — real HCL values,
mechanically serialized into JSON. `templatefile()` is the other
approach: write the JSON (or a script, or any text) as its own file,
with `${...}` placeholders, and have Terraform render it with real
values substituted in.

``` hcl
# main.tf
resource "aws_iam_user_policy" "instance_manager" {
  name = "InstanceManagePolicy"
  user = aws_iam_user.created_user.name
  policy = templatefile("${path.module}/user-policy.tftpl", {
    ec2_policies = [
      "ec2:RunInstances",
      "ec2:StopInstances",
      "ec2:TerminateInstances",
      "ec2:RequestSpotInstances",
    ]
  })
}
```

``` text
# user-policy.tftpl
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ${jsonencode(ec2_policies)},
            "Resource": "*"
        }
    ]
}
```

`templatefile(path, vars)` takes two arguments: the file to render, and
a map of variables the template can reference. Inside the `.tftpl` file,
`${ec2_policies}` would insert a raw HCL representation of the list —
wrapping it in `jsonencode(...)`, as above, is what turns it into valid
JSON array syntax instead.

### Why reach for a separate file at all

- Nothing here is impossible with `jsonencode()` alone — the difference
  is where the content lives.
- A large JSON policy, a multi-line bootstrap script, or an nginx config
  reads far more naturally as its own properly-formatted file (real
  syntax highlighting, no HCL string-escaping) than as a nested HCL data
  structure.
- `templatefile()` also supports its own mini control-flow syntax inside
  the template file itself — a `for` directive and an `if` directive,
  the template-text equivalents of a `for` expression and a conditional.

### %{ for } — repeating a line once per item

``` hcl
# allowed_ips.tftpl
%{ for ip in allowed_ips ~}
allow ${ip};
%{ endfor ~}
deny all;
```

``` hcl
templatefile("${path.module}/allowed_ips.tftpl", {
  allowed_ips = ["203.0.113.10", "203.0.113.20"]
})
```

``` text
# rendered output
allow 203.0.113.10;
allow 203.0.113.20;
deny all;
```

!!! note "The ~ is a whitespace-strip marker, not part of the loop"

    - Without `~`, every `%{ for ... }` and `%{ endfor }` line still
      emits its own trailing newline into the output — a template
      written across multiple lines would render with extra blank lines
      where the directive lines themselves used to be.
    - `%{ for ip in allowed_ips ~}` strips the newline immediately after
      the directive; `%{ endfor ~}` does the same before it.
    - The result is clean output with no artifacts from the directive
      syntax itself — always worth adding on multi-line `for`/`if`
      directives unless you've checked the output without it and it
      already looks right.

A key-value version works the same way as a two-variable `for`
expression (`each.key`/`each.value`, here as template text instead):

``` hcl
%{ for name, port in services ~}
${name}: ${port}
%{ endfor ~}
```

### %{ if } / %{ else } — conditional content

``` hcl
# userdata.tftpl
#!/bin/bash
yum install -y httpd
%{ if enable_monitoring ~}
yum install -y amazon-cloudwatch-agent
systemctl enable --now amazon-cloudwatch-agent
%{ else ~}
echo "monitoring agent skipped"
%{ endif ~}
systemctl start httpd
```

``` hcl
user_data = templatefile("${path.module}/userdata.tftpl", {
  enable_monitoring = var.enable_monitoring   # a plain bool
})
```

`%{ else }` is optional — a bare `%{ if ... }`/`%{ endif }` with nothing
in between the false branch and `endif` simply renders nothing when the
condition is false, the same as an `if` with no `else` in most
languages.

### Indenting a directive line leaks whitespace into the output

Indenting `%{ if }`/`%{ for }` to match the surrounding code is natural
— but `~` only strips whitespace on the side of the directive it's
placed on. A trailing-only `~}` does nothing about the spaces typed
*before* `%{` on that same line:

``` text
#!/bin/bash
    %{ if enable ~}
    yum install -y agent
    %{ endif ~}
systemctl start httpd
```

``` text
# actual rendered output -- verified directly
#!/bin/bash
        yum install -y agent
    systemctl start httpd
```

!!! danger "The indentation doesn't just appear, it accumulates"

    `yum install -y agent` rendered with **8** leading spaces, not 4 —
    its own indentation plus the 4 unstripped spaces sitting before
    `%{ if enable ~}` on the line above, since only that directive's
    trailing newline was stripped, not its leading whitespace.
    `systemctl start httpd` — which had no indentation in the source at
    all — picked up 4 leading spaces leaked from the `%{ endif ~}` line
    the same way. The whitespace doesn't just leak, it silently shifts
    onto lines that were never indented in the source.

The fix is `~` on *both* sides of a directive-only line — `%{~ if
enable ~}` — which strips the leading whitespace/newline too:

``` text
#!/bin/bash
    %{~ if enable ~}
    yum install -y agent
    %{~ endif ~}
systemctl start httpd
```

``` text
# rendered output -- clean
#!/bin/bash
    yum install -y agent
systemctl start httpd
```

!!! success "Default to both-sided ~ on directive-only lines"

    A line that contains nothing but a `%{ if }`/`%{ for }`/`%{ endif
    }`/`%{ endfor }` directive is never meant to produce output itself —
    it exists purely for control flow. `%{~ ... ~}` on every such line
    is the safe default; reach for one-sided `~` only when a directive
    shares a line with real content you specifically want to keep.

`%{ for }`/`%{ if }` aren't a `templatefile()`-only feature — they're
part of HCL's general template syntax, usable inside *any* string
expression, including a heredoc written directly in a resource block,
with no separate file at all:

``` hcl
user_data = <<-EOF
  #!/bin/bash
  %{ if enable_monitoring ~}
  yum install -y amazon-cloudwatch-agent
  %{ endif ~}
EOF
```

!!! success "templatefile() only changes where the text lives"

    The directive syntax above is identical whether it's inline in a
    heredoc or inside a file read by `templatefile()` — the only thing
    `templatefile()` adds is reading that text from a separate file
    instead of writing it directly in the resource block.

|  | `jsonencode({...})` | `templatefile("...tftpl", {...})` |
|---|---|---|
| Where the content lives | Inline, inside the `.tf` file, as real HCL values | A separate file, with `${...}` placeholders |
| Syntax correctness | Guaranteed valid JSON — it's built mechanically, never hand-typed | Only as correct as whatever's typed in the template file — a missing comma is a real, hand-made mistake |
| Good for | Policies and structures that are naturally HCL-shaped already (lists, maps you're already building) | Long or reused text — multi-line scripts, large policies, anything an editor should syntax-highlight properly |
| Failure mode | A typo is a normal HCL error, caught early and clearly | A typo can be a raw JSON parse error with a byte offset — a plan-time failure, but far less readable |

!!! danger "This is the exact error a missing comma produces"

    A real `plan` against the template above (before its comma was
    added) failed with `"policy" contains an invalid JSON policy:
    invalid character '"' after object key:value pair, at byte offset
    35`. That's what `templatefile()`'s tradeoff looks like in
    practice: the file is plain text as far as Terraform's HCL parser is
    concerned, so a hand-typed JSON mistake surfaces as a raw JSON
    parser complaint, not a clean, typed HCL error the way a mistake
    inside `jsonencode({...})` would.

!!! danger "Neither approach checks that the action names are real"

    Fixing the JSON syntax doesn't mean the policy is correct —
    `"ec2:RequestSpotInstance"` (singular) parsed as perfectly valid
    JSON and passed `templatefile()` without complaint, but AWS itself
    rejected it: the real action is `RequestSpotInstances` (plural).
    Neither `jsonencode()` nor `templatefile()` validates that an IAM
    action actually exists — that check only happens once AWS evaluates
    the policy, at `apply` time, regardless of which method built the
    JSON.

## null_resource — Provisioners With No Real Infrastructure Attached

Every provisioner has to live inside some `resource` block — but
sometimes the action you want (run a script, hit a webhook, invalidate
a cache) doesn't correspond to creating any real cloud resource at all.
`null_resource` is a resource that creates nothing in AWS — it exists
purely to give a provisioner (or a dependency edge) somewhere to
attach.

``` hcl
resource "aws_instance" "app_server" {
  ami           = "ami-08188a5a4dfdbd573"
  instance_type = "t3.micro"
  tags          = { Name = "app-server" }
}

resource "null_resource" "notify_on_change" {
  triggers = {
    instance_id = aws_instance.app_server.id
  }

  provisioner "local-exec" {
    command = "echo Hello World"
  }
}
```

!!! note "Why triggers exists"

    A `null_resource` has no real attributes of its own, so on a normal
    `apply` nothing about it ever looks "changed" — Terraform would
    never know to re-run its provisioner again. `triggers` is the
    workaround: any change to a value inside that map (here,
    `aws_instance.app_server.id`, which changes whenever that instance
    is replaced) marks the `null_resource` itself as needing
    replacement, which re-runs its provisioner. Without a matching entry
    in `triggers`, the provisioner would only ever run once, on the very
    first `apply`, no matter what changed afterward.

### When to reach for it

- Running a script that depends on more than one resource finishing,
  with no single natural resource to attach the provisioner to
- Invalidating a CDN cache (CloudFront) right after a new S3 deployment
- Running a one-off database migration or seed script once the app
  server and database both exist
- Sending a deploy notification (Slack, a webhook) after other resources
  finish applying
- Re-running a local script whenever an unrelated value changes — e.g.
  `triggers = { script_hash = filemd5("deploy.sh") }`, re-running only
  when that specific file's contents change

!!! danger "Still bound by the same caution about provisioners generally"

    `null_resource` doesn't make provisioners any less of a last resort
    — it just removes the "which resource do I attach this to" obstacle.
    Everything above still applies: it needs Terraform to hold a
    connection/process open during `apply`, and it can fail for reasons
    that have nothing to do with real infrastructure being wrong.

!!! success "terraform_data is the newer, provider-free equivalent"

    Terraform 1.4+ ships `terraform_data` as a built-in resource (no
    separate `null` provider required) covering the same role — a
    resource with no real infrastructure, driven by a
    `triggers_replace` argument instead of `triggers`. `null_resource`
    still works and remains extremely common in existing code, but new
    code on a recent Terraform version has one fewer provider to declare
    by reaching for `terraform_data` instead.

## depends_on — Use Cases, Pros and Cons

`depends_on` exists for the case a reference can't express — an IAM
policy attachment finishing before something that needs it starts.
That's the only reason it exists at all: everywhere Terraform *can* see
a dependency (one resource's argument reading another resource's
attribute), it already orders things correctly on its own. `depends_on`
only matters for the remaining cases where the real-world ordering
requirement leaves no trace in any argument.

### Real use cases

- A provisioner or `user_data` script that needs another resource to
  exist first, but only refers to it by a hardcoded name or convention
  — never a real attribute reference (an S3 bucket a startup script
  downloads from, named as a plain string rather than
  `aws_s3_bucket.x.id`)
- IAM permissions that must be attached before a dependent resource
  starts using them
- An AWS-side ordering requirement that isn't visible through any
  argument at all — something that only shows up as a real API error
  when created in the wrong order
- Forcing a `data` source to read *after* a resource is created, when
  the data source's own arguments don't reference that resource
  directly
- Ordering an entire `module` block relative to another resource or
  module — `depends_on` works on modules too, waiting for every
  resource inside the whole module to finish

### A real file with both a correct use and a redundant one

``` hcl
resource "aws_instance" "app" {
  # ...
  vpc_security_group_ids = [aws_security_group.main.id]
  key_name                = aws_key_pair.deployer.key_name

  depends_on = [
    aws_s3_bucket.bucket,        # correct -- nothing above references this bucket at all
    aws_security_group.main,    # redundant -- already inferred from vpc_security_group_ids
    aws_key_pair.deployer,      # redundant -- already inferred from key_name
  ]
}
```

!!! danger "Spot the redundant entries"

    Only `aws_s3_bucket.bucket` belongs in this `depends_on` — nothing
    in the resource block references any attribute of that bucket, so
    Terraform has no other way to know it should exist first.
    `aws_security_group.main` and `aws_key_pair.deployer` are already
    ordered correctly by `vpc_security_group_ids` and `key_name` —
    listing them again in `depends_on` changes nothing about how
    `apply` behaves, it's just dead weight that makes a reader wonder if
    there's a hidden reason for the dependency beyond what's already
    visible in the arguments above it.

### Pros

- Makes a real ordering requirement explicit and visible in code, for
  the cases where no argument reference could express it
- One `depends_on` can list several resources at once for a single
  combined ordering constraint
- Works on `data` sources and whole `module` blocks, not just resources

### Cons

- Operates on the *whole* resource, not a specific attribute — Terraform
  waits for everything about the other resource to finish, even if only
  one small part of it actually matters, which can serialize applies
  more than necessary
- Explains *that* two resources are related, never *why* — a reference
  shows the actual attribute being used; a bare `depends_on` entry needs
  a comment to mean anything to the next reader
- Easy to add "just in case" without confirming it's actually needed —
  as the redundant entries above show, once one is added nothing forces
  anyone to remove it later, even after it stops meaning anything
- Silently masks a design that could be improved — the "reach for it
  last" principle exists because restructuring toward a real reference
  is often possible and stays correct automatically through future
  refactors, where a `depends_on` entry has to be remembered and kept in
  sync by hand
