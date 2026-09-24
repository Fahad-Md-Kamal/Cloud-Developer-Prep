---
title: "VPC Security, Gateways & the Hands-On Build"
---

# VPC Security, Gateways & the Hands-On Build

Continues from [AWS Networking: VPC & Subnet Design](aws-networking-vpc.md)
(VPC basics, CIDR math, subnet types, route tables). This page covers the
Internet Gateway, NAT Gateway, and bastion host; security groups vs. NACLs;
VPC Flow Logs; the step-by-step build of a real VPC by hand; and a full
walkthrough of why every component in that build exists and what breaks
without it.

## Key Network Components

### Internet Gateway (IGW)

- Attached to the VPC. Provides a path between the VPC and the internet —
  instances in public subnets with a public IP communicate through it.
- One IGW per VPC; horizontally scaled, redundant, and managed by AWS — not
  a bottleneck.

### NAT Gateway

- Sits in a public subnet.
- Lets private-subnet instances initiate outbound connections (downloading
  updates, calling external APIs) without being reachable from the internet.

!!! note "Cost"

    $0.045/hour (~$32/month) per NAT Gateway, plus data processing charges. For production, put one in each AZ for fault tolerance. For dev/learning, one is enough — just know it's a single point of failure.

!!! success "Cost-saving tip"

    Consider a NAT Instance (a small EC2 instance configured to do NAT) instead — ~$3/month for a t3.nano vs $32/month. Less reliable, but fine for learning.

### Bastion Host (Jump Box)

- An EC2 instance in a public subnet that you SSH into, then SSH from there
  into private instances — the only instance with a public IP and SSH
  access, a single auditable entry point into your private network.
- **Modern alternative:** AWS Systems Manager Session Manager — no bastion,
  no SSH keys to manage, all sessions logged in CloudTrail.

## Security Groups vs NACLs

Two layers of firewall, working at different levels.

| Aspect | Security Group | NACL |
|---|---|---|
| **Level** | Instance (attached to ENI) | Subnet (all traffic entering/leaving) |
| **State** | Stateful — allowed inbound response is auto-allowed outbound | Stateless — must explicitly allow both directions |
| **Rules** | Allow only (implicit deny for everything else) | Allow and Deny, evaluated in rule-number order |
| **Default** | Deny all inbound, allow all outbound | Allow all inbound and outbound |
| **Evaluation** | All rules together (most permissive wins) | In order (first match wins) |

### Practical security group design

!!! note "ALB (public)"

    ```
    Inbound:  TCP 443 from 0.0.0.0/0     (HTTPS from anywhere)
    Inbound:  TCP 80 from 0.0.0.0/0      (HTTP, redirects to HTTPS)
    Outbound: All traffic to app-sg        (forward to app servers)
    ```

!!! note "App servers"

    ```
    Inbound:  TCP 8080 from alb-sg        (only from the load balancer)
    Outbound: TCP 5432 to db-sg           (connect to database)
    Outbound: TCP 443 to 0.0.0.0/0       (call external APIs via NAT)
    ```

!!! note "Database"

    ```
    Inbound:  TCP 5432 from app-sg        (only from app servers)
    Outbound: None needed                  (database doesn't initiate connections)
    ```

- **Notice the chain:** internet → ALB (443) → app (only from ALB) →
  database (only from app).
- Each layer only talks to its neighbor — the database cannot be reached
  from the internet, there's no path.

## VPC Flow Logs

- Captures metadata about IP traffic flowing through your VPC — source/
  destination IP, port, protocol, action (ACCEPT/REJECT), bytes transferred.
- Doesn't capture packet contents — it's metadata, not a packet capture.
- Sent to CloudWatch Logs or S3.

Essential for:

- Debugging connectivity issues ("why can't my app reach the database?")
- Security auditing ("who tried to access this subnet?")
- Compliance ("prove that no unauthorized traffic reached the database subnet")

## Building the VPC by Hand — Step by Step

Build it in the console first to understand each component, then repeat via
CLI to prove you can script it.

