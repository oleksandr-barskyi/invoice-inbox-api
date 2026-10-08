from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from invoices.models import Invoice

from .pdfs import GOOD_INVOICE, MISMATCH_INVOICE, make_pdf

pytestmark = pytest.mark.django_db


def upload(api, content: bytes, name="invoice.pdf", capture=None):
    f = SimpleUploadedFile(name, content, content_type="application/pdf")
    if capture is None:
        return api.post("/api/invoices/upload/", {"file": f}, format="multipart")
    with capture(execute=True):
        return api.post("/api/invoices/upload/", {"file": f}, format="multipart")


def test_requires_authentication(client):
    assert client.get("/api/invoices/").status_code == 401


def test_rejects_non_pdf(api):
    res = upload(api, b"hello", name="notes.txt")
    assert res.status_code == 400
    assert "Only PDF" in res.json()["file"][0]


def test_upload_is_parsed_by_the_task_after_commit(api, django_capture_on_commit_callbacks):
    res = upload(api, make_pdf(GOOD_INVOICE), capture=django_capture_on_commit_callbacks)
    assert res.status_code == 202
    assert res.json()["status"] == "pending"

    detail = api.get(f"/api/invoices/{res.json()['id']}/").json()
    assert detail["status"] == "parsed"
    assert detail["vendor"] == "Lumora Studio"
    assert Decimal(detail["total"]) == Decimal("1250.00")
    assert len(detail["lines"]) == 2


def test_mismatched_totals_go_to_review_and_can_be_confirmed(api, django_capture_on_commit_callbacks):
    res = upload(api, make_pdf(MISMATCH_INVOICE), capture=django_capture_on_commit_callbacks)
    invoice_id = res.json()["id"]
    detail = api.get(f"/api/invoices/{invoice_id}/").json()
    assert detail["status"] == "needs_review"
    assert detail["issues"] == ["total_mismatch:125.00!=165.00"]

    fixed = api.patch(f"/api/invoices/{invoice_id}/review/", {"total": "125.00"}, format="json").json()
    assert fixed["status"] == "parsed"
    assert fixed["issues"] == []


def test_corrupt_pdf_fails_without_crashing(api, django_capture_on_commit_callbacks):
    res = upload(api, b"%PDF-1.4 this is not really a pdf", capture=django_capture_on_commit_callbacks)
    detail = api.get(f"/api/invoices/{res.json()['id']}/").json()
    assert detail["status"] == "failed"
    assert "Not a readable PDF" in detail["error"]


def test_reprocess_runs_the_task_again(api, django_capture_on_commit_callbacks):
    res = upload(api, make_pdf(GOOD_INVOICE), capture=django_capture_on_commit_callbacks)
    invoice_id = res.json()["id"]
    with django_capture_on_commit_callbacks(execute=True):
        assert api.post(f"/api/invoices/{invoice_id}/reprocess/").status_code == 202
    invoice = Invoice.objects.get(pk=invoice_id)
    assert invoice.attempts == 2
    assert invoice.lines.count() == 2


def test_users_only_see_their_own_invoices(api, other_api, django_capture_on_commit_callbacks):
    res = upload(api, make_pdf(GOOD_INVOICE), capture=django_capture_on_commit_callbacks)
    assert other_api.get(f"/api/invoices/{res.json()['id']}/").status_code == 404
    assert other_api.get("/api/invoices/").json()["count"] == 0


def test_filters_summary_and_vendor_totals(api, django_capture_on_commit_callbacks):
    upload(api, make_pdf(GOOD_INVOICE), capture=django_capture_on_commit_callbacks)
    upload(api, make_pdf(MISMATCH_INVOICE), capture=django_capture_on_commit_callbacks)

    assert api.get("/api/invoices/?status=needs_review").json()["count"] == 1
    assert api.get("/api/invoices/?issued_after=2026-09-30").json()["count"] == 1
    assert api.get("/api/invoices/?vendor=lumora").json()["count"] == 1

    summary = api.get("/api/invoices/summary/").json()
    assert {row["currency"] for row in summary["by_currency"]} == {"USD", "EUR"}

    vendors = {v["name"]: v for v in api.get("/api/vendors/").json()["results"]}
    assert Decimal(vendors["Lumora Studio"]["total_spent"]) == Decimal("1250.00")
    assert vendors["Northwind Supplies"]["invoice_count"] == 1


def test_list_query_count_does_not_grow_with_rows(
    api, django_capture_on_commit_callbacks, django_assert_max_num_queries
):
    for _ in range(5):
        upload(api, make_pdf(GOOD_INVOICE), capture=django_capture_on_commit_callbacks)
    with django_assert_max_num_queries(4):
        assert api.get("/api/invoices/").json()["count"] == 5
