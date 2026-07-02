from django.contrib import admin
from .models import Product, VerifiedSupplier
from .models import Product, VerifiedSupplier, Service

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["is_featured", "name", "seller", "price", "stock", "created_at"]
    list_filter = ["is_featured", "seller", "created_at", "stock"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "seller", "price", "created_at"]
    search_fields = ["name", "description"]
    list_filter = ["seller", "created_at"]

@admin.register(VerifiedSupplier)
class VerifiedSupplierAdmin(admin.ModelAdmin):
    list_display = [
        "nit",
        "name",
        "dv",
        "city",
        "department",
        "verified_at",
        "api_source",
    ]
    search_fields = ["nit", "name", "city", "department"]
    list_filter = ["api_source", "city", "department", "verified_at"]
    readonly_fields = ["verified_at"]
