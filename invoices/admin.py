from django.contrib import admin

from .models import Invoice, LineItem, Vendor


class LineItemInline(admin.TabularInline):
    model = LineItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "vendor", "number", "status", "currency", "total", "created_at"]
    list_filter = ["status", "currency"]
    search_fields = ["number", "original_name", "vendor__name"]
    inlines = [LineItemInline]


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["name", "owner"]
    search_fields = ["name"]
