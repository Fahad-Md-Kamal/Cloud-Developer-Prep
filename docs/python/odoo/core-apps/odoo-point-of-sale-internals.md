---
title: Odoo Point of Sale Internals
---

# Odoo Point of Sale Internals

Point of Sale (POS) is different from the other core apps in one big
way: **the cashier's screen is a browser app that keeps working without
the server, and the books are written only when the shift is closed.**
Orders are sent to the server in the background, but the accounting
entries are created once, at the end of the session, as one combined
document. If you remember "orders sync now, accounting posts at close,"
the rest of POS follows from it.

!!! note "Version"
    Written for **Odoo 20**, from the `20.0` branch of the official
    repository. Search for method names, because line numbers change.

## 1. "What are the main POS models and modules?"

**Answer:**

| Model | What it is |
|---|---|
| `pos.config` | A shop or register setup (journals, payment methods, price list) |
| `pos.session` | One shift on one register, from opening to closing |
| `pos.order` | One sale made in a session |
| `pos.order.line` | A product line of an order |
| `pos.payment` | A payment on an order (cash, card, and so on) |

- `point_of_sale` depends on `account`, `product`, and a few helper
  modules. It does **not** depend on `sale` or `stock`.
- Stock is added by a bridge module, `pos_stock`. It depends on
  `point_of_sale` and `stock_account`, and installs itself automatically
  when both are present.
