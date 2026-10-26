---
title: "FastAPI Fundamentals: Routing & Pydantic Validation"
---

# FastAPI Fundamentals: Routing & Pydantic Validation

Project structure, path/query/body parameters, and Pydantic
validation — the request-shape fundamentals DRF's serializers handle
in Django, done FastAPI's way: via type hints instead of a separate
serializer class. For general REST API design principles that apply
regardless of framework, see
[REST Deep Dive](../architecture/rest-deep-dive.md). For
Django/DRF, see [Django & DRF Deep Dive](django-drf.md).

---

## 1. Project Structure That Scales

```python
# routers/orders.py
router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/{order_id}")
async def get_order(order_id: int, service: OrderService = Depends(get_order_service)):
    return await service.get(order_id)

# main.py
app = FastAPI()
app.include_router(orders.router)
app.include_router(users.router)
```

- `APIRouter` is FastAPI's equivalent to Django's per-app `urls.py` —
  build one per resource, then `include_router` wires it into the app
  with a shared prefix/tags, instead of one giant `main.py` with every
  route declared inline.
- Keep the same layer split Django benefits from: **schemas**
  (Pydantic models — API shape), **routers** (request orchestration,
  call a service, return the result), **services** (plain
  functions/classes holding the actual business logic) — a router
  function that reaches three levels deep into SQLAlchemy models
  directly is FastAPI's version of Django's "fat view."

