---
title: "Chapter 3: Advanced REST API Design (FastAPI & Django REST)"
---

# Chapter 3: Advanced REST API Design (FastAPI & Django REST)

Master production-grade REST API architecture for high-performance backend systems at companies like Lawstronaut (legal document APIs) and Optimizely (real-time analytics APIs). Learn to design APIs that handle millions of requests while maintaining security, consistency, and developer experience.

## Learning Objectives

- Design enterprise-grade REST APIs with proper resource modeling and HTTP semantics
- Implement high-performance FastAPI services with async patterns and dependency injection
- Master Django REST Framework for complex domain models and business logic
- Build scalable API architectures with caching, rate limiting, and monitoring
- Handle API versioning, backward compatibility, and evolution strategies

## 1. Enterprise API Design Principles

**Strategic API design is the foundation of scalable backend systems.** At Lawstronaut, APIs must handle complex legal document queries across jurisdictions, while Optimizely's APIs power real-time personalization for millions of users. Poor API design creates technical debt that becomes exponentially expensive to fix as systems scale.

### 1.1 RESTful Resource Modeling

- **Resource-first thinking**: Model APIs around business entities, not database tables
- **Hierarchical relationships**: Use nested resources for clear parent-child relationships
- **Consistent naming**: Follow predictable patterns that developers can intuit
- **HTTP semantics**: Leverage HTTP methods and status codes correctly

```python
# Good: Resource-oriented design
GET /api/v1/legal-documents/{doc_id}/sections
POST /api/v1/experiments/{exp_id}/variants

# Bad: RPC-style endpoints
POST /api/getLegalDocumentSections
GET /api/createExperimentVariant
```

**Enterprise Benefits:**
- Reduces onboarding time for new developers
- Enables automatic SDK generation
- Simplifies caching and CDN integration
- Improves API discoverability

**Review Checklist:**
- Stable, noun-based resources; avoid verb-driven RPC endpoints
- Consistent naming (pluralization, casing) across services and versions
- Expose opaque IDs and pagination cursors; never leak DB internals
- Model relationships explicitly (parent/child), with clear pagination defaults

**Lawstronaut Scenario**: Design APIs for legal document hierarchy (jurisdictions → laws → sections → amendments) where each level has specific access controls and versioning requirements.

### 1.2 HTTP Method and Status Code Mastery

- **Idempotency guarantees**: Ensure PUT and DELETE operations are safe to retry
- **Partial updates**: Use PATCH for selective field updates with merge semantics
- **Conditional operations**: Implement ETags and If-Modified-Since headers
- **Error communication**: Use precise status codes with detailed error responses

```python
# Proper status code usage
201 Created      # Resource successfully created
202 Accepted     # Async operation initiated
409 Conflict     # Resource version mismatch
422 Unprocessable Entity  # Validation errors
```

**Optimizely Scenario**: Handle experiment configuration updates where concurrent modifications must be detected and merged intelligently, preventing data loss in multi-user environments.

**Idempotency & Concurrency Guardrails:**
- Require idempotency keys on mutation POSTs to make retries safe
- Use ETags/If-Match for optimistic locking; respond with 409 on conflicts
- Document PATCH merge semantics; avoid surprise full overwrites
- Map validation to 422 with machine-readable error codes for clients

### 1.3 Content Negotiation and Versioning

- **Media type evolution**: Use content-type headers for format negotiation
- **API versioning strategies**: URL, header, or media-type based versioning
- **Backward compatibility**: Maintain older versions while deprecating gracefully
- **Schema evolution**: Handle field additions, removals, and type changes

**Versioning Playbook:**
- Prefer additive changes; introduce new fields as optional first
- Communicate deprecations via `Deprecation`/`Sunset` headers and changelog timelines
- Maintain contract tests between versions; block deploys on breaking diffs
- For breaking changes, run versions in parallel with dual-read/dual-write until migration completes

```python
# Header-based versioning
Accept: application/vnd.lawstronaut.v2+json
API-Version: 2.0

# Media type versioning
Content-Type: application/json; version=2.0
```

## 2. FastAPI for High-Performance APIs

**FastAPI combines Python's developer experience with performance approaching compiled languages.** Its async-first architecture and automatic validation make it ideal for high-throughput services like Optimizely's real-time personalization engine.

### 2.1 Advanced Dependency Injection

