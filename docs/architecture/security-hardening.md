---
title: "Security Hardening"
---

# Security Hardening

Input validation, injection prevention, XSS, and a security-headers
baseline — the defenses that sit around authentication/authorization
rather than inside them. See
[Authentication Patterns](authentication-patterns.md) and
[Authorization Patterns](authorization-patterns.md) for *who* and
*what*; [Threat Detection & Monitoring](threat-detection-and-monitoring.md)
for catching what gets through anyway.

## 1. Input Validation and Injection Prevention

**"Design input validation for an API accepting user content, and explain how parameterized queries actually stop SQL injection."**

```python
from pydantic import BaseModel, validator
import bleach

class DocumentUpload(BaseModel):
    title: str
    content: str

    @validator("content")
    def sanitize(cls, v):
        return bleach.clean(v, tags=["p", "br", "strong", "em"], strip=True)
```

```python
from sqlalchemy import text

query = text("SELECT id, title FROM documents WHERE owner_id = :uid AND type = :t")
db.execute(query, {"uid": user_id, "t": doc_type})  # bound params, not string-built SQL
```

**Answer:**

- Validate at the API boundary, before business logic sees the input —
  whitelist allowed values/formats, reject unknown fields, enforce
  size limits, never echo raw rejected input into logs/errors.
- **Parameterized queries work because the query structure and the
  data travel to the database as two separate things** — user input
  can never be reinterpreted as SQL syntax, no matter what characters
  it contains.
- An ORM parameterizes normal queries by default — the risk returns
  the moment you concatenate user input into a raw fragment, most
  commonly `ORDER BY`/`LIMIT` (many ORMs don't parameterize those).
  Whitelist allowed columns there explicitly.
- Least-privilege DB accounts (no runtime DDL) limit the damage if
  something still gets through.

**Follow-up — "what about NoSQL?"** Same idea: validate document
structure/types before insertion, whitelist allowed operators. MongoDB
injection usually comes from passing a raw user dict straight into a
query filter, letting an operator like `$where`/`$ne` sneak in where a
plain value was expected.

## 2. Cross-Site Scripting (XSS) Protection

**"Sanitize on input or escape on output — why does it matter which?"**

```python
import bleach

def sanitize_rich_text(html: str) -> str:
    return bleach.clean(html, tags=["p", "b", "i", "a"], attributes={"a": ["href"]}, strip=True)
```

**Answer:**

- **Escape on output by default**, per sink (HTML/JS/CSS/URL) — what
  auto-escaping template engines already do, safe because it happens
  right before data reaches a place that could interpret it as code.
- **Sanitize on input** only for the narrow case of storing and later
  rendering real rich-text HTML (a comment box with bold/italic) —
  allowlist, never a blocklist.
- CSP is the backstop for anything that slips through: disallow inline
  scripts, use nonce-based CSP when inline is unavoidable, strip
  dangerous URL schemes (`javascript:`, `data:`) from user links.

| Pros | Cons / Trade-offs |
|---|---|
| Output encoding: safe by default, automatic in most template engines | Wrong for content genuinely meant to render as HTML |
| Input sanitization: lets you store/render limited rich text at all | Easy to get the allowlist wrong — too loose, and you've built an XSS vector |
| CSP backstop: blocks exploitation even if a sanitizer has a bug | Real maintenance cost — a strict CSP breaks the first unreviewed third-party script |

## 3. Security Headers and HTTPS Enforcement

**"What does a solid security-headers baseline look like, and what does each header actually stop?"**

```python
response.headers.update({
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": f"default-src 'self'; frame-ancestors 'none'; script-src 'self' 'nonce-{request_nonce}'",
})
```

**Answer:**

- **HSTS** — stops protocol-downgrade/SSL-stripping by forcing HTTPS
  at the browser level.
- **`frame-ancestors 'none'`** (or `X-Frame-Options: DENY`) — stops
  clickjacking.
- **`X-Content-Type-Options: nosniff`** — stops the browser executing
  a file as a different content type than declared.
- **A strict CSP** is the main XSS backstop — only if `unsafe-inline`
  is avoided, since that's exactly what lets an injected `<script>`
  execute. Use a per-request nonce for legitimate inline scripts.

**Follow-up — "why exclude a subdomain from HSTS preload?"** If any
subdomain still serves plain HTTP, preload breaks it for every
visitor, permanently — removal from preload lists is slow and not
guaranteed.

---

## Code Samples

No dedicated code samples yet for this page — the validation/sanitization
snippets above are small enough to adapt directly.