**Avoid:** business logic inline in a route function instead of a
service it calls — makes it untestable without spinning up the whole
HTTP layer, same reasoning as Django's service-layer advice in
[Django & DRF §1](django-drf.md#1-project-structure-that-scales).

## 2. Path, Query & Body Parameters

```python
@router.get("/{order_id}/items")
async def list_order_items(
    order_id: int,
    status: str | None = None,
    limit: int = Query(default=20, le=100),
):
    ...

@router.post("/")
async def create_order(order: OrderCreate):
    ...
```

- A parameter declared in the path (`{order_id}`) is a **path
  parameter**; any other simple-typed parameter not in the path is
  automatically a **query parameter** (`status`, `limit` above) —
  FastAPI infers this from where the name does or doesn't appear in
  the route's path string, not from an explicit decorator.
- A parameter typed as a Pydantic model (`order: OrderCreate`) is
  automatically parsed from the **request body** as JSON — the same
  type-hint-driven inference applies: FastAPI reads the function
  signature to decide where each value comes from.
- `Query(default=20, le=100)` adds validation metadata (bounds,
  description) to a query parameter beyond what a bare type hint can
  express — the same role `Field()` plays inside a Pydantic model,
  covered next.

**Interview point:** this convention-over-configuration behavior
(reading parameter source from type + path presence) is exactly what
frees FastAPI from needing a separate serializer class for simple
input shapes — and exactly what makes an interviewer's "where does
FastAPI decide if a parameter is path, query, or body" question worth
having a crisp answer for.

## 3. Pydantic Models & Validation in Depth

```python
from pydantic import BaseModel, Field, field_validator

class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate]
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, value):
        if not value:
            raise ValueError("An order needs at least one item.")
        return value

    model_config = {"str_strip_whitespace": True}
```

- `Field()` carries per-field validation (`max_length`, `gt`/`lt`,
  `pattern`) and metadata — the Pydantic analogue of DRF's field
  arguments (`max_length=`, `required=`) on a serializer field.
- `@field_validator` is Pydantic v2's equivalent of DRF's
  `validate_<field>` — single-field validation that raises on bad
  input. Cross-field validation (Pydantic's equivalent of DRF's
  `validate(self, attrs)`) uses `@model_validator(mode="after")`
  instead, checking relationships between already-validated fields.
- `model_config` (Pydantic v2; `class Config:` in v1) configures
  model-wide behavior — `str_strip_whitespace` here, or
  `from_attributes=True` (formerly `orm_mode`) to let a model build
  directly from an ORM object's attributes instead of only from a
  dict, covered next in response models.

**Know this:** unlike a DRF serializer, a Pydantic model has no idea
it's being used in an API at all — it's a standalone validation/
parsing library FastAPI happens to integrate deeply. That's also why
the same `OrderCreate` model can validate a config file, a CLI
argument, or a queue message with zero FastAPI involvement — the
validation logic isn't coupled to the web framework the way a DRF
serializer is coupled to DRF.

## 4. Response Models & Serialization

```python
class OrderRead(BaseModel):
    id: int
    status: str
    total: float
    model_config = {"from_attributes": True}

@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, service: OrderService = Depends(get_order_service)):
    return await service.get(order_id)  # returns an ORM object, not a dict
```

- `response_model` is a second Pydantic model describing what goes
  *out*, separate from the one validating what came *in* — the
  FastAPI equivalent of a DRF serializer sometimes needing separate
  read/write serializers for the same resource.
- `from_attributes=True` lets `OrderRead` build itself from an ORM
  object's attributes (`order.id`, `order.status`, …) instead of
  requiring the route to manually convert to a dict first — the route
  can just return the ORM object FastAPI/SQLAlchemy gave it.
- `response_model` also does one more job besides output shaping: it
  strips any field the route function's return value has but the
  response model doesn't — a service returning extra internal fields
  (an audit flag, a raw password hash) never leaks into the response
  just because the route forgot to exclude it.
  `response_model_exclude_unset=True` additionally omits fields that
  were never explicitly set (useful for a `PATCH` response that
  shouldn't imply every field was touched).

**Interview point:** a route with no `response_model` at all still
returns *something* — FastAPI falls back to serializing whatever the
function returns via its own JSON encoder. The risk: nothing enforces
a stable output shape or strips unintended fields, so a refactor that
adds an internal field to the returned object silently changes the
API's response. Always declaring `response_model` is the safety net
DRF's serializer gives you by construction.

## 5. Status Codes & Error Responses

```python
from fastapi import HTTPException, status

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, service: OrderService = Depends(get_order_service)):
    if not await service.customer_exists(order.customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return await service.create(order)
```

- `status_code=` on the decorator sets the *success* status (default
  `200`); `HTTPException` is how a route signals a *failure* status,
  raised like a normal exception rather than returned.
- `HTTPException(detail=...)` becomes `{"detail": "..."}` in the
  response body by default — a custom, consistent error envelope
  across an entire API needs a custom exception handler, covered in
  [FastAPI: Auth, Middleware & Lifecycle Events §6](fastapi-auth-and-middleware.md#6-custom-exception-handlers).
- A Pydantic validation failure on input (a missing required field, a
  value outside `Field()` bounds) never reaches the route function at
  all — FastAPI returns `422 Unprocessable Entity` automatically
  before the route runs, with a body describing exactly which field
  failed and why. This is the main reason FastAPI route functions
  rarely need manual "is this field present" checks: invalid input
  never gets that far.

## 6. Interview Questions You're Likely to Get Asked

**Routing & parameters**

- "How does FastAPI decide whether a parameter is a path parameter, a
  query parameter, or the request body?" — expects
  [§2](#2-path-query-body-parameters)'s rule: path parameters appear
  in the route string, a Pydantic-model-typed parameter is the body,
  everything else simple-typed is a query parameter.
- "Why organize routes with `APIRouter` instead of declaring
  everything on `app` directly?" — expects
  [§1](#1-project-structure-that-scales)'s per-resource router +
  `include_router` pattern, the FastAPI analogue of Django's per-app
  `urls.py`.

**Validation**

- "Where does cross-field validation belong in a Pydantic model?" —
  expects `@model_validator(mode="after")`, not stacking checks
  inside a single `@field_validator`,
  [§3](#3-pydantic-models-validation-in-depth).
- "A client sends a request with a missing required field — does
  your route function ever run?" — expects no: FastAPI returns `422`
  automatically before the route executes,
  [§5](#5-status-codes-error-responses).

**Response shaping**

- "What does `response_model` actually protect against, beyond
  documentation?" — expects: it strips fields not declared on the
  response model, preventing an internal field from leaking just
  because a service object happened to carry it,
  [§4](#4-response-models-serialization).
- "Can the same Pydantic model validate both API input and build
  itself from an ORM row?" — expects recognizing that's usually
  *two* models (an input model and a `from_attributes=True` output
  model), not one doing both jobs,
  [§3](#3-pydantic-models-validation-in-depth)–[§4](#4-response-models-serialization).

---

## Code Samples

No dedicated code samples for this page — see
`code_samples/chapter-3/fastapi_document_service.py` for a working
FastAPI service using Pydantic request/response models in practice.
