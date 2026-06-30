from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Order, OrderItem, WarrantyClaim
from products.models import Product
from .forms import WarrantyClaimForm


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

    return render(
        request,
        "orders/order_list.html",
        {"orders": orders, "is_admin": is_admin, "is_vendedor": is_vendedor},
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
        {"order": order, "is_admin": is_admin, "is_vendedor": is_vendedor},
    )



@login_required
def order_approve(request, order_id):
    """Approve/receive order when delivered"""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.status in ["shipped", "delivered"]:
        order.status = "delivered"
        order.save()
        messages.success(request, f"Pedido #{order.id} marcado como recibido")
    else:
        messages.error(request, "El pedido debe estar enviado para confirmar recepción")
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

    # Only admin/vendor can change to any status, client can only mark as delivered
    if order.user == request.user and not is_admin and not is_vendedor:
        # Client can only mark as delivered when shipped
        if new_status not in ["delivered"]:
            messages.error(request, "Solo puedes marcar como recibido")
            return redirect("order_list")
        if order.status != "shipped":
            messages.error(request, "El pedido debe estar enviado para confirmar")
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

    old_status = order.status
    order.status = new_status

    if new_status == "shipped" and old_status != "shipped":
        order.shipped_at = timezone.now()

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



