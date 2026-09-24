---
title: "Large-Scale Report Generation"
---

# Large-Scale Report Generation

Generating a PDF/XLSX/CSV report from 10+GB of source data without
blowing up memory — the core constraint is the same regardless of
output format: never materialize the whole dataset in memory,
anywhere in the pipeline.

## 1. "You need to generate a 10GB+ report — what's the core principle before picking any library?"

**Answer:**

- Never materialize the full dataset in memory, at any stage of the
  pipeline — not when reading from the source, not when transforming
  it, not when writing the output.
- A report is almost always a **summary** of 10GB, not the raw 10GB
  itself — push aggregation into the database (`GROUP BY`, window
  functions) rather than pulling raw rows and summing them in Python.
  Same principle as
  [PostgreSQL for Scale](postgresql-for-scale.md) and
  [Django ORM Query Cheat Sheet](../programming-languages/python/django-orm.md).
- If the transform genuinely needs to touch the full 10GB (multiple
  joins/aggregations across all of it), that's out-of-core/distributed
  territory — [Apache Spark & PySpark](spark-pyspark.md) — not a
  single Python process holding it all in RAM.

## 2. "How do you stream data out of the database without loading it all into memory first?"

```python
# Django: .iterator() streams from the DB cursor in chunks instead
# of caching the whole queryset
for row in Order.objects.filter(status="completed").iterator(chunk_size=5000):
    process(row)

# Raw psycopg2: a named (server-side) cursor keeps results on the
# server and fetches in batches, instead of pulling everything at once
with connection.cursor(name="report_cursor") as cursor:
    cursor.itersize = 5000
    cursor.execute("SELECT * FROM orders WHERE status = %s", ["completed"])
    for row in cursor:
        process(row)
```

**Answer:**

- A plain `Model.objects.all()` (or `cursor.fetchall()`) pulls the
  entire result set into memory before you touch a single row —
  exactly what has to be avoided at this scale.
- Django's `.iterator(chunk_size=...)` streams from the database
  cursor in fixed-size batches instead of caching the whole queryset.
- A raw DB-API **named/server-side cursor** does the same thing one
  layer down — results stay on the server and are fetched in batches
  as the client asks for more, rather than all at once.
- Batch size (5k–50k rows, tuned to row width) is a real trade-off:
  too small means excessive round trips, too large defeats the point
  of streaming.

| Pros | Cons / Trade-offs |
|---|---|
| Constant memory regardless of total result set size | Can't do things that need the whole result set at once (e.g. `len()`, random access) |
| Server-side cursors avoid one giant network payload | Named cursors hold server-side resources open for the duration — a long-running one can affect DB connection limits |
| Works the same way at 1GB or 100GB of source data | Batch size needs tuning per row width/workload, not a universal default |

## 3. "How do you write a multi-GB XLSX file without holding the whole workbook in memory?"

```python
import xlsxwriter

# constant_memory=True flushes each row to disk as it's written,
# instead of holding the whole worksheet in RAM
workbook = xlsxwriter.Workbook("report.xlsx", {"constant_memory": True})
worksheet = workbook.add_worksheet()

for row_num, row in enumerate(stream_rows_from_db()):
    worksheet.write_row(row_num, 0, row)

workbook.close()
```

**Answer:**

- The default in-memory `Workbook` object (in `xlsxwriter`, `openpyxl`,
  or similar) builds the entire spreadsheet as Python objects before
  writing anything to disk — exactly what has to be avoided.
- `xlsxwriter`'s `constant_memory=True` mode flushes each row to disk
  as it's written instead of holding the whole worksheet in RAM. The
  trade-off: rows must be written in order, and you can't go back and
  edit an earlier row/cell once written.
- `openpyxl`'s `write_only=True` mode is the equivalent — a
  write-only, streaming worksheet.
- Excel has a hard limit of 1,048,576 rows per sheet — 10GB of
  row-oriented data will likely need splitting across multiple sheets
  or multiple files regardless of the memory question.

**Likely follow-up — "what if the report needs formatting, formulas, or multiple passes over the data?"**

