import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def make_pdf(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in lines:
        c.drawString(60, y, line)
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


GOOD_INVOICE = [
    "Vendor: Lumora Studio",
    "Invoice No: INV-2026-0917",
    "Date: 17.09.2026",
    "Design review 2 x 150.00 = 300.00",
    "Landing page build 1 x 950.00 = 950.00",
    "Total: 1,250.00 USD",
]

MISMATCH_INVOICE = [
    "Vendor: Northwind Supplies",
    "Invoice Number: NW-4471",
    "Date: 2026-10-01",
    "Paper boxes 10 x 12.50 = 125.00",
    "Total due: EUR 165.00",
]
