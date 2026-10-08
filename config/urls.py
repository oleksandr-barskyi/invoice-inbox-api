from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from invoices.views import InvoiceViewSet, VendorViewSet

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("vendors", VendorViewSet, basename="vendor")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", obtain_auth_token),
    path("api/", include(router.urls)),
]
