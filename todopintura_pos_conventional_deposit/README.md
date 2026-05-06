# todopintura_pos_conventional_deposit

Primer paso para separar el comportamiento de clientes del POS convencional en tres modos:

- `Vacío`: sin venta a crédito ni depósito.
- `Crédito`: venta a crédito permitida en cualquier tienda.
- `Depósito`: reservado para la futura operativa de depósitos, reutilizando las tiendas permitidas del partner.

Este addon depende de `todopintura_extend_pos_conventional` y mantiene compatibilidad con el booleano legado `pos_credit_sale_enabled`.

