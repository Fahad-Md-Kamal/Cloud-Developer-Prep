---
title: Odoo Data Files, Sequences & Translations
---

# Odoo Data Files, Sequences & Translations

Odoo apps ship **data**, not only code: menus, views, groups, email
templates, default records, numbering rules, and translated text. All of
it travels in the module as XML and CSV files, and is loaded into the
database when the module is installed or updated. Three questions come up
again and again: **what is loaded when**, **how does numbering work
(`ir.sequence`)**, and **how does text get translated**.

!!! note "Version"
    Written for **Odoo 20**, from `odoo/tools/convert.py`,
    `odoo/addons/base/models/ir_sequence.py`, and
    `odoo/modules/module.py` on the `20.0` branch.

## 1. "What does the manifest control?"

```python
{
    'name': 'Service Desk',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.access.csv',
        'data/sequence.xml',
        'views/ticket_views.xml',
    ],
    'demo': ['demo/ticket_demo.xml'],
}
```

**Answer:**

- `__manifest__.py` is a Python dictionary. Odoo fills in defaults for
  missing keys. Useful defaults: `version` is `1.0`, `installable` is
  `True`, `application` is `False`, `auto_install` is `False`, and
  `data` and `demo` are empty lists. A missing `license` becomes
  `LGPL-3`.
- `depends` decides **load order**. A module loads after everything it
  depends on.
- `data` lists the files loaded on **install and every update**.
- `demo` lists files loaded **only when demo data is enabled** for the
  database.
- **File order matters.** Files load top to bottom, and a file can only
  refer to records that exist already. Put security and data first, views
  after, and menus last.
- Records that refer to others use `ref="module.xml_id"`. An XML id such
  as `service_desk.sequence_ticket` is how you name a record across
  files and modules.

## 2. "What does `noupdate` do?"

```xml
<odoo noupdate="1">
    <record id="sequence_ticket" model="ir.sequence">
        <field name="name">Service Ticket</field>
        <field name="code">service.ticket</field>
        <field name="prefix">TCK/</field>
        <field name="padding">4</field>
    </record>
</odoo>
```

**Answer:**

- Loading has two modes: **init** (install) and **update** (upgrade).
- With `noupdate="1"`, a record is created on install but **not
  overwritten on update**. The loader skips existing records in update
  mode.
- Why it exists: an administrator may edit that record after install (a
  sequence's next number, an email template's wording). An upgrade must
  not undo the change.
- The default for normal data is the opposite: **update mode overwrites**
  the record with the file's values. So views, menus, and actions are
  refreshed on every `-u`. This is why editing a view in the UI and then
  upgrading the module loses your edit.
- `forcecreate` defaults to true: even a `noupdate` record is **created**
  if it is missing at update time.
- Rule of thumb:
    - Code-owned data (views, menus, actions, groups): normal.
    - Customer-editable data (sequences, templates, settings): `noupdate`.
- See [Odoo Upgrades & Migration Scripts](odoo-upgrades-and-migrations.md)
  for where data loading sits in an upgrade.

## 3. "What is a sequence, and how do you use it?"

```python
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('service.ticket')
    return super().create(vals_list)
```

**Answer:**

- A sequence (`ir.sequence`) produces numbered strings such as
  `TCK/0001`. Its main fields:
    - `code` — the name you ask for in code.
    - `prefix` and `suffix` — text around the number.
    - `padding` — how many digits, filled with zeros.
    - `number_next` and `number_increment` — where it starts and the step.
    - `company_id` — a company-specific or shared sequence.
    - `use_date_range` — a separate counter per date range, such as one
      per year.
- Prefix and suffix can hold **date placeholders** such as `%(year)s`,
  `%(month)s`, and `%(day)s`. They are filled when the number is drawn.
- `next_by_code('service.ticket')` finds the sequence with that code. If
  several match (multi-company), **the one for the current company wins**,
  then the shared one. It returns `False` if none exists, so a missing
  sequence shows up as an empty name, not an error.
- Create the sequence record in a **data file** (with `noupdate`), and draw
  numbers in `create`. Do not compute numbers yourself with
  `search(...) + 1`. Two users saving at once get the same number.

## 4. "Standard or no-gap: what is the difference?"

**Answer:**

