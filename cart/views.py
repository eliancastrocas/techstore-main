from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType


from .models import Cart, CartItem
from products.models import Product, Service, StockMovement
from users.models import UserProfile


def _user_is_cliente(request):
    """True sólo si el usuario autenticado tiene rol 'cliente'."""
    if not request.user.is_authenticated:
        return False
    try:
        return hasattr(request.user, "profile") and request.user.profile.is_cliente()
    except Exception:
        return False


def _block_if_not_cliente(request):
    """Bloquea backendmente cualquier intento de carrito/compra para roles no-cliente."""
    if not _user_is_cliente(request):
        messages.error(
            request,
            "No tienes permisos para realizar compras. Solo los clientes pueden comprar.",
        )
        # No asumimos existencia de una ruta específica; usamos home como fallback.
        # La UI del carrito también quedará bloqueada/redirigida.
        return redirect("home")
    return None



def cart_detail(request):
    """Show the user's shopping cart"""
    blocked = _block_if_not_cliente(request)
    if blocked:
        return blocked
    cart = Cart.get_cart(request)
    return render(request, "cart/cart_detail.html", {"cart": cart})



def cart_add_product(request, product_id):
    """Add a product to the cart"""
    blocked = _block_if_not_cliente(request)
    if blocked:
        return blocked
    product = get_object_or_404(Product, pk=product_id)

    cart = Cart.get_cart(request)
    content_type = ContentType.objects.get_for_model(Product)

    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        content_type=content_type,
        object_id=product_id,
        defaults={"quantity": 1},
    )

    # Bloquear que el cliente agregue más de lo disponible en stock
    # (si no hay stock, no permitimos agregar nada)
    max_stock = product.stock if getattr(product, "stock", None) is not None else 0
    if max_stock <= 0:
        messages.error(request, f"No hay stock disponible para {product.name}.")
        # si se creó con defaults, lo eliminamos
        if item_created and cart_item.quantity > 0:
            cart_item.delete()
        return redirect("cart_detail")

    if not item_created:
        # si ya tenía 1 o más, intentamos incrementar pero sin pasar el máximo
        cart_item.quantity = min(cart_item.quantity + 1, max_stock)
        cart_item.save()
    else:
        # si fue creado con defaults=1, aseguramos que no supere el stock
        cart_item.quantity = min(cart_item.quantity, max_stock)
        cart_item.save()

    if cart_item.quantity >= max_stock:
        messages.success(
            request,
            f"{product.name} agregado al carrito (máximo disponible: {max_stock}).",
        )
    else:
        messages.success(request, f"{product.name} agregado al carrito")
    return redirect("cart_detail")



def cart_add_service(request, service_id):
    """Add a service to the cart"""
    blocked = _block_if_not_cliente(request)
    if blocked:
        return blocked
    service = get_object_or_404(Service, pk=service_id)

    cart = Cart.get_cart(request)
    content_type = ContentType.objects.get_for_model(Service)

    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        content_type=content_type,
        object_id=service_id,
        defaults={"quantity": 1},
    )

    if not item_created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f"{service.name} agregado al carrito")
    return redirect("cart_detail")


def cart_remove(request, item_id):
    """Remove an item from the cart"""
    blocked = _block_if_not_cliente(request)
    if blocked:
        return blocked
    cart = Cart.get_cart(request)

    cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item_name = cart_item.item.name
    cart_item.delete()
    messages.success(request, f"{item_name} eliminado del carrito")
    return redirect("cart_detail")


def cart_update(request, item_id):
    """Update quantity of a cart item.

    Supports AJAX: returns JSON with updated subtotal for the item and total cart.
    """
    blocked = _block_if_not_cliente(request)
    if blocked:
        return blocked

    cart = Cart.get_cart(request)

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get(
        "ajax"
    ) == "1"

    if request.method == "POST":
        cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        raw_quantity = request.POST.get("quantity", "1")
        try:
            quantity = abs(int(raw_quantity))
        except ValueError:
            quantity = 1

        removed = False
        if quantity <= 0:
            cart_item.delete()
            removed = True
        else:
            # Para productos: no permitir superar el stock disponible
            if cart_item.content_type.model == "product":
                product = cart_item.item
                max_stock = (
                    product.stock if getattr(product, "stock", None) is not None else 0
                )
                if max_stock <= 0:
                    cart_item.delete()
                    removed = True
                    messages.error(
                        request, f"No hay stock disponible para {product.name}."
                    )
                else:
                    cart_item.quantity = min(quantity, max_stock)
                    cart_item.save()
            else:
                # Para servicios: solo setear
                cart_item.quantity = quantity
                cart_item.save()

        # Response
        if is_ajax:
            # cart_item may have been deleted
            updated_cart = Cart.get_cart(request)

            def format_cop(amount):
                # Django's currency template filter is not available in views.
                # Format as: $1,610,000 COP
                try:
                    amount_float = float(amount)
                except Exception:
                    amount_float = 0.0
                # round to nearest integer peso
                pesos = int(round(amount_float))
                return f"${pesos:,} COP"

            response = {
                "item_id": item_id,
                "removed": removed,
                "cart_total": str(updated_cart.total),
                "cart_total_formatted": format_cop(updated_cart.total),
                "cart_item_count": updated_cart.item_count,
            }

            if not removed:
                updated_item = updated_cart.items.get(pk=item_id)
                response["item_quantity"] = updated_item.quantity
                response["item_subtotal"] = str(updated_item.subtotal)
                response["item_subtotal_formatted"] = format_cop(
                    updated_item.subtotal
                )

            return JsonResponse(response)



        return redirect("cart_detail")

    return redirect("cart_detail")




