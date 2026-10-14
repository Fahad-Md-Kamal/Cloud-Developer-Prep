---
title: "Ansible: Handlers, Templates, Roles & Vault"
---

# Ansible: Handlers, Templates, Roles & Vault

Second in a three-part Ansible series — see
[Ansible Fundamentals](ansible-fundamentals.md) for inventory, modules,
playbooks, variables, and loops/conditionals first, and
[Collections, Execution Environments & Automation Platform](ansible-collections-and-automation-platform.md)
for what comes after this page.

## Handlers & notify

A handler is a task that only runs if something **notified** it — the
standard "restart nginx, but only if its config actually changed"
pattern. A handler runs once at the end of a play, even if several tasks
notified it during that play.

``` yaml
tasks:
  - name: Deploy nginx config
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
    notify: restart nginx

handlers:
  - name: restart nginx
    ansible.builtin.service:
      name: nginx
      state: restarted
```

- If the template task makes no change (the rendered file is identical
  to what's already there), the handler never fires — no unnecessary
  restart.
- If three different tasks all notify the same handler in one play, it
  still only runs once, at the end.

## Error Handling: block, rescue, always

A direct parallel to `try`/`except`/`finally`:

``` yaml
tasks:
  - block:
      - name: Risky task that might fail
        ansible.builtin.command: /opt/app/migrate.sh
    rescue:
      - name: Roll back on failure
        ansible.builtin.command: /opt/app/rollback.sh
    always:
      - name: Always runs, success or failure
        ansible.builtin.debug:
          msg: "Migration attempt finished"
```

- `ignore_errors: true` on a single task — Ansible keeps going even if
  that one task fails, without the full block/rescue machinery.
- `failed_when:` — overrides a module's own notion of "failed" when it
  isn't the one that actually matters here (e.g. a `command` module that
  exits 0 but prints "ERROR" to stdout).

## Templates (Jinja2)

The `template` module renders a `.j2` file with full Jinja2 —
variables, conditionals, loops — into a real config file on the target.
This is how one template produces a correct `nginx.conf` for every
environment, instead of hand-maintaining one file per environment.

``` jinja
# nginx.conf.j2
server {
    listen {{ nginx_port | default(80) }};
    server_name {{ ansible_facts['hostname'] }};

    location / {
        proxy_pass http://127.0.0.1:{{ app_port }};
    }
}
```

``` yaml
- name: Deploy nginx config from template
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/sites-available/app.conf
  vars:
    app_port: 3000
  notify: restart nginx
```

## Roles

A standard directory layout (`tasks/`, `handlers/`, `templates/`,
`defaults/`, `vars/`, `meta/`) that packages a reusable unit of
automation.

```
roles/
└── nginx/
    ├── tasks/main.yml
    ├── handlers/main.yml
    ├── templates/nginx.conf.j2
    ├── defaults/main.yml
    └── meta/main.yml
```

!!! success "Wait for the second real use"

    The same judgment call as extracting a
    [Terraform module](terraform-modules-and-advanced-hcl.md#module-interface-design):
    once the same handful of tasks shows up in a second playbook, that's
    the signal to stop copy-pasting YAML and extract a role instead —
    not before, on the guess that it'll probably be needed eventually.

## Ansible Vault

Encrypts a variables file (or any file) at rest with a password or a
KMS-backed key, so a secret can live in git without living in git *in
plaintext*. Same non-negotiable rule
[Jenkins' credentials store](jenkins-security-hardening-and-production-patterns.md#plugin-hygiene-the-credentials-store-folder-level-security)
and Terraform's Secrets Manager integration already enforce elsewhere in
this project — just enforced at the file level here instead of
per-value.

``` bash
ansible-vault create secrets.yml      # new encrypted file
ansible-vault edit secrets.yml        # edit in place, re-encrypts on save
ansible-vault view secrets.yml        # read without decrypting to disk
```

``` yaml
# secrets.yml, once decrypted -- never commit the decrypted version
db_password: "actual-secret-value"
```

``` yaml
# A task referencing the encrypted variable like any other variable
- name: Write app config
  ansible.builtin.template:
    src: app.env.j2
    dest: /opt/app/.env
  vars:
    db_password: "{{ db_password }}"
```

``` bash
# Running a playbook that uses a vault-encrypted file
ansible-playbook deploy.yml --ask-vault-pass
# or, non-interactively, with a password file kept out of git:
ansible-playbook deploy.yml --vault-password-file ~/.vault_pass
```
