---
title: Odoo Configuration & Deployment
---

# Odoo Configuration & Deployment

Running Odoo on your laptop and running it for real users are different
jobs. In production you decide **how many worker processes** serve
requests, **what limits** stop one bad request from hurting the rest,
**who talks to the database**, and **what sits in front** of the server.
All of it is configuration: command-line options, a config file, or
environment variables. This page covers the settings that matter, with the
real option names and defaults from the Odoo 20 source.

!!! note "Version"
    Written for **Odoo 20**, from `odoo/tools/config.py` on the `20.0`
    branch. Check `odoo-bin --help` on your install for the full list.

## 1. "Where do settings come from?"

```ini
; odoo.conf
[options]
addons_path = /opt/odoo/addons,/opt/custom_addons
db_host = db.internal
db_name = production
workers = 4
proxy_mode = True
```

**Answer:**

- Three sources, from the same option names:
    1. **Command line** — `odoo-bin --workers=4`.
    2. **A config file** — pass it with `-c` or `--config`, or the
       `ODOO_RC` environment variable. The file has an `[options]`
       section with the same names (`workers = 4`).
    3. **Environment variables** — each file-loadable option gets an
       automatic name, `ODOO_` plus the option name in capitals, such as
       `ODOO_WORKERS`. Database options also honor the standard
       PostgreSQL names, such as `PGHOST` and `PGDATABASE`.
- This makes container setups easy: no file, only environment variables.
- You can write a config file from your current options with `--save`.
- A secret like the database password should come from an environment
  variable or a protected file, not from a command line anyone can read
  in the process list.

## 2. "Which options matter first?"

**Answer:**

| Option | Default | What it does |
|---|---|---|
| `addons_path` | none | Folders with modules (core and your custom ones) |
| `db_name` (`-d`) | none | Database(s) to use |
| `db_host`, `db_port`, `db_user`, `db_password` | local | How to reach PostgreSQL |
| `http_interface` | `127.0.0.1` | Address to listen on |
| `http_port` (`-p`) | `8069` | Main web port |
| `gevent_port` | `8072` | Port of the gevent worker (live chat, notifications) |
| `proxy_mode` | off | Trust proxy headers (use only behind a trusted proxy) |
| `data_dir` (`-D`) | a default folder | Where attachments and sessions are stored |
| `logfile`, `log_level` | stderr, info | Where and how much to log |
| `list_db` | on | Show the database manager and list. Turn off in production |
| `admin_passwd` | `admin` | Master password for database management. **Change it.** |

- `http_interface` defaults to `127.0.0.1`, so a fresh Odoo is **not**
  reachable from outside. To serve other machines, bind a different
  address or, better, put a proxy in front.
- Turn off the database list in production (`--no-database-list`), and set
  `db_name` so users cannot browse other databases.
- Leaving `admin_passwd` at its default `admin` lets anyone who reaches the
  database manager create, copy, or delete databases.

## 3. "What are workers, and how many do you need?"

**Answer:**

- Default is `workers = 0`: **threaded mode**. One process handles
  requests with threads. Fine for development, not for production.
- With `workers = N` (N above 0), Odoo runs **prefork mode**: N separate
  HTTP worker processes, plus cron workers and a gevent worker for
  long-lived connections (`--gevent-workers`, default 1).
- Why separate processes: Python threads share one interpreter lock, so
  one process cannot use many CPU cores. Workers also isolate failures.
  See [Threading & the GIL](../../concurrency/threading-and-the-gil.md).
- Cron jobs have their own threads (`max_cron_threads`, default 2).
- A common starting rule: roughly one worker per CPU core (a little
  more), then measure. Each worker uses memory, so more is not always
  better.
- Workers are **recycled** when they hit limits, which keeps memory
  growth under control.

## 4. "What do the limit options protect you from?"

**Answer:**

| Option | Default | Effect |
|---|---|---|
| `limit_memory_soft` | 2048 MiB | A worker over this is reset **after** its current request |
| `limit_memory_hard` | 2560 MiB | Over this, memory allocation **fails** |
| `limit_time_cpu` | 60 s | Max CPU time per request |
| `limit_time_real` | 120 s | Max wall-clock time per request |
| `limit_time_real_cron` | follows `limit_time_real` | Max time per cron job (0 means no limit) |

