---
title: "Linux Fundamentals for DevOps"
---

# Linux Fundamentals for DevOps

Knowing `systemctl restart nginx` is the tool-usage version of Linux
administration. The fundamentals below — what a signal actually does to
a process, what `systemd` is actually tracking, why `df` can show free
space while writes still fail, and what a connection's actual state
means — are what let you debug a box that's behaving strangely, instead
of just running the one command you already know and hoping.

## Processes & Signals

A **process** is a running program — the kernel tracks it by a **PID**,
its own memory space, and a parent/child relationship to whatever
started it (almost everything traces back to PID 1).

A **signal** is how the kernel, or another process, asks a running
process to do something — interrupt it, usually. Two matter most:

`SIGTERM`
:   A polite request to exit. A process **can catch it** and run its
    own cleanup first — close database connections, finish an in-flight
    request, flush a buffer to disk — before actually exiting on its
    own terms.

`SIGKILL`
:   Not a request — the kernel terminates the process immediately,
    with **no chance to clean up at all**. A process can't catch,
    block, or ignore `SIGKILL`; that's deliberate, since it exists
    specifically as the "nothing else worked" escape hatch.

<svg viewBox="0 0 820 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of SIGTERM allowing a process to shut down cleanly, versus a stuck process being forcibly SIGKILLed once the grace period expires" style="width:100%;height:auto;max-width:820px;display:block;margin:0 auto;font-family:inherit;">
<rect x="40" y="140" width="220" height="90" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="150" y="180" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Orchestrator</text>
<text x="150" y="200" font-size="12" text-anchor="middle" fill="#5b6472">(Kubernetes / systemd / Docker)</text>
<rect x="560" y="140" width="220" height="90" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="3"><animate attributeName="stroke" values="#1f9d6b;#1f9d6b;#b5831f;#b5831f;#8a98ab;#1f9d6b;#1f9d6b;#b5831f;#b5831f;#c0392b;#c0392b" keyTimes="0;0.1;0.12;0.28;0.3;0.36;0.56;0.58;0.85;0.87;1" dur="15s" repeatCount="indefinite"></animate></rect>
<text x="670" y="175" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">Process</text>
<text x="670" y="198" font-size="13" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="1;1;0;0;1;1;0;0" keyTimes="0;0.1;0.12;0.36;0.38;0.56;0.58;1" dur="15s" repeatCount="indefinite"></animate>Running</text>
<text x="670" y="198" font-size="13" text-anchor="middle" fill="#7a5c14"><animate attributeName="opacity" values="0;0;1;1;0;0;1;1;0;0" keyTimes="0;0.1;0.12;0.28;0.3;0.56;0.58;0.85;0.87;1" dur="15s" repeatCount="indefinite"></animate>Shutting down…</text>
<text x="670" y="198" font-size="13" text-anchor="middle" fill="#5b6472"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.28;0.3;0.36;0.38;1" dur="15s" repeatCount="indefinite"></animate>Exited cleanly</text>
<text x="670" y="198" font-size="13" font-weight="600" text-anchor="middle" fill="#8e2d20"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.85;0.87;1" dur="15s" repeatCount="indefinite"></animate>Killed (SIGKILL)</text>
<circle r="10" fill="#d9822b" cy="185"><animate attributeName="cx" values="260;260;560;560;260;260;560;560" keyTimes="0;0.04;0.1;0.3;0.34;0.5;0.56;1" dur="15s" repeatCount="indefinite"></animate><animate attributeName="opacity" values="0;0;1;1;0;0;1;1;0;0" keyTimes="0;0.04;0.06;0.3;0.32;0.54;0.56;0.7;0.72;1" dur="15s" repeatCount="indefinite"></animate></circle>
<text x="410" y="340" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.32;0.36;1" dur="15s" repeatCount="indefinite"></animate>SIGTERM asks nicely — the process finishes its work and exits on its own.</text>
<text x="410" y="340" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.38;0.42;1" dur="15s" repeatCount="indefinite"></animate>Still running when the grace period ends → SIGKILL terminates it instantly, mid-work.</text>
</svg>

