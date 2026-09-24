---
title: "Pathlib & File Operations"
---

# Pathlib & File Operations

Object-oriented path handling, lazy file discovery, and atomic writes —
the standard-library file operations that come up once a system is
processing more than a handful of files.

## 1. "Why use `pathlib` instead of `os.path` for file operations?"

```python
from pathlib import Path

document_path = Path("docs") / "regulations" / "gdpr.pdf"
```

**Answer:**

- `Path` is object-oriented and chainable (`Path("a") / "b" / "c"`)
  instead of string concatenation (`os.path.join`), which removes
  manual separator/escaping bugs across operating systems.
- `Path` objects are immutable — operations return new `Path` objects
  rather than mutating in place, which makes them safer to pass around
  and easier to mock in tests.
- Built-in methods cover what used to need `os.path` + `glob` +
  `shutil` scattered together: `.exists()`, `.glob()`, `.stat()`,
  `.read_text()`, `.mkdir(parents=True)`.
- Type-hint friendly — `def process(path: Path)` documents intent
  better than `path: str`.

**Likely follow-up — "when would you still reach for `os.path` or a raw string?"**

- An extremely hot loop doing millions of path operations, where
  `pathlib`'s object overhead is measurably worse than raw string
  ops — a rare, profile-verified case, not a default assumption.
- Interop with an older API that only accepts strings — `str(path)`
  bridges it, but the internal logic still benefits from `Path`.

| Pros | Cons / Trade-offs |
|---|---|
| Chainable, readable path construction — no manual separator handling | Slightly more overhead per operation than raw string manipulation |
| Immutable objects are safer to pass around and easier to mock in tests | Some older stdlib/third-party APIs still expect a plain string |
| One consistent API replaces `os.path` + `glob` + parts of `shutil` | Team members unfamiliar with the API need a short ramp-up |

## 2. "How do you find and process every file matching a pattern, without loading the whole list into memory first?"

```python
from pathlib import Path
import time

cutoff_time = time.time() - 30 * 86400
recent_docs = (
    p for p in Path("archive").rglob("*.pdf")
    if p.stat().st_mtime > cutoff_time
)
```

**Answer:**

- `Path.glob("**/*.pdf")` (or the equivalent `.rglob("*.pdf")`) returns
  a lazy generator, not a materialized list — matches are produced on
  demand as the caller iterates.
- Chaining a filter (`if p.stat().st_mtime > cutoff`) combines
  discovery and filtering in one pass instead of building a full list
  first and filtering it afterward.
- For a very large or network-mounted tree, the recursive walk itself
  is usually the actual bottleneck — not something `pathlib` can fix,
  since it's disk/network I/O, not a Python-level cost.

**Likely follow-up — "what's the risk of a recursive glob on a huge, deep directory tree?"**

- `**` walks the entire subtree — on a genuinely enormous or
  network-mounted filesystem this can be slow or block the caller.
- For that case, consider `os.walk` with early pruning of directories
  you don't need, or an indexed/database-backed file catalog instead
  of re-walking the filesystem on every request.

## 3. "How do you write a file safely so a crash mid-write doesn't leave a corrupted file?"

```python
import tempfile
import os
from pathlib import Path

def atomic_write(target: Path, data: bytes) -> None:
    fd, tmp_path = tempfile.mkstemp(dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, target)  # atomic on POSIX and Windows
    except Exception:
        os.unlink(tmp_path)
        raise
```

**Answer:**

- Write to a temporary file in the *same directory* as the target,
  then atomically rename/replace it onto the final path.
- `os.replace()` is atomic on both POSIX and Windows, so a reader
  never observes a partially-written file — it either sees the old
  version or the fully-written new one, never something in between.
- The temp file must be created on the same filesystem as the target
  — rename/replace across filesystems isn't atomic, and some
  implementations fall back to a non-atomic copy.
- Clean up the temp file on failure (the `except` branch) so a crash
  before the rename leaves only a stray temp file, not a corrupted
  final file.

| Pros | Cons / Trade-offs |
|---|---|
| Readers never see a partially-written file, even under a crash | Requires enough free disk space for both the temp and final file simultaneously |
| `os.replace` is atomic on both POSIX and Windows | Temp file must live on the same filesystem as the target, or the atomicity guarantee breaks |
| Failure path leaves the original file untouched | Slightly more code than a naive `open(path, "w")` |

---

## Code Samples

- `code_samples/chapter-38/pathlib_enterprise_patterns.py` —
  cross-platform file operations, document processing pipelines,
  atomic file operations
- `code_samples/chapter-38/integrated_stdlib_system.py` — several
  standard-library modules combined in one realistic pipeline
