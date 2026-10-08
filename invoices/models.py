from decimal import Decimal

from django.conf import settings
from django.db import models


class Vendor(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendors")
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_vendor_per_owner")]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PARSED = "parsed"
        NEEDS_REVIEW = "needs_review"
        FAILED = "failed"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    file = models.FileField(upload_to="invoices/%Y/%m/")
    original_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    number = models.CharField(max_length=64, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    issues = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    parsed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "status"]), models.Index(fields=["owner", "issue_date"])]

    def __str__(self) -> str:
        return self.number or self.original_name

    @property
    def lines_total(self) -> Decimal:
        return sum((line.amount for line in self.lines.all()), Decimal("0"))


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.description}: {self.amount}"
