---
title: Odoo Inventory Internals
---

# Odoo Inventory Internals

Inventory in Odoo is built on one idea: **stock is never edited
directly. It changes only when a stock move is completed.** A move says
"this much of this product goes from location A to location B." The
current stock you see on screen is the sum of all completed moves. This
page follows one move from request to done, using the real model and
method names.

!!! note "Version"
    Written for **Odoo 20**, from the `20.0` branch of the official
    repository. Search for method names, because line numbers change.

## 1. "What are the main Inventory models?"

**Answer:**

| Model | What it is |
|---|---|
| `stock.location` | A place: a warehouse, a shelf, a customer, a supplier, a virtual "inventory loss" |
| `stock.move` | A **plan**: move N units of a product from location A to B |
| `stock.move.line` | A **detail** of a move: which lot, which package, how much was really reserved or picked |
| `stock.picking` | A **document** (a transfer, such as a delivery order) that groups moves |
| `stock.quant` | A **current count**: how much of a product (lot, package) is in one location now |
| `stock.rule` | A rule that says how to fulfil a need: pull from a location, buy, or manufacture |

- The key split: **move = intent, quant = reality**.
- Moves are created and confirmed first. The quant changes only when the
  move is done.
- "Customer", "Supplier", and "Inventory adjustment" are also locations.
  That is how receipts, deliveries, and adjustments all use the same
  mechanism. There is no special "add stock" operation.

## 2. "How does a sales need find a rule?"

**Answer:**

