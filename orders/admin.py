from django.contrib import admin
from .models import Order, OrderItem, WarrantyClaim


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "total", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["user__username", "id"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product", "quantity", "price"]
    search_fields = ["order__id", "product__name"]


@admin.register(WarrantyClaim)
class WarrantyClaimAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "user",
        "damage_type",
        "claim_type",
        "status",
        "created_at",
    ]
    list_filter = ["status", "damage_type", "claim_type"]
    search_fields = ["order__id", "user__username"]
