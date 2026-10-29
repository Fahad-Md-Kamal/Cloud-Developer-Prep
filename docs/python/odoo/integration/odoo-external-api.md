---
title: Odoo External API (JSON-2)
---

# Odoo External API (JSON-2)

Other software often needs Odoo's data: a website that creates tickets,
a script that exports invoices, a mobile app. For that, Odoo offers an
**external API**: you send an HTTP request, and a model method runs on the
server, with the same rights as the user behind your key. In Odoo 20 the
way to do this is **JSON-2**, added in Odoo 19. The older **XML-RPC and
JSON-RPC** endpoints are deprecated, and most tutorials online still teach
them. This page teaches the current way first, then what to do with old
code.

!!! note "Version"
    Written for **Odoo 20**, from the external API reference on the
    `20.0` branch of the documentation.

## 1. "How does a JSON-2 request look?"

```python
import requests

BASE_URL = "https://mycompany.example.com/json/2"
API_KEY = ...  # read it from a secure place, never hard-code it

headers = {
    "Authorization": f"bearer {API_KEY}",
    "X-Odoo-Database": "mycompany",
}

res = requests.post(
    f"{BASE_URL}/res.partner/search_read",
    headers=headers,
    json={
        "domain": [["name", "ilike", "%deco%"], ["is_company", "=", True]],
        "fields": ["name"],
    },
)
res.raise_for_status()
print(res.json())   # [{"id": 25, "name": "Deco Addict"}]
```

**Answer:**

- You **POST a JSON object** to `/json/2/<model>/<method>`.
- Headers:
    - `Authorization: bearer <API key>` — required.
    - `Content-Type: application/json` — required.
    - `X-Odoo-Database` — needed when the server hosts several databases
      and the database filter does not pick one from the host name.
    - `User-Agent` — recommended, the name of your software.
- The **body** holds the method's arguments **by name**:
    - `ids` — the records to run the method on. Leave it out for methods
      that work on the model as a whole (`@api.model` methods).
    - `context` — optional, for example `{"lang": "en_US"}`.
    - Any other key is a **parameter of the method**. For `search_read`
      these are `domain` and `fields`. For `create` the parameter is
      `vals_list`.
- Model methods are available, not only the basic ones. The
  documentation itself uses a business method, `action_confirm` on a sale
  order, as its example.
- On **success**: HTTP 200 and the method's return value as JSON.
- On **error**: HTTP 4xx or 5xx and a JSON object with `name` (the Python
  exception), `message`, `arguments`, `context`, and `debug` (the
  traceback, for developers).

## 2. "How do you get and manage an API key?"

**Answer:**

- A key replaces the password. Create one in the user's preferences,
  under Account Security, with a **description** and a **duration**.
- Rules from the documentation:
    - The key is shown **once**. Copy it and store it securely.
    - A key can last **at most three months**, so long-lived integrations
      must **rotate** keys.
    - Use a short duration (about a day) for interactive use.
- **Programmatic keys:** the methods `generate` and `revoke` on
  `res.users.apikeys` create and remove keys over the same API.
    - By default only users with Settings administration rights may use
      them. The system parameter `base.enable_programmatic_api_keys`
      opens this to other users.
    - A user can create up to 10 keys by default
      (`base.programmatic_api_keys_limit`). More returns HTTP 422.
- **Rotation, in order:** generate the new key, store it, switch the
  services, then revoke the old key. Authenticating with the new key to
  revoke the old one is a good habit.
- Use **one key per integration**, so you can see which is in use and
  revoke one without breaking others.

## 3. "Whose rights does an API call use?"

**Answer:**

- The call runs **as the user who owns the key**. All the normal checks
  apply: access rights, their domains, and field access. See
  [Odoo Security Model](../framework/odoo-security.md).
- For a one-off script, a personal account is fine.
- For a real integration, create a **dedicated bot user**:
    - It gets **only the rights the integration needs**, so a leaked key
      does little harm.
    - You can set an **empty password**, so nobody can log in with it.
    - The "created by" and "modified by" fields show the bot, not a real
      person.
- Never use an administrator's key for an integration.

## 4. "How do transactions work, and why does it matter?"

**Answer:**

- **Every call is its own transaction.** On success it is committed. On
  error it is rolled back.
- You **cannot chain several calls into one transaction.** Between two
  calls, another user may change the data.
- This is dangerous for work like reservations or payments. A pattern of
  "search, then read, then write" over three calls can fail halfway or act
  on stale data.
- The fix: call **one method that does the whole job**. Examples:
    - `search_read` does a search and a read in one transaction.
    - Business methods named `action_...`, such as `action_confirm` on a
      sale order, check and change everything together.
