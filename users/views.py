from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from .forms import (
    RegisterForm,
    UserProfileForm,
    VendorRegisterForm,
    ContactForm,
)

from .models import UserProfile, Complaint
from products.models import Product, Service, StockMovement
from products.dian_api import validate_supplier_nit
from orders.models import OrderItem
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                return redirect("login")
            except Exception as e:
                if "Duplicate entry" in str(e) and "username" in str(e):
                    form.add_error(
                        "username", "Ya existe un usuario con ese nombre de usuario."
                    )
                else:
                    form.add_error(None, f"Error al registrar usuario: {str(e)}")
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            # Bloqueo admin: impedir acceso si está bloqueado
            try:
                profile = user.profile
                if profile.status == "blocked":
                    messages.error(
                        request,
                        "Tu cuenta está bloqueada. Contacta al administrador si crees que es un error.",
                    )
                    return redirect("login")
            except ObjectDoesNotExist:
                # Si no existe profile, dejamos que el flujo normal continúe
                pass

            # Asegurar que no se pueda iniciar sesión si el usuario ya tiene sesión previa
            # (en caso de que el bloqueo se haya aplicado mientras estaba logueado)
            # Esto evita redirecciones a páginas protegidas durante el mismo ciclo.
            if user.is_authenticated:
                try:
                    profile = user.profile
                    if profile.status == "blocked":
                        logout(request)
                        return redirect("login")
                except ObjectDoesNotExist:
                    pass


            login(request, user)

            # Merge session cart to user cart if exists
            from cart.models import Cart, CartItem

            session_key = request.session.session_key
            if session_key:
                anon_cart = Cart.objects.filter(session_key=session_key).first()
                if anon_cart:
                    user_cart, _ = Cart.objects.get_or_create(user=user)
                    for item in anon_cart.items.all():
                        item.cart = user_cart
                        item.save()
                    anon_cart.delete()

            return redirect("home")
    else:
        form = AuthenticationForm()

    return render(request, "users/login.html", {"form": form})



def user_logout(request):
    logout(request)
    return redirect("login")


