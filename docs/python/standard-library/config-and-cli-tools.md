---
title: "Configuration & CLI Tools"
---

# Configuration & CLI Tools

Layered configuration across environments, and building an internal
CLI with `argparse` — the operational tooling every backend team
eventually needs, without an external dependency.

## 1. "How do you manage configuration across dev/staging/production without duplicating every setting?"

```python
import configparser
from pathlib import Path

config = configparser.ConfigParser()
config.read([Path("default.ini"), Path("production.ini")])
```

**Answer:**

- `ConfigParser.read([...])` reads multiple files in order — later
  files override keys set by earlier ones, giving a base +
  environment-override pattern without manually merging dictionaries.
- Keep secrets out of any committed `.ini` file entirely — inject them
  via environment variables at runtime (`os.environ`) and treat the
  config file as structure and non-sensitive defaults only.
- Validate the loaded config at startup, not at first use — a bad or
  missing value should fail fast at boot, not three hours into a
  batch job that only reads that setting once, deep in its run.

| Pros | Cons / Trade-offs |
|---|---|
| Base + override pattern avoids duplicating shared settings per environment | No built-in type validation — everything reads back as a string unless you convert it |
| Keeping secrets out of committed files is enforced by convention, not by the tool | Convention-based secret separation relies on discipline, not a hard guarantee |
| Startup-time validation catches config mistakes before they cause a mid-run failure | Requires writing that validation explicitly — `ConfigParser` doesn't do it for you |

## 2. "When would you reach for `argparse` instead of a config file?"

```python
import argparse

parser = argparse.ArgumentParser(description="Batch document processor")
parser.add_argument("--batch-size", type=int, default=100)
parser.add_argument("--dry-run", action="store_true")

subparsers = parser.add_subparsers(dest="command")
subparsers.add_parser("migrate")
subparsers.add_parser("backfill")
```

**Answer:**

- **Config files** hold settings that are stable across runs — DB
  host, log level, feature flags.
- **CLI args** (`argparse`) hold per-invocation parameters that change
  every run — which file to process, `--dry-run`, `--batch-size`.
- These aren't either/or in practice — a well-built CLI tool loads a
  config file for defaults and lets CLI args override specific values
  for that one run.
- **Subcommands** (`add_subparsers`) organize a tool that does several
  distinct operations (`mytool migrate`, `mytool backfill`) instead of
  one script with a dozen mutually-exclusive flags trying to cover
  every mode at once.

**Likely follow-up — "why bother with a real CLI tool instead of a one-off script with hardcoded values?"**

- A one-off script's hardcoded values become a liability the moment
  someone other than the original author needs to run it differently.
- `argparse`'s `--help` output, type coercion (`type=int`), and
  validation (`choices=[...]`) turn a script into something a
  teammate — or the same author, six months later — can run correctly
  without reading the source first.

| Pros | Cons / Trade-offs |
|---|---|
| `--help` and type coercion make a tool usable by someone other than its author | More upfront code than a script with hardcoded values |
| Subcommands scale cleanly as a tool grows more operations | Poorly organized subcommands can still become confusing at scale |
| CLI args overriding config defaults gives per-run flexibility without editing files | Two sources of truth (config + CLI) need a clear, documented precedence order |

---

## Code Samples

- `code_samples/chapter-38/enterprise_configuration.py` —
  multi-environment configs, secret separation, validation patterns
- `code_samples/chapter-38/config/default.ini`,
  `code_samples/chapter-38/config/development.ini`,
  `code_samples/chapter-38/config/production.ini` — example layered
  config files
