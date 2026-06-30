from django.db import models
from django.contrib.auth.models import User
from products.models import Product, Service


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("processing", "Procesando"),
        ("shipped", "Enviado"),
        ("delivered", "Entregado"),
        ("cancelled", "Cancelado"),
    ]
    PAYMENT_CHOICES = [
        ("contra_entrega", "Pago Contra Entrega"),
        ("transfer", "Transferencia Bancaria"),
        ("card", "Tarjeta de Crédito/Débito"),
    ]
    DELIVERY_CHOICES = [
        ("delivery", "Envío a domicilio"),
        ("pickup", "Recogida en tienda"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default="contra_entrega"
    )
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    card_holder_name = models.CharField(max_length=100, blank=True, null=True)
    card_number = models.CharField(max_length=20, blank=True, null=True)
    delivery_type = models.CharField(
        max_length=20, choices=DELIVERY_CHOICES, default="pickup"
    )
    delivery_address = models.TextField(blank=True, null=True)
    
    # COD pickup fields
    pickup_full_name = models.CharField(max_length=200, blank=True, null=True)
    pickup_document = models.CharField(max_length=20, blank=True, null=True)
    pickup_phone = models.CharField(max_length=20, blank=True, null=True)
    pickup_date = models.DateField(blank=True, null=True)
    
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    estimated_delivery_days = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.user.username}"

    def get_delivery_status(self):
        from django.utils import timezone
        from datetime import timedelta

        if self.status == "delivered":
            return {
                "status": "delivered",
                "message": "Entregado",
                "days": 0,
                "progress": 100,
            }

        if self.status in ["pending", "processing"]:
            return {
                "status": self.status,
                "message": "En preparación",
                "days": self.estimated_delivery_days,
                "progress": 25,
            }

        if self.status == "shipped" and self.shipped_at:
            now = timezone.now()
            days_passed = (now - self.shipped_at).days
            days_left = max(0, self.estimated_delivery_days - days_passed)
            progress = min(100, int((days_passed / self.estimated_delivery_days) * 100))

            status_msg = "En camino"
            if days_left == 0:
                status_msg = "Llegando hoy"
            elif days_left == 1:
                status_msg = "Llega mañana"
            else:
                status_msg = f"Llega en {days_left} días"

            return {
                "status": "shipped",
                "message": status_msg,
                "days": days_left,
                "progress": progress,
                "days_passed": days_passed,
            }

        if self.status == "cancelled":
            return {
                "status": "cancelled",
                "message": "Cancelado",
                "days": 0,
                "progress": 0,
            }

        return {
            "status": "unknown",
            "message": "Estado desconocido",
            "days": 0,
            "progress": 0,
        }

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        item_name = (
            self.product.name
            if self.product
            else self.service.name
            if self.service
            else "Unknown"
        )
        return f"{item_name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity

    @property
    def item_name(self):
        return (
            self.product.name
            if self.product
            else self.service.name
            if self.service
            else "Unknown"
        )


class WarrantyClaim(models.Model):
    DAMAGE_CHOICES = [
        ("no_enciende", "No enciende"),
        ("pantalla_rota", "Pantalla rota/dañada"),
        ("bateria_mala", "Batería no dura/carga mal"),
        ("sonido_malo", "Sonido defectuoso"),
        ("botones_no_funcionan", "Botones no funcionan"),
        ("wifi_no_funciona", "WiFi no conecta"),
        ("touch_no_funciona", "Touch/no responde"),
        ("cargador_no_funciona", "Cargador no funciona"),
        ("otro", "Otro problema"),
    ]

    CONDITION_CHOICES = [
        ("sellado", "Sellado (sin abrir)"),
        ("usado_poco", "Usado poco tiempo"),
        ("usado_normal", "Uso normal"),
        ("mal_uso", "Mal uso visible"),
    ]

    ORDER_TYPE_CHOICES = [
        ("reemplazo", "Reemplazo del producto"),
        ("devolucion", "Devolución del dinero"),
        ("reparacion", "Reparación"),
        ("descuento", "Descuento por daño"),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="warranty_claims"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    damage_type = models.CharField(max_length=50, choices=DAMAGE_CHOICES)
    damage_description = models.TextField(blank=True, null=True)
    condition_when_received = models.CharField(max_length=50, choices=CONDITION_CHOICES)
    claim_type = models.CharField(max_length=50, choices=ORDER_TYPE_CHOICES)
    observations = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Garantía #{self.id} - Pedido #{self.order.id}"

