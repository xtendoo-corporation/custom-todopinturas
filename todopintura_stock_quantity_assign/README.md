# Todopintura Stock Quantity Assign

## Descripción

Este módulo evita que se rellenen automáticamente las cantidades en los movimientos de stock (pickings) relacionados con órdenes de compra.

## Funcionalidad

Cuando se confirma una orden de compra que genera un picking (ya sea por rutas o reglas de abastecimiento):

- El picking se crea normalmente
- Los movimientos de stock (stock.move) se crean pero con cantidad = 0
- El usuario debe rellenar manualmente el campo "quantity" en cada línea del picking

### Escaneo de códigos de barras

El módulo incluye soporte nativo para escaneo de códigos de barras usando el módulo `barcodes` de Odoo:

- **Sin dependencias adicionales**: No requiere módulos externos como `xtendoo_stock_barcode` o `stock_barcode`
- Al escanear el código de barras o código de referencia (default_code) de un producto en un picking, se incrementa automáticamente la cantidad en 1
- Actualiza tanto el movimiento (stock.move) como la línea de detalle (stock.move.line)
- Funciona con escáneres de código de barras físicos o mediante el campo de entrada del formulario del picking
- Muestra mensajes informativos si el producto no se encuentra o no está en el picking

#### Cómo funciona el escaneo:

1. El modelo `stock.picking` hereda de `barcodes.barcode_events_mixin`
2. La vista del picking incluye el campo `_barcode_scanned` con widget `barcode_handler`
3. Cuando se escanea un código de barras:
   - Se busca el producto por código de barras o referencia interna
   - Se localiza el movimiento correspondiente en el picking
   - Se crea o actualiza una línea de movimiento (move_line) incrementando la cantidad en 1
   - Se marca la línea como "picked"

Esto permite un mayor control manual sobre las cantidades recibidas en las compras.

## Dependencias

- **stock**: Gestión de inventario
- **purchase_stock**: Integración de compras con inventario
- **barcodes**: Sistema de códigos de barras de Odoo (módulo estándar)

## Instalación

1. Agregar el módulo a la ruta de addons de Odoo
2. Actualizar la lista de módulos
3. Instalar el módulo "Todopintura Stock Quantity Assign"

## Configuración

No requiere configuración adicional. El módulo funciona automáticamente una vez instalado.

## Uso

### Uso Manual

1. Crear una orden de compra
2. Confirmar la orden de compra
3. Abrir el picking generado
4. Observar que las cantidades están en 0
5. Rellenar manualmente las cantidades de cada producto

### Uso con Escaneo de Códigos de Barras

1. Crear una orden de compra
2. Confirmar la orden de compra
3. Abrir el picking generado
4. Escanear el código de barras de cada producto recibido
5. La cantidad se incrementará automáticamente con cada escaneo
6. Continuar escaneando hasta completar la recepción

## Autor

Xtendoo

## Licencia

AGPL-3.0
