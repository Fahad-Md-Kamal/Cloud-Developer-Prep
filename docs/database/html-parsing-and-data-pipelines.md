---
title: "HTML Parsing & Data Pipelines"
---

# HTML Parsing & Data Pipelines

BeautifulSoup and lxml both turn HTML into something you can query, but
"which one is faster" is the wrong first question — the real one is what
a parser is actually building, and why malformed HTML (missing closing
tags, unescaped characters) mostly still works anyway. That mechanism is
what explains the real trade-offs, not a benchmark number.

## What a Parser Is Actually Building: the DOM Tree

Parsing HTML means turning a flat stream of text into a **tree**
structure — the Document Object Model — where each tag becomes a node,
nested inside its parent tag's node. Once that tree exists, "find all
the product prices" becomes a tree-traversal query instead of pattern
matching raw text, which is why nobody parses HTML with regular
expressions in practice: a regex has no concept of nesting, and HTML's
structure is fundamentally about nesting.

**Why malformed HTML still parses:** real HTML parsers (including every
browser's own parser) apply well-defined error-correction rules — an
unclosed `<li>` gets implicitly closed when the next sibling `<li>` or
the parent's closing tag appears, a missing `<tbody>` gets inserted
automatically around table rows. This isn't a bug being tolerated; it's
a documented part of the HTML parsing specification, precisely because
real-world HTML is never perfectly well-formed and the web would break
constantly if parsers didn't account for that.

## 1. "BeautifulSoup vs. lxml — what's actually different, and why does the comparison confuse people?"

**Answer:**

- **BeautifulSoup is an interface, not a parser** — it's a consistent
  Python API that sits *on top of* a choice of underlying parsers:
  Python's built-in `html.parser`, `lxml`, or `html5lib`. "Using
  BeautifulSoup" doesn't specify which actual parsing engine is doing
  the work, which is the source of most of the confusion in this
  comparison.
- **lxml is a Python binding to libxml2/libxslt** — mature C libraries,
  not pure Python — which is why parsing through lxml (either directly,
  or as BeautifulSoup's backend) is dramatically faster than Python's
  pure-Python `html.parser` on large documents.
- The real, practical comparison is: BeautifulSoup-with-lxml-backend
  gives both a friendly API *and* C-level parsing speed — the common
  production choice — versus using `lxml.etree` directly, which is
  faster still (no Python-object-wrapping overhead on top) but has a
  less forgiving, more XML-flavored API.
- `html5lib` is the slowest of the three, but the most spec-accurate —
  it implements the exact same error-correction algorithm real browsers
  use, which matters specifically when a page's exact rendered structure
  (including how a browser would have fixed its malformed HTML) needs to
  be reproduced precisely.

## 2. "CSS selectors vs. XPath — these query the same tree, so what's actually different?"

```python
# CSS selector
soup.select("div.product > span.price")

# Equivalent XPath
tree.xpath("//div[@class='product']/span[@class='price']")

# Something only XPath expresses directly: select by text content
tree.xpath("//button[text()='Add to Cart']")
```

**Answer:**

- Both are query languages over the exact same underlying tree — neither
  parses anything differently; they just express "which nodes do I
  want" differently.
- CSS selectors are more familiar to anyone who's written frontend CSS,
  and cover the large majority of real scraping needs (by tag, class,
  ID, attribute, nesting).
- XPath can express things CSS selectors fundamentally can't: selecting
  by a node's **text content**, selecting a node's **parent** (CSS can
  only select descendants/siblings, never ancestors), and positional
  logic like "the third `<tr>` in this table." Reach for XPath
  specifically when the thing you need to match isn't expressible as
  "an element with these tag/class/attribute characteristics."

## 3. "A document is too large to comfortably hold as a full parsed tree in memory — what do you do?"

```python
import lxml.etree as ET

# Builds the ENTIRE tree in memory before you can query anything
tree = ET.parse("huge_feed.xml")

# Processes one element at a time, discarding it once handled --
# memory stays flat regardless of document size
for _, elem in ET.iterparse("huge_feed.xml", tag="product"):
    process(elem)
    elem.clear()  # free this element's memory before moving to the next
```

**Answer:**

- A full DOM-tree parse holds the *entire* document structure in memory
  at once — fine for a normal page, genuinely a problem for a
  multi-gigabyte XML feed or sitemap.
- `iterparse` processes the document incrementally, yielding each
  element as it's parsed and letting you discard it (`elem.clear()`)
  once you've extracted what you need — memory use stays flat regardless
  of total document size, the same trade-off as the
  [generator-vs-load-everything pattern](../backend/python/memory-and-caching.md#1-how-would-you-process-a-file-too-large-to-fit-in-memory)
  covered for plain file processing.
- The cost is the same trade-off, too: a streaming parse can't do random
  access or re-visit an earlier element — once you've moved past it and
  called `clear()`, it's gone, so anything that genuinely needs the
  whole tree at once (complex cross-references between distant parts of
  the document) still needs the full parse.

## 4. "You're pulling the same fields from documents across several different sources — what's the actual pipeline shape?"

**Answer:**

- **Extract** — parse each source's HTML/XML and pull out the target
  fields using CSS selectors or XPath, same mechanism regardless of
  source.
- **Validate** — a field that's missing, in the wrong format, or
  obviously wrong (a negative price, an empty required field) should be
  flagged or rejected before it enters the pipeline, not silently passed
  through and discovered broken downstream.
- **Normalize** — different sources format the same kind of data
  differently (dates, currency, whitespace) — standardizing to one
  consistent representation here is what makes later deduplication and
  comparison possible at all; see
  [Data Cleaning, Normalization & Deduplication](data-cleaning-and-deduplication.md)
  for the mechanism behind that step specifically.
- **Load** — write the cleaned, normalized records into whatever store
  the pipeline feeds, usually in batches rather than one record at a
  time, for the same throughput reasons bulk inserts beat row-by-row
  inserts in any database.

| Pros | Cons / Trade-offs |
|---|---|
| BeautifulSoup-with-lxml gives a friendly API at C-level parsing speed | Raw `lxml.etree` is faster still, at the cost of a less forgiving API |
| XPath expresses selections (by text, by parent) CSS selectors simply can't | Less familiar to most engineers than CSS selectors |
| Streaming parse (`iterparse`) keeps memory flat on huge documents | No random access — can't revisit an element once it's cleared |
| html5lib matches real browser error-correction exactly | The slowest of the three common parsing backends |

---

## Code Samples

No dedicated code samples for this page.