def home(request):
    profile = None
    is_admin = False
    is_vendedor = False
    admin_data = None

    # Home debe ser accesible para usuarios no autenticados.
    # Para evitar problemas en la vista/template, solo consultamos perfil si existe usuario.
    if request.user.is_authenticated:
        try:
            profile = request.user.profile

            # Si el admin bloquea mientras el usuario está logueado, sacarlo del sistema
            if profile.status == "blocked":
                logout(request)
                messages.error(
                    request,
                    "Tu cuenta está bloqueada. Contacta al administrador si crees que es un error.",
                )
                return redirect("login")

            is_admin = profile.is_admin() or request.user.is_superuser
            # Para mostrar el dashboard/advertencia de vendedor incluso si está pendiente,
            # usamos el rol y no `profile.is_vendedor()` (que requiere approved_by_admin=True).
            is_vendedor = profile.role == "vendedor"

        except ObjectDoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

    from cart.models import Cart
    from orders.models import Order

    cart = Cart.get_cart(request)


    # Admin dashboard data
    if is_admin:
        all_users = UserProfile.objects.select_related("user").order_by("-created_at")
        total_users = all_users.count()
        total_clients = all_users.filter(role="cliente").count()
        total_vendors = all_users.filter(role="vendedor").count()

        pending_orders = Order.objects.filter(status="pending").order_by("-created_at")[
            :10
        ]
        completed_orders = Order.objects.filter(status="delivered").order_by(
            "-created_at"
        )[:10]

        total_orders = Order.objects.count()
        pending_count = Order.objects.filter(status="pending").count()
        completed_count = Order.objects.filter(status="delivered").count()

        total_revenue = (
            Order.objects.filter(
                status__in=["pending", "processing", "shipped", "delivered"]
            ).aggregate(models.Sum("total"))["total__sum"]
            or 0
        )
        completed_revenue = (
            Order.objects.filter(status="delivered").aggregate(models.Sum("total"))[
                "total__sum"
            ]
            or 0
        )

        # Calculate profit margin (assuming 20% average margin)
        estimated_profit = float(completed_revenue) * 0.20

        # Products stats
        total_products = Product.objects.count()
        low_stock = Product.objects.filter(stock__lt=5, stock__gt=0).count()
        out_of_stock = Product.objects.filter(stock=0).count()

        admin_data = {
            "total_users": total_users,
            "total_clients": total_clients,
            "total_vendors": total_vendors,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "total_orders": total_orders,
            "pending_count": pending_count,
            "completed_count": completed_count,
            "total_revenue": total_revenue,
            "completed_revenue": completed_revenue,
            "estimated_profit": estimated_profit,
            "total_products": total_products,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "recent_users": all_users[:10],
            "clients_percent": round(total_clients / total_users * 100, 1)
            if total_users
            else 0,
            "vendors_percent": round(total_vendors / total_users * 100, 1)
            if total_users
            else 0,
        }

    # Vendor dashboard data
    vendor_data = None
    vendor_pending_approval = False
    if request.user.is_authenticated and profile and profile.role == "vendedor" and not profile.approved_by_admin:
        vendor_pending_approval = True

        # Para vendedores pendientes: mostrar advertencia pero no habilitar dashboard.
        # (El template controla mostrar/ocultar el resto en base a vendor_pending_approval.)
        # Mantener vendor_data en None.


    if is_vendedor:

        from orders.models import OrderItem

        own_products_count = Product.objects.filter(seller=profile).count()
        own_services_count = Service.objects.filter(seller=profile).count()

        order_items = OrderItem.objects.filter(product__seller=profile)
        service_items = OrderItem.objects.filter(service__seller=profile)

        all_items = order_items | service_items

        total_sales = sum(item.subtotal for item in all_items)
        total_orders = all_items.values("order").distinct().count()

        pending_orders = (
            all_items.filter(order__status="pending").values("order").distinct().count()
        )
        completed_orders = (
            all_items.filter(order__status="delivered")
            .values("order")
            .distinct()
            .count()
        )

        low_stock_count = Product.objects.filter(
            seller=profile, stock__lt=5, stock__gt=0
        ).count()

        recent_orders = all_items.select_related(
            "order", "product", "service"
        ).order_by("-order__created_at")[:10]

        product_sales = {}
        for item in all_items:
            item_name = (
                item.product.name
                if item.product
                else (item.service.name if item.service else "Unknown")
            )
            product_sales[item_name] = product_sales.get(item_name, 0) + item.quantity

        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        total_top_sales = sum(qty for _, qty in top_products) if top_products else 1

        top_products_with_percent = [
            {
                "name": name,
                "quantity": qty,
                "percentage": round(qty / total_top_sales * 100, 1),
            }
            for name, qty in top_products
        ]

        vendor_data = {
            "own_products_count": own_products_count,
            "own_services_count": own_services_count,
            "total_sales": total_sales,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "low_stock_count": low_stock_count,
            "recent_orders": recent_orders,
            "top_products": top_products_with_percent,
        }

    # Productos para vista pública (usuarios no registrados)
    public_products = None
    if not request.user.is_authenticated:
        # Mejor aproximación sin estadística de ventas: destacados primero (si existen), y luego los más recientes con stock.
        # Si tu modelo no tiene `is_featured`, esta consulta fallará: en ese caso ajustamos.
        try:
            public_products = list(
                Product.objects.filter(stock__gt=0, is_featured=True)
                .order_by("-created_at")[:8]
            )
        except Exception:
            public_products = list(Product.objects.filter(stock__gt=0).order_by("-created_at")[:8])

    # Client dashboard data
    client_data = None
    if request.user.is_authenticated and profile and profile.role == "cliente":
        from orders.models import Order


        recent_orders = (
            Order.objects.filter(user=request.user)
            .order_by("-created_at")[:5]
        )
        total_orders = Order.objects.filter(user=request.user).count()
        pending_orders = Order.objects.filter(
            user=request.user, status="pending"
        ).count()
        processing_orders = Order.objects.filter(
            user=request.user, status="processing"
        ).count()
        shipped_orders = Order.objects.filter(
            user=request.user, status="shipped"
        ).count()
        delivered_orders = Order.objects.filter(
            user=request.user, status="delivered"
        ).count()

        # Featured services
        featured_services = Service.objects.all()[:4]

        # Available products for catalog
        products = Product.objects.filter(stock__gt=0).order_by("-created_at")[:12]

        client_data = {
            "recent_orders": recent_orders,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "processing_orders": processing_orders,
            "shipped_orders": shipped_orders,
            "delivered_orders": delivered_orders,
            "featured_services": featured_services,
            "products": products,
        }

    return render(
        request,
        "users/home.html",
        {
            "profile": profile,
            "cart": cart,
            "is_admin": is_admin,
            "is_vendedor": is_vendedor,
            "admin_data": admin_data,
        "vendor_data": vendor_data,
            "vendor_pending_approval": vendor_pending_approval,
            "client_data": client_data,
        },
    )


