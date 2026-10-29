---
title: Odoo OWL & the Web Client
---

# Odoo OWL & the Web Client

Everything you see in the Odoo backend — menus, forms, lists, the chat
window — runs in the browser as JavaScript. That code is built with
**Owl**, a small component framework made by Odoo. Python gives the web
client its data and its view definitions. JavaScript decides how things
**look and behave on the screen**. When you need a screen element no
standard view offers (a coloured badge, a custom widget, a button in the
top bar), you write an Owl component and **register** it where the web
client looks for it. This page is the map: components, registries,
services, assets, and patching.

!!! note "Version"
    Written for **Odoo 20**, from the developer documentation on the
    `20.0` branch (frontend reference: Owl components, registries, assets,
    patching). The Owl documentation itself is the full reference for
    the framework.

## 1. "What is Owl, and what does a component look like?"

```javascript
import { Component, useState } from "@odoo/owl";

class Counter extends Component {
    static template = "service_desk.Counter";

    setup() {
        this.state = useState({ value: 1 });
    }

    increment() {
        this.state.value++;
    }
}
```

```xml
<templates xml:space="preserve">
    <t t-name="service_desk.Counter">
        <div t-on-click="increment">
            <t t-esc="state.value"/>
        </div>
    </t>
</templates>
```

**Answer:**

- **Owl** is a declarative component framework, loosely inspired by Vue and
  React. A component is a **JavaScript class** with a **QWeb template**.
