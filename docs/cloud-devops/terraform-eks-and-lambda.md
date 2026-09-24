---
title: "Terraform: EKS, Worked Examples & Lambda"
---

# Terraform: EKS, Worked Examples & Lambda

The Kubernetes and serverless half of the same platform — an EKS
cluster with IRSA, two full worked examples built and verified end to
end against a real AWS account, an AWS Lambda deployment, and
provisioning a Jenkins controller. See
[Terraform: Building a Platform in Code](terraform-building-a-platform.md)
for the ALB/ASG/ACM/RDS/ECS half, and
[Terraform: Iteration, Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md)
for the module-design principles referenced throughout.

## The EKS Cluster, Node Group and IRSA

A second runtime for the same kind of service ECS runs elsewhere — more
moving parts: the control plane, a node group of worker EC2 instances,
and IRSA (IAM Roles for Service Accounts) so pods get scoped AWS
permissions without static credentials baked into a container image.

``` hcl
resource "aws_eks_cluster" "main" {
  name     = "${var.name_prefix}-eks"
  role_arn = aws_iam_role.eks_cluster.arn
  vpc_config { subnet_ids = var.private_subnet_ids }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.name_prefix}-ng"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = var.private_subnet_ids
  scaling_config {
    desired_size = 2
    min_size     = 2
    max_size     = 4
  }
}

# IRSA -- lets the order-service pod assume an IAM role scoped to just its own needs
resource "aws_iam_openid_connect_provider" "eks" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
}

resource "aws_iam_role" "order_service_pod" {
  name = "order-service-irsa"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.eks.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub" =
            "system:serviceaccount:default:order-service"
        }
      }
    }]
  })
}
```

!!! note "Why IRSA over a node-wide IAM role"

    - Without IRSA, every pod on a node inherits the node group's own
      IAM role — the order-service pod and any other pod scheduled on
      that same worker would share identical AWS permissions.
    - IRSA scopes credentials to the individual Kubernetes service
      account instead, matching the least-privilege principle a
      production readiness review explicitly checks for.

### The networking underneath it, built for real

The snippet above assumes `var.private_subnet_ids` already exists — a
real EKS cluster needs a VPC, public and private subnets across at
least two AZs, an Internet Gateway, a NAT Gateway, and route tables
tying it all together, before `aws_eks_cluster` has anywhere to
actually launch into. A separate personal project,
[`IaC/tf-eks/`](https://github.com/Fahad-Md-Kamal/DevOps-Roadmap/tree/main/IaC/tf-eks),
is that networking foundation, applied for real — five small modules
(`vpc`, `igw`, `subnet`, `nat`, `routes`) composed from the root, not
the EKS cluster/node-group/IRSA resources themselves yet.

``` mermaid
flowchart TD
    VPC["VPC<br/>10.0.0.0/16"] --> IGW["Internet Gateway"]
    VPC --> PrivSN1["Private subnet<br/>zone 1"]
    VPC --> PrivSN2["Private subnet<br/>zone 2"]
    VPC --> PubSN1["Public subnet<br/>zone 1"]
    VPC --> PubSN2["Public subnet<br/>zone 2"]

    PubSN1 --> NAT["NAT Gateway<br/>+ Elastic IP"]
    IGW --> PubRT["Public route table<br/>0.0.0.0/0 -> IGW"]
    NAT --> PrivRT["Private route table<br/>0.0.0.0/0 -> NAT"]

    PubSN1 --> PubRT
    PubSN2 --> PubRT
    PrivSN1 --> PrivRT
    PrivSN2 --> PrivRT
```

One NAT Gateway, deliberately, not one per AZ — cheaper, but every
private subnet's internet egress depends on that single NAT Gateway
staying up.

The same `subnet` module builds all four subnets, and the same
`routes` module builds both route tables — a `type =
"public"`/`"private"` variable on each drives everything that actually
differs:

- **Subnet module:** `map_public_ip_on_launch` defaults `false`; only
  the public-zone calls override it to `true`. The
  `kubernetes.io/role/*elb` tag EKS's own Load Balancer Controller
  looks for also depends on `type` — `kubernetes.io/role/elb` for
  public, `kubernetes.io/role/internal-elb` for private — built with a
  module-local computed prefix (`var.type == "public" ? "" :
  "internal-"`) interpolated straight into the tag *key*, not just its
  value.
- **Routes module:** one `aws_route_table` resource, reused for both
  tiers. Its single route sets `nat_gateway_id` and `gateway_id`
  conditionally on `var.type`, with the one that doesn't apply
  resolving to `null` — AWS rejects a route with *both* set, but a
  `null` attribute is simply treated as not provided.

!!! danger "CIDR overlap is invisible to `terraform validate` — it's an AWS-side check, not an HCL one"

    - A subnet was written with `cidr_block = "10.0.0.0/16"` —
      identical to the VPC's own CIDR block, consuming the VPC's entire
      address space for one subnet alone.
    - `terraform validate` passed cleanly, because nothing about that
      is a syntax or type error; HCL has no idea what a CIDR block even
      means, let alone whether one range contains another.
    - This is exactly the kind of mistake that only surfaces from AWS's
      own API, at `plan` or `apply` time (or, if caught late enough, as
      a straight-up conflict error mid-`apply`) — the same lesson as a
      module `validation` block's value, just for a constraint that
      can't be expressed as a simple regex: `/19` blocks used elsewhere
      in the same VPC align on 32-address boundaries in the third octet
      (`.0`, `.32`, `.64`, `.96`, ...), and eyeballing that by hand is
      exactly how the overlap happened in the first place.

!!! success "The same backend-migration lesson, in the exact place it actually happened"

    This is the same `IaC/tf-eks/` project the `-reconfigure`-vs-
    `-migrate-state` danger box in [State, Environments &
    Regions](terraform-state-environments-and-regions.md) is drawn from
    — real applied resources, a backend added after the fact, and the
    live confirmation (`terraform plan` reporting no drift against the
    new S3 backend) that the migration preserved everything Terraform
    already knew about.

## Worked Examples

Two full case studies, distinct in kind from the single-topic
explainers above: a complete config built and verified end to end, then
that same config refactored into modules — a VPC with public and
private subnets, an EC2 pair reachable through *both* an ALB and an
NLB. Every block in both is validated and planned against a real AWS
account.

### Building It: A VPC With Both an ALB and an NLB, Story-Book Style

Built up in the order each piece actually depends on the one before it.
Read it top to bottom the way it's written: why the piece exists, the
code, then what it accomplished and what it unlocks next.

#### Why each piece exists, before any code

Each component below solves exactly one problem the one before it
doesn't — this is the dependency chain, not the network layout (that's
the next diagram).