- If no such method exists, **write one in a module** and call it. This is
  a good reason to put real business logic in model methods, as in
  [Odoo Wizards & Reports](../framework/odoo-wizards-and-reports.md#3-how-do-you-design-a-good-wizard).

## 5. "How do you create a record from outside?"

```python
res = requests.post(
    f"{BASE_URL}/service.ticket/create",
    headers=headers,
    json={"vals_list": [{"name": "Printer is broken", "partner_id": 7}]},
)
res.raise_for_status()
ticket_ids = res.json()
```

**Answer:**

- `create` takes `vals_list`, a **list** of dictionaries, one per record.
  It returns the new ids.
- A missing required field, or a failed constraint, returns an error
  object and creates **nothing**, because the transaction rolls back.
- To run a business step afterwards, make a second call:
  `POST /json/2/service.ticket/action_confirm` with `{"ids": [ticket_id]}`.
  This is a second transaction. If the two steps must be atomic, put them
  in one method instead.
- Many2one fields take an id. For x2many fields, the ORM page explains
  the command format used in code:
  [Odoo ORM & Recordsets §4](../framework/odoo-orm-and-recordsets.md#4-how-do-you-write-one2many-and-many2many-fields).
  Try a small call against a test database to see the exact JSON shape
  your version expects.

## 6. "What happened to XML-RPC and JSON-RPC?"

**Answer:**

- The old endpoints `/xmlrpc`, `/xmlrpc/2`, and `/jsonrpc` are
  **deprecated since Odoo 19**. They expose three services: `common`,
  `db`, and `object`.
- The removal plan, from the documentation:
    - The **`db` service was removed in Odoo 20** (fall 2026).
    - The **`common` and `object` services are planned for removal in Odoo
      22** (fall 2028).
- So old scripts may still run, but only for a limited time, and anything
  that creates or drops databases through the `db` service is already
  gone.
- Mapping from old to new:

| Old (RPC) | New |
|---|---|
| `object.execute_kw(db, uid, pwd, model, method, args, kw)` | `POST /json/2/<model>/<method>` with named parameters |
| `common.version()` | `GET /web/version` |
| `common.login` / `authenticate` (user id and password) | An **API key** as a bearer token. No user id or password. |
| Your user's own id | `POST /json/2/res.users/context_get` |
| Database create, duplicate, drop, backup | The `/web/database/...` controllers (the database manager) |
| `list_lang`, `list_countries` | JSON-2 on `res.lang` and `res.country` |

- A big change: the old `execute_kw` passed arguments **by position**
  (`args`, then `kw`). JSON-2 passes them **by name**, so you must know the
  parameter names of the method.
- **Not affected:** your own controllers declared with
  `@route(type='jsonrpc')` (named `type='json'` up to Odoo 18). They are a
  different thing, used for example by the web client.

## 7. "What should you check before shipping an integration?"

**Answer:**

- **Plan and access:** the documentation says external API access is
  available on Odoo's **Custom** pricing plans, not on the free One App
  or Standard plans. Check your plan if you use Odoo's hosted service.
- **Keys:** one key per integration, short expiry, a rotation plan, and
  the key kept in a secret store.
- **Bot user:** minimum rights, no password.
- **HTTPS only:** never send a key over plain HTTP.
- **Atomic operations:** one call per business step. No "search then
  write" races.
- **Errors:** read the `message` and `name` of the error object, and
  retry only the failures that are safe to retry.
- **Limits:** do not loop one request per record. Use batch methods
  (`create` with a list, one `write` for many ids). See
  [Odoo Performance & Testing](../framework/odoo-performance-and-testing.md).

## 8. "Where does AI help here?"

**Answer:**

- Good for writing the HTTP client code and explaining an error object.
- It very often writes **old XML-RPC code** (`xmlrpc.client`,
  `execute_kw`), because most examples online use it. Ask for JSON-2
  specifically, and check against this page.
- Never paste a real API key into an AI tool.
- See [Interviewing in the AI Era](../../../interview-prep/interviewing-in-the-ai-era.md).

## 9. Interview Questions You're Likely to Get Asked

**Basics**

- "How do you call Odoo from another system today?" — expects JSON-2:
  POST to `/json/2/<model>/<method>` with a bearer API key,
  [§1](#1-how-does-a-json-2-request-look).
- "XML-RPC or JSON-2?" — expects JSON-2, since the RPC endpoints are
  deprecated and the `db` service is already removed,
  [§6](#6-what-happened-to-xml-rpc-and-json-rpc).

**Security**

- "Which user should an integration run as?" — expects a dedicated bot
  user with minimal rights, [§3](#3-whose-rights-does-an-api-call-use).
- "How long can an API key live?" — expects at most three months, so
  rotate, [§2](#2-how-do-you-get-and-manage-an-api-key).

**Design**

- "Why can't you do search, then write, safely over the API?" — expects
  one transaction per call, so use a single business method,
  [§4](#4-how-do-transactions-work-and-why-does-it-matter).
- "How do arguments differ from `execute_kw`?" — expects named
  parameters in the JSON body instead of positional `args`,
  [§6](#6-what-happened-to-xml-rpc-and-json-rpc).

---

## Code Samples

No dedicated code samples for this page — the snippets above are
illustrative and assume a `service.ticket` model. Reference to read: the
"External JSON-2 API" chapter of the Odoo 20 developer documentation, and
`odoo/http.py` for how routes and authentication work.