!!! danger "This is why a container/pod needs a real shutdown handler"

    Kubernetes, Docker, and `systemd` all follow the same pattern: send
    `SIGTERM`, wait a configurable **grace period**
    (`terminationGracePeriodSeconds` in Kubernetes), then `SIGKILL`
    anything still running. An application with no `SIGTERM` handler at
    all just gets forcibly killed on every single restart or
    deployment — dropping whatever request or write was in flight at
    that exact moment, every time, not just during real incidents.

## systemd: Managing Services

`systemd` is what actually starts, stops, and supervises long-running
processes on most modern Linux distributions — a **unit file**
(`myapp.service`) declares what to run and how to manage it, and
`systemd` tracks whether it's currently up.

```ini
# /etc/systemd/system/myapp.service
[Service]
ExecStart=/usr/bin/myapp
Restart=on-failure
```

```bash
systemctl start myapp      # start it now
systemctl enable myapp     # start it automatically on boot
systemctl status myapp     # is it running, and its recent log lines
journalctl -u myapp -f     # follow that service's logs live
```

- `Restart=on-failure` is `systemd` itself noticing the process died
  and restarting it — the same supervision role a container
  orchestrator plays for a pod, just at the single-host level.
- `journalctl` reads the **journal** — `systemd`'s own structured log
  store — filtered to one service's output with `-u`, instead of
  grepping through a flat text file in `/var/log`.

## Disk & Filesystem Troubleshooting

`df` vs `du`
:   `df` reports free space **per filesystem** (the whole disk/volume).
    `du` reports space used **per directory** — different questions:
    "is this disk full" vs "what on this disk is actually using the
    space." Reaching for the wrong one wastes time hunting through the
    wrong scope entirely.

`Running out of inodes, not space`
:   Every file needs an **inode** (metadata: permissions, owner,
    location on disk) — a filesystem has a *fixed* number of inode
    slots, set when it was created, completely separate from how many
    raw bytes are free. Millions of tiny files can exhaust every inode
    slot while `df` still shows plenty of free space — "No space left
    on device" with space visibly available is the classic symptom.
    `df -i` shows inode usage specifically, instead of byte usage.

`lsof: what's holding a file open`
:   Deleting a file with `rm` doesn't free its disk space if a running
    process still has that file open — the space isn't reclaimed until
    every process closes its handle to it. `lsof | grep deleted` finds
    exactly which process is still holding onto space `rm` should have
    already freed, the real fix for "I deleted a huge log file and `df`
    still shows the disk full."

## Networking Troubleshooting Toolkit

`ss` / `netstat`
:   What's listening on which port, and what connections are currently
    open — `ss -tlnp` lists every listening TCP socket and the process
    behind it, the first command for "is anything actually listening
    on the port I expect."

`curl -v`
:   Shows the actual request and response — headers, status code, and
    (with `-v`) the TLS handshake itself — instead of guessing what a
    client is really sending or receiving.

`tcpdump`
:   Captures raw packets off the wire, below the application layer
    entirely — the tool for when `curl`'s view isn't enough and the
    question is genuinely "what is actually going out over this
    network interface." Builds directly on
    [how TCP actually moves bytes](../architecture/how-the-internet-moves-files.md#from-bytes-to-packets-what-tcp-actually-does).

`dig` / `nslookup`
:   Query DNS directly, bypassing whatever a client library might be
    caching — see
    [How DNS Resolution Actually Works](load-balancing-and-dns.md#how-dns-resolution-actually-works)
    for the resolver chain these tools are actually querying against.

## File Permissions

```bash
chmod 644 config.yml    # owner: read/write, group & other: read-only
chmod 600 id_rsa        # owner only — the mode SSH keys require
chown appuser:appgroup /opt/myapp
```

- Three permission sets — **owner**, **group**, **other** — each with
  **read**, **write**, **execute** bits. `644` is
  `rw-r--r--`: the owner can write, everyone else can only read.
- `chown` changes who owns a file; `chmod` changes what its owner,
  group, and everyone else are allowed to do with it — two separate
  questions, often needed together when setting up a new service.
- This is the same reasoning behind
  [running a container as a non-root user](docker-production-images.md#non-root-users)
  — a process's actual Linux permissions decide what it can touch if
  something goes wrong, container or not.

---

## Code Samples

No dedicated code samples yet for this page — the commands above are
meant to be run directly on a real Linux box.
