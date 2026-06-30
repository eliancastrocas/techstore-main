from django.db import models
from django.contrib.auth.models import User
from users.models import UserProfile


class Product(models.Model):
    CATEGORY_CHOICES = [
        ("celular", "Celulares"),
        ("tv", "Televisores"),
        ("parlante", "Parlantes"),
        ("audifonos", "Audífonos"),
        ("smartwatch", "Smartwatches"),
        ("cargador", "Cargadores"),
        ("cable", "Cables"),
        ("tablet", "Tablets"),
        ("laptop", "Laptops"),
        ("accesorio", "Accesorios"),
        ("otro", "Otros"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="otro",
        verbose_name="Categoría",
    )
    image_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL de la imagen (ej. https://ejemplo.com/imagen.jpg)",
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        help_text="O subir una imagen desde tu computadora",
    )
    stock = models.IntegerField(default=0)
    seller = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="products",
    )
    is_featured = models.BooleanField(default=False, verbose_name="Producto Destacado")
    is_service = models.BooleanField(
        default=False, verbose_name="Es un servicio (no tiene stock físico)"
    )
    is_damaged = models.BooleanField(default=False, verbose_name="Producto dañado")

    WARRANTY_MONTHS = [
        (1, "1 Mes"),
        (3, "3 Meses"),
        (6, "6 Meses"),
        (12, "12 Meses (1 Año)"),
        (0, "Sin Garantía"),
    ]

    WARRANTY_TYPE = [
        ("proveedor", "Garantía del Proveedor"),
        ("cliente", "Garantía del Cliente"),
        ("ambos", "Ambos"),
    ]

    warranty_months = models.PositiveIntegerField(
        choices=WARRANTY_MONTHS, default=3, verbose_name="Meses de Garantía"
    )
    warranty_type = models.CharField(
        max_length=20,
        choices=WARRANTY_TYPE,
        default="proveedor",
        verbose_name="Tipo de Garantía",
    )
    warranty_details = models.TextField(
        blank=True,
        verbose_name="Detalles de la Garantía",
        help_text="Ej: Solo daños de fábrica, no incluye daños físicos",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def display_image(self):
        """Returns the image URL to display - prefers uploaded image over URL"""
        if self.image:
            return self.image.url
        return self.image_url or ""

    def save(self, *args, **kwargs):
        if self.price is not None and self.price < 0:
            self.price = abs(self.price)
        if self.stock is not None and self.stock < 0:
            self.stock = abs(self.stock)
        super().save(*args, **kwargs)


class ProductDetails(models.Model):
    """Información adicional para la ficha pública del producto."""

    product = models.OneToOneField(
        "Product",
        on_delete=models.CASCADE,
        related_name="details",
    )

    referencias = models.TextField(blank=True, default="", verbose_name="Referencias")
    especificaciones_tecnicas = models.TextField(
        blank=True, default="", verbose_name="Especificaciones técnicas"
    )
    caracteristicas = models.TextField(
        blank=True, default="", verbose_name="Características"
    )
    contenido_caja = models.TextField(
        blank=True, default="", verbose_name="Contenido de la caja"
    )
    compatibilidades = models.TextField(
        blank=True, default="", verbose_name="Compatibilidades"
    )
    dimensiones = models.TextField(
        blank=True, default="", verbose_name="Dimensiones"
    )
    materiales = models.TextField(blank=True, default="", verbose_name="Materiales")

    garantia_detalle = models.TextField(
        blank=True,
        default="",
        verbose_name="Garantía (detalle adicional)",
        help_text="Complementa warranty_details si aplica.",
    )

    # Campo requerido por el enunciado.
    otras_comentarios = models.TextField(
        blank=True, default="", verbose_name="Otras observaciones"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Detalles de {self.product.name}"


class Service(models.Model):
    name = models.CharField(max_length=200)

    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL de la imagen (ej. https://ejemplo.com/imagen.jpg)",
    )
    image = models.ImageField(
        upload_to="services/",
        blank=True,
        null=True,
        help_text="O subir una imagen desde tu computadora",
    )
    seller = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="services",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def display_image(self):
        """Returns the image URL to display - prefers uploaded image over URL"""
        if self.image:
            return self.image.url
        return self.image_url or ""

    def save(self, *args, **kwargs):
        if self.price is not None and self.price < 0:
            self.price = abs(self.price)
        super().save(*args, **kwargs)


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ("entrada", "Entrada (Inventario)"),
        ("salida", "Salida (Venta)"),
        ("compra", "Compra (Cliente)"),
        ("devolucion", "Devolución"),
        ("ajuste", "Ajuste de Inventario"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="movements",
        null=True,
        blank=True,
    )
    movement_type = models.CharField(max_length=15, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True)
    supplier_nit = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="NIT Proveedor",
        help_text="NIT del proveedor (validado contra DIAN)",
    )
    supplier_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nombre Proveedor",
        help_text="Nombre del proveedor validado en DIAN",
    )
    supplier_city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ciudad Proveedor",
    )
    supplier_department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Departamento Proveedor",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, null=True, blank=True
    )
    stock_after = models.IntegerField(
        null=True, blank=True, help_text="Stock del producto DESPUÉS de este movimiento"
    )
    stock_before = models.IntegerField(
        null=True, blank=True, help_text="Stock del producto ANTES de este movimiento"
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
    )

    def __str__(self):
        sup = f" - {self.supplier_name}" if self.supplier_name else ""
        return f"{self.get_movement_type_display()} {self.quantity} - {self.product.name if self.product else 'Servicio'}{sup}"

    def save(self, *args, **kwargs):
        if self.product and self.stock_after is None:
            self.stock_before = self.product.stock
            if self.movement_type in ["entrada", "devolucion"]:
                self.product.stock += self.quantity
            elif self.movement_type in ["salida", "compra"]:
                self.product.stock = max(0, self.product.stock - self.quantity)
            self.product.save()
            self.stock_after = self.product.stock
        super().save(*args, **kwargs)