@login_required
def edit_profile(request):
    try:
        profile = request.user.profile
    except ObjectDoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Update user fields
            request.user.username = form.cleaned_data.get("username")
            # Email no se edita desde esta pantalla
            request.user.save()

            # Save profile (this handles the avatar upload)
            form.save()

            return redirect("home")
    else:
        form = UserProfileForm(instance=profile)

    return render(
        request, "users/edit_profile.html", {"form": form, "profile": profile}
    )


@login_required
def vendor_dashboard(request):
    """
    Dashboard exclusivo para vendedores
    """
    try:
        profile = request.user.profile
    except ObjectDoesNotExist:
        messages.error(request, "No tienes un perfil de usuario.")
        return redirect("home")

    # Unificar condición con el menú del dashboard (home usa profile.role == "vendedor").
    # Evita redirecciones a login cuando profile.is_vendedor() depende de approved_by_admin/status.
    if getattr(profile, "role", None) != "vendedor":
        messages.error(request, "No tienes permisos de vendedor.")
        return redirect("home")

    # Get all products (vendors can edit any)
    products = Product.objects.all().order_by("-created_at")
    product_count = products.count()
    own_products_count = Product.objects.filter(seller=profile).count()

    # Get total sales (sum of order items for vendor's products)
    order_items = OrderItem.objects.filter(product__seller=profile)
    total_sales = sum(item.subtotal for item in order_items)
    total_orders = order_items.values("order").distinct().count()

    # Pending and completed orders
    pending_orders = (
        order_items.filter(order__status="pending").values("order").distinct().count()
    )
    completed_orders = (
        order_items.filter(order__status="delivered").values("order").distinct().count()
    )

    # Low stock products
    low_stock_count = Product.objects.filter(
        seller=profile, stock__lt=5, stock__gt=0
    ).count()

    # Recent orders (last 5)
    recent_orders = order_items.select_related("order", "product").order_by(
        "-order__created_at"
    )[:5]

    context = {
        "profile": profile,
        "products": products[:10],
        "product_count": product_count,
        "total_sales": total_sales,
        "total_orders": total_orders,
        "recent_orders": recent_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "low_stock_count": low_stock_count,
    }
    return render(request, "users/vendor_dashboard.html", context)


