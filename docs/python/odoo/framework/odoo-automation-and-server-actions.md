---
title: Odoo Automation & Server Actions
---

# Odoo Automation & Server Actions

A **server action** is a saved piece of logic: "update these fields,"
"create a record," "run this Python," or "call this URL." An
**automation rule** says **when** to run it: "when a ticket's state
becomes Done," or "three days after creation." Together they let a user
add behavior **from the screen, without a module**. The price is that
the logic lives in the database, not in Git, and it runs with high
rights. Knowing how it works tells you when to use it and when to write
Python instead.

!!! note "Version"
    Written for **Odoo 20**, from `addons/base_automation/` and
    `odoo/addons/base/models/ir_actions.py` on the `20.0` branch.

## 1. "What is the difference between a server action and an automation rule?"

**Answer:**

- **Server action** (`ir.actions.server`) — **what** to do. It lives in
  the base of Odoo, and it can also be a button, a menu entry, or a
  scheduled action.
- **Automation rule** (`base.automation`) — **when** to do it. It lives in
  the `base_automation` module. A rule holds a **trigger**, optional
  **filters**, and a list of server actions to run.
- One rule can run several actions, and one server action can be used
  from several places.
- The module depends on `mail` and `sms`, so rules can send emails and
  messages too. Other modules add more action types.

## 2. "What kinds of server action exist?"

**Answer:**

- The base types (`state` on `ir.actions.server`):

| Type | Does |
|---|---|
| `object_write` | Update fields of the record |
| `object_create` | Create a new record |
| `object_copy` | Duplicate a record |
| `code` | Run Python code |
| `webhook` | Send a notification to a URL |
| `multi` | Run several other actions in order |

- Other modules add types, such as sending an email or scheduling an
  activity.
- **Code actions** run through `safe_eval`, a restricted evaluator. The
  context offers things like `user`, `time`, `datetime`, `Command`, and a
  `log` helper, plus the records in question. It is **not** full Python:
  imports and many built-ins are blocked.
- A `multi` action runs its child actions in order, so you can combine
  steps.

## 3. "What triggers can an automation rule use?"

**Answer:**

- Triggers fall into groups:

| Group | Examples |
|---|---|
| Field changes | Stage set, user set, tag added, state set, priority set |
| Record life | On create, on create and edit, on archive, on unarchive, on deletion |
| Screen | On UI change (an onchange) |
| Time | Based on a date field, after creation, after last update |
| Messages | On incoming message, on outgoing message |
| External | On webhook |

- `on_write` still exists but is marked deprecated. Use "on create and
  edit."
- **Filters** narrow when a rule fires:
    - The **before** filter must match the record **before** the change.
    - The **after** filter must match **after** the change.
    - Together they express "went from X to Y."
- **Trigger fields** limit the rule to changes of chosen fields. With no
  trigger fields, any change counts.

## 4. "How does a rule run when someone saves a record?"

**Answer:**

- When Odoo starts, `base.automation._register_hook` **patches the
  models** that have rules. It wraps `create`, `write`, `unlink`, and the
  onchange method.
- Because the model itself is patched, the rule fires for changes made in
  the **UI, by other code, imports, and the API** alike. It is not a
  screen feature.
- For a save, the wrapper does this:
    1. Finds the rules for the model and trigger.
    2. Checks the **before** filter on the old records.
    3. Calls the **original** method.
    4. Checks the **after** filter on the result.
    5. Calls `_process`, which runs the actions.
- `_process`:
    - Skips records the rule has already run on in this call, using a
      marker in the context. **This stops infinite loops**, for example a
      rule that writes the field it watches.
    - Keeps only records where a watched field changed.
    - Runs each server action **as superuser** (`sudo`), once per record,
      with `active_id` and `active_ids` in the context.
    - Logs each run, with status and duration.
- If an action raises an error, the error propagates. The whole save
  **fails and rolls back**, and the user sees the message.