- Soft vs hard: soft is a polite recycle between requests. Hard is a wall.
- The limits only apply in prefork mode (`workers` above 0). In threaded
  mode, nothing stops a runaway request.
- If users see requests killed at 120 seconds, a report or import is too
  big for a request. The fix is usually **moving it to a cron job or a
  queue**, not raising the limit. Raising limits hides problems and can
  exhaust memory.
- See [Odoo Performance & Testing](../framework/odoo-performance-and-testing.md) for
  finding the slow part first.

## 5. "What should sit in front of Odoo?"

**Answer:**

- A **reverse proxy** (nginx or similar) is the standard front door:
    - It terminates **HTTPS** (TLS, the encryption layer).
    - It forwards normal requests to the HTTP port (8069) and live
      connections to the gevent port (8072).
    - It serves static files and compresses responses.
- Then turn on **`proxy_mode`**. Odoo reads the real client address and
  protocol from the proxy's headers. Only enable it when a **trusted**
  proxy is in front, because otherwise anyone could fake those headers.
- `x_sendfile` lets the web server send large files (attachments, assets)
  directly instead of Odoo streaming them.
- Keep PostgreSQL **off the public network**. Only Odoo needs to reach it.
- Set `db_maxconn` (default 64) with the worker count in mind. Total
  connections used is about workers times the pool size, and PostgreSQL
  has its own connection limit.

## 6. "How do you run it with containers?"

**Answer:**

- The usual shape: one container for Odoo, one for PostgreSQL, a volume
  for the database files, and a volume for Odoo's data directory.
- Pass settings as **environment variables** (`ODOO_*`, `PG*`) or mount an
  `odoo.conf`.
- Mount your custom modules as a folder and add it to `addons_path`.
- Run **more than one Odoo container** only when attachments and sessions
  are on shared storage and a proxy balances the load. The data directory
  must be shared, or users lose sessions and files.
- Back up **both** the database and the data directory. A database backup
  alone loses the attachments stored on disk.

## 7. "What should you check before going live?"

**Answer:**

- **Security:** `admin_passwd` changed, database list off, `db_name` set
  (or `dbfilter`), HTTPS in front, PostgreSQL private.
- **Performance:** `workers` set, limits reviewed, a plan for long jobs.
- **Safety:** automatic backups of database **and** data directory, and a
  restore you have actually tested.
- **Observability:** logs written to a file or a log service, with a
  sensible `log_level`. The automation and upgrade logs from other pages
  are only useful if you keep them.
- **Upgrades:** a copy of production to rehearse on. See
  [Odoo Upgrades & Migration Scripts](odoo-upgrades-and-migrations.md).
- **Modules:** custom modules in a known folder, in version control, with
  the `depends` of each one correct.

## 8. "Where does AI help here?"

**Answer:**

- Good for drafting an nginx config, a compose file, and a list of
  settings to review.
- Risky for exact defaults and option names. They change between
  versions, so compare with `odoo-bin --help` and the source.
- Never paste real passwords or private hostnames into an AI tool.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Settings**

- "How do you configure Odoo in a container?" — expects environment
  variables or a mounted `odoo.conf`,
  [§1](#1-where-do-settings-come-from).
- "What is `proxy_mode` and when is it dangerous?" — expects trusting
  proxy headers, only safe behind a trusted proxy,
  [§5](#5-what-should-sit-in-front-of-odoo).

**Performance**

- "Why does production use workers?" — expects one interpreter-locked
  process can't use many cores, plus failure isolation,
  [§3](#3-what-are-workers-and-how-many-do-you-need).
- "Requests are killed at two minutes. What do you do?" — expects move
  the work to cron or a queue, not just raise the limit,
  [§4](#4-what-do-the-limit-options-protect-you-from).

**Operations**

- "What do you back up?" — expects the database **and** the data
  directory, [§6](#6-how-do-you-run-it-with-containers).
- "What is the first security setting you change?" — expects the master
  password and the database list,
  [§2](#2-which-options-matter-first).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Source to read in the `20.0` branch:

- `odoo/tools/config.py` — every option, its default, and its help text