def cart_clear(request):
    """Clear all items from the cart"""
    blocked = _block_if_not_cliente(request)
    if blocked:
        return blocked
    cart = Cart.get_cart(request)
    cart.items.all().delete()
    messages.success(request, "Carrito vaciado")
    return redirect("cart_detail")


@login_required
def checkout(request):
    blocked = _block_if_not_cliente(request)
    if blocked:
        return blocked

    print("[checkout] GET/POST recibido. user=", request.user)
    if request.method != "POST":
        print("[checkout] NO es POST, renderizando checkout GET")


    cart = Cart.get_cart(request)

    print("[checkout] cart items count:", cart.items.count())

    if not cart.items.exists():
        messages.error(request, "Tu carrito está vacío")
        print("[checkout] carrito vacío, redirigiendo")
        return redirect("cart_detail")

    from .forms import CheckoutForm
    from orders.models import Order, OrderItem

    if request.method == "POST":
        print("[checkout] POST recibido")
        print("[checkout] request.POST:", dict(request.POST))
        form = CheckoutForm(request.POST)
        is_valid = form.is_valid()
        print("[checkout] form.is_valid() =>", is_valid)
        if not is_valid:
            print("[checkout] form.errors:", form.errors)
            messages.error(request, "Error de validación en el formulario de checkout")
            return render(request, "cart/checkout.html", {"cart": cart, "form": form})

        # form válido: continuar
        if form.is_valid():
            delivery_type = form.cleaned_data["delivery_type"]

            estimated_days = 1 if delivery_type == "pickup" else 3

            if form.cleaned_data.get("delivery_address"):
                address = form.cleaned_data["delivery_address"].lower()
                if "bogota" in address or "bogotá" in address:
                    estimated_days = 2
                elif "medellin" in address or "medellín" in address:
                    estimated_days = 2
                elif "cali" in address or "barranquilla" in address:
                    estimated_days = 3
                else:
                    estimated_days = 5

            print("[checkout] creando Order. cart.total=", cart.total)
            order = Order.objects.create(
                user=request.user,
                total=cart.total,
                status="pending",
                payment_method=form.cleaned_data["payment_method"],
                bank_name=form.cleaned_data.get("bank_name"),
                bank_account_number=form.cleaned_data.get("bank_account_number"),
                card_holder_name=form.cleaned_data.get("card_holder_name"),
                card_number=form.cleaned_data.get("card_number"),
                delivery_type=delivery_type,
                delivery_address=form.cleaned_data.get("delivery_address"),
                pickup_full_name=form.cleaned_data.get("pickup_full_name"),
                pickup_document=form.cleaned_data.get("pickup_document"),
                pickup_phone=form.cleaned_data.get("pickup_phone"),
                pickup_date=form.cleaned_data.get("pickup_date"),
                estimated_delivery_days=estimated_days,
            )
            print("[checkout] Order creado: id=", order.id)

            for cart_item in cart.items.all():
                if cart_item.content_type.model == "product":
                    product = cart_item.item
                    requested_qty = cart_item.quantity

                    max_stock = product.stock if getattr(product, "stock", None) is not None else 0
                    if max_stock <= 0:
                        # si ya no hay stock, no generamos el item del pedido
                        messages.error(
                            request,
                            f"{product.name} no tiene stock disponible. Se omitió del pedido.",
                        )
                        continue

                    # ajustar cantidad al máximo disponible
                    quantity = min(requested_qty, max_stock)

                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.price,
                    )

                    # Get seller for stock movement (use buyer if no seller)
                    seller = product.seller
                    if not seller:
                        # Try to get seller's profile for the movement
                        try:
                            if hasattr(request.user, "profile"):
                                seller = request.user.profile
                        except Exception as e:
                            print("[checkout] error obteniendo seller para movimiento producto:", e)
                            seller = None


                    # Create stock movement (salida/compra) - stock update happens automatically
                    StockMovement.objects.create(
                        product=product,
                        movement_type="compra",
                        quantity=quantity,
                        reason=f"Venta - Pedido #{order.id}",
                        created_by=seller,
                        order=order,
                    )


                elif cart_item.content_type.model == "service":
                    service = cart_item.item
                    quantity = cart_item.quantity

                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        service=service,
                        quantity=quantity,
                        price=service.price,
                    )

                    # Get seller for stock movement (use buyer if no seller)
                    seller = service.seller
                    if not seller:
                        try:
                            if hasattr(request.user, "profile"):
                                seller = request.user.profile
                        except Exception as e:
                            print("[checkout] error obteniendo seller para movimiento servicio:", e)
                            seller = None


                    # Create stock movement for service
                    StockMovement.objects.create(
                        product=None,  # Services don't have stock
                        movement_type="compra",
                        quantity=quantity,
                        reason=f"Servicio vendido - Pedido #{order.id} - {service.name}",
                        created_by=seller,
                        order=order,
                        stock_after=None,
                    )

            # Clear cart after all items are processed
            print("[checkout] limpiando carrito y guardando order items")
            cart.items.all().delete()

            payment_msg = {

                "contra_entrega": "Pago contra entrega - Paga cuando recibas el producto",
                "transfer": "Transferencia bancaria - Te enviaremos los datos para realizar el pago",
                "card": "Pago con tarjeta - Procesando...",
            }
            msg = payment_msg.get(order.payment_method, "Pedido confirmado")
            messages.success(request, f"¡Pedido #{order.id} confirmado! {msg}")
            return redirect("order_detail", order_id=order.id)
        else:
            form = CheckoutForm()
    else:
        form = CheckoutForm()

    return render(request, "cart/checkout.html", {"cart": cart, "form": form})
