---
title: Odoo Security Model
---

# Odoo Security Model

Odoo checks access in **layers**, from coarse to fine: which menus and
buttons a user sees, which models and **records** they can touch
(access rights, each with an optional domain), and which fields they
can see. A feature that "works for admin and fails for everyone else"
is nearly always a missing layer.

!!! note "Version"
    Written for **Odoo 20**. In Odoo 20, record rules (`ir.rule`) and
    the old `ir.model.access` are merged into one model, `ir.access`.
    On Odoo 19 and earlier, the same ideas live in two places: an
    `ir.model.access.csv` file plus `ir.rule` records. The
    [§8 table](#8-what-changed-from-odoo-19-and-earlier) maps old to new.

## 1. "What are the layers of security in Odoo?"

**Answer:**

- **Groups** (`res.groups`) — named sets of users, such as "Sales / User".
  Everything else attaches to groups.
- **Access rights** (`ir.access`) — each row says: this **group** may do
  these **operations** on this **model**, optionally only for records that
  match a **domain**.
- **Field access** — `groups="..."` on a field hides it from everyone
  outside those groups.
- **UI visibility** — groups on menus, buttons, and views. This is
  cosmetic only. It does **not** protect the data by itself.

## 2. "How do you define access rights?"

```text
id,name,model_id,group_id/id,operation,domain
access_book_user,book user,library.book,base.group_user,r,
access_book_manager,book manager,library.book,library.group_manager,crud,
access_loan_own,own loans,library.loan,base.group_user,crud,"[('user_id', '=', user.id)]"
```

**Answer:**

- It is a CSV (comma-separated values) file named
  `security/ir.access.csv`, listed in the manifest `data`.
- Each row has:
    - `model_id` — the model it applies to.
    - `group_id/id` — the group that gets the access.
    - `operation` — a subset of the letters `crud` (create, read, update,
      delete).
    - `domain` — optional. Only records matching it are covered. Empty
      means all records of the model.
- In the example, normal users can only read books, managers can do
  everything, and each user can only work with their **own** loans.
- A domain can use `time`, `user`, `company_id`, and `company_ids`. For
  the domain syntax, see
  [Odoo ORM & Recordsets](odoo-orm-and-recordsets.md#3-how-do-domains-work).
- A model with no row is closed to normal users.

## 3. "How do access rights combine?"

**Answer:**

- **Group rows** (with a group) are **additive**. A user in two groups
  gets the **union** of what both groups allow.
- **Global rows** (empty `group_id`) apply to **every** user. They act
  as **restrictions**, and several of them **intersect** (AND). Each
  one can only narrow access.
- Global and group rows intersect too, so a global row can block access
  that a group row would grant.
- The final check is: every global row AND (any matching group row).
- Use a global row for hard limits like company separation. Use group
  rows to grant access.

## 4. "How does multi-company security work?"

```text
id,name,model_id,group_id/id,operation,domain
access_loan_company,company limit,library.loan,,crud,"[('company_id', 'in', company_ids)]"
```

**Answer:**

- A company-owned model has a `company_id` field.
- The row above has **no group**, so it is global. It limits everyone to
  records of the companies they have switched on.
- Forgetting this on a new model leaks data between companies.
- Also set `company_id` by default on create, or records land with no
  owner.

## 5. "What does `sudo()` do, and why is it dangerous?"

```python
partner = self.env['res.partner'].sudo().browse(partner_id)
```

**Answer:**

- `sudo()` returns a recordset that **skips access rights**, including
  their domains.
- It is the right tool for system work, such as a cron job writing to a
  log model.
- It is dangerous in user-facing code. A controller that calls
  `sudo()` on user input can leak or change anything.
- Safe habits:
    - Use `sudo()` on the **smallest** recordset, for the shortest time.
    - Check the user's right yourself first, then `sudo()` only the
      exact read or write.
    - Never pass user-supplied ids or domains straight into a `sudo()`
      call.

## 6. "How do you secure HTTP controllers and raw SQL?"

**Answer:**

- A route sets `auth='user'` (logged in), `auth='public'` (anyone, as the
  public user), or `auth='none'` (no database user). Pick the
  strictest one that works.
- Keep CSRF (Cross-Site Request Forgery) protection on for routes that
  change data.
- Raw SQL skips the ORM, so it also skips access rights. Always pass
  values as parameters: `cr.execute("... WHERE id = %s", (rec_id,))`.
  Never build SQL with f-strings. That is SQL injection.

## 7. "How do you debug 'user can't see a record'?"

**Answer:**

- Check in this order:
    1. **Group rows** — does a row exist for the user's group, with the
       right operation?
    2. **Domains** — does the row's domain hide the record?
    3. **Global rows** — does one narrow it, such as the company row?
    4. **Company** — is the right company switched on?
    5. **Field groups** — is only a field hidden, not the record?
    6. **UI** — is a view or menu limited to a group?
- Test by switching user (`with_user` in a test, or "impersonate" in
  developer mode). Do not test only as admin.

## 8. "What changed from Odoo 19 and earlier?"

**Answer:**

| Odoo 19 and earlier | Odoo 20 |
|---|---|
| `security/ir.model.access.csv` (model-level) | `security/ir.access.csv` (one file) |
| `ir.rule` records in XML (record-level) | A `domain` column on the same row |
| `perm_read`, `perm_write`, `perm_create`, `perm_unlink` columns | One `operation` column, such as `crud` |
| Global rule = a rule with no groups | Global row = empty `group_id` |

- The ideas stay the same: additive group access, global restrictions,
  domains with `user` and `company_ids`.
- When you read older tutorials or modules, translate them with this
  table.

## 9. Interview Questions You're Likely to Get Asked

**Layers**

- "Is hiding a button with `groups` secure?" — expects no: UI only, the
  server still needs real access rows,
  [§1](#1-what-are-the-layers-of-security-in-odoo).
- "A new model works for admin only. Why?" — expects a missing access
  row, [§2](#2-how-do-you-define-access-rights).

**Combining**

- "Two group rows apply to one user. Result?" — expects the union, and
  global rows intersect on top,
  [§3](#3-how-do-access-rights-combine).
- "How do you limit users to their own records?" — expects a domain on
  the access row, [§2](#2-how-do-you-define-access-rights).

**Safe code**

- "When is `sudo()` acceptable?" — expects system tasks, smallest scope,
  checks first, [§5](#5-what-does-sudo-do-and-why-is-it-dangerous).

**Versions**

- "Where did record rules go?" — expects: in Odoo 20 they are domains
  on `ir.access` rows, [§8](#8-what-changed-from-odoo-19-and-earlier).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Test every new model as a normal user, not only as
admin. Related: [Odoo Performance & Testing](odoo-performance-and-testing.md).