``` mermaid
flowchart TD
    VPC["VPC<br/>Your own isolated network"] --> Subnet["Subnet<br/>A slice of that network, pinned to one AZ"]
    Subnet --> IGW["Internet Gateway<br/>The door to the internet"]
    IGW --> RT["Route Table + Route<br/>0.0.0.0/0 -> IGW is what actually makes a subnet public"]
    RT --> SG["Security Group<br/>Firewall -- explicitly allows specific traffic in"]
    SG --> AMI["AMI (data source)<br/>The OS image an instance boots from"]
    AMI --> EC2["EC2 Instance<br/>The actual server doing the work"]
    EC2 --> TG["Target Group<br/>A named, health-checked pool of backends"]
    TG --> LB["ALB / NLB<br/>The entry point -- HTTP-aware vs raw TCP passthrough"]
    LB --> Listener["Listener<br/>Opens a port, defines what to do with what arrives"]
```

Each layer only becomes meaningful once the one above it exists — a
security group rule is meaningless without a route letting traffic
reach the subnet at all; a listener is meaningless without a target
group to forward into.

VPC
:   Your own private, isolated network inside AWS. Nothing else exists
    outside of one.

Subnet
:   A slice of the VPC's address space, pinned to one Availability
    Zone. "Public" vs "private" isn't inherent to the subnet — it's
    just which route table it ends up tied to.

Internet Gateway (IGW)
:   The door between the VPC and the internet. Without it, nothing
    inside the VPC can reach, or be reached from, outside AWS at all.

Route Table + Route
:   The actual switch that makes a subnet public: a `0.0.0.0/0 → IGW`
    route plus an association is the entire mechanism. No route table
    entry, no internet, regardless of anything else.

Security Group
:   The firewall. AWS denies all inbound by default — this is what
    explicitly allows specific traffic (port 80, from where) to reach a
    specific resource.

AMI (data source)
:   The OS disk image an EC2 instance boots from. Looked up live
    instead of hardcoded so it never goes stale.

EC2 Instance
:   The actual server doing the work — running Apache, serving `/`,
    `/foo`, `/bar`.

Target Group
:   A named, health-checked pool of backends. A load balancer never
    points at instances directly — it always points at a target group,
    and instances register into it separately.

ALB (Application Load Balancer)
:   Layer 7, understands HTTP (paths, headers). The entry point for web
    traffic.

NLB (Network Load Balancer)
:   Layer 4, raw TCP passthrough, no HTTP awareness, much higher
    throughput, gives static IPs. Used here as a second, independent
    path to the same servers.

Listener
:   Opens an actual port on a load balancer and says what to do with
    what arrives. Without one, the load balancer exists but accepts
    nothing.

