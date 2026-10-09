---
title: "Django & DRF Deep Dive"
---

# Django & DRF Deep Dive

Django/DRF-specific depth beyond what's covered elsewhere — serializers,
permissions, auth, signals, migrations, testing, caching. For query
optimization and ORM patterns (`select_related`, `F()`, `Subquery`,
window functions), see the
[Django ORM Query Cheat Sheet](django-orm.md). For general REST API
design principles and versioning, see
[API Design Fundamentals](../../architecture/api-design-fundamentals.md); for the FastAPI
comparison, see [FastAPI](fastapi-dependency-injection.md).

---

## 1. Project Structure That Scales

Keep layers separate as the codebase grows, or "fat views"/"fat
serializers" become the thing that makes every change risky:

- **Models** — persistence and data integrity only (constraints,
  `clean()`, model-level validation).
- **Serializers** — API shape and input validation, not business logic.
- **Views/ViewSets** — request orchestration: call a service, return a
  response. Not where business rules live.
- **Services** (plain functions or classes, not a framework concept) —
  business workflows once logic outgrows a serializer's `validate()`. A
  `cancel_order(order, reason)` function that a view, a management
  command, and a Celery task can all call is the pattern.

**Avoid:** business logic buried in `signals.py` where it's invisible
from the code path that triggers it (see §5); validation duplicated
across serializer and model; views that directly manipulate multiple
models' internals instead of calling one service function.

## 2. Serializers in Depth

```python
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "status", "items", "total", "created_at"]

    def get_total(self, obj):
        return sum(item.price * item.quantity for item in obj.items.all())

    def validate_status(self, value):
        if value == "cancelled" and self.instance and self.instance.status == "shipped":
            raise serializers.ValidationError("Cannot cancel a shipped order.")
        return value

    def validate(self, attrs):
        # cross-field validation goes here, not validate_<field>
        return attrs
```

`validate_<field>` for single-field rules, `validate(self, attrs)` for
anything involving more than one field. `SerializerMethodField` for
computed, read-only values — but watch for N+1: `get_total` above
iterating `obj.items.all()` without `prefetch_related("items")` upstream
in the view's queryset is exactly the kind of hidden N+1 that doesn't
show up by reading the serializer alone, only by reading the queryset
that feeds it.

**Nested serializers** (`items = OrderItemSerializer(many=True)`) are
read-only by default for writes — nested *writable* serializers need an
explicit `create()`/`update()` override to handle the nested data, which
is exactly why many teams instead flatten writes into a separate
serializer or a service function rather than fighting DRF's nested-write
ergonomics.

## 3. ViewSets, Generic Views, and When to Use Which

| | Use when |
|---|---|
| `APIView` | Full manual control, doesn't fit CRUD shape |
| `GenericAPIView` + mixins | CRUD, but need to customize one or two methods |
| `ModelViewSet` | Standard CRUD, router-friendly, least code |

```python
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.user
        ).select_related("customer").prefetch_related("items__product")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        cancel_order(order, reason=request.data.get("reason"))
        return Response({"status": "cancelled"})
```

`get_queryset()` as a method (not a `queryset = ...` class attribute)
when the result depends on the request — filtering to the current user
is the most common reason. `@action` adds a non-CRUD endpoint
(`/orders/{id}/cancel/`) to a ViewSet without leaving the router-based
URL pattern.

## 4. Authentication & Permissions

**Session vs. token vs. JWT:** session auth needs a shared session
store (fine for a monolith serving its own frontend); token auth
(`TokenAuthentication`, one static token per user) is simple but has no
expiry without extra work; JWT carries claims in the token itself
(stateless, works well across services) at the cost of harder
revocation — a compromised JWT is valid until it expires, since there's
no server-side session to invalidate. Short-lived access tokens +
refresh tokens is the standard mitigation.

```python
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user
```

`has_permission` runs before the queryset is even touched (view-level:
"can this user hit this endpoint at all"); `has_object_permission` runs
per-object, only on detail routes, after the object is fetched. Mixing
them up is a common bug — putting per-object logic in `has_permission`
either never runs (no object to check yet) or silently no-ops.

