# Project instructions

## Site architecture

This site is built with [Zensical](https://zensical.org/) (a Markdown-based
static site generator). Content lives in `docs/*.md`, config in
`zensical.toml`, and `.github/workflows/docs.yml` builds and deploys it to
GitHub Pages automatically on every push to `main`.

- **To add or edit a page**: see `docs/README.md`.
- **Local build/preview**: `pip install -r requirements.txt`, then
  `zensical build --clean` (full rebuild, exits non-zero / warns on broken
  internal links) or `zensical serve` (local preview server with
  live-reload).
- This is meant to be an ongoing, evolving job-prep resource — not scoped to
  one interview. New tracks (new roles, new topic areas) get their own pages
  and `nav` entries rather than replacing what's here.

## This repo must stay PRIVATE — do not suggest making it public again

As of 2026-09-22 this repo holds real client/employer-confidential content
alongside the original genericized material:

- `docs/*.md` (excluding `docs/manuscript/`) — the original public-safe
  content (genericized project labels on `docs/system-design.md`, etc.).
  This layer was written to survive being public.
- `docs/manuscript/` — migrated from a separate private project
  (`In-Prep`). Contains real company/target names (Lawstronaut, Optimizely,
  Cefalo) and a real client case study (`docs/manuscript/appendix-a.md`,
  the MeetingFlow system). **Not genericized.**

Both are now built into the same site by the same `zensical.toml`/GitHub
Actions workflow, so the public/private boundary is enforced entirely at
the **repo visibility** level (must be private), not per-file anymore. If
asked to make this repo public again, flag `docs/manuscript/` explicitly
first — it would need to be removed or genericized before that's safe.

The user's own name, email, and real project details are fine here now —
this is a private repo, not a public prep site anymore.

If unsure whether something is safe to add given this repo's current
privacy state, ask.

## Known Zensical/Markdown gotchas

These are real, confirmed bugs in Python-Markdown's HTML/table handling.

**Embedding raw HTML (especially a hand-drawn `<svg>` diagram) directly in a
`.md` file** — three separate things will silently corrupt it:

1. A `<style>` tag anywhere inside the block causes Python-Markdown to drop
   *every child element* of the block, leaving just the empty outer tag.
2. A **blank line** anywhere inside the block ends it early — everything
   after falls back to normal Markdown parsing and gets mangled.
3. An **HTML comment** (`<!-- ... -->`) anywhere inside the block does the
   same thing as a blank line.

The fix for all three: no `<style>` tag (inline `style="..."` per element
instead), no blank lines inside the block, no comments.

**Writing a `def_list` (Term\n:   Definition) block** — if two term/
definition pairs are placed back-to-back with **no blank line between
them**, Python-Markdown nests the second pair *inside* the first
definition instead of treating them as siblings. Always put a blank line
between each term/definition pair.

**Writing a Markdown table** — a literal `|` character inside a cell's text
is parsed as an extra column separator and silently corrupts/drops the rest
of that row. Escape it as `\|`.

**A table with no blank line before it** — if a table's header row
immediately follows a non-blank, non-table line (e.g. `**Trace Table:**`
directly above the `| ... |` header, no blank line between), Python-Markdown
doesn't recognize it as a table at all — the whole thing gets absorbed into
the preceding paragraph as literal text with `<br />` tags instead of
rendering a `<table>`. This was a real, confirmed bug found across 114
occurrences in the migrated manuscript content (mostly Chapter 36's
"Trace Table:" pattern), fixed by inserting a blank line before every
such table. Always put a blank line between a preceding line and a
table's header row.

## Verifying content changes

- `zensical build --clean` exits with "No issues found." Any "Warning:
  anchor does not exist" means a broken internal link — fix it.

## Internal cross-references between pages

Zensical auto-generates heading anchors by slugifying the heading text:
lowercase, strip everything that isn't a word character/whitespace/hyphen,
collapse whitespace to a single hyphen. To link to a heading on a
*different* page, use `otherpage.md#the-computed-slug` in the Markdown
source — Zensical rewrites this to the correct final URL at build time.
Don't guess the slug; build once and check the generated `id=` attribute if
unsure.
