---
title: Odoo Upgrades & Migration Scripts
---

# Odoo Upgrades & Migration Scripts

When you update a module (`-u my_module`), Odoo changes the **database
structure and data** to match the new code. For most changes (a new
field, a new view) Odoo does it alone. For changes it cannot guess — a
renamed field, moved data, a new required column on existing rows — you
write a **migration script**, a small Python file that Odoo runs at a
fixed moment of the update. Knowing *when* each kind of script runs is
the whole skill.

!!! note "Version"
    Written for **Odoo 20**, from `odoo/modules/migration.py` and
    `odoo/modules/loading.py` on the `20.0` branch.

## 1. "What happens, in order, when a module is upgraded?"

**Answer:**

- For each module marked "to upgrade", the loader does these steps in
  this order:

| Step | What happens |
|---|---|
| 1 | **`pre-` migration scripts** run |
| 2 | The module's Python code is loaded |
| 3 | The models are loaded and the **database schema is updated** (new columns, constraints) |
| 4 | The module's **data files** (XML and CSV) are loaded in update mode |
| 5 | **`post-` migration scripts** run |
| 6 | Views of the module are validated |
| 7 | The module is marked `installed` and its `latest_version` is saved |
| 8 | After **all** modules are done, **`end-` scripts** run |

- Why this matters:
    - A `pre-` script runs **before** the schema change, so it sees the
      **old** columns. New fields do not exist yet.
    - A `post-` script runs **after** the schema and data changes, so it
      sees the **new** structure and the ORM works as expected.
    - An `end-` script runs after every module is upgraded, so it can
      rely on other modules being finished too.

## 2. "Where do the scripts go, and how are they chosen?"

```text
my_module/
`-- migrations/
    |-- 1.1/
    |   |-- pre-10-rename-isbn.py
    |   `-- post-10-fill-shelf.py
    `-- 0.0.0/
        `-- end-invariants.py
```

**Answer:**

- Scripts live in `<module>/migrations/<version>/`. Odoo 20 also reads
  `<module>/upgrades/` and any `odoo.upgrade` package on the server,
  which is how Odoo ships migrations for its own apps.
- The file name starts with `pre-`, `post-`, or `end-`. Anything else is
  ignored. A `README` in the folder is fine.
- Each file must define a function with exactly this signature:

    ```python
    def migrate(cr, version):
        ...
    ```

  Odoo checks the signature. Any other parameters raise an error.
- **Which version folders run?** Those with a version **above the
  installed version** and **up to the module's new manifest version**.
    - Bump `version` in `__manifest__.py`, or no script runs.
    - A short folder like `1.1` is read as `<server version>.1.1`, here
      `20.0.1.1`.
    - A short folder is **not** run again when you move to a new Odoo
      major version. A full folder such as `20.0.1.1` runs only on that
      server version.
- **Order inside a version:** files run sorted by **file name**. That is
  why people number them (`pre-10-...`, `pre-20-...`).
- **The `0.0.0` folder** runs on **every** version change. In the `pre`
  stage it runs **first**. In `post` and `end` it runs **last**.
- Scripts only run when the module is actually being upgraded
  (`-u my_module`), not on every server start.

## 3. "Which stage should a script use?"

**Answer:**

| Stage | Use it to | Tools |
|---|---|---|
| `pre-` | Rename a column or table, copy data out of a field that is about to change, fill a column before a new constraint | Raw SQL with `cr`. The ORM does not know the new fields yet. |
| `post-` | Fill new fields, create or fix records, convert data | The ORM, with a superuser environment |
| `end-` | Final cleanup or checks that need all modules upgraded | The ORM |

- Why `pre-` for a rename: if you only rename a field in Python, Odoo
  sees a new field and an old unused column. The old data stays behind
  and the new field is empty. A `pre-` script renames the **column** so
  the schema step finds it ready.
- Why `pre-` for a new required field on existing rows: the schema step
  cannot apply "not null" while rows are empty. Add the value first.
- Why `post-` for backfilling: the new column exists only after the
  schema step.
- Write scripts you can run twice safely. A failed upgrade is often
  re-run after a fix.

## 4. "What about install and uninstall hooks?"

**Answer:**

- Hooks are set in the manifest and run only at **install** (and
  uninstall), not on upgrade:
    - `pre_init_hook` — runs on install, **before** the module's models
      are created.
    - `post_init_hook` — runs on install, **after** the data is loaded.
    - `uninstall_hook` — runs on removal.
- A hook is a function in the module's `__init__.py` that receives the
  environment (`env`), not a cursor.
- Use a hook for **first-time setup** (for example, filling a new field
  for rows that already exist when the module is installed).
- Use a migration script for **changes between versions** of a module
  that is already installed.
- Mixing them up is a common mistake. A `post_init_hook` will not run
  when an existing installation is upgraded.

## 5. "What does a real migration look like?"