**Multi-tenant auth:** the pattern that actually matters — every
queryset filtered by tenant *at the ORM level*, not just checked in a
permission class, since a permission check that runs after the object
is already fetched by ID is too late if the ID itself leaked across
tenants. `get_queryset()` filtering by `request.user.organization` (as
in §3's example) is the real enforcement point.

## 5. Django Signals — and Why to Be Careful With Them

```python
@receiver(post_save, sender=Order)
def send_order_confirmation(sender, instance, created, **kwargs):
    if created:
        send_confirmation_email.delay(instance.id)
```

Signals decouple "an order was created" from "send a confirmation
email" — useful when the emitting code genuinely shouldn't know about
every consumer. The cost: the connection is invisible from
`Order.objects.create(...)` itself — a reader has to know signals exist
and go find `signals.py` to discover that saving an order also sends an
email. Ordering between multiple receivers on the same signal is also
not guaranteed by default.

**Interview position:** signals are reasonable for genuinely
cross-cutting, optional side effects (audit logging, cache invalidation)
where the core flow shouldn't depend on the side effect succeeding.
For anything business-critical — the email *must* send, the inventory
*must* decrement — call it explicitly from a service function instead,
where it's visible in the code path and its failure is handled where the
rest of the transaction is.

## 6. Middleware

Request flows through middleware top-to-bottom (as listed in
`MIDDLEWARE`) on the way in, and bottom-to-top on the way out — this is
why authentication middleware sits near the top (needs to run before
most other things can assume `request.user` exists) and something like
GZip sits near the bottom (wants to compress the final response, after
everything else has run).

```python
class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        response["X-Response-Time"] = f"{time.monotonic() - start:.3f}"
        return response
```

**Where this actually shows up:** request ID injection for log
correlation, response timing headers, and — the one that bites people —
placing custom middleware in the wrong position in `MIDDLEWARE` relative
to `AuthenticationMiddleware`, so `request.user` isn't populated yet
when your middleware runs.

## 7. Migrations

`makemigrations` diffs current models against the last-recorded state
and writes a migration file; `migrate` applies pending migrations in
dependency order. Two kinds worth distinguishing in an interview:
**schema migrations** (add a column, add an index) and **data
migrations** (`RunPython`, backfilling or transforming existing rows) —
the second kind is where real production risk lives.

**Zero-downtime pattern for a breaking schema change** (e.g. renaming or
changing the type of a column that's actively being read/written): add
the new column nullable → deploy code that writes to both old and new →
backfill existing rows in a data migration → deploy code that reads from
the new column only → drop the old column in a later migration. Skipping
the dual-write step is the most common way this goes wrong — old code
still running during a rolling deploy writes to a column the new
migration already dropped.

`squashmigrations` collapses a long migration history into fewer files
once old migrations no longer need to be run individually — mostly a
housekeeping move for a codebase with years of accumulated migrations,
not something reached for often.

## 8. Testing DRF

```python
import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_cancel_order_as_owner(api_client, order_factory, user_factory):
    user = user_factory()
    order = order_factory(customer=user, status="pending")
    api_client.force_authenticate(user=user)

    response = api_client.post(f"/api/orders/{order.id}/cancel/")

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.status == "cancelled"
```

`pytest-django` + `pytest.mark.django_db` for DB access in a test;
`factory_boy` factories over fixtures loaded from JSON, since factories
compose (an `OrderFactory` can build its own `CustomerFactory`
dependency) and stay valid as the schema evolves. `APIClient` +
`force_authenticate` skips real auth for speed in most tests; keep a
smaller set of tests that go through actual auth to catch permission
regressions the mocked path would hide. Mock external calls
(`unittest.mock.patch` or a fixture that swaps the real client for a
fake) — a test suite that makes real third-party API calls is slow and
flaky for reasons that have nothing to do with your code.

## 9. Caching

```python
from django.core.cache import cache

def get_dashboard_stats(organization_id):
    key = f"dashboard_stats:{organization_id}"
    stats = cache.get(key)
    if stats is None:
        stats = compute_expensive_stats(organization_id)
        cache.set(key, stats, timeout=300)
    return stats
```

The low-level cache API (`cache.get`/`cache.set`, backed by Redis in
production) for computed values worth memoizing; `@cache_page` for
whole-view caching on genuinely static or near-static endpoints. The
harder problem is always invalidation, not caching itself — key the
cache by everything the value depends on (as above, by
`organization_id`), and invalidate explicitly on the write path
(`cache.delete(key)` when the underlying data changes) rather than
relying on TTL alone for data that needs to be fresh.

## 10. Pagination

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
```

| | Shape | Use when |
|---|---|---|
| `PageNumberPagination` | `?page=2` | simple UIs, page numbers shown to the user |
| `LimitOffsetPagination` | `?limit=25&offset=50` | client needs arbitrary slicing, not fixed pages |
| `CursorPagination` | opaque `?cursor=...` | large/real-time-changing datasets where page-number pagination would skip or repeat rows as new rows are inserted |

**Interview point:** `PageNumberPagination`/`LimitOffsetPagination`
use `OFFSET` under the hood — on a large table, a high offset
(`?page=5000`) still has to scan and discard everything before it,
getting slower the deeper you page. `CursorPagination` avoids this by
paginating off an indexed, ordered column instead of a row count —
the standard fix for "pagination gets slow on page 500."

## 11. Filtering, Searching, and Ordering

```python
# pip install django-filter
class OrderFilter(django_filters.FilterSet):
    min_total = django_filters.NumberFilter(field_name="total", lookup_expr="gte")
    status = django_filters.ChoiceFilter(choices=Order.STATUS_CHOICES)

    class Meta:
        model = Order
        fields = ["status", "min_total"]

class OrderViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ["customer__name", "id"]
    ordering_fields = ["created_at", "total"]
```

`django-filter`'s `FilterSet` for structured query-param filtering
(`?status=pending&min_total=100`); DRF's own
`SearchFilter`/`OrderingFilter` for simpler `?search=`/`?ordering=`
needs.

**Interview point:** `search_fields` on a relation (`customer__name`)
does a `JOIN` + `LIKE` — fine occasionally, but a frequently-searched
field benefits from a real database index (or a dedicated search
engine — see
[Elasticsearch Architecture](../../database/elasticsearch-architecture.md))
rather than a `LIKE '%term%'` scan on every request.

## 12. Throttling

```python
class BurstRateThrottle(UserRateThrottle):
    scope = "burst"

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"user": "1000/day", "burst": "60/min"},
}
```

`AnonRateThrottle` (by IP) vs. `UserRateThrottle` (by authenticated
user) vs. `ScopedRateThrottle` (different limits per view).

**Interview point:** DRF's built-in throttles use the cache backend —
a correctly configured Redis cache is required for them to work
correctly across multiple app server processes. The default
local-memory cache means each process tracks its own counts, so the
effective rate limit under multiple workers becomes (configured rate ×
worker count) — a common surprise in production.

## 13. API Versioning

| Strategy | Example | Trade-off |
|---|---|---|
| URL path | `/api/v1/orders/` | Most explicit/cacheable; clutters URLs with version churn |
| Query param | `/api/orders/?version=1` | Easy to default; easy to forget/omit, silently hitting the default |
| Accept header | `Accept: application/json; version=1.0` | Clean URLs; invisible to casual API exploration — can't just paste a URL in a browser |

**Interview point:** whichever strategy, the harder problem is never
picking the mechanism — it's the policy of how long old versions stay
supported, and whether a breaking change to a serializer's output
shape requires a new version at all or can ship as an additive
(non-breaking) field instead.

## 14. Custom Exception Handling

```python
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)  # DRF's default first
    if response is not None:
        response.data = {
            "error": {"code": response.status_code, "detail": response.data}
        }
    return response