@login_required
def vendor_movimientos(request):
    """
    Control de movimientos de stock para vendedores
    """
    try:
        profile = request.user.profile
    except ObjectDoesNotExist:
        messages.error(request, "No tienes un perfil de usuario.")
        return redirect("home")

    # Unificar condición con el menú del dashboard (home usa profile.role == "vendedor").
    if getattr(profile, "role", None) != "vendedor":
        messages.error(request, "No tienes permisos de vendedor.")
        return redirect("home")

    products = Product.objects.filter(seller=profile).order_by("name")

    # Base query - movimientos del vendedor
    movements = StockMovement.objects.filter(
        models.Q(product__seller=profile) | models.Q(created_by=profile)
    ).select_related("product", "created_by", "order")

    # Filter parameters
    search_query = request.GET.get("search", "").strip()
    movement_type_filter = request.GET.get("movement_type", "")
    product_filter = request.GET.get("product", "")
    category_filter = request.GET.get("category", "")
    supplier_nit_filter = request.GET.get("supplier_nit", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    # Apply filters
    if search_query:
        movements = movements.filter(
            models.Q(product__name__icontains=search_query)
            | models.Q(reason__icontains=search_query)
            | models.Q(order__id__icontains=search_query)
            | models.Q(supplier_name__icontains=search_query)
        )

    if movement_type_filter:
        movements = movements.filter(movement_type=movement_type_filter)

    if product_filter:
        movements = movements.filter(product_id=product_filter)

    if category_filter:
        movements = movements.filter(product__category=category_filter)

    if supplier_nit_filter:
        movements = movements.filter(supplier_nit__icontains=supplier_nit_filter)

    if date_from:
        from django.utils.dateparse import parse_date

        parsed_date = parse_date(date_from)
        if parsed_date:
            movements = movements.filter(created_at__date__gte=parsed_date)


    if date_to:
        from django.utils.dateparse import parse_date

        parsed_date = parse_date(date_to)
        if parsed_date:
            movements = movements.filter(created_at__date__lte=parsed_date)

    movements = movements.order_by("-created_at")

    # For statistics
    total_entradas = movements.filter(movement_type="entrada").count()
    total_salidas = movements.filter(movement_type="salida").count()
    total_compras = movements.filter(movement_type="compra").count()

    if request.method == "POST":
        product_id = request.POST.get("product_id")
        movement_type = request.POST.get("movement_type")
        raw_quantity = request.POST.get("quantity", "0")
        try:
            quantity = abs(int(raw_quantity))
        except ValueError:
            quantity = 0
        reason = request.POST.get("reason", "").strip()
        supplier_nit = request.POST.get("supplier_nit", "").strip()
        supplier_name = ""
        supplier_city = ""
        supplier_department = ""
        dian_message = ""

        if supplier_nit:
            (
                is_valid,
                supplier_name,
                dian_message,
                supplier_city,
                supplier_department,
            ) = validate_supplier_nit(supplier_nit)
            if not is_valid:
                messages.warning(request, f"DIAN: {dian_message}")

        if (
            product_id
            and movement_type in ["entrada", "salida", "compra", "devolucion", "ajuste"]
            and quantity > 0
        ):
            product = get_object_or_404(Product, id=product_id, seller=profile)

            StockMovement.objects.create(
                product=product,
                movement_type=movement_type,
                quantity=quantity,
                reason=reason,
                supplier_nit=supplier_nit,
                supplier_name=supplier_name,
                supplier_city=supplier_city,
                supplier_department=supplier_department,
                created_by=profile,
            )
            if supplier_nit and dian_message:
                messages.success(request, f"¡Movimiento registrado! {dian_message}")
            else:
                messages.success(
                    request,
                    f"¡Movimiento registrado! Stock actualizado a {product.stock}.",
                )
            return redirect("vendor_movimientos")
        else:
            messages.error(request, "Datos inválidos.")

    context = {
        "profile": profile,
        "products": products,
        "movements": movements[:100],
        "search_query": search_query,
        "movement_type_filter": movement_type_filter,
        "product_filter": product_filter,
        "category_filter": category_filter,
        "supplier_nit_filter": supplier_nit_filter,
        "date_from": date_from,
        "date_to": date_to,
        "total_entradas": total_entradas,
        "total_salidas": total_salidas,
        "total_compras": total_compras,
    }
    return render(request, "users/vendor_movimientos.html", context)


# ========== Vendor Registration Views ==========


def vendor_register(request):
    """
    Vendor registration (sin código de verificación)
    """
    if request.method == "POST":
        form = VendorRegisterForm(request.POST)
        if form.is_valid():
            try:
                # Crea user + profile en estado pendiente (aprobación administrativa pendiente)
                profile = form.save()
                if getattr(profile, "approved_by_admin", None) is not False:
                    profile.approved_by_admin = False
                    # si el modelo usa status 'pending', mantenemos coherencia
                    if getattr(profile, "status", None) == "verified":
                        profile.status = "pending"
                    profile.save()

            except ValidationError as e:
                msg = getattr(e, "message", None) or str(e)
                form.add_error(None, msg)
            else:
                messages.success(
                    request,
                    "¡Registro exitoso! Tu solicitud como vendedor queda pendiente de aprobación del administrador.",
                )
                return redirect("login")
    else:
        form = VendorRegisterForm()

    return render(request, "users/vendor_register.html", {"form": form})






def vendor_resend_code(request, profile_id):
    """
    Resend verification code to admin
    """
    if not request.user.is_authenticated:
        return redirect("login")

    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        messages.error(request, "Vendedor no encontrado.")
        return redirect("admin_vendors")

    # Generate new code and send to admin
    success, code = profile.send_verification_whatsapp()

    messages.success(request, f"¡Código reenviado! Código de prueba: {code}")
    return redirect("admin_vendors")


# ========== Admin Views ==========


@login_required
def admin_dashboard(request):
    """
    Admin dashboard - manage ALL users
    """
    try:
        profile = request.user.profile
        if not profile.is_admin() and not request.user.is_superuser:
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    # All users
    users = UserProfile.objects.select_related("user").order_by("-created_at")

    # Stats
    total_users = users.count()
    total_clients = users.filter(role="cliente").count()
    total_vendors = users.filter(role="vendedor").count()
    pending_vendors = users.filter(role="vendedor", approved_by_admin=False).count()

    context = {
        "users": users,
        "total_users": total_users,
        "total_clients": total_clients,
        "total_vendors": total_vendors,
        "pending_vendors": pending_vendors,
    }
    return render(request, "users/admin_dashboard.html", context)


@login_required
def admin_vendors(request):
    """
    Admin panel to manage vendor approvals
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    # Get all vendors
    vendors = UserProfile.objects.filter(role="vendedor").order_by("-created_at")

    # Separate by status
    pending_vendors = vendors.filter(status="pending")
    verified_vendors = vendors.filter(status="verified", approved_by_admin=False)
    approved_vendors = vendors.filter(approved_by_admin=True)
    blocked_vendors = vendors.filter(status="blocked")

    return render(
        request,
        "users/admin_vendors.html",
        {
            "vendors": vendors,
            "pending_vendors": pending_vendors,
            "verified_vendors": verified_vendors,
            "approved_vendors": approved_vendors,
            "blocked_vendors": blocked_vendors,
        },
    )


@login_required
def approve_vendor(request, profile_id):
    """
    Approve a vendor (admin action)
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    try:
        profile = UserProfile.objects.get(id=profile_id, role="vendedor")
    except UserProfile.DoesNotExist:
        messages.error(request, "Vendedor no encontrado.")
        return redirect("admin_vendors")

    profile.approved_by_admin = True
    profile.save()

    messages.success(
        request, f"¡Vendedor {profile.user.username} aprobado exitosamente!"
    )
    return redirect("admin_vendors")


@login_required
def reject_vendor(request, profile_id):
    """
    Reject/block a vendor (admin action)
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    try:
        profile = UserProfile.objects.get(id=profile_id, role="vendedor")
    except UserProfile.DoesNotExist:
        messages.error(request, "Vendedor no encontrado.")
        return redirect("admin_vendors")

    profile.status = "blocked"
    profile.approved_by_admin = False
    profile.save()

    messages.warning(request, f"Vendedor {profile.user.username} ha sido bloqueado.")
    return redirect("admin_vendors")


@login_required
def toggle_vendor_status(request, profile_id):
    """
    Toggle vendor active status
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    try:
        profile = UserProfile.objects.get(id=profile_id, role="vendedor")
    except UserProfile.DoesNotExist:
        messages.error(request, "Vendedor no encontrado.")
        return redirect("admin_vendors")

    if profile.status == "blocked":
        profile.status = "verified"
        messages.success(request, f"Vendedor {profile.user.username} activado.")
    else:
        profile.status = "blocked"
        messages.warning(request, f"Vendedor {profile.user.username} desactivado.")

    profile.save()
    return redirect("admin_vendors")


@login_required
def admin_approve_user(request, profile_id):
    """
    Approve any user (admin action)
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("admin_dashboard")

    profile.approved_by_admin = True
    if profile.role == "vendedor":
        profile.status = "verified"
    profile.save()

    messages.success(
        request, f"¡Usuario {profile.user.username} aprobado exitosamente!"
    )
    return redirect("admin_dashboard")


@login_required
def admin_toggle_role(request, profile_id):
    """
    Toggle user role: cliente -> vendedor -> admin -> cliente
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("admin_dashboard")

    roles_cycle = ["cliente", "vendedor", "admin"]
    current_index = roles_cycle.index(profile.role)
    new_role = roles_cycle[(current_index + 1) % 3]
    profile.role = new_role
    profile.approved_by_admin = True  # Auto approve on role change
    profile.status = "verified"
    profile.save()

    messages.success(
        request,
        f"¡Rol cambiado a {profile.get_role_display()} para {profile.user.username}!",
    )
    return redirect("admin_dashboard")


@login_required
def admin_toggle_status(request, profile_id):
    """
    Toggle user status blocked <-> verified
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("admin_dashboard")

    if profile.status == "blocked":
        profile.status = "verified"
        messages.success(request, f"¡Usuario {profile.user.username} activado!")
    else:
        profile.status = "blocked"
        messages.warning(request, f"¡Usuario {profile.user.username} bloqueado!")
    profile.save()
    return redirect("admin_dashboard")


@login_required
def admin_delete_user(request, profile_id):
    """
    Hard delete user - elimina User + Profile completamente
    """
    try:
        user_profile = request.user.profile
        if not user_profile.is_admin():
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("home")
    except ObjectDoesNotExist:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect("home")

    try:
        profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("admin_dashboard")

    username = profile.user.username
    profile.user.delete()  # Elimina User + Profile (cascade OneToOne)

    messages.success(
        request, f"¡Usuario {username} eliminado permanentemente de la base de datos!"
    )
    return redirect("admin_dashboard")


@login_required
def admin_user_detail(request, profile_id):
    """
    Ver detalles completos de un usuario
    """
    try:
        profile = UserProfile.objects.select_related("user").get(id=profile_id)
    except UserProfile.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("admin_dashboard")

    try:
        admin_profile = request.user.profile
        if not admin_profile.is_admin() and not request.user.is_superuser:
            messages.error(request, "No tienes permisos.")
            return redirect("home")
    except:
        messages.error(request, "No tienes permisos.")
        return redirect("home")

    return render(request, "users/admin_user_detail.html", {"profile": profile})


@login_required
def vendor_movimientos_pdf(request):
    """
    Genera PDF de movimientos de stock para el vendedor actual
    """
    try:
        profile = request.user.profile
    except ObjectDoesNotExist:
        return HttpResponse("No autorizado", status=403)

    if getattr(profile, "role", None) != "vendedor":
        return HttpResponse("No autorizado", status=403)

    movements = (
        StockMovement.objects.filter(
            models.Q(product__seller=profile) | models.Q(created_by=profile)
        )
        .select_related("product", "created_by", "order")
        .order_by("-created_at")
    )

    # Apply same filters as HTML view
    search_query = request.GET.get("search", "").strip()
    movement_type_filter = request.GET.get("movement_type", "")
    product_filter = request.GET.get("product", "")
    category_filter = request.GET.get("category", "")
    supplier_nit_filter = request.GET.get("supplier_nit", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if search_query:
        movements = movements.filter(
            models.Q(product__name__icontains=search_query)
            | models.Q(reason__icontains=search_query)
            | models.Q(order__id__icontains=search_query)
        )

    if movement_type_filter:
        movements = movements.filter(movement_type=movement_type_filter)

    if product_filter:
        movements = movements.filter(product_id=product_filter)

    if category_filter:
        movements = movements.filter(product__category=category_filter)

    if supplier_nit_filter:
        movements = movements.filter(supplier_nit__icontains=supplier_nit_filter)

    if date_from:
        from django.utils.dateparse import parse_date

        parsed_date = parse_date(date_from)
        if parsed_date:
            movements = movements.filter(created_at__date__gte=parsed_date)

    if date_to:
        from django.utils.dateparse import parse_date

        parsed_date = parse_date(date_to)
        if parsed_date:
            movements = movements.filter(created_at__date__lte=parsed_date)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Center
    )

    story = []

    # Title
    title = f"<b>Movimientos de Stock</b><br/><br/>{profile.user.username}"
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 20))

    # Table data
    data = [
        [
            "Fecha",
            "Producto",
            "Tipo",
            "Cantidad",
            "Proveedor",
            "Motivo",
            "Stock Después",
        ]
    ]

    for movement in movements[:50]:  # Same as HTML
        tipo_display = movement.get_movement_type_display()
        cantidad = (
            f"+{movement.quantity}"
            if movement.movement_type == "entrada"
            else f"-{movement.quantity}"
        )
        motivo = movement.reason or "-"
        fecha = movement.created_at.strftime("%d/%m/%Y %H:%M")

        supplier_info = "-"
        if movement.supplier_nit:
            supplier_info = movement.supplier_name or movement.supplier_nit
            if movement.supplier_city:
                supplier_info += (
                    f" ({movement.supplier_city}/{movement.supplier_department})"
                )

        product_name = movement.product.name if movement.product else "-"

        data.append(
            [
                fecha,
                product_name,
                tipo_display,
                cantidad,
                supplier_info,
                motivo,
                str(movement.stock_after),
            ]
        )

    # Create table
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
            ]
        )
    )

    story.append(table)

    # Footer stats
    total = len(movements)
    story.append(Spacer(1, 20))
    stats = f"<b>Total de movimientos: {total}</b>"
    story.append(Paragraph(stats, styles["Normal"]))

    doc.build(story)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="movimientos_{profile.user.username}.pdf"'
    )
    return response


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            motivo = form.cleaned_data["motivo"]
            destinatario = form.cleaned_data["destinatario"]
            mensaje = form.cleaned_data["mensaje"]

            # Log complaint (for admin review)
            recipient = "admin" if destinatario == "admin" else "vendedor"
            subject = motivo
            complaint = f"Queja nueva - Destinatario: {recipient}\nEmail: {email}\nAsunto: {subject}\nMensaje: {mensaje}"
            messages.success(
                request, f"¡Tu queja ha sido enviada al {recipient} exitosamente!"
            )

            # In real app, save to model or send email
            print(complaint)  # Console log for now

            return redirect("home")
    else:
        form = ContactForm()

    return render(request, "users/contact_form.html", {"form": form})
