# Adding a new page to this site

This file is **not** part of the built site — Zensical excludes `README.md`
automatically since this folder already has its own `index.md`. Safe to keep
here for anyone (or any agent) editing content.

## `docs/` is organized into subdirectories matching the nav

As of 2026-09-24, `docs/*.md` is no longer flat — every file lives
under a subdirectory matching its top-level nav group (e.g.
`docs/data-and-engineering/postgresql-for-scale.md`,
`docs/programming-languages/python/django-orm.md`). Only `index.md`
and `session-log.md` stay at `docs/` root, as the site's entry points.
Put a new file in the subdirectory matching where it belongs in the
nav — don't drop it back at the flat root.

Internal links between pages are normal relative Markdown paths from
the linking file's own location — `../other-group/page.md` to link
across subdirectories, `page.md` (or `../page.md`, `../../page.md`)
within or above the current one. Zensical resolves these the same way
any relative link resolves; there's no docs-root-relative shortcut.

## Steps

1. **Create the file** under the right subdirectory, with frontmatter:

   ```markdown
   ---
   title: My New Topic
   ---

   # My New Topic

   Content here — headings, admonitions (`!!! note`/`!!! success`/`!!! danger`),
   tables, fenced code blocks, `def_list` definition lists, and Mermaid
   diagrams (` ```mermaid `) all work.
   ```

2. **Add it to `nav` in `zensical.toml`** (repo root), with its path
   relative to `docs/`:

   ```toml
   nav = [
     { "Home" = "index.md" },
     ...
     { "My New Topic" = "some-group/my-new-topic.md" },
   ]
   ```

   Zensical builds *any* `.md` file under `docs/` whether or not it's in
   `nav` — but without a `nav` entry the page has no sidebar link.

3. **(Optional) Link it from `docs/index.md`** too, matching the existing
   topic bullets, so it shows up on the hub page.

4. **Regenerate the PDF-export nav manifest** whenever `nav` changes:

   ```bash
   python3 scripts/generate_nav_manifest.py
   ```

   This writes `docs/nav-order.json`, which the in-browser "Download PDF"
   button (`docs/javascripts/download-pdf.js`) fetches to know every page
   and the order to assemble them in. It's regenerated automatically in
   CI before every deploy, but a stale local copy means the button won't
   include a page you just added when testing with `zensical serve`.

## Verify before pushing

```bash
zensical build --clean   # full rebuild; warns on broken internal links
zensical serve           # local preview, live-reloads on save
```

## This repo is private — see CLAUDE.md before adding real names

This repo holds real client/employer-confidential content directly in
`docs/**/*.md` (see the root `CLAUDE.md`, "This repo must stay PRIVATE").
That's only safe as long as the repo's GitHub visibility stays private —
if you're ever asked to make it public again, that requires a full pass
over `docs/**/*.md` to genericize real names first, starting with
`docs/reference-case-studies/project-stories.md`.
`docs/reference-case-studies/meeting-intelligence-case-study.md` is
already anonymized (no real project name or client-identifying detail)
and doesn't need that pass.
