# Adding a new page to this site

This file is **not** part of the built site — Zensical excludes `README.md`
automatically since this folder already has its own `index.md`. Safe to keep
here for anyone (or any agent) editing content.

## Steps

1. **Create the file** under `docs/`, with frontmatter:

   ```markdown
   ---
   title: My New Topic
   ---

   # My New Topic

   Content here — headings, admonitions (`!!! note`/`!!! success`/`!!! danger`),
   tables, fenced code blocks, `def_list` definition lists, and Mermaid
   diagrams (` ```mermaid `) all work.
   ```

2. **Add it to `nav` in `zensical.toml`** (repo root):

   ```toml
   nav = [
     { "Home" = "index.md" },
     ...
     { "My New Topic" = "my-new-topic.md" },
   ]
   ```

   Zensical builds *any* `.md` file under `docs/` whether or not it's in
   `nav` — but without a `nav` entry the page has no sidebar link.

3. **(Optional) Link it from `docs/index.md`** too, matching the existing
   topic bullets, so it shows up on the hub page.

## Verify before pushing

```bash
zensical build --clean   # full rebuild; warns on broken internal links
zensical serve           # local preview, live-reloads on save
```

## Genericizing client/employer content — read before adding project stories

This site is public. Real client names, product names, and any
client-confidential details are **not** to be published here — see the root
`CLAUDE.md` for the specific rule and the labels already in use for existing
projects. When adding a new project story (e.g. after a new engagement),
apply the same treatment before writing it into `docs/system-design.md`.
