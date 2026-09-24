---
title: Refactoring Legacy Systems
---

# Refactoring Legacy Systems

Incremental modernization, the Strangler Fig pattern, and zero-downtime
database migrations — how production systems change without a risky
big-bang cutover.

## Incremental Modernization

**"How do you add type hints to a large, untyped legacy codebase without a big-bang rewrite?"**

```python
# Before
def process_document(doc, options):
    if options.get('validate', True) and not validate_doc(doc):
        return None
    return transform_doc(doc, options)

# After -- accepts both old and new shapes during the transition
def process_document(
    doc: dict | Document,
    options: dict,
) -> ProcessedDocument | None:
    if isinstance(doc, dict):
        doc = Document.from_dict(doc)
    if options.get('validate', True) and not validate_doc(doc):
        return None
    return transform_doc(doc, options)
```

**Answer:** Support both the old and new shape simultaneously during
the transition, add types to the highest-traffic/highest-risk modules
first, and never require every caller to migrate at once. A full
rewrite risks a long-lived branch that diverges from production while
it's being built.

| Pros | Cons / Trade-offs |
|---|---|
| Ships continuously — no long-lived "big rewrite" branch | The transitional dual-shape code is itself extra complexity, temporarily |
| Each step is independently revertible | Momentum can stall — "incremental" sometimes means "never finished" without a deadline |
| Team keeps shipping features alongside modernization | Requires real discipline to actually sunset the legacy path, not just leave both forever |

## Monolith → Microservices (Strangler Fig)

**"Walk me through extracting one service from a monolith without a risky big-bang cutover."**

```python
# Step 1: define the interface the extracted service must satisfy
class DocumentStorageService(Protocol):
    async def store(self, doc: Document) -> str: ...

# Step 2: implement it as a remote call to the new service
class RemoteDocumentStorageService:
    async def store(self, doc: Document) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/documents", json=doc.to_dict()) as resp:
                return (await resp.json())["document_id"]

# Step 3: the monolith depends on the interface, routes a small % of
# traffic to the new implementation, and compares results before cutover
```

**Answer:** The Strangler Fig pattern: put a seam (an interface) around
the capability being extracted, route a small percentage of traffic to
the new service, compare outputs against the old path for consistency,
and only fully cut over once confidence is high — the old and new
implementations coexist during the transition instead of a single
risky switch.

| Pros | Cons / Trade-offs |
|---|---|
| Each extraction is small and independently revertible | Slower than a big-bang rewrite — deliberately so |
| Real production traffic validates the new service before full cutover | Running both implementations in parallel has real infra cost during transition |
| Failure is contained to the one service being extracted | Requires genuine discipline to actually finish — a half-migrated system is worse than either extreme |

## Database Migration (Dual Read / Dual Write)

**"How do you migrate a schema with zero downtime when the table is actively being read and written?"**

```python
class DocumentMigrationService:
    async def migrate_v1_to_v2(self, doc_v1: DocumentV1) -> DocumentV2:
        metadata = json.loads(doc_v1.metadata or "{}")
        return DocumentV2(
            id=doc_v1.id,
            content=doc_v1.content,
            title=metadata.get("title"),
            raw_metadata=doc_v1.metadata,  # kept for rollback
        )

    async def read_with_fallback(self, doc_id: str) -> DocumentV2:
        if doc_v2 := await self.read_v2(doc_id):
            return doc_v2
        if doc_v1 := await self.read_v1(doc_id):
            return await self.migrate_v1_to_v2(doc_v1)  # migrate-on-read
        raise DocumentNotFoundError(doc_id)
```

**Answer:** Add the new column/table nullable → deploy code that writes
to *both* old and new shapes → backfill existing rows asynchronously →
switch reads to the new shape (falling back to the old shape + migrating
on read for anything not yet backfilled) → once fully migrated, drop the
old column. Skipping the dual-write step is the most common way this
goes wrong — old code still running mid-deploy writes to a column a
migration already dropped.

| Pros | Cons / Trade-offs |
|---|---|
| Genuinely zero downtime — no maintenance window needed | More moving parts to coordinate correctly than a single migration script |
| Rollback stays possible until the old shape is actually dropped | Dual-write/dual-read code is real, if temporary, complexity |
| Backfill can be throttled to protect production load | Easy to forget to actually clean up and drop the legacy path afterward |
