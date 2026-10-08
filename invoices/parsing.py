import io
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from pypdf import PdfReader

CURRENCIES = {"USD", "EUR", "GBP", "UAH", "PLN"}
SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₴": "UAH"}

NUMBER_RE = re.compile(r"invoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})", re.I)
VENDOR_RE = re.compile(r"^(?:vendor|from|seller|issued by)\s*:\s*(.+)$", re.I | re.M)
DATE_RE = re.compile(r"(?:invoice\s+)?date\s*:\s*([0-9]{1,4}[./\-][0-9]{1,2}[./\-][0-9]{1,4})", re.I)
TOTAL_RE = re.compile(
    r"^(?:total|total due|amount due)\s*:?\s*"
    r"(?P<pre>[A-Z]{3}|[$€£₴])?\s*"
    r"(?P<amt>[0-9][0-9,.\s]*[0-9])\s*"
    r"(?P<post>[A-Z]{3})?\s*$",
    re.I | re.M,
)
LINE_RE = re.compile(
    r"^(?P<desc>.+?)\s+(?P<qty>[0-9]+(?:[.,][0-9]+)?)\s*x\s*(?P<price>[0-9][0-9,.]*)\s*=\s*(?P<amount>[0-9][0-9,.]*)\s*$",
    re.I | re.M,
)


@dataclass
class ParsedLine:
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


@dataclass
class ParsedInvoice:
    number: str = ""
    vendor: str = ""
    issue_date: date | None = None
    currency: str = ""
    total: Decimal | None = None
    lines: list[ParsedLine] = field(default_factory=list)


def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def to_decimal(raw: str) -> Decimal | None:
    s = raw.replace(" ", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = f"{head.replace(',', '')}.{tail}" if len(tail) == 2 else s.replace(",", "")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def to_date(raw: str) -> date | None:
    parts = re.split(r"[./\-]", raw)
    if len(parts) != 3:
        return None
    try:
        a, b, c = (int(p) for p in parts)
        if len(parts[0]) == 4:
            return date(a, b, c)
        if len(parts[2]) == 4:
            return date(c, b, a)
    except ValueError:
        return None
    return None


def parse_invoice(text: str) -> ParsedInvoice:
    out = ParsedInvoice()
    if m := NUMBER_RE.search(text):
        out.number = m.group(1).strip()
    if m := VENDOR_RE.search(text):
        out.vendor = m.group(1).strip()
    if m := DATE_RE.search(text):
        out.issue_date = to_date(m.group(1))
    if m := TOTAL_RE.search(text):
        out.total = to_decimal(m.group("amt"))
        code = (m.group("pre") or m.group("post") or "").upper()
        out.currency = SYMBOLS.get(code, code if code in CURRENCIES else "")
    for m in LINE_RE.finditer(text):
        qty, price, amount = to_decimal(m.group("qty")), to_decimal(m.group("price")), to_decimal(m.group("amount"))
        if qty is None or price is None or amount is None:
            continue
        out.lines.append(ParsedLine(m.group("desc").strip(), qty, price, amount))
    return out


def find_issues(p: ParsedInvoice) -> list[str]:
    issues: list[str] = []
    for name in ("number", "vendor", "issue_date", "currency", "total"):
        if not getattr(p, name):
            issues.append(f"missing_{name}")
    for i, line in enumerate(p.lines, start=1):
        if (line.quantity * line.unit_price).quantize(Decimal("0.01")) != line.amount:
            issues.append(f"line_{i}_math")
    if p.lines and p.total is not None:
        lines_sum = sum((line.amount for line in p.lines), Decimal("0"))
        if lines_sum != p.total:
            issues.append(f"total_mismatch:{lines_sum}!={p.total}")
    return issues
