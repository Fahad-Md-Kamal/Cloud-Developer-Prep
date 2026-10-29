---
title: "Regex & Text Processing"
---

# Regex & Text Processing

Keeping `re` fast at scale, avoiding catastrophic backtracking, and
knowing when regex is the wrong tool entirely.

## 1. "How do you keep regex fast when the same pattern runs across millions of documents?"

```python
import re

CITATION_PATTERN = re.compile(r"\b\d+\s+U\.S\.\s+\d+\b", re.IGNORECASE)

def extract_citations(text: str) -> list[str]:
    return CITATION_PATTERN.findall(text)
```

**Answer:**

- Compile the pattern once (`re.compile(...)`) at module load time and
  reuse the compiled object. Python does cache a small number of
  recently-used uncompiled patterns internally, but relying on that
  implicit cache is fragile — an explicit module-level compiled
  pattern is the reliable version.
- Use non-greedy quantifiers and specific character classes
  deliberately — a naive greedy pattern can hit **catastrophic
  backtracking** on certain inputs, effectively hanging the process.
- For very large documents, process in a streaming/chunked fashion
  rather than loading the entire document into one regex call, if the
  pattern doesn't actually need full-document context to match.

**Likely follow-up — "what's catastrophic backtracking, concretely?"**

- A pattern with nested or overlapping quantifiers (e.g. `(a+)+b`) can
  force the regex engine to try an exponential number of ways to match
  an input that ultimately fails — a string that should fail instantly
  instead hangs the process for seconds, minutes, or longer.
- The fix is rewriting the pattern to remove the ambiguity (e.g.
  `a+b` instead of `(a+)+b`), not hoping a pathological input never
  arrives — user-supplied strings are exactly the input that finds
  this bug in production.

**Likely follow-up — "when should you not reach for regex at all?"**

- Anything with nested or recursive structure — HTML, JSON, deeply
  nested document sections — regex fundamentally can't correctly
  handle arbitrary nesting. Use a real parser (`html.parser`, `json`,
  a grammar-based parser) instead. "Now you have two problems" is the
  classic warning here for a reason.

| Pros | Cons / Trade-offs |
|---|---|
| Compiled patterns reused across calls avoid repeated compilation cost | A poorly written pattern can hang the process on pathological input |
| Extremely fast for genuinely flat, non-nested text patterns | Fundamentally wrong tool for nested/recursive structure (HTML, JSON) |
| No external dependency needed for structured-data extraction from flat text | Complex patterns become write-only — hard for anyone else to safely modify |

## 2. "Beyond simple matching, what do named groups and lookarounds actually buy you?"

```python
import re

CASE_PATTERN = re.compile(
    r"(?P<year>\d{4})\s+(?<=Vol\.\s)(?P<volume>\d+)"
)
```

**Answer:**

- **Named groups** (`(?P<year>\d{4})`) make `match.group("year")`
  self-documenting instead of `match.group(1)` — a pattern that breaks
  silently later if someone reorders the groups without updating every
  positional reference.
- **Lookarounds** (`(?=...)`, `(?<=...)`) match a *position* based on
  surrounding context without consuming it — useful for "find X only
  when followed/preceded by Y" without including Y in the captured
  result.
- Both add real regex-engine cost and cognitive overhead — reach for
  them when they genuinely simplify a tricky extraction, not as a
  default habit for every pattern.

| Pros | Cons / Trade-offs |
|---|---|
| Named groups make extraction code self-documenting and resilient to reordering | Slightly more verbose to write than positional groups |
| Lookarounds express "context without consuming it" cleanly | Harder to read for anyone unfamiliar with lookaround syntax |
| Both reduce brittle assumptions baked into positional-only patterns | Adds real matching cost — not free performance-wise |

---

## Code Samples

No dedicated code samples yet for this section — flag if you want a
runnable regex-performance/backtracking-safety example added under
`code_samples/`.