1. Create the VPC with CIDR 10.0.0.0/16
2. Create 6 subnets (public × 2 AZs, private-app × 2 AZs, private-db × 2 AZs)
3. Create and attach an Internet Gateway
4. Create a NAT Gateway in one public subnet (allocate an Elastic IP first)
5. Create route tables — public → 0.0.0.0/0 to IGW, associate with public subnets; private → 0.0.0.0/0 to NAT Gateway, associate with private subnets
6. Create security groups (ALB-sg, app-sg, db-sg) with the rules described above
7. Enable VPC Flow Logs to CloudWatch
8. Verify: launch a test instance in the public subnet, confirm internet access. Launch one in the private subnet, confirm it can reach the internet via NAT but cannot be reached from outside.

## Why Each Component Exists — and What Breaks Without It

Every piece of the build above, with the full justification: what it does,
why it exists, and what fails if you remove it.

<svg aria-label="Diagram of the VPC showing two availability zones, each with public, private-app, and private-DB subnets, the Internet Gateway, the single NAT Gateway in AZ-a, and where the ALB, EC2, and RDS components sit" role="img" style="display:block;margin:0 0 16px;max-width:720px" viewbox="0 0 720 540" width="100%">
<defs>
<marker id="vpc-arrow" markerheight="6" markerwidth="6" orient="auto-start-reverse" refx="8" refy="5" viewbox="0 0 10 10">
<path d="M0,0 L10,5 L0,10 z" fill="#5c5468"></path>
</marker>
</defs>
<text style="font-family:'IBM Plex Sans Condensed',sans-serif;font-size:13px;font-weight:700;fill:#211a2b" text-anchor="middle" x="360" y="20">How the pieces fit together</text>
<rect fill="none" height="24" rx="12" stroke="#5c5468" stroke-width="1.2" width="120" x="300" y="34"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" text-anchor="middle" x="360" y="50">Internet</text>
<line marker-end="url(#vpc-arrow)" stroke="#5c5468" stroke-width="1.5" x1="360" x2="360" y1="58" y2="80"></line>
<rect fill="#eef0fe" height="32" rx="6" stroke="#4f46e5" stroke-width="1.2" width="200" x="260" y="82"></rect>
<text style="font-family:'IBM Plex Sans Condensed',sans-serif;font-size:13px;font-weight:700;fill:#3730a3" text-anchor="middle" x="360" y="103">Internet Gateway</text>
<line marker-end="url(#vpc-arrow)" stroke="#5c5468" stroke-width="1.5" x1="310" x2="195" y1="114" y2="176"></line>
<line marker-end="url(#vpc-arrow)" stroke="#5c5468" stroke-width="1.5" x1="410" x2="525" y1="114" y2="176"></line>
<rect fill="none" height="280" rx="8" stroke="#e0d9d0" stroke-width="1.5" width="680" x="20" y="126"></rect>
<text style="font-family:'IBM Plex Sans Condensed',sans-serif;font-size:13px;font-weight:700;fill:#3730a3" x="34" y="142">VPC 10.0.0.0/16 — fahad-devops-vpc</text>
<text style="font-family:'IBM Plex Sans Condensed',sans-serif;font-size:13px;font-weight:700;fill:#3730a3" text-anchor="middle" x="195" y="164">AZ-a — ap-south-1a</text>
<text style="font-family:'IBM Plex Sans Condensed',sans-serif;font-size:13px;font-weight:700;fill:#3730a3" text-anchor="middle" x="525" y="164">AZ-b — ap-south-1b</text>
<rect fill="#dc4c2f" height="64" opacity=".12" rx="6" stroke="#dc4c2f" stroke-width="1.2" width="290" x="50" y="176"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" x="60" y="190">Public 10.0.1.0/24</text>
<rect fill="#dc4c2f" height="28" opacity=".85" rx="4" width="125" x="60" y="198"></rect>
<text style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;fill:#ffffff;letter-spacing:.01em" text-anchor="middle" x="122" y="216">ALB (alb-sg)</text>
<rect fill="#4f46e5" height="28" opacity=".85" rx="4" width="135" x="195" y="198"></rect>
<text style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;fill:#ffffff;letter-spacing:.01em" text-anchor="middle" x="262" y="216">NAT Gateway</text>
<rect fill="#dc4c2f" height="64" opacity=".12" rx="6" stroke="#dc4c2f" stroke-width="1.2" width="290" x="380" y="176"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" x="390" y="190">Public 10.0.2.0/24</text>
<rect fill="#dc4c2f" height="28" opacity=".85" rx="4" width="125" x="390" y="198"></rect>
<text style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;fill:#ffffff;letter-spacing:.01em" text-anchor="middle" x="452" y="216">ALB (alb-sg)</text>
<line marker-end="url(#vpc-arrow)" stroke="#5c5468" stroke-width="1.5" x1="195" x2="195" y1="240" y2="252"></line>
<line marker-end="url(#vpc-arrow)" stroke="#5c5468" stroke-width="1.5" x1="525" x2="525" y1="240" y2="252"></line>
<rect fill="#4f46e5" height="64" opacity=".12" rx="6" stroke="#4f46e5" stroke-width="1.2" width="290" x="50" y="252"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" x="60" y="266">Private app 10.0.10.0/24</text>
<rect fill="#4f46e5" height="28" opacity=".85" rx="4" width="170" x="130" y="274"></rect>
<text style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;fill:#ffffff;letter-spacing:.01em" text-anchor="middle" x="215" y="292">EC2 (app-sg)</text>
<rect fill="#4f46e5" height="64" opacity=".12" rx="6" stroke="#4f46e5" stroke-width="1.2" width="290" x="380" y="252"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" x="390" y="266">Private app 10.0.11.0/24</text>
<rect fill="#4f46e5" height="28" opacity=".85" rx="4" width="170" x="460" y="274"></rect>
<text style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;fill:#ffffff;letter-spacing:.01em" text-anchor="middle" x="545" y="292">EC2 (app-sg)</text>
<line marker-end="url(#vpc-arrow)" stroke="#5c5468" stroke-width="1.5" x1="195" x2="195" y1="316" y2="328"></line>
<line marker-end="url(#vpc-arrow)" stroke="#5c5468" stroke-width="1.5" x1="525" x2="525" y1="316" y2="328"></line>
<rect fill="#3730a3" height="64" opacity=".15" rx="6" stroke="#3730a3" stroke-width="1.2" width="290" x="50" y="328"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" x="60" y="342">Private DB 10.0.20.0/24</text>
<rect fill="#3730a3" height="28" opacity=".85" rx="4" width="170" x="130" y="350"></rect>
<text style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;fill:#ffffff;letter-spacing:.01em" text-anchor="middle" x="215" y="368">RDS (db-sg)</text>
<rect fill="#3730a3" height="64" opacity=".15" rx="6" stroke="#3730a3" stroke-width="1.2" width="290" x="380" y="328"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" x="390" y="342">Private DB 10.0.21.0/24</text>
<rect fill="#3730a3" height="28" opacity=".85" rx="4" width="170" x="460" y="350"></rect>
<text style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;fill:#ffffff;letter-spacing:.01em" text-anchor="middle" x="545" y="368">RDS (db-sg)</text>
<rect fill="#dc4c2f" height="14" opacity=".85" rx="2" width="14" x="40" y="426"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11.5px;fill:#5c5468" x="62" y="437">Public subnet — internet-facing (ALB, NAT)</text>
<rect fill="#4f46e5" height="14" opacity=".85" rx="2" width="14" x="40" y="450"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11.5px;fill:#5c5468" x="62" y="461">Private app subnet — reachable only from the ALB</text>
<rect fill="#3730a3" height="14" opacity=".85" rx="2" width="14" x="40" y="474"></rect>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11.5px;fill:#5c5468" x="62" y="485">Private DB subnet — reachable only from the app tier</text>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" text-anchor="middle" x="360" y="506">Only one NAT Gateway (in AZ-a) — a deliberate cost trade-off for this learning build.</text>
<text style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;fill:#5c5468" text-anchor="middle" x="360" y="522">Production would place one NAT per AZ for redundancy.</text>
</svg>