- Sales builds a **procurement**: product, quantity, destination
  location, date, and extra values. It calls `stock.rule.run(...)`.
  See [Odoo Core Flow: Sales to Cash](odoo-sales-to-cash-flow.md#3-how-does-confirming-a-sale-create-a-delivery).
- `run` looks up a rule with `_get_rule(product, location, values)`. It
  searches the **routes** on the product, the product category, and the
  warehouse.
- If no rule matches, the user sees: "No rule has been found to
  replenish ... Verify the routes configuration on the product." This is
  the most common "nothing was delivered" cause.
- `run` then dispatches by the rule's **action**, using the name:
  `_run_pull`, `_run_buy`, or `_run_manufacture`.
    - If the method does not exist for the action, it logs an error.
    - Modules add their own actions by adding a `_run_<action>` method.
      This is how Purchase and Manufacturing plug in.
- `_run_pull` needs a source location on the rule. It builds the move
  values with `_get_stock_move_values`, creates the `stock.move` records
  (as superuser, because the salesperson may not have stock rights),
  and calls `_action_confirm()` on them.

## 3. "What states does a move go through?"

**Answer:**

- `stock.move` has seven states:

| State | Meaning |
|---|---|
| `draft` | Created, not confirmed |
| `waiting` | Waiting for another move to finish |
| `confirmed` | Confirmed, but the stock cannot be reserved yet |
| `partially_available` | Some stock reserved |
| `assigned` | All stock reserved ("Ready") |
| `done` | Finished, the quant has changed |
| `cancel` | Cancelled |

- `_action_confirm` only works on `draft` moves, and it decides the next
  state:
    - Move has a previous move (`move_orig_ids`): `waiting`.
    - `make_to_order` method: `waiting`, and a new procurement is created
      for the earlier step (for example, a purchase).
    - `mts_else_mto` ("make to stock, else to order"): `confirmed`, and a
      procurement is created for the missing part.
    - Otherwise: `confirmed`.
- The transfer (`stock.picking`) has its own state, but it is
  **computed from its moves** (`_compute_state`). You never set it by
  hand.

## 4. "What does reserving stock actually do?"

**Answer:**

- `_action_assign` reserves stock for a move. It does this by creating
  `stock.move.line` records. Each line says "take this much, from this
  quant (lot, package, location)."
- A move is `assigned` when the reserved quantities add up to the
  needed quantity. If less, it is `partially_available`.
- Reserving does **not** remove stock. It only marks part of the quant
  as reserved, so a second order cannot take it.
- The quant methods behind this: `_gather` finds quants (using the
  removal strategy such as FIFO — first in, first out) and
  `_update_reserved_quantity` marks them reserved.
- After reserving, **putaway rules** may change the destination
  location of the move.

## 5. "What happens when a delivery is validated?"

**Answer:**

- The user clicks Validate on the picking, which calls `button_validate`.
  It ends in the move's `_action_done`.
- `_action_done` does these things, in order:
    1. Confirms any move still in `draft`.
    2. Cancels moves with nothing picked (unless the move is an inventory
       adjustment).
    3. Creates a **backorder** for the remainder, unless told to cancel
       it. A partial delivery leaves a second picking for the rest.
    4. Calls `_action_done` on the move lines.
- The move lines then call the quant method `_update_available_quantity`
  for the source and destination locations. **This is the only moment
  the real stock numbers change.**
- The sale order line reads the done moves to compute its delivered
  quantity, which feeds invoicing.

## 6. "How do you debug an Inventory problem?"

**Answer:**

- Start from the picking, then the move, then the move lines, then the
  quant. The flow is always in that order.
- Common problems and checks:
    - **Nothing created:** check the product type is Goods, the routes,
      and the "no rule found" message.
    - **Stuck in Waiting:** a previous move is not done, or stock is not
      available. Check `move_orig_ids` and the quants.
    - **Reserved but not moving:** it is reserved, not done. Validate the
      picking.
    - **Wrong quantity on screen:** check completed moves and lines, not
      the quant first. The quant is the result.
- Developer mode shows the technical names of each field and state.

## 7. "How do you customize Inventory safely?"

**Answer:**

- Extend with `_inherit` on `stock.move`, `stock.picking`, or
  `stock.rule`, and call `super()`.
- Prefer small, existing extension methods over copying big ones:
  `_get_stock_move_values` and `_get_custom_move_fields` exist so you can
  add values to the moves a rule creates.
- Never write to `stock.quant` quantities directly. Always go through a
  move, or the move history and the real stock disagree.
- Add a new fulfilment type by adding a rule action and a
  `_run_<action>` method.
- Test with moves from creation to done, as a normal user. Rule runs use
  superuser, so permission bugs hide from admin tests.

## 8. "How does AI help with this?"

**Answer:**

- Good for explaining a method such as `_action_assign` line by line.
- Weak at stock logic spread across modules. Ask it to name the exact
  method and model for each claim, then check them in the source.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Concepts**

- "What is the difference between a stock move and a quant?" — expects
  intent vs current count, [§1](#1-what-are-the-main-inventory-models).
- "How can stock be added if there is no 'add stock' operation?" —
  expects a move from a virtual location, [§1](#1-what-are-the-main-inventory-models).

**Flow**

- "How does Odoo decide how to fulfil a need?" — expects routes, rules,
  and the `_run_<action>` dispatch,
  [§2](#2-how-does-a-sales-need-find-a-rule).
- "What does reserving do?" — expects move lines and reserved quantity,
  not a stock decrease,
  [§4](#4-what-does-reserving-stock-actually-do).
- "When does the real stock change?" — expects when move lines are done,
  [§5](#5-what-happens-when-a-delivery-is-validated).

**Practice**

- "Add a custom field that must follow from a rule to its move." —
  expects `_get_custom_move_fields`,
  [§7](#7-how-do-you-customize-inventory-safely).

---

## Code Samples

No dedicated code samples for this page — it is a guided reading of
real Odoo source. Files to open in the `20.0` branch:

- `addons/stock/models/stock_rule.py` — `run`, `_run_pull`, `_get_rule`
- `addons/stock/models/stock_move.py` — `_action_confirm`,
  `_action_assign`, `_action_done`
- `addons/stock/models/stock_quant.py` — `_gather`,
  `_update_available_quantity`, `_update_reserved_quantity`
- `addons/stock/models/stock_picking.py` — `button_validate`
