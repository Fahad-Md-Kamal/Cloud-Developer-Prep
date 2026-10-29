---
title: Odoo Inheritance & Customization
---

# Odoo Inheritance & Customization

Odoo's rule for customizing: **never edit core files, extend them from
your own module.** Inheritance is how you do that. It works on three
layers — models (Python), views (XML), and data — and it is the most
common topic in Odoo interviews.

!!! note "Version"
    Written for **Odoo 20**. Core view ids and method names can change between major versions, so check them against the core source of your version.

## 1. "What are the three kinds of model inheritance?"

**Answer:**

- Odoo has three, and the difference is whether you get a **new table**
  and whether the data is **shared**.

| Kind | Syntax | Table | Use it when |
|---|---|---|---|
| Classic (extension) | `_inherit = 'res.partner'` | Same table | You add fields or change behavior of an existing model |
| Prototype (copy) | `_name = 'x'` plus `_inherit = 'res.partner'` | New table, copied fields | You want a new model that starts as a copy |
| Delegation | `_inherits = {'res.partner': 'partner_id'}` | New table plus a link to the parent | A new model "is a" partner and shares its fields |

- **Classic** is by far the most common. It changes the model itself, so
  every module sees your fields.
- **Prototype** copies the definition, not the data. The two models
  then live apart.
- **Delegation** uses a required `Many2one`. Fields of the parent show
  up on the child, but each lives in its own table. Example: `res.users`
  delegates to `res.partner`.

## 2. "How does a classic extension look, and how do you override a method?"

```python
class ResPartner(models.Model):
    _inherit = 'res.partner'

    loyalty_points = fields.Integer(default=0)

    def write(self, vals):
        if 'loyalty_points' in vals and vals['loyalty_points'] < 0:
            raise ValidationError("Points cannot be negative.")
        return super().write(vals)
```

**Answer:**

- No `_name` is needed. You are adding to the existing model.
- Add fields by declaring them. Change behavior by redefining a method
  and calling `super()`.
- **Always call `super()`** unless you are sure you want to replace the
  core logic. Skipping it breaks other modules that also extend it.
- Return the result of `super()` so callers get what they expect.

**Why this works — the mechanism:**

- Odoo builds the final model class by stacking every `_inherit` class
  from all installed modules, using Python's normal
  [Method Resolution Order](../../language-fundamentals/python-internals-and-advanced-oop.md).
- Module **load order** decides the stack. It follows the `depends`
  list in each `__manifest__.py`.
- That is why `depends` matters. If your module does not depend on the
  one you extend, load order is not guaranteed.

## 3. "How do you change an existing view?"

```xml
<record id="view_partner_form_loyalty" model="ir.ui.view">
    <field name="name">res.partner.form.loyalty</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='phone']" position="after">
            <field name="loyalty_points"/>
        </xpath>
    </field>
</record>
```

**Answer:**

- A new view record points to the original with `inherit_id`.
- `xpath` finds the spot (`expr` uses XPath, a query language for XML).
- `position` says what to do:
    - `before`, `after` — insert next to the match.
    - `inside` — insert as the last child.
    - `replace` — swap the match for your content.
    - `attributes` — change attributes only, such as `invisible`.
- Shortcut: `<field name="phone" position="after">` works when you
  target a field by name.
- Prefer `after`/`inside`/`attributes` over `replace`. A `replace`
  removes the element for **other** modules too and is the first thing
  to break on upgrade.

## 4. "What are abstract models and mixins?"

**Answer:**

- `models.AbstractModel` has **no table**. It holds shared fields and
  methods only.
- You mix it into real models with `_inherit = ['mail.thread', 'my.mixin']`.
- `mail.thread` is the best-known one. It adds the chatter (message log
  and followers) to any model.
- Use a mixin for behavior that several models share, such as an
  approval flow.
- `models.TransientModel` is different: a table whose rows are cleaned
  up automatically. Wizards use it.

## 5. "How do you extend without breaking upgrades?"

**Answer:**

- Put every change in your own module and extend with `_inherit`.
- Depend only on the modules you really need.
- Use `super()` and keep overrides small.
- Avoid `replace` in views, and avoid copying a core method just to
  change one line. Add a small hook-style method if you control it, or
  wrap with `super()` and adjust the result.
- Test on the next major version early. Core methods and view ids do
  change between versions.

## 6. "Where does AI help here?"

**Answer:**

- It drafts XPath and field additions quickly.
- It often picks the wrong `position`, invents view ids that do not
  exist, or forgets `super()`.
- Always check an inherited view id against the core module source.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 7. Interview Questions You're Likely to Get Asked

**Model inheritance**

- "`_inherit` vs `_inherits` vs `_name` plus `_inherit`?" — expects the
  table above: same table, linked tables, copied table,
  [§1](#1-what-are-the-three-kinds-of-model-inheritance).
- "Why must you call `super()` in an override?" — expects that other
  modules sit in the same chain, [§2](#2-how-does-a-classic-extension-look-and-how-do-you-override-a-method).
- "What decides which module's override runs first?" — expects module
  load order from `depends`, [§2](#2-how-does-a-classic-extension-look-and-how-do-you-override-a-method).

**Views**

- "How do you add a field to a core form without editing it?" — expects
  an inherited view with `xpath` and `position`,
  [§3](#3-how-do-you-change-an-existing-view).
- "Why avoid `position="replace"`?" — expects that it removes the
  element for other modules too and breaks on upgrade,
  [§3](#3-how-do-you-change-an-existing-view).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Read how core modules extend each other (for example how
`sale` extends `res.partner`) for real examples. Related:
[Odoo ORM & Recordsets](odoo-orm-and-recordsets.md).