- **Hierarchical dependencies**: Create composable, testable service layers
- **Async dependency resolution**: Handle database connections and external services
- **Security dependencies**: Implement authentication and authorization chains
- **Request context**: Maintain state across dependency resolution

```python
# Dependency injection example
async def get_db() -> AsyncSession:
    async with get_session() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    return await authenticate_user(db, token)
```

**Enterprise Benefits:**
- Reduces boilerplate code by 60-80%
- Enables comprehensive testing through dependency mocking
- Provides built-in request validation and error handling
- Generates interactive API documentation automatically

**Dependency Patterns:**
- Keep dependency functions side-effect free; avoid opening sockets or threads during wiring
- Centralize security chains (authn → authz → rate limit) as composable dependencies
- Pass request-scoped context via `Depends` instead of globals
- Provide test overrides for every external dependency (DB, cache, LLM client)

### 2.2 Background Tasks and Async Processing

- **Non-blocking operations**: Offload heavy computation from request threads
- **Task queues**: Integration with Celery and Redis for distributed processing
- **Streaming responses**: Handle large datasets without memory exhaustion
- **WebSocket support**: Real-time bidirectional communication

```python
# Background task pattern
@app.post("/api/documents/{doc_id}/analyze")
async def analyze_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    background_tasks.add_task(extract_legal_entities, doc_id)
    return {"status": "analysis_started", "doc_id": doc_id}
```

**Lawstronaut Scenario**: Handle document analysis requests that may take minutes to complete, allowing users to continue working while processing happens asynchronously.

**Async/Background Guardrails:**
- Bound queues and executors to prevent overload; prefer backpressure over unbounded growth
- Persist job metadata (state, attempts, ETA) so users can poll and resume
- Enforce per-tenant concurrency/rate limits; shed load gracefully on saturation
- Make tasks idempotent with dedupe keys to avoid duplicate work on retries

### 2.3 Performance Optimization Patterns

- **Connection pooling**: Manage database connections efficiently
- **Response caching**: Implement intelligent caching with cache invalidation
- **Request batching**: Combine multiple operations to reduce latency
- **Memory optimization**: Use streaming and pagination for large responses

**Performance Toolkit:**
- Profile hot paths (`asyncio` debug, sampling profilers) before optimizing
- Enable compression and appropriate cache headers for cacheable GETs
- Use faster JSON encoders (`ORJSONResponse`) where compatible
- Batch outbound calls; coalesce N+1 with bounded `asyncio.gather`

## 3. Django REST Framework for Complex Domains

**Django REST Framework excels at complex business logic and data relationships.** Its mature ecosystem and ORM integration make it perfect for Lawstronaut's intricate legal document relationships and complex permission systems.

### 3.1 Advanced Serialization Patterns

- **Nested serializers**: Handle complex object graphs with proper validation
- **Dynamic serialization**: Adapt responses based on user permissions or context
- **Custom field types**: Create reusable validators and transformers
- **Bulk operations**: Efficiently handle large datasets with minimal queries

```python
# Advanced serializer with business logic
class LegalDocumentSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)
    effective_date = serializers.DateTimeField(
        validators=[validate_future_date]
    )
    
    def validate(self, attrs):
        # Complex cross-field validation
        if attrs['status'] == 'published':
            if not attrs.get('approval_signature'):
                raise ValidationError("Published documents require approval")
        return attrs
```

### 3.2 ViewSet and Permission Architecture

- **Custom permission classes**: Implement complex authorization logic
- **ViewSet composition**: Build reusable view components
- **Action-based permissions**: Different permissions for different operations
- **Row-level security**: Control access to individual records

**Optimizely Scenario**: Implement experiment access controls where users can view all experiments but only modify those they own or have specific permissions for.

**Permission Design Notes:**
- Separate authN from authZ; cache decoded tokens/claims safely
- Use object-level permissions; avoid leaking resource existence via inconsistent 403/404 responses
- Place business rules near the data layer; reuse in serializers, views, and signals
- Audit privileged actions with actor, subject, and reason for traceability

### 3.3 Query Optimization and Filtering

- **Select_related and prefetch_related**: Minimize database queries
- **Custom filter backends**: Create reusable filtering logic
- **Search integration**: Connect with Elasticsearch for full-text search
- **Pagination strategies**: Handle large datasets efficiently

**Query Tuning Checklist:**
- Inspect query counts; add `select_related/prefetch_related` for hot endpoints
- Cap page sizes; prefer cursor pagination for real-time feeds
- Avoid heavy serializer computation; precompute or annotate in the queryset
- Delegate search-heavy workloads to search engines with defined consistency rules