### VPC (fahad-devops-vpc — 10.0.0.0/16)

What it does
:   Your private isolated network inside AWS. Nothing can enter or leave unless you explicitly allow it.

Why it exists
:   Without a VPC, all your resources sit on a shared flat network. The VPC is the wall around your house — it defines what's inside your network and what's outside.

Without it
:   You'd have to use the default VPC, which puts everything in public subnets with public IPs. Fine for testing; a security risk for production.

### Public subnets (10.0.1.0/24, 10.0.2.0/24)

What they do
:   Subnets where the route table points `0.0.0.0/0` to the Internet Gateway. Resources here can have public IPs and be reached from the internet.

Why they exist
:   The ALB needs to receive traffic from users on the internet. The NAT Gateway needs internet access to relay traffic for private instances. These are the *only* things that should be internet-facing.

Without them
:   No way for users to reach your application — your ALB would have no internet connectivity.

Why two?
:   One per AZ (ap-south-1a and ap-south-1b). If AZ-a goes down, the ALB in AZ-b keeps serving. This is high availability.

### Application Load Balancer (fahad-alb)

What it does
:   Sits in both public subnets, terminates TLS, and distributes incoming requests across healthy targets in the app subnets.

Why it exists
:   Users need one stable DNS name to hit, not a shifting list of individual EC2 IPs. The ALB also health-checks targets — if the App instance in AZ-a stops responding, the ALB simply stops sending it traffic, no manual intervention needed.