#### What it looks like assembled

``` mermaid
flowchart TD
    Users(["Users"])
    Users -->|"https://.../foo<br/>https://.../bar"| ALB
    Users -->|"tcp://nlb-url"| NLB

    subgraph VPC["VPC 11.0.0.0/16 — fmk_vpc"]
        IGW["Internet Gateway<br/>fmk_igw"]
        ALB["ALB<br/>fmk_alb : 80"]
        NLB["NLB<br/>fmk_nlb : 80"]
        TGpub["Target Group<br/>fmk-tg-public (HTTP)"]
        TGpriv["Target Group<br/>fmk-tg-private (TCP)"]

        subgraph AZa["Availability Zone — ap-south-1a"]
            PubA["Public Subnet 11.0.1.0/24<br/>fmk-public-1a"]
            EC2A["EC2<br/>ec2-A"]
            PrivA["Private Subnet 11.0.3.0/24<br/>fmk-private-1a — empty"]
            PubA --- EC2A
        end

        subgraph AZb["Availability Zone — ap-south-1b"]
            PubB["Public Subnet 11.0.2.0/24<br/>fmk-public-1b"]
            EC2B["EC2<br/>ec2-B"]
            PrivB["Private Subnet 11.0.4.0/24<br/>fmk-private-1b — empty"]
            PubB --- EC2B
        end

        ALB --> TGpub
        NLB --> TGpriv
        TGpub --> EC2A
        TGpub --> EC2B
        TGpriv --> EC2A
        TGpriv --> EC2B
        PubA -. "route 0.0.0.0/0" .-> IGW
        PubB -. "route 0.0.0.0/0" .-> IGW
    end

    classDef empty fill:transparent,stroke-dasharray: 4 3,color:#888;
    class PrivA,PrivB empty;
```

Both AZs carry a public/private pair (AZ pinning from step 3); only the
public side is populated so far — the private subnets (dashed) stay
empty until a database moves in.

#### 1. Provider — connect Terraform to the account

- **Why:** every resource below needs to know which AWS account and
  region to talk to. Nothing else in the file works without this.

``` hcl
provider "aws" {
  region  = "ap-south-1"
  profile = "fahad"
}
```

- **What it did:** pointed Terraform at the `fahad` AWS CLI profile, in
  `ap-south-1`.
- **Next:** before anything can be created, it needs somewhere to live
  — a VPC.

#### 2. VPC — the network boundary everything else lives inside

- **Why:** every subnet, load balancer, and instance below has to be
  created inside some VPC. `11.0.0.0/16` gives ~65,000 usable private
  addresses to divide up.

``` hcl
resource "aws_vpc" "fmk_vpc" {
  cidr_block = "11.0.0.0/16"
}
```

- **What it did:** reserved the address range. It's still empty — no
  subnets, no routing, nothing launchable yet.
- **Next:** a VPC this size is too undifferentiated to launch into
  directly — it needs dividing into subnets.

#### 3. Subnets — dividing the VPC into public and private zones, across two AZs

- **Why:** "public" and "private" aren't a property of the VPC as a
  whole — they're a property of which route table a subnet ends up
  associated with (steps 5/6 decide that). These four blocks carve out
  four non-overlapping ranges, one pair per Availability Zone: a public
  and a private subnet in `ap-south-1a`, a public and a private subnet
  in `ap-south-1b`.
- Pinning `availability_zone` explicitly (rather than letting AWS
  auto-assign one) is what guarantees a public/private pair actually
  shares an AZ — the pairing this diagram's two-AZ layout depends on,
  and the shape a database subnet group will need once the private
  subnets are actually used.

``` hcl
resource "aws_subnet" "fmk_public_1a" {
  vpc_id            = aws_vpc.fmk_vpc.id
  cidr_block        = "11.0.1.0/24"
  availability_zone = "ap-south-1a"
  tags = { Name = "fmk-public-1a" }
}

resource "aws_subnet" "fmk_public_1b" {
  vpc_id            = aws_vpc.fmk_vpc.id
  cidr_block        = "11.0.2.0/24"
  availability_zone = "ap-south-1b"
  tags = { Name = "fmk-public-1b" }
}

resource "aws_subnet" "fmk_private_1a" {
  vpc_id            = aws_vpc.fmk_vpc.id
  cidr_block        = "11.0.3.0/24"
  availability_zone = "ap-south-1a"
  tags = { Name = "fmk-private-1a" }
}

resource "aws_subnet" "fmk_private_1b" {
  vpc_id            = aws_vpc.fmk_vpc.id
  cidr_block        = "11.0.4.0/24"
  availability_zone = "ap-south-1b"
  tags = { Name = "fmk-private-1b" }
}
```

