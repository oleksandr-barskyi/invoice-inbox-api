from django.conf import settings
from rest_framework import serializers

from .models import Invoice, LineItem, Vendor

PDF_MAGIC = b"%PDF-"


class LineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ["id", "description", "quantity", "unit_price", "amount"]


class InvoiceListSerializer(serializers.ModelSerializer):
    vendor = serializers.CharField(source="vendor.name", default=None, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "original_name",
            "status",
            "vendor",
            "number",
            "issue_date",
            "currency",
            "total",
            "created_at",
        ]


class InvoiceDetailSerializer(InvoiceListSerializer):
    lines = LineItemSerializer(many=True, read_only=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = [*InvoiceListSerializer.Meta.fields, "issues", "error", "attempts", "parsed_at", "lines"]


class InvoiceUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, f):
        if f.size > settings.MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File is larger than 5 MB.")
        head = f.read(len(PDF_MAGIC))
        f.seek(0)
        if head != PDF_MAGIC:
            raise serializers.ValidationError("Only PDF files are accepted.")
        return f


class InvoiceReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["number", "issue_date", "currency", "total"]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.status = Invoice.Status.PARSED
        instance.issues = []
        instance.save(update_fields=["status", "issues"])
        return instance


class VendorSerializer(serializers.ModelSerializer):
    invoice_count = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Vendor
        fields = ["id", "name", "invoice_count", "total_spent"]