# settings.py
REST_FRAMEWORK = {"EXCEPTION_HANDLER": "myapp.exceptions.custom_exception_handler"}
```

DRF's default handler already converts `Http404`, `PermissionDenied`,
and `ValidationError` into the right status codes — a custom handler
is for reshaping the *response body* into one consistent envelope
across the whole API, not for replacing that status-code logic.

**Interview point:** an unhandled exception that isn't one DRF
recognizes (a raw `ValueError` from deep in a service function) still
becomes a 500 with no custom shape applied — `custom_exception_handler`
only runs for exceptions DRF's default handler already catches;
anything else needs to be caught and translated explicitly in the
view/service layer.

## 15. File Uploads

```python
class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = Document
        fields = ["id", "file", "uploaded_at"]

class DocumentViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser, FormParser]
```

`MultiPartParser` for `multipart/form-data` uploads — the standard way
a browser `<form>` or most HTTP clients send files.

**Interview point:** validating file size/type belongs in the
serializer's `validate_file()` — rejecting an oversized file *after*
Django has already buffered the whole thing into memory or a temp
file is a resource-exhaustion risk; `DATA_UPLOAD_MAX_MEMORY_SIZE`/
`FILE_UPLOAD_MAX_MEMORY_SIZE` in settings is the hard backstop, not
the primary control.

## 16. Async Views in Django/DRF

```python
# plain Django async view -- works today
async def order_status(request, order_id):
    order = await Order.objects.aget(pk=order_id)
    return JsonResponse({"status": order.status})
