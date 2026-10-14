---
title: "Ansible Fundamentals: Configuration Management"
---

# Ansible Fundamentals: Configuration Management

[Terraform](terraform-fundamentals.md) answers "what infrastructure should
exist" — it provisions the VPC, the EC2 instance, the database, and tracks
all of it as state. Ansible answers a different question: "what should be
configured, once that infrastructure exists." This is the first of a
three-part Ansible series; see
[Handlers, Templates, Roles & Vault](ansible-handlers-templates-roles-vault.md)
and
[Collections, Execution Environments & Automation Platform](ansible-collections-and-automation-platform.md)
for what follows.

## What Ansible Is, and Why It Sits Alongside Terraform

- Ansible is a **configuration management** tool, not a provisioning one.
- Agentless — it reaches a target purely over SSH (or WinRM for Windows),
  no daemon to install on the target first.
- Push-based — the control node decides when something runs, rather than
  an agent polling for work.
- Idempotent by convention — a module's whole contract is "converge the
  target to this state, do nothing if it's already there." Same
  idempotency principle Terraform's `plan`/`apply` cycle is built around,
  just enforced per-module instead of via a tracked state file.

|  | Terraform | Ansible |
|---|---|---|
| Answers | What infrastructure should exist | What should be configured on it |
| Tracks via | A state file | Nothing persistent — re-checks the target every run |
| Reaches targets via | Cloud provider APIs | SSH / WinRM |
| Typical role in the chain | Provisions the EC2 instance | Installs packages, drops config, deploys the app onto it |

In practice the two are chained, not chosen between: Terraform provisions
instances from [Compute & Scaling](compute-and-scaling.md), and Ansible is
what then installs packages, drops config files, and deploys the
application onto them — either from a dynamic inventory built straight
from Terraform's own output, or from AWS directly (the
`amazon.aws.aws_ec2` inventory plugin, covered in
[Collections, Execution Environments & Automation Platform](ansible-collections-and-automation-platform.md#dynamic-inventory-from-aws)).

## A Local Practice Lab, No AWS Cost

Every concept below is learnable against two plain Docker containers
standing in for managed nodes — no AWS spend, rebuildable in seconds, and
exactly the same SSH-based mechanics Ansible uses against a real EC2
instance.

``` bash
# One-time setup
python3 -m venv .venv && source .venv/bin/activate && pip install ansible
docker build -t ansible-practice-node -f docker/Dockerfile.node docker/
docker run -d --name ansible-node1 -p 2221:22 ansible-practice-node
docker run -d --name ansible-node2 -p 2222:22 ansible-practice-node

# Each new session
source .venv/bin/activate
docker start ansible-node1 ansible-node2
ansible web -m ping
```

!!! danger "A non-interactive shell can break Ansible outright"

    Running `ansible`/`ansible-playbook` from some automated or
    non-interactive shells fails immediately with `ERROR: Ansible
    requires blocking IO on stdin/stdout/stderr`. Piping the command
    through `| cat` forces blocking I/O and fixes it — a normal
    interactive terminal never hits this, so it only shows up when
    Ansible is driven from a script or another tool's shell.

## Inventory

The list of managed nodes Ansible operates against — a static
`.ini`/`.yaml` file to start, `group_vars`/`host_vars` for per-host or
per-group data, and eventually a dynamic inventory plugin that queries
AWS directly instead of hand-maintaining a host list that drifts the
moment an Auto Scaling Group changes size.

``` ini
# inventory.ini -- two local containers standing in for real EC2 hosts
[web]
node1 ansible_host=127.0.0.1 ansible_port=2221
node2 ansible_host=127.0.0.1 ansible_port=2222

[web:vars]
ansible_user=ansible
ansible_ssh_private_key_file=./docker/ansible_practice_key
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
ansible_python_interpreter=/usr/bin/python3
```

- Everything under `[web]` is a **group** — a playbook targets a group,
  never a bare list of hosts.
- `[web:vars]` sets variables for every host in that group at once,
  instead of repeating `ansible_user=...` on every line.
- A real EC2-backed inventory swaps `ansible_host`/`ansible_port` for the
  instance's actual address and drops the port-mapping noise — the
  group/task/role logic above it doesn't change at all.

## Modules & Ad-Hoc Commands

- A **module** is one idempotent unit of work —
  `ansible.builtin.package`, `ansible.builtin.service`,
  `amazon.aws.ec2_instance`, hundreds more.
- An **ad-hoc command** runs exactly one module against the inventory
  with no playbook at all — the fastest way to answer "is this true
  right now across my fleet" without writing anything down.

``` bash
ansible web -m ping
ansible web -a "systemctl status nginx"
ansible web -m setup   # dump every fact Ansible can gather about a host
```

## Playbooks, Plays & Tasks

A playbook is a YAML file of **plays**; each play targets a group from
the inventory and runs an ordered list of **tasks**, each task invoking
one module. This is the unit everything else in this series builds on.

``` yaml
# install_nginx.yml
- name: Install and start nginx
  hosts: web
  become: true

  tasks:
    - name: Update apt cache
      ansible.builtin.apt:
        update_cache: true
        cache_valid_time: 3600

    - name: Install nginx
      ansible.builtin.apt:
        name: nginx
        state: present

    - name: Ensure nginx is running and enabled
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true
```

``` bash
ansible-playbook install_nginx.yml
```

!!! note "Idempotent — run it twice and look at the second run"

    The first run reports several `changed` tasks. Run the exact same
    command again right after, and every task reports `ok` with
    `changed=0` — nginx is already installed, already running, nothing
    left to do. That's the idempotency contract made visible, not just a
    claim: a playbook is safe to re-run on every deploy, the same way a
    repeated `terraform apply` is safe once nothing's left to change.

## Variables & Facts

Data a playbook depends on — set in inventory, in
`group_vars`/`host_vars`, passed with `-e`, or discovered automatically
as **facts** (`ansible_facts`, gathered from the target itself at the
start of a play unless `gather_facts: false`).

``` bash
ansible web -m setup -a "filter=ansible_distribution*"
```

!!! note "Precedence is one of the genuinely fiddly parts"

    `-e` on the command line beats everything; a role's own `vars/`
    beats its `defaults/`; `host_vars` beats `group_vars`. Worth
    deliberately studying the full order rather than discovering it by
    accident the first time two sources disagree and the "wrong" one
    wins — the same kind of question Terraform's own `.tfvars` loading
    order raises.

## Loops & Conditionals

- `loop:` runs a task once per item in a list.
- `when:` skips a task based on a fact or variable.
- Together these turn a flat task list into something that actually
  branches per host.

``` yaml
- name: Install several packages
  ansible.builtin.apt:
    name: "{{ item }}"
    state: present
  loop:
    - nginx
    - git
    - curl

- name: Restart nginx only on Debian-family hosts
  ansible.builtin.service:
    name: nginx
    state: restarted
  when: ansible_facts['os_family'] == "Debian"
```