```python
# my_module/migrations/1.1/pre-10-rename-isbn.py
def migrate(cr, version):
    cr.execute("ALTER TABLE library_book RENAME COLUMN isbn13 TO isbn")
```

```python
# my_module/migrations/1.1/post-10-fill-shelf.py
from odoo import SUPERUSER_ID, api

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    books = env['library.book'].search([('shelf', '=', False)])
    books.write({'shelf': 'UNSORTED'})
```

**Answer:**

- The task: the field `isbn13` is renamed `isbn`, and a new `shelf` field
  must have a value on old books.
- The `pre-` script renames the column, so the data follows the new name.
- The `post-` script uses the ORM to set the new field, in one `write`
  on the whole recordset. See
  [Odoo ORM & Recordsets](../framework/odoo-orm-and-recordsets.md#2-how-do-you-search-create-update-and-delete-records).
- Steps to ship it:
    1. Change the Python field name.
    2. Bump `version` in the manifest, for example from `1.0` to `1.1`.
    3. Add the two scripts under `migrations/1.1/`.
- On a large table, prefer one SQL `UPDATE` to loading every record
  through the ORM. See
  [Odoo Performance & Testing](../framework/odoo-performance-and-testing.md).

## 6. "How do major-version upgrades differ?"

**Answer:**

- Odoo's **own apps** carry migration scripts for their data, which is
  what the `odoo.upgrade` path is for.
- **Your custom modules** are your job. Each one must be adapted to the
  new version's code **before** the database is upgraded, and may need
  its own scripts.
- Typical breakages between versions are syntax and API changes you have
  seen on other pages: view syntax, constraint syntax, security files,
  and renamed methods.
- Safe process:
    1. Restore a **copy** of the production database. Never test on the
       real one.
    2. Port the custom modules to the new version.
    3. Run the upgrade on the copy and fix errors.
    4. Test the business flows by hand and with automated tests.
    5. Repeat until it is clean, then schedule the real upgrade.
- Keep the number of custom modules and the amount of copied core code
  small. Both make every upgrade harder. See
  [Odoo Inheritance & Customization §5](../framework/odoo-inheritance.md#5-how-do-you-extend-without-breaking-upgrades).

## 7. "How do you test and debug an upgrade?"

**Answer:**

- Run it on a copy:

    ```bash
    odoo-bin -d copy_db -u my_module --stop-after-init
    ```

- Read the log. Each script prints a line like
  `module my_module: Running upgrade [>1.1] pre-10-rename-isbn`. The
  brackets show the stage: `[>x]` is pre, `[x>]` is post, `[$x]` is end.
- If a script did not run, check in this order:
    1. Was the manifest `version` bumped above the installed one?
    2. Is the folder name a valid version?
    3. Does the file name start with `pre-`, `post-`, or `end-`?
    4. Does it define `migrate(cr, version)` exactly?
    5. Was the module really upgraded (`-u`)?
- If a view fails to load after the upgrade, it is usually an inherited
  view whose target changed. See
  [Odoo Views, Actions & QWeb](../framework/odoo-views-actions-and-qweb.md#5-how-does-view-inheritance-work).
- Always take a backup first. A bad migration can destroy data.

## 8. "Where does AI help here?"

**Answer:**

- Good for drafting the SQL for a rename and for porting old view syntax.
- Risky for deciding the stage. Models often put a rename in `post-`,
  where it is too late.
- Ask it which stage a step belongs in and why, then compare with
  [§1](#1-what-happens-in-order-when-a-module-is-upgraded).
- Never run generated migration SQL on production without a test on a
  copy.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Order and stages**

- "When does a `pre-` script run compared to the schema update?" —
  expects before, so it sees the old columns,
  [§1](#1-what-happens-in-order-when-a-module-is-upgraded).
- "You renamed a field. How do you keep the data?" — expects a `pre-`
  script renaming the column,
  [§3](#3-which-stage-should-a-script-use).
- "What is an `end-` script for?" — expects work that needs every module
  upgraded, [§1](#1-what-happens-in-order-when-a-module-is-upgraded).

**Mechanics**

- "My migration script did not run. Why?" — expects manifest version,
  folder name, file prefix, and signature,
  [§7](#7-how-do-you-test-and-debug-an-upgrade).
- "What does the `0.0.0` folder do?" — expects runs on every version
  change, first in `pre` and last in `post` and `end`,
  [§2](#2-where-do-the-scripts-go-and-how-are-they-chosen).
- "`post_init_hook` vs a migration script?" — expects install-only vs
  version change, [§4](#4-what-about-install-and-uninstall-hooks).

**Process**

- "How would you upgrade a database with many custom modules?" — expects
  a copy, port first, test, repeat,
  [§6](#6-how-do-major-version-upgrades-differ).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Source to read in the `20.0` branch:

- `odoo/modules/migration.py` — `MigrationManager`, the version rules,
  the `migrate(cr, version)` check
- `odoo/modules/loading.py` — the exact order of pre, schema, data, post,
  hooks