```python
# Optimized queryset with complex filtering
class ExperimentViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Experiment.objects.select_related('owner')\
            .prefetch_related('variants__metrics')\
            .filter(organization=self.request.user.organization)
```

### 3.4 Advanced Django ORM Query Patterns

Senior Django interviews often move beyond serializers and viewsets into whether you can express non-trivial data access patterns efficiently in the ORM. The goal is not to show off obscure APIs. The goal is to avoid unnecessary Python loops, reduce query count, and let PostgreSQL do the work it is good at.

#### Atomic updates with `F()` expressions

```python
from django.db.models import F

Product.objects.filter(pk=product_id, stock__gt=0).update(
    stock=F("stock") - 1
)
```

Use this when concurrent requests may update the same row. It is safer than reading the value into Python, decrementing it, and saving it back.

#### Subqueries for per-row derived values

```python
from django.db.models import OuterRef, Subquery

latest_order_total = (
    Order.objects
    .filter(customer=OuterRef("pk"))
    .order_by("-created_at")
    .values("total_amount")[:1]
)

customers = Customer.objects.annotate(
    latest_order_total=Subquery(latest_order_total)
)
```

This is useful for dashboards and reporting APIs where each parent row needs one derived value from a related table.

#### Boolean existence checks with `Exists`

```python
from django.db.models import Exists, OuterRef

pending_invoices = Invoice.objects.filter(
    customer=OuterRef("pk"),
    status="pending",
)

customers = Customer.objects.annotate(
    has_pending_invoice=Exists(pending_invoices)
)
```

Use `Exists` when you need a flag, not the rows themselves.

#### Transaction-safe row locking

```python
from django.db import transaction

with transaction.atomic():
    ticket = SupportTicket.objects.select_for_update().get(pk=ticket_id)
    ticket.assigned_to = request.user
    ticket.save(update_fields=["assigned_to"])
```

This matters for flows like stock allocation, payment processing, and any workflow where two concurrent writers must not overwrite each other.

#### Window functions for ranking and analytics

```python
from django.db.models import F, Window
from django.db.models.functions import Rank

employees = Employee.objects.annotate(
    team_rank=Window(
        expression=Rank(),
        partition_by=[F("team_id")],
        order_by=F("performance_score").desc(),
    )
)
```

This is useful when APIs need ranked leaderboards, top performers per team, or similar analytics.

**Interview pattern to remember:**
- use `select_related` and `prefetch_related` to remove N+1 queries
- use `annotate()` for aggregates
- use `F()` for in-database updates
- use `Subquery` and `Exists` for efficient per-row derived values
- use `select_for_update()` inside `transaction.atomic()` when correctness under concurrency matters

## 4. API Performance and Production Readiness

**Production APIs must handle failure gracefully while maintaining performance under load.** Both Lawstronaut and Optimizely require APIs that can scale to millions of requests while providing consistent response times.

### 4.1 Caching Strategies

- **Multi-layer caching**: Application, database, and CDN caching
- **Cache invalidation**: Smart cache busting with dependency tracking
- **Conditional requests**: ETags and Last-Modified headers
- **Cache warming**: Proactive cache population for critical data

**Caching Playbook:**
- Compose cache keys with tenant + resource + version; set explicit TTLs
- Invalidate on writes using dependency graphs; avoid global flushes
- Use conditional requests to let clients save bandwidth when unchanged
- Layer CDN caching for safe GETs; ensure responses are deterministic

### 4.2 Rate Limiting and Security

- **Adaptive rate limiting**: Dynamic limits based on user behavior
- **Distributed rate limiting**: Coordination across multiple servers
- **Security headers**: CORS, CSP, and security best practices
- **Input validation**: Prevent injection attacks and data corruption

**Security & Limits:**
- Apply per-IP, per-tenant, and per-user rate limits; return 429 with retry hints
- Enforce payload size limits and request timeouts; stream uploads/downloads
- Set security headers (CORS, CSP, HSTS, X-Content-Type-Options)
- Validate and canonicalize input; reject unexpected fields early

### 4.3 Monitoring and Observability

- **Request tracing**: Track requests across service boundaries  
- **Performance metrics**: Response times, error rates, and throughput
- **Business metrics**: Track API usage patterns and feature adoption
- **Alerting strategies**: Proactive issue detection and escalation

