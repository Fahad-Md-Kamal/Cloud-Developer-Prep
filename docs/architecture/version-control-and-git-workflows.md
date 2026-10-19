---
title: Version Control & Git Workflows
---

# Version Control & Git Workflows

Knowing `git merge`/`git rebase` is the tool-usage version of Git. The
fundamentals below — what Git actually stores, and why a branch is
"just a pointer" — are what make merge, rebase, the reflog, and a
detached `HEAD` all click as applications of *one* simple mechanism,
instead of a pile of commands memorized separately. The practical
workflow knowledge (merge vs. rebase, `blame`, other VCS tools) follows
below that.

## How Git Actually Stores Everything

A common misconception worth correcting first: **Git doesn't store
diffs.** Every commit is a complete snapshot of the entire project at
that point, built from three simple object types — and every one of
those objects is named by the hash of its own content, not an
arbitrary ID.

`Blob`
:   The raw content of one file — just the bytes. No filename, no
    path. Two files with identical content anywhere in the project's
    history get the exact same blob, automatically deduplicated.

`Tree`
:   A directory listing — maps names to blob hashes (for files) and
    other tree hashes (for subdirectories). A tree is how an entire
    directory structure gets represented as one object.

`Commit`
:   Points to exactly **one tree** (the full project snapshot at that
    moment), plus the hash of its **parent commit** (or two parents,
    for a merge commit), plus metadata — author, message, timestamp.

Because a commit's hash is computed from all of that — including which
commit is its parent — changing *any* of it produces a genuinely
different object with a different hash. This single fact is the reason
rebase rewrites history and merge doesn't; see below.

**A branch is nothing more than a movable pointer** — a small file
under `.git/refs/heads/` holding one commit's hash, nothing else.
Creating a branch is writing one tiny new pointer file, not copying any
project files — this is exactly why branches are so cheap in Git,
unlike the centralized model covered in §1 below.

<svg viewBox="0 0 900 480" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of a commit graph, showing a merge commit joining two branch tips versus a rebase replaying commits onto a new parent with new hashes" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<line x1="130" y1="77" x2="190" y2="77" stroke="#c7cedb" stroke-width="2"></line>
<line x1="280" y1="77" x2="340" y2="77" stroke="#c7cedb" stroke-width="2"></line>
<line x1="235" y1="105" x2="300" y2="180" stroke="#c7cedb" stroke-width="2"></line>
<line x1="355" y1="207" x2="415" y2="207" stroke="#c7cedb" stroke-width="2"></line>
<rect x="40" y="50" width="90" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="85" y="83" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">A</text>
<rect x="190" y="50" width="90" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="235" y="83" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">B</text>
<rect x="340" y="50" width="90" height="55" rx="8" fill="#eef1f5" stroke="#434d5c" stroke-width="2"></rect>
<text x="385" y="83" font-size="15" font-weight="600" text-anchor="middle" fill="#2b313b">C</text>
<rect x="265" y="180" width="90" height="55" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="stroke" values="#2f6fb3;#2f6fb3;#9aa5b3;#9aa5b3" keyTimes="0;0.64;0.68;1" dur="17s" repeatCount="indefinite"></animate></rect>
<text x="310" y="213" font-size="15" font-weight="600" text-anchor="middle" fill="#1d4a78">D</text>
<rect x="415" y="180" width="90" height="55" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"><animate attributeName="stroke" values="#2f6fb3;#2f6fb3;#9aa5b3;#9aa5b3" keyTimes="0;0.64;0.68;1" dur="17s" repeatCount="indefinite"></animate></rect>
<text x="460" y="213" font-size="15" font-weight="600" text-anchor="middle" fill="#1d4a78">E</text>
<text x="385" y="35" font-size="13" font-weight="600" text-anchor="middle" fill="#0f6b45"><animate attributeName="opacity" values="1;1;0;0;1;1" keyTimes="0;0.3;0.34;0.58;0.62;1" dur="17s" repeatCount="indefinite"></animate>main</text>
<text x="460" y="165" font-size="13" font-weight="600" text-anchor="middle" fill="#7b4ea3"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.66;0.7;1" dur="17s" repeatCount="indefinite"></animate>feature</text>
<g><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.3;0.34;0.58;0.62;1" dur="17s" repeatCount="indefinite"></animate>
<line x1="430" y1="77" x2="490" y2="77" stroke="#1f9d6b" stroke-width="2"></line>
<line x1="460" y1="180" x2="530" y2="105" stroke="#1f9d6b" stroke-width="2" stroke-dasharray="5,5"></line>
<rect x="490" y="50" width="90" height="55" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"></rect>
<text x="535" y="83" font-size="15" font-weight="600" text-anchor="middle" fill="#0f6b45">M</text>
<text x="535" y="35" font-size="13" font-weight="600" text-anchor="middle" fill="#0f6b45">main</text>
</g>
<g><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.66;0.7;1" dur="17s" repeatCount="indefinite"></animate>
<line x1="385" y1="105" x2="535" y2="300" stroke="#b5831f" stroke-width="2"></line>
<line x1="580" y1="327" x2="640" y2="327" stroke="#b5831f" stroke-width="2"></line>
<rect x="490" y="300" width="90" height="55" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="535" y="333" font-size="15" font-weight="600" text-anchor="middle" fill="#7a5c14">D′</text>
<rect x="640" y="300" width="90" height="55" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="685" y="333" font-size="15" font-weight="600" text-anchor="middle" fill="#7a5c14">E′</text>
<text x="685" y="285" font-size="13" font-weight="600" text-anchor="middle" fill="#7b4ea3">feature</text>
</g>
<text x="450" y="420" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.26;0.3;1" dur="17s" repeatCount="indefinite"></animate>main and feature share commit B, then diverge — C on main, D and E on feature.</text>
<text x="450" y="420" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.3;0.34;0.58;0.62;1" dur="17s" repeatCount="indefinite"></animate>merge: ONE new commit M, pointing to both C and E. Nothing existing is touched.</text>
<text x="450" y="420" font-size="18" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.64;0.68;1" dur="17s" repeatCount="indefinite"></animate>rebase: D and E replay as D′ and E′ on top of C — new parents mean new hashes. The old D/E become unreachable.</text>
</svg>

!!! success "This is the mechanism behind §2's rule of thumb below"

    Merge creates one new object with two parents — every existing
    commit stays exactly as it was, which is why merge is always safe
    on a shared branch. Rebase creates brand-new commit objects with a
    different parent, which means different hashes, even though the
    actual file changes are identical — the old commits don't get
    edited, they just stop being reachable from the branch pointer,
    which is exactly why force-pushing a rebase rewrites history out
    from under anyone who already has the old commits.

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
