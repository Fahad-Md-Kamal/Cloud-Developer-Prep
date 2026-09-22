# Cloud Developer Prep

A living backend/cloud interview-prep guide — built from real practice
sessions, not a static checklist copied off the internet.

**[Read the live site →](https://fahad-md-kamal.github.io/Cloud-Developer-Prep/)**

## What this is

Started as prep for a Senior Python/Django role, but meant to keep
growing as an ongoing job-prep resource: new tracks and topics get added
rather than replacing what's here.

Each topic page pairs a review checklist with worked examples pulled
directly from practice Q&A — including the mistakes, not just the clean
final answer — plus a [session log](docs/session-log.md) that's the
actual dated record of what was asked, answered, and corrected.

## Topics

- **Python Core** — language fundamentals: mutable defaults, generators,
  decorators, the GIL, context managers.
- **Django & DRF** — ORM query optimization, migrations, signals,
  middleware, DRF serializers/permissions, Celery + Redis.
- **SQL** — joins, indexing, normalization, window functions,
  transactions.
- **AWS Services** — hands-on services plus a crash-review of gap
  services named in target job descriptions.
- **System Design & Stories** — STAR-shaped stories from real project
  experience (genericized for public posting).
- **Session Log** — the running practice-session record.

## Repository layout

| Path | What it is |
|---|---|
| `docs/` | The site's content, as Markdown. See `docs/README.md` for how to add or edit a page. |
| `zensical.toml`, `requirements.txt`, `.github/workflows/` | Site build/deploy config — [Zensical](https://zensical.org/) generates the static site, GitHub Actions deploys to GitHub Pages on every push to `main`. |
| `CLAUDE.md` | Project instructions, including the rule for genericizing client-identifying names before publishing. |
