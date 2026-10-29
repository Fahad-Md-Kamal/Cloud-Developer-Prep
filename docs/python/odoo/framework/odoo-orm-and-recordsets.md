---
title: Odoo ORM & Recordsets
---

# Odoo ORM & Recordsets

In Odoo, a **model** is a Python class that maps to one PostgreSQL
table, and a **recordset** is an ordered set of records of one model.
Almost all Odoo code is "get a recordset, read or change it." The
Object-Relational Mapper (ORM) handles the SQL (Structured Query
Language) for you. Learn recordsets first and the rest of Odoo gets
much easier.

!!! note "Version"
    Written for **Odoo 20**. Where an older version differs, the page says so.

## 1. "What is a recordset, and how is it different from a Django QuerySet?"

```python
partners = self.env['res.partner'].search([('is_company', '=', True)])
partners.mapped('name')            # list of names
partners.filtered('active')        # new recordset
partners[0]                        # a recordset with one record
```

**Answer:**

- A recordset is always a **set**, even when it holds one record or none.
- Every ORM call returns one, and `self` inside a model method is one too.
- Unlike a Django QuerySet, it is **not lazy**. `search` runs the query
  right away and returns real record ids.
- Field values are loaded on first access, then cached in the
  environment (see [§7](#7-what-is-the-environment-env-context-and-sudo)).
- Use `ensure_one()` when a method expects exactly one record. It raises
  an error if the set has zero or many.
- Useful helpers: `mapped`, `filtered`, `sorted`, `exists`, and
  set operations (`|`, `&`, `-`).

| Pros | Cons / Trade-offs |
|---|---|
| One API for one record and many, so batch code is natural | Reading a field on an empty or multi-record set raises an error |
| Records in the same set share one prefetch, which avoids many queries | Not lazy, so a wide `search` loads ids for every match |
| Set operations read cleanly (`a - b`) | Easy to forget `for rec in self` and write code that only works for one record |

## 2. "How do you search, create, update, and delete records?"

```python
Book = self.env['library.book']

books = Book.search([('state', '=', 'available')], order='title', limit=20)
count = Book.search_count([('state', '=', 'available')])

book = Book.create({'title': 'Dune', 'isbn': '978-0441013593'})
book.write({'state': 'borrowed'})
book.unlink()
```

**Answer:**

- `search(domain, offset, limit, order)` returns a recordset.
- `browse(ids)` builds a recordset from known ids. It runs no query.
- `create(vals)` makes a record. It takes a dictionary of field values.
- `write(vals)` updates **every** record in the set in one go.
- `unlink()` deletes the records.
- Prefer one `write` on a recordset over a loop of single writes. It is
  one SQL `UPDATE`, not many.
- To create many records, pass a list of dictionaries. `create` takes a
  list, and overrides use `@api.model_create_multi` so they handle
  batches.

## 3. "How do domains work?"

```python
domain = ['|', ('state', '=', 'draft'), ('user_id', '=', self.env.uid),
          ('amount', '>', 100)]
```

**Answer:**

- A domain is a list of conditions: `(field, operator, value)`.
- Conditions are joined with **AND** by default.
- `|` (OR) and `!` (NOT) are **prefix** operators. They apply to the next
  one or two conditions, not to the whole list.
- In the example above, `|` covers the first two conditions, and the
  third is still ANDed.
- Common operators: `=`, `!=`, `in`, `like`, `ilike`, `>`, `child_of`.
- You can follow relations with dots: `('partner_id.country_id.code', '=', 'BD')`.
- The same domain format is used in `search`, access rights, view filters,
  and actions.

## 4. "How do you write One2many and Many2many fields?"

```python
from odoo import Command

order.write({
    'line_ids': [
        Command.create({'product_id': 1, 'qty': 2}),
        Command.update(line.id, {'qty': 5}),
        Command.delete(old_line.id),
        Command.link(existing_id),
    ],
})
```

**Answer:**

- You do not assign a list of ids. You pass a list of **commands**.
- Main commands:
    - `create` — make a new related record.
    - `update` — change one related record.
    - `delete` — remove the record from the database.
    - `unlink` — remove the link only, keep the record.
    - `link` — add a link to an existing record.
    - `set` — replace all links with a given list of ids.
- `Many2one` is simpler. Assign an id, or a one-record recordset.

## 5. "How do computed fields work, and when do you use `store=True`?"

```python
total = fields.Float(compute='_compute_total', store=True)

@api.depends('line_ids.price', 'line_ids.qty')
def _compute_total(self):
    for order in self:
        order.total = sum(l.price * l.qty for l in order.line_ids)
```

**Answer:**

- A computed field is a field whose value comes from a method.
- `@api.depends` lists the fields it reads. Odoo uses that list to know
  **when to recompute**.
- The method must assign a value for **every** record in `self`, so
  always loop with `for rec in self`.
- **Non-stored** (default): computed on read, held in the cache only.
  You cannot search or group by it, unless you add a `search` method.
- **Stored** (`store=True`): saved in the database. You can search, sort,
  and group by it.
- The price of storing: it recomputes whenever a dependency changes, so
  a wide dependency chain makes writes slower.

**Likely follow-up — "what goes wrong with a bad `@api.depends`?"**

- A missing dependency means the stored value goes stale. No error shows.
- This is the most common computed-field bug.

| Pros | Cons / Trade-offs |
|---|---|
| Logic lives in one place, and values stay in sync | Wrong `@api.depends` fails silently |
| Stored fields can be searched, sorted, and grouped | Stored fields add write cost and can cascade through many records |
| Non-stored fields cost no disk space | Non-stored fields cannot be used in a domain without extra work |

## 6. "What is the difference between a constraint and an onchange?"

**Answer:**

- **`@api.constrains`** runs on `create` and `write`, on the server, for
  every caller. Raise `ValidationError` to block bad data. This is real
  validation.
- **`@api.onchange`** runs only in the **form view**, while the user is
  typing. It updates other fields on screen.
- An `onchange` does **not** run when code calls `create` or `write`. Never
  rely on it for correctness.
- SQL constraints (unique, check) are enforced by PostgreSQL itself and
  are the strongest guarantee.
- In Odoo 20 you declare them as class attributes with
  `models.Constraint`:

    ```python
    _positive_price = models.Constraint(
        "CHECK (price >= 0)", "Price must be positive.")
    ```

- Before Odoo 19 this was the `_sql_constraints` list. Old modules
  still show it, so you will see both.

## 7. "What is the environment (`env`), context, and `sudo`?"

**Answer:**

- `self.env` carries four things: the database cursor, the current user,
  the **context** (a dictionary of flags such as language or timezone),
  and the record cache.
- `with_context(key=value)` returns a recordset with changed context.
  Records are never changed in place.
- `with_user(user)` runs as another user, and the access rights of that
  user apply.
- `sudo()` skips access rights, including their domains. See
  [Odoo Security](odoo-security.md) for why it is risky.
- Environments are cheap. Chaining `with_context` and `sudo` is normal.

## 8. "How do you use AI tools for ORM work?"

**Answer:**

- Good for drafting `search` and `write` code and for explaining core
  methods.
- Check the output for single-record assumptions (no `for rec in self`),
  `@api.depends` lists that miss a field, and calls that exist only in
  another Odoo version.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Recordsets**

- "What does `self` contain in a model method?" — expects a recordset
  that may hold zero, one, or many records,
  [§1](#1-what-is-a-recordset-and-how-is-it-different-from-a-django-queryset).
- "Why loop with `for rec in self`?" — expects that the method may be
  called on many records at once, [§5](#5-how-do-computed-fields-work-and-when-do-you-use-storetrue).

**Fields and logic**

- "Stored vs non-stored computed field?" — expects the search, sort,
  and write-cost trade-off, [§5](#5-how-do-computed-fields-work-and-when-do-you-use-storetrue).
- "Why can't you rely on `@api.onchange` for validation?" — expects that
  it only runs in the form UI, [§6](#6-what-is-the-difference-between-a-constraint-and-an-onchange).
- "How do you add a line to a One2many from code?" — expects
  `Command.create`, not a list of ids, [§4](#4-how-do-you-write-one2many-and-many2many-fields).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative and assume a module with a `library.book` model. Build
that module yourself to try them.
