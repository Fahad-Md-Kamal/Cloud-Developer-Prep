---
title: "AWS Systems Manager"
---

# AWS Systems Manager

[Session Manager](vpc-security-groups-and-flow-logs.md#bastion-host-jump-box)
already shows up as the modern bastion-host replacement, and
[Parameter Store](kms-secrets-and-cognito.md#secrets-manager-vs-parameter-store)
as a config-value store. Both are part of the same service — Systems
Manager — which the exam also tests for fleet-wide operational tasks
beyond those two pieces.

## Session Manager

Browser- or CLI-based shell access to an EC2 instance (or on-premises
server) with **no open SSH port, no SSH key to manage, and no bastion
host** — access is brokered entirely through the Systems Manager agent
and IAM, and every session is logged to CloudTrail/S3 automatically.

## Run Command

Executes a command (or a predefined document — install a package,
restart a service) across a fleet of instances at once, targeted by tag
or instance ID, without SSH-ing into each one individually.

## Patch Manager

Automates applying OS/security patches across a fleet on a schedule
(a **maintenance window**), instead of patching instances by hand or
rebuilding an AMI for every patch cycle — the fast, low-effort path for
patches that don't require a full
[Golden AMI re-bake](compute-and-scaling.md#when-to-re-bake).

## Automation Documents (Runbooks)

Pre-built or custom multi-step workflows (e.g. "stop an instance, take
a snapshot, restart it") that run as a single, repeatable, auditable
action instead of a human clicking through the same steps manually
every time — the same motivation as a
[Terraform module](terraform-modules-and-advanced-hcl.md#module-interface-design)
or an
[Ansible role](ansible-handlers-templates-roles-vault.md#roles):
package a repeated multi-step procedure once, run it by reference
afterward.

## Inventory & State Manager

`Inventory`
:   Collects metadata about what's actually installed/running across
    the fleet — applications, OS versions, network configs — for
    answering "which of our instances are running an outdated version
    of X" without checking each one by hand.

`State Manager`
:   Continuously enforces a defined configuration across a fleet (e.g.
    "this antivirus agent must always be installed and running") — similar
    enforcement idea to
    [AWS Config Rules](aws-security-and-compliance-services.md#aws-config-resource-configuration-compliance),
    but driving instances toward compliance directly rather than just
    flagging non-compliance.

!!! success "The exam signal"

    "Patch a fleet of instances on a schedule, with minimal operational
    overhead" → Patch Manager. "Run one command across many instances
    right now" → Run Command. "SSH access with no open port, fully
    audited" → Session Manager. All of these replace an older
    "install an agent and script it yourself" approach — the exam
    consistently rewards knowing that Systems Manager already has a
    built-in feature for most "manage a fleet of instances" scenarios.