Without it
:   You'd expose EC2 instances directly to the internet (defeating the whole private-subnet design), or hand out individual instance IPs that break every time Auto Scaling replaces one.

Why registered in both public subnets?
:   An ALB is inherently multi-AZ — AWS runs its nodes in every AZ you attach it to. Registering both public subnets gives it the same redundancy as the rest of the architecture, for free.

### Private app subnets (10.0.10.0/24, 10.0.11.0/24)

What they do
:   Subnets with no direct internet route. Traffic goes outbound only through the NAT Gateway.

Why they exist
:   Your application servers don't need to be internet-facing. They receive traffic *only* from the ALB, and reach the internet *only* through NAT. Even if your app has a vulnerability, an attacker can't directly connect from the internet.

Without them
:   You'd put app servers in public subnets with public IPs. Any misconfigured security group would expose them directly to the internet.

### EC2 instances (Auto Scaling group, app-sg)

What they do
:   Run the actual application code, one per AZ at minimum, launched through an [Auto Scaling Group](auto-scaling-groups.md) rather than as standalone instances — see that page for how the group itself spreads instances across AZs and reacts to load.

Why Auto Scaling instead of a fixed instance?
:   If an instance crashes or an AZ has issues, the ASG launches a replacement automatically in a healthy AZ — you don't get paged to manually relaunch a server at 2am.

Why they can only be reached through the ALB
:   `app-sg` only allows inbound traffic from `alb-sg`. Even if you know an instance's private IP, you can't connect to it directly — traffic has to come through the load balancer, which is the only thing the security group trusts.

### Private DB subnets (10.0.20.0/24, 10.0.21.0/24)

What they do
:   The most isolated subnets. No internet route at all (or outbound-only via NAT for updates).

Why they exist
:   Your database is the crown jewel — it holds all your customer data. It should *only* be reachable from the app servers, nothing else. Not from the internet, not from your laptop, not from any other service.

Why separate from app subnets?
:   So you can apply different security groups per tier. DB-sg only allows port 5432 from App-sg. Separate subnets also let you apply different NACL rules per tier.

### RDS (db-sg)

What it does
:   A managed relational database in the private DB subnets, holding the application's persistent data.

Why it exists
:   `db-sg` allows inbound traffic only from `app-sg` on port 5432. The database has no route to the internet in either direction — nothing outside the app tier can reach it, and it can't reach out.

Without it
:   You'd run your own database engine on EC2, taking on patching, backups, and failover yourself — the trade-off inherent to AWS's shared responsibility model (the further up the managed-service stack you go, the less infrastructure toil you own, in exchange for less control).

Why two DB subnets, one per AZ?
:   So RDS Multi-AZ has somewhere to place a synchronous standby in AZ-b. If the primary in AZ-a fails, AWS promotes the standby automatically — an active-passive failover pattern, applied at the database layer.

### Internet Gateway (fahad-igw)

What it does
:   The door between your VPC and the public internet. Bidirectional — traffic flows both in and out.

Why it exists
:   Without it, nothing in your VPC can reach the internet, and no one on the internet can reach anything in your VPC. Your ALB wouldn't work, your users couldn't connect.

Without it
:   A completely isolated VPC. Useful for extremely sensitive air-gapped workloads, but not for a web application.

