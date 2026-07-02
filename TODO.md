# TODO

## Objetivo
Agregar un sistema de mensajes del vendedor hacia el cliente dentro de pedidos y formularios (FormRequest), editable por vendedor y visible por cliente con la última versión.

## Pasos
1. (Backend) Crear modelo de mensaje asociado a `orders.Order` y a `products.FormRequest` (un solo mensaje vigente por cada entidad, con historial si se desea; requerido: última versión visible).
2. (Backend) Crear vistas/URLs:
   - `seller` puede crear/editar mensaje para un pedido.
   - `client` solo obtiene/visualiza el mensaje.
3. (Backend) Actualizar `orders/views.py` y el contexto de `order_list`/`order_detail` para incluir el mensaje más reciente del vendedor.
4. (Frontend) Actualizar `templates/orders/order_list.html` y `templates/orders/order_detail.html` para mostrar el mensaje al cliente (en “Mis Compras” / vista de pedido).
5. (Backend/Frontend) Para formularios `FormRequest`: como el cliente ve formularios dentro de `orders/`, integrar visualización y mensaje en `templates/orders/order_list.html` sin modificar otras funcionalidades.
6. (Vendedor) Agregar textarea + botón “Guardar” para mensajes tanto en vista de pedido como en el panel vendedor que lista `vendor_form_requests` (o equivalente). # Nota: si la vista exacta no lista editable, se agrega en `order_detail` si aplica.

7. Migraciones y pruebas:
   - Crear migración.
   - Correr migraciones.
   - Probar flujo: vendedor escribe/actualiza → cliente recarga y ve último mensaje.

