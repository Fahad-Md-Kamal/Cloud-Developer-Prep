---
title: "Pathlib & File Operations"
---

# Pathlib & File Operations

Knowing `open()`/`.read()`/`.write()` is the tool-usage version of file
I/O. The fundamentals below — what `open()` actually asks the OS for,
where "written" data really sits before it's durable, and why text mode
can silently corrupt binary data — are what separate "I called
`f.write()`" from being able to answer a senior-level question about
whether that write actually survived a crash. Object-oriented path
handling, lazy file discovery, and atomic writes (the practical,
standard-library side of this) follow below that.

## How File I/O Actually Works

### File Descriptors: What `open()` Actually Gets You

`open()` in Python ultimately asks the OS, via a syscall, for a **file
descriptor** — a small integer the kernel uses as a handle to that open
file (`0`, `1`, `2` are always stdin/stdout/stderr; a newly opened file
gets the next free one). Every read, write, or seek Python does
eventually comes down to the kernel looking up that integer in its own
open-file table. `f.fileno()` returns it; `os.read(fd, n)`/`os.write(fd,
data)` are the thin, nearly-direct wrappers around the actual syscalls,
with Python's own `open()` layering everything below on top.

### The Buffering Stack: Three Layers, Not One

`open()`'s result isn't one simple object — it's a stack of three,
each adding one capability on top of the layer below:

1. **Raw I/O** (`FileIO`) — the unbuffered layer, a thin wrapper
   directly around the file descriptor's `read`/`write` syscalls.
2. **Buffered I/O** (`BufferedReader`/`BufferedWriter`) — adds an
   in-process memory buffer, so Python doesn't make a syscall for every
   single `.read(1)` or `.write(x)` call — it reads/writes in larger
   chunks and serves small calls out of memory.
3. **Text I/O** (`TextIOWrapper`) — adds character encoding/decoding and
   universal-newline translation on top of the buffered binary layer.
   This is the layer `open(path, "r")` (text mode) gives you; `open(path,
   "rb")` (binary mode) stops one layer earlier and hands back raw
   bytes, no decoding at all.

This is *why* binary mode is both faster and safer for non-text data:
text mode is doing real work (decoding bytes to `str`, translating line
endings) that binary mode skips entirely — work that actively corrupts
the data if it was never valid text to begin with.

### Where "Written" Data Actually Sits

`f.write(data)` returning successfully does **not** mean the data is
safe on disk — it means the data reached layer 2 above, Python's own
buffer, nothing more. There are three distinct places data passes
through, each with a different durability guarantee:

<svg viewBox="0 0 900 380" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated diagram of written data moving from Python's buffer to the OS page cache on flush, then to physical disk on fsync" style="width:100%;height:auto;max-width:900px;display:block;margin:0 auto;font-family:inherit;">
<rect x="20" y="60" width="260" height="110" rx="8" fill="#fdf3e3" stroke="#b5831f" stroke-width="2"></rect>
<text x="150" y="100" font-size="16" font-weight="600" text-anchor="middle" fill="#7a5c14">Python's Buffer</text>
<text x="150" y="122" font-size="13" text-anchor="middle" fill="#7a5c14">(user-space memory)</text>
<text x="150" y="144" font-size="12" text-anchor="middle" fill="#9a7420">lost if the process crashes</text>
<rect x="320" y="60" width="260" height="110" rx="8" fill="#eaf2fb" stroke="#2f6fb3" stroke-width="2"></rect>
<text x="450" y="100" font-size="16" font-weight="600" text-anchor="middle" fill="#1d4a78">OS Page Cache</text>
<text x="450" y="122" font-size="13" text-anchor="middle" fill="#1d4a78">(kernel memory)</text>
<text x="450" y="144" font-size="12" text-anchor="middle" fill="#3d699a">lost if the machine loses power</text>
<rect x="620" y="60" width="260" height="110" rx="8" fill="#e8f7f0" stroke="#1f9d6b" stroke-width="2"></rect>
<text x="750" y="100" font-size="16" font-weight="600" text-anchor="middle" fill="#0f6b45">Physical Disk</text>
<text x="750" y="122" font-size="13" text-anchor="middle" fill="#0f6b45">(persistent storage)</text>
<text x="750" y="144" font-size="12" text-anchor="middle" fill="#3d9a73">survives both</text>
<circle r="10" fill="#d9822b" cy="115"><animate attributeName="cx" values="150;150;150;450;450;450;750;750;750;150" keyTimes="0;0.15;0.2;0.38;0.45;0.6;0.78;0.85;0.97;1" dur="13s" repeatCount="indefinite"></animate></circle>
<text x="450" y="230" font-size="19" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.33;0.37;1" dur="13s" repeatCount="indefinite"></animate>f.write(data) — lands only in Python's own buffer. A crashed process loses this.</text>
<text x="450" y="230" font-size="19" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.36;0.4;0.73;0.77;1" dur="13s" repeatCount="indefinite"></animate>f.flush() — a write() syscall hands it to the OS page cache. A power loss here still loses it.</text>
<text x="450" y="230" font-size="19" text-anchor="middle" fill="#1f2a3a"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.76;0.8;1" dur="13s" repeatCount="indefinite"></animate>os.fsync(f.fileno()) — forces the OS to actually commit it to disk. Only this survives a power loss.</text>
</svg>

