import django_filters

from .models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    issued_after = django_filters.DateFilter(field_name="issue_date", lookup_expr="gte")
    issued_before = django_filters.DateFilter(field_name="issue_date", lookup_expr="lte")
    min_total = django_filters.NumberFilter(field_name="total", lookup_expr="gte")
    vendor = django_filters.CharFilter(field_name="vendor__name", lookup_expr="icontains")

    class Meta:
        model = Invoice
        fields = ["status", "currency"]