- **What it did:** sliced `11.0.0.0/16` into four `/24`s, each pinned
  to a specific AZ — two tagged "public" and two "private," but the AZ
  pinning is a real constraint, not just a label.
- **Next:** a subnet needs a door to the internet before anything
  inside it is reachable from outside AWS.

!!! note "The private subnets stay empty, on purpose"

    This build only ever launches EC2 instances into the two public
    subnets — `fmk-private-1a`/`fmk-private-1b` exist with their own
    route table (step 6) but hold nothing yet. That's deliberate:
    they're reserved for whatever shouldn't be directly
    internet-reachable, most likely an RDS instance revisiting the
    database patterns covered in [State, Environments &
    Regions](terraform-state-environments-and-regions.md) and
    [Building a Platform](terraform-building-a-platform.md). An empty
    subnet costs nothing to leave declared.

#### 4. Internet Gateway — the VPC's door to the internet

- **Why:** a VPC is fully isolated by default. An Internet Gateway
  makes reaching the internet possible, but only for whichever subnets
  are explicitly routed through it (step 5).

``` hcl
resource "aws_internet_gateway" "fmk_igw" {
  vpc_id = aws_vpc.fmk_vpc.id
  tags   = { Name = "fmk-igw" }
}
```

- **What it did:** created the gateway and attached it to `fmk_vpc` —
  the `vpc_id` argument itself does the attaching, no separate resource
  needed.
- **Next:** attachment alone routes no traffic. Each subnet still needs
  its own route table pointing at it.

#### 5. Public routing — route table, its route to the IGW, and its subnets

- **Why:** this is the piece that actually makes "public" mean
  something. Every route table gets an in-VPC "local" route for free;
  adding a `0.0.0.0/0` → Internet Gateway rule, then associating a
  subnet with this table, is the entire mechanism that makes that
  subnet public. Nothing else about the subnet changes.

``` hcl
resource "aws_route_table" "fmk_public_rt" {
  vpc_id = aws_vpc.fmk_vpc.id
  tags   = { Name = "fmk-public-rt" }
}

resource "aws_route" "fmk_public_default" {
  route_table_id         = aws_route_table.fmk_public_rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id              = aws_internet_gateway.fmk_igw.id
}

resource "aws_route_table_association" "fmk_public_1a" {
  subnet_id      = aws_subnet.fmk_public_1a.id
  route_table_id = aws_route_table.fmk_public_rt.id
}

resource "aws_route_table_association" "fmk_public_1b" {
  subnet_id      = aws_subnet.fmk_public_1b.id
  route_table_id = aws_route_table.fmk_public_rt.id
}
```

- **What it did:** gave the table one rule (everything not bound for
  inside the VPC goes to the IGW), then associated both public subnets
  with it — they're now genuinely public.
- **Next:** the private subnets need routing too, just without that
  `0.0.0.0/0` rule.

#### 6. Private routing — a route table with no path to the internet

- **Why:** every subnet needs an explicit association, or it silently
  falls back to the VPC's implicit main route table. Giving the private
  subnets their own table with no internet route makes "these are
  private" a visible, deliberate fact in the code, not an accident of
  what wasn't configured.

``` hcl
resource "aws_route_table" "fmk_private_rt" {
  vpc_id = aws_vpc.fmk_vpc.id
  tags   = { Name = "fmk-private-rt" }
}

resource "aws_route_table_association" "fmk_private_1a" {
  subnet_id      = aws_subnet.fmk_private_1a.id
  route_table_id = aws_route_table.fmk_private_rt.id
}

resource "aws_route_table_association" "fmk_private_1b" {
  subnet_id      = aws_subnet.fmk_private_1b.id
  route_table_id = aws_route_table.fmk_private_rt.id
}
```

- **What it did:** associated both private subnets with a table that
  has no internet route — they keep the automatic in-VPC "local" route,
  so they can still reach the rest of the VPC, just never the internet
  directly.
- **Next:** the network layout is done. Now security — what's actually
  allowed to reach what, regardless of how traffic is routed.

#### 7. Security group — the firewall in front of the EC2 instances

- **Why:** routing decides whether traffic *can* reach a subnet. A
  security group decides whether it's actually *allowed* to reach a
  specific resource, port by port. AWS denies all inbound by default —
  without this, the instances below would be unreachable even sitting
  in a public, internet-routed subnet.

``` hcl
resource "aws_security_group" "fmk_tls_sg" {
  name        = "fmk_tls_sg"
  description = "Allow TLS inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.fmk_vpc.id
}

resource "aws_vpc_security_group_ingress_rule" "allow_tls_ipv4" {
  security_group_id = aws_security_group.fmk_tls_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  ip_protocol       = "tcp"
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.fmk_tls_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}
```

