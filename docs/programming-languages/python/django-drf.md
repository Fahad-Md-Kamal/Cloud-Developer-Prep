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
[API Design Fundamentals](../../core-engineering-foundations/api-design-fundamentals.md); for the FastAPI
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
