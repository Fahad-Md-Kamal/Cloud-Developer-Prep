---
title: "FastAPI: Database Integration & Testing"
---

# FastAPI: Database Integration & Testing

SQLAlchemy 2.0's async engine, Alembic migrations, and testing a
FastAPI app end-to-end — the data-layer and test-suite concerns
Django gets for free from its own ORM and `pytest-django`, assembled
here from separate libraries instead of one framework. For
dependency injection fundamentals, see
[FastAPI: Dependency Injection & Background Tasks](fastapi-dependency-injection.md).
For the Django/DRF equivalents, see
[Django ORM Query Cheat Sheet](../django/django-orm.md) and
[Django & DRF Deep Dive §8](../django/django-drf.md#8-testing-drf).

---

## 1. SQLAlchemy 2.0 Async Setup

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=5)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session
```

- FastAPI has **no built-in ORM** — SQLAlchemy (usually its async
  engine, SQLAlchemy 2.0+) is the de facto standard, the way Django's
  ORM is bundled into Django itself. This is a real structural
  difference worth naming in an interview: choosing FastAPI means
  also choosing and wiring an ORM, not getting one by default.
- `expire_on_commit=False` keeps an object's attributes readable
  after a commit without triggering a fresh query to re-fetch them —
  without it, accessing `order.status` right after
  `await session.commit()` would issue another DB round-trip just to
  re-read a value already in memory.
- `pool_size`/`max_overflow` configure the connection pool created
  once at startup — the engine itself, not the session, owns the
  pool; this is the object that should be created in `lifespan` (see
  [Auth, Middleware & Lifecycle Events §5](fastapi-auth-and-middleware.md#5-lifespan-events-startup-shutdown)),
  not per-request.

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(default="pending")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
```

- SQLAlchemy 2.0's `Mapped[...]`/`mapped_column()` style ties a
  model's type hints directly to its database column types — closer
  in spirit to how a Django model field declares its type than
  SQLAlchemy's older, more verbose `Column(Integer, ...)` style.

## 2. Alembic Migrations

```bash
alembic revision --autogenerate -m "add orders table"
alembic upgrade head
```

- Alembic is a separate library (not part of SQLAlchemy itself) that
  plays the exact role Django's `makemigrations`/`migrate` play —
  `--autogenerate` diffs the current models against the database's
  recorded state and writes a migration file; `upgrade head` applies
  pending migrations, the same two-step shape as Django.
- The same zero-downtime discipline from
  [Django & DRF §7](../django/django-drf.md#7-migrations) applies identically
  here: add a new column nullable → deploy dual-write code → backfill
  → deploy read-from-new-column code → drop the old column later.
  Nothing about using FastAPI/SQLAlchemy instead of Django changes
  that underlying production-safety reasoning, since it's about how
  rolling deploys interact with schema changes, not about the
  framework.
- **Interview point:** `--autogenerate` is a *diff tool*, not a
  guarantee — it can miss some changes (certain constraint/index
  changes, data-only migrations) the same way Django's
  `makemigrations` can, and the generated migration should always be
  read before being trusted, never applied blind.

## 3. Repository / Service Layer Pattern

```python
class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, order_id: int) -> Order:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

async def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)
```

- The same layering discipline from
  [Django & DRF §1](../django/django-drf.md#1-project-structure-that-scales) —
  keep business logic out of the route function — maps onto FastAPI
  as a service class, itself resolved as a dependency
  (`get_order_service` depending on `get_db`). A route function stays
  a thin orchestration layer: call the service, return the result.
- This is also what makes the SQLAlchemy session swappable for
  testing without touching a single route — override `get_db` (and
  therefore every dependency chained off it, including
  `get_order_service`) the same way [§5](#5-dependency-overrides-for-testing)
  below does.
- Raising a plain domain exception (`OrderNotFoundError`) from inside
  the service, rather than an `HTTPException`, keeps the service
  layer free of any HTTP concept — the exception handler covered in
  [Auth, Middleware & Lifecycle Events §6](fastapi-auth-and-middleware.md#6-custom-exception-handlers)
  is what translates it into an actual HTTP response.

## 4. Testing with TestClient & httpx AsyncClient

```python
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_order(client):
    response = await client.post("/orders/", json={"customer_id": 1, "items": [...]})
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
```

- `TestClient` (synchronous, wraps `httpx` under the hood) is fine
  for purely synchronous test suites; an **async test suite testing
  async routes** should use `httpx.AsyncClient` with `ASGITransport`
  instead, so the test itself can `await` the request the same way a
  real async client would — `pytest-asyncio` (`@pytest.mark.asyncio`,
  or `asyncio_mode = "auto"` in config) is required to actually run
  `async def` test functions at all.
- Neither client starts a real running server or opens a real socket
  — `ASGITransport` calls the ASGI app in-process, directly, the same
  "no real server, no real socket" test speed Django's `APIClient`
  gives you by calling the view machinery directly rather than
  spinning up `runserver`.

## 5. Dependency Overrides for Testing

```python
@pytest.fixture
async def test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with test_async_session() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client(test_db):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- `app.dependency_overrides` is a dict FastAPI checks before
  resolving any dependency — swapping `get_db` here means **every**
  route that depends on it (directly or, per
  [Dependency Injection §2](fastapi-dependency-injection.md#2-sub-dependencies-and-per-request-caching)'s
  caching, transitively through a service dependency) gets the test
  session automatically, with zero changes to route code. This is the
  direct FastAPI equivalent of swapping Django's test database
  connection, just explicit rather than implicit.
- **Always clear overrides after the test**
  (`app.dependency_overrides.clear()`) — `app` is a shared
  module-level object, so an override left in place leaks into the
  next test file that imports the same `app` instance, a real and
  easy-to-hit source of test pollution across a suite.
- `factory_boy`/`factory` (the same library Django teams use, via
  `SQLAlchemyModelFactory` instead of `DjangoModelFactory`) works
  here too, for the same reason it's preferred in
  [Django & DRF §8](../django/django-drf.md#8-testing-drf): factories compose
  and stay valid as the schema evolves, unlike fixtures loaded from a
  static JSON/YAML file.

## 6. Interview Questions You're Likely to Get Asked

**Database layer**

- "Django bundles an ORM. What does choosing FastAPI mean for data
  access?" — expects naming SQLAlchemy + Alembic as the de facto
  standard choice FastAPI itself doesn't make for you,
  [§1](#1-sqlalchemy-20-async-setup)–[§2](#2-alembic-migrations).
- "Why does accessing an attribute right after a commit sometimes
  trigger an unexpected query?" — expects `expire_on_commit` and
  what it controls, [§1](#1-sqlalchemy-20-async-setup).

**Testing**

- "Why use `httpx.AsyncClient` instead of the synchronous
  `TestClient` for an async test suite?" — expects: testing async
  routes from an `async def` test function needs an async client it
  can genuinely `await`,
  [§4](#4-testing-with-testclient-httpx-asyncclient).
- "How do you swap the real database for a test database across an
  entire FastAPI app without editing route code?" — expects
  `app.dependency_overrides[get_db] = ...`, plus remembering to clear
  it after the test, [§5](#5-dependency-overrides-for-testing).

**Architecture**

- "Where should business logic live in a FastAPI app, if not in the
  route function?" — expects the service-layer pattern in
  [§3](#3-repository-service-layer-pattern), the same reasoning as
  Django's service-layer advice.

---

## Code Samples

No dedicated code samples for this page — see
`code_samples/chapter-3/api_integration_testing.py` for integration
tests against a FastAPI/httpx endpoint.
