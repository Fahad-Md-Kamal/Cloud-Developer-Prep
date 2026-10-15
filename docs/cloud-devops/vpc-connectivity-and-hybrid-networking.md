---
title: "VPC Connectivity: Endpoints, Peering & Hybrid Networking"
---

# VPC Connectivity: Endpoints, Peering & Hybrid Networking

[VPC & Subnet Design](aws-networking-vpc.md) and
[Security Groups, Gateways & Flow Logs](vpc-security-groups-and-flow-logs.md)
cover a single VPC reaching the internet through an Internet Gateway and
a NAT Gateway. This page covers everything else a VPC can connect
to — other VPCs, AWS services without touching the internet at all, and
an actual on-premises network.

## VPC Endpoints: Reaching AWS Services Without the Internet

Normally, an EC2 instance calling the S3 API routes that traffic out
through the Internet Gateway (or NAT Gateway from a private subnet) —
even though the request never leaves AWS's own network. A VPC endpoint
skips that path entirely.

|  | Gateway Endpoint | Interface Endpoint |
|---|---|---|
| Supports | S3 and DynamoDB only | Most other AWS services (SQS, SNS, KMS, Secrets Manager, …) and third-party services via PrivateLink |
| How it works | A route table entry pointing at the service | An ENI with a private IP inside your subnet |
| Cost | Free | Hourly charge + per-GB data processing charge |
| DNS | No change needed | Private DNS can transparently redirect the normal service hostname to the endpoint |

!!! success "The exam signal"

    "Private subnet needs to reach S3 without a NAT Gateway, for cost or
    security reasons" → Gateway Endpoint, free and removes the NAT
    Gateway's per-GB data processing charge for that traffic entirely.
    Anything else (Secrets Manager, SQS, a third-party SaaS API) →
    Interface Endpoint.

### PrivateLink: The Mechanism Behind Interface Endpoints

PrivateLink is the underlying technology an Interface Endpoint uses, and
it's also how a **service provider** exposes their own service to
**other people's VPCs** privately:

- A provider puts their service behind a Network Load Balancer and
  creates a **VPC Endpoint Service**.
- A consumer creates an Interface Endpoint pointing at that service —
  traffic never leaves AWS's backbone, and the consumer's VPC CIDR never
  needs to be shared with (or avoid overlapping with) the provider's.
- This is how AWS's own managed services (and SaaS vendors selling
  "private connectivity" as a feature) expose themselves without a VPC
  peering connection.

## VPC Peering

A direct, private network connection between two VPCs, routed as if they
were on the same network.

- **Not transitive** — if VPC A peers with B, and B peers with C, A
  still cannot reach C. Every pair that needs to talk requires its own
  peering connection — this is the single most tested fact about
  peering, and the reason Transit Gateway exists.
- CIDR blocks must not overlap between peered VPCs.
- Works across accounts and across regions.

!!! danger "N VPCs, all talking to each other = N×(N-1)/2 peering connections"

    Five VPCs that all need to reach each other require 10 separate
    peering connections, each one managed individually. This is exactly
    the operational-overhead problem Transit Gateway solves.

## Transit Gateway

A central hub that every VPC (and on-premises connection) attaches to
once, instead of a mesh of individual peering connections.

- Turns the N×(N-1)/2 peering problem into N simple attachments to one
  hub.
- Transitive by design — a VPC attached to the Transit Gateway can reach
  every other attached VPC (and attached VPN/Direct Connect connections)
  through it, subject to its route tables.
- Can span multiple AWS accounts and span regions (inter-region peering
  between two Transit Gateways).

!!! success "The exam signal"

    "Connect dozens of VPCs (and an on-premises network) to each other
    with minimal operational overhead" → Transit Gateway. "Connect
    exactly two VPCs" → plain VPC Peering is simpler and has no hourly
    hub charge.

## Connecting to an Actual On-Premises Network

|  | Site-to-Site VPN | Direct Connect |
|---|---|---|
| Connection type | Encrypted tunnel over the public internet | A dedicated, private physical network link |
| Setup time | Minutes | Weeks (physical cross-connect at a Direct Connect location) |
| Bandwidth | Limited by internet connection, variable | Consistent, up to 100 Gbps |
| Cost | Low, pay for the VPN connection + data | Higher — a physical circuit plus port-hours |
| Typical use | Quick setup, dev/test, backup path | Production, large/consistent data transfer, consistent latency needs |

- Both terminate on a **Virtual Private Gateway** (or Transit Gateway)
  attached to the VPC.
- A common production pattern: **Direct Connect as primary, Site-to-Site
  VPN as an automatic failover path** — get the consistent low-latency
  link most of the time, with a resilient fallback that doesn't depend
  on the same physical circuit.

!!! success "The exam signal"

    "Need it set up today" / "no capital investment" → Site-to-Site VPN.
    "Consistent, high-bandwidth connection to our data center, cost
    matters at scale" → Direct Connect. "Can't have the connection
    unavailable even if one path fails" → both, together.
