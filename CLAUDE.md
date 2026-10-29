# Project Instructions

Study-prep site built with [Zensical](https://zensical.org/). Ongoing,
evolving resource — not scoped to one interview. These rules apply to
any agent (Claude or otherwise) working in this repo; follow them the
same way regardless of session.

## 1. Architecture

- Content: `docs/**/*.md`, mirroring `zensical.toml`'s `nav` structure
  1:1 (e.g. `docs/database/postgresql-for-scale.md`). Only `index.md`
  sits at `docs/` root.
- Nav is flat and domain-based — no "Study Materials" wrapper, no
  "Programming Languages" grouping. Current top-level domains:
  Frontend, Python, Backend, Architecture, Microservices & Distributed
  Systems, Software Testing, Cyber Security, Database, Cloud & DevOps,
  AI & LLM, Machine Learning, Algorithms, Interview Prep.
- **Promote a nested group to its own top-level domain** (or fold one
  into a better-fitting parent) when its scale or scope outgrows its
  current home — precedent: Machine Learning (ex-AI & LLM),
  Microservices & Distributed Systems (ex-Backend, via Architecture),
  Python itself (ex-Backend). Trigger: a nested group is bigger than
  several existing top-level domains, or its content no longer matches
  the domain it's nested under.
- **Redistribute scattered bare files into named groups** when a
  domain accumulates single-file nav entries sitting alongside its
  existing groups — a lighter, more frequent operation than promoting
  a whole domain. Precedent: AI & LLM, Database, Backend, Cyber
  Security, and Architecture itself all got this treatment. Mirror the
  grouping in `docs/index.md`'s Contents section.
- **Every nav group is a subfolder** (`docs/python/` is split into
  `language-fundamentals/`, `concurrency/`, `web-frameworks/django/`,
  `odoo/framework/`, and so on). When you move files, rewrite every
  relative link, the nav, `docs/index.md`, and `nav-order.json`, then
  build.
- **Nav order is learning order.** Put prerequisites first and optional
  or advanced topics later. A page must not link forward to a concept
  taught after it. Capstones and build plans go last. Keep a group to
  about 9 items; split into sub-groups beyond that.
- File names are descriptive kebab-case (`django-orm.md`, not
  `chapter-6.md`) — legacy numbered files get renamed when touched.
- New tracks (roles, topic areas) get their own pages/nav entries
  rather than replacing what's here.
- Config: `zensical.toml`. Deploys to GitHub Pages on every push to
  `main` via `.github/workflows/docs.yml`.

## 2. Workflow

- **Add/edit a page**: see `docs/README.md`.
- **Build/preview**: `pip install -r requirements.txt`, then
  `zensical build --clean` (full rebuild; exits non-zero / warns on
  broken internal links) or `zensical serve` (live-reload preview).
- **After any `nav` change**: `python3 scripts/generate_nav_manifest.py`
  to regenerate `docs/nav-order.json` (also runs automatically in CI,
  but run it locally too).
- **PDF export** (Zensical has none built in):
    - In-browser: "Download PDF" button
      (`docs/javascripts/download-pdf.js` + `docs/stylesheets/print.css`)
      fetches every page in `nav-order.json`, assembles them, calls
      `window.print()` → real selectable-text PDF.
    - Local/CLI: `python3 scripts/export_pdf.py` after a clean build —
      headless Chrome + `pdfunite` → `Cloud-Developer-Prep.pdf` at repo
      root (gitignored). Needs `google-chrome` and `pdfunite` on PATH.
- **Verify**: `zensical build --clean` must print "No issues found."
  Any "Warning: anchor does not exist" is a broken internal link — fix
  it before moving on.
- **If `zensical serve` is running**, `build --clean` fails with
  "cache directory could not be removed" because both use `.cache`.
  Don't kill the user's server. Verify in a throwaway copy instead:
  `rsync -a --exclude .venv --exclude .cache --exclude site --exclude .git ./ /tmp/copy/`,
  then run `zensical build --clean` there.

## 3. Git

- **Never push unprompted.** Commit locally by default; leave pushing
  to the user. Applies even when a push seems like the natural next
  step.
- **"Commit and push" always means squash, then push.** Whenever the
  user says "commit and push" (or "merge commits and push as one",
  "finally merge commits and push"), commit any pending changes, then
  squash **all unpushed commits** into one: `git fetch` → check
  `git log origin/main..HEAD` → `git reset --soft origin/main` → one
  descriptive commit message → `git push`. No need to re-confirm.
  Never push without that request.
- Never add a `Co-Authored-By: Claude` (or similar AI-attribution)
  trailer to commits.

## 4. Writing style

Applies to new site content and chat answers alike.

- **Bullets, not paragraphs.** `**Answer:**` sections and explanations
  are short list items, one idea each — not prose paragraphs. A 1-2
  sentence lead-in before the bullets is fine; large paragraphs as the
  default are not. Pros/Cons tables already satisfy this.
- **Say less.** Cut restated questions, throat-clearing lead-ins, and
  redundant examples (one makes the point). Test: could this survive
  losing a third of its words? If yes, cut them. Don't cut real
  trade-offs/nuance — cut padding around them.
- **Lead with the one core idea.** Find the single thing that matters
  most and say it first, in a sentence a reader could stop after.
  Supporting bullets back that idea up, not N parallel same-weight
  facts the reader has to synthesize.
- **Plain vocabulary.** Prefer the everyday word over an obscure one
  when both say the same thing ("works with every language and HTTP
  client," not "ubiquitous tooling") — much of the real audience is
  non-native English speakers. Real domain terms (idempotent, mutex,
  polymorphism, eventual consistency) stay exactly as-is; this is
  about decorative vocabulary, not technical precision.
- Existing pages predating a style rule don't need retroactive
  rewriting unless asked — these govern new content going forward.

## 5. New-page design

- **Standard shape**: numbered Q&A sections (`## N. "Realistic
  interview-style question?"`, heading text in quotes) each followed
  by a `**Answer:**` bullet list (§4). Code block first when a
  question is concrete/mechanical; bullets alone when it's conceptual.
- **Fundamentals before the question that prompted the page.** A
  reader can't evaluate a comparison/trade-off/"why X instead of Y"
  without a mental model of what X and Y *are* first. Before the first
  such question, plainly state what the thing *is*, in a sentence
  needing no prior knowledge. The question that prompted the page is
  where the content *arrives*, not where it starts.
- **Cross-link instead of duplicating.** When a concept is already
  explained elsewhere on the site (a shared mechanism, a term with its
  own real explanation — closures, bytecode, a prior chapter's
  pattern), link to it (`see [X §Y](other-page.md#anchor)`) instead of
  re-explaining it. This includes jargon/abbreviations that have a
  dedicated page — link the term itself, don't just expand the
  acronym inline and stop there.
- **Spell out every abbreviation on first use**, generously, even ones
  that feel obvious (`API` → "API (Application Programming
  Interface)"). Exception: a literal copy-pasteable artifact (a prompt
  template, code block, CLI command) — its audience is the tool, not
  the reader.
- **End with `## Code Samples`.** Either real references to runnable
  files (`code_samples/chapter-N/*.py`) plus install/run commands, or
  an honest "No dedicated code samples for this page — see X" when
  there's nothing to run. Every page gets this section, even if empty.
- **Interview Questions section** (before Code Samples, on pages
  substantial enough to warrant it): `## N. Interview Questions You're
  Likely to Get Asked`, grouped under bold mini-headers by sub-topic,
  each item a quoted realistic question followed by "— expects
  [the answer], [§ cross-reference]".
- **Split, don't just reorganize**, when a page grows too large or
  covers several distinct sub-topics: one top-level `zensical.toml`
  entry becomes a group of standalone files, one per sub-topic, each
  with its own `title:`/nav entry — not headings inside one giant
  page. Mirror the split in `docs/index.md`'s Contents section,
  regenerate `nav-order.json`, and fix any cross-refs that pointed at
  old single-file anchors (`zensical build --clean` flags broken
  ones). This is about navigability, not shortening — don't cut
  material to avoid splitting.
- **Depth over tools**: a chapter centered on a tool/service teaches
  the underlying mechanism *before* the "how to use it" material, not
  instead of it (e.g. what a container actually is — namespaces,
  cgroups, union filesystem — before the `docker run` flags). Signal
  something's missing: a bullet asserting a behavior without
  explaining *why* it's true at the system level. Reserve this for
  chapters genuinely shaped like a command reference; don't retrofit
  everywhere on a whim.
    - Use an **animated** inline SVG (`<animate>`/`<animateTransform>`,
      no CSS/JS) specifically for a process unfolding over time
      (copy-on-write, a request moving through a pipeline). Use a
      **static** diagram for structure or a side-by-side comparison.
      Same raw-HTML constraints as §7 apply.
- **Nav labels stay short** — roughly 2-5 words, not a colon-separated
  list of every subtopic (long labels wrap in the sidebar). The page's
  own H1/`title:` can and should stay fully descriptive; only the nav
  label needs to be short (e.g. nav label "ORM Query Cheat Sheet" vs.
  H1 "Django ORM Query Cheat Sheet for Senior Engineers"). Forward-looking
  only — don't rename existing labels on a whim.

## 6. Content scope

- **Weave in the AI-driven hiring era** where genuinely relevant — not
  forced everywhere. Interviewers now ask how candidates use AI tools
  day to day, live coding happens with an AI assistant present, some
  panels run on adaptive AI interviewers, resumes pass through AI
  ATS screening ([Interviewing in the AI Era](interview-prep/interviewing-in-the-ai-era.md)
  is the dedicated page). Add a short, concrete note (same
  interview-ready depth as the rest of the chapter) when AI-assisted
  workflows realistically changed that topic's day-to-day practice.
  Skip pure CS-theory topics. A real interview question naming this
  directly is the signal to add it.
- **Always use the latest stable version** of every technology, unless
  the user asks for an older one. Verify the current version (web
  search or the source) before writing, state it in the page (for
  example a `!!! note "Version"` admonition under the intro), and use
  that version's APIs and syntax. Mention older-version differences
  briefly, only where they help. Current example: Odoo 20.
- **Verify technical facts against the source, don't write from
  memory.** Prefer official source and docs. When a docs site blocks
  fetching (`odoo.com` returns 403), read the GitHub raw files instead
  (`odoo/odoo` and `odoo/documentation`, branch `20.0`). Cite real
  method and file names. If a detail can't be confirmed, soften it or
  leave it out. Never present a guess as fact.
- **The owner learns for mastery, not only for interviews.** Favor
  breadth and correct depth over interview shortcuts, and say plainly
  what a page does not cover.
- **Odoo app build is deferred.** Only the plan page exists
  (`docs/python/odoo/build-an-odoo-app-plan.md`). Do not write or run
  the app unless asked. If asked: put it in
  `code_samples/odoo/service_desk/`, one commit per step, and test each
  step in Docker (Odoo 20 + PostgreSQL).
- **Keep it name-agnostic** — this repo is meant to eventually go
  public. New content uses generic placeholders (`demo`, `example.com`,
  "a legal-tech startup," "a Senior Python Developer JD") — never the
  owner's real name, a real employer/client name, or a real personal
  resource-naming convention (e.g. no `fahad`-prefixed AWS resources).
  If unsure whether something's generic enough, ask.
- **A pasted job description becomes study content, not a tracker.**
  Don't create a "JD notes"/"JD tracker" summary page. Identify named
  technologies not yet covered and add each as a real, full-depth
  study page (same Q&A format as existing chapters) — not a stub.
  Classify each as general-purpose/reusable (Spark, Kafka, Kong) vs.
  genuinely domain-specific (FHIR/HL7 for healthcare) *before*
  grouping — general-purpose tech gets a topic-named section, not
  lumped under a domain-named one just because it came from the same
  posting. A quick CV gap-check is a conversational judgment call, not
  a saved artifact.

## 7. Known Zensical/Markdown bugs

Confirmed Python-Markdown bugs — not style preferences:

- **Raw HTML block (e.g. a hand-drawn `<svg>`) silently corrupts** if
  it contains: a `<style>` tag (drops *every* child element), a
  **blank line** (ends the block early, rest falls back to normal
  Markdown), or an **HTML comment** (same effect as a blank line). Fix:
  inline `style="..."` per element, no blank lines, no comments.
- **`def_list` pairs** (`Term\n:   Definition`) with no blank line
  between two consecutive pairs get nested into each other instead of
  staying siblings. Always blank-line-separate them.
- **A literal `|` inside a table cell** is parsed as a column
  separator and corrupts the row. Escape as `\|`.
- **A table with no blank line before its header row** (e.g. right
  after a `**Label:**` line) doesn't get recognized as a table at all
  — gets absorbed into the preceding paragraph with `<br />` tags
  instead. Always blank-line-separate a table from the line above it.

## 8. Cross-page anchors

Zensical slugifies headings: lowercase, strip everything that isn't a
word character/whitespace/hyphen, collapse whitespace to one hyphen.
Link to another page's heading as `otherpage.md#the-computed-slug` —
Zensical rewrites it to the right URL at build time. Don't guess the
slug for anything non-trivial; build and check the generated `id=`
attribute.