| Implementation | How it counts | Trade-off |
|---|---|---|
| `standard` (default) | A native PostgreSQL sequence | Fast, safe with many users. A rolled-back save **burns a number**, leaving a gap. |
| `no_gap` | An `UPDATE` on the sequence row | No number skipped by a rollback. Slower, because each save waits for the row lock. |

- A PostgreSQL sequence is **not transactional**. Once a number is
  handed out, a rollback does not return it. That is why `standard`
  numbers can skip.
- `no_gap` makes a save wait for the previous save to finish, so
  concurrent writers queue up. Use it only where the law or the business
  requires unbroken numbers, such as invoices in some countries.
- Even `no_gap` does not stop gaps if someone **deletes** a record.
- For tickets, `standard` is almost always right.

## 5. "How does translation work?"

**Answer:**

- **Python text:** wrap user-visible strings so they can be translated.
  Odoo 20 core uses `self.env._("text")`, and older code uses `_("text")`.
  Do not build the sentence by joining pieces. Use placeholders:
  `self.env._("Ticket %(name)s closed", name=ticket.name)`.
- **Field labels and help:** translated automatically from the `string` and
  `help` of your fields.
- **Field values:** add `translate=True` to a field (such as a product
  name) so each language can have its own value. Views are stored with
  translatable text, too.
- **Files:** translations live in `.po` files in the module's `i18n/`
  folder, one per language, and a `.pot` template with all terms.
- **Loading:** on install and on upgrade, Odoo updates translations for
  **all installed languages**. By default existing translations are kept.
  The server option `--i18n-overwrite` replaces them with the file's text.
- **Workflow:**
    1. Export the terms of your module (the `.pot`, or a language `.po`).
    2. Translate the empty entries.
    3. Put the file in `i18n/`, and upgrade the module.
    4. Switch a test user to that language and check the screens.
- Untranslated text shows in the source language, so a half-translated
  screen is normal while you work.

## 6. "What mistakes are common here?"

**Answer:**

- **Editing a view in the UI, then upgrading.** The upgrade overwrites it.
  Change views in code.
- **Missing `noupdate` on customer-editable data.** An upgrade resets the
  sequence or the template.
- **Wrong file order in `data`.** "External ID not found" means a file
  refers to a record that loads later.
- **Hand-made numbers** with `search_count + 1`. Use a sequence.
- **Strings joined from pieces**, which cannot be translated well.
- **Demo data referenced from real data.** Demo files may not load, so
  nothing real should depend on them.
- **Sequence code typo.** `next_by_code` returns `False` silently.

## 7. "Where does AI help here?"

**Answer:**

- Good for drafting data XML, a sequence record, and a first translation
  of a `.po` file.
- Risky for business terms. Have a native speaker review translations, and
  check the placeholders (`%(name)s`) were kept.
- Ask it to put customer-editable records under `noupdate`, then verify.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 8. Interview Questions You're Likely to Get Asked

**Data**

- "What does `noupdate="1"` do?" — expects: created on install, not
  overwritten on update, [§2](#2-what-does-noupdate-do).
- "Why did my view edit disappear after an upgrade?" — expects: view
  data is overwritten on update, [§2](#2-what-does-noupdate-do).
- "`data` vs `demo`?" — expects every install vs only with demo data,
  [§1](#1-what-does-the-manifest-control).

**Sequences**

- "How do you give each ticket a number safely?" — expects `ir.sequence`
  and `next_by_code`, [§3](#3-what-is-a-sequence-and-how-do-you-use-it).
- "Why are there gaps in my numbers?" — expects the non-transactional
  PostgreSQL sequence, [§4](#4-standard-or-no-gap-what-is-the-difference).
- "When would you choose `no_gap`?" — expects legal unbroken numbering
  and the cost of row locking,
  [§4](#4-standard-or-no-gap-what-is-the-difference).

**Translations**

- "How do you translate a module?" — expects `.pot`, `.po` in `i18n/`,
  then upgrade, [§5](#5-how-does-translation-work).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Source to read in the `20.0` branch:

- `odoo/addons/base/models/ir_sequence.py` — `next_by_code`,
  `_next_do`, the two implementations
- `odoo/tools/convert.py` — how `noupdate` and `forcecreate` are applied
- `odoo/modules/module.py` — the manifest defaults
