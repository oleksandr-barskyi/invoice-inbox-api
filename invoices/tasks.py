import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from pypdf.errors import PdfReadError

from .models import Invoice, LineItem, Vendor
from .parsing import extract_text, find_issues, parse_invoice

log = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def process_invoice(self, invoice_id: int) -> str:
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().filter(pk=invoice_id).first()
        if invoice is None:
            return "missing"
        if invoice.status != Invoice.Status.PENDING:
            return f"skipped:{invoice.status}"
        invoice.attempts += 1
        try:
            with invoice.file.open("rb") as fh:
                text = extract_text(fh.read())
        except PdfReadError as exc:
            invoice.status = Invoice.Status.FAILED
            invoice.error = f"Not a readable PDF: {exc}"
            invoice.save(update_fields=["status", "error", "attempts"])
            return "failed"

        parsed = parse_invoice(text)
        issues = find_issues(parsed)
        vendor = None
        if parsed.vendor:
            vendor, _ = Vendor.objects.get_or_create(owner=invoice.owner, name=parsed.vendor)

        invoice.vendor = vendor
        invoice.number = parsed.number
        invoice.issue_date = parsed.issue_date
        invoice.currency = parsed.currency
        invoice.total = parsed.total
        invoice.issues = issues
        invoice.error = ""
        invoice.status = Invoice.Status.NEEDS_REVIEW if issues else Invoice.Status.PARSED
        invoice.parsed_at = timezone.now()
        invoice.save()

        invoice.lines.all().delete()
        LineItem.objects.bulk_create(
            LineItem(
                invoice=invoice,
                description=line.description[:255],
                quantity=line.quantity,
                unit_price=line.unit_price,
                amount=line.amount,
            )
            for line in parsed.lines
        )
    log.info("invoice %s processed: %s", invoice_id, invoice.status)
    return invoice.status