- Formatting (column widths, cell styles, conditional formatting) is
  still possible in streaming mode — it's set per cell/row as it's
  written, same as normal.
- A formula that depends on a value written earlier works fine; one
  that depends on a value not yet written (e.g. a grand total at the
  top of the sheet) doesn't, since streaming mode can't revisit
  earlier rows — compute that value first (a cheap separate query) and
  write it before streaming the detail rows, rather than trying to
  patch it in afterward.

| Pros | Cons / Trade-offs |
|---|---|
| Constant memory regardless of file size — the whole point | Rows must be written strictly in order, no revisiting earlier ones |
| Formatting/styles still work per-cell as written | No formulas referencing not-yet-written cells (e.g. a leading grand total) |
| Scales the same at 100k rows or 10M rows | Excel's ~1M row-per-sheet limit is a hard ceiling independent of memory |

## 4. "What about PDF — and is a 10GB PDF even the right ask?"

**Answer:**

- Realistically, nobody wants a 10GB PDF — hundreds of thousands of
  pages is not a usable report. This is almost always "aggregate
  first, then format a summary," with the full raw data offered
  separately as CSV/XLSX (or a data warehouse query) if it's needed at
  all.
- For a PDF that genuinely does need many pages (a long but bounded
  document, not literally 10GB), generate incrementally with a
  streaming-capable library (e.g. ReportLab) that writes pages as
  they're built instead of assembling the entire document tree in
  memory first.
- Pushing the summarization into SQL (aggregates, top-N, grouped
  totals) before the report layer ever sees the data is what actually
  makes a 10GB source dataset into a reasonably-sized PDF in the first
  place.

## 5. "How do you structure this as a production system, not just a script?"

```python
from celery import Celery

app = Celery("reports", broker="redis://localhost:6379")

@app.task(bind=True)
def generate_report(self, filters: dict):
    self.update_state(state="PROGRESS", meta={"rows_processed": 0})

    output_path = f"/tmp/report-{self.request.id}.xlsx"
    workbook = xlsxwriter.Workbook(output_path, {"constant_memory": True})
    worksheet = workbook.add_worksheet()

    for i, row in enumerate(stream_rows_from_db(filters)):
        worksheet.write_row(i, 0, row)
        if i % 5000 == 0:
            self.update_state(state="PROGRESS", meta={"rows_processed": i})

    workbook.close()
    upload_to_object_storage(output_path)  # S3 or equivalent
    return {"download_url": get_signed_url(output_path)}
```

**Answer:**

- This doesn't belong inline in an HTTP request — a 10GB report can
  take minutes, far beyond any reasonable request timeout. Run it as a
  background job (Celery), the same pattern as
  [Practical Patterns §3](../programming-languages/python/practical-patterns.md#3-when-do-you-reach-for-celery-instead-of-just-handling-something-in-the-request).
- Stream progress back (`update_state`) so the client can show real
  progress instead of a spinner with no information for several
  minutes.
- Write the finished file to object storage (S3 or equivalent), not
  back through the web process — the web server shouldn't be a
  bottleneck (or a memory risk) for serving a multi-GB file either.
- Give the client a signed, time-limited download URL rather than
  streaming the file through the application server on request.

| Pros | Cons / Trade-offs |
|---|---|
| No HTTP timeout risk — the job runs as long as it needs to | Requires polling/websocket infrastructure for the client to see progress |
| Web server never touches the multi-GB file directly | Adds a background-job system as a dependency if one doesn't already exist |
| Object storage handles serving the large file efficiently | Signed URLs and cleanup (deleting old generated reports) need their own lifecycle management |

**Likely follow-up — "how do you verify the pipeline is actually streaming, not just assumed to be?"**

- Measure it — `tracemalloc` (see
  [Memory & Caching](../programming-languages/python/memory-and-caching.md)) or `memory-profiler`
  against a realistic-size test run, rather than trusting a library's
  "streaming mode" flag blindly. A subtly wrong configuration (e.g.
  accidentally calling `.fetchall()` somewhere in a supposedly
  streaming path) is an easy, easy-to-miss regression.

---

## Code Samples

No dedicated code samples yet for this section.
