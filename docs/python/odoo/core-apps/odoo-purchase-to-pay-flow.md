---
title: "Odoo Core Flow: Purchase to Pay"
---

# Odoo Core Flow: Purchase to Pay

"Purchase to pay" is the mirror of
[Sales to Cash](odoo-sales-to-cash-flow.md): the company needs a
product, orders it from a vendor, receives it, gets a vendor bill, and
pays. It uses the same building blocks — a bridge module
(`purchase_stock`), a stock rule action (`_run_buy`), and the shared
`account.move` model — so once you know Sales to Cash, this page is
mostly about **what is different**: a purchase can be triggered
automatically by a stock need.

!!! note "Version"
    Written for **Odoo 20**, from the `20.0` branch of the official
    repository. Search for method names, because line numbers change.

## 1. "What does a purchase order look like in code?"

**Answer:**

- `purchase.order` has five states: `draft` (RFQ — Request For
  Quotation), `sent` (RFQ Sent), `to approve`, `purchase` (Purchase
  Order), and `cancel`.
- Compare with `sale.order`, which has no approval state. Purchase adds
  an optional **double validation** step.
- `button_confirm` is the Confirm button. It:
    1. Skips orders not in `draft` or `sent`.
    2. Checks for an error message and validates analytic distribution.
    3. If the user is allowed to approve (`_approval_allowed`), calls
       `button_approve`. Otherwise sets `to approve`.
- `button_approve` writes `state = 'purchase'` and the approval date,
  and may lock the order.
- **The same hook idea as Sales:** `purchase` stays pure, and
  `purchase_stock` overrides `button_approve` to call
  `_create_picking()` after the parent method. That is what creates the
  receipt.

## 2. "How does Inventory create a purchase automatically?"

**Answer:**

- The stock rule action `buy` runs `_run_buy`. This is the method that
  `stock.rule.run` dispatches to, as explained in
  [Odoo Inventory Internals](odoo-inventory-internals.md#2-how-does-a-sales-need-find-a-rule).
- Triggers: a sale of a product with the "Buy" route, a reordering rule
  (minimum stock), or a manufacturing order that lacks a component.
- `_run_buy` does this for each procurement:
    1. Finds the **vendor price** (`_select_seller`) on the product.
    2. If there is no vendor, it does **not** block the sale. It
       notifies the responsible user and falls back to make-to-stock.
       The exception is a reordering run, where it reports an error.
    3. Computes a **domain** that describes a matching open purchase
       order (same vendor, company, and so on).
- Then, for each group of procurements with the same domain:
    - If a matching **draft** PO exists, it reuses it, and adds the new
      origin to the PO's `origin` text.
    - If not, it **creates a new PO** with `_prepare_purchase_order`.
    - It then adds or updates a purchase order **line** for each
      product. If a candidate line exists (`_find_candidate`), the
      quantity is added to it instead of creating a duplicate line.
- Result: ten sales needing the same product from the same vendor can
  end up as **one PO with one line**.
- The PO is created as the superuser, unless a user triggered the
  replenishment manually. A salesperson usually has no purchase rights.

## 3. "What happens when a purchase order is approved?"

**Answer:**

- `purchase_stock` overrides `button_approve`:

    ```python
    def button_approve(self, force=False):
        self.order_line._set_date_promised()
        result = super().button_approve(force=force)
        self._create_picking()
        return result
    ```

- `_create_picking` builds a `stock.picking` (a receipt) with a move per
  purchase line. From there it is the normal stock flow: confirm,
  reserve, validate.
- Validating the receipt moves goods from the **Vendor** location to the
  warehouse. This is the moment the stock increases. See
  [Inventory Internals §5](odoo-inventory-internals.md#5-what-happens-when-a-delivery-is-validated).
- The received quantity is written back to the PO line, like the
  delivered quantity on a sales line.

## 4. "How does the vendor bill come in?"

**Answer:**

- `purchase.order.action_create_invoice` creates a vendor bill: an
  `account.move` with `move_type = 'in_invoice'`.
- Values come from `_prepare_invoice`, and lines from the PO lines,
  the same pattern as the sales invoice.
- Which quantity is billed depends on the product's **bill control**
  (ordered quantity or received quantity).
- Posting the bill, payment, and reconciliation are the same Accounting
  steps. See [Odoo Accounting Internals](odoo-accounting-internals.md).
- Vendor bills can also arrive by email, with the document import mixin
  that `account.move` inherits, without any purchase order at all.

## 5. "Can you trace one purchase end to end?"

**Answer:**

| Step | Who | Method | Result |
|---|---|---|---|
| 1. Need | `stock` | `stock.rule.run` | Rule with action `buy` found |
| 2. Order | `purchase_stock` | `_run_buy` | RFQ created or extended |
| 3. Confirm | `purchase` | `button_confirm` | `purchase` or `to approve` |
| 4. Approve | `purchase_stock` | `button_approve` | Receipt picking created |
| 5. Receive | `stock` | `button_validate` | Stock increases |
| 6. Bill | `purchase` | `action_create_invoice` | Draft vendor bill |
| 7. Post | `account` | `action_post` | Posted journal entry |

- Debug in order. "No PO was created" almost always means step 2:
  no vendor on the product, or the Buy route is missing.

## 6. "How do you customize this flow?"

**Answer:**

- Extend `purchase.order` with `_inherit` and override **hooks**:
  `_prepare_purchase_order` to add fields to a new PO, `_prepare_invoice`
  for the bill.
- To add a field that flows from a sale to its purchase, pass it in the
  procurement values and read it in `_prepare_purchase_order`.
- Add a custom approval rule by overriding `_approval_allowed`.
- Always call `super()`. The same chain also serves the other modules in
  the stack.
- Test with a normal user. The PO is created by the superuser, so
  permission bugs show only on the follow-up steps.

## 7. Interview Questions You're Likely to Get Asked

**Flow**

- "How does a sale trigger a purchase?" — expects the Buy route,
  `stock.rule.run`, then `_run_buy`,
  [§2](#2-how-does-inventory-create-a-purchase-automatically).
- "What creates the receipt?" — expects `purchase_stock`'s
  `button_approve` calling `_create_picking`,
  [§3](#3-what-happens-when-a-purchase-order-is-approved).
- "Two sales need the same product from one vendor. How many POs?" —
  expects one PO and a merged line,
  [§2](#2-how-does-inventory-create-a-purchase-automatically).

**Design**

- "Why does `purchase` not create the receipt itself?" — expects bridge
  modules keep apps independent,
  [§1](#1-what-does-a-purchase-order-look-like-in-code).
- "How would you add a second approval level?" — expects overriding
  `_approval_allowed`, [§6](#6-how-do-you-customize-this-flow).

---

## Code Samples

No dedicated code samples for this page — it is a guided reading of
real Odoo source. Files to open in the `20.0` branch:

- `addons/purchase/models/purchase_order.py` — `button_confirm`,
  `button_approve`, `action_create_invoice`
- `addons/purchase_stock/models/stock_rule.py` — `_run_buy`
- `addons/purchase_stock/models/purchase_order.py` — the
  `button_approve` override, `_create_picking`
