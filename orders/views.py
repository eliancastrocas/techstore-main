from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Order, OrderItem, WarrantyClaim, OrderVendorMessage
from products.models import Product, FormRequest, FormRequestVendorMessage
from .forms import OrderVendorMessageForm





@login_required
def order_list(request):
    """Show all orders for admin/vendor, user's orders for regular users"""
    user = request.user



    # Check if user is admin or vendor
    is_admin = False
    is_vendedor = False
    try:
        profile = user.profile
        is_admin = profile.is_admin() or user.is_superuser
        is_vendedor = profile.is_vendedor()
    except:
        pass

    # Admin and vendors see ALL orders, regular users see only their own
    if is_admin or is_vendedor:
        orders = Order.objects.select_related("user").order_by("-created_at")
    else:
        orders = Order.objects.filter(user=request.user).order_by("-created_at")

    # Mensaje vendedor->cliente por pedido (última versión)
    # (OneToOneField: related name vendor_message)
    return render(
        request,
        "orders/order_list.html",
        {
            "orders": orders,
            "is_admin": is_admin,
            "is_vendedor": is_vendedor,
        },
    )



@login_required
def order_detail(request, order_id):
    """Show details of a specific order"""
    order = get_object_or_404(Order, pk=order_id)


    # Check if user is admin, vendor, or the owner

    is_admin = False
    is_vendedor = False
    try:
        profile = request.user.profile
        is_admin = profile.is_admin() or request.user.is_superuser
        is_vendedor = profile.is_vendedor()
    except:
        pass

    if not (is_admin or is_vendedor or order.user == request.user):
        order = get_object_or_404(Order, pk=order_id, user=request.user)

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "is_admin": is_admin,
            "is_vendedor": is_vendedor,
            "vendor_message": getattr(order, "vendor_message", None),
        },
    )





@login_required
def order_approve(request, order_id):
    """Approve/receive order when delivered"""

    def _get_transition_error(order: Order, new_status: str) -> str | None:
        flow = ["pending", "processing", "shipped", "delivered"]
        if order.status == "delivered":
            return "El pedido entregado ya no puede ser modificado."
        try:
            current_idx = flow.index(order.status)
        except ValueError:
            return "El pedido debe seguir el orden establecido"

        if new_status not in flow:
            return "El pedido debe seguir el orden establecido"

        new_idx = flow.index(new_status)

        # No saltos ni regresos
        if new_idx != current_idx + 1:
            # Ejemplos: pending→shipped, processing→delivered, delivered→... (regresos)
            return "El pedido debe seguir el orden establecido"
        return None

    order = get_object_or_404(Order, pk=order_id, user=request.user)

    error = _get_transition_error(order, "delivered")
    if error:
        messages.error(request, error)
        return redirect("order_list")

    order.status = "delivered"
    order.delivered_at = timezone.now()
    order.save()
    messages.success(request, f"Pedido #{order.id} marcado como recibido")
    return redirect("order_list")



@login_required
def order_cancel(request, order_id):
    """Cancel order"""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.status == "pending":
        order.status = "cancelled"
        order.save()
        messages.success(request, f"Pedido #{order.id} cancelado")
    else:
        messages.error(request, "Solo puedes cancelar pedidos pendientes")
    return redirect("order_list")