**Observability Essentials:**
- Emit structured logs with request/trace IDs, user/tenant, status, and latency
- Track RED/USE metrics (rate/errors/duration, utilization/saturation/errors) for services and infra
- Propagate tracing context across services (W3C TraceContext); instrument DB/cache/external calls
- Set SLOs (availability, latency percentiles) and alert on error budget burn, not only raw counts

## Code Examples and Implementations

### FastAPI Examples

**High-Performance Document API**
- File: `code_samples/chapter-3/fastapi_document_service.py`
- Demonstrates: Async processing, dependency injection, background tasks

**Real-time Analytics API**  
- File: `code_samples/chapter-3/fastapi_analytics_api.py`
- Demonstrates: WebSockets, streaming responses, caching

### Django REST Framework Examples

**Complex Legal Document API**
- File: `code_samples/chapter-3/django_legal_document_api.py`
- Demonstrates: Nested serializers, permissions, query optimization

**Experiment Management API**
- File: `code_samples/chapter-3/django_experiment_api.py`
- Demonstrates: ViewSets, custom actions, advanced filtering

### Integration Examples

**API Gateway with Rate Limiting**
- File: `code_samples/chapter-3/api_gateway_integration.py`
- Demonstrates: Rate limiting, caching, load balancing

**Performance Testing Suite**
- File: `code_samples/chapter-3/api_performance_tests.py`
- Demonstrates: Load testing, benchmarking, monitoring

### Running the Examples

```bash
# Install dependencies
pip install fastapi uvicorn django djangorestframework redis

# Run FastAPI examples
uvicorn code_samples.chapter-3.fastapi_document_service:app --reload

# Run Django examples
cd code_samples/chapter-3/django_examples
python manage.py runserver

# Run performance tests
python code_samples/chapter-3/api_performance_tests.py
```

### Code Organization

```
code_samples/
└── chapter-3/
    ├── fastapi_document_service.py
    ├── fastapi_analytics_api.py
    ├── django_legal_document_api.py
    ├── django_experiment_api.py
    ├── api_gateway_integration.py
    ├── api_performance_tests.py
    ├── requirements.txt
    └── django_examples/
        ├── manage.py
        ├── settings.py
        └── apps/
```

## Interview Prep Alignment: API Design & Webhooks (Week 1)

### REST vs GraphQL vs gRPC
| Feature | **REST** | **GraphQL** | **gRPC** |
| :--- | :--- | :--- | :--- |
| Paradigm | Resource-oriented | Query-based | Service/RPC-oriented |
| Data fetching | Prone to over/under-fetching; multiple round trips | Exact fields in one request | Strong contracts, less flexible queries |
| Payload | JSON | JSON | Protobuf (compact binary) |
| Transport | HTTP/1.1 | HTTP/1.1 | HTTP/2 (streaming, multiplexing) |
| Best use | Public APIs, cacheable CRUD | Mobile/Spa clients needing tailored data | Internal high-performance service-to-service |

### API Versioning Playbook
- Prefer URI versioning for clarity; reserve header/media-type versioning for advanced clients.
- Keep changes additive where possible; run old/new models in parallel during migrations.
- Communicate deprecations via headers/changelog; provide sunset timelines.

### Error Handling Patterns
- Standard HTTP status codes; avoid custom codes.
- Consistent JSON error body: machine code, human message, optional docs link.
- Avoid leaking internals (stack traces/SQL errors); map validation to 422.

### Webhooks vs Polling
- Webhooks = server push for event-driven updates; reduce polling waste.
- When to use: real-time notifications, async workflows, third-party integrations.
- When to avoid: synchronous reads, firewalled consumers, ultra-high-volume low-value events.
- Design basics: subscription URL registration, retries with backoff, signature verification, small payload + follow-up fetch when needed.

---

## Interview Focus Areas

**System Design Questions:**
- "Design a REST API for a legal document management system that handles 10M+ documents"
- "How would you implement real-time analytics APIs that serve personalization data?"
- "Design an API versioning strategy for a platform with 1000+ external integrations"

**Technical Deep Dives:**
- Django ORM optimization for complex queries
- FastAPI async patterns and performance tuning  
- API security and rate limiting strategies
- Caching architectures and invalidation strategies

**Trade-off Discussions:**
- REST vs GraphQL for different use cases
- Synchronous vs asynchronous API patterns
- Microservices vs monolithic API design
- SQL vs NoSQL for different API requirements
