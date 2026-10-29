---
title: Odoo Views, Actions & QWeb
---

# Odoo Views, Actions & QWeb

In Odoo, the screens are **data**, not code. A view is an XML document
stored in the database as an `ir.ui.view` record. A menu item points to
an **action**, the action points to a model and a list of view types, and
the browser asks the server for the matching view. QWeb is the template
language Odoo uses for the free-form parts: PDF reports, emails, website
pages, and kanban cards. Learn the chain "menu → action → view" first,
and everything on screen becomes traceable.

!!! note "Version"
    Written for **Odoo 20**, from the `20.0` branch of the official
    repository. Older tutorials use `<tree>` and `attrs=`. See
    [§4](#4-what-changed-in-the-view-syntax).

## 1. "How does a click on a menu become a screen?"

```xml
<record id="action_books" model="ir.actions.act_window">
    <field name="name">Books</field>
    <field name="res_model">library.book</field>
    <field name="view_mode">list,kanban,form</field>
</record>

<menuitem id="menu_books" name="Books"
          action="action_books" parent="menu_library_root" sequence="10"/>
```

**Answer:**

- A **menu item** (`ir.ui.menu`) points to an **action**.
- The most common action is `ir.actions.act_window` ("window action"). It
  says:
    - `res_model` — which model to show.
    - `view_mode` — which view types, in order. The first is the default,
      and the user can switch between the rest.
    - Optional `domain` (a fixed filter), `context` (default values and
      flags such as `search_default_x`), `search_view_id`, and `help`
      (the text for an empty list).
- The server then finds the best view for each type with `get_view`,
  applies all inheritance, and sends the result to the browser.
- If a menu shows nothing, check the chain in order: menu, action, model,
  then the user's access rights. See
  [Odoo Security Model](odoo-security.md).

## 2. "What view types exist, and what does each do?"

**Answer:**

- `ir.ui.view.type` in Odoo 20 has these values:

| Type | Shows |
|---|---|
| `list` | Rows in a table |
| `form` | One record, for reading and editing |
| `kanban` | Cards in columns |
| `search` | The search bar, filters, and group-by options |
| `pivot` | A pivot table |
| `graph` | Bar, line, or pie charts |
| `calendar` | Records on a calendar |
| `card` | A card layout |
| `qweb` | A QWeb template (not a screen by itself) |

- Other modules add more types. For example, the Sales action also lists
  `activity` in its `view_mode`.
- A model needs at least a form and a list view to be usable. Odoo can
  generate a default if you give none, but it is plain.
- The `search` view is separate. It defines the filters, but it does not
  show records.

## 3. "What is inside a form view?"

```xml
<form string="Book">
    <header>
        <button name="action_borrow" string="Borrow" type="object"
                invisible="state != 'available'"/>
        <field name="state" widget="statusbar"
               statusbar_visible="available,borrowed"/>
    </header>
    <sheet>
        <group>
            <field name="title"/>
            <field name="isbn" readonly="state == 'borrowed'"/>
        </group>
    </sheet>
    <chatter/>
</form>
```

**Answer:**

- `<header>` holds the action buttons and the **status bar**
  (`widget="statusbar"` on the state field).
- `<sheet>` is the white page with the fields. Inside it, `<group>`
  lays fields out in two columns, and `<notebook>` makes tabs.
- A **smart button** area is a `div` named `button_box` at the top of the
  sheet.
- `<chatter/>` adds the message log and activities. It only works if the
  model inherits `mail.thread`.
- A button has a `type`:
    - `object` calls a Python method of the model.
    - `action` opens another action.
- Each button's `name` must be a real method, or the click fails at
  runtime, not at install time.

## 4. "What changed in the view syntax?"

**Answer:**

- **Conditions are now plain expressions.** Core Odoo 20 views write
  `invisible="state != 'draft'"` and `readonly="state == 'borrowed'"`
  directly on the element. Older tutorials use `attrs="{'invisible': ...}"`
  and `states="..."`. Translate them when you copy.
- **List columns** use `column_invisible` to hide a whole column.
  `invisible` hides the value in a row only.
- **The list view tag is `<list>`.** Older tutorials call it `<tree>`.
- **Views are validated at install.** A field that does not exist, or a
  broken XML, stops the module from loading with a clear error.
- Rule of thumb: copy patterns from **core views of the same version**,
  not from blog posts.

## 5. "How does view inheritance work?"

```xml
<record id="book_form_extra" model="ir.ui.view">
    <field name="name">library.book.form.extra</field>
    <field name="model">library.book</field>
    <field name="inherit_id" ref="library.book_form"/>
    <field name="arch" type="xml">
        <field name="isbn" position="after">
            <field name="shelf"/>
        </field>
        <xpath expr="//header" position="inside">
            <button name="action_lost" string="Mark Lost" type="object"/>
        </xpath>
    </field>
</record>
```

**Answer:**

- A view with `inherit_id` is a **set of edits** to its parent, not a
  full view.
- It has a `mode`, with two values:
    - `extension` (default): the edits are applied to the parent whenever
      the parent is requested. This is the normal way to customize.
    - `primary`: a **new** view that starts from a fully resolved parent
      and then applies its edits. Use it to create a variant, such as a
      different form for one menu, without changing the original.
- To apply them, the server takes the closest primary view, then applies
  every extension in a depth-first order, then the next level of primary
  views and their children.
- Each edit finds its place with a field name or an `xpath`, and then
  uses a `position`:

| Position | Effect |
|---|---|
| `inside` (default) | Add at the end of the match |
| `after` / `before` | Add next to the match |
| `replace` | Replace the match (`mode="inner"` replaces only its content) |
| `attributes` | Change attributes with `<attribute name="..." add/remove>` |
| `move` | Move an existing element into the place (used inside a spec) |

- Core views also use the shorthand `<kanban position="attributes">`.
- If a spec cannot find its target, the view fails to load, and the
  error shows the spec. This is why view ids and element names must match
  the exact version you target.
- Put `groups="..."` on a field or button to hide it from other users.
  Setting groups on the whole `ir.ui.view` record limits the view itself.
- More about extending safely:
  [Odoo Inheritance & Customization §3](odoo-inheritance.md#3-how-do-you-change-an-existing-view).

## 6. "Why don't my XML changes show up?"

**Answer:**

- Views are loaded from the XML file into the database **when the module
  is installed or updated**. Editing the file alone does nothing.
- Fix one of:
    - Update the module (`-u my_module`).
    - Run in dev mode with `--dev=xml`, so the server reads the view from
      the file on each request.
- In the UI, developer mode lets you open and edit the current view
  record.
- If a user edited a view in the UI, the database copy can differ from
  the file. The `arch_fs` and `arch_prev` fields exist to reset or
  restore it. Prefer changing views in code, not in the UI, so they stay
  in Git.

## 7. "What is QWeb, and what are its main directives?"

```xml
<template id="ticket_cards">
    <t t-foreach="tickets" t-as="ticket">
        <div t-attf-class="card #{ticket.state}">
            <h3 t-out="ticket.name"/>
            <span t-if="ticket.priority == '1'">High</span>
            <span t-else="">Normal</span>
        </div>
    </t>
</template>
```

**Answer:**

- QWeb is Odoo's XML template language. A `<template>` is a view of
  type `qweb`. Its **directives** are attributes that start with `t-`.
- The main ones:

| Directive | Does |
|---|---|
| `t-if`, `t-elif`, `t-else` | Conditions |
| `t-foreach` with `t-as` | Loops |
| `t-set` with `t-value` | Defines a variable |
| `t-out` | Prints a value (safely escaped) |
| `t-field` | Prints a record field with its formatting, with `t-options` |
| `t-att-*`, `t-attf-*` | Sets an attribute from an expression or a format string |
| `t-call` | Includes another template |

- `t-out` is the current output directive. Older templates use `t-esc`.
  Treat `t-raw` as a warning sign, because it skips escaping.
- Use `t-field` for dates, money, and selection labels. It formats them
  for the user's language. `t-out` prints the raw value.
- QWeb **compiles** each template to Python code, with one compile method
  per directive. A template is not interpreted again for every request.
- Where it is used:
    - **PDF reports** (a report action plus a template, rendered to PDF by
      a separate tool).
    - **Emails**, **website pages**, and **portal pages**.
    - **Kanban cards**, inside the kanban view.

## 8. "How do you debug a view problem?"

**Answer:**

- **Module won't install, with a view error:** read the message. It names
  the view and the failing spec or field.
- **Field missing on screen:** check access groups on the field, then
  inheritance order, then whether another module hides it.
- **Button does nothing or errors:** the `name` must match a method on the
  model, and `type` must be right.
- **Change not visible:** see [§6](#6-why-dont-my-xml-changes-show-up).
- **Slow form or list:** non-stored computed fields and many `one2many`
  rows. See [Odoo Performance & Testing](odoo-performance-and-testing.md).

## 9. "Where does AI help here?"

**Answer:**

- Good for drafting a form, a list, and a kanban view for a model, and
  for converting old `attrs` and `<tree>` code.
- It often writes the old syntax, invents the id of a core view, or
  forgets `<chatter/>` needs `mail.thread`.
- Always check an inherited view's id and field names against the core
  source of your version.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Chain**

- "What links a menu to a screen?" — expects menu, window action, then
  `view_mode` and `get_view`,
  [§1](#1-how-does-a-click-on-a-menu-become-a-screen).

**Inheritance**

- "`primary` vs `extension` inherited view?" — expects edits applied to
  the parent vs a new variant view,
  [§5](#5-how-does-view-inheritance-work).
- "What happens if the xpath target does not exist?" — expects the view
  fails to load, [§5](#5-how-does-view-inheritance-work).

**Syntax and tooling**

- "How do you hide a field when state is draft?" — expects
  `invisible="state == 'draft'"` as an expression,
  [§4](#4-what-changed-in-the-view-syntax).
- "I edited the XML, nothing changed." — expects module update or
  `--dev=xml`, [§6](#6-why-dont-my-xml-changes-show-up).

**QWeb**

- "`t-out` vs `t-field`?" — expects raw value vs formatted field,
  [§7](#7-what-is-qweb-and-what-are-its-main-directives).
- "Why is `t-raw` risky?" — expects it skips escaping, so user text can
  inject HTML,
  [§7](#7-what-is-qweb-and-what-are-its-main-directives).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative and assume a `library.book` model. Real examples to read in
the `20.0` branch:

- `addons/sale/views/sale_order_views.xml` — list, kanban, form, and the
  window action
- `odoo/addons/base/models/ir_ui_view.py` — view types, `inherit_id`,
  `mode`
- `odoo/tools/template_inheritance.py` — how each `position` is applied
- `odoo/addons/base/models/ir_qweb.py` — the QWeb directives
