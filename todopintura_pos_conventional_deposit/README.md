# todopintura_pos_conventional_deposit

Addon para operar pedidos en depósito dentro del POS convencional.

- `Vacío`: sin venta a crédito ni depósito.
- `Crédito`: venta a crédito permitida en cualquier tienda.
- `Depósito`: el pedido se envía a depósito y, cuando se liquida, se cobra siempre completo.

El asistente de cobro de depósitos permite seleccionar uno o varios pedidos del mismo cliente y caja,
y genera una única factura con pago completo de los pedidos seleccionados.

Este addon depende de `todopintura_extend_pos_conventional` y mantiene compatibilidad con el booleano legado `pos_credit_sale_enabled`.