- **What it did:** one group, two rules — inbound TCP 80 from anywhere
  (matching what Apache actually serves), and all outbound. This same
  group gets reused for the ALB, the NLB's targets, and the instances
  themselves — no separate front-door group here.
- **Next:** the actual compute, and the AMI it boots from.

#### 8. AMI lookup — which OS image the instances boot from

- **Why:** an instance needs an AMI to boot from. Querying for
  "whichever Amazon Linux 2023 AMI is newest right now" instead of
  hardcoding an ID avoids that ID going stale the moment AWS ships a
  patched version.

``` hcl
data "aws_ami" "amzn_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}
```

- **What it did:** nothing created — `data` blocks only read (see
  [Terraform Fundamentals](terraform-fundamentals.md)). This resolves
  to today's latest Amazon Linux 2023 AMI ID for `ap-south-1` at
  plan/apply time.
- **Next:** the EC2 instances themselves.

#### 9. EC2 instances — the actual servers

- **Why:** the real compute — two servers that will sit behind both
  load balancers. Each launches into a different public subnet so the
  pair survives a single AZ failure.

``` hcl
resource "aws_instance" "ec2-A" {
  ami                    = data.aws_ami.amzn_linux.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.fmk_public_1a.id
  user_data              = file("${path.module}/userdata.sh")
  vpc_security_group_ids = [aws_security_group.fmk_tls_sg.id]
  tags                   = { Name = "fmk-ec2-A" }
}

resource "aws_instance" "ec2-B" {
  ami                    = data.aws_ami.amzn_linux.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.fmk_public_1b.id
  user_data              = file("${path.module}/userdata.sh")
  vpc_security_group_ids = [aws_security_group.fmk_tls_sg.id]
  tags                   = { Name = "fmk-ec2-B" }
}
```