- The template language is the same QWeb you know from
  [Odoo Views, Actions & QWeb §7](../framework/odoo-views-actions-and-qweb.md#7-what-is-qweb-and-what-are-its-main-directives),
  with extra Owl directives, such as `t-on-click` for events.
- **State** that should update the screen lives in `useState`. Change
  `this.state.value` and the template re-renders by itself.
- Odoo's rules:
    - Use **`setup()`**, never the constructor. Constructors cannot be
      overridden, and Odoo code must stay extensible.
    - Name templates **`addon_name.ComponentName`**, to avoid clashes
      between addons.
    - Put templates in an **XML file**, not inline in JavaScript, so they
      can be translated.
- A component usually has two or three files side by side: `.js`, `.xml`,
  and optionally `.scss`.
- Odoo uses one shared Owl version across its recent releases.

## 2. "How does your code get into the browser?"

```python
# __manifest__.py
'assets': {
    'web.assets_backend': [
        'service_desk/static/src/**/*',
    ],
},
```

**Answer:**

- Files are loaded through **asset bundles**. A bundle is a list of file
  paths, declared in the `assets` key of the manifest.
- Three file types: code (`.js`), style (`.css` or `.scss`), and
  templates (`.xml`).
- Important bundles:

| Bundle | For |
|---|---|
| `web.assets_backend` | The backend web client (forms, lists, menus) |
| `web.assets_frontend` | The public website, portal, and eCommerce |
| `web.assets_common` | Low-level code shared by several apps |
| `web.assets_unit_tests` | JavaScript tests and helpers |

- A file you forget to list **does not exist** for the browser. "My
  component is not showing" often means it is not in a bundle.
- Odoo joins and minifies the files of a bundle, and stores the result.
  Each file has a checksum in its URL, so the browser can cache it for a
  long time.
- Templates are different: the browser fetches them from the server
  (`/web/webclient/qweb/`) when it loads.
- While developing, use the **`debug=assets`** mode, so files are not
  minified and are easier to debug.
- Patterns (`**/*`) select many files at once. Order can matter, so rely on
  the bundle operations for that (`before`, `after`, `replace`, `remove`),
  not on file names.

## 3. "What are registries, and why are they the main extension point?"

```javascript
import { registry } from "@web/core/registry";

registry.category("fields").add("priority_badge", PriorityBadge);
```

**Answer:**

- A **registry** is an ordered key/value map. The web client looks up
  things in registries whenever it needs a definition: which component
  shows a field, which view to use, which action to run.
- To customize, you **add an entry** under the right key. You do not
  change the framework.
- Registries are grouped by **category**. Useful ones:

| Category | Holds |
|---|---|
| `fields` | Field widgets, the components that show or edit a field |
| `views` | View types |
| `services` | Long-lived services |
| `systray` | Components in the top bar |
| `user_menuitems` | Entries in the user menu |
| `main_components` | Components shown all the time |
| `formatters`, `parsers` | Functions that format and read values |

- `add(key, value)` throws an error if the key already exists. Use the
  `force` option only when you mean to replace.
- To use a custom field widget, register it in `fields`, then name it in
  the view: `<field name="priority" widget="priority_badge"/>`. This is
  the link between the Python/XML side and the JavaScript side.
- The shape of the entry that a field expects can differ between
  versions. Copy how a **core field of the same version** registers
  itself.

## 4. "What are services?"

**Answer:**

- A **service** is long-lived code that provides a feature, such as
  showing notifications or calling the server. Services form a small
  **dependency-injection** system: a service can declare which other
  services it needs.
- Components get a service with the `useService` hook:

    ```javascript
    setup() {
        this.notification = useService("notification");
    }
    ```

- Two you will use first: `notification` (a small message on screen) and
  the one that makes requests to the Odoo server.
- A service is registered in the `services` category and has a `start`
  method.
- Services and registries are the answer to "how do I reuse something
  across screens?"

## 5. "How do you change an existing component?"

```javascript
import { patch } from "@web/core/utils/patch";

patch(SomeComponent.prototype, {
    setup() {
        super.setup(...arguments);
        // extra behavior
    },
});
```

**Answer:**

- When a registry is not enough, you can **patch** code in place with
  `patch(objectOrPrototype, extension)` from `@web/core/utils/patch`.
- Inside a patched method you can call the original with the native
  `super` keyword, the same idea as `super()` in a Python override. See
  [Odoo Inheritance & Customization §2](../framework/odoo-inheritance.md#2-how-does-a-classic-extension-look-and-how-do-you-override-a-method).
- `patch` returns a function that removes the patch. It is useful in
  tests.
- Patching is **powerful and fragile**. You are changing code you do not
  own, so an Odoo upgrade can break it silently. Prefer, in order:
    1. A registry entry.
    2. An existing hook or extension point in the component.
    3. A patch.
- This is how the Point of Sale screen is customized. See
  [Odoo Point of Sale Internals](../core-apps/odoo-point-of-sale-internals.md#6-how-do-you-customize-pos).

## 6. "How do the Python and JavaScript sides connect?"

**Answer:**

- **Views and fields:** a view's XML names a widget. The JavaScript
  registry supplies the component.
- **Data:** the client asks the server for records and receives the field
  values the user may see. If a field is missing on screen, check Python
  access and the view first, then the component. See
  [Odoo Security Model](../framework/odoo-security.md).
- **Actions:** a button or menu runs an action from the server, and the
  client shows the result. See
  [Odoo Views, Actions & QWeb §1](../framework/odoo-views-actions-and-qweb.md#1-how-does-a-click-on-a-menu-become-a-screen).
- **Custom HTTP routes:** controllers marked `type='jsonrpc'` are the way
  your own JavaScript calls your own Python. They are not covered by the
  deprecation of the old external RPC endpoints. See
  [Odoo External API](odoo-external-api.md).
- **Translation:** text in templates is translated automatically. Text
  in JavaScript needs the translation function.

## 7. "How do you build your first widget without getting lost?"

**Answer:**

1. Pick a **core field widget** that is close to what you want, such as
   the badge field (`badge_field.js` and `badge_field.xml` under
   `addons/web/static/src/views/fields/badge/`). Read both files in the
   Odoo source of your version.
2. Copy its structure into your module, and rename it with your addon
   prefix.
3. Add the files to `web.assets_backend`.
4. Register it in the `fields` registry.
5. Use it in one form with `widget="..."`.
6. Reload with `debug=assets`, and read the browser console for errors.
- Do one small thing first, such as a coloured badge. Grow from there.
- Plan for the Owl documentation as your companion. This page only gives
  the Odoo-specific parts.

## 8. "What goes wrong in frontend work?"

**Answer:**

- **Nothing changes after editing:** the file is not in a bundle, the
  bundle is cached, or you did not use `debug=assets`.
- **Template not found:** the name does not match
  `addon_name.ComponentName`, or the XML file is not loaded.
- **Widget not used:** it is not in the `fields` registry, or the
  `widget` name in the view is different.
- **Works until an upgrade:** you patched internals. Move to a registry
  entry, or retest after every upgrade.
- **Constructor used instead of `setup`:** overrides and patches stop
  working.
- **Blank screen with an error in the console:** read it first. Most
  errors name the file and the line.

## 9. "Where does AI help here?"

**Answer:**

- Good for drafting a small component and its template, and explaining an
  Owl error.
- It often writes older Odoo JavaScript (legacy widgets, `odoo.define`),
  uses a constructor, or invents registry keys. Odoo's frontend changes
  often between versions.
- Always compare with a core component of **your** version.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 10. Interview Questions You're Likely to Get Asked

**Basics**

- "What is Owl?" — expects a component framework: a class plus a QWeb
  template, with `useState`,
  [§1](#1-what-is-owl-and-what-does-a-component-look-like).
- "Why `setup()` and not a constructor?" — expects constructors cannot
  be overridden, [§1](#1-what-is-owl-and-what-does-a-component-look-like).
- "My JavaScript file is not running. Why?" — expects it is missing from
  an asset bundle, [§2](#2-how-does-your-code-get-into-the-browser).

**Extension**

- "How would you add a custom widget for a field?" — expects a component
  registered in the `fields` registry, then `widget="..."` in the view,
  [§3](#3-what-are-registries-and-why-are-they-the-main-extension-point).
- "Registry or patch?" — expects registry first, patch last, because patches
  are fragile, [§5](#5-how-do-you-change-an-existing-component).
- "What is a service?" — expects long-lived code injected with
  `useService`, [§4](#4-what-are-services).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative. Read these before writing your own:

- The Owl repository and its documentation (tutorial and reference)
- The `web` module source in the `20.0` branch. A small, good first
  read is the badge field: `addons/web/static/src/views/fields/badge/badge_field.js`
  and `badge_field.xml`.
