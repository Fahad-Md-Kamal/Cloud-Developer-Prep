---
title: "Authorization Patterns"
---

# Authorization Patterns

RBAC, ABAC, per-resource checks, and API key scoping — deciding *what*
an already-authenticated caller can do. See
[Authentication Patterns](authentication-patterns.md) for *who* they are.

## 1. Role-Based Access Control (RBAC)

**"How do you design a role hierarchy that doesn't turn into permission sprawl?"**

```python
class Role:
    def __init__(self, name: str, permissions: set[str], parent: "Role | None" = None):
        self.name = name
        self.permissions = permissions
        self.parent = parent

    def all_permissions(self) -> set[str]:
        perms = self.permissions.copy()
        return perms | self.parent.all_permissions() if self.parent else perms
```

**Answer:**

- Keep a small, actively-owned role catalog — not a role per team's ad
  hoc request.
- Default deny when a check is ambiguous; least privilege by default.
- Separate duties — no single role holds two permissions that should
  require two people (e.g. "approve payment" + "create vendor").
- Review high-risk roles periodically; grants drift, they don't stay
  correct on their own.

| Pros | Cons / Trade-offs |
|---|---|
| Simple — one role, one fixed permission set | Coarse — can't express "only during business hours" or "only this tenant" |
| Easy to audit — a readable permission list | Role explosion if every edge case becomes a new role |
| Fast checks — one lookup | Sprawl over time without an active owner pruning it |

## 2. Attribute-Based Access Control (ABAC)

**"When does RBAC stop being enough, and what does ABAC add?"**

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class ABACPolicy:
    name: str
    condition: Callable[[dict], bool]  # never eval() a raw policy string
    effect: str  # "ALLOW" or "DENY"

def is_authorized(policies: list[ABACPolicy], context: dict) -> bool:
    for policy in policies:
        if policy.condition(context):
            return policy.effect == "ALLOW"
    return False  # default deny
```

**Answer:**

- RBAC answers "what role does this user have." ABAC answers "given
  this user, this resource, and this context (time, location, device),
  is this action allowed" — needed once rules depend on more than
  role (e.g. "marketing reads customer data on a corporate device
  during business hours, not from a personal device at 2am").
- Normalize attribute names/types and document their source.
- Prefer deny-overrides on policy conflicts.
- Cache low-volatility attributes; short TTL on volatile ones (IP
  reputation, device risk).

**Follow-up — "what's wrong with `eval()`-ing a policy condition string?"**
Arbitrary code execution the moment the policy source isn't fully
trusted (a config file, a DB row someone else can edit). Use a
restricted evaluator or a real policy engine (Cedar, OPA/Rego, XACML).

## 3. Resource-Level Authorization

**"How do you authorize access to one specific resource without hitting the DB on every check?"**

```python
def can_access(db, user_id: str, document_id: str, action: str) -> bool:
    doc = db.get_document(document_id)
    if doc is None:
        return False
    if doc.owner_id == user_id:
        return True
    return db.has_permission(document_id, user_id, action)  # explicit grant/ACL
```

**Answer:**

- Check ownership first (cheapest, most common case), then fall back
  to an explicit grant/ACL table.
- Cache the allow/deny decision with a short TTL, invalidated on ACL
  change rather than only expiring.
- Expose a bulk/batch decision endpoint for list views — a 50-row list
  shouldn't mean 50 authorization round-trips.

**Follow-up — "what if the permission changes mid-TTL?"** A stale-cache
window — keep TTL short, invalidate on write, and log every allow/deny
with actor/resource/action so a stale decision is at least auditable.

## 4. API Key Management and Scoping

**"How do you design an API key system so one leaked key doesn't hand out the keys to the kingdom?"**

```python
import secrets, hashlib

def create_api_key(scopes: list[str]) -> tuple[str, str]:
    key_id = secrets.token_urlsafe(16)
    secret = secrets.token_urlsafe(32)
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    store_api_key(key_id, secret_hash, scopes)  # only the hash is persisted
    return key_id, secret  # plaintext returned exactly once
```

**Answer:**

- Store only a hash of the secret, never the plaintext; show plaintext
  exactly once, at creation.
- Scope every key narrowly (read-only default, explicit expiration) —
  never an all-access key.
- Bind to IP ranges/service accounts where practical; monitor for
  anomalous volume or geography.
- Automate rotation; have a fast revoke-on-compromise path with a
  known blast radius per key.

---

## Code Samples

See [Authentication Patterns' Code Samples](authentication-patterns.md#code-samples)
— the JWT/OAuth2 examples there cover the claims and scopes this page's
authorization checks consume.
