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

## This repo is public — never add real client/employer-confidential details

Do not write real client names, real product/project names from client
engagements, real employer-internal details, or any other identifying
information about a specific employer's client into any tracked file under
`docs/`.

Project stories on `docs/system-design.md` use generic, descriptive labels
instead of real names — e.g. "Geospatial Data Platform (confidential
client)" instead of a real product name. The **technical substance stays
real** (stack, architecture decisions, metrics/outcomes) since that's not
confidential — only the identifying name is genericized. If the user pastes
new project details containing a real client/product name, genericize the
name before writing it to a file, but keep the technical content.

The user's own name, email, and generic role/skill self-assessments are
fine to publish — this is their personal prep site. The line is
**client-identifying information**, not personal information.

If unsure whether something is identifying, ask before publishing it.

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