- This is the same bridge pattern as `sale_stock`. See
  [Sales to Cash §1](odoo-sales-to-cash-flow.md#1-how-do-the-three-apps-depend-on-each-other).
- The cashier screen is a JavaScript app. The server is the database and
  the accounting engine behind it.

## 2. "What states do sessions and orders have?"

**Answer:**

- `pos.session.state` has four values:

| State | Meaning |
|---|---|
| `opening_control` | Counting the cash before the first sale |
| `opened` | In Progress: sales are allowed |
| `closing_control` | Counting the cash at the end |
| `closed` | Closed and posted to accounting |

- `pos.order.state` has four values:

| State | Meaning |
|---|---|
| `draft` | New, still being edited |
| `paid` | Payment is complete |
| `done` | Posted in accounting |
| `cancel` | Cancelled |

- An order becomes `done` **only when its session is closed** (or it is
  invoiced). `paid` does not mean "in the books yet."

## 3. "How does an order get from the screen to the database?"

**Answer:**

- The browser calls `pos.order.sync_from_ui(orders)` with a list of
  order dictionaries. This is the main entry point.
- For each order:
    - **No existing order:** it is created through `_process_order`.
    - **Existing order in `draft`:** it is updated. This is how a draft
      saved earlier gets overwritten.
    - **Existing order in any other state:** the sync is **ignored**,
      with one exception for tips added after payment.
- Each order carries a `uuid`, made by the browser. The server uses it to
  find "the same order" again. That makes a repeated sync safe, which
  matters because a flaky connection retries.
- If the order arrives for a session that is already `closing_control` or
  `closed`, `_process_order` moves it to a valid open session.
- A refund can only refund products of **one** original order. More than
  one raises an error.
- After saving, the method returns the saved data to the browser, and
  tells the other devices on the same register to refresh.
- Because the browser works from its own copy, the cashier can keep
  selling while the connection is down. The orders sync when it returns.

## 4. "What happens when a session is closed?"

```python
# addons/point_of_sale/models/pos_session.py  (simplified)
def close_session_from_ui(self, payment_method_closing={}):
    if any(order.state == 'draft' for order in self.get_session_orders()):
        return {'status': False, 'type': 'draft_orders', ...}
    ...
    self._validate_session_accounting()
    self._handle_bank_payment_method_difference(payment_method_closing)
    self._handle_cash_statement_entries(payment_method_closing)
    ...
    self.write({'state': 'closed', 'stop_at': ...})
    self._get_closed_orders().write({'state': 'done'})
```

**Answer:**

- Closing is blocked while any **draft** order exists. This is the most
  common "I can't close the shift" cause.
- The docstring calls `_validate_session_accounting` the **only** entry
  point for creating the session's accounting entries.
- It splits the paid orders in two groups:
    - **Invoiced** orders already have a real customer invoice. They only
      need to be posted.
    - **Non-invoiced** orders (most retail sales) get **no invoice each**.
- The non-invoiced orders are combined into **one** `account.move` for
  sales (`out_invoice`) and **one** for refunds (`out_refund`):
    - It uses the register's closing journal.
    - The partner is the register's default customer.
    - Each order's `account_move` field points to that shared entry.
- Orders with all-zero quantities are skipped, because they have no
  financial effect.
- Then the payment differences (cash counted vs expected) are booked, the
  session becomes `closed`, and the orders become `done`.
- Result: 500 receipts in a day create **two** journal entries, not 500.
  See [Odoo Accounting Internals](odoo-accounting-internals.md).

## 5. "What if the customer wants an invoice?"

**Answer:**

- `action_pos_order_invoice` handles it.
- If the order already has a real customer invoice, it opens it.
- Otherwise it prepares the missing invoice (`_prepare_missing_invoice_moves`),
  which also handles the stock picking when `pos_stock` is installed.
- An invoiced order is **excluded** from the combined closing entry, so it
  is not counted twice.

## 6. "How do you customize POS?"

**Answer:**

- **Server side:** extend `pos.order`, `pos.session`, or `pos.config`
  with `_inherit`, and call `super()`.
    - The closing logic has hooks. For example,
      `_prepare_session_closing_extra_line_commands` is empty in
      `point_of_sale` and is **filled by `pos_stock`**. That is the hook
      pattern again.
    - What the browser may read is controlled by the `_load_pos_data_*`
      methods. Add a field there, or the screen cannot see it.
- **Browser side:** the screen is built with OWL (Odoo's JavaScript
  component framework). Custom behavior is added by patching its
  components in your own module. Plan for this as a separate skill from
  the Python work.
- Rules to keep:
    - Never post accounting entries per order. Let the session close do
      it.
    - Think "offline": the browser must work from data it already
      loaded.
    - Test the sync path (`sync_from_ui`) and the close path
      (`close_session_from_ui`), not only the screen.

## 7. "How do you debug a POS problem?"

**Answer:**

- **Can't close the shift:** look for a draft order in the session.
- **Order missing on the server:** check the sync log. `sync_from_ui`
  logs each order's start, creation, update, or ignore, with a
  synchronization number.
- **Order not in the books:** it is `paid`, not `done`. The session is
  still open.
- **Totals differ from the bank or cash:** read the closing step, which
  books payment differences.
- **A field is missing on the screen:** it is not in the data the browser
  loads.

## 8. "Where does AI help here?"

**Answer:**

- Good for explaining `sync_from_ui` or the closing flow step by step.
- Weak on the browser side, where internal names change often between
  versions. Have it quote the source, then read it.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Concepts**

- "When are POS accounting entries created?" — expects at session close,
  as combined entries, not per order,
  [§4](#4-what-happens-when-a-session-is-closed).
- "Why can POS work offline?" — expects the browser app syncs orders
  with `sync_from_ui` using client-made `uuid`s,
  [§3](#3-how-does-an-order-get-from-the-screen-to-the-database).
- "Why does `point_of_sale` not depend on `stock`?" — expects the bridge
  module `pos_stock`, [§1](#1-what-are-the-main-pos-models-and-modules).

**Practice**

- "A cashier can't close the register. Why?" — expects a draft order,
  [§4](#4-what-happens-when-a-session-is-closed).
- "A customer asks for an invoice after the sale." — expects
  `action_pos_order_invoice`, and exclusion from the closing entry,
  [§5](#5-what-if-the-customer-wants-an-invoice).
- "How do you add a custom field to the POS screen?" — expects server
  field plus the data-loading method, plus the browser patch,
  [§6](#6-how-do-you-customize-pos).

---

## Code Samples

No dedicated code samples for this page — it is a guided reading of
real Odoo source. Files to open in the `20.0` branch:

- `addons/point_of_sale/models/pos_order.py` — `sync_from_ui`,
  `_process_order`, `action_pos_order_invoice`
- `addons/point_of_sale/models/pos_session.py` —
  `close_session_from_ui`, `_validate_session_accounting`
- `addons/pos_stock/` — the stock bridge
