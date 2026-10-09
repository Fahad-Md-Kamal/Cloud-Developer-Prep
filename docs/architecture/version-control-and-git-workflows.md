---
title: Version Control & Git Workflows
---

# Version Control & Git Workflows

Git-specific depth beyond "know how to commit and push" — the
questions that actually separate "uses Git" from "understands what Git
is doing."

## 1. "Have you used any version control system other than Git?"

**Answer:**

- This question is less about naming other tools and more about
  whether you understand what's actually distinctive about Git's
  model — distributed, not centralized.
- **Subversion (SVN)** — centralized: one single server holds the
  history, and a client checks out a working copy. No local commits;
  every commit requires network access to the central server. Branching
  is expensive and comparatively rare compared to Git, where every
  clone carries the *entire* history and branches are cheap, local
  pointers.
- **Mercurial** — conceptually close to Git (distributed, similar
  branching model), lost mindshare mostly for ecosystem/tooling
  reasons rather than a fundamental technical gap.
- **Perforce** — still common in game development and anywhere large
  binary assets dominate (art, audio) — centralized, with file locking
  as a first-class feature, since binary files can't be *merged* the
  way text can.
- A GUI (SourceTree, GitKraken, VS Code's built-in Git panel) is fine
  day-to-day, but CLI fluency matters because a GUI tends to hide
  exactly the state you need to see to debug a bad situation — a
  rebase conflict, a detached `HEAD`, a reflog entry pointing at a
  commit that's about to be garbage-collected.

## 2. "What's the difference between merge and rebase?"

```bash
# merge -- creates a new commit joining two histories
git checkout main
git merge feature-branch

# rebase -- replays feature-branch's commits on top of main
git checkout feature-branch
git rebase main
```

**Answer:**

- `git merge` creates a new merge commit joining two branches'
  histories — it preserves exactly what happened, including the fact
  that the branches diverged, at the cost of a less linear, "noisier"
  commit history (two parent commits, a merge commit for every
  integration).
- `git rebase` replays one branch's commits on top of another,
  producing a linear history with no merge commit — cleaner history,
  at the cost of rewriting commit hashes entirely. Every replayed
  commit is a genuinely new commit object, even if the diff looks
  identical.
- That hash rewrite is exactly why rebase is dangerous on anything
  already pushed/shared: force-pushing a rebased branch rewrites
  history out from under anyone who already pulled the old commits and
  built further work on top of them — their branch now diverges from
  a history that no longer exists upstream.

**Rule of thumb:**

- Rebase local, not-yet-pushed work to clean up a messy commit history
  before sharing it (squashing "wip" commits, reordering).
- Merge — never rebase — once a branch is shared or pushed, so
  collaborators' history is never rewritten out from under them.

| | Pros | Cons / Trade-offs |
|---|---|---|
| `merge` | Safe on shared branches; preserves true history | Noisier log — merge commits and non-linear graph |
| `rebase` | Clean, linear history — easy to read as a story | Rewrites hashes — unsafe on anything already shared/pushed |

## 3. "Which Git command shows who last changed each line of a file?"

```bash
git blame path/to/file.py

# scope to a line range
git blame -L 10,20 path/to/file.py

# pair with git log -p to see the full commit a blamed line came from
git log -p -- path/to/file.py
```

**Answer:**

- `git blame` annotates every line of a file with the commit hash,
  author, and date that last touched it — the direct answer to "who
  wrote this, and when."
- `-L start,end` scopes it to a line range instead of annotating the
  whole file, useful on a large file when only one function is under
  investigation.
- `git blame` alone only shows *which* commit touched a line, not
  *why* — pairing it with `git log -p <commit>` (or `git show
  <commit>`) on the hash it reports gets the full diff and commit
  message behind that line, which is usually the actual answer being
  looked for ("why does this line exist").
- A common follow-up trap: a line can show as "last changed" by a
  reformatting or rename commit, not the commit that actually
  introduced the logic. `git blame -w` ignores whitespace changes, and
  `git log --follow` tracks a file's history across renames — both
  worth knowing when blame points at a misleading commit.