@login_required
def order_status_update(request, order_id, new_status):
    """Update order status - admin, vendor, or client can update"""

    def _validate_transition(order: Order, target_status: str) -> str | None:
        flow = ["pending", "processing", "shipped", "delivered"]

        if order.status == "delivered":
            return "un pedido entregado ya no puede ser modificado"

        if target_status not in flow:
            return "El pedido debe seguir el orden establecido"

        try:
            current_idx = flow.index(order.status)
        except ValueError:
            return "El pedido debe seguir el orden establecido"

        new_idx = flow.index(target_status)

        # Obligatorio: exactamente el siguiente paso
        if new_idx != current_idx + 1:
            return "El pedido debe seguir el orden establecido"

        return None

    order = get_object_or_404(Order, pk=order_id)

    # Check if user is admin, vendor, or the owner of the order
    try:
        profile = request.user.profile
        is_admin = profile.is_admin() or request.user.is_superuser
        is_vendedor = profile.is_vendedor()
    except:
        is_admin = False
        is_vendedor = False

    # Allow: admin, vendor, or own order
    if not (is_admin or is_vendedor or order.user == request.user):
        messages.error(request, "No tienes permisos")
        return redirect("order_list")

    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if new_status not in valid_statuses:
        messages.error(request, "Estado no válido")
        return redirect("order_list")

    # Si el pedido ya fue entregado, no puede modificarse nunca más (incluye cualquier actualización).
    if order.status == "delivered":
        messages.error(request, "El pedido entregado ya no puede ser modificado")
        return redirect("order_list")

    # Si no está entregado, validar la transición.
    error = _validate_transition(order, new_status) if new_status != "cancelled" else None


    # Only admin/vendor can change to any status in the flow.
    # Client can only mark as delivered when shipped (and only as the next step).
    if order.user == request.user and not is_admin and not is_vendedor:
        if new_status != "delivered":
            messages.error(request, "El pedido debe seguir el orden establecido")
            return redirect("order_list")

    if error:
        messages.error(request, error)
        return redirect("order_list")

    old_status = order.status
    order.status = new_status

    # Auto-update dates based on status
    if new_status == "shipped" and old_status != "shipped":
        order.shipped_at = timezone.now()
    elif new_status == "delivered" and old_status != "delivered":
        order.delivered_at = timezone.now()

    order.save()
    messages.success(request, f"Pedido #{order.id} actualizado")
    return redirect("order_list")



@login_required
def vendor_order_list(request):
    """Show all orders for vendors with their products"""
    from products.models import Product

    try:
        profile = request.user.profile
    except:
        messages.error(request, "No tienes un perfil de usuario.")
        return redirect("home")

    if not profile.is_vendedor():
        messages.error(request, "No tienes permisos de vendedor.")
        return redirect("home")

    # Get orders that contain vendor's products
    vendor_products = Product.objects.filter(seller=profile)
    order_items = OrderItem.objects.filter(product__in=vendor_products).select_related(
        "order", "product", "order__user"
    )

    # Group by order
    orders_dict = {}
    for item in order_items:
        order_id = item.order.id
        if order_id not in orders_dict:
            orders_dict[order_id] = {
                "order": item.order,
                "items": [],
                "total": 0,
            }
        orders_dict[order_id]["items"].append(item)
        orders_dict[order_id]["total"] += float(item.subtotal)

    # Filter by status
    status_filter = request.GET.get("status", "")
    if status_filter:
        orders_dict = {
            k: v for k, v in orders_dict.items() if v["order"].status == status_filter
        }

    return render(
        request, "orders/vendor_order_list.html", {"orders_dict": orders_dict}
    )


@login_required
def vendor_update_order_status(request, order_id, new_status):

    """Vendor: Update order status"""
    from products.models import Product

    def _validate_transition(order: Order, target_status: str) -> str | None:
        flow = ["pending", "processing", "shipped", "delivered"]

        if order.status == "delivered":
            return "un pedido entregado ya no puede ser modificado"

        if target_status not in flow:
            return "El pedido debe seguir el orden establecido"

        try:
            current_idx = flow.index(order.status)
        except ValueError:
            return "El pedido debe seguir el orden establecido"

        new_idx = flow.index(target_status)

        if new_idx != current_idx + 1:
            return "El pedido debe seguir el orden establecido"

        return None

    order = get_object_or_404(Order, pk=order_id)


    try:
        profile = request.user.profile
    except:
        messages.error(request, "No tienes un perfil de usuario.")
        return redirect("home")

    if not profile.is_vendedor():
        messages.error(request, "No tienes permisos de vendedor.")
        return redirect("home")

    # Verify vendor has products in this order
    vendor_products = Product.objects.filter(seller=profile)
    order_items = OrderItem.objects.filter(order=order, product__in=vendor_products)

    if not order_items.exists():
        messages.error(request, "Este pedido no contiene tus productos.")
        return redirect("vendor_order_list")

    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if new_status not in valid_statuses:
        messages.error(request, "Estado no válido")
        return redirect("vendor_order_list")

    # Bloqueo: si el pedido ya fue entregado, no puede modificarse nunca más (incluye cambiar a cancelado).
    if order.status == "delivered":
        messages.error(request, "El pedido entregado ya no puede ser modificado")
        return redirect("vendor_order_list")

    error = _validate_transition(order, new_status) if new_status != "cancelled" else None
    if error:
        messages.error(request, error)
        return redirect("vendor_order_list")



    old_status = order.status
    order.status = new_status

    # Auto-update dates based on status
    if new_status == "shipped" and old_status != "shipped":
        order.shipped_at = timezone.now()
    elif new_status == "delivered" and old_status != "delivered":
        order.delivered_at = timezone.now()

    order.save()
    messages.success(request, f"Pedido #{order.id} actualizado a '{new_status}'")
    return redirect("vendor_order_list")



