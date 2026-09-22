# Preparation Guideline — Upcoming Interview & Ongoing Job Search

*Private working document — not published, not part of the Cloud-Developer-Prep
site. Contains real company names and job-search context that shouldn't be
public. Last updated 2026-09-22.*

---

## The system, stated plainly

Three things already exist, each with a different job. The point of this
guideline is to use them deliberately instead of starting from scratch every
time an interview comes up:

| Layer | What it is | Role |
|---|---|---|
| `/home/bjit/Desktop/In-Prep` | A 38-chapter manuscript + appendices (Django, system design, Docker/K8s, LLM/RAG, DSA) | The deep reference — the encyclopedia. Read from, don't rebuild. |
| `Cloud-Developer-Prep` (this repo, public/genericized) | Active-recall practice: checklists, worked examples, a real SQL sandbox, a dated session log of actual mistakes | Where the reps actually happen. Public because it's genericized — real client names never go here. |
| Per-company crash book (e.g. `In-Prep/cefalo-interview-prep.md`) | A short, fast, company-specific tactical doc, built 2–3 days before a real interview | Pulls from the two layers above, adds JD-specific positioning. Private, since it names the real company. |

This already worked once — the Cefalo crash book (March 2026) is a genuinely
good template: gap analysis, a 2-day and 3-day plan, a 10-question drill, full
mock rounds with sample answers, a final-evening checklist. Reuse that shape
for every future interview rather than reinventing it. The rest of this
document applies that system to the current situation.

---

## Part A — Immediate: Senior Python Developer (external client via BJIT)

### Where things actually stand (from `docs/session-log.md`, 2026-09-22)

| Area | Status | Evidence |
|---|---|---|
| Python core | ✅ solid | Mutable-default-argument question, correct after one nudge |
| Django/DRF (`select_related`/`prefetch_related`) | ⚠️ needs another rep | N+1 correctly diagnosed, but reached for the wrong tool first |
| SQL — window functions | ❌ → improving | First attempt used `GROUP BY` with no join, no window function at all. Since then: `RANK()` walked through with real data, practice sandbox problem 1 solved correctly on the 3rd try |
| SQL — sandbox problems 2–8 | Not started | Aggregates, `HAVING`, tie-handling, top-N-per-group, running totals, `LAG`/`LEAD` |
| AWS gaps (ECS, Aurora RDS, DynamoDB) | Not started | Named in the JD, not on the CV — see `docs/aws-services.md` |
| System design / STAR stories | Ready | 4 project stories written up in `docs/system-design.md`, not yet rehearsed out loud |
| Full 90-minute mock run | Not done | |
| Interview date/format | **Unconfirmed** | "possibly next week," test format unknown (live coding? take-home? quiz?) |

### Priority-ordered remaining work

1. **Confirm logistics with the BJIT recruiter/account manager** — this is
   blocking, not optional. Ask: exact date, test format (live coding /
   take-home / written quiz), tooling (shared IDE? their own repo?
   HackerRank?), timezone. Everything below assumes you don't know this yet;
   knowing it would let you weight prep correctly (e.g. no point drilling
   whiteboard SQL if the test is multiple-choice).
2. **SQL sandbox, problems 2–8** — this was the confirmed weak spot, and it's
   the one with a real practice tool already built (`practice/sql/`). Highest
   leverage use of remaining time.
3. **Second Django ORM rep** — a fresh `select_related` vs `prefetch_related`
   question, cold, until the answer is immediate rather than reasoned-out.
4. **AWS crash review** — ECS, Aurora RDS, DynamoDB, 30–45 min each (see
   `docs/aws-services.md`). Target is "has something sensible to say," not
   expertise.
5. **Say the 4 system-design stories out loud**, timed to ~90 seconds each,
   from `docs/system-design.md` — reading them silently doesn't build the
   fluency; speaking them does. Use the **real** project names when actually
   speaking to the interviewer (Zenrin, CyRisk, CEC IRTool, Mevrik DCX) — the
   genericized labels on the public site are a publishing constraint, not
   something to repeat in the room.
6. **One full 90-minute mock run**, once the above is solid — coding +
   verbal + a couple of behavioral questions back to back, timed, to
   calibrate pacing before the real thing.