- **Time-based** rules do not use the patched methods. A scheduled job
  (`_cron_process_time_based_actions`) finds matching records and runs
  the rule.

## 5. "When should you use a rule, and when should you write code?"

**Answer:**

| Use an automation rule when | Use Python in a module when |
|---|---|
| An administrator should be able to change it later | It protects data correctness (an invariant) |
| It is simple: set a field, send an email, create a task | It has branches, loops, or needs tests |
| It is specific to one customer's setup | It belongs in every installation |
| You are prototyping | It must be in Git and survive upgrades |

- Rules run **with superuser rights**. A rule can change data the
  triggering user could not. Treat them as security-relevant.
- Rules are **hard to test and review**. They live in the database, so
  they are not in Git unless you export them as data.
- A rule adds a check to **every** create or write of its model. Many
  rules on a busy model cost time.
- Rules can **chain**: one rule's change triggers another. Keep them few
  and easy to explain.
- Rule of thumb: **correctness in code, configuration in rules.**

## 6. "How do you ship rules with a module?"

**Answer:**

- Define the rule and its server actions as **XML data** in your module,
  like any other record.
- Then they are in Git, installed with the module, and reviewed like code.
- For upgrades, decide whether the data should be overwritten on update
  or left alone, so a customer's changes are not lost. See
  [Odoo Upgrades & Migration Scripts](odoo-upgrades-and-migrations.md).
- Name rules clearly. The name appears in the logs and in the error
  messages.

## 7. "How do you debug an automation rule?"

**Answer:**

- **It did not fire:** check the trigger, the before and after filters,
  and the trigger fields. A filter that is too strict is the most common
  cause.
- **It fires too often or loops:** look at the trigger fields and at
  whether an action changes a field the rule watches.
- **Wrong user or rights:** actions run as superuser, so the difference
  is usually in what you expected, not in access errors.
- **Slow saves:** read the logs. Each run logs the rule name, status,
  number of records, and duration.
- **An error blocks the save:** the action failed. The message names the
  rule. Fix the action, or add a filter that skips the bad case.
- Compare with doing the same step in Python, as in Step 23 of the
  [App Build Plan](../build-an-odoo-app-plan.md).

## 8. "Where does AI help here?"

**Answer:**

- Good for drafting the Python of a code action and turning a business
  sentence into trigger and filter settings.
- Weak at the restricted `safe_eval` context. It may import modules or
  use names that do not exist there.
- Ask it to keep the code small, and test with real data on a copy.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Concepts**

- "Server action vs automation rule?" — expects what to do vs when to do
  it, [§1](#1-what-is-the-difference-between-a-server-action-and-an-automation-rule).
- "How does a rule fire when code writes a record, not the UI?" —
  expects patched `create`/`write`/`unlink` on the model,
  [§4](#4-how-does-a-rule-run-when-someone-saves-a-record).
- "How do rules avoid infinite loops?" — expects the per-record marker in
  the context, [§4](#4-how-does-a-rule-run-when-someone-saves-a-record).

**Judgement**

- "A client wants to change a business rule themselves. Rule or module?" —
  expects rule for configuration, code for invariants,
  [§5](#5-when-should-you-use-a-rule-and-when-should-you-write-code).
- "What is the risk of automation rules?" — expects superuser rights,
  hidden logic outside Git, and chains,
  [§5](#5-when-should-you-use-a-rule-and-when-should-you-write-code).

**Practice**

- "How do you express 'when state changes from draft to done'?" —
  expects before and after filters,
  [§3](#3-what-triggers-can-an-automation-rule-use).

---

## Code Samples

No dedicated code samples for this page — it is a guided reading of real
Odoo source. Files to open in the `20.0` branch:

- `addons/base_automation/models/base_automation.py` — `_register_hook`,
  `_process`, the trigger list
- `odoo/addons/base/models/ir_actions.py` — server action types and the
  code evaluation context
