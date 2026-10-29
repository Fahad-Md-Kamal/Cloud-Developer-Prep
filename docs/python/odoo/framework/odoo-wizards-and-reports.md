---
title: Odoo Wizards & Reports
---

# Odoo Wizards & Reports

Two features turn a data model into something a business can use: a
**wizard** (a pop-up that asks the user a few questions and then does a
job) and a **report** (a printable document, usually a PDF). A wizard is
a model whose rows are temporary. A report is a QWeb template plus a
small action that says what to print. Learn these two and you can finish
most "the user needs a button that…" requests.

!!! note "Version"
    Written for **Odoo 20**, from `odoo/orm/models_transient.py` and the
    developer documentation on the `20.0` branch.

## 1. "What is a wizard?"

**Answer:**

- A wizard is a **`models.TransientModel`**. It looks like a normal model
  (fields, methods, a form view), but its rows are **temporary**.
- Why temporary: a wizard only collects input for one job (for example,
  "close these tickets with this note"). The input is not business data.
- Odoo cleans them up by itself. A scheduled **autovacuum**
  (`_transient_vacuum`) deletes old rows. It uses two limits: an age limit
  in hours (`_transient_max_hours`, from the `transient_age_limit` server
  option) and a count limit (`_transient_max_count`, from
  `osv_memory_count_limit`).
- Because rows disappear, **never keep data in a wizard that you need
  later.** Write the result to a real model.
- A wizard still needs a form view and a way to open it. The model is
  defined like this:

    ```python
    class TicketCloseWizard(models.TransientModel):
        _name = 'service.ticket.close.wizard'
        _description = 'Close Tickets'

        resolution = fields.Text(required=True)

        def action_confirm(self):
            tickets = self.env['service.ticket'].browse(
                self.env.context.get('active_ids', []))
            tickets.write({'state': 'done', 'resolution': self.resolution})
            return {'type': 'ir.actions.act_window_close'}
    ```

## 2. "How does a wizard open, and how does it know which records to work on?"

**Answer:**

- A wizard opens from an **action** with `target` set to `new`, which means
  "show the view in a dialog."
- The usual way is a button on the form or list:
    - A window action record with `res_model` set to the wizard and
      `target="new"`.
    - The button calls it with `type="action"`, or a Python method returns
      the same action as a dictionary.
- The action can also be **bound** to a model (`binding_model_id`), so it
  appears in the "Action" menu when the user selects rows in a list.
- The **context** carries the selection: `active_model`, `active_ids`, and
  `active_id` tell the wizard which records the user selected.
  The confirm method reads `self.env.context['active_ids']`, as in the code
  above.
- To pre-fill fields from that context, override `default_get`.
- After the job, return `{'type': 'ir.actions.act_window_close'}` to close
  the dialog, or return another action to open the next screen.