### If the interview lands week of 2026-09-28

A rough shape (adjust once the actual date is confirmed):

- **Day 1–2:** SQL sandbox problems 2–8
- **Day 2–3:** Django/DRF second rep + AWS crash review (ECS/Aurora/DynamoDB)
- **Day 4:** Say all 4 system-design stories out loud; refine any that feel
  shaky
- **Day 5:** One full mock run-through, timed
- **Day before:** Logistics check only (camera/mic/internet, quiet space,
  CV + this guideline open in a second window). Light review, no cramming.
  Sleep.

---

## Part B — Ongoing: job search outside BJIT

The Cefalo crash book is evidence this is already active, not hypothetical.
The goal here is to make it sustainable and repeatable instead of an ad-hoc
scramble each time.

### 1. Don't rebuild the technical base per company

Every new opportunity should reuse the same two layers (`In-Prep` for depth,
`Cloud-Developer-Prep` for active recall) and only add a thin, fast
company-specific crash book on top — the way Cefalo's did. If a topic gap
shows up in a company crash book that isn't covered well in either base
layer, that's a signal to add it to `Cloud-Developer-Prep` (if it's
general-purpose, like the SQL window-function work from this session) or to
`In-Prep` (if it's deep reference material) — not just to that one crash book
— so the next interview benefits too.

### 2. A lightweight pipeline tracker

Worth keeping somewhere private (a simple table is enough — doesn't need
tooling): company, role, stage, key dates, next action, and one line on fit/
interest. Without this, momentum across multiple simultaneous processes is
easy to lose. Suggest keeping it in `In-Prep` (already private, already
where Cefalo's material lives) rather than creating a new location.

### 3. Per-company crash book workflow (repeat the Cefalo pattern)

1. JD gap analysis against the current CV/skills matrix (same exercise done
   at the start of this session for the BJIT client role)
2. Pull relevant material from `In-Prep` chapters + `Cloud-Developer-Prep`
   pages — don't re-derive explanations that already exist
3. Write a short, company-named crash book (2–3 day plan, positioning
   statement, likely-questions drill, mock rounds) — private, real names,
   same shape as `cefalo-interview-prep.md`
4. Mock run-through before the real interview
5. **Retrospective, after** — Cefalo's file has strong *prep* content but no
   record of how the actual interview went. Add one next time: what was
   actually asked, what landed, what didn't, any surprise the JD didn't
   signal. This is the single highest-leverage habit to add — it's what
   turns "prepared for one interview" into "compounds across every future
   one," the same way `docs/session-log.md` compounds practice sessions here.

### 4. Resume/CV

The current CV (`BJIT_Fahad_MD_Kamal_Senior_Software_Engineer_Python.docx`)
is strong and already tailored toward Python/Django/cloud roles. Two low-effort
additions worth considering:
- Link the public `Cloud-Developer-Prep` site from the CV/LinkedIn as
  evidence of active, structured continued learning — genuinely
  differentiating, and it costs nothing since it's already genericized and
  public.
- Keep the skills matrix in sync with what's actually being learned on
  current BJIT projects (e.g. if PostGIS/geospatial work deepens further,
  that's worth reflecting).

### 5. Confidentiality / operational hygiene

- `Cloud-Developer-Prep` stays genericized by design (enforced in its
  `CLAUDE.md`) — that boundary is already working, keep it that way as more
  content gets added.
- This file, `interview-prep.md`, the CV, and any future company crash books
  stay out of that public repo (already `.gitignore`d) — real employer/
  client names and active job-search context don't belong in anything
  publicly linked from a BJIT-visible identity.
- Keep job-search-specific material (this file, `In-Prep`'s crash books) on
  personal, not company-managed, infrastructure if that's not already the
  case.

### 6. Cadence

Avoid over-preparing generically at the expense of burnout — the useful
rhythm is roughly:
- **Ongoing, light:** keep `Cloud-Developer-Prep` fresh — a session every so
  often even with nothing scheduled, so core skills don't atrophy between
  opportunities.
- **On demand, focused:** a company crash book only once an interview is
  actually scheduled, not speculatively for every application.
