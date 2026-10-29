---
title: Odoo Accounting Internals
---

# Odoo Accounting Internals

Everything in Odoo Accounting is a **journal entry**: a document with
lines, where total debit equals total credit. A customer invoice, a
vendor bill, a payment, and a manual entry are all the same model,
`account.move`, with a different `move_type`. If you understand that one
model, the rest of Accounting is variations on it.

!!! note "Version"
    Written for **Odoo 20**, from the `20.0` branch of the official
    repository. Search for method names, because line numbers change.

## 1. "What is `account.move`, and why is an invoice one?"

**Answer:**

- `account.move` is one model for **all** accounting documents. The field
  `move_type` says which kind:

| `move_type` | Meaning |
|---|---|
| `entry` | Manual journal entry |
| `out_invoice` | Customer invoice |
| `out_refund` | Customer credit note |
| `in_invoice` | Vendor bill |
| `in_refund` | Vendor credit note |
| `out_receipt` / `in_receipt` | Sales / purchase receipt |

- It has only three states: `draft`, `posted`, and `cancel`.
- It also inherits the chatter (`mail.thread`), activities, and a
  sequence mixin for numbering. That is why every invoice has a message
  log and a number like `INV/2026/0001`.
- Sales sends its invoice as a `Command.create` list of lines. See
  [Odoo Core Flow: Sales to Cash](odoo-sales-to-cash-flow.md#4-how-does-an-order-become-an-invoice).

## 2. "What are journal items, and what is `invoice_line_ids`?"

**Answer:**

- `line_ids` are the **journal items** (`account.move.line`). They are
  the real accounting data: each line has an account, a debit, or a
  credit.
- `invoice_line_ids` is **a subset** of `line_ids`. It holds only the
  product lines a user types on the invoice.
- Odoo then **generates the other lines** for you:
    - Tax lines, from the taxes on the product lines.
    - A receivable (or payable) line for the total, with the customer.
- Example, a customer invoice for 100 plus 10% tax:

| Account | Debit | Credit |
|---|---|---|
| Receivable (customer) | 110 | |
| Revenue | | 100 |
| Tax payable | | 10 |

- The user sees one product line. The database holds three. That gap is
  the main thing that confuses new Odoo developers.

## 3. "How does Odoo guarantee the books balance?"

**Answer:**

- The rule: total debit must equal total credit on every move.
- `_check_balanced` enforces it. It runs on create and write, and
  raises "The entry is not balanced." if the totals differ.
- It compares sums **rounded to the currency's decimal places**, using a
  direct SQL query. It must not depend on computed fields, because the
  ORM may not have recomputed them yet.
- The source has a way to postpone the check while lines are built in
  several steps, then run it at the end (see `_check_balanced` and its
  `check_move_validity` handling).
- Takeaway: if you create `account.move.line` records in code, create
  them **together** with the move.

## 4. "What does posting do?"

**Answer:**

- `action_post` calls `_post(soft=True)`.
- Posting:
    - Gives the document its **number** from the journal sequence.
    - Checks the document is complete. Some fields are optional in draft
      and required after.
    - Moves it from `draft` to `posted`.
- `soft=True` means a document dated in the future is not posted now. It
  is scheduled to post automatically at its accounting date.
- If the journal uses a **hash** (a tamper-proof lock), some fields
  cannot change after posting.
- Posted documents are not edited. To fix a mistake, you reverse it with
  a credit note or a reversing entry. This is a core accounting rule that
  Odoo enforces in code.

## 5. "How do journals and the other core models fit?"

**Answer:**

| Model | Role |
|---|---|
| `account.journal` | A book that groups entries and numbers them (Sales, Purchases, Bank, Misc) |
| `account.account` | An account in the chart of accounts |
| `account.tax` | A tax rule that produces tax lines |
| `account.payment` | A payment, which creates its own journal entry |
| `account.partial.reconcile` | A link that marks a payment line against an invoice line |

- Every move belongs to a **journal**, and the journal decides the
  numbering and default accounts.
- **Reconciliation** matches a payment line with an invoice line on the
  receivable account. When the matched amounts cover the invoice, it is
  shown as paid.
- Note that "paid" is not a state on `account.move`. It is computed from
  reconciliation.

## 6. "How do you create an invoice from code?"

```python
move = self.env['account.move'].create({
    'move_type': 'out_invoice',
    'partner_id': partner.id,
    'invoice_line_ids': [Command.create({
        'name': 'Repair service',
        'quantity': 1,
        'price_unit': 100.0,
    })],
})
move.action_post()
```

**Answer:**

- Create the move with `move_type` and the **invoice lines only**. Odoo
  adds the tax and receivable lines.
- Call `action_post()` to number and finalize it.
- Do not create receivable or tax lines by hand unless you are sure
  about the accounting.
- Pass `partner_id`, and use the right company with
  `with_company(...)` when working in a multi-company setup.
- To bill from your own model, follow the Sales pattern: build the
  invoice values in a `_prepare_invoice` method and the lines in another,
  so other modules can extend them.

## 7. "What mistakes do developers make in Accounting code?"

**Answer:**

- **Editing posted entries.** Reverse them instead.
- **Creating lines one at a time** and hitting "not balanced."
- **Ignoring the currency.** Amounts are rounded by currency decimals, so
  `0.1 + 0.2` style float problems appear in tests.
- **Writing to journal items directly** to "fix" a number, which breaks
  the link to the source document.
- **Testing only as admin.** Accounting has its own groups. See
  [Odoo Security Model](../framework/odoo-security.md).

## 8. "How does AI help with this?"

**Answer:**

- Good for turning a business description into a draft invoice
  structure.
- Weak at tax and rounding details, and at version differences in field
  names. Check every generated field name against the `account.move`
  source.
- Accounting mistakes are expensive. Always add a test that posts the
  move and checks that debit equals credit.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Model**

- "Why are invoices and bills the same model?" — expects one
  `account.move` with `move_type`,
  [§1](#1-what-is-accountmove-and-why-is-an-invoice-one).
- "What is the difference between `line_ids` and `invoice_line_ids`?" —
  expects journal items vs the user's product lines,
  [§2](#2-what-are-journal-items-and-what-is-invoice_line_ids).

**Rules**

- "How does Odoo ensure debit equals credit?" — expects
  `_check_balanced` on create and write,
  [§3](#3-how-does-odoo-guarantee-the-books-balance).
- "How do you correct a posted invoice?" — expects a credit note or
  reversal, not an edit,
  [§4](#4-what-does-posting-do).
- "How does an invoice become 'paid'?" — expects reconciliation, not a
  state, [§5](#5-how-do-journals-and-the-other-core-models-fit).

**Practice**

- "Create an invoice from your custom model." — expects `account.move`
  with `invoice_line_ids`, then `action_post`,
  [§6](#6-how-do-you-create-an-invoice-from-code).

---

## Code Samples

No dedicated code samples for this page — it is a guided reading of
real Odoo source. Files to open in the `20.0` branch:

- `addons/account/models/account_move.py` — `_check_balanced`, `_post`,
  `action_post`
- `addons/sale/models/sale_order.py` — `_create_invoices`,
  `_prepare_invoice`
