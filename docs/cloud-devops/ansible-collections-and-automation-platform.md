---
title: "Ansible: Collections, Execution Environments & Automation Platform"
---

# Ansible: Collections, Execution Environments & Automation Platform

Last in a three-part Ansible series — see
[Ansible Fundamentals](ansible-fundamentals.md) and
[Handlers, Templates, Roles & Vault](ansible-handlers-templates-roles-vault.md)
for what comes before this page.

## Collections & Galaxy

A collection bundles modules, roles, and plugins for distribution
(`amazon.aws`, `community.general`, hundreds more).

``` bash
ansible-galaxy collection install amazon.aws
ansible-galaxy collection list
```

[galaxy.ansible.com](https://galaxy.ansible.com) is where to look for an
existing collection or role before writing a module from scratch —
reading a well-maintained, widely-used published role is also a faster
way to learn real structure and conventions than writing one from zero
with no reference.

## ansible.cfg

The behavior-configuration file — inventory path, default remote user,
SSH settings, retry/fact-caching behavior — read from several possible
locations in a defined precedence order (an environment variable, then
`./ansible.cfg` in the current directory, then `~/.ansible.cfg`, then
`/etc/ansible/ansible.cfg`). The same kind of "where did this setting
actually come from" question Terraform's own `*.tfvars` precedence
raises.

``` ini
# ansible.cfg
[defaults]
inventory = inventory.ini
host_key_checking = False
```

## Execution Environments & ansible-navigator

The current, container-based way to actually run a playbook:

- An **Execution Environment** is a container image bundling a specific
  Ansible version, Python dependencies, and collections — built with
  `ansible-builder`.
- `ansible-navigator run` executes a playbook inside one.
- This replaces "whatever happens to be pip-installed on the control
  node" with something as reproducible as the
  [Docker images](docker-production-images.md) this project already
  builds for the application itself — same motivation, same fix.

``` bash
ansible-builder build -t my-ee:1.0 -f execution-environment.yml
ansible-navigator run install_nginx.yml --execution-environment-image my-ee:1.0
```

## Dynamic Inventory from AWS

A static `inventory.ini` drifts the moment an Auto Scaling Group changes
size — a new instance never shows up until someone edits the file by
hand. The `amazon.aws.aws_ec2` inventory plugin queries AWS directly
instead:

``` yaml
# aws_ec2.yml -- an inventory source file, not a playbook
plugin: amazon.aws.aws_ec2
regions:
  - ap-south-1
filters:
  tag:Role: web
keyed_groups:
  - key: tags.Role
```

``` bash
ansible-inventory -i aws_ec2.yml --graph
ansible-playbook -i aws_ec2.yml install_nginx.yml
```

- Hosts are grouped by tag instead of by hand-maintained `.ini`
  sections — tag an instance `Role=web` in
  [Terraform](terraform-fundamentals.md) or the console, and it appears
  in the `web` group on the next run with no inventory edit at all.
- This is the natural next step once
  [Compute & Scaling](compute-and-scaling.md) is provisioning real
  instances: Terraform's own output (or just its tags) becomes Ansible's
  source of truth for what to configure.

## Automation Controller & Automation Hub

Ansible Automation Platform's web UI/API layer, for once an organization
moves past a single engineer's laptop running playbooks by hand:

- **Automation Controller** — job templates, scheduling, RBAC,
  credential storage.
- **Automation Hub** — a private collection registry, for content that
  shouldn't go to public Galaxy.

## Beyond the Checkpoint: Red Hat Ansible Certification

Ansible is a Red Hat product, so Red Hat is the only vendor certification
body for it — current as of October 2026, re-check Red Hat's own
certification pages before relying on any exam detail, since the lineup
is periodically reorganized.

| Exam | Role |
|---|---|
| EX200 (RHCSA) | Foundational RHEL exam — the required prerequisite for everything below, not Ansible-specific itself. |
| EX294 | Playbooks for day-to-day RHEL administration — packages, services, firewall rules, storage, users. Paired with EX200 to earn **RHCE, Ansible specialization**. |
| EX374 | Collections, execution environments, dynamic inventories, automation controller — the advanced, AAP-platform-aware specialist exam. |
| EX417 / EX457 / EX467 | Specialist exams for Windows targets, network device automation, and managing Automation Platform at scale, respectively. |

!!! danger "RHCE is not one exam"

    "Get RHCE" is often shorthand for "pass EX294," but RHCE is earned
    per specialization, requiring **two** exams — EX200 + EX294 for the
    Ansible track. EX294 alone, without a current EX200 already on file,
    does not earn RHCE.

A reasonable order starting from zero: EX200 first (the shared
prerequisite), then EX294 — objective-for-objective, the
best-aligned exam with this series' core curriculum. **RHCA** (Red Hat
Certified Architect) is the tier above that, earned via any three of the
four specialist exams (EX374/417/457/467) once a specific depth — AAP
platform, Windows fleets, or network devices — actually matches the work
being done.