Key detail
:   One IGW per VPC. Fully managed by AWS — horizontally scaled, redundant, never a bottleneck.

### NAT Gateway (fahad-nat)

What it does
:   Sits in a public subnet, relays outbound traffic for private subnets. One-way — the internet can't initiate connections through it.

Why it exists
:   Your app servers in private subnets need to reach the internet: downloading OS updates, calling external APIs (Stripe, SendGrid), pulling Docker images. NAT lets them do this without being directly reachable.

Without it
:   Your private instances would be completely isolated — they couldn't install packages, call external services, or push metrics to external monitoring.

Why in a public subnet?
:   The NAT needs internet access to relay traffic. It gets this through the IGW via the public route table. Putting it in a private subnet would create a chicken-and-egg problem — NAT needs internet to provide internet.

!!! danger "Cost warning"

    NAT Gateway is ~$32/month — the most expensive component in your VPC. Delete it when not studying. Also delete the Elastic IP after, or it charges too.

### Route tables (fahad-public-rt, fahad-private-rt)

What they do
:   Rules that tell traffic where to go. Every subnet is associated with one route table: "if the destination matches this CIDR, send it there."

Why they exist
:   Without route tables, traffic inside the VPC wouldn't know how to reach the internet or other subnets. Route tables are the GPS of your network.

| Route table | Rule | Meaning |
|---|---|---|
| **fahad-public-rt** | `10.0.0.0/16 → local` | Traffic within the VPC stays internal |
| `0.0.0.0/0 → IGW` | Everything else goes to the internet |
| **fahad-private-rt** | `10.0.0.0/16 → local` | Traffic within the VPC stays internal |
| `0.0.0.0/0 → NAT` | Everything else goes outbound through NAT |

!!! note "Without them"

    Every subnet would use the VPC's main route table (which has only the `local` route). No internet access for anything.

### Security groups (fahad-alb-sg, fahad-app-sg, fahad-db-sg)

What they do
:   Stateful firewalls attached to individual resources. They define *who* can talk to *whom* on *which port*.

The chain
:   Internet → ALB-sg (port 443) → App-sg (port 8080, only from ALB-sg) → DB-sg (port 5432, only from App-sg)

Without them
:   Everything in the VPC could talk to everything else on any port. A compromised ALB could connect directly to the database.

Why reference security groups (not IPs)?
:   If you wrote "allow from 10.0.1.0/24," you'd have to update it every time the ALB's IP changes. By referencing `ALB-sg` as the source, it automatically applies to anything that has ALB-sg attached — regardless of IP.

### VPC Flow Logs

What they do
:   Capture metadata about every network connection — source IP, destination IP, port, protocol, accept/reject, bytes. Sent to CloudWatch Logs.

Why they exist
:   When something doesn't work ("my app can't reach the database"), flow logs tell you whether the traffic was attempted and rejected (security group issue) or never attempted (routing issue).

Without them
:   Debugging network issues blind. "Is traffic being blocked or not reaching?" becomes a guessing game.

### What about NACLs?

!!! note "Deliberately skipped"

    This build kept every subnet's NACL at its AWS default (allow all in, allow all out) and did all the enforcement with security groups instead. Security groups already implement the exact alb → app → db chain from [Security Groups vs NACLs](#security-groups-vs-nacls); stacking a second, stateless firewall on top adds real operational cost (remembering to open *both* directions for every rule) without adding protection this architecture doesn't already have. Custom NACLs earn their place as a second layer at the public subnet boundary in stricter, compliance-driven environments — worth revisiting later, not required for this build.

### How a user request flows through all these components

```
1. User types your-app.com
2. Route 53 resolves to ALB's IP
3. Request hits ALB in public subnet         (ALB-sg allows port 443)
4. ALB forwards to EC2 in private app subnet (App-sg allows from ALB-sg)
5. EC2 queries RDS in private DB subnet      (DB-sg allows from App-sg)
6. Response flows back: RDS → EC2 → ALB → user

If EC2 needs to call Stripe API:
7. EC2 → NAT Gateway → IGW → internet       (outbound only, no inbound)
```

!!! success "The test"

    For each component, ask: "what breaks if I remove this?" If you can answer that for every piece, you understand the VPC. If you can't, re-read that component's section.