!!! danger "`with open(...) as f: f.write(data)` guarantees less than it looks like"

    `close()` (which the `with` block calls automatically) flushes
    Python's buffer to the OS — but it does **not** call `fsync`. The
    data is guaranteed to have reached the OS, not that it's physically
    on disk. A process crash after `close()` is safe; a *power loss*
    after `close()` but before the OS itself flushes its page cache is
    not. This is exactly the gap in the
    [atomic-write pattern below](#3-how-do-you-write-a-file-safely-so-a-crash-mid-write-doesnt-leave-a-corrupted-file) —
    it's atomic (a reader never sees a half-written file), but not
    durable against power loss, unless an explicit `os.fsync(fd)` is
    added before the `os.replace()` call. Atomicity and durability are
    two different guarantees; getting one doesn't get you the other for
    free.

### Buffering Modes, and the "My print() Didn't Show Up" Bug

- **Unbuffered**: every write is an immediate syscall. Rare in practice
  (slow), mostly used for `stderr`.
- **Line-buffered**: flushes automatically on every `\n`. This is what
  `stdout` uses when it's attached to an interactive terminal.
- **Fully (block) buffered**: flushes only when the buffer fills (a few
  KB) or `flush()`/`close()` is called explicitly. This is what `stdout`
  uses when it's redirected to a file or piped to another process — a
  genuinely different mode than the terminal case, not just a detail.

This is the real mechanism behind a classic bug: `print()` statements
showing up immediately in a terminal, but seeming to "go missing" (or
appear all at once, out of order relative to another process's output)
when the same script's output is piped or redirected — the buffering
mode silently changed underneath the same code.

### Text Mode's Hidden Work: Encoding and Newlines

Opening in text mode (`"r"`/`"w"`, no `b`) does two things silently:

- **Decodes/encodes** bytes using a codec — `utf-8` on most modern
  defaults, but **not guaranteed**: it can fall back to
  `locale.getpreferredencoding()`, which differs by OS and locale
  settings. This is the real mechanism behind "works on my Linux
  machine, breaks for a Windows teammate" file-encoding bugs — always
  pass `encoding="utf-8"` explicitly rather than trusting the platform
  default.
- **Translates line endings** — `\r\n` on disk (Windows-written files)
  becomes `\n` once read in Python's text mode, and back again on write
  (universal newlines). Binary mode sees the raw `\r\n` untouched.

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
            f.flush()
            os.fsync(f.fileno())  # durable, not just atomic -- see note below
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
- The `flush()` + `os.fsync()` pair matters for a reason that's easy to
  miss: atomicity (never seeing a half-written file) and durability
  (surviving a power loss) are
  [two different guarantees](#where-written-data-actually-sits) — the
  rename makes this atomic on its own, but without the explicit fsync
  the "written" data could still only be sitting in the OS page cache,
  not physically on disk, at the moment of the rename.
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
