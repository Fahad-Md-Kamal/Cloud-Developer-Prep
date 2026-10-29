---
title: Odoo Manufacturing Internals
---

# Odoo Manufacturing Internals

Manufacturing in Odoo is **stock moves again, with a recipe on top.** A
Bill of Materials (BoM) says "to make 1 table, consume 4 legs and 1
top." A Manufacturing Order (MO, model `mrp.production`) is the
instance of that recipe. Confirming an MO creates stock moves that
consume the components and produce the finished product. If you
understand [Inventory Internals](odoo-inventory-internals.md), almost
everything here is a variation.

!!! note "Version"
    Written for **Odoo 20**, from the `20.0` branch of the official
    repository. Search for method names, because line numbers change.

## 1. "How does Manufacturing connect to the rest?"

**Answer:**

- Same trigger as Purchase: a stock rule. The action is `manufacture`,
  and the method is `_run_manufacture` in the `mrp` module.
- A sale of a "Manufacture" product, a reordering rule, or another MO
  lacking a component can all trigger it.
- The result is an `mrp.production` record instead of a purchase order.
- Compare the three fulfilment actions:

| Action | Method | Creates |
|---|---|---|
| Pull from another location | `_run_pull` | A `stock.move` |
| Buy | `_run_buy` | A `purchase.order` line |
| Manufacture | `_run_manufacture` | An `mrp.production` |

- Adding a new way to fulfil a need means adding a rule action and a
  `_run_<action>` method. Manufacturing is the example to copy.

## 2. "What does `_run_manufacture` do?"

**Answer:**

- For each procurement it first skips **zero or negative** quantities.
  It never makes an MO for a negative amount.
- It finds the BoM with `_get_matching_bom`:
    - A BoM given in the procurement values wins.
    - Then the BoM on the reordering rule.
    - Then a search by product and operation type, with a fallback that
      ignores the operation type.
- It then looks for an **existing open MO** to reuse. The match needs the
  same BoM, product, operation type, company, and states `draft` or
  `confirmed`. It must also be unplanned and without an assigned user.
- If there is a match, it **adds the quantity** to that MO (through the
  quantity-change wizard model). If not, it prepares new MO values.
- If the BoM has a **batch size**, a large quantity is split into several
  MOs of that size.
- It creates the MOs as the superuser (unless a user triggered it
  manually), auto-confirms them when the rule says so, and then runs a
  post step.
- The idea is the same as the purchase merge: many needs can end up in
  one order.

## 3. "What happens when an MO is confirmed?"

```python
# addons/mrp/models/mrp_production.py  (simplified)
def action_confirm(self):
    ...
    moves_to_confirm._action_confirm(merge=False)
    workorder_to_confirm._action_confirm()
    self.move_raw_ids._trigger_scheduler()
    self.picking_ids.filtered(lambda p: p.state not in ('cancel', 'done')).action_confirm()
    self.filtered(lambda mo: mo.state == 'draft').state = 'confirmed'
```

**Answer:**

- An MO has two sets of moves:
    - `move_raw_ids` — the **components** to consume.
    - `move_finished_ids` — the **finished product** (and by-products) to
      produce.
- Confirming does these things:
    1. Confirms **all** those stock moves with the normal
       `_action_confirm` (without merging them).
    2. Confirms the **work orders**, the steps from the BoM routing.
    3. Runs `_trigger_scheduler` on the components. **If a component is
       short, this triggers new procurements**, which may create a
       purchase order or another MO for it.
    4. Confirms related pickings (for example a pick-components transfer).
    5. Moves the MO from `draft` to `confirmed`.
- Step 3 is what makes Odoo "multi-level": an MO for a table can start
  an MO for a leg, which can start a purchase of wood.

## 4. "What are the MO states?"

**Answer:**

- `mrp.production.state` has six values: `draft`, `confirmed`,
  `progress` (In Progress), `to_close`, `done`, and `cancel`.
- It is a **computed stored field** (`_compute_state`). You never set it
  by hand. It follows the moves, work orders, and produced quantity.
- A separate `reservation_state` says whether components are reserved:
  `confirmed` (Waiting), `assigned` (Ready), or `waiting` (Waiting
  Another Operation).
- Two different questions have two different fields:
    - "Where is the order in its life?" is `state`.
    - "Do I have the components?" is `reservation_state`.

## 5. "What does Mark as Done do?"

**Answer:**

- The button calls `button_mark_done`. It closes the MO, handles any
  **backorder** (a remainder not yet produced), and completes the stock
  moves.
- Completing the moves is the normal `_action_done`. The component
  quants **decrease** and the finished-product quant **increases**. This
  is the only moment the stock numbers change, as in
  [Inventory Internals §5](odoo-inventory-internals.md#5-what-happens-when-a-delivery-is-validated).
- Cost: the finished product's value comes from its components and work
  order costs. The cost logic lives in other modules that extend `mrp`
  (accounting bridges), the same way `stock_account` does for stock.

## 6. "How do you customize Manufacturing?"

**Answer:**

- Extend `mrp.production`, `mrp.bom`, or `stock.rule` with `_inherit`,
  and call `super()`.
- Hook methods exist for the common needs:
    - `_prepare_mo_vals` — add fields to a new MO.
    - `_get_custom_move_fields` — carry extra fields from a rule to its
      moves (`mrp` itself adds `bom_line_id` this way).
    - `_get_moves_raw_values` and `_get_moves_finished_values` — change
      the component and finished moves.
    - `_make_mo_get_domain` — change which open MOs can be reused.
- Do not edit stock quantities. Produce and consume through moves.
- Test the multi-level case: a component shortage that starts a
  purchase or a child MO. That is where bugs live.

## 7. "Where does AI help here?"

**Answer:**

- Good for drafting a BoM and routing data, and explaining
  `_run_manufacture` step by step.
- Weak at multi-level flows and costing. Have it show the exact method
  for each claim, then read it.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 8. Interview Questions You're Likely to Get Asked

**Concepts**

- "What is the difference between a BoM and an MO?" — expects recipe vs
  instance, [intro](#odoo-manufacturing-internals).
- "How does a sale of a made product start production?" — expects
  `stock.rule.run` and `_run_manufacture`,
  [§1](#1-how-does-manufacturing-connect-to-the-rest).

**Flow**

- "What does confirming an MO do?" — expects component and finished
  moves, work orders, and the scheduler trigger,
  [§3](#3-what-happens-when-an-mo-is-confirmed).
- "A component is out of stock. What happens?" — expects a procurement
  for it, possibly a purchase or a child MO,
  [§3](#3-what-happens-when-an-mo-is-confirmed).
- "Why are there two status fields on an MO?" — expects `state` vs
  `reservation_state`, [§4](#4-what-are-the-mo-states).

**Practice**

- "How do you add a field from the sale to the MO?" — expects the
  procurement values and `_prepare_mo_vals`,
  [§6](#6-how-do-you-customize-manufacturing).

---

## Code Samples

No dedicated code samples for this page — it is a guided reading of
real Odoo source. Files to open in the `20.0` branch:

- `addons/mrp/models/stock_rule.py` — `_run_manufacture`,
  `_get_matching_bom`, `_prepare_mo_vals`
- `addons/mrp/models/mrp_production.py` — `action_confirm`,
  `button_mark_done`, `_compute_state`
- `addons/mrp/models/mrp_bom.py` — the BoM model
