---
title: "Build an Odoo App: The Step-by-Step Plan"
---

# Build an Odoo App: The Step-by-Step Plan

Reading about Odoo teaches the ideas. **Building one app teaches the
habits.** This page is the plan for building a small but real app, a
**Service Desk**, in 13 short steps. Each step adds one idea to the
same app, ends with a check you can see working, and points to the page
that explains the idea. The goal is to **learn Odoo properly**, not only
to pass an interview. The plan has three parts:

- Steps 1-13: the **core build**.
- Steps 14-20: **Phase 2**, how real Odoo apps are designed.
- Steps 21-26: **Phase 3**, the platform features most tutorials skip.

!!! note "Version"
    Written for **Odoo 20**. This page is a **plan**. It has no finished
    code on purpose: you write the code, and the linked pages explain
    each part.

## 1. "What are we building, and why this app?"

**Answer:**

- A **Service Desk**: a customer reports a problem, a technician fixes
  it, parts are used, and the customer is invoiced.
- Phase 2 adds what real Odoo apps have: a bridge module, real stock
  moves, an approval step, multi-company, a customer portal, and a scale
  test.
- It is small enough to hold in your head, and it touches most of Odoo:
  models, views, workflow, security, wizards, reports, scheduled jobs,
  inheritance, accounting, tests, and the external API.
- It connects to real Odoo apps (Contacts, Users, Products, Accounting),
  which shows how custom modules sit on top of core apps. See
  [Odoo Core Flow: Sales to Cash](core-apps/odoo-sales-to-cash-flow.md).
- Two models carry the app:
    - `service.ticket` — one customer problem.
    - `service.ticket.line` — one part or service used on a ticket.

## 2. "How should you work through the steps?"

**Answer:**

- **One step per sitting.** Stop when the check passes. Do not start the
  next step tired.
- **Commit to Git after every step.** Then a mistake costs you one step,
  not the whole app.
- **Do not skip the check.** Each step ends with something you can click
  or run. If it fails, fix it before moving on.
- **Read the linked page first** (10 minutes), then write the code. It is
  faster than writing first and reading when stuck.
- **Type the code, don't paste it.** Typing is what makes the names stick.
- **When you are stuck,** open the same feature in a core module such as
  `sale`, using the `20.0` branch of the Odoo source. Copy the pattern,
  not the text.
- **Use AI as a helper, not as the driver.** Let it explain an error or
  draft boilerplate. Then check names and syntax against the source of
  your version. See
  [Interviewing in the AI Era](../../interview-prep/interviewing-in-the-ai-era.md).

## 3. "What are the 13 core steps?"

**Answer:**

### Step 1: Setup

- **Goal:** a running Odoo 20 and an empty module you can install.
- **Do:**
    - Run Odoo 20 and its PostgreSQL database in Docker, with your module
      folder shared into the container.
    - Create the empty module with Odoo's scaffold command.
    - Turn on developer mode and install the module.
- **Check:** the module appears in Apps and installs without errors.
- **Read first:** [Odoo ORM & Recordsets](framework/odoo-orm-and-recordsets.md)
  (intro only).

### Step 2: The first model

- **Goal:** create and list tickets from the screen.
- **Do:**
    - Add `service.ticket` with a few simple fields (name, description,
      date).
    - Add a form view, a list view, a window action, and a menu.
- **Check:** you can create, edit, and delete a ticket from the menu.
- **Read first:**
  [Views, Actions & QWeb](framework/odoo-views-actions-and-qweb.md).

### Step 3: Relations

- **Goal:** tickets belong to people and carry parts.
- **Do:**
    - Add a customer (`Many2one` to `res.partner`) and a technician
      (`Many2one` to `res.users`).
    - Add tags (`Many2many`).
    - Add `service.ticket.line` and show the lines on the ticket
      (`One2many`).