- **What it did:** launched both instances, each bootstrapped by
  `userdata.sh` (installs Apache, writes `/`, `/foo`, and `/bar` pages
  showing that instance's own hostname and IP), each attached to
  `fmk_tls_sg` so port 80 can actually reach them.
- **Next:** the servers are individually reachable if you knew their
  IPs — but nothing distributes traffic across the two yet. That's the
  ALB's job first.

!!! danger "user_data has to match the AMI family, not just the SSH user"

    - The wrong-SSH-user version of this mistake (`ubuntu` vs
      `ec2-user`, covered in [Modules & Advanced
      HCL](terraform-modules-and-advanced-hcl.md)) has a matching bug
      in the *script itself*, not just the login.
    - A real `user_data` script written with `apt-get update` /
      `apt-get install -y apache2` against this exact `al2023-...` AMI
      failed completely: Amazon Linux has no `apt-get` at all (it uses
      `dnf`/`yum`), so the very first line errors with `command not
      found` and nothing after it ever runs.
    - Even fixed to the right package manager, the package name is also
      OS-specific — Amazon Linux's Apache is called `httpd`, never
      `apache2` (that's Debian/Ubuntu's name for the same thing).
    - Matching `userdata.sh`'s commands to the actual AMI family is
      exactly as necessary as matching the SSH username to it.

!!! success "Check /var/log/cloud-init-output.log before rewriting blind"

    A failed `user_data` script gives no error anywhere in `terraform
    apply` — the instance still reaches `running` either way, since AWS
    considers the instance successfully launched regardless of what its
    boot script did. The only place the actual failure (`apt-get:
    command not found`, in this case) shows up is
    `/var/log/cloud-init-output.log` on the instance itself, over SSH —
    worth checking directly rather than guessing at what a silent
    script failure was.

#### 10. ALB path — target group, then the ALB, then its listener

- **Why a target group first:** an ALB never points at instances
  directly — a target group is the indirection layer in between, a
  named, health-checked pool the ALB forwards to. Declaring the group
  and its membership separately from the ALB means instances can be
  added or removed without touching the ALB at all.

``` hcl
resource "aws_lb_target_group" "fmk-tg-public" {
  name        = "fmk-tg-public-1a"
  target_type = "instance"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.fmk_vpc.id
}

resource "aws_lb_target_group_attachment" "ec2_a" {
  target_group_arn = aws_lb_target_group.fmk-tg-public.arn
  target_id         = aws_instance.ec2-A.id
  port              = 80
}

resource "aws_lb_target_group_attachment" "ec2_b" {
  target_group_arn = aws_lb_target_group.fmk-tg-public.arn
  target_id         = aws_instance.ec2-B.id
  port              = 80
}
```

- **Why the ALB:** the actual internet-facing entry point — what a
  browser connects to. It needs the public subnets (to be
  internet-reachable) and the security group governing what can reach
  it.

``` hcl
resource "aws_alb" "fmk_alb" {
  name               = "fmk-alb-tf"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.fmk_tls_sg.id]
  subnets            = [aws_subnet.fmk_public_1a.id, aws_subnet.fmk_public_1b.id]
}
```

- **Why the listener:** this is what actually opens a port on the ALB
  and defines what to do with what arrives on it — without one, the ALB
  accepts nothing and every connection times out.

``` hcl
resource "aws_lb_listener" "fmk_alb_http" {
  load_balancer_arn = aws_alb.fmk_alb.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.fmk-tg-public.arn
  }
}
```

- **What it did:** opened port 80 on the ALB, forwarding everything
  into `fmk-tg-public`. The ALB path is complete: internet → ALB:80 →
  `fmk-tg-public` → `ec2-A`/`ec2-B`. No separate listener rules for
  `/foo`/`/bar` are needed — both instances already serve those paths
  themselves (`userdata.sh`), so one forward action reaches either path
  on whichever instance the ALB picks.
- **Next:** the second path — the same instances, reached through an
  NLB instead.

#### 11. NLB path — a second target group, the NLB, and its listener

- **Why a second target group:** an ALB target group and an NLB target
  group aren't interchangeable — this one is TCP, matching what an NLB
  actually forwards (raw connections, no HTTP awareness at all). The
  same two instances register here too — one pool of servers, reachable
  through two independent paths, not two separate pools.

``` hcl
resource "aws_lb_target_group" "fmk-tg-private" {
  name     = "fmk-tg-private-1a"
  port     = 80
  protocol = "TCP"
  vpc_id   = aws_vpc.fmk_vpc.id
}

resource "aws_lb_target_group_attachment" "ec2_a_nlb" {
  target_group_arn = aws_lb_target_group.fmk-tg-private.arn
  target_id         = aws_instance.ec2-A.id
  port              = 80
}

resource "aws_lb_target_group_attachment" "ec2_b_nlb" {
  target_group_arn = aws_lb_target_group.fmk-tg-private.arn
  target_id         = aws_instance.ec2-B.id
  port              = 80
}
```

- **Why the NLB:** the same role as the ALB — the entry point — but
  Layer 4 instead of Layer 7. Notice there's no `security_groups`
  argument: an NLB has no security group of its own, being pure
  passthrough. Access control for this path lives entirely on the
  target's own SG (`fmk_tls_sg`, step 7), which is why that rule had to
  allow `0.0.0.0/0` rather than being scoped to one specific load
  balancer.

``` hcl
resource "aws_lb" "fmk_nlb" {
  name               = "fmk-nlb-tf"
  internal           = false
  load_balancer_type = "network"
  subnets            = [aws_subnet.fmk_public_1a.id, aws_subnet.fmk_public_1b.id]
}

resource "aws_lb_listener" "fmk_nlb_tcp" {
  load_balancer_arn = aws_lb.fmk_nlb.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.fmk-tg-private.arn
  }
}
```

- **What it did:** opened port 80 on the NLB, forwarding every raw TCP
  connection into `fmk-tg-private`. Both paths are now complete:
  internet → ALB:80 → `fmk-tg-public` → the instances, and internet →
  NLB:80 → `fmk-tg-private` → the same instances.

!!! success "Verified, not just written"

    This exact config — 28 resources — ran clean through `terraform
    validate` and `terraform plan` against a real AWS account with zero
    errors. Building it surfaced real mistakes worth recognizing on
    sight: a `security_groups` argument pointed at rule resources
    instead of the group itself, a missing `subnets` argument on an
    ALB, an underscore in a load-balancer name (AWS only allows
    hyphens), a security group rule scoped to 443/VPC-only when the app
    actually serves 80 to the internet, a `target_type` of `"alb"` left
    over on a target group meant to hold EC2 instances, and two EC2
    instances launched with no security group attached at all — each
    one invisible until either `validate` caught it structurally, or
    reasoning through what the diagram actually required caught it
    semantically.

### The Same 28 Resources, Refactored Into Modules

The single `main.tf` above pulled apart into four modules — `network`,
`security`, `compute`, `loadbalancing` — following exactly the
module-design principles from
[Modules & Advanced HCL](terraform-modules-and-advanced-hcl.md). Worth
being honest about the trade-off up front: the "rule of three" says
don't extract a module until something's genuinely reused a third time,
and this only has one caller. Doing it anyway here is a deliberate
learning exercise — practicing the shape of a real module before
there's a second environment forcing the issue — not a case where the
rule stopped applying.

``` text
day02-modules/
├── versions.tf      -- Terraform + provider version constraints
├── variables.tf     -- root inputs: region, profile, vpc_cidr, name_prefix
├── main.tf          -- four `module` calls, wiring outputs into inputs. No resource blocks.
├── outputs.tf       -- vpc_id, alb_dns_name, nlb_dns_name
└── modules/
    ├── network/        (VPC, 4 subnets, IGW, both route tables)
    ├── security/        (the shared security group + its two rules)
    ├── compute/         (AMI lookup, EC2 instances, userdata.sh)
    └── loadbalancing/   (both target groups, ALB, NLB, both listeners)
        each containing: versions.tf, variables.tf, main.tf, outputs.tf
```

#### What each file type holds, and why it's separate

`versions.tf`
:   Terraform and provider version constraints (see [Terraform
    Fundamentals](terraform-fundamentals.md)) — nothing here creates
    anything, it's checked once at `init`. Every module carries its own
    copy: a module should be explicit about what it needs regardless of
    what the root happens to declare, so it stays correct if it's ever
    pulled into a different project.

`variables.tf`
:   The module's inputs — its public interface. Reading this file
    alone should tell you everything needed to call the module, without
    opening `main.tf` at all. `modules/security/variables.tf`, for
    example, says "give me a `vpc_id`; I'll assume port 80 unless you
    override `ingress_port`."

`main.tf`
:   The actual `resource`/`data` blocks — the implementation. A caller
    never needs to read this; it's free to change internally as long as
    `variables.tf` and `outputs.tf` stay the same contract.

`outputs.tf`
:   The module's return values — whatever the next module in the chain
    needs back. `modules/network/outputs.tf` hands back `vpc_id` and
    both subnet maps because `security`, `compute`, and
    `loadbalancing` all need those downstream.

!!! note "Root main.tf contains zero resource blocks"

    Once split, the root `main.tf` is just four `module` calls passing
    outputs forward — `module.network.vpc_id` into `security`, both of
    those into `compute`, all three into `loadbalancing`. Every actual
    `resource` lives one level down, inside a module. This is what "the
    root just wires things together" looks like in a real file, not
    just as a description.

#### One resource, before and after

Splitting into modules was also a chance to apply the `for_each`
guidance retroactively. Four separately-named subnet resources became
one `for_each` block over a map:

``` hcl
## Before -- four separate resources
resource "aws_subnet" "fmk_public_1a" { cidr_block = "11.0.1.0/24" ... }
resource "aws_subnet" "fmk_public_1b" { cidr_block = "11.0.2.0/24" ... }
# state addresses: aws_subnet.fmk_public_1a, aws_subnet.fmk_public_1b

## After (day02-modules) -- one resource, driven by the caller's map
resource "aws_subnet" "public" {
  for_each          = var.public_subnets
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.availability_zone
}
# state addresses: module.network.aws_subnet.public["1a"], ["1b"]
```

Same two subnets get created either way — `terraform plan` on the
modularized version still shows **28 to add, 0 to change, 0 to
destroy**, identical to the original. What changed is that adding a
third AZ later means adding one entry to the `public_subnets` map
passed into the module, not writing a fifth resource block by hand.

## AWS Lambda: IAM, Packaging & the S3 Deployment Pattern

A Lambda function needs three things before it can run at all: an IAM
role it assumes, permission to actually write logs, and its code
packaged into a deployment artifact. None of these are optional — skip
the role and the function has no identity to run as; skip the logging
permission and it runs but you can never see why it failed.

``` hcl
# 1. The role Lambda itself assumes when invoking the function
resource "aws_iam_role" "lambda_role" {
  name = "tf-aws-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# 2. What that role is actually allowed to do -- here, just write logs
resource "aws_iam_policy" "iam_policy_for_lambda" {
  name = "aws_iam_policy_for_tf_aws_lambda_role"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:*:*:*"
      Effect   = "Allow"
    }]
  })
}

# 3. Attach the policy to the role -- two separate resources, same pattern as
#    every other IAM role+policy pairing ("declare the parent, then the membership")
resource "aws_iam_role_policy_attachment" "attach_iam_policy_to_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_lambda.arn
}

# 4. Zip the function code -- a data source, not a resource: it reads
#    local files and produces an archive, it doesn't create anything in AWS
data "archive_file" "zip_the_lambda_code" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda/lambda-func.zip"
}

# 5. The function itself, uploaded directly
resource "aws_lambda_function" "tf_lambda_func" {
  filename      = data.archive_file.zip_the_lambda_code.output_path
  function_name = "fmk-tf-lambda-function"
  role          = aws_iam_role.lambda_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.10"
  depends_on    = [aws_iam_role_policy_attachment.attach_iam_policy_to_role]
}
```

!!! note "jsonencode() over a raw heredoc"

    Both work, but `jsonencode({...})` builds the JSON from real HCL
    values — Terraform catches a typo'd key or a missing comma at
    `plan` time, the same way a module `validation` block catches
    mistakes before `apply` does. A policy document written as a
    `<<EOF` heredoc string is just text as far as Terraform's
    concerned — a malformed JSON heredoc doesn't fail until AWS itself
    rejects the policy.

!!! success "depends_on earns its place here"

    Nothing about `aws_lambda_function` references the policy
    attachment directly, so Terraform can't infer the ordering from a
    value reference the way it does for `role =
    aws_iam_role.lambda_role.arn`. Without the explicit `depends_on`,
    the function could attempt to create before the role actually has
    its logging permission attached, and either fail outright or
    succeed with a role that briefly can't write logs.

### Large functions: deploying from S3 instead of a direct upload

`filename` above uploads the zip directly as part of the
`CreateFunction`/`UpdateFunctionCode` API call. That has a hard
ceiling: AWS caps a **direct** deployment package at 50 MB zipped. Past
that, or as a matter of course in most real pipelines regardless of
size, the function's code is uploaded to S3 first, and the Lambda
resource just points at where it landed:

``` hcl
resource "aws_s3_object" "lambda_package" {
  bucket = "fmk-lambda-deployments"
  key    = "tf-aws-lambda/lambda-func.zip"
  source = data.archive_file.zip_the_lambda_code.output_path
  etag   = data.archive_file.zip_the_lambda_code.output_md5
}

resource "aws_lambda_function" "tf_lambda_func" {
  s3_bucket     = aws_s3_object.lambda_package.bucket
  s3_key        = aws_s3_object.lambda_package.key
  function_name = "fmk-tf-lambda-function"
  role          = aws_iam_role.lambda_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.10"
  depends_on    = [aws_iam_role_policy_attachment.attach_iam_policy_to_role]
}
```

!!! success "Why real pipelines use this even under 50 MB"

    - Beyond the size ceiling, S3-based deployment means the artifact
      exists as a named, addressable object — a CI pipeline can build
      the zip once, upload it, and reference the exact same S3 object
      from multiple environments (dev/stg/prod) without re-zipping or
      re-uploading.
    - `etag = data.archive_file...output_md5` is what makes Terraform
      notice the code actually changed: without it, updating the local
      zip wouldn't trigger a new `aws_s3_object` upload at all, and the
      function would silently keep running the old code.

!!! danger "250 MB unzipped is still a hard ceiling either way"

    S3-based deployment raises the limit, it doesn't remove it — AWS
    caps the *unzipped* deployment package (code plus every dependency)
    at 250 MB regardless of upload method. A function approaching that
    size is usually a sign it's bundling more than it needs (the same
    over-abstraction warning from [Modules & Advanced
    HCL](terraform-modules-and-advanced-hcl.md), applied to a
    dependency tree instead of a module) — worth checking whether a
    Lambda Layer, or splitting into more than one function, fits better
    than pushing the ceiling.

