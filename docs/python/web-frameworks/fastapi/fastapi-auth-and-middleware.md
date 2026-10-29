---
title: "FastAPI: Auth, Middleware & Lifecycle Events"
---

# FastAPI: Auth, Middleware & Lifecycle Events

OAuth2/JWT authentication, middleware ordering, startup/shutdown
events, and turning raised exceptions into one consistent error
envelope — the request-pipeline concerns DRF's permission classes,
middleware stack, and custom exception handler cover in Django. For
dependency injection fundamentals, see
[FastAPI: Dependency Injection & Background Tasks](fastapi-dependency-injection.md).
For the Django/DRF equivalents, see
[Django & DRF Deep Dive §4 and §6](../django/django-drf.md#4-authentication-permissions).

---

## 1. OAuth2 Password Flow & JWT

```python
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = jwt.encode({"sub": user.username, "exp": ...}, SECRET_KEY, algorithm="HS256")
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return await get_user(payload["sub"])
```

- `OAuth2PasswordBearer` is just a **dependency that extracts the
  bearer token from the `Authorization` header** — it does not itself
  validate or decode anything; `get_current_user` doing the actual
  `jwt.decode()` is where validation happens. This is the same
  dependency-chain pattern as
  [Dependency Injection §1](fastapi-dependency-injection.md#1-dependency-injection),
  just applied to auth specifically.
- Auth in FastAPI is therefore not a separate framework-level concept
  the way `AuthenticationMiddleware` + `permission_classes` is in
  DRF — it's a `Depends(get_current_user)` on every route that needs
  it, which is both more explicit (visible right in the route
  signature) and easier to forget (nothing enforces it site-wide
  without deliberately applying it, unlike DRF's
  `DEFAULT_PERMISSION_CLASSES` default-deny setting).
- **Interview point:** the "require auth on every route by default,
  opt out per-route" posture DRF gives you via
  `DEFAULT_PERMISSION_CLASSES` has to be built deliberately in
  FastAPI — typically via a router-level dependency
  (`APIRouter(dependencies=[Depends(get_current_user)])`) applied to
  every protected router, rather than relying on each route to
  remember its own `Depends(get_current_user)`.

## 2. Security Scopes & Role-Based Access

```python
from fastapi.security import SecurityScopes

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> User:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    token_scopes = payload.get("scopes", [])
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    return await get_user(payload["sub"])

@router.delete("/orders/{order_id}", dependencies=[Security(get_current_user, scopes=["orders:delete"])])
async def delete_order(order_id: int):
    ...
```

- `SecurityScopes` lets one `get_current_user` dependency serve every
  route, with each route declaring *which* scopes it needs via
  `Security(..., scopes=[...])` instead of writing a separate
  permission check per role — the FastAPI equivalent of DRF's
  per-view `permission_classes` list, just expressed as scope strings
  carried inside the JWT rather than separate permission classes.
- This still only checks **view-level** access ("can this token do
  `orders:delete` at all") — it says nothing about *which* order. The
  Django/DRF distinction between `has_permission` (view-level) and
  `has_object_permission` (per-object) in
  [Django & DRF §4](../django/django-drf.md#4-authentication-permissions)
  applies identically here: object-level checks ("does this user own
  *this* order") still need an explicit check inside the
  route/service — scopes alone don't cover it.

## 3. API Key Authentication

```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_client(api_key: str = Depends(api_key_header)) -> Client:
    client = await lookup_client_by_key(api_key)
    if client is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return client
```

- A simpler alternative to OAuth2/JWT for service-to-service or
  third-party integration auth, where there's no human login flow —
  `APIKeyHeader`/`APIKeyQuery`/`APIKeyCookie` extract the key from
  wherever it's expected, the same "just another dependency" shape as
  `OAuth2PasswordBearer`.
- **Interview point:** an API key is a long-lived, rarely-rotated
  credential by nature — unlike a short-lived JWT access token, a
  leaked API key stays valid until someone notices and revokes it.
  Rate limiting and per-key usage auditing matter more here than for
  session-based auth, precisely because revocation is the only real
  defense once a key leaks.

## 4. Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_methods=["GET", "POST"],
)
```

- FastAPI middleware is Starlette middleware underneath (FastAPI is
  built on Starlette) — `call_next` is how a middleware hands the
  request to the next layer and gets the response back, the same
  "wraps the handler" shape as Django's `get_response` callable in
  [Django & DRF §6](../django/django-drf.md#6-middleware).
- **Execution order matters the same way it does in Django, but
  reversed in how it's declared**: middleware added *last* via
  `add_middleware` runs *first* on the way in (it wraps everything
  added before it) — the opposite of Django's top-to-bottom
  `MIDDLEWARE` list reading order, a genuine gotcha for anyone coming
  from Django.
- `CORSMiddleware` is FastAPI/Starlette's built-in answer to the
  browser's cross-origin restriction — `allow_origins` is the actual
  access-control decision; leaving it as `["*"]` in production is the
  same class of mistake as a wide-open Django `CORS_ALLOWED_ORIGINS`.

## 5. Lifespan Events: Startup & Shutdown

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_engine = create_async_engine(DATABASE_URL)
    app.state.redis = await aioredis.from_url(REDIS_URL)
    yield
    await app.state.db_engine.dispose()
    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)
```

- `lifespan` is the current, recommended way to run startup/shutdown
  code — code before `yield` runs once when the app starts, code
  after `yield` runs once when it stops, the same "setup, yield,
  teardown" shape as a `yield` dependency in
  [Dependency Injection §3](fastapi-dependency-injection.md#3-yield-dependencies-setup-teardown-exception-propagation),
  just scoped to the whole app's lifetime instead of one request.
- The older `@app.on_event("startup")`/`@app.on_event("shutdown")`
  decorators still work but are deprecated in favor of `lifespan` —
  worth recognizing both forms, since plenty of existing production
  code still uses `on_event`.
- **Where this actually shows up:** creating a connection pool (DB
  engine, Redis client, an HTTP client session) once at startup and
  reusing it across every request, instead of opening a new
  connection per request — directly feeding into the
  connection-pooling advice in
  [FastAPI: Performance & Production Patterns §1](fastapi-performance-patterns.md#1-performance-patterns).

## 6. Custom Exception Handlers

```python
@app.exception_handler(OrderNotFoundError)
async def order_not_found_handler(request: Request, exc: OrderNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "ORDER_NOT_FOUND", "detail": str(exc)}},
    )
```

- `@app.exception_handler` maps a specific exception type to a
  response — the FastAPI equivalent of DRF's `EXCEPTION_HANDLER`
  setting in
  [Django & DRF §14](../django/django-drf.md#14-custom-exception-handling),
  except registered per exception type instead of one global handler
  function that inspects the exception.
- Letting a plain domain exception (`OrderNotFoundError`, raised deep
  inside a service function) propagate up and get translated at this
  one boundary keeps the service layer free of any HTTP-specific
  concern (`HTTPException`, status codes) — the service just raises a
  meaningful Python exception, and the web layer alone decides what
  HTTP status/shape that becomes.
- **Interview point:** without a registered handler, an unhandled
  exception becomes a generic `500` with FastAPI's default error
  response — exactly like DRF's behavior for an exception its default
  handler doesn't recognize. The fix is the same instinct in both
  frameworks: catch and translate known domain exceptions explicitly,
  don't rely on a catch-all to produce a meaningful response.

## 7. Interview Questions You're Likely to Get Asked

**Auth**

- "How does FastAPI know a request is authenticated — is there a
  framework-level concept like Django's `AuthenticationMiddleware`?"
  — expects no: auth is just a dependency
  (`Depends(get_current_user)`), applied per-route or per-router,
  [§1](#1-oauth2-password-flow-jwt).
- "A route checks `scopes=["orders:delete"]` and lets the request
  through — is that enough to confirm the user owns *this* order?" —
  expects no, scopes are view-level only; object-level ownership
  still needs an explicit check,
  [§2](#2-security-scopes-role-based-access).

**Middleware & lifecycle**

- "You add two middlewares, A then B, via `add_middleware` — which
  one sees the incoming request first?" — expects B (the one added
  last wraps outermost), [§4](#4-middleware).
- "Where should a database connection pool be created — per request,
  or somewhere else?" — expects once, in `lifespan`'s startup phase,
  reused across requests,
  [§5](#5-lifespan-events-startup-shutdown).

**Error handling**

- "A service function raises a plain Python exception instead of an
  `HTTPException` — how does that become a sensible API response?" —
  expects a registered `@app.exception_handler` for that exception
  type, keeping the service layer HTTP-agnostic,
  [§6](#6-custom-exception-handlers).

---

## Code Samples

No dedicated code samples for this page — see
`code_samples/chapter-3/fastapi_analytics_api.py` for authentication
and middleware used together in a working endpoint.
