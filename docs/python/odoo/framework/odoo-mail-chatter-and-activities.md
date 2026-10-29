---
title: Odoo Mail, Chatter & Activities
---

# Odoo Mail, Chatter & Activities

The **chatter** is the message log at the bottom of almost every Odoo
form. It is not a special screen. It is the visible part of one mixin,
`mail.thread`, which gives a model **messages, followers, change
tracking, and email in and out**. A second mixin, `mail.activity.mixin`,
adds **activities**: scheduled to-dos on a record. Add the mixins to your
model and you get all of this without writing the feature yourself.

!!! note "Version"
    Written for **Odoo 20**, from `addons/mail/models/` on the `20.0`
    branch. Search for method names, because line numbers change.

## 1. "What does `mail.thread` give a model?"

```python
class ServiceTicket(models.Model):
    _name = 'service.ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    state = fields.Selection([...], tracking=True)
```

```xml
<chatter/>
```

**Answer:**

- `mail.thread` is an **abstract model** (a mixin, no table of its own).
  It is the same idea as in
  [Odoo Inheritance & Customization §4](odoo-inheritance.md#4-what-are-abstract-models-and-mixins).
- Add it with `_inherit` and put `<chatter/>` in the form view. Without the
  mixin, `<chatter/>` has nothing to show.
- It gives the model:
    - **Messages** and notes, stored as `mail.message` records.
    - **Followers**: people who get notified about the record.
    - **Tracking**: automatic log lines when chosen fields change.
    - **Incoming and outgoing email** for the record.
- Posting needs rights on the document. The default is **write access**
  on the record (`_mail_post_access = 'write'`). A user who can only read
  a record cannot post on it.

## 2. "How does tracking work?"

**Answer:**

- Put `tracking=True` on a field. When a user changes it, Odoo writes a
  line in the chatter: "State: New → In Progress."
- Core models such as `sale.order` pass a number (`tracking=3`) instead
  of `True`. Read `mail_thread.py` for exactly what the number controls.
- It is stored with the message, so the history stays even if the data
  changes again.
- Track only fields that matter. Every tracked change creates a message,
  and a model with many tracked fields makes the chatter noisy and
  writes slower.
- To skip tracking in code (for a bulk fix), use the context key
  `mail_notrack=True`. Odoo itself does this when it fills the alias
  field in the source.

## 3. "How do you post a message from code?"

```python
ticket.message_post(
    body="The part has arrived.",
    subject="Part arrived",
    partner_ids=[customer.id],
)
```

**Answer:**

- `message_post(...)` posts into the record's thread and returns the new
  `mail.message`.
- Main arguments:
    - `body` — plain text is escaped. Use `Markup` for HTML.
    - `subject`, `author_id` or `email_from`, `attachment_ids`.
    - `partner_ids` — extra people to notify, on top of the followers.
    - `subtype_xmlid` or `subtype_id` — the **type** of message.
- The **subtype** matters. Followers choose which subtypes they want to
  hear about. A message with a subtype that nobody follows still shows in
  the chatter, but sends no notification.
- `message_notify(...)` sends a notification to people **without**
  posting into the document's history.
- For a message with no email at all, check the message type and subtype
  first. Most "no email was sent" problems are subtype or follower
  settings, not code.

## 4. "How do followers and notifications work?"

**Answer:**

- A follower is a partner subscribed to a record, with a list of
  subtypes. Add one with `message_subscribe(partner_ids=...)`.
- After a message is posted, `_notify_thread` decides who is told and how:
    - **Inbox** — the notification list in the Odoo UI.
    - **Email** — a real outgoing email.
    - **Web push** — a browser notification.
- Each user chooses inbox or email in their preferences.
- Models often subscribe people automatically, for example the user
  assigned to a record. That is why people can get notifications they
  never asked for.

## 5. "How does an incoming email become a record?"

**Answer:**

- The mail server hands each incoming email to `message_process`. That
  calls `message_route`, which finds the **destination** in this order:
    1. **A reply to an existing thread.** If the email's `Message-Id`
       header matches a known message, it goes to that record.
    2. **An alias.** If a recipient address matches a `mail.alias`, use
       that alias's model, record, and default values.
    3. **A fallback** model, if one was provided.
    4. Otherwise, an error is raised, and the email is not delivered to
       any record.
- Then the route is processed:
    - A **new** thread calls `message_new(msg_dict, custom_values)`.
      The default creates a record, using the email **subject** as the
      record's name and the sender as its primary email.
    - An **existing** thread calls `message_update(msg_dict, update_vals)`.
- To control what happens, **override `message_new`**:

    ```python
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        custom_values = dict(custom_values or {}, description=msg_dict.get('body'))
        return super().message_new(msg_dict, custom_values)
    ```

- This is how a support address becomes tickets, and how replies from the
  customer land on the same ticket.

## 6. "How do aliases work on a model?"

**Answer:**

- A **mail alias** (`mail.alias`) is an email address such as
  `support@example.com` that points to a model.
- `mail.alias.mixin` gives each record of your model its own alias. It
  uses **delegation inheritance** (`_inherits`), so `alias_id` is a
  required link to a `mail.alias` row. See
  [Odoo Inheritance & Customization §1](odoo-inheritance.md#1-what-are-the-three-kinds-of-model-inheritance).
- The alias fields (`alias_name`, `alias_defaults`) then appear on your
  record. `alias_defaults` supplies default values for records created
  by incoming email.
- The model should have a primary email field (`_primary_email`, default
  `email`), so the sender can be stored on the new record.
- Only some models need a record-level alias. Many apps use **one** alias
  per team or per project, not one per ticket.
- A mail server must deliver mail to Odoo (a catch-all or a fetch setup).
  Without it, aliases exist but nothing arrives.

## 7. "What are activities, and how do you schedule one?"

```python
ticket.activity_schedule(
    'mail.mail_activity_data_todo',
    date_deadline=fields.Date.today() + timedelta(days=2),
    summary="Call the customer",
    user_id=technician.id,
)
```

**Answer:**

- An activity is a **to-do tied to a record**, with a deadline and an
  assigned user. It shows in the user's activity list and on the record.
- The model is `mail.activity`. Its main fields:
    - `res_model` and `res_id` — the record it belongs to.
    - `activity_type_id` — the kind (call, email, to-do).
    - `summary`, `user_id`, and a **required** `date_deadline`.
    - `state` — computed from the deadline: overdue, today, or planned.
    - `automated` — true when code created it, not a person.
- Add `mail.activity.mixin` to the model to get these methods:
    - `activity_schedule(...)` — create activities.
    - `activity_reschedule(...)` — change the date or the user.
    - `activity_feedback(...)` — mark them done, with a note.
    - `activity_unlink(...)` — delete them.
- `feedback`, `reschedule`, and `unlink` act **only on automated
  activities** by default (`only_automated=True`). A person's manual
  to-do is not closed by your code unless you ask for it.
- The context key `mail_activity_automation_skip` skips scheduling. Use it
  in a bulk script so you do not create thousands of activities.
- Typical use: schedule a follow-up when a ticket is created, and close it
  with `activity_feedback` when the ticket is done.

## 8. "How do you customize and debug mail behavior?"

**Answer:**

- **Customize:** override `message_new` for incoming mail, add tracked
  fields, and add your own subtypes for notifications people can opt in
  or out of.
- **No chatter on the form:** the model is missing `mail.thread`.
- **No notification:** check the subtype, the follower's subtypes, and the
  user's notification preference.
- **Email never created a record:** check the alias, the mail server
  setup, the model's primary email, and the logs of `message_route`.
- **Too many messages:** too many tracked fields, or scripts posting in a
  loop. Use `mail_notrack` for bulk work.
- **Rights errors when posting:** the user needs write access on the
  record. See [Odoo Security Model](odoo-security.md).

## 9. "Where does AI help here?"

**Answer:**

- Good for drafting `message_new` overrides and explaining the routing
  rules in plain words.
- Weak on mail server setup and on which subtype ids exist in your
  version. Ask it to name the source method, then check it.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Basics**

- "How do you add a chatter to a model?" — expects `mail.thread` in
  `_inherit` plus `<chatter/>` in the form,
  [§1](#1-what-does-mailthread-give-a-model).
- "How do you log field changes automatically?" — expects
  `tracking=True`, [§2](#2-how-does-tracking-work).

**Email**

- "How does an incoming email become a record?" — expects alias routing
  and `message_new`, [§5](#5-how-does-an-incoming-email-become-a-record).
- "A customer replies to an automatic email. Where does it go?" —
  expects the `Message-Id` match to the existing thread,
  [§5](#5-how-does-an-incoming-email-become-a-record).
- "How would you turn the email subject into a ticket title?" — expects
  the default `message_new`, or an override,
  [§5](#5-how-does-an-incoming-email-become-a-record).

**Activities**

- "How do you create a follow-up task from code?" — expects
  `activity_schedule`, [§7](#7-what-are-activities-and-how-do-you-schedule-one).
- "Why did my code not close the user's own to-do?" — expects
  `only_automated=True`,
  [§7](#7-what-are-activities-and-how-do-you-schedule-one).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Source to read in the `20.0` branch:

- `addons/mail/models/mail_thread.py` — `message_post`, `message_route`,
  `message_new`, `_notify_thread`
- `addons/mail/models/mail_activity_mixin.py` — `activity_schedule` and
  friends
- `addons/mail/models/mail_alias_mixin.py` — the alias mixin
