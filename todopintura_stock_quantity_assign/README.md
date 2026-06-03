# Todopintura Stock Quantity Assign

## Descripción

Este módulo evita que se rellenen automáticamente las cantidades en los movimientos de stock (pickings) relacionados con órdenes de compra.

## Funcionalidad

Cuando se confirma una orden de compra que genera un picking (ya sea por rutas o reglas de abastecimiento):

- El picking se crea normalmente
- Los movimientos de stock (stock.move) se crean pero con cantidad = 0
- El usuario debe rellenar manualmente el campo "quantity" en cada línea del picking

Esto permite un mayor control manual sobre las cantidades recibidas en las compras.

## Dependencias

- stock
- purchase_stock

## Instalación

1. Agregar el módulo a la ruta de addons de Odoo
2. Actualizar la lista de módulos
3. Instalar el módulo "Todopintura Stock Quantity Assign"

## Configuración

No requiere configuración adicional. El módulo funciona automáticamente una vez instalado.

## Uso

1. Crear una orden de compra
2. Confirmar la orden de compra
3. Abrir el picking generado
4. Observar que las cantidades están en 0
5. Rellenar manualmente las cantidades de cada producto

## Autor

Xtendoo

## Licencia

AGPL-3.0
