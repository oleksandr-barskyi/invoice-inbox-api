from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .filters import InvoiceFilter
from .models import Invoice, Vendor
from .serializers import (
    InvoiceDetailSerializer,
    InvoiceListSerializer,
    InvoiceReviewSerializer,
    InvoiceUploadSerializer,
    VendorSerializer,
)
from .tasks import process_invoice


def enqueue(invoice_id: int) -> None:
    transaction.on_commit(lambda: process_invoice.delay(invoice_id))


class InvoiceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    filterset_class = InvoiceFilter
    ordering_fields = ["created_at", "issue_date", "total"]

    def get_queryset(self):
        qs = Invoice.objects.filter(owner=self.request.user).select_related("vendor")
        if self.action == "retrieve":
            qs = qs.prefetch_related("lines")
        return qs

    def get_serializer_class(self):
        return {
            "retrieve": InvoiceDetailSerializer,
            "upload": InvoiceUploadSerializer,
            "review": InvoiceReviewSerializer,
        }.get(self.action, InvoiceListSerializer)

    def get_throttles(self):
        if self.action == "upload":
            self.throttle_scope = "uploads"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    @action(detail=False, methods=["post"])
    def upload(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        f = serializer.validated_data["file"]
        with transaction.atomic():
            invoice = Invoice.objects.create(owner=request.user, file=f, original_name=f.name[:255])
            enqueue(invoice.id)
        return Response(InvoiceListSerializer(invoice).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def reprocess(self, request: Request, pk=None) -> Response:
        invoice = self.get_object()
        with transaction.atomic():
            Invoice.objects.filter(pk=invoice.pk).update(status=Invoice.Status.PENDING, error="")
            enqueue(invoice.pk)
        return Response({"id": invoice.pk, "status": Invoice.Status.PENDING}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["patch"])
    def review(self, request: Request, pk=None) -> Response:
        invoice = self.get_object()
        serializer = self.get_serializer(invoice, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        qs = self.filter_queryset(self.get_queryset())
        by_currency = (
            qs.exclude(currency="")
            .values("currency")
            .annotate(count=Count("id"), total=Sum("total"))
            .order_by("currency")
        )
        by_status = qs.values("status").annotate(count=Count("id")).order_by("status")
        return Response({"by_currency": list(by_currency), "by_status": list(by_status)})


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VendorSerializer
    ordering_fields = ["name", "total_spent", "invoice_count"]

    def get_queryset(self):
        counted = ~Q(invoices__status=Invoice.Status.FAILED)
        return (
            Vendor.objects.filter(owner=self.request.user)
            .annotate(
                invoice_count=Count("invoices", filter=counted),
                total_spent=Coalesce(
                    Sum("invoices__total", filter=counted),
                    Value(0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
            .order_by("name")
        )
