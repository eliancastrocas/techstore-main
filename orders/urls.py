from django.urls import path
from . import views

urlpatterns = [
    path("", views.order_list, name="order_list"),
    path("vendor/", views.vendor_order_list, name="vendor_order_list"),
    path("vendor/<int:order_id>/", views.order_detail, name="vendor_order_detail"),
    path("<int:order_id>/", views.order_detail, name="order_detail"),
    path("<int:order_id>/aprobar/", views.order_approve, name="order_approve"),
    path("<int:order_id>/cancelar/", views.order_cancel, name="order_cancel"),
    path(
        "<int:order_id>/actualizar/<str:new_status>/",
        views.order_status_update,
        name="order_status_update",
    ),
    path(
        "vendor/<int:order_id>/actualizar/<str:new_status>/",
        views.vendor_update_order_status,
        name="vendor_update_order_status",
    ),
    path("garantia/", views.warranty_claim_list, name="warranty_claim_list"),
    path("<int:order_id>/garantia/", views.warranty_claim, name="warranty_claim"),
    path("<int:order_id>/delete/", views.order_delete, name="order_delete"),
    path(
        "<int:order_id>/delete/confirm/",
        views.order_delete_confirm,
        name="order_delete_confirm",
    ),

    path("vendor-message/<int:order_id>/", views.save_vendor_message, name="save_vendor_message",
    ),
]

