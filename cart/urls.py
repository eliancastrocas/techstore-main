from django.urls import path
from . import views

urlpatterns = [
    path("", views.cart_detail, name="cart_detail"),
    path(
        "agregar/producto/<int:product_id>/",
        views.cart_add_product,
        name="cart_add_product",
    ),
    path(
        "agregar/servicio/<int:service_id>/",
        views.cart_add_service,
        name="cart_add_service",
    ),
    path("eliminar/<int:item_id>/", views.cart_remove, name="cart_remove"),
    path("actualizar/<int:item_id>/", views.cart_update, name="cart_update"),
    path("vaciar/", views.cart_clear, name="cart_clear"),
    path("checkout/", views.checkout, name="checkout"),
]