## Provisioning a Jenkins Controller

A Jenkins controller is itself just a resource — an EC2 instance, a
security group, and a `user_data` script that installs and starts it,
the same shape as every other compute resource covered so far.

``` bash
#!/bin/bash
dnf update -y
dnf install -y java-17-amazon-corretto
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2023.key
dnf install -y jenkins
systemctl enable --now jenkins
```

!!! note "dnf, not apt-get — the same lesson as the worked example above"

    This script assumes an Amazon Linux AMI, matching the exact
    AMI-family reasoning already covered for `user_data` scripts in
    general: the package manager and package names have to match the
    actual OS the instance boots from, not whatever was copied from a
    different example.

``` hcl
resource "aws_ebs_volume" "jenkins_home" {
  availability_zone = aws_instance.jenkins_controller.availability_zone
  size              = 50
  tags              = { Name = "jenkins-home" }
}

resource "aws_volume_attachment" "jenkins_home" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.jenkins_home.id
  instance_id = aws_instance.jenkins_controller.id
}
```

!!! danger "JENKINS_HOME does not belong on the root volume"

    - Every job config, build history, and credential Jenkins holds
      lives under `JENKINS_HOME` (`/var/lib/jenkins` by default).
    - Mounting it on a separate EBS volume, not the instance's root
      volume, means replacing the controller instance itself — a new
      AMI, a resize, a region move — doesn't threaten that data at all:
      detach the volume, attach it to the new instance, done.
    - Same principle as `prevent_destroy` on a critical resource (see
      [Operating Terraform in
      Production](terraform-operating-in-production.md)) — the data
      that actually matters shouldn't share a lifecycle with the
      compute that happens to be running it this week.
