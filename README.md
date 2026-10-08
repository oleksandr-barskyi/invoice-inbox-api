# Invoice Inbox API

Upload PDF invoices, get structured data back. A **Django + Django REST Framework** API
where parsing runs in a **Celery** worker: vendor, number, date, currency, total and line
items are extracted from the PDF text and checked against each other. Invoices that do not
add up go to a review queue instead of silently landing in your books.

## Flow

```
POST /api/invoices/upload/   PDF in, 202 Accepted, status "pending"
        |
        |  transaction.on_commit -> Celery task process_invoice
        v
  pypdf text -> regex parsing -> validation
        |
        +-- all fields found, lines add up      -> "parsed"
        +-- missing fields or totals mismatch   -> "needs_review" (with a list of issues)
        +-- not a readable PDF                  -> "failed" (with an error)

PATCH /api/invoices/{id}/review/   a human fixes fields, invoice becomes "parsed"
POST  /api/invoices/{id}/reprocess/  run the task again
```

## Endpoints

| Method | Path | What |
| --- | --- | --- |
| POST | `/api/token/` | get an auth token (username, password) |
| POST | `/api/invoices/upload/` | upload a PDF (5 MB max, magic bytes checked, throttled) |
| GET | `/api/invoices/` | list with filters: `status`, `currency`, `vendor`, `issued_after`, `issued_before`, `min_total`, `ordering` |
| GET | `/api/invoices/{id}/` | detail with line items and issues |
| PATCH | `/api/invoices/{id}/review/` | correct fields after review |
| POST | `/api/invoices/{id}/reprocess/` | re-run parsing |
| GET | `/api/invoices/summary/` | totals per currency and counts per status |
| GET | `/api/vendors/` | vendors with invoice count and total spent (ORM annotations) |

## Design choices

- **The task is idempotent and safe to retry.** It locks the row with `select_for_update`,
  skips anything not `pending`, replaces line items inside one transaction, and retries
  with backoff only on I/O errors.
- **Enqueue on commit.** `transaction.on_commit` makes sure the worker never picks up an
  invoice whose row is not committed yet.
- **Parsing is pure Python.** `invoices/parsing.py` has no Django imports; it handles
  `1,250.00` and `1.250,00`, three date formats and currency codes or symbols.
- **Per-user data.** Every queryset is scoped to `request.user`; another user gets 404.
- **No N+1.** The list uses `select_related`, the detail `prefetch_related`; a test asserts
  the list stays at a fixed number of queries as rows grow.

## Run

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # .venv/bin/pip on macOS and Linux
python manage.py migrate
python manage.py createsuperuser
CELERY_TASK_ALWAYS_EAGER=true python manage.py runserver   # no Redis needed
```

With a real worker and Redis:

```bash
docker compose up --build
```

## Tests

22 tests with pytest-django: number and date parsing, parsing text out of PDFs generated
on the fly with reportlab, the full upload flow through the eager Celery task, review and
reprocess, corrupt files, per-user isolation, filters, summary, vendor annotations and a
query-count guard. CI also runs ruff and checks for missing migrations.

```bash
pytest
```

Stack: Python, Django 5.2, Django REST Framework, django-filter, Celery, Redis, pypdf, pytest.