class FormRequest(models.Model):
    SERVICE_TYPES = [
        ("mantenimiento", "Mantenimiento/Reparación"),
        ("venta", "Venta/Compra Producto"),
        ("garantia", "Garantía/Reparación"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("reviewed", "Respondido"),
        ("completed", "Solucionado"),
    ]


    ISSUE_TYPES = [
        ("pantalla", "Problema de Pantalla"),
        ("bateria", "Batería/Duración"),
        ("cargador", "Cargador no funciona"),
        ("audio", "Problema de Audio"),
        ("software", "Error de Software"),
        ("botones", "Botones sin función"),
        ("wifi", "Conexión WiFi"),
        ("touch", "Touch no responde"),
        ("Sobrecalentamiento", "Sobrecalentamiento"),
        ("Otro", "Otro problema"),
    ]

    SERVICE_OPTIONS = [
        ("revision", "Revisión Técnica"),
        ("reparacion", "Reparación"),
        ("cambio", "Cambio de Pieza"),
        ("mantenimiento", "Mantenimiento"),
        ("limpieza", "Limpieza"),
        ("garantia", "Garantía"),
    ]

    PRIORITY_LEVELS = [
        ("normal", "Normal"),
        ("urgente", "Urgente"),
        ("seguimiento", "Solo Seguimiento"),
    ]

    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    issue_type = models.CharField(
        max_length=20, choices=ISSUE_TYPES, blank=True, null=True
    )
    service_option = models.CharField(
        max_length=20, choices=SERVICE_OPTIONS, blank=True, null=True
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_LEVELS, default="normal"
    )
    customer_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    device = models.CharField(max_length=200)
    description = models.TextField()
    files = models.JSONField(
        default=list, blank=True, help_text="List of uploaded file names"
    )

    # Imagen adjunta desde formularios (opcional)
    # Se usa para mostrar/descargar desde el panel del vendedor.
    # No reemplaza el campo files; solo agrega soporte real para 1 imagen.
    image = models.ImageField(
        upload_to="form_requests/",
        blank=True,
        null=True,
        help_text="Imagen adjunta a la solicitud de reparación/mantenimiento",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    seller = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="form_requests",
    )

    def __str__(self):
        return (
            f"{self.customer_name} - {self.device} ({self.get_service_type_display()})"
        )

    class Meta:
        ordering = ["-created_at"]


class VerifiedSupplier(models.Model):
    nit = models.CharField(max_length=15, unique=True, verbose_name="NIT")

    name = models.CharField(max_length=200, verbose_name="Razón Social")
    dv = models.CharField(max_length=2, verbose_name="Dígito de Verificación")
    activity = models.CharField(
        max_length=200, blank=True, verbose_name="Actividad Económica"
    )
    city = models.CharField(max_length=100, blank=True, verbose_name="Ciudad")
    department = models.CharField(
        max_length=100, blank=True, verbose_name="Departamento"
    )
    verified_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de Verificación"
    )
    api_source = models.CharField(
        max_length=50, default="dian_api", verbose_name="Fuente API"
    )

    def __str__(self):
        return f"{self.nit} - {self.name}"

    class Meta:
        ordering = ["-verified_at"]
        verbose_name = "Proveedor Verificado"
        verbose_name_plural = "Proveedores Verificados"