@login_required
def warranty_claim(request, order_id):
    """CLIENTE: crear garantía.

    Reglas:
    - Prohibido para VENDEDOR.
    - Solo el dueño del pedido puede crear.
    """
    from django.http import HttpResponseForbidden

    # Bloquear VENDEDOR (y superuser si aplica)
    try:
        if request.user.profile.is_vendedor() or request.user.is_superuser:
            return HttpResponseForbidden("Permiso denegado")
    except Exception:
        pass

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == "POST":
        form = WarrantyClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.order = order
            claim.user = request.user
            claim.save()
            messages.success(request, f"Garantía creada para el pedido #{order.id}")
            return redirect("order_detail", order_id=order.id)
    else:
        form = WarrantyClaimForm()

    return render(
        request,
        "orders/warranty_claim.html",
        {
            "form": form,
            "order": order,
        },
    )



@login_required
def warranty_claim_list(request):
    """CLIENTE: ver garantías.

    Reglas:
    - Prohibido para VENDEDOR.
    """
    from django.http import HttpResponseForbidden

    try:
        if request.user.profile.is_vendedor() or request.user.is_superuser:
            return HttpResponseForbidden("Permiso denegado")
    except Exception:
        pass

    claims = WarrantyClaim.objects.filter(user=request.user).order_by("-created_at")

    return render(
        request,
        "orders/warranty_claim_list.html",
        {
            "claims": claims,
        },
    )



@login_required
def order_delete(request, order_id):
    """AJAX delete order endpoint.

    Reglas de permisos:
    - SOLO VENDEDOR puede eliminar pedidos (Cliente NO).
    - Solo pedidos con status='pending'.
    """

    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "Método no permitido"}, status=405)

    order = get_object_or_404(Order, pk=order_id)

    # Permission: solo vendedor
    is_vendedor = False
    try:
        is_vendedor = request.user.profile.is_vendedor()
    except Exception:
        is_vendedor = False

    if not is_vendedor:
        return JsonResponse({"ok": False, "message": "Permiso denegado"}, status=403)

    # Business rule: only allow deleting pending orders
    if order.status != "pending":
        return JsonResponse(
            {
                "ok": False,
                "message": "Solo puedes eliminar pedidos pendientes.",
            },
            status=400,
        )

    order.delete()
    return JsonResponse({"ok": True})



@login_required
def order_delete_confirm(request, order_id):
    """Delete order endpoint (non-AJAX) for the modern modal in order_detail.

    Reglas:
    - SOLO VENDEDOR puede eliminar pedidos (Cliente NO).
    - Solo pedidos con status='pending'.
    """
    from django.http import HttpResponseForbidden

    if request.method != "POST":
        return redirect("order_detail", order_id=order_id)

    order = get_object_or_404(Order, pk=order_id)

    # Permission: solo vendedor
    is_vendedor = False
    try:
        is_vendedor = request.user.profile.is_vendedor()
    except Exception:
        is_vendedor = False

    if not is_vendedor:
        return HttpResponseForbidden("Permiso denegado")

    # Business rule: only allow deleting pending orders
    if order.status != "pending":
        messages.error(request, "Solo puedes eliminar pedidos pendientes.")
        return redirect("order_detail", order_id=order_id)

    order.delete()
    messages.success(request, "Pedido eliminado correctamente.")
    return redirect("order_list")
    
@login_required
def save_vendor_message(request, order_id):
    if request.method != "POST":
        return redirect("order_list")
    
    order = get_object_or_404(Order, pk=order_id)

    try:
        profile = request.user.profile
        is_vendedor = profile.is_vendedor()
        is_admin = profile.is_admin() or request.user.is_superuser
    except:
        is_vendedor = False
        is_admin = False

    if not (is_vendedor or is_admin):
        messages.error(request, "No tienes permisos.")
        return redirect("order_list")

    message_text = request.POST.get("message", "").strip()

    vendor_message, created = OrderVendorMessage.objects.get_or_create(
        order=order
    )

    vendor_message.message = message_text
    vendor_message.save()

    messages.success(request, "Mensaje enviado al cliente.")
    return redirect("order_list")