- A wizard that works on many records must handle a **set** of records.
  Do the work with one `write` on the recordset where you can. See
  [Odoo ORM & Recordsets](odoo-orm-and-recordsets.md#2-how-do-you-search-create-update-and-delete-records).

## 3. "How do you design a good wizard?"

**Answer:**

- **One job per wizard.** A wizard that does three things becomes hard to
  test and explain.
- **Validate before you act.** Check the selected records are in the right
  state, and raise a `UserError` with a clear message if not.
- **Put the real logic on the business model.** The wizard method calls
  something like `tickets.action_close(note)`. Then other code and tests
  can reuse it without a wizard.
- **Test it as a normal user, not only as admin.** Rights problems with
  wizards show up only for ordinary users. See
  [Odoo Security Model](odoo-security.md).
- **Keep the result visible.** Post a message in the chatter of each
  changed record, so there is a trace. See
  [Odoo Mail, Chatter & Activities](odoo-mail-chatter-and-activities.md).

## 4. "How is a report built?"

```xml
<record id="action_report_ticket" model="ir.actions.report">
    <field name="name">Ticket</field>
    <field name="model">service.ticket</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">service_desk.report_ticket</field>
    <field name="binding_model_id" ref="model_service_ticket"/>
</record>

<template id="report_ticket">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="o">
            <t t-call="web.external_layout">
                <div class="page">
                    <h2>Ticket <span t-field="o.name"/></h2>
                    <p>Customer: <span t-field="o.partner_id"/></p>
                </div>
            </t>
        </t>
    </t>
</template>
```

**Answer:**

- A report has **two parts**:
    1. A **report action** (`ir.actions.report`): what to print and how.
    2. A **QWeb template**: the layout of the document. See
       [Odoo Views, Actions & QWeb §7](odoo-views-actions-and-qweb.md#7-what-is-qweb-and-what-are-its-main-directives).
- Main fields of the action:

| Field | Meaning |
|---|---|
| `model` | The model the report is about |
| `report_type` | `qweb-pdf` (default) or `qweb-html` |
| `report_name` | The id of the QWeb template to render |
| `print_report_name` | A Python expression for the file name |
| `binding_model_id` | Shows the report in the **Print** menu of that model |
| `paperformat_id` | Paper size and margins (the company format if empty) |
| `groups_id` | Which groups may use it |
| `attachment_use` | Generate once, then reuse the stored PDF |

- The template id **must match** `report_name`. Here, `service_desk.report_ticket`.
- The template receives these variables: `docs` (the records),
  `doc_ids`, `doc_model`, plus `user`, `res_company`, `time`,
  `web_base_url`, and `context_timestamp` (converts UTC to the user's
  time zone).
- `web.html_container` wraps the page. `web.external_layout` adds the
  company header and footer. The PDF body is the content of
  `<div class="page">`.
- The **PDF is made by wkhtmltopdf**, a tool that turns HTML into PDF. If
  PDFs come out without styles or fail, check that this tool is installed
  and that Odoo can reach its own web address from the server.
- Use `t-field` for dates, money, and selection labels, so they are
  formatted for the user's language.
- Bootstrap and FontAwesome classes can be used in a report template.
- Barcodes and QR codes are images from a controller:
  `<img t-att-src="'/report/barcode/QR/%s' % 'text'"/>`.
- `attachment_use` is for documents that must **not change** once printed
  (for legal reasons). Otherwise the report is rebuilt every time.

## 5. "How do you add data a template can't reach?"

```python
class TicketReport(models.AbstractModel):
    _name = 'report.service_desk.report_ticket'

    def _get_report_values(self, docids, data=None):
        docs = self.env['service.ticket'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'service.ticket',
            'docs': docs,
            'total_open': self.env['service.ticket'].search_count(
                [('state', '!=', 'done')]),
        }
```

**Answer:**

- By default the report passes only the selected records to the template.
- To pass more, create an **abstract model named
  `report.<module>.<report_name>`** with a `_get_report_values(docids, data)`
  method. Odoo looks for this model first.
- Returning your own dictionary **replaces** the defaults. If you still
  want `docs`, `doc_ids`, and `doc_model`, you must put them in yourself,
  as in the example.
- Use it for totals across records, data from other models, or heavy
  calculations that do not belong in the template.
- Keep logic here, in Python. A template full of `t-set` and loops is hard
  to read and to test.

## 6. "How do you print a report in the customer's language?"

**Answer:**

- Split the report into **two templates**: a main one, and a "document"
  template with the real layout.
- The main template calls the document with `t-lang`:

    ```xml
    <t t-call="service_desk.report_ticket_document"
       t-lang="o.partner_id.lang"/>
    ```

- In the document template, **re-browse the record in that language**:
  `o = o.with_context(lang=o.partner_id.lang)`. This is needed only if
  you print translatable fields, such as product or country names.
- `t-lang` works only on `t-call`, not on an ordinary element. To translate
  part of a document, move that part into its own template and call it.
- Do not re-browse when no translatable field is used. It costs time.

## 7. "What goes wrong with wizards and reports?"

**Answer:**

- **Wizard does nothing:** the context has no `active_ids` because it
  was opened some other way. Handle an empty selection with a clear
  message.
- **Data lost:** it was stored in a wizard and vacuumed. Move it to a real
  model.
- **Report is blank or fails:** the template id does not match
  `report_name`, or wkhtmltopdf is not available.
- **Report has no styles:** the server cannot load its own assets. Check
  the web base URL and `proxy_mode`. See
  [Odoo Configuration & Deployment](../operations/odoo-configuration-and-deployment.md).
- **Report is slow:** a query inside a loop in the template. Move the
  data to `_get_report_values`. See
  [Odoo Performance & Testing](odoo-performance-and-testing.md).
- **Wrong language:** the record was not re-browsed with the right
  context.

## 8. "Where does AI help here?"

**Answer:**

- Good for drafting a report template, the wizard form, and the
  `_get_report_values` method.
- It often forgets `web.html_container` or the `page` div, mismatches
  `report_name`, or omits `docs` from a custom report.
- Always print the real PDF and open the wizard as a normal user.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Wizards**

- "What is a transient model, and why use one for a wizard?" — expects
  temporary rows that are vacuumed, [§1](#1-what-is-a-wizard).
- "How does a wizard know which records the user selected?" — expects
  `active_ids` in the context, and `target="new"` to open as a dialog,
  [§2](#2-how-does-a-wizard-open-and-how-does-it-know-which-records-to-work-on).
- "Where should the business logic live?" — expects on the business
  model, not in the wizard,
  [§3](#3-how-do-you-design-a-good-wizard).

**Reports**

- "What are the two parts of a report?" — expects a report action and a
  QWeb template, linked by `report_name`,
  [§4](#4-how-is-a-report-built).
- "How do you add extra data to a report?" — expects the
  `report.<module>.<name>` abstract model with `_get_report_values`,
  [§5](#5-how-do-you-add-data-a-template-cant-reach).
- "How do you print each order in its customer's language?" — expects
  `t-lang` on a `t-call` plus re-browsing with the language,
  [§6](#6-how-do-you-print-a-report-in-the-customers-language).
- "What renders the PDF?" — expects wkhtmltopdf,
  [§4](#4-how-is-a-report-built).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative and assume a `service.ticket` model. Source to read in the
`20.0` branch:

- `odoo/orm/models_transient.py` — the vacuum rules
- `addons/sale/report/ir_actions_report.xml` and
  `addons/sale/report/ir_actions_report_templates.xml` — a real report
  action and its template
- The developer documentation chapters "QWeb Reports" and "Actions"