- **Check:** a ticket shows its customer, technician, tags, and lines.
- **Read first:**
  [ORM §4: x2many fields](framework/odoo-orm-and-recordsets.md#4-how-do-you-write-one2many-and-many2many-fields).

### Step 4: Workflow and chatter

- **Goal:** a ticket moves through states and keeps a history.
- **Do:**
    - Add a `state` field: New, In Progress, Done.
    - Add buttons that move the state, a status bar, and the chatter.
- **Check:** the buttons change the state, and each change is logged in
  the chatter.
- **Read first:**
  [Views §3: form view](framework/odoo-views-actions-and-qweb.md#3-what-is-inside-a-form-view).

### Step 5: Computed fields and rules

- **Goal:** values that calculate themselves, and data that checks
  itself.
- **Do:**
    - Add a parts total (computed, stored).
    - Add an SLA (Service Level Agreement) deadline and an overdue flag.
    - Add a constraint, for example "quantity must be positive".
- **Check:** changing a line updates the total, and bad data is refused.
- **Read first:**
  [ORM §5: computed fields](framework/odoo-orm-and-recordsets.md#5-how-do-computed-fields-work-and-when-do-you-use-storetrue)
  and [§6: constraints](framework/odoo-orm-and-recordsets.md#6-what-is-the-difference-between-a-constraint-and-an-onchange).

### Step 6: Security

- **Goal:** the right people see the right tickets.
- **Do:**
    - Create three groups: User, Technician, Manager.
    - Write the access rows in `ir.access.csv`. Give each user only their
      own tickets with a domain, and add a company row.
- **Check:** log in as a normal user. You see only your tickets. Admin
  still sees all.
- **Read first:** [Odoo Security Model](framework/odoo-security.md).

### Step 7: A wizard

- **Goal:** a pop-up that closes a ticket with a note.
- **Do:**
    - Add a wizard model (a transient model) with a "resolution" field.
    - Add a button on the ticket that opens it and a confirm button that
      closes the ticket.
- **Check:** closing a ticket without the pop-up is not possible, and the
  note is saved on the ticket.
- **Read first:**
  [Inheritance §4: abstract and transient models](framework/odoo-inheritance.md#4-what-are-abstract-models-and-mixins).

### Step 8: Report and email

- **Goal:** a PDF for the customer and an email when the ticket is done.
- **Do:**
    - Add a PDF report with a QWeb template.
    - Add an email template and send it from the close step.
- **Check:** you can print the PDF, and the email shows in the chatter.
- **Read first:**
  [Views §7: QWeb](framework/odoo-views-actions-and-qweb.md#7-what-is-qweb-and-what-are-its-main-directives).

### Step 9: A scheduled action

- **Goal:** overdue tickets escalate by themselves.
- **Do:**
    - Add a method that finds overdue open tickets and raises their
      priority.
    - Register it as a scheduled action (cron).
- **Check:** run the action by hand from the UI and see the priority
  change.
- **Read first:**
  [Performance §3](framework/odoo-performance-and-testing.md#3-what-else-makes-odoo-slow)
  (why bulk work in one `write` matters).

### Step 10: Extend a core app

- **Goal:** tickets show up on the customer form.
- **Do:**
    - Extend `res.partner` with `_inherit` and add a ticket count.
    - Add a smart button on the partner form with an inherited view.
- **Check:** open a customer, see the count, click through to the
  tickets.
- **Read first:**
  [Odoo Inheritance & Customization](framework/odoo-inheritance.md).

### Step 11: Invoice from a ticket

- **Goal:** bill the parts and service from the ticket.
- **Do:**
    - Add a button that builds a draft customer invoice from the ticket
      lines, then posts it.
    - Keep the invoice values in a separate `_prepare_invoice` method,
      like core modules do.
- **Check:** the invoice shows the same total as the ticket, and the
  ticket links to it.
- **Read first:**
  [Odoo Accounting Internals](core-apps/odoo-accounting-internals.md#6-how-do-you-create-an-invoice-from-code).

### Step 12: Tests

- **Goal:** protect the app from your own future changes.
- **Do:**
    - Test the workflow and the computed total with `TransactionCase`.
    - Test the wizard with `Form`.
    - Test security as a normal user.
    - Add a query-count test for the ticket list.
- **Check:** the test run is green, and breaking a rule makes it red.
- **Read first:**
  [Performance & Testing §5](framework/odoo-performance-and-testing.md#5-what-are-the-main-test-classes).

### Step 13: The external API and an upgrade

- **Goal:** use the app from outside, and change it safely later.
- **Do:**
    - Create a ticket from a small script through the external API.
    - Rename one field and write a migration script for it.
- **Check:** the script creates a ticket you can see in the UI, and the
  renamed field keeps its old data after `-u`.
- **Read first:**
  [Upgrades & Migration Scripts](framework/odoo-upgrades-and-migrations.md).

## 4. "What is Phase 2, and when should you start it?"

**Answer:**

- Phase 2 is **optional**. Start it only after Step 13 works and is
  committed.
- Why it exists: Steps 1-13 prove you know the tools. Phase 2 proves you
  can design **the way Odoo itself is designed**.
- Each step still ends with a check. The same rules apply as before: one
  step per sitting, one commit per step.

### Step 14: Split into a core module and a bridge module

- **Goal:** `service_desk` works alone, and a second module adds stock.
- **Do:**
    - Keep tickets, lines, workflow, and security in `service_desk`.
    - Create `service_desk_stock`, which depends on `service_desk` and
      `stock`, and installs itself automatically when both are present.
    - In the core module, leave an empty hook method that is called when
      a ticket is done. The bridge will fill it.
- **Check:** install only the core module, and the app works without
  Inventory. Install Inventory, and the bridge appears.
- **Read first:**
  [Sales to Cash §1 and §2](core-apps/odoo-sales-to-cash-flow.md#1-how-do-the-three-apps-depend-on-each-other)
  (the same pattern between `sale` and `sale_stock`).

### Step 15: Use real stock moves for parts

- **Goal:** closing a ticket takes the parts out of stock.
- **Do:**
    - In the bridge, fill the hook so it creates a transfer (a picking) with
      one move per ticket line, from your warehouse to a virtual
      "consumption" location.
    - Validate it, and link the transfer to the ticket.
- **Check:** the on-hand quantity of the product goes down, and the
  ticket shows its transfer.
- **Read first:**
  [Inventory Internals §1 and §5](core-apps/odoo-inventory-internals.md#5-what-happens-when-a-delivery-is-validated).

### Step 16: An approval step

- **Goal:** expensive tickets need a manager before work starts.
- **Do:**
    - Add a `to approve` state. A ticket goes there when its total is
      above a limit you keep in a setting.
    - Add an approve button for managers only, and a method that decides
      whether approval is needed, so others can override it.
- **Check:** a technician cannot approve, a manager can, and cheap
  tickets skip the step.
- **Read first:**
  [Purchase to Pay §1](core-apps/odoo-purchase-to-pay-flow.md#1-what-does-a-purchase-order-look-like-in-code).

### Step 17: Multi-company and currency

- **Goal:** two companies share one database and never see each other's
  tickets.
- **Do:**
    - Add `company_id` to tickets and lines, with a sensible default.
    - Add a global access row that limits users to their companies.
    - Add a currency to the lines, and compute the ticket total in the
      company currency.
- **Check:** create two companies and two users. Each sees only their own
  company's tickets, and the totals are in the right currency.
- **Read first:**
  [Odoo Security Model §4](framework/odoo-security.md#4-how-does-multi-company-security-work).

### Step 18: A customer portal

- **Goal:** customers see and create their own tickets from a web page.
- **Do:**
    - Add a controller route that lists the customer's tickets.
    - Give the portal group a read access row with a domain, so a customer
      can only reach their own tickets.
    - Add a simple form to create a ticket, with CSRF protection on.
- **Check:** a portal user sees only their tickets. Changing the ticket id
  in the URL to someone else's gives an access error, not their data.
- **Read first:**
  [Odoo Security Model §6](framework/odoo-security.md#6-how-do-you-secure-http-controllers-and-raw-sql)
  and [Views §7: QWeb](framework/odoo-views-actions-and-qweb.md#7-what-is-qweb-and-what-are-its-main-directives).

### Step 19: A scale test

- **Goal:** find and fix a real performance problem.
- **Do:**
    - Write a script that creates about 100,000 tickets with lines.
    - Open the ticket list, count the queries, and find what is slow:
      an N+1 loop, a non-stored computed field, or a missing index.
    - Fix it, and add a query-count test so it cannot come back.
- **Check:** the list opens fast, and the test fails if you reintroduce the
  slow code.
- **Read first:**
  [Performance & Testing §1 to §4](framework/odoo-performance-and-testing.md#1-how-does-odoo-load-data-and-what-is-the-n1-problem).

### Step 20 (optional): A small custom widget in OWL

- **Goal:** one custom screen element, such as a coloured priority badge.
- **Do:**
    - Learn the basics of OWL (Odoo's JavaScript component framework) from
      the official tutorial for Odoo 20 first.
    - Build one small widget and use it on the ticket form or kanban card.
- **Check:** the widget shows on the screen and updates when the value
  changes.
- **Read first:**
  [Point of Sale Internals §6](core-apps/odoo-point-of-sale-internals.md#6-how-do-you-customize-pos)
  (how the browser side is customized by patching components).
- This step is a separate skill from the Python work. It is fine to skip
  it.

## 5. "What is Phase 3?"

**Answer:**

- Phase 3 covers the everyday Odoo features that the first two parts do not
  touch. They are small steps. Together they make the app feel like a
  real Odoo app.
- It is for learning, so there are no interview shortcuts. Do the steps
  in any order.

### Step 21: Ticket numbers with a sequence

- **Goal:** each ticket gets a number like `TCK/0001`.
- **Do:**
    - Define a sequence record (`ir.sequence`) in a data file.
    - Assign the next number when a ticket is created.
- **Check:** new tickets get consecutive numbers, and numbers are never
  reused after a delete.
- **Read first:**
  [Data Files, Sequences & Translations §3](framework/odoo-data-sequences-and-translations.md#3-what-is-a-sequence-and-how-do-you-use-it).

### Step 22: Email to ticket, and activities

- **Goal:** an email sent to a support address creates a ticket, and
  people get to-do reminders on tickets.
- **Do:**
    - Give the model an email alias, so incoming mail creates a record.
    - Add the activity feature, so users can schedule calls and follow-ups.
- **Check:** send a test email to the alias and see a new ticket. Schedule
  an activity and see it in your to-do list.
- **Read first:**
  [Mail, Chatter & Activities](framework/odoo-mail-chatter-and-activities.md)
  (§5 incoming email, §6 aliases, §7 activities).

### Step 23: Automated actions and server actions

- **Goal:** let a user add logic from the screen, without code.
- **Do:**
    - Create a server action that changes a field on selected tickets.
    - Create an automated rule that runs it when a ticket changes state.
- **Check:** change a ticket's state, and see the rule fire. Then do the
  same thing in Python and compare the two.
- **Read first:**
  [Automation & Server Actions](framework/odoo-automation-and-server-actions.md).
  Notice what each can and cannot do compared with code.

### Step 24: Reporting views

- **Goal:** statistics for managers.
- **Do:**
    - Add a pivot view and a graph view for tickets (by technician, by
      month, by state).
    - Add a calendar view for deadlines.
    - Add useful default filters and group-by options to the search view.
- **Check:** open the pivot, change the grouping, and see the numbers match
  the list view.
- **Read first:**
  [Views, Actions & QWeb §2](framework/odoo-views-actions-and-qweb.md#2-what-view-types-exist-and-what-does-each-do).

### Step 25: Demo data and translations

- **Goal:** the app ships with sample data and works in a second language.
- **Do:**
    - Add demo data files, loaded only when demo data is enabled.
    - Export the translatable terms, translate them into one language, and
      load them.
- **Check:** a database created with demo data shows sample tickets, and a
  user set to the second language sees translated labels.
- **Read first:**
  [Data Files, Sequences & Translations](framework/odoo-data-sequences-and-translations.md)
  (§1 demo data, §2 `noupdate`, §5 translations).

### Step 26: Configuration and deployment

- **Goal:** know how Odoo runs outside your laptop.
- **Do:**
    - Read and write an `odoo.conf` file: database settings, addons path,
      and logging.
    - Learn the main server settings: worker processes and memory limits.
    - Put a reverse proxy in front of Odoo, and run it from a
      production-style container setup.
- **Check:** start Odoo only from the config file, open it through the
  proxy, and see the logs.
- **Read first:**
  [Configuration & Deployment](framework/odoo-configuration-and-deployment.md).
  Performance work from Step 19 will make more sense after this.

## 6. "What is still not covered, even after Phase 3?"

**Answer:**

- Odoo is a very large product. No single practice app covers all of it.
  After the plan, deepen the areas you care about with this study list:
    - **Business apps:** Projects and Timesheets, HR, Website and
      eCommerce, and Manufacturing used for real (not only read).
    - **Money details:** taxes, pricelists, analytic accounting, and
      multi-step reconciliation.
    - **Frontend:** OWL in depth, website snippets, and the portal.
    - **Integration:** payment providers, shipping connectors, and
      webhooks.
    - **Operations:** backups, monitoring, upgrades of a large database.
- Existing pages that already go deep:
  [Core Apps Flow](core-apps/odoo-sales-to-cash-flow.md) for Sales,
  Purchase, Inventory, Manufacturing, Accounting, and POS.
- When you finish a part, pick one item from the list above and read the
  matching core module source, as you did in the Core Apps pages.

## 7. "How long will it take?"

**Answer:**

- About 1-2 hours per step if the page was read first.
- Steps 1-5 are the core. Stopping there is already a real result.
- Steps 6, 10, and 11 look best in an interview among the core steps.
- Phase 2 steps take longer, about 2-3 hours each. Steps 14, 15, and 19
  look best in a senior interview.
- Phase 3 steps are smaller, about 1-2 hours each.
- A relaxed pace of 2-3 steps a week: about 5 weeks for Steps 1-13, about
  3 more for Phase 2, and about 2-3 more for Phase 3.

## 8. "What do you get from finishing it?"

**Answer:**

- A working app you can show, with a Git history of 13 clean steps.
- A concrete answer to "tell me about an Odoo module you built":
    - What it does, and which core apps it connects to.
    - How you secured it and tested it.
    - What you would do differently on the next version.
- Real familiarity with the error messages you will meet at work.
- After Phase 3, an app that uses the platform the way real Odoo apps do:
  numbering, email, automation, reporting, translations, and deployment.
- After Phase 2, a project that shows **design judgement**: a bridge
  module, real stock moves, approval flow, multi-company, a portal, and a
  measured performance fix.

## 9. Interview Questions This Plan Prepares You For

**Design**

- "Walk me through a custom Odoo module you built." — expects models,
  workflow, security, and a connection to a core app, Steps 2-11.
- "How would you secure a model so users see only their own records?" —
  expects a group row with a domain, Step 6.
- "How would you extend the customer form without editing it?" —
  expects `_inherit` and an inherited view, Step 10.

**Senior design (Phase 2)**

- "How do you keep a module usable without Inventory, but integrated when
  it is installed?" — expects a core module plus a bridge module with
  `auto_install`, Step 14.
- "How should a custom module change stock?" — expects stock moves and
  pickings, never direct quant edits, Step 15.
- "How do you stop a portal user from reading another customer's
  ticket?" — expects an access row with a domain, not just a hidden menu,
  Step 18.
- "A list view is slow with 100,000 records. What do you do?" — expects
  measuring queries, finding N+1 or an unindexed field, and adding a
  query-count test, Step 19.

**Practice**

- "Create an invoice from a custom model." — expects `account.move`
  with invoice lines, then posting, Step 11.
- "How do you test an Odoo module?" — expects `TransactionCase`, `Form`,
  and a security test, Step 12.
- "You renamed a field. How do you keep the data?" — expects a `pre-`
  migration script, Step 13.

---

## Code Samples

No code samples yet — this page is the plan. When you build the app, put
it under `code_samples/odoo/service_desk/`, with one Git commit per
step. The pages linked in each step are the references.