```

Django itself supports `async def` views and has async ORM methods
(`aget`, `acreate`, `afilter`, …) since Django 4.1+.

**Interview point:** DRF's `APIView`/`ModelViewSet` machinery is still
fundamentally synchronous as of the versions in common production
use — mixing `async def` methods into a DRF view generally doesn't get
you real async benefits, since DRF wraps the call synchronously
regardless. The honest answer in an interview: async Django views are
real and useful for I/O-bound custom views; async *DRF*
(serializers, viewsets) is not yet a mature, "just works" story — know
this trade-off rather than claiming async DRF is a drop-in win.

## 17. API Schema & Documentation

```python
# pip install drf-spectacular
SPECTACULAR_SETTINGS = {"TITLE": "Orders API"}

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
```

`drf-spectacular` introspects serializers/views to generate an OpenAPI
schema (and a Swagger/Redoc UI) without hand-written YAML.

**Interview point:** auto-generated schemas are only as accurate as
what's introspectable — a view with heavily custom logic in
`get_queryset()`/`@action` methods often needs `@extend_schema`
annotations to describe behavior the introspector can't infer (e.g.
query params read manually from `request.query_params` instead of a
declared filter class).

## 18. Request/Response Lifecycle

- **Parsing:** DRF picks a parser (`JSONParser`, `MultiPartParser`, …)
  based on the request's `Content-Type` header — `request.data` is
  already parsed by the time a view sees it, not raw bytes.
- **Content negotiation:** DRF picks a renderer (`JSONRenderer` by
  default, `BrowsableAPIRenderer` in dev) based on the request's
  `Accept` header — this is why hitting an API in a browser shows the
  browsable HTML UI while a `curl` with `Accept: application/json`
  gets plain JSON from the same endpoint.
- **Interview point:** `request.data` vs. Django's own `request.POST`
  — `request.POST` only populates for form-encoded data; `request.data`
  is DRF's parsed body regardless of content type (JSON, form,
  multipart), which is why DRF views should always use `request.data`,
  not `request.POST`.

## 19. Interview Questions You're Likely to Get Asked

Real questions interviewers ask about Django/DRF, grouped by what
they're actually probing.

**Serializers & validation**

- "Where does cross-field validation belong, and why not just put
  everything in `validate_<field>`?" — expects distinguishing
  `validate_<field>` (single field) from `validate(self, attrs)`
  (cross-field), [§2](#2-serializers-in-depth).
- "A nested serializer works for reads but writes silently do nothing
  with the nested data — why?" — expects: nested serializers are
  read-only by default; writable nested data needs an explicit
  `create()`/`update()` override, [§2](#2-serializers-in-depth).

**Permissions & auth**

- "A per-object permission check never seems to run — what's the
  likely bug?" — expects mixing up `has_permission` (view-level, runs
  first) vs. `has_object_permission` (object-level, detail routes
  only), [§4](#4-authentication-permissions).
- "How do you make sure a multi-tenant API never leaks another
  tenant's row by ID?" — expects filtering at the `get_queryset()`
  level by tenant, not only checking in a permission class after the
  object is already fetched, [§4](#4-authentication-permissions).

**Scale & performance**

- "Pagination works fine in dev but gets slower every page deeper in
  production — why, and what's the fix?" — expects recognizing
  `OFFSET`-based pagination's cost and `CursorPagination` as the fix,
  [§10](#10-pagination).
- "Your rate limiting is supposed to cap each user at 1000
  requests/day, but users are clearly getting more than that in
  production. What's the likely misconfiguration?" — expects the
  local-memory cache / multi-worker throttle gotcha,
  [§12](#12-throttling).

**Architecture & judgment**

- "Where do you draw the line between a signal and calling a function
  directly from a view/service?" — expects
  [§5](#5-django-signals-and-why-to-be-careful-with-them)'s
  cross-cutting-optional vs. business-critical distinction.
- "Should this endpoint's business logic live in the serializer, the
  view, or a separate service function?" — expects
  [§1](#1-project-structure-that-scales)'s layering: serializers
  validate shape, views orchestrate, services hold the actual
  workflow logic.
- "Is DRF ready for async views the same way plain Django is?" —
  expects the honest nuance in
  [§16](#16-async-views-in-djangodrf) rather than a flat yes/no.

---

## Code Samples

- `code_samples/chapter-3/django_legal_document_api.py` — nested
  serializers, permissions, query optimization

## Practice Notes (from live session)

No dedicated rounds here yet — the `select_related` vs `prefetch_related`
round from the session log lives in the
[Django ORM Query Cheat Sheet](django-orm.md#practice-notes-from-live-session),
since it was specifically about ORM query behavior. Future rounds on
serializers, permissions, or auth get logged here.